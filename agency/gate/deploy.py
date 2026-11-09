"""A pull-based deploy gate, reduced to its decisions.

In production a timer on the always-on machine runs this every 5 minutes: fetch main into a clone
nobody edits, then:

  1. quiet window   never deploy while a scheduled business run is in progress
  2. checks         secret and personal-data scan, every Python file compiles, the offline test suite
  3. drift guard    refuse if a live file was edited outside git (see drift.py)
  4. copy           copy changed files live, keeping a dated backup of each file replaced
  5. manifest       record what is now live, for the next drift check

Each check is a callable returning (ok, detail), so the gate can be tested without a real machine.
Reporting (a commit status to GitHub, an alert on WhatsApp on failure) and removing files that were
deleted from the repo are left to the caller, to keep the reference small.
"""
from __future__ import annotations

import datetime as dt
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from . import drift as drift_mod


@dataclass
class Report:
    ok: bool
    stage: str                       # where it stopped, or "deployed" / "nothing to deploy"
    detail: str = ""
    copied: list = field(default_factory=list)
    backups: list = field(default_factory=list)


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def in_quiet_window(now: dt.datetime, windows) -> bool:
    """windows: [("10:15", "11:30"), ...] in the machine's local time; a window may cross midnight."""
    t = now.hour * 60 + now.minute
    for start, end in windows:
        a, b = _minutes(start), _minutes(end)
        if (a <= t < b) if a <= b else (t >= a or t < b):
            return True
    return False


def compile_check(src: Path, files) -> tuple:
    errors = []
    for f in files:
        if f.endswith(".py"):
            try:                                   # compile in memory: no .pyc files left in the clone
                compile((src / f).read_text(encoding="utf-8"), f, "exec")
            except SyntaxError as e:
                errors.append(f"{f}:{e.lineno}: {e.msg}")
    return (not errors, "; ".join(errors) or "all files compile")


def changed_files(src: Path, live: Path, files) -> list:
    return [f for f in files if not (live / f).is_file() or drift_mod.sha256(src / f) != drift_mod.sha256(live / f)]


def deploy(src: Path, live: Path, files, manifest: Path, *, now: dt.datetime = None,
           quiet_windows=(), checks=()) -> Report:
    """Deploy `files` (paths relative to src) from the clean clone `src` to `live`."""
    now = now or dt.datetime.now()
    if in_quiet_window(now, quiet_windows):
        return Report(False, "quiet window", f"{now:%H:%M} is inside a scheduled run window; will retry")
    for name, check in [("compile", lambda: compile_check(src, files)), *checks]:
        ok, detail = check()
        if not ok:
            return Report(False, name, detail)
    # A live file that already matches the new commit is not drift: it is a deploy that copied it and
    # then stopped before writing the manifest. Let the run finish instead of blocking itself.
    drifted = [d for d in drift_mod.drift(live, manifest)
               if not (d.startswith("changed: ") and (src / d[9:]).is_file()
                       and drift_mod.sha256(src / d[9:]) == drift_mod.sha256(live / d[9:]))]
    if drifted:
        return Report(False, "drift", "edited outside git, commit or revert first: " + ", ".join(drifted))
    todo = changed_files(src, live, files)
    if not todo:
        drift_mod.write_manifest(live, manifest, files)
        return Report(True, "nothing to deploy")
    stamp = now.strftime("%Y%m%d-%H%M%S")
    backups = []
    for f in todo:
        dst = live / f
        if dst.exists():
            b = live / ".backups" / stamp / f
            b.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, b)
            backups.append(b.relative_to(live).as_posix())
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / f, dst)
    drift_mod.write_manifest(live, manifest, files)
    return Report(True, "deployed", f"{len(todo)} file(s)", copied=todo, backups=backups)
