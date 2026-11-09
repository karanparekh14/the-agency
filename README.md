# The Agency

### Three AI agents. One Handler. All of it inside WhatsApp.

I built and run a small agency of AI agents that do real work for real people every day.
**The Operations agent** runs the routine operations of a small business team. **The Assistant** is a
personal assistant in a private two-person chat. **The Handler** lets me command both of them from my
phone, watches over the whole system, and cannot act without me.

Live since **25 August 2026**. Designed and built by **Karan Parekh**, with AI assisted development tools
for parts of the coding.

[![gate](https://github.com/karanparekh14/the-agency/actions/workflows/ci.yml/badge.svg)](https://github.com/karanparekh14/the-agency/actions/workflows/ci.yml)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![deps](https://img.shields.io/badge/dependencies-stdlib%20only-lightgrey)
![license](https://img.shields.io/badge/license-MIT-green)

> The production system is private because it serves real people. This repository tells its story and
> contains a runnable reference implementation of its most important parts, written fresh with no
> private data. See [What is in this repository](#what-is-in-this-repository).

**What is technically interesting here**

- **Prompt injection handled outside the model.** The Handler reads email and web pages, so it gets no
  free tool access: it can only propose visible commands, and a separate dispatcher runs them only if
  they came from my number and, for anything with side effects, only if my own message asked for that
  action.
- **Code first, model last.** Plain rules sort most of the work for free. In inbox triage, one-time codes,
  replies in my own threads and known noise are decided in code; a model judges only what is left, and
  every call is costed.
- **A deploy gate like a small company's,** run on one desktop: secret scan, tests, a drift guard that
  refuses to overwrite live edits, quiet windows, nightly behaviour checks, a test that fails a deploy when
  an instruction file repeats a retired fact, and traceability for every change by people, AI coding
  tools and the agents themselves.

---

## Meet the agents

| Agent | What it does |
|---|---|
| 🔎 **The Operations agent** | Lives in a business team's WhatsApp group. Two scheduled runs a day that end in one report, weekly timesheets filed from Outlook and checked against the team's workbook, reminder drafts for missing weeks that a person reviews and sends, a Monday scorecard, a sent log and an alert after any WhatsApp outage. |
| 🐼 **The Assistant** | Lives in a private two-person chat. Reminders, research, link reading in an isolated signed-out browser, pictures checked by a model before they are posted, voice notes transcribed locally for free, and answers taken from the chat's own record rather than a model's memory. |
| 🕶️ **The Handler** | Lives in my own WhatsApp group. My single point of command: runs the other two from my phone, checks the health of everything every 10 minutes, triages my mail every 2 minutes (hourly overnight) into a log every agent can read, posts scheduled summaries and usage reports, watches my phone's texts and missed calls, and acts only through visible commands that a separate process runs only if they came from me. |

Each agent has its own job, its own people, its own Linux user and its own wall. In production they go by
the names Scout, Panda and 007; this repository calls each one by the work it does.

---

## The vision: one Handler, many agents

Agents are easy to start and hard to run. Every new one is another chat to check, another set of
permissions, another thing that can quietly go wrong or say the wrong thing to the wrong person. Two
agents with very different lives make this sharp: the Operations agent handles business for a team, the
Assistant handles a personal conversation. They must never leak into each other, and I still need to run both.

My answer is a **Handler**, the way an intelligence agency runs field agents:

- **One place to ask "how is everything?"** The Handler checks the gateway, the channels, the scheduled
  jobs, the deploys and the browser windows every 10 minutes, alerts me when something breaks, and shows
  how many tokens each agent used.
- **One place to give orders.** I tell the Handler what I want in plain language from my phone. It turns
  that into a visible `🔧` command in its reply, and a separate dispatcher runs it only if the message came
  from my own number. The Handler itself cannot write files or call tools freely, and anything with side
  effects also needs my own message to have asked for that action, so a command smuggled into an email or a web page
  is held, not run. These are keyword rules, not magic: they stop accidents and casual injection, and
  anything irreversible should still need a confirmation.
- **No back channels.** The Handler relays to the Operations agent or the Assistant only when I explicitly
  ask, and a topic guard keeps personal subjects out of work and work out of the private chat.
- **Trust that grows slowly.** The agents start with no access to their own code. Specific files can be
  opened to one agent at a time, and every change, by me, by an AI coding tool or by an agent, must say
  who made it and why, or it never reaches production.

### A command's journey

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/diagrams/command-path-dark.svg">
  <img alt="How the dispatcher decides: four checks in order, then RAN, HELD or REFUSED, every decision logged" src="docs/diagrams/command-path-light.svg" width="100%">
</picture>

<details>
<summary><b>See the Handler decide six messages</b> (<code>python3 examples/handler_demo.py</code>)</summary>

```

Owner asks for a status check
  message: 'how is everything?'
  🔧 status: all
     -> RAN: gateway ok, 3 agents up, last 15:00 report ok, 0 alerts

Owner explicitly asks for a relay
  message: 'tell ops to re-run the weekly report'
  🔧 relay: ops re-run the weekly report
     -> RAN: queued for ops

The Handler tries a relay nobody asked for
  message: 'the afternoon report looked thin'
  🔧 relay: ops widen the afternoon report
     -> HELD: the owner did not explicitly ask for this relay

An email tries to smuggle in a command
  message: 'read me my latest email'
  🔧 book: everything
     -> HELD: has side effects and the owner did not ask for it

A relay that would cross the assistant's wall
  message: 'tell the assistant the client invoices are late'
  🔧 relay: assistant the client invoices are late
     -> REFUSED: crosses assistant's wall

Someone else tries to drive the Handler
  message: 'tell ops to book everything'
  🔧 relay: ops book everything
     -> REFUSED: trigger did not come from the owner

audit log: 6 decisions recorded, sender numbers masked
```

</details>

---

## What is in this repository

| Path | What it is |
|---|---|
| `docs/` | The story, the vision, how each agent is built, engineering and lessons, decisions, use cases and a dated timeline |
| `agency/dispatch/` | The Handler pattern: sender-verified command lines, explicit asks for side effects, per-agent walls, an audit log |
| `agency/inbox/` | Code-first inbox triage: rules before any model, a costed judge, no guessing on a missing answer, masked numbers, log limits per verdict, summaries that say why they stayed silent |
| `agency/gate/` | The deploy gate: privacy scan (staged files and commit messages), commit traceability, drift guard, quiet windows, test runner |
| `tests/` | 6 offline suites, run by CI on every push |
| `docs/diagrams/` | The three diagrams in this README, light and dark, drawn by `build.py` (standard library only) |
| `examples/` | `handler_demo.py` (the Handler deciding six messages) and `inbox_demo.py` (eight fictional emails triaged) |
| `hooks/`, `PROJECT/ACCESS.json` | The git hooks and access rules this repository itself is developed under |

The agents' production code, prompts and conversations are not here: they belong to real people. The model
judge in this repository is a deterministic offline stand-in with the same interface.

### Run it

Python 3.10 or newer, no dependencies.

```bash
python3 examples/handler_demo.py         # The Handler deciding six messages
python3 examples/inbox_demo.py           # eight fictional emails, rules first, an offline judge
python3 -m agency.gate.run_tests         # every offline suite, one line each, real exit code
python3 -m agency.gate.scan              # the privacy scan this repository is committed under
python3 -m agency.gate.trace --history   # every commit says who made it and why

git config core.hooksPath hooks          # optional: the same pre-commit and commit-msg hooks
```

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/diagrams/inbox-triage-dark.svg">
  <img alt="Inbox triage: plain rules first, a costed model judge for the rest, PENDING instead of a guess, and a mail log that keeps only what it should" src="docs/diagrams/inbox-triage-light.svg" width="100%">
</picture>

Sample run of the inbox demo:

```
CODE      by rule   Your sign-in code                       keeps nothing    (one-time code: its text is never stored)
IMPORTANT by rule   Re: kitchen tap                         keeps 63 chars   (a reply in a thread the owner wrote in)
NOISE     by rule   48 hours only: 40% off                  keeps 29 chars   (known noise sender)
IMPORTANT by judge  Payment due on card ending 4421         keeps 79 chars   (needs the owner)
NOISE     by rule   You have 3 new followers                keeps 31 chars   (social tab with no work signal)
IMPORTANT by judge  Assignment deadline moved               keeps 60 chars   (needs the owner)
FYI       by judge  Your receipt                            keeps 40 chars   (worth knowing)
NOISE     by judge  Club newsletter                         keeps 39 chars   (nothing to act on)

4 of 8 decided by plain rules; 4 judged, cost $0.000715
Card line as logged: A payment on card XXXXXXXXXXXX4421 is due on the 14th. Minim

A quiet hour: posted nothing; the log says: silent: 0 of 2 emails worth a summary since noon
```

---

## The Operations agent

A small business team already coordinates in a WhatsApp group, so the Operations agent joined that group
and took over the routine work nobody enjoys:

- **Two scheduled runs a day (10:30 and 15:00 CT).** Plain code gathers, de-duplicates, filters and
  scores; a model judges only the short list that survives; the team gets one report by email and one
  short line in the group. Deploys and restarts never happen inside these windows.
- **Timesheets at zero tokens.** Weekly timesheets are filed from Outlook with a consistent name, checked
  against the team's workbook, and the dates inside the document are checked when the subject and the
  file name disagree. Missing weeks get a reminder saved as an Outlook draft that a person reviews and
  sends. A nightly check and a weekly summary go to the group.
- **Reliability.** A Monday scorecard, a log of everything it sent, nightly snapshots, and an alert after
  any WhatsApp outage.

What the Operations agent could do next, with the same patterns, is listed honestly as **not built yet**
in [docs/use-cases.md](docs/use-cases.md#whats-next-not-built).

## The Assistant

The Assistant is a personal assistant in a private two-person chat, with tone controls agreed with both
people. It sets reminders, researches questions, reads links through an isolated, signed-out browser that cannot reach any mail service, posts pictures from a web image search only after a
small model has checked each one, transcribes voice notes on the desktop itself at no cost, and searches
its own chat history in plain code so it answers from the record. A topic guard keeps its world out of
work.

More on all three agents: [docs/agents.md](docs/agents.md) and [docs/vision.md](docs/vision.md).

---

## By the numbers

Production system, measured on 8 November 2026.

| | |
|---|---|
| Live since | 25 Aug 2026 (first agent); all three agents in one repository since 23 Sep 2026 |
| Commits | 650 from 23 Sep to 8 Nov, every one since 14 Oct naming its author and reason |
| Codebase | about 56,600 lines of Python in 183 files |
| Tests | 62 offline test files, 627 tests, run on every deploy |
| Health checks | every 10 minutes, plus a daily context check of every new commit and the live system |
| Mail | triaged every 2 minutes from 7 AM to 1 AM, hourly overnight; plain rules decide first, a model judges only the rest |
| Zero-token pipelines | timesheets, health checks, chat logs, voice-note transcription |

## Architecture

One always-on Windows desktop runs the whole agency. The agents live in WSL2 Ubuntu; what only Windows can
do (Outlook, a visible browser, scheduled tasks in the user's session) runs on the Windows side and is
reached through WSL interop.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/diagrams/architecture-dark.svg">
  <img alt="Architecture: WhatsApp groups, the gateway, three walled agents and the dispatcher, the tools they use, shared plain-text state, and the deploy pipeline" src="docs/diagrams/architecture-light.svg" width="100%">
</picture>

More: [docs/architecture.md](docs/architecture.md). How each agent is built, step by step:
[docs/how-to-build-an-agent.md](docs/how-to-build-an-agent.md).

## Engineering highlights

- **Plain code first, a model only for judgement.** Filtering, scoring, filing, formatting, status and
  counts are deterministic code. When a model ignored an instruction twice, the decision moved into code.
  Every model call is costed per action.
- **No answer means do nothing.** A missing or unclear model verdict once fell back to the risky choice
  and sent a false reply. Now it does nothing, says so, and retries on the next run.
- **Walls between agents.** Each agent runs as its own Linux user with its own allow-list. Outbound
  messages leave through an outbox that a small trusted process checks and posts.
- **Humans stay in the loop where it counts.** Mail to people is saved as drafts a person sends; the Handler's mail
  bridge has no send function at all; one-time codes are never kept in the mail log.
- **A deploy gate like a small company's.** A pull-based bot scans for secrets, compiles everything, runs
  the full offline suite, refuses to overwrite live edits, reports to GitHub and WhatsApp, and never
  deploys during the scheduled business runs. Behaviour checks on real turns run at night, only for an
  agent whose instructions changed.
- **Context for every coding agent.** Any coding tool that touches the system reads the same pack first:
  the rules, the architecture, a generated map of every file, a day-by-day progress log and the lessons
  below. A morning check reports any change that skipped them.

Detail and the lessons that cost the most: [docs/engineering.md](docs/engineering.md). The reasoning
behind each choice: [docs/decisions.md](docs/decisions.md).

## Tech stack

| Area | Used |
|---|---|
| Language | Python (standard-library heavy), PowerShell, VBScript, Google Apps Script |
| Agent runtime | OpenClaw agent gateway, Claude CLI runtime, Claude Sonnet and Claude Haiku |
| Channel | WhatsApp, one group bound to one agent |
| Platform | WSL2 Ubuntu with systemd user services and cron; Windows Task Scheduler |
| Automation | Outlook through COM; Microsoft Edge through the Chrome DevTools Protocol (own minimal WebSocket client); an Android automation app posting phone alerts to a bridge |
| Speech | SenseVoice and Whisper, both run locally |
| Data | Plain TSV and Markdown logs, Excel (openpyxl), JSON config |
| Delivery | GitHub, GitHub Actions, a pull-based deploy bot, git hooks, offline regression suites, nightly behaviour evals |

## Timeline

From one agent reviewing documents on 25 August to a three-agent agency with a Handler, mail triage,
chat logs, scheduled summaries, local voice notes and full change traceability on 8 November:
[docs/timeline.md](docs/timeline.md).

## About

Designed and built by **Karan Parekh**. I designed the agency, made the architecture and safety decisions,
built and directed the implementation, and run it every day. AI assisted development tools wrote parts of
the code, which is exactly why the traceability rules exist: every change, human or AI, says who made it
and why.

Licensed under MIT.
