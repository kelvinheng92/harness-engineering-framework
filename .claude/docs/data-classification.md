# Data Classification Guide — Claude Code Usage

This guide defines what data may and may not be included in Claude
prompts, code examples, or generated outputs.

---

## Classification levels

| Level | Definition | Examples |
|---|---|---|
| **PUBLIC** | Approved for external release | Published research, marketing copy |
| **INTERNAL** | For OCBC staff only | Aggregated metrics, internal docs |
| **CONFIDENTIAL** | Business-sensitive, restricted access | Customer counts, model performance, anonymised datasets |
| **SECRET** | Highest sensitivity, strictly controlled | Individual customer PII, account data, MNPI |

---

## What you may use with Claude Code

### ✅ Always safe

| Data type | Notes |
|---|---|
| Aggregated statistics | No individual-level data |
| Schema definitions (column names only) | No sample rows |
| Code logic, algorithms, pipeline structure | No embedded data |
| Internal documentation (INTERNAL classification) | Check with team lead |
| Publicly available financial models / research | Cite the source |

### ⚠️ Conditional — check before use

| Data type | Condition |
|---|---|
| Industry benchmark data | Must be INTERNAL or lower classification |
| Partial schema with sample rows | Rows must use synthetic values only |
| Model outputs (scores, predictions) | Aggregated only; no customer-linked outputs |

### 🚫 Never include in any Claude prompt or code example

| Data type | Reason |
|---|---|
| NRIC / FIN / Passport numbers | Singapore PII — legal requirement |
| Full name + any identifier | Linkable PII |
| Account numbers (savings, loan, credit card) | Financial PII |
| Transaction data (amounts, dates, merchants) | Financial PII |
| Credit scores or risk ratings linked to individuals | CONFIDENTIAL+ |
| Internal customer IDs, i.e CIF number | Linkable to individual |
| Corporate UEN linked to a specific company + financial detail | CONFIDENTIAL |
| MNPI (Material Non-Public Information) | Regulatory — MAS requirements |
| Salary or employment data | Sensitive personal data |

---

## Practical rules for code and prompts

### Strip notebook outputs before committing

The pre-commit hook enforces this via `nbstripout`, but double-check
notebooks that contain inline data previews (`df.head()`, `df.sample()`).

### Using Claude for SQL queries

Fine to share the query structure and column names. Never paste `LIMIT 10`
output rows into the prompt.

```sql
-- ✅ Allowed — share this
SELECT customer_segment, COUNT(*) as count, AVG(credit_score) as avg_score
FROM credit.customers
GROUP BY customer_segment;

-- 🚫 Not allowed — never paste this output into a prompt
-- | customer_id | nric       | credit_score |
-- | CUST_00123  | S1234567A  | 720          |
```

---

## When you're unsure

1. Check this guide
2. Prompt me to ask
3. When still unsure: treat it as SECRET and do not include it

The principle: **if in doubt, leave it out.**

---

## Incident reporting

If you accidentally include PII or CONFIDENTIAL data in a Claude prompt:

1. Note the approximate time and what was shared
2. Report immediately to me
3. The AI Lab will check the audit logs and assess the scope
4. No disciplinary action for genuine accidents — the goal is learning

Deliberate circumvention of these controls is a policy violation and
will be escalated to InfoSec.
