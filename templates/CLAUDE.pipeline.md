# ML Pipeline — Project Rules
# Extends: org-wide CLAUDE.md (do not duplicate those rules here)

## Scope
This directory contains ML pipeline code: feature engineering, training,
evaluation, and batch scoring jobs on Cloudera.

## Pipeline-specific standards

### Entry points
- `train.py` — training entrypoint, reads from `config.yaml`
- `evaluate.py` — evaluation logic, writes metrics to MLflow
- `score.py` — batch scoring, writes predictions to Hive

### Config
- All paths, table names, and hyperparameters live in `config.yaml`
- Never hardcode HDFS paths or Hive table names in Python files

### MLflow
- Log every run: params, metrics, input dataset version, model artifact
- Tag runs with `env` (dev/staging/prod) and `triggered_by` (manual/oozie)

### Data handling
- Input: read from Hive via ibis or PySpark — never raw SQL f-strings
- Output: write to a dedicated output table, never overwrite source tables
- Validate schema at pipeline entry — fail fast on unexpected columns

## Allowed agents for this directory
- `data-scientist` — model development and experiment code
- `data-analyst` — feature validation queries
- `quality-assurance` — pipeline tests and data quality checks
