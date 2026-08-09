#!/usr/bin/env python3
"""Cold-start: FeatureLineageGate refuse missing passport."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from passport import Admit, FeatureColumn, FeatureLineageGate, FeaturePassport

def main() -> int:
    cols = [
        FeatureColumn("f1", FeaturePassport("f1", "t.a", "h1", "2026-01-01")),
        FeatureColumn("f2", None),
    ]
    decision, bad = FeatureLineageGate().admit_training(cols)
    out = {
        "decision": decision.value,
        "bad": bad,
        "expected_decision": Admit.REFUSE.value,
        "ok": decision is Admit.REFUSE and "f2" in bad,
    }
    print(json.dumps(out, sort_keys=True))
    return 0 if out["ok"] else 1
if __name__ == "__main__":
    raise SystemExit(main())
