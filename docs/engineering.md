# Engineering

## Delivery pipeline

- **One repository** for all agents. The live machine is never edited by hand.
- **Pull-based deploy bot** (a systemd timer, every 5 minutes) on the always-on machine:
  1. fetch `main` into its own clone, which nobody edits;
  2. checks: secret and personal-data scan, every Python file compiles, the full offline regression suite;
  3. **drift guard**: refuse to deploy if a live file was edited outside git, and say how to fix it;
  4. copy changed files live with backups, restore generated blocks inside instruction files, re-pin hashes;
  5. report a commit status to GitHub, and alert on WhatsApp on failure.
- **Behaviour evals on real turns**, at most once a night and only for an agent whose instructions
  changed, so they cost nothing on a quiet day.
- **Quiet windows**: no deploys or restarts during the scheduled business runs.
- Things the bot deliberately does not do (restart the gateway, install the crontab, copy Windows-side
  files) are done by hand and logged with who, what, why and how to undo.

Reference implementation: [`agency/gate/deploy.py`](../agency/gate/deploy.py) and
[`agency/gate/drift.py`](../agency/gate/drift.py).

## Tests

- In production: 62 test files and 627 tests, all offline: throwaway folders, no WhatsApp, no mailbox, no
  model calls. This repository's reference code has its own 6 offline suites, run by CI on every push.
- Found automatically by a small runner, one line per suite, real exit codes
  ([`agency/gate/run_tests.py`](../agency/gate/run_tests.py)).
- Every fixed incident gets a regression test that reproduces it, and a test is never weakened to get a
  deploy through.
- **Instructions are tested too.** When a behaviour changes, its old wording goes on a retired-facts list,
  and a test fails the deploy if any instruction file still says it.

## Context for coding agents

Several coding tools work on this system, at different times and on different machines. Each one reads
the same pack before changing anything: the rules and the checklist for every change, the architecture,
a generated map of every file and where it runs live, a generated day-by-day progress log, and a lessons
file. Every commit updates the agent's changelog and the architecture in the same commit, and a morning
check reads the new commits and the live system and reports any gap, such as a Windows-side file that
differs from the repository.

## Guardrails and traceability

- **Pre-commit privacy scan** blocks secrets, private chat links and denylisted names, and flags unknown
  emails and phone numbers. It scans the staged copy of each file, so a secret removed from the working
  copy after staging is still caught, and commit messages are scanned too
  ([`agency/gate/scan.py`](../agency/gate/scan.py)).
- **Every commit names its author and reason** with `Agent:` and `Why:` trailers, whether the author is a
  person, an AI coding tool or one of the agents. A commit-msg hook checks it, and the deploy-time tests
  check every commit again, so skipping the hook still cannot reach production
  ([`agency/gate/trace.py`](../agency/gate/trace.py)).
- **Per-author access list.** The agents start with no code access; specific paths are opened one agent
  at a time. The rules, the deploy system and the hooks are protected, and each commit is judged by the
  rules as they were before it, so no commit can widen its own access.
- **Behavioural walls**: walled Linux users, sender-verified command lines, a mail bridge with no send
  function, drafts-only outbound mail, one-time codes never kept, long numbers masked, never storing
  passwords.

A note on what the trailers prove: they are written by the author, so they make an audit trail and catch
honest mistakes and drifting AI sessions. They are not protection against someone deliberately forging a
trailer; signed commits and a protected branch with required review are the next layer for that.

## Token efficiency

- **Code first.** Filtering, scoring, scheduling, filing, formatting, status and counts are all plain code.
  A model is called only to judge a short list or understand free text, at low effort.
- **Read once, log once.** Mail is triaged once by a watcher and written to a plain-text log; the agents
  read the log instead of the mailbox. Each reader sets its own limit, and a limit is checked against the
  part that matters (a summary card once lost a whole section when a file it read the first 8,000
  characters of was reorganised).
- **Cost is measured per action** ([`agency/inbox/cost.py`](../agency/inbox/cost.py)).
- **Model choice was A/B tested where it mattered.** On the same 16 items, a cheaper model flipped 4
  verdicts between runs and the stronger one flipped 2, with better reasons, so the stronger model judges.

## Operations

- Health checks every 10 minutes; an offline alert after WhatsApp outages; usage alerts at fixed
  thresholds.
- Nightly snapshots and a rolling conversation memory per agent.
- Memory-aware: browser windows open on demand and close after 10 idle minutes.

## Lessons that cost the most

Kept as a file every coding agent reads before a fix. The general ones:

1. **Verify the final output, not an intermediate value.** A fix changed the decision function, the
   summary said the draft was addressed correctly, and the real draft still went to a mailing list. After
   any change to something an agent sends, look at the real thing it produced.
2. **A missing model answer is not a "no".** Missing output once fell back to the risky choice. No answer
   means do nothing, say so, retry.
3. **Caps and truncation drop items silently.** A ranker that read the first 1,800 characters missed
   requirements in 38 of 60 items. Count and name what is past a cap.
4. **The sender is not the person.** Mailing lists and robot senders were taken for people. Treat them as
   relays and find the real party, or stop.
5. **"Couldn't look" is not "nothing found".** With the internet down, every search failed and the run
   reported no matches. Tell a failed read from an empty one, and alert when a periodic job finds nothing
   for days.
6. **Trial runs must not write live state.** A dry run rewrote the day's report. A trial writes only trial
   files and never moves a bookmark.
7. **New state must survive a save.** The same alert posted every 75 minutes through three fixes, because
   the new field was not in the list of keys that were saved. Test that a new field survives a save and a
   load.
8. **A silent job looks like a broken job.** Make the log say why it stayed silent, and read that log
   before calling it broken.
9. **A fresh self-test is not the live chat.** A fix passed in new sessions while the live session kept
   copying its own earlier wording. Judge a fix on the next real reply; a slip that keeps repeating is
   fixed in code.
10. **Host failures look like agent failures.** A full Windows disk took every agent down for 7 hours
    while the health check said "ok", because it measured the Linux virtual disk. When everything goes
    quiet, check the host first.

## What the reference code in this repo covers

| Production piece | Here |
|---|---|
| Secret and personal-data scan | `agency/gate/scan.py` |
| Commit traceability and per-author access | `agency/gate/trace.py`, `PROJECT/ACCESS.json`, `hooks/` |
| Drift guard, quiet windows, deploy with backups | `agency/gate/drift.py`, `agency/gate/deploy.py` |
| Test runner | `agency/gate/run_tests.py` |
| The Handler's sender-verified command lines, explicit asks for side effects, per-agent walls | `agency/dispatch/commands.py` |
| Mail triage: rules first, costed judge, no guessing, masking, log limits, silent summaries | `agency/inbox/triage.py` |
| Cost ledger | `agency/inbox/cost.py` |

The reference code is a fresh, simplified rewrite: same decisions, no private data, standard library only.
Not included: the agents' prompts, the model judge's rubric and the behaviour evals, because they are
built around real people's data. The judge here is a deterministic offline stand-in with the same
interface, so the triage and its cost accounting can be run and tested anywhere.
