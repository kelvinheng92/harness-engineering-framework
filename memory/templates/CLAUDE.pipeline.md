# Pipeline Rules

@claude-framework/CLAUDE.md

---

## Pipeline identity

<!-- What this pipeline does, input sources, output destinations. -->
<!-- Example: Ingests raw transaction data from Hive, produces features for the churn model. -->

## Data sources

<!-- List tables/topics this pipeline reads from. Use schema.table notation, no real values. -->
<!-- Example:
- raw.txn_events          — daily transaction events partitioned by ds
- curated.customer_dim    — customer dimension (SCD Type 2)
-->

## Output schema

<!-- Describe output tables or files. Column names and types only — no sample data. -->
<!-- Example:
- features.churn_features (customer_id STRING, recency_days INT, txn_count_30d INT, ds STRING)
-->

---

## Pipeline-specific rules

### Partitioning & idempotency

- Always partition output tables by `ds` (format: `YYYY-MM-DD`)
- Pipelines must be idempotent: delete the target partition before writing (`INSERT OVERWRITE`)
- Never append to an existing partition without first verifying intent with the user

### Data quality gates

- Raise `ValueError` and abort if primary key column contains nulls before any write
- Assert row count > 0 after each major transformation step; log the count with `structlog`
- Validate that `ds` partition values match the expected run date before committing output

### Logging

- Use `structlog` for all logging — no `print()`, no `logging.basicConfig()`
- Every log entry must include `job_id`, `run_id`, and `ds` in the bound context
- Log row counts at source read, after each transform, and at final write
- Never log raw cell values — reference column names and aggregates only

### Error handling

- Catch specific exceptions, not bare `except:`
- On failure, log the error with full context then re-raise — do not silently swallow exceptions
- Pipeline exit codes: `0` success, `1` data quality failure, `2` infrastructure error

### Performance

- Push filter predicates into the Hive read (partition pruning before any Python transform)
- Use `spark.sql` or PySpark — avoid `pandas` on datasets > 1 M rows unless explicitly scoped
- Cache DataFrames only when reused more than twice in the same job; unpersist when done

### Security & compliance

- Never write output to a path outside the approved data lake prefix for this pipeline
- Strip or hash any column that qualifies as PII before writing to non-restricted zones
- If the pipeline reads a restricted-zone table, confirm the output zone is also restricted

### Testing

- Unit-test all transformation functions with a small synthetic DataFrame (no real data)
- Integration tests must use a dedicated test schema, never production tables
- Include a dry-run flag (`--dry-run`) that runs all transforms but skips the final write
****