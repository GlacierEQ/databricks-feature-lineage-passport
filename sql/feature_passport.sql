-- Babel: SQL — feature lineage passports required for train admit.
CREATE TABLE IF NOT EXISTS feature_passports (
  feature_name     VARCHAR PRIMARY KEY,
  source_table     VARCHAR NOT NULL,
  transform_hash   CHAR(64) NOT NULL,
  as_of            DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS training_feature_set (
  run_id           VARCHAR NOT NULL,
  feature_name     VARCHAR NOT NULL REFERENCES feature_passports(feature_name),
  PRIMARY KEY (run_id, feature_name)
);
-- Missing passport => cannot insert into training_feature_set (FK).
