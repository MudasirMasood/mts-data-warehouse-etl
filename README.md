# Medical Equipment Supply — Data Warehouse & CI/CD Pipeline

An end-to-end **Python & SQL Data Engineering pipeline** built to ingest, clean, model, and analyze real hospital equipment demand and quotation pipelines.

## Key Engineering Features
- **Ingestion & Normalization:** Regex-based SKU standardization (`normalize_code`) and 1-to-many order exploding (`OT-02:3, ICU-02:4` → atomic relational rows).
- **Star Schema Data Warehouse (SQLite / SQL):** `dim_equipment` (Dimension) and `fact_leads` (Fact) tables with deterministic SHA-256 `lead_hash` keys and `ON CONFLICT` incremental upserts.
- **Data Observability:** Persistent `dq_audit_log` table + Python `logging` (`pipeline.log`) tracking row counts, unmapped codes, and pipeline health.
- **SQL Analytics & Serving Layer:** CTEs, `LEFT JOIN` + `COALESCE`, SQL Window Functions (`RANK()`, `ROW_NUMBER() OVER (PARTITION BY department)`), and automated `.xlsx` executive reporting via `openpyxl`.
- **CI/CD Quality Gate:** Automated `unittest` regression suite (`test_de_pipeline.py`) enforced prior to ETL execution (`run_pipeline_ci.py`).

## Quick Start
```bash
pip install openpyxl
python run_pipeline_ci.py
```
