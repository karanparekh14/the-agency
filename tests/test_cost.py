import tempfile
import unittest
from pathlib import Path

from agency.inbox.cost import Ledger


class LedgerTest(unittest.TestCase):
    def test_pricing_and_rollup(self):
        l = Ledger({"big": (3.0, 15.0), "small": (1.0, 5.0)})
        l.add("judge", "big", 1_000_000, 100_000)
        l.add("judge", "big", 0, 0)
        l.add("caption", "small", 2_000, 500)
        self.assertAlmostEqual(l.total_usd(), 4.5 + 0.0045)
        a = l.by_action()
        self.assertEqual(a["judge"]["calls"], 2)
        self.assertAlmostEqual(a["caption"]["usd"], 0.0045)

    def test_unknown_model_is_an_error(self):
        with self.assertRaises(KeyError):
            Ledger({}).add("x", "mystery", 1, 1)

    def test_tsv_export(self):
        l = Ledger({"m": (1.0, 1.0)})
        l.add("a", "m", 10, 10, ref="c1")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "usage.tsv"
            l.to_tsv(p)
            self.assertIn("a\tm\t10\t10", p.read_text())


if __name__ == "__main__":
    unittest.main()
