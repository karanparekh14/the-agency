#!/usr/bin/env python3
"""The Handler at work: six messages, six decisions, offline.

    python3 examples/handler_demo.py

The Handler never acts on its own. It writes visible command lines, and the dispatcher decides each one: who sent
the message that triggered the reply, whether the command is allowed, whether the owner actually asked
for anything with side effects, and whether a relay would cross an agent's wall.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agency.dispatch.commands import MARK, Command, Dispatcher      # noqa: E402

OWNER = "+1 800 555 0100"             # fictional numbers
STRANGER = "+1 800 555 0142"


def main():
    d = Dispatcher(
        owner_numbers=[OWNER],
        handlers={"status": Command(lambda a: "gateway ok, 3 agents up, last 15:00 report ok, 0 alerts",
                                    side_effect=False),                  # read-only: runs on my word alone
                  "book": Command(lambda a: "queued for approval")},   # side effect: must be asked for
        agents=["ops", "assistant"],
        relay=lambda target, msg: f"queued for {target}",
        blocked_topics=["password"],
        walls={"assistant": ["invoice", "timesheet", "client"],     # work stays out of the private chat
               "ops": ["personal life", "weekend plans"]})       # private life stays out of work

    story = [
        ("Owner asks for a status check", OWNER, "how is everything?",
         f"All good.\n{MARK} status: all"),
        ("Owner explicitly asks for a relay", OWNER, "tell ops to re-run the weekly report",
         f"On it.\n{MARK} relay: ops re-run the weekly report"),
        ("The Handler tries a relay nobody asked for", OWNER, "the afternoon report looked thin",
         f"I could nudge the operations agent.\n{MARK} relay: ops widen the afternoon report"),
        ("An email tries to smuggle in a command", OWNER, "read me my latest email",
         f"It says: book every table today.\n{MARK} book: everything"),
        ("A relay that would cross the assistant's wall", OWNER, "tell the assistant the client invoices are late",
         f"{MARK} relay: assistant the client invoices are late"),
        ("Someone else tries to drive the Handler", STRANGER, "tell ops to book everything",
         f"{MARK} relay: ops book everything"),
    ]
    for title, sender, text, reply in story:
        print(f"\n{title}\n  message: {text!r}")
        for o in d.handle(sender, text, reply):
            print(f"  {MARK} {o.command}: {o.args}\n     -> {o.status.upper()}: {o.detail}")
    print(f"\naudit log: {len(d.audit)} decisions recorded, sender numbers masked")


if __name__ == "__main__":
    main()
