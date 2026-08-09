from __future__ import annotations
import unittest
from pathlib import Path
SQL = Path(__file__).resolve().parents[1] / "sql" / "feature_passport.sql"
class T(unittest.TestCase):
    def test_fk(self):
        t = SQL.read_text()
        self.assertIn("REFERENCES feature_passports", t)
if __name__ == "__main__":
    unittest.main()
