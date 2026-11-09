# Timeline (2026)

| Date | Milestone |
|---|---|
| 25 Aug | First agent live in a WhatsApp group: document review against a fixed rubric. The same day, a cheaper conversational model was tried and reverted, and group access was redesigned. |
| 27 Aug | After a 10-hour silent outage, autostart was split into two scheduled tasks that repair each other, and idle sleep was disabled. |
| 28 Aug | Intake and a feedback loop; reviews delivered as PDFs because people read them on their phones; first security hardening pass. |
| 1 Sep | Cold-reboot recovery and multi-day unattended operation verified. |
| 21 Sep | The Operations agent's twice-daily scheduled runs built. |
| 22 Sep | Moved from the development laptop to an always-on desktop; nightly snapshots and a change log. |
| 23 Sep | One git repository for all agents and the pull-based deploy bot; the Handler goes live, completing the three-agent agency; rolling conversation memory for every agent. |
| 24 Sep | Relay guardrails between agents; mail and calendar through a bridge with no send function; agents moved toward walled Linux users. |
| 3 Oct | Full offline regression suite run on every deploy; the Assistant posts pictures, each checked by a model first. |
| 8 Oct | Browser windows open on demand and close when idle. |
| 9 Oct | Offline alert after WhatsApp outages. |
| 13 Oct | Timesheet automation with Outlook drafts; an isolated, signed-out reader for the Assistant; development moved to the desktop itself; traceability and per-author access control for every change. |
| 20 Oct | An audit found 69 stale lines in the agents' instructions; retired wording now fails a deploy. A full Windows disk took the agents down for 7 hours while the health check said "ok"; host checks went into the lessons every coding agent reads. |
| 22 Oct | A context pack every coding agent reads first (rules, architecture, a generated map and progress log, lessons) and a daily context watch; phone watch for texts, missed calls and voicemails. |
| 26 to 27 Oct | Mail watch every 2 minutes: one-time codes recognised and never kept, a verdict for every email, a plain-text mail log the summaries read instead of the mailbox. |
| 30 Oct | Chat logs of every group, both ways, with media, within seconds of each message. |
| 3 to 4 Nov | Scheduled mail summaries and usage reports in the Handler group, timed clear of the Operations agent's runs; a silent slot writes why. |
| 5 Nov | The mail log keeps the whole text of each important email, each reader sets its own limit, and mail cannot be lost silently; nightly behaviour evals only for an agent whose instructions changed. |
| 8 Nov | The Assistant's voice notes transcribed locally (SenseVoice, with Whisper as the fallback) and pictures from a web image search, two or three per request; a gateway upgrade reviewed and postponed until it can be rehearsed on a copy. |
