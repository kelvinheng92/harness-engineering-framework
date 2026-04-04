# [Project Name] — ML Pipeline

> Extends: ~/claude-framework/claude-config/CLAUDE.md
> Project type: ML model / pipeline
> Data classification: [INTERNAL / CONFIDENTIAL / SECRET — fill in]
> Owner: [DS name] | [team]
> Last updated: [date]

---

## Project context

[Describe what this pipeline does in 2–3 sentences. e.g.:
"This pipeline trains and serves the corporate credit scoring model used by
RMs during credit origination. It ingests financial statement features from
the feature store and outputs a probability-of-default score."]

---

## Data sources

List the data sources Claude is allowed to interact with in this project.
Remove any that do not apply.

| Source | Location | Classification | Notes |
|---|---|---|---|
| Feature store | `feast.internal / credit_features` | CONFIDENTIAL | Read-only |
| Raw financials | `hdfs:///data/financials/processed/` | CONFIDENTIAL | No customer PII |
| Model outputs | `hdfs:///data/model-outputs/credit/` | INTERNAL | Aggregated only |
| Synth dev data | `hdfs:///internal/synth-data/credit/` | INTERNAL | Use for local dev |

Claude must not read from or write to any path not listed above without
explicit approval from the data owner.

---

## Model artefacts

- Registry: `http://mlflow.internal` — project: `[mlflow-project-name]`
- Artefact storage: `hdfs:///mlflow-artefacts/[project]/`
- Do NOT save model files to local disk or personal HDFS home directories

---

## Pipeline standards

### File structure

```
project/
├── CLAUDE.md               ← this file
├── pyproject.toml
├── src/
│   ├── features/           ← feature engineering
│   ├── training/           ← model training scripts
│   ├── evaluation/         ← metrics, fairness checks
│   └── serving/            ← inference pipeline
├── tests/
├── notebooks/              ← EDA only; outputs stripped by pre-commit
└── configs/                ← YAML configs (no secrets)
```

### Required practices

- All hyperparameters in YAML config files, not hardcoded
- Log every experiment to MLflow: params, metrics, artefacts
- Fairness evaluation required before promoting any model to production
- Models must pass the `evaluation/fairness_check.py` gate
- Use `src/` layout — no scripts at repo root

### Spark / Impala

- Use the cluster at `spark-master.internal`
- Prefer Impala for ad-hoc queries; Spark for transformations > 1 GB
- Always set `spark.app.name` to `[project-name]-[your-name]`

---

## Things Claude should flag immediately in this project

- Any attempt to read from `hdfs:///data/raw/customer-pii/`
- Hardcoded model thresholds that bypass the fairness gate
- Saving raw dataframes to local files (even in /tmp)
- Using `pd.read_csv()` on a path containing customer data

---

## Project-specific commands

```bash
# Run training
python -m src.training.train --config configs/train.yaml

# Run evaluation + fairness check
python -m src.evaluation.evaluate --run-id [mlflow-run-id]

# Run tests
pytest tests/ -v

# Submit Spark job
spark-submit src/training/spark_train.py --config configs/spark.yaml
```
