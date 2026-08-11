from __future__ import annotations
import unittest
from src.passport import (
    Admit,
    DatasetSnapshot,
    FeatureColumn,
    FeatureLineageGate,
    FeatureLineageGraph,
    FeaturePassport,
    ParentRef,
    TransformStep,
    parent_ref,
)


class PassTests(unittest.TestCase):
    def test_refuse_missing(self):
        status, bad = FeatureLineageGate().admit_training([FeatureColumn("f1", None)])
        self.assertEqual(status, Admit.REFUSE)
        self.assertIn("f1", bad)

    def test_legacy_single_hop_admit_remains_compatible(self):
        passport = FeaturePassport("f1", "t.events", "abc", "2026-08-01")
        status, bad = FeatureLineageGate().admit_training([FeatureColumn("f1", passport)])
        self.assertEqual(status, Admit.ADMIT)
        self.assertEqual(bad, [])

    def make_graph(self):
        events = DatasetSnapshot("events-snapshot", "t.events", "snap-2026-08-01", "events-hash")
        users = DatasetSnapshot("users-snapshot", "t.users", "snap-2026-08-01", "users-hash")
        normalized = TransformStep("normalize", "normalize-v3", (parent_ref(events),))
        joined = TransformStep(
            "join-users",
            "join-v5",
            (parent_ref(normalized), parent_ref(users)),
        )
        aggregate = TransformStep("aggregate", "agg-v2", (parent_ref(joined),))
        graph = FeatureLineageGraph(
            snapshots=(events, users),
            transforms=(normalized, joined, aggregate),
            terminal_node_id="aggregate",
        )
        return graph, events, users, normalized, joined, aggregate

    def test_multistep_dag_is_reproducible_and_strictly_admitted(self):
        graph, *_ = self.make_graph()
        verification = graph.verify()
        self.assertTrue(verification.ok)
        self.assertEqual(verification.breaks, ())
        self.assertEqual(set(verification.snapshot_nodes), {"events-snapshot", "users-snapshot"})
        self.assertEqual(set(verification.transform_nodes), {"normalize", "join-users", "aggregate"})
        self.assertEqual(len(verification.graph_fingerprint), 64)

        passport = FeaturePassport("f1", "t.events", "agg-v2", "2026-08-01", graph)
        status, bad = FeatureLineageGate(require_reproducible_lineage=True).admit_training(
            [FeatureColumn("f1", passport)]
        )
        self.assertEqual(status, Admit.ADMIT)
        self.assertEqual(bad, [])

    def test_strict_gate_refuses_legacy_passport_without_graph(self):
        passport = FeaturePassport("f1", "t.events", "abc", "2026-08-01")
        status, bad = FeatureLineageGate().admit_training_strict([FeatureColumn("f1", passport)])
        self.assertEqual(status, Admit.REFUSE)
        self.assertEqual(bad, ["LINEAGE_MISSING:f1"])

    def test_missing_parent_is_reported_as_lineage_break(self):
        snapshot = DatasetSnapshot("events", "t.events", "s1", "h1")
        broken = TransformStep("normalize", "v1", (ParentRef("missing", "a" * 64),))
        graph = FeatureLineageGraph((snapshot,), (broken,), "normalize")
        verification = graph.verify()
        self.assertFalse(verification.ok)
        self.assertIn("MISSING_PARENT:normalize:missing", verification.breaks)

        passport = FeaturePassport("f1", "t.events", "v1", "2026-08-01", graph)
        status, bad = FeatureLineageGate(True).admit_training([FeatureColumn("f1", passport)])
        self.assertEqual(status, Admit.REFUSE)
        self.assertTrue(any("MISSING_PARENT" in item for item in bad))

    def test_parent_fingerprint_mismatch_detects_mutated_ancestry(self):
        snapshot = DatasetSnapshot("events", "t.events", "s1", "h1")
        forged_ref = ParentRef("events", "f" * 64)
        step = TransformStep("normalize", "v1", (forged_ref,))
        graph = FeatureLineageGraph((snapshot,), (step,), "normalize")
        verification = graph.verify()
        self.assertFalse(verification.ok)
        self.assertIn("PARENT_FINGERPRINT_MISMATCH:normalize:events", verification.breaks)

    def test_dataset_snapshot_change_changes_graph_and_passport_identity(self):
        graph, events, users, normalized, joined, aggregate = self.make_graph()
        passport = FeaturePassport("f1", "t.events", "agg-v2", "2026-08-01", graph)
        changed_events = DatasetSnapshot(events.node_id, events.dataset, "snap-2026-08-02", "events-hash-v2")
        changed_graph = FeatureLineageGraph(
            snapshots=(changed_events, users),
            transforms=(normalized, joined, aggregate),
            terminal_node_id="aggregate",
        )
        self.assertNotEqual(graph.fingerprint(), changed_graph.fingerprint())
        self.assertNotEqual(passport.fingerprint(), FeaturePassport("f1", "t.events", "agg-v2", "2026-08-01", changed_graph).fingerprint())
        self.assertFalse(changed_graph.verify().ok)
        self.assertTrue(any("PARENT_FINGERPRINT_MISMATCH" in reason for reason in changed_graph.verify().breaks))

    def test_transform_order_and_parent_order_are_identity_bearing(self):
        left = DatasetSnapshot("left", "t.left", "s1", "h1")
        right = DatasetSnapshot("right", "t.right", "s1", "h2")
        join_lr = TransformStep("join", "join-v1", (parent_ref(left), parent_ref(right)))
        join_rl = TransformStep("join", "join-v1", (parent_ref(right), parent_ref(left)))
        self.assertNotEqual(join_lr.fingerprint(), join_rl.fingerprint())

    def test_no_reachable_snapshot_refuses_graph(self):
        a = TransformStep("a", "v1", (ParentRef("b", "b" * 64),))
        b = TransformStep("b", "v1", (ParentRef("a", "a" * 64),))
        graph = FeatureLineageGraph((), (a, b), "a")
        verification = graph.verify()
        self.assertFalse(verification.ok)
        self.assertIn("NO_REACHABLE_DATASET_SNAPSHOT", verification.breaks)


if __name__ == "__main__":
    unittest.main()
