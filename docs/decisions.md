# Design decisions and why

| Decision | Why |
|---|---|
| **Plain code first, a model only for judgement** | Cost and reliability. Filtering, scoring, filing, formatting, status and counts are deterministic; only short-list judging and free-text understanding need a model. Every pipeline reports its token cost. |
| **A model that ignores an instruction twice loses that decision to code** | Twice, a model copied its own earlier replies instead of the corrected instruction. Anything code can compute (status, counts, which list, whether to run) is now decided by code, and the model writes only the part that needs judgement. |
| **No model answer means do nothing** | A missing verdict once defaulted to the risky choice and sent a false reply to a group. Now a missing or unclear answer does nothing, says so, and is retried on the next run. |
| **A stronger model judges, a cheaper one assists** | In an A/B on the same 16 items, the cheaper model flipped 4 verdicts between runs and the stronger one 2, with better reasons. A cheaper conversational model was also tried early for the group agent and reverted the same day. |
| **One Handler for all agents** | Two agents with opposite lives (a team's business, a private chat) need one point of command and oversight, and no path between them that the owner did not open. |
| **Each agent in its own walled Linux user** | Isolation inside one shared account is not enough. Separate users with their own allow-lists keep one agent's files and context away from the others. |
| **The Handler acts only through visible, sender-checked command lines** | A model that reads outside text can be talked into things. The Handler cannot write files or call tools freely; a dispatcher runs a `🔧` line only if the triggering message came from the owner's own number, and holds relays and other side effects the owner did not explicitly ask for. |
| **Code posts results, the model never retells them** | A model retelling a result can change a number. Results go to the group from the code that computed them. |
| **A mail bridge with no send function** | Ordinary mail credentials can always send. A small Apps Script bridge can read and draft but has no send function at all, so no prompt can make the Handler send mail. |
| **Mail read from a log, not the mailbox** | Every agent reading the mailbox costs tokens and API calls and gives different answers. One watcher triages each email once and writes a plain-text log; agents read the log and go to the mailbox only for attachments, links or very old mail. |
| **One-time codes are never kept, long numbers are masked** | A log is read by several agents and backed up. A code is recognised and its text is not stored; card, account and loan numbers keep only their last four digits. |
| **Outbound mail to people is a draft a human sends** | Reminders go out under a person's name, so a person checks them and presses Send. |
| **A job that stays silent writes why** | People asked three times why a summary had not come; every slot had run and nothing qualified. A silent job and a broken job look the same unless the log says which. |
| **Pull-based deploy from one repo, never edit live** | The desktop pulls, tests and deploys. A live edit is treated as drift and blocks the deploy until it is committed, so the repository is always the truth. |
| **Tests before every deploy, judged by exit codes** | A failing commit once got through because a test run was piped through `tail`; the runner and the bot now rely on exit codes only. |
| **Instructions are tested like code** | An audit found 69 stale lines in instruction files (wrong times, retired commands). Old wording now goes on a retired-facts list, and a test fails the deploy if an instruction file repeats it. |
| **Traceability for every change, by anyone** | Several AI sessions and, later, the agents themselves change the system. Every commit names its author and reason, file access is opened per agent and slowly, and changes outside git are logged too. |
| **Visible browsers on the user's desktop, opened on demand** | Outlook and the sites the agents use need a real Windows desktop session. Windows open through interactive scheduled tasks and close after 10 idle minutes to save memory. |
| **An isolated, signed-out reader for the Assistant** | Link reading never touches a signed-in account, and mail services are unreachable from that browser. |
| **Speech runs locally** | Voice notes never leave the desktop and cost no tokens. A free local model handles most languages; a second local model is the fallback. |
| **Quiet windows around scheduled runs** | Deploys and restarts never collide with the daily business runs. |
| **Rolling memory instead of endless sessions** | Long chats grow towards the model's context limit and sessions get cut; a 7-day block and a weekly journal keep what matters. |
| **Gateway upgrades are rehearsed, not tried** | A gateway upgrade migrates its databases one way, and reinstalling the old version does not undo it. An upgrade waits for a full cold backup and a rehearsal on a copy. |
