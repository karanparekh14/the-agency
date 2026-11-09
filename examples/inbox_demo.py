#!/usr/bin/env python3
"""Inbox triage at work: eight fictional emails, rules first, a judge only where needed, offline.

    python3 examples/inbox_demo.py

Watch three things: how few emails reach the judge (and what they cost), that the sign-in code leaves
no text behind, and that the card number in the log keeps only its last four digits.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agency.inbox.cost import Ledger                                   # noqa: E402
from agency.inbox.triage import CODE, KeywordJudge, Mail, Triage, summary  # noqa: E402

PRICES = {"judge-model": (1.0, 5.0)}     # illustrative dollars per million input and output tokens


def main():
    data = json.loads((Path(__file__).parent / "sample_inbox.json").read_text())
    ledger = Ledger(PRICES)
    triage = Triage(owner_threads=set(data["owner_threads"]), noise_senders=tuple(data["noise_senders"]),
                    judge=KeywordJudge(), ledger=ledger)
    decisions = triage.run([Mail(**m) for m in data["mail"]])

    print("Triage\n------")
    for d in decisions:
        kept = "nothing" if d.verdict == CODE else f"{len(d.kept)} chars"
        print(f"{d.verdict:<9} by {d.by:<5}  {d.mail.subject[:38]:<38}  keeps {kept:<9}  ({d.why})")

    judged = sum(d.by == "judge" for d in decisions)
    print(f"\n{len(decisions) - judged} of {len(decisions)} decided by plain rules; {judged} judged, "
          f"cost ${ledger.total_usd():.6f}")
    card = next(d for d in decisions if d.mail.id == "m4")
    print(f"Card line as logged: {card.kept[:60]}")

    text, why = summary(decisions, "8:00 AM")
    print(f"\nSummary ({why})\n-------\n{text}")
    quiet, why = summary([d for d in decisions if d.mail.id in ("m3", "m5")], "noon")
    print(f"\nA quiet hour: posted {'nothing' if not quiet else quiet}; the log says: {why}")


if __name__ == "__main__":
    main()
