# ISSUE CONTRACT

## Pain
Feature stores and training pipelines can preserve a feature name while losing the exact dataset snapshots and multi-step transforms that produced it.

## Success
- Strict training admission requires a reproducible feature-lineage graph.
- Dataset snapshots bind dataset, snapshot identity, and content hash.
- Transform nodes bind ordered parent node IDs and expected parent fingerprints.
- Multi-step and multi-parent ancestry is fingerprinted deterministically.
- Missing parents, mutated ancestry, invalid terminal lineage, and snapshotless chains fail closed.
- SQL preserves normalized snapshot/transform/edge representation while Python verifies DAG integrity.

## Boundaries
- Snapshot IDs, content hashes, and transform hashes are caller-supplied unless externally attested.
- No Databricks affiliation or adoption.
- No Unity Catalog or production feature-store integration claim.
