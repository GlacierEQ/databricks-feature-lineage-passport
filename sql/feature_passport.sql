-- Babel: SQL — feature lineage passports with reproducible DAG ancestry.
CREATE TABLE IF NOT EXISTS lineage_dataset_snapshot (
  node_id          VARCHAR PRIMARY KEY,
  dataset_name     VARCHAR NOT NULL,
  snapshot_id      VARCHAR NOT NULL,
  content_hash     VARCHAR NOT NULL,
  node_fingerprint CHAR(64) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS lineage_transform_step (
  node_id          VARCHAR PRIMARY KEY,
  transform_hash   VARCHAR NOT NULL,
  node_fingerprint CHAR(64) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS lineage_transform_parent (
  transform_node_id      VARCHAR NOT NULL REFERENCES lineage_transform_step(node_id),
  parent_ordinal         INTEGER NOT NULL,
  parent_node_id         VARCHAR NOT NULL,
  expected_fingerprint  CHAR(64) NOT NULL,
  PRIMARY KEY (transform_node_id, parent_ordinal),
  UNIQUE (transform_node_id, parent_node_id)
);

CREATE TABLE IF NOT EXISTS feature_passports (
  feature_name       VARCHAR PRIMARY KEY,
  source_table       VARCHAR NOT NULL,
  transform_hash     VARCHAR NOT NULL,
  as_of              DATE NOT NULL,
  terminal_node_id   VARCHAR,
  lineage_fingerprint CHAR(64)
);

CREATE TABLE IF NOT EXISTS training_feature_set (
  run_id           VARCHAR NOT NULL,
  feature_name     VARCHAR NOT NULL REFERENCES feature_passports(feature_name),
  PRIMARY KEY (run_id, feature_name)
);

-- The Python verifier is the strict admission authority for DAG ancestry: it checks
-- missing parents, parent fingerprint mismatches, cycles, terminal existence, and
-- reachability to at least one dataset snapshot before training admission.
-- SQL preserves the normalized lineage representation; it does not by itself prove
-- that arbitrary parent_node_id values reference a valid snapshot/transform union.
