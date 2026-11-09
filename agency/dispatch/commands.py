"""Sender-verified command lines: how a read-only Handler agent is allowed to act.

The Handler reads outside text (mail, web pages, other people's messages), so it can be talked
into things. It therefore has no free tool access. To act, it writes a visible line in its reply:

    🔧 status: all
    🔧 relay: ops re-run the 15:00 report

A small dispatcher process, not the model, decides whether each line runs:

  1. the message that triggered the reply must come from the owner's own number;
  2. the command must be on the allowlist, each with its own handler;
  3. a command with side effects (every command unless declared read-only, and every relay) must be
     asked for in the owner's own words: a clause of the owner's message has to start with the ask
     ("tell ops ...", "please book ..."), so questions ("did you tell ops?"), negations
     ("don't tell ops") and mentions ("send me the ops report") are not asks;
  4. what the line would do must come from the owner's words too: at least half of the content words
     in its arguments must appear in the owner's message, and each ask authorises one action. A line
     that text the Handler read smuggled into its reply ("book: everything") is held;
  5. a command line that appears in content the Handler read this turn (pass it as `fetched`) is refused outright;
  6. a relay never carries a globally blocked topic and never crosses the target agent's wall.

Lines inside quotes (> ...) or code fences are skipped as a first, best-effort filter.

What this is and is not: rule 1 is exact. Rules 3 to 6 are keyword and text rules: they stop
accidents and casual injection, not a determined attacker who also controls the owner's wording.
Anything irreversible should additionally need an explicit confirmation step.

Every decision is logged, and because the line is in the reply, the owner sees exactly what ran.
"""
from __future__ import annotations

import datetime as dt
import re
import unicodedata
from dataclasses import dataclass
from typing import Callable

MARK = "\U0001F527"                                   # the wrench emoji
LINE = re.compile(rf"^[ \t]*{MARK}[ \t]*([a-z][a-z0-9_-]*)[ \t]*:[ \t]*(.*?)[ \t]*$")
RELAY_VERBS = ("tell", "ask", "relay", "pass", "forward", "send", "message", "remind")
POLITE = (("please",), ("pls",), ("kindly",), ("can", "you"), ("could", "you"), ("would", "you"),
          ("will", "you"), ("can", "u"))
FILLERS = {"this", "it", "that", "these", "on", "along", "over", "to"}
STOP = {"this", "that", "with", "from", "have", "what", "when", "will", "would", "could", "about",
        "their", "there", "them", "they", "your", "please", "just", "also", "then", "into", "some"}
CONFUSABLE = str.maketrans("аеорсхуіј",
                           "aeopcxyij")               # Cyrillic letters that look Latin


@dataclass(frozen=True)
class CommandLine:
    command: str
    args: str


@dataclass(frozen=True)
class Outcome:
    command: str
    args: str
    status: str          # ran | held | refused
    detail: str = ""


@dataclass(frozen=True)
class Command:
    """An allowed command. Commands have side effects unless declared read-only, so forgetting to
    classify one fails safe. Side-effect commands must be asked for with one of `ask_words` (default:
    the command's own name)."""
    fn: Callable
    side_effect: bool = True
    ask_words: tuple = ()


def digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def normal(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").lower().translate(CONFUSABLE)
    return text.replace("’", "'")


def words(text: str) -> list:
    return re.findall(r"[a-z0-9']+", normal(text))


def squash(text: str) -> str:
    """Letters and digits only, so "pass word" and "pass-word" still match "password"."""
    return re.sub(r"[^a-z0-9]", "", normal(text))


def content_words(text: str) -> set:
    return {w for w in words(text) if len(w) >= 4 and w not in STOP}


NEGATION_ONLY = {"don't", "dont", "do", "not", "never", "no", "please", "pls"}


def clauses(text: str) -> list:
    """(tokens, is_question) for each clause of a message. A bare negation such as "don't," carries over
    to the rest of its sentence ("don't, under any circumstances, tell ops")."""
    out = []
    for part, end in re.findall(r"([^.;!?\n]+)([.;!?\n]?)", normal(text)):
        negated = False
        for piece in re.split(r",|\b(?:and|then|but|also)\b", part):
            toks = re.findall(r"[a-z0-9']+", piece)
            if not toks:
                continue
            if set(toks) <= NEGATION_ONLY and set(toks) - {"please", "pls"}:
                negated = True
                continue
            if not negated:
                out.append((toks, end == "?"))
    return out


def _strip_polite(toks: list) -> tuple:
    """(tokens without a polite opener, whether one was there)."""
    for p in POLITE:
        if tuple(toks[:len(p)]) == p:
            return toks[len(p):], True
    return toks, False


def asks(text: str, verbs, target: str = None) -> int:
    """How many clauses of `text` are an imperative ask starting with one of `verbs` (and, for a relay,
    naming `target` right after the verb, allowing a few fillers: "pass this on to ops")."""
    verbs = {v.lower() for v in verbs}
    n = 0
    for toks, question in clauses(text):
        toks, polite = _strip_polite(toks)
        if not toks or toks[0] not in verbs or (question and not polite):
            continue
        if target is not None:
            rest = toks[1:]
            k = 0
            while k < len(rest) and k < 3 and rest[k] in FILLERS:
                k += 1
            if k >= len(rest) or rest[k] != target.lower():
                continue
        n += 1
    return n


def tied_to_owner(args: str, owner_text: str) -> bool:
    """At least half of the content words of what the line would do appear in the owner's message."""
    c = content_words(args)
    return not c or 2 * len(c & set(words(owner_text))) >= len(c)


def parse(reply: str) -> list:
    """Command lines in a reply, skipping quoted lines and fenced blocks (best effort)."""
    out, fence = [], None
    for line in (reply or "").splitlines():
        s = line.strip()
        if s.startswith("```") or s.startswith("~~~"):
            fence = None if fence and s.startswith(fence) else (fence or s[:3])
            continue
        if fence or s.startswith(">"):
            continue
        m = LINE.match(line)
        if m:
            out.append(CommandLine(m.group(1), m.group(2)))
    return out


class Dispatcher:
    def __init__(self, owner_numbers, handlers: dict, agents=(), relay: Callable = None,
                 blocked_topics=(), walls: dict = None, clock: Callable = dt.datetime.now):
        self.owners = {digits(n) for n in owner_numbers if digits(n)}
        self.handlers = dict(handlers)
        self.agents = {a.lower() for a in agents}
        self.relay = relay
        self.blocked = [squash(b) for b in blocked_topics]
        self.walls = {a.lower(): [squash(t) for t in ts] for a, ts in (walls or {}).items()}
        self.clock = clock
        self.audit = []

    def _log(self, sender: str, o: Outcome) -> Outcome:
        d = digits(sender)
        self.audit.append({"time": self.clock().isoformat(timespec="seconds"),
                           "sender": ("***" + d[-2:]) if d else "?",
                           "command": o.command, "status": o.status, "detail": o.detail})
        return o

    def handle(self, sender: str, trigger_text: str, reply: str, fetched=()) -> list:
        """Decide and run every command line in one agent reply. `fetched` is any outside text the agent
        read while producing the reply (an email body, a web page)."""
        lines = parse(reply)
        if not lines:
            return []
        if digits(sender) not in self.owners:
            return [self._log(sender, Outcome(l.command, l.args, "refused", "trigger did not come from the owner"))
                    for l in lines]
        outside = [squash(f) for f in fetched if f]
        used = {}                                      # asks already spent, per command or relay target
        out = []
        for l in lines:
            body = squash(l.args)
            if any(squash(f"{l.command}:{l.args}") in f or (len(body) >= 8 and body in f) for f in outside):
                o = Outcome(l.command, l.args, "refused", "this line appears in content the agent read")
            else:
                o = self._one(l, trigger_text, used)
            out.append(self._log(sender, o))
        return out

    @staticmethod
    def _spend(used: dict, key: str, available: int) -> bool:
        if used.get(key, 0) >= available:
            return False
        used[key] = used.get(key, 0) + 1
        return True

    def _one(self, line: CommandLine, owner_text: str, used: dict) -> Outcome:
        if line.command == "relay":
            return self._relay(line, owner_text, used)
        cmd = self.handlers.get(line.command)
        if cmd is None:
            return Outcome(line.command, line.args, "refused", "not an allowed command")
        if not isinstance(cmd, Command):
            cmd = Command(cmd)                         # unclassified: treated as having side effects
        if cmd.side_effect:
            n = asks(owner_text, cmd.ask_words or (line.command,))
            if not n:
                return Outcome(line.command, line.args, "held", "has side effects and the owner did not ask for it")
            if not tied_to_owner(line.args, owner_text):
                return Outcome(line.command, line.args, "held", "not what the owner asked for")
            if not self._spend(used, line.command, n):
                return Outcome(line.command, line.args, "held", "one action per ask")
        try:
            return Outcome(line.command, line.args, "ran", str(cmd.fn(line.args)))
        except Exception as e:                         # a failing handler must not kill the dispatcher
            return Outcome(line.command, line.args, "refused", f"handler error: {type(e).__name__}")

    def _relay(self, line: CommandLine, owner_text: str, used: dict) -> Outcome:
        target, _, message = line.args.partition(" ")
        target = target.lower()
        if self.relay is None:
            return Outcome("relay", line.args, "refused", "relays are not enabled")
        if target not in self.agents:
            return Outcome("relay", line.args, "refused", f"unknown agent '{target}'")
        if any(b and b in squash(message) for b in self.blocked):
            return Outcome("relay", line.args, "refused", "blocked topic")
        if any(t and t in squash(message) for t in self.walls.get(target, [])):
            return Outcome("relay", line.args, "refused", f"crosses {target}'s wall")
        n = asks(owner_text, RELAY_VERBS, target)
        if not n:
            return Outcome("relay", line.args, "held", "the owner did not explicitly ask for this relay")
        if not tied_to_owner(message, owner_text):
            return Outcome("relay", line.args, "held", "not what the owner asked to relay")
        if not self._spend(used, "relay:" + target, n):
            return Outcome("relay", line.args, "held", "one relay per ask")
        return Outcome("relay", line.args, "ran", str(self.relay(target, message.strip())))
