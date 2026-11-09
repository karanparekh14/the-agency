#!/usr/bin/env python3
"""Run every offline test suite, one line each, with a real exit code.

    python -m agency.gate.run_tests        all suites, a line each
    python -m agency.gate.run_tests -v     every suite's own output too

Suites are found, not listed: every tests/test_*.py. Each runs in its own process with a timeout,
so one hanging suite cannot stall the deploy. All suites are offline: throwaway folders, no
WhatsApp, no mailbox, no model calls.

The gate trusts the exit code only. In the production system a failing commit once got through
because a test run was piped through `tail`, which hid the failure; never parse output to decide.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TIMEOUT = 180                                                   # seconds per suite


def suites(root: Path = ROOT) -> list:
    return [(p.stem[5:], [sys.executable, "-m", "unittest", "-q", f"tests.{p.stem}"])
            for p in sorted((root / "tests").glob("test_*.py"))]


def failures(text: str) -> list:
    """Names of failed checks in a unittest run's output."""
    return [n.strip() for n in re.findall(r"^(?:FAIL|ERROR): (\S+)", text, re.M)][:6]


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    verbose = "-v" in argv
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    bad, t0 = [], time.time()
    for name, cmd in suites():
        t = time.time()
        try:
            r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=TIMEOUT)
            out, code = (r.stdout or "") + (r.stderr or ""), r.returncode
        except subprocess.TimeoutExpired:
            out, code = f"FAIL: timed out after {TIMEOUT}s", 1
        if verbose:
            print(out)
        names = failures(out)
        if code:
            bad.append(f"{name}: " + ("; ".join(names) or f"exit {code}"))
        print(f"{'ok  ' if not code else 'FAIL'} {name} ({time.time() - t:.1f}s)" + (f": {'; '.join(names)}" if code and names else ""))
    print(f"\n{len(bad)} suite(s) failed" if bad else "\nall suites passed", f"in {time.time() - t0:.1f}s")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
