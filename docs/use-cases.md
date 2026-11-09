# Use cases

The same few patterns (code first, a model only for judgement, visible commands, drafts a person sends,
plain-text logs) cover very different work. Here is what they do today, and, clearly marked, what they
could do next.

## A small business team: the Operations agent

**The work before the agent**

| Task | What it involves | Why it hurts |
|---|---|---|
| A recurring report | Gather the day's items from several sources, drop duplicates and the ones that can never work, decide which matter | Repetitive, and the same item appears many times |
| Weekly timesheets | Find each person's timesheet in email, file it, update the workbook, chase missing weeks | Weekly, deadline-driven, and unforgiving of gaps |
| Keeping track | Know what was sent, what is overdue, and whether the system itself is healthy | Nobody owns it, so it slips |

**A day with the Operations agent**

The team already coordinates in a WhatsApp group, so the Operations agent joined that group. Nobody had to learn a new
tool.

- **10:30 and 15:00 CT.** A scheduled run gathers, de-duplicates, filters and scores in plain code. Only
  the short list goes to a model, which gives a reason for every verdict. The team gets one report by
  email and one short line in the group, not a wall of links.
- **Timesheets.** Weekly timesheets are found in Outlook, filed under a consistent name, and checked
  against the team's workbook. Missing weeks get a polite reminder saved as an Outlook draft, which a
  person reviews and sends. A nightly check and a weekly summary go to the group. This pipeline uses no
  model at all.
- **Monday scorecard** and a log of everything the Operations agent sent.

**Guardrails that matter to the business**

- **No mail to a person without a human.** Reminders are saved as drafts; a person reviews them and
  presses Send. The Operations agent's own report leaves through a bridge that can send only that report.
- **Personal topics stay out of work.** Relays between agents happen only on an explicit request, and a
  topic guard keeps personal subjects out.
- **Every change is traceable.** Who changed what, and why, is recorded for code and for everything
  outside code.

### What's next (not built)

None of the following exists yet. Each is a natural next step that the patterns above already support,
listed here so it is clear what the system does today and what it could do:

- **Invoice and payment follow-up.** Match incoming payments against open invoices in code, and draft a
  polite reminder for anything overdue, for a person to send.
- **Expense receipts from the group.** A photo of a receipt in the group becomes a row in a spreadsheet:
  amount, date and vendor read by a model, totals and duplicates checked by code.
- **Contract and renewal dates.** A plain-code calendar of end dates and notice periods, with a reminder
  in the group a fixed number of weeks before each one.
- **Meeting notes.** A voice note after a meeting, transcribed locally the way the Assistant already does, turned
  into a short summary with action items posted to the group.
- **A weekly operations digest.** One message on Monday: what was sent, what is overdue, what the team
  asked for and what is still open, built from the logs that already exist.
- **Shared-inbox triage for the team.** The Handler's mail triage, pointed at a team mailbox, with the same
  rules first, a costed judge and a log every agent can read.

## A private conversation: the Assistant

Two people in a private chat get reminders, research, link reading through a signed-out browser that
cannot reach any mail service, checked pictures, voice notes transcribed on the desktop at no cost, and
answers from the chat's own record. What matters here is trust: the Assistant never logs in anywhere, its files
are behind its own Linux user, and nothing crosses to work.

## One person running all of it: the Handler

The owner gets one place to ask "how is everything?", one place to give orders, and one place where mail,
texts, missed calls, usage and health come together, without any of it being able to act on its own.

- **Mail without reading the mailbox.** Rules decide first, a model judges only the rest, a log keeps what
  matters, and summaries arrive at fixed times only when there is something new.
- **Phone and calendar in the same place.** Texts, missed calls and voicemails are posted to the Handler
  group; non-urgent posts wait during calls on the calendar.
- **Health and cost.** Health every 10 minutes, usage alerts at fixed thresholds, and a morning check of
  every change made to the system.

## Any team with a WhatsApp group

Nothing here is specific to one business. A team with a WhatsApp group, a repetitive workflow and a few
judgement calls a day can get its own field agent, run by the same Handler, behind the same walls.
