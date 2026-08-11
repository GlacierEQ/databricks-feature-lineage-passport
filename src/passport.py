"""Feature lineage passport — provenance-bound multi-step feature ancestry."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Iterable


def canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(obj: object) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def _token(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name)
    return value


class Admit(str, Enum):
    ADMIT = "ADMIT"
    REFUSE = "REFUSE"


@dataclass(frozen=True)
class ParentRef:
    node_id: str
    fingerprint: str

    def __post_init__(self) -> None:
        _token("parent_node_id", self.node_id)
        if len(self.fingerprint) != 64 or any(ch not in "0123456789abcdef" for ch in self.fingerprint):
            raise ValueError("parent_fingerprint")


@dataclass(frozen=True)
class DatasetSnapshot:
    node_id: str
    dataset: str
    snapshot_id: str
    content_hash: str

    def __post_init__(self) -> None:
        for name in ("node_id", "dataset", "snapshot_id", "content_hash"):
            _token(name, getattr(self, name))

    def fingerprint(self) -> str:
        return digest(
            {
                "kind": "dataset_snapshot",
                "node_id": self.node_id,
                "dataset": self.dataset,
                "snapshot_id": self.snapshot_id,
                "content_hash": self.content_hash,
            }
        )


@dataclass(frozen=True)
class TransformStep:
    node_id: str
    transform_hash: str
    parents: tuple[ParentRef, ...]

    def __post_init__(self) -> None:
        _token("node_id", self.node_id)
        _token("transform_hash", self.transform_hash)
        if not self.parents:
            raise ValueError("transform_parents")
        if any(not isinstance(parent, ParentRef) for parent in self.parents):
            raise TypeError("transform_parent")
        parent_ids = [parent.node_id for parent in self.parents]
        if len(parent_ids) != len(set(parent_ids)):
            raise ValueError("duplicate_transform_parent")

    def fingerprint(self) -> str:
        return digest(
            {
                "kind": "transform_step",
                "node_id": self.node_id,
                "transform_hash": self.transform_hash,
                "parents": [
                    {"node_id": parent.node_id, "fingerprint": parent.fingerprint}
                    for parent in self.parents
                ],
            }
        )


LineageNode = DatasetSnapshot | TransformStep


def parent_ref(node: LineageNode) -> ParentRef:
    return ParentRef(node.node_id, node.fingerprint())


@dataclass(frozen=True)
class LineageVerification:
    ok: bool
    breaks: tuple[str, ...]
    graph_fingerprint: str
    reachable_nodes: tuple[str, ...]
    snapshot_nodes: tuple[str, ...]
    transform_nodes: tuple[str, ...]


@dataclass(frozen=True)
class FeatureLineageGraph:
    snapshots: tuple[DatasetSnapshot, ...]
    transforms: tuple[TransformStep, ...]
    terminal_node_id: str

    def __post_init__(self) -> None:
        if any(not isinstance(node, DatasetSnapshot) for node in self.snapshots):
            raise TypeError("snapshot")
        if any(not isinstance(node, TransformStep) for node in self.transforms):
            raise TypeError("transform")
        _token("terminal_node_id", self.terminal_node_id)

    def nodes(self) -> dict[str, LineageNode]:
        out: dict[str, LineageNode] = {}
        for node in (*self.snapshots, *self.transforms):
            if node.node_id in out:
                raise ValueError(f"DUPLICATE_NODE_ID:{node.node_id}")
            out[node.node_id] = node
        return out

    def fingerprint(self) -> str:
        return digest(
            {
                "snapshots": [
                    {
                        "node_id": node.node_id,
                        "dataset": node.dataset,
                        "snapshot_id": node.snapshot_id,
                        "content_hash": node.content_hash,
                        "fingerprint": node.fingerprint(),
                    }
                    for node in sorted(self.snapshots, key=lambda item: item.node_id)
                ],
                "transforms": [
                    {
                        "node_id": node.node_id,
                        "transform_hash": node.transform_hash,
                        "parents": [
                            {"node_id": parent.node_id, "fingerprint": parent.fingerprint}
                            for parent in node.parents
                        ],
                        "fingerprint": node.fingerprint(),
                    }
                    for node in sorted(self.transforms, key=lambda item: item.node_id)
                ],
                "terminal_node_id": self.terminal_node_id,
            }
        )

    def verify(self) -> LineageVerification:
        breaks: list[str] = []
        try:
            nodes = self.nodes()
        except ValueError as exc:
            return LineageVerification(False, (str(exc),), self.fingerprint(), (), (), ())

        if self.terminal_node_id not in nodes:
            breaks.append(f"TERMINAL_MISSING:{self.terminal_node_id}")

        for step in self.transforms:
            for parent in step.parents:
                actual = nodes.get(parent.node_id)
                if actual is None:
                    breaks.append(f"MISSING_PARENT:{step.node_id}:{parent.node_id}")
                    continue
                if actual.fingerprint() != parent.fingerprint:
                    breaks.append(f"PARENT_FINGERPRINT_MISMATCH:{step.node_id}:{parent.node_id}")

        graph: dict[str, tuple[str, ...]] = {
            node.node_id: () for node in self.snapshots
        }
        for step in self.transforms:
            graph[step.node_id] = tuple(parent.node_id for parent in step.parents)

        visiting: set[str] = set()
        visited: set[str] = set()
        cycle_nodes: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                cycle_nodes.add(node_id)
                return
            if node_id in visited or node_id not in graph:
                return
            visiting.add(node_id)
            for parent_id in graph[node_id]:
                visit(parent_id)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in sorted(graph):
            visit(node_id)
        for node_id in sorted(cycle_nodes):
            breaks.append(f"CYCLE:{node_id}")

        reachable: set[str] = set()
        if self.terminal_node_id in nodes:
            stack = [self.terminal_node_id]
            while stack:
                current = stack.pop()
                if current in reachable:
                    continue
                reachable.add(current)
                for parent_id in graph.get(current, ()):
                    if parent_id in nodes:
                        stack.append(parent_id)

        reachable_snapshots = sorted(
            node_id for node_id in reachable if isinstance(nodes.get(node_id), DatasetSnapshot)
        )
        if self.terminal_node_id in nodes and not reachable_snapshots:
            breaks.append("NO_REACHABLE_DATASET_SNAPSHOT")

        return LineageVerification(
            ok=not breaks,
            breaks=tuple(sorted(set(breaks))),
            graph_fingerprint=self.fingerprint(),
            reachable_nodes=tuple(sorted(reachable)),
            snapshot_nodes=tuple(reachable_snapshots),
            transform_nodes=tuple(
                sorted(node_id for node_id in reachable if isinstance(nodes.get(node_id), TransformStep))
            ),
        )


@dataclass(frozen=True)
class FeaturePassport:
    feature_name: str
    source_table: str
    transform_hash: str
    as_of: str
    lineage: FeatureLineageGraph | None = None

    def __post_init__(self) -> None:
        for name in ("feature_name", "source_table", "transform_hash", "as_of"):
            _token(name, getattr(self, name))
        if self.lineage is not None and not isinstance(self.lineage, FeatureLineageGraph):
            raise TypeError("lineage")

    def fingerprint(self) -> str:
        return digest(
            {
                "feature_name": self.feature_name,
                "source_table": self.source_table,
                "transform_hash": self.transform_hash,
                "as_of": self.as_of,
                "lineage_fingerprint": self.lineage.fingerprint() if self.lineage else None,
            }
        )


@dataclass(frozen=True)
class FeatureColumn:
    name: str
    passport: FeaturePassport | None


class FeatureLineageGate:
    def __init__(self, require_reproducible_lineage: bool = False):
        self.require_reproducible_lineage = bool(require_reproducible_lineage)

    def admit_training(self, columns: list[FeatureColumn]) -> tuple[Admit, list[str]]:
        missing = [column.name for column in columns if column.passport is None]
        mismatched = [
            column.name
            for column in columns
            if column.passport is not None and column.passport.feature_name != column.name
        ]
        bad = missing + [f"MISMATCH:{name}" for name in mismatched]

        for column in columns:
            passport = column.passport
            if passport is None or passport.feature_name != column.name:
                continue
            if self.require_reproducible_lineage and passport.lineage is None:
                bad.append(f"LINEAGE_MISSING:{column.name}")
                continue
            if passport.lineage is not None:
                verification = passport.lineage.verify()
                if not verification.ok:
                    bad.extend(
                        f"LINEAGE_BREAK:{column.name}:{reason}"
                        for reason in verification.breaks
                    )

        if bad:
            return Admit.REFUSE, sorted(set(bad))
        return Admit.ADMIT, []

    def admit_training_strict(self, columns: list[FeatureColumn]) -> tuple[Admit, list[str]]:
        return FeatureLineageGate(require_reproducible_lineage=True).admit_training(columns)
