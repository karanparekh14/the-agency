# How an agent is built

This is the pattern the agents in the system are built on, from an empty folder to a live agent in a
WhatsApp group.

## 1. Start from the job, not the model

Write down what the agent is for, who will talk to it, and what it must never do. For the operations
agent that meant: run the team's scheduled report and its weekly paperwork, talk only to the team, never
mail anyone without a human pressing Send.

Then split the job into **what rules can decide** and **what needs judgement**. De-duplication, filters,
scoring, filing, formatting, status and counts are rules. Judging a short list and understanding free
text need a model. Everything in the first list becomes plain code; the model only gets the second.

## 2. Give it a channel and a binding

The OpenClaw gateway connects to WhatsApp and routes each group to exactly one agent. A binding says
"this group belongs to this agent". In large groups, only messages that mention the agent reach the
model, which keeps cost down and stops the agent from answering every message.

## 3. Write its instructions as files

Each agent has instruction files that the runtime loads: who it is, who it serves, its rules, and how to
reply. Some blocks inside those files are generated, for example the rolling 7-day conversation memory
that a keeper job rewrites every 10 minutes. The deploy pipeline knows which blocks are generated and
restores them after copying a new version live.

## 4. Give it tools as scripts, not as free access

An agent's abilities are small scripts with one job each (run the report, file a timesheet, read the
mail log, post a summary). Each one does the deterministic part in code and returns a short, structured
result for the agent to talk about. When a script needs judgement, it calls the model itself, with a
fixed rubric, and logs what the call cost.

For an agent that reads outside text, go further: no free tool access at all, and let it act only through
visible command lines that a dispatcher checks against the sender and, for anything with side effects,
against what the sender actually asked for
([`agency/dispatch/commands.py`](../agency/dispatch/commands.py)).
Code posts the result; the model never retells it.

## 5. Put it behind a wall

Each agent runs its model turns as its own Linux user with its own allow-list, so it cannot read the
other agents' files or the Handler's. Messages it wants to send go into an outbox, and a small trusted
process checks them and posts them. That limits what a confused agent can reach.

## 6. Reach Windows only where you must

When a task needs Windows (Outlook, a visible browser), the agent does not drive Windows directly. A
scheduled task, registered to run in the user's interactive session, does one specific thing: open this
browser profile, save these drafts. Windows close themselves when idle.

## 7. Schedule it

Recurring work runs from cron (business runs at 10:30 and 15:00, health every 10 minutes, mail watch
every 2 minutes by day, nightly snapshots). A job that posts only when there is something new writes why it
stayed silent. The deploy pipeline knows these times and never deploys or restarts during them.

## 8. Test it offline

Every behaviour gets an offline test: throwaway folders, no WhatsApp, no mailbox, no model calls.
When something breaks in production, the fix comes with a regression test that reproduces it, for
example a missing model answer that fell back to the risky choice
([`tests/test_triage.py`](../tests/test_triage.py)). The instruction files are tested too: retired
wording fails the deploy.

## 9. Ship it through the gate

The agent's files live in the one repository. A commit passes the privacy scan and the traceability
check at commit time; the deploy bot then scans, compiles, runs every suite, checks for live edits,
and only then copies it live ([`agency/gate/`](../agency/gate/)). That night, if the agent's instructions
changed, behaviour evals replay real turns against it.

## 10. Watch it

Health checks every 10 minutes cover the gateway, the channels, the scheduled jobs, the deploys and the
browser windows. Failures alert the owner on WhatsApp, usage alerts fire at fixed thresholds, and a
morning context check reports any change that skipped its records.
