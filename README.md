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
# Medical Equipment Supply — Data Warehouse, CI/CD ETL & AI Receptionist

An end-to-end **Python & SQL Data Engineering + AI Automation system** built to capture inbound inquiries, ingest and normalize raw operational records, maintain historical price lineage, and deliver executive analytics.

---

## System Architecture

```text
[24/7 AI Receptionist (FastAPI + Gemini)] ──▶ [Raw CSV Leads & Catalog]
                                                       │
                                                       ▼
                                        [CI/CD Unit Test Gate (unittest)]
                                                       │
                                                       ▼
                              [Incremental ETL & Anomaly Guardrails (Python)]
                                                       │
                         ┌─────────────────────────────┴─────────────────────────────┐
                         ▼                                                           ▼
       [dim_equipment_scd2 (SCD Type 2)]                         [fact_leads (SHA-256 Upserts)]
                         │                                                           │
                         └─────────────────────────────┬─────────────────────────────┘
                                                       ▼
                                    [SQL Window Functions + OpenPyXL .xlsx]
```

---

## Key Engineering Features

### 1. Dimensional Modeling & SCD Type 2 (`de_etl_lab.py`)
* **Slowly Changing Dimensions (SCD Type 2):** `dim_equipment_scd2` tracks historical equipment price changes over time using `valid_from`, `valid_to`, and `is_current` flags so historical quotes always preserve accurate price lineage.
* **Incremental Fact Upserts:** `fact_leads` generates deterministic 16-character `SHA-256` surrogate keys (`lead_hash`) and executes atomic `ON CONFLICT` upserts—preventing duplicate records across repeated runs.
* **Ingestion & Normalization:** Regex-based SKU standardization (`normalize_code`) and 1-to-many order exploding (`OT-02:3, ICU-02:4` → atomic relational rows).

### 2. Data Quality, Observability & CI/CD (`run_pipeline_ci.py`, `test_de_pipeline.py`)
* **Pre-ETL CI/CD Quality Gate:** Enforces an automated `unittest` regression suite covering SKU normalization, deterministic hashing, and in-memory SQLite SCD2 schema creation before executing the warehouse pipeline.
* **Automated Anomaly Guardrails:** Flags outlier quantities (`OUTLIER_QTY`) and missing contact fields (`MISSING_PHONE`) into `dq_flag` and records run health metrics in `dq_audit_log` and `pipeline.log`.

### 3. SQL Analytics & Executive Serving Layer
* **SQL Window Functions:** Uses Common Table Expressions (CTEs), `RANK() OVER (ORDER BY ...)`, `ROW_NUMBER() OVER (PARTITION BY department ...)`, and `SUM() OVER (...)` to rank deals globally and within each medical department.
* **Automated Excel Reporting:** Exports styled executive workbooks (`mts_executive_report.xlsx`) with dynamic column sizing and department revenue share percentages via `openpyxl`.

### 4. Dual-Mode 24/7 AI Receptionist (`ai_receptionist.py`, `dashboard.py`)
* **Multi-Turn Conversation Memory:** Tracks session context across messages so visitors never repeat their name, contact number, or requested equipment/service.
* **Structured JSON Lead Extraction:** Powered by Python `FastAPI` and Google Gemini API (with automatic model fallback), replying naturally in English and Roman Urdu while logging qualified leads directly into the warehouse ingestion layer.
* **Master CLI Launcher (`dashboard.py`):** Unified command center for running CI/CD ETL pipelines, CRM follow-ups, quote generation, and launching the FastAPI AI Receptionist server.

---

## Repository Structure

```text
├── ai_receptionist.py     # FastAPI 24/7 AI Receptionist (Web UI + WhatsApp Webhook + Session Memory)
├── dashboard.py           # Master CLI Command Center for ETL, CRM, and AI Receptionist
├── de_etl_lab.py          # SCD Type 2 Dimension Loader, Incremental Fact Upserts & Window Analytics
├── run_pipeline_ci.py     # CI/CD Quality Gate (runs unit tests prior to ETL execution)
├── test_de_pipeline.py    # Automated unittest regression suite
└── .gitignore             # Excludes .env secrets, private client CSVs, local SQLite DBs & logs
```

---

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install fastapi uvicorn google-genai openpyxl
   ```
2. **Configure environment variable (for `ai_receptionist.py`):**
   Create a `.env` file in the root directory:
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```
3. **Run the CI/CD Data Warehouse Pipeline:**
   ```bash
   python run_pipeline_ci.py
   ```
4. **Launch the 24/7 AI Receptionist Web Widget:**
   ```bash
   uvicorn ai_receptionist:app --reload
   ```
