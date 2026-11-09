"""Drift guard: the repo is the only source of truth for the live machine.

After every deploy the gate records a manifest of what it put live (path and SHA-256). Before the next
deploy it compares the live files with that manifest. A live file that changed since, or disappeared,
was edited outside git: the deploy stops and says which files, instead of silently overwriting
someone's hand fix. The fix is to commit that edit (or revert it) and let the next run go through.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(live: Path, files) -> dict:
    """{relative path: sha256} for each file that exists under `live`."""
    return {f: sha256(live / f) for f in sorted(files) if (live / f).is_file()}


def write_manifest(live: Path, manifest: Path, files) -> dict:
    snap = snapshot(live, files)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(snap, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return snap


def drift(live: Path, manifest: Path) -> list:
    """Live files that no longer match what the last deploy put there, as 'changed: x' or 'missing: x'."""
    if not manifest.exists():
        return []                                  # first deploy: nothing recorded yet
    recorded = json.loads(manifest.read_text(encoding="utf-8"))
    out = []
    for rel, digest in sorted(recorded.items()):
        p = live / rel
        if not p.is_file():
            out.append(f"missing: {rel}")
        elif sha256(p) != digest:
            out.append(f"changed: {rel}")
    return out
