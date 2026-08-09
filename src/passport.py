"""Feature lineage passport — provenance-bound features."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum


def digest(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Admit(str, Enum):
    ADMIT = "ADMIT"
    REFUSE = "REFUSE"


@dataclass(frozen=True)
class FeaturePassport:
    feature_name: str
    source_table: str
    transform_hash: str
    as_of: str

    def fingerprint(self) -> str:
        return digest(self.__dict__)


@dataclass(frozen=True)
class FeatureColumn:
    name: str
    passport: FeaturePassport | None


class FeatureLineageGate:
    def admit_training(self, columns: list[FeatureColumn]) -> tuple[Admit, list[str]]:
        missing = [c.name for c in columns if c.passport is None]
        mismatched = [
            c.name
            for c in columns
            if c.passport is not None and c.passport.feature_name != c.name
        ]
        bad = missing + [f"MISMATCH:{n}" for n in mismatched]
        if bad:
            return Admit.REFUSE, bad
        return Admit.ADMIT, []
