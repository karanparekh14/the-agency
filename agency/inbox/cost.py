"""Cost is a requirement, so every model call is recorded and priced per action.

Rates are configuration, in US dollars per million tokens, because real prices change. The values in
the examples are placeholders, not anyone's current price list.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Usage:
    action: str
    model: str
    input_tokens: int
    output_tokens: int
    ref: str = ""


class Ledger:
    def __init__(self, rates: dict):
        """rates: {model: (usd_per_million_input, usd_per_million_output)}"""
        self.rates = dict(rates)
        self.rows = []

    def add(self, action: str, model: str, input_tokens: int, output_tokens: int, ref: str = "") -> Usage:
        if model not in self.rates:
            raise KeyError(f"no rate configured for model '{model}'")
        u = Usage(action, model, int(input_tokens), int(output_tokens), ref)
        self.rows.append(u)
        return u

    def usd(self, u: Usage) -> float:
        i, o = self.rates[u.model]
        return (u.input_tokens * i + u.output_tokens * o) / 1_000_000

    def total_usd(self) -> float:
        return sum(self.usd(u) for u in self.rows)

    def by_action(self) -> dict:
        """{action: {"calls", "input_tokens", "output_tokens", "usd"}}"""
        out = {}
        for u in self.rows:
            a = out.setdefault(u.action, {"calls": 0, "input_tokens": 0, "output_tokens": 0, "usd": 0.0})
            a["calls"] += 1
            a["input_tokens"] += u.input_tokens
            a["output_tokens"] += u.output_tokens
            a["usd"] += self.usd(u)
        return out

    def to_tsv(self, path: Path) -> None:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["action", "model", "input_tokens", "output_tokens", "usd", "ref"])
            for u in self.rows:
                w.writerow([u.action, u.model, u.input_tokens, u.output_tokens, f"{self.usd(u):.6f}", u.ref])
