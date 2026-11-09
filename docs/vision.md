# The vision: one Handler, many agents

## The problem with more than one agent

A single agent is a project. Several agents are an operation. Each new agent brings another chat to
watch, another set of permissions, another schedule, another way to fail quietly at 3 a.m., and another
chance to say something to the wrong person.

The Agency makes this sharp on purpose. Its two field agents could not be more different:

| | The Operations agent | The Assistant |
|---|---|---|
| Serves | A small business team | Two people in a private chat |
| Stakes | Business: reports, timesheets, reminders | Trust: a personal conversation |
| Must never | Mail a person without a human pressing Send | Leak anything, anywhere |

Both run every day. They must never leak into each other. And one person has to run both, mostly from a
phone.

## The answer: a Handler

In an intelligence agency, field agents do the work and a handler runs them: one point of contact,
orders given deliberately, nothing passed between agents that the handler did not authorise. The Agency
works the same way: **one agent is the Handler.**

### What the Handler does

- **Oversight.** Every 10 minutes the Handler checks the gateway, the WhatsApp channels, the scheduled jobs, the
  deploys and the browser windows. It alerts on failure, reports usage at fixed thresholds, and every
  morning reads the new commits and the live system for any change that skipped its records.
- **Command.** I ask in plain language from my phone ("how did the 15:00 run go?", "tell the operations agent to
  re-run the weekly report"). The Handler answers and, when something needs doing, writes a visible `🔧` command
  line in its reply. Code posts the result; the model never retells it.
- **Relay, only on request.** The Handler passes a message to the Operations agent or the Assistant only when I explicitly ask for it.
- **Mail and calendar.** The Handler triages my mail every 2 minutes (hourly overnight) into a plain-text log and posts summaries at
  fixed times, only when something is new. It reads mail and calendar through a bridge that can read,
  draft and manage the calendar but has no send function at all.
- **Phone.** Texts, missed calls and voicemails reach the Handler group through a token that can only add
  alerts.

### What the Handler cannot do

This half matters more.

- **It cannot act on its own.** The Handler has no free tool access and cannot write files. A separate dispatcher
  process reads each command line and runs it only if the message that triggered the reply came from my own
  number and the command is on the allowlist. Anything with side effects also needs me to have asked for
  it in that message, so a command smuggled in through text the Handler reads, such as an email or a web page,
  is held rather than run.
- **It cannot open a back channel.** A relay that I did not explicitly ask for is held, and a topic guard
  keeps personal subjects from crossing between agents.
- **It cannot quietly change the system.** Every change to the code, by me, by an AI coding tool or
  by an agent, must say who made it and why, and must stay inside the files that author may touch. The
  rules themselves are protected, and no change can widen its own access.

The reference implementation of the dispatcher, with per-agent walls and an audit log, is in
[`agency/dispatch/commands.py`](../agency/dispatch/commands.py). Run
`python3 examples/handler_demo.py` to watch it decide six messages, including an email that tries to
smuggle in a command.

## Walls, not promises

The boundaries are enforced outside the model, in code or by the operating system, not by asking a model
nicely:

| Boundary | Enforced by |
|---|---|
| Agents cannot read each other's files | A separate Linux user and allow-list per agent |
| The Handler cannot act without me | A dispatcher outside the model that checks the sender and the ask |
| The Handler cannot send mail, and reminders to people are never sent by an agent | The Handler's bridge has no send function; reminders are drafts a person sends |
| The Assistant's reader cannot reach mail | Mail services blocked at the resolver for that browser |
| A commit cannot widen its own access | Each commit judged by the rules in its parent |

Two of these checks are keyword rules rather than hard walls: "did I ask for it" and the topic guard.
They stop accidents and casual injection; a confirmation step for anything irreversible is the next
layer, and the first thing I would harden.

## Where it is going

- **A control plane, not a chat.** The Handler is the one place to see and steer the whole agency.
  Adding an agent should mean a walled user, a WhatsApp binding and an entry in the Handler's roster, not one
  more thing to watch.
- **Agents that improve themselves, carefully.** The agents start with no access to their own code.
  Specific files are opened to one agent at a time, under the same traceability rules as any developer,
  so the system can learn from its own operation without anyone losing track of who changed what.
- **The same pattern for any team.** Nothing here is specific to one business. A team with a WhatsApp group,
  a repetitive workflow and a few judgement calls a day can get its own field agent, run by the same
  Handler.
