import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = json.loads((ROOT / "machine" / "excellence-state.json").read_text(encoding="utf-8"))
POSITION = json.loads((ROOT / "machine" / "canonical-position.json").read_text(encoding="utf-8"))
CAPABILITIES = json.loads((ROOT / "machine" / "capabilities.json").read_text(encoding="utf-8"))


class CanonicalPositionContractTests(unittest.TestCase):
    def test_evolving_state_is_gate_complete(self):
        self.assertEqual(STATE["principal_state"], "EVOLVING")
        self.assertEqual(STATE["gates"]["CANONICAL_POSITION_RESOLVED"]["status"], "PASS")
        self.assertEqual(STATE["gates"]["EVOLUTION_CURSOR_DEFINED"]["status"], "PASS")
        self.assertEqual(STATE["canonical_position_ref"], "machine/canonical-position.json")

    def test_identity_and_lineage_are_preserved(self):
        self.assertEqual(POSITION["repository"], STATE["repository"])
        self.assertEqual(POSITION["canonical_identity"], "feature-lineage-passport")
        policy = POSITION["integration_policy"]
        self.assertTrue(policy["preserve_repository_identity"])
        self.assertTrue(policy["preserve_lineage"])
        self.assertTrue(policy["presentation_independent"])
        self.assertTrue(policy["absorption_requires_functional_equivalence"])
        self.assertTrue(policy["absorption_requires_proof_equivalence"])

    def test_capabilities_name_repository_native_lineage_mechanisms(self):
        self.assertEqual(CAPABILITIES["capability_family"], "feature_lineage_admission")
        capabilities = set(CAPABILITIES["capabilities"])
        self.assertIn("feature-lineage-passport-admission", capabilities)
        self.assertIn("transform-hash-provenance-binding", capabilities)
        self.assertIn("fail-closed-missing-lineage-refusal", capabilities)
        self.assertIn("deterministic-passport-fingerprints", capabilities)
        self.assertIn("multi-step-feature-dag-ancestry", capabilities)
        self.assertIn("lineage-break-detection", capabilities)
        self.assertNotIn("hyper-scaling", capabilities)

    def test_evolution_and_claim_boundary_are_material(self):
        self.assertEqual(
            POSITION["completed_evolution"]["cursor"],
            "next:multi_step_feature_DAG_ancestry_dataset_snapshots_reproducible_transform_chains_lineage_break_detection",
        )
        self.assertEqual(
            STATE["evolution_cursor"],
            "next:catalog_attested_snapshots_reproducible_transform_execution_receipts_and_lineage_rebuild_proof",
        )
        self.assertIn("externally attested catalog identities", POSITION["next_evolution"])
        self.assertIn("no Databricks affiliation", POSITION["nonclaims"])
        self.assertIn("No Databricks adoption", CAPABILITIES["truth_boundary"])


if __name__ == "__main__":
    unittest.main()
