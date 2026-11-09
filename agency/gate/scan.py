#!/usr/bin/env python3
"""Refuse to commit secrets or personal data. Runs as a pre-commit hook and again before every deploy.

    python -m agency.gate.scan [path ...]          default: every tracked or new file in the repo
    python -m agency.gate.scan --staged path ...   the staged (about to be committed) copy of each path

Two classes of finding:

  BLOCK   API keys, tokens, private keys, app passwords, webhook URLs, links to private AI chat
          sessions, and any term from a private denylist. Never allowed.
  REVIEW  email addresses, phone numbers, WhatsApp ids. Allowed only when the value is an obvious
          placeholder (example.com, .test, 555-01xx numbers, all-zero ids) or is listed in
          scan-allow.txt at the repo root (one value per line, or `file:<path>` for a reviewed file).

The denylist holds names that must never be published (people, companies, machines). It lives outside
the repo, because a list of private names is itself private: one term per line in the file named by
AGENCY_SCAN_DENYLIST, or by default in ~/.config/agency/denylist.txt. The scan says so when none is
loaded.

Matches are printed masked, never in full, so the scan output is itself safe to share.
Exit code 1 if anything blocks or is left to review.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

BLOCK = {
    "anthropic-key": r"sk-ant-[A-Za-z0-9_-]{10,}",
    "openai-key": r"\bsk-[A-Za-z0-9]{20,}",
    "github-token": r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})",
    "google-key": r"\bAIza[0-9A-Za-z_-]{30,}",
    "google-oauth-secret": r"GOCSPX-[A-Za-z0-9_-]{10,}",
    "aws-key": r"\bAKIA[0-9A-Z]{16}\b",
    "slack-token": r"\bxox[abprs]-[A-Za-z0-9-]{10,}",
    "private-key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "app-password": r"(?i)(?:app|pass|pwd)[^\n]{0,40}[\"'][a-z]{4} [a-z]{4} [a-z]{4} [a-z]{4}[\"']",
    "private-chat-link": r"(?:https?://)?(?:claude\.ai/(?:code/)?(?:session_|chat/|share/|project/|artifact/)"
                         r"|chatgpt\.com/(?:c|share|g)/)[\w-]+",
    "assigned-secret": r"(?i)\b(?:token|secret|password|passwd|api[_-]?key)\b[\"']?\s*[:=]\s*[\"'][A-Za-z0-9_\-+/=.]{16,}[\"']",
    "script-url": r"https://script\.google\.com/macros/s/[A-Za-z0-9_-]{20,}",
    "tailscale-key": r"tskey-[a-z]+-[A-Za-z0-9-]{10,}",
    "long-hex": r"\b[0-9a-f]{40,}\b",
}
REVIEW = {
    "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    # international (+44 20 7946 0123) and North American formats with or without +1:
    # 800-555-0142, (800) 555-0142, 800.555.0142, 8005550142
    "phone": r"(?<![\w.+])(?:\+\d[\d .()-]{8,17}\d|\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4})(?!\w)",
    "whatsapp-id": r"\b\d{10,20}(?:-\d+)?@(?:g\.us|s\.whatsapp\.net|lid)\b",
}
PLACEHOLDER = re.compile(
    r"@(?:[\w.-]+\.)?example\.(?:com|org|net)$"   # reserved example domains
    r"|\.(?:test|example|invalid|localhost)$"      # reserved TLDs
    r"|@users\.noreply\.github\.com$"
    r"|^noreply@anthropic\.com$"
    r"|555[ .-]?01\d\d$"                           # North American fictional range 555-0100 to 0199
    r"|20[ .-]?7946[ .-]?0\d{3}$"                  # UK drama range 020 7946 0000 to 0999
    r"|^\d*?0{8,}(?:-\d+)?@"                       # all-zero WhatsApp ids
    , re.I)
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".ico", ".woff", ".woff2"}


@dataclass(frozen=True)
class Finding:
    level: str      # BLOCK or REVIEW
    kind: str
    path: str
    line: int
    masked: str

    def __str__(self) -> str:
        return f"{self.level:6} {self.kind:20} {self.path}:{self.line}  {self.masked}"


def mask(value: str) -> str:
    return value[:3] + "***" + value[-2:] if len(value) > 8 else "***"


def is_placeholder(value: str) -> bool:
    return bool(PLACEHOLDER.search(value.strip()))


DEFAULT_DENYLIST = Path.home() / ".config" / "agency" / "denylist.txt"


def load_denylist(path: str = None) -> tuple:
    """Terms from AGENCY_SCAN_DENYLIST, else from ~/.config/agency/denylist.txt, else none."""
    path = path if path is not None else (os.environ.get("AGENCY_SCAN_DENYLIST") or str(DEFAULT_DENYLIST))
    if not path or not Path(path).is_file():
        return ()
    return tuple(_spaced(t) for t in Path(path).read_text(encoding="utf-8").splitlines()
                 if t.strip() and not t.lstrip().startswith("#"))


def _spaced(text: str) -> str:
    """Lower case, Unicode-normalised, every run of spaces, hyphens or underscores as one space."""
    return re.sub(r"[\s_\-]+", " ", unicodedata.normalize("NFKC", text).lower()).strip()


def _squashed(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKC", text).lower())


def denied(line: str, deny: tuple) -> list:
    """Denylisted terms in a line: as whole words, and for longer terms also with the spaces and
    punctuation squeezed out, so "AcmeWidgets" and "Acme-Widgets" match "acme widgets"."""
    hits, spaced, squashed = [], _spaced(line), _squashed(line)
    for term in deny:
        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", spaced):
            hits.append(term)
        elif len(_squashed(term)) >= 6 and _squashed(term) in squashed:
            hits.append(term)
    return hits


def scan_text(text: str, path: str = "<text>", allow: frozenset = frozenset(), deny: tuple = None) -> list:
    """Every finding in one file's text. `allow` holds reviewed values and `file:<path>` entries;
    `deny` defaults to the terms in the file named by AGENCY_SCAN_DENYLIST."""
    out = []
    deny = load_denylist() if deny is None else deny
    file_ok = f"file:{path}" in allow
    for n, line in enumerate(text.splitlines(), 1):
        for term in denied(line, deny):
            out.append(Finding("BLOCK", "denylisted", path, n, mask(term)))
        for kind, pat in BLOCK.items():
            for m in re.finditer(pat, line):
                out.append(Finding("BLOCK", kind, path, n, mask(m.group(0))))
        for kind, pat in REVIEW.items():
            for m in re.finditer(pat, line):
                v = m.group(0)
                if file_ok or is_placeholder(v) or v in allow or v.replace(" ", "") in allow:
                    continue
                out.append(Finding("REVIEW", kind, path, n, mask(v)))
    return out


def repo_files(root: Path) -> list:
    r = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=root, capture_output=True, text=True)
    if r.returncode != 0:                                  # not a git repo: walk the folder instead
        return [p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]
    return [root / f for f in r.stdout.splitlines() if f]


def load_allow(root: Path) -> frozenset:
    f = root / "scan-allow.txt"
    if not f.exists():
        return frozenset()
    return frozenset(l.strip() for l in f.read_text(encoding="utf-8").splitlines()
                     if l.strip() and not l.lstrip().startswith("#"))


def scan_paths(paths, root: Path) -> list:
    allow = load_allow(root)
    out = []
    for p in paths:
        p = Path(p)
        if not p.is_file() or p.suffix.lower() in SKIP_SUFFIXES:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        try:
            rel = p.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            rel = p.as_posix()
        out += scan_text(text, rel, allow)
    return out


def scan_staged(paths, root: Path) -> list:
    """Scan what is staged for commit, not the working copy: a secret that was staged and then
    edited out of the file on disk would otherwise slip through."""
    allow = load_allow(root)
    out = []
    for rel in paths:
        if Path(rel).suffix.lower() in SKIP_SUFFIXES:
            continue
        r = subprocess.run(["git", "show", f":{rel}"], cwd=root, capture_output=True)
        if r.returncode != 0:
            continue
        try:
            text = r.stdout.decode("utf-8")
        except UnicodeDecodeError:
            continue
        out += scan_text(text, Path(rel).as_posix(), allow)
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = Path.cwd()
    if argv[:1] == ["--staged"]:
        paths = argv[1:]
        findings = scan_staged(paths, root)
    else:
        paths = [Path(a) for a in argv] if argv else repo_files(root)
        findings = scan_paths(paths, root)
    for f in findings:
        print(f)
    if not load_denylist():
        print(f"note: no private denylist loaded (set AGENCY_SCAN_DENYLIST or create {DEFAULT_DENYLIST})",
              file=sys.stderr)
    blocking = sum(f.level == "BLOCK" for f in findings)
    review = len(findings) - blocking
    print(f"\nscan: {blocking} blocking, {review} to review, {len(paths)} file(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
