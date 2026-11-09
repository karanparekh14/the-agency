# The agents

Three agents, each with its own people, its own Linux user and its own wall, run by one Handler.

## The Operations agent

The Operations agent works inside a small business team's WhatsApp group.

- **Two scheduled runs a day (10:30 and 15:00 CT, cron).** Plain code gathers the day's items,
  de-duplicates them, drops the ones that can never work and scores the rest; a model judges only the
  short list. The team gets one report by email, sent from the Operations agent's own mailbox through a send-only bridge,
  and one short line in the group. Quiet windows around both runs: no deploys, no restarts.
- **Timesheets.** Files weekly timesheets from Outlook into each person's folder with a consistent name,
  checks them against the team's workbook (never while it is open in Excel), checks the dates inside the
  document when the subject and the file name disagree, drafts reminders for missing weeks in Outlook for
  a person to review and send, and posts a nightly check and a weekly summary. Zero model tokens.
- **Commands from the group.** The Operations agent uses the same pattern as the Handler: the model writes a visible
  command line, and code runs it and posts the result.
- **Reliability.** A Monday scorecard, a log of everything it sent, an offline alert after a WhatsApp
  outage, nightly snapshots, and its own copy of its group's chat log.

Ideas for what the Operations agent could take on next are in [use-cases.md](use-cases.md#whats-next-not-built), marked
as not built.

## The Assistant

The Assistant is a personal assistant in a private two-person chat, walled off from everything else.

- **Reminders**, with a guard that removes a false "no reminder scheduled" warning only when one really
  was set.
- **Research and link reading** through an isolated, signed-out browser that is read-only, closes itself,
  and cannot reach any mail service at all.
- **Pictures** from a web image search with strict safe search, open-licence libraries as the fallback: two or three different ones per request, one per website, no repeats in
  a day, no watermarked stock sites, each checked by a small model before it is posted. Daily caps exist only
  to stop a runaway loop.
- **Voice notes** transcribed on the desktop itself, free: SenseVoice for every note, Whisper only if that
  fails, and a one-line command to re-read the last note in a named language.
- **Answers from the record**: it searches its own chat history in plain code, so it quotes what was
  actually said rather than relying on a model's memory.
- **Tone controls** agreed with both people in the chat.
- Its own walled Linux user and allow-list, so neither the Operations agent nor the Handler can read its files, and a topic
  guard that keeps personal subjects from crossing to the other agents.

## The Handler

The Handler is the agency's control point: the one agent I talk to in order to run the other two. Full design
and reasoning: [vision.md](vision.md).

- **Command from a phone**: status, health, and relays to the Operations agent or the Assistant, only when explicitly asked.
- **Acts only through command lines.** The Handler is read-only. To do anything it writes a visible `🔧` line in
  its reply, and a separate dispatcher runs it only if the triggering message came from my own number.
  Code posts the result straight to the group; the model never retells a code result. Reference
  implementation: [`agency/dispatch/commands.py`](../agency/dispatch/commands.py).
- **Mail triage every 2 minutes** (hourly overnight). Plain rules first: a one-time code is recognised and its text never
  kept, a reply in a thread I wrote in is important, known noise is noise. A model judges only the rest.
  Everything lands in a plain-text mail log (whole text for what matters, the first 500 characters of
  noise, long numbers masked to the last four digits), so every agent reads the log instead of the
  mailbox. Reference: [`agency/inbox/triage.py`](../agency/inbox/triage.py).
- **Scheduled summaries.** Mail summaries at fixed times of day, timed clear of the Operations agent's runs, covering
  only what is new since the last one. A quiet slot posts nothing, and the log says why.
- **Usage reports.** A morning report of tokens used, plus an alert when the week's usage crosses 25, 50,
  75, 90 and 100 percent, or a 5-hour window crosses 80 percent.
- **Mail and calendar** through a Google Apps Script bridge that can read, draft and manage the calendar
  but has no send function, by design.
- **Phone watch.** An automation app on my phone posts texts, missed calls and voicemails to a bridge
  through a token that can only add alerts. The Handler posts them, and holds non-urgent posts during calls on my
  calendar.
- **Chat logs.** Every message of every group, both ways, with its media, is written to plain files
  within seconds of being sent; each agent reads only its own group's copy.
- **Health monitoring every 10 minutes** (gateway, channels, scheduled jobs, deploys, browser windows)
  with alerts and per-agent token usage.
- **Context watch.** Every morning it reads the new commits and the live system and tells me only about a
  change another agent made or a record that was not kept.
