#!/usr/bin/env python3
"""Every change says who made it and why, and stays inside what that author may touch.

Several authors change the production system: the owner, AI coding assistants, and the agents
themselves. From the commit that adds PROJECT/ACCESS.json onward, every commit must end with two
trailers in its last paragraph:

    Agent: <id from ACCESS.json>    who made the change (a person, a coding assistant, an agent)
    Why: <reason>                   why, ideally whose request it was

and may only touch files allowed by that author's "paths". "protected" paths (the rules, the gate
itself, the hooks, CI) are never open to the system's own agents, and need an "Approved-by: <owner>"
trailer from any non-human author.

    python -m agency.gate.trace --msg <file>    commit-msg hook: the message being written + staged files
    python -m agency.gate.trace --history       every commit since the rules began; run in CI and by the
                                                deploy gate, so skipping the hook cannot reach production

Each historical commit is judged by the rules as they were in its parent, so no commit can widen its
own access. Commit messages, author and committer fields are checked too, because they are published
with the code: no secrets, private links, contact details or denylisted names, and no-reply emails only.

What this is and is not: trailers are written by the author, so this is an audit trail and a guard
against honest mistakes and drifting AI sessions, not protection against someone who forges a
trailer. For that, pair it with signed commits and a protected branch that requires review.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

try:
    from . import scan
except ImportError:                                    # run as a plain script
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from agency.gate import scan

ACCESS = "PROJECT/ACCESS.json"
HOW = ("Add two lines at the end of the commit message, for example\n"
       "    Agent: claude-code\n    Why: owner asked for <...>\n"
       f"Author ids are in {ACCESS}.")


def git(root, *args) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout


def trailers(msg: str) -> dict:
    """Last value of each `Key: value` line in the message's final paragraph, keys lower-cased."""
    out = {}
    for line in msg.strip().split("\n\n")[-1].splitlines():
        m = re.match(r"^([A-Za-z][A-Za-z-]*):\s*(.+)$", line.strip())
        if m:
            out[m.group(1).lower()] = m.group(2).strip()
    return out


def _glob_rx(glob: str) -> str:
    """A path glob where `*` stays inside one folder and `**` crosses folders."""
    out, i = "", 0
    while i < len(glob):
        if glob.startswith("**", i):
            out += ".*"
            i += 2
        elif glob[i] == "*":
            out += "[^/]*"
            i += 1
        elif glob[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(glob[i])
            i += 1
    return out


def allowed(path: str, globs) -> bool:
    return any(re.fullmatch(_glob_rx(g), path) for g in globs)


def check(msg: str, files, rules: dict) -> list:
    """Problems with one change; an empty list means it is fine."""
    t = trailers(msg)
    agent = t["agent"].split()[0].lower() if t.get("agent") else ""
    if not agent:
        return ["no 'Agent:' line"]
    who = rules["agents"].get(agent)
    if who is None:
        return [f"unknown author '{agent}' (not in {ACCESS})"]
    probs = [] if t.get("why") else ["no 'Why:' line"]
    owner = (rules.get("owner") or "owner").lower()     # never empty: "" would approve everything
    for f in files:
        if allowed(f, rules.get("protected", [])):
            if who["kind"] == "own-agent":
                probs.append(f"{agent} may never change protected file {f}")
            elif who["kind"] != "human" and (t.get("approved-by") or "").split(" ")[0].lower() != owner:
                probs.append(f"{f} is protected: needs 'Approved-by: {owner}'")
        elif not allowed(f, who.get("paths", [])):
            probs.append(f"{agent} is not allowed to change {f}")
    return probs


SAFE_EMAILS = re.compile(r"@users\.noreply\.github\.com$|^noreply@github\.com$|^noreply@anthropic\.com$", re.I)


def message_problems(msg: str) -> list:
    """Secrets, private links, contact details or denylisted terms in a commit message: messages are
    published with the code."""
    return [f"commit message: {f.kind} {f.masked}"
            for f in scan.scan_text(msg, "<commit message>", scan.load_allow(Path.cwd()))]


def identity_problems(name: str, email: str, role: str = "author") -> list:
    """Author and committer fields are public too: a no-reply email, and no denylisted name."""
    probs = []
    e = email.strip()
    if not (SAFE_EMAILS.search(e) or scan.is_placeholder(e) or e in scan.load_allow(Path.cwd())):
        probs.append(f"{role} email {scan.mask(email)} is not a no-reply address")
    if scan.denied(name, scan.load_denylist()):
        probs.append(f"{role} name {scan.mask(name)} is denylisted")
    return probs


def _ident(var: str) -> tuple:
    """(name, email) from `git var GIT_AUTHOR_IDENT` style output."""
    m = re.match(r"^(.*) <([^>]*)>", var.strip())
    return (m.group(1), m.group(2)) if m else ("", "")


def load_rules(text: str) -> dict:
    return json.loads(text)


def history(root) -> list:
    """(sha, subject, problems) for every failing non-merge commit since ACCESS.json was added."""
    first = git(root, "log", "--diff-filter=A", "--format=%H", "--", ACCESS).split()
    if not first:
        return [("-", "-", [f"{ACCESS} is not in the history"])]
    start = first[-1]
    has_parent = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "-q", f"{start}^"],
                                capture_output=True).returncode == 0
    # When the rules arrive in the very first commit (a fresh repo), there is no parent to range from.
    span = f"{start}^..HEAD" if has_parent else "HEAD"
    bad = []
    for sha in git(root, "rev-list", "--reverse", "--no-merges", span).split():
        msg = git(root, "log", "-1", "--format=%B", sha)
        files = [f for f in git(root, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", sha).splitlines() if f]
        try:
            rules = load_rules(git(root, "show", f"{sha}^:{ACCESS}"))
        except subprocess.CalledProcessError:      # the commit that introduces the rules is judged by them
            rules = load_rules(git(root, "show", f"{sha}:{ACCESS}"))
        an, ae, cn, ce = git(root, "log", "-1", "--format=%an%x00%ae%x00%cn%x00%ce", sha).strip().split("\x00")
        p = (check(msg, files, rules) + message_problems(msg)
             + identity_problems(an, ae, "author") + identity_problems(cn, ce, "committer"))
        if p:
            bad.append((sha[:7], msg.splitlines()[0][:70] if msg.strip() else "", p))
    return bad


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[argv.index("--repo") + 1]) if "--repo" in argv else Path.cwd()
    if "--msg" in argv:
        msg = Path(argv[argv.index("--msg") + 1]).read_text(encoding="utf-8")
        msg = "\n".join(l for l in msg.splitlines() if not l.startswith("#"))
        files = [f for f in git(root, "diff", "--cached", "--name-only").splitlines() if f]
        probs = check(msg, files, load_rules((root / ACCESS).read_text(encoding="utf-8"))) + message_problems(msg)
        for role, var in (("author", "GIT_AUTHOR_IDENT"), ("committer", "GIT_COMMITTER_IDENT")):
            probs += identity_problems(*_ident(git(root, "var", var)), role)
        if probs:
            print("Commit refused (traceability):\n  - " + "\n  - ".join(probs) + "\n" + HOW, file=sys.stderr)
            return 1
        return 0
    if "--history" in argv:
        bad = history(root)
        for sha, subj, p in bad:
            print(f"FAIL {sha} {subj}  -> {'; '.join(p)}")
        print(f"{'ok' if not bad else 'FAILED'}: traceability of every commit since the rules began")
        return 1 if bad else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
