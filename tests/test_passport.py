from __future__ import annotations
import unittest
from src.passport import Admit, FeatureColumn, FeatureLineageGate, FeaturePassport

class PassTests(unittest.TestCase):
    def test_refuse_missing(self):
        g = FeatureLineageGate()
        st, bad = g.admit_training([FeatureColumn("f1", None)])
        self.assertEqual(st, Admit.REFUSE)

    def test_admit(self):
        p = FeaturePassport("f1", "t.events", "abc", "2026-08-01")
        st, bad = FeatureLineageGate().admit_training([FeatureColumn("f1", p)])
        self.assertEqual(st, Admit.ADMIT)
        self.assertEqual(bad, [])

if __name__ == "__main__":
    unittest.main()
