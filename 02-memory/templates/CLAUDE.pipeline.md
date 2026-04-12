# Pipeline Rules

@claude-framework/CLAUDE.md

---

## Pipeline identity

<!-- What this pipeline does, input sources, output destinations. -->
<!-- Example: Ingests raw transaction data from Hive, produces features for the churn model. -->

## Data sources

<!-- List tables/topics this pipeline reads from. Use schema.table notation, no real values. -->

## Output schema

<!-- Describe output tables or files. Column names only — no sample data. -->

## Pipeline-specific rules

<!-- Add rules that apply only within this directory. Examples: -->
<!-- - Always partition output tables by ds (YYYY-MM-DD) -->
<!-- - Use structlog with job_id and run_id in every log message -->
<!-- - Raise on null primary keys before writing -->
