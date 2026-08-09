from __future__ import annotations
import unittest
from src.passport import Admit, FeatureColumn, FeatureLineageGate, FeaturePassport

class Adv(unittest.TestCase):
    def test_name_mismatch(self):
        cols = [FeatureColumn("f1", FeaturePassport("other", "t", "h", "d"))]
        d, bad = FeatureLineageGate().admit_training(cols)
        self.assertEqual(d, Admit.REFUSE)
        self.assertTrue(any(x.startswith("MISMATCH:") for x in bad))
    def test_admit_all(self):
        cols = [FeatureColumn("f1", FeaturePassport("f1", "t", "h", "d"))]
        d, bad = FeatureLineageGate().admit_training(cols)
        self.assertEqual(d, Admit.ADMIT)
        self.assertEqual(bad, [])
    def test_passport_fingerprint(self):
        p = FeaturePassport("f1", "t", "h", "d")
        self.assertEqual(len(p.fingerprint()), 64)

if __name__ == "__main__":
    unittest.main()
