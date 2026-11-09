"""Inbox triage: how the Handler reads a mailbox without reading it all, and without forgetting.

The production version watches the owner's mailbox every two minutes and writes a plain-text log that
every agent reads instead of the mailbox itself. The rules below are the same ideas, rewritten fresh:

  1. Plain rules decide first, for free:
       a one-time code is CODE and its text is never stored;
       a reply in a thread the owner wrote in is IMPORTANT;
       a known noise sender, or a promotions or social tab without any work signal, is NOISE.
  2. Only what the rules cannot decide goes to a model judge, and every call is costed in a ledger.
  3. A missing or unclear answer from the judge is never turned into a guess. The mail stays PENDING
     and is judged again on the next run (a missing answer once fell back to the risky choice).
  4. The log keeps the whole text of IMPORTANT and FYI mail (up to a limit), the first 500 characters
     of NOISE (enough to catch a misjudged email later), and nothing at all of a code. Long numbers
     (cards, accounts, loans) are masked to their last four digits before anything is written.
  5. A summary posts only when there is something new to say, and when it stays silent, the log says
     why: a silent job and a broken job look the same from the outside.

The judge is an interface. `KeywordJudge` is a deterministic offline stand-in with the same shape,
so the tests and the demo run without a model or a network.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from agency.inbox.cost import Ledger

IMPORTANT, FYI, NOISE, CODE, PENDING = "IMPORTANT", "FYI", "NOISE", "CODE", "PENDING"
KEEP_FULL = 20_000            # characters of IMPORTANT and FYI text kept in the log
KEEP_NOISE = 500              # characters of NOISE kept, for a later search after a misjudged email
CODE_RE = re.compile(r"\b(verification|security|one[- ]time|login|sign[- ]in)\s+code\b|\bOTP\b", re.I)
CODE_DIGITS = re.compile(r"(?<!\d)\d{4,8}(?!\d)")
LONG_NUMBER = re.compile(r"(?<![\w])(?:\d[ -]?){8,}\d(?![\w])")
WORK_SIGNAL = re.compile(r"\b(interview|invoice|deadline|due|contract|meeting|call|offer|schedule)\b", re.I)


@dataclass(frozen=True)
class Mail:
    id: str
    thread: str
    sender: str
    subject: str
    body: str
    tab: str = "primary"            # primary, promotions, social, updates


@dataclass
class Decision:
    mail: Mail
    verdict: str
    why: str
    by: str                         # "rule" or "judge"
    kept: str = ""                  # the text the log keeps, already masked and cut


def mask_numbers(text: str) -> str:
    """Card, account and loan numbers keep only their last four digits."""
    def last4(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        return "X" * (len(digits) - 4) + digits[-4:]
    return LONG_NUMBER.sub(last4, text)


def is_code(mail: Mail) -> bool:
    text = f"{mail.subject} {mail.body[:400]}"
    return bool(CODE_RE.search(text) and CODE_DIGITS.search(text))


@dataclass
class Triage:
    owner_threads: set = field(default_factory=set)     # threads the owner has written in
    noise_senders: tuple = ()                           # lower-case substrings of sender addresses
    judge: Optional[Callable[[Mail], tuple]] = None     # mail -> (verdict, why, in_tokens, out_tokens)
    ledger: Optional[Ledger] = None
    model: str = "judge-model"

    def rule(self, mail: Mail) -> Optional[tuple]:
        """(verdict, why) when a plain rule decides, else None."""
        if is_code(mail):
            return CODE, "one-time code: its text is never stored"
        if mail.thread in self.owner_threads:
            return IMPORTANT, "a reply in a thread the owner wrote in"
        sender = mail.sender.lower()
        if any(s in sender for s in self.noise_senders):
            return NOISE, "known noise sender"
        if mail.tab in ("promotions", "social") and not WORK_SIGNAL.search(f"{mail.subject} {mail.body[:600]}"):
            return NOISE, f"{mail.tab} tab with no work signal"
        return None

    def decide(self, mail: Mail) -> Decision:
        got = self.rule(mail)
        if got:
            return self._keep(Decision(mail, got[0], got[1], "rule"))
        if self.judge is None:
            return Decision(mail, PENDING, "no judge configured", "judge")
        try:
            verdict, why, tin, tout = self.judge(mail)
        except Exception as ex:                                  # noqa: BLE001  a failed call is not an answer
            return Decision(mail, PENDING, f"judge failed ({type(ex).__name__}); retried next run", "judge")
        if self.ledger is not None:
            self.ledger.add("triage", self.model, tin, tout, ref=mail.id)
        if verdict not in (IMPORTANT, FYI, NOISE):
            return Decision(mail, PENDING, "no clear verdict; retried next run", "judge")
        return self._keep(Decision(mail, verdict, why or "judged", "judge"))

    @staticmethod
    def _keep(d: Decision) -> Decision:
        if d.verdict == CODE:
            d.kept = ""
        elif d.verdict == NOISE:
            d.kept = mask_numbers(d.mail.body)[:KEEP_NOISE]
        else:
            d.kept = mask_numbers(d.mail.body)[:KEEP_FULL]
        return d

    def run(self, mails: list) -> list:
        return [self.decide(m) for m in mails]


def summary(decisions: list, since_label: str) -> tuple:
    """(text, why). Text is empty when nothing qualifies, and `why` then says so for the log."""
    worth = [d for d in decisions if d.verdict in (IMPORTANT, FYI)]
    pending = sum(d.verdict == PENDING for d in decisions)
    if not worth:
        why = f"silent: 0 of {len(decisions)} emails worth a summary since {since_label}"
        return "", why + (f"; {pending} still pending" if pending else "")
    lines = [f"Mail since {since_label}: {len(worth)} worth a look"]
    for d in sorted(worth, key=lambda d: d.verdict != IMPORTANT):
        mark = "!" if d.verdict == IMPORTANT else "-"
        lines.append(f"{mark} {d.mail.subject} ({d.why})")
    if pending:
        lines.append(f"{pending} not judged yet; they are retried next run")
    return "\n".join(lines), f"posted {len(worth)}"


class KeywordJudge:
    """Offline stand-in for the model judge: same interface, deterministic, no network."""

    def __init__(self, important=("interview", "deadline", "due", "overdue", "offer"), fyi=("receipt", "update", "statement")):
        self.important, self.fyi = important, fyi

    def __call__(self, mail: Mail) -> tuple:
        text = f"{mail.subject} {mail.body}".lower()
        tokens = len(text) // 4 + 60                              # a rough token count for the ledger
        if any(w in text for w in self.important):
            return IMPORTANT, "needs the owner", tokens, 20
        if any(w in text for w in self.fyi):
            return FYI, "worth knowing", tokens, 20
        return NOISE, "nothing to act on", tokens, 20
