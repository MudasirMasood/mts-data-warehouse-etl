import csv
import hashlib
import os
import re
import sqlite3
from datetime import datetime

DB_FILE = "de_warehouse.db"
CATALOG_CSV = "mts_catalog.csv"
LEADS_CSV = "leads_tracker.csv"
EXEC_REPORT_CSV = "mts_executive_report.csv"
EXEC_REPORT_XLSX = "mts_executive_report.xlsx"


def normalize_code(raw_code):
    code = raw_code.strip().upper()
    m = re.match(r"^([A-Z]+)-?(\d+)$", code)
    return f"{m.group(1)}-{int(m.group(2)):02d}" if m else code


def make_lead_hash(hospital_name, item_code):
    raw_key = f"{hospital_name.strip().lower()}|{item_code.strip().upper()}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]


def load_dimension_catalog(conn):
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS dim_equipment (item_code TEXT PRIMARY KEY, department TEXT, item_name TEXT, supply_mode TEXT, new_market_price_pkr REAL, est_mts_price_pkr REAL)")
    valid_codes = set()
    if os.path.exists(CATALOG_CSV):
        with open(CATALOG_CSV, mode="r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                code = r["item_code"].strip().upper()
                mp = float(r["new_market_price_pkr"])
                cur.execute("INSERT OR REPLACE INTO dim_equipment VALUES (?, ?, ?, ?, ?, ?)",
                            (code, r["department"].strip(), r["item_name"].strip(), r["supply_mode"].strip(), mp, round(mp * 0.60, 2)))
                valid_codes.add(code)
    conn.commit()
    print(f"[1. DIMENSION UPSERT] Synced {len(valid_codes)} medical systems into 'dim_equipment'.")
    return valid_codes


def etl_fact_leads_incremental(conn, valid_codes):
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(fact_leads)")
    cols = [row for row in cur.fetchall()]
    if cols and "lead_hash" not in cols:
        cur.execute("DROP TABLE fact_leads")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fact_leads (
            lead_hash TEXT PRIMARY KEY, hospital_name TEXT, doctor_name TEXT, phone TEXT,
            item_code TEXT, qty INTEGER, last_contact_date TEXT, status TEXT,
            is_valid_code INTEGER, first_seen_at TEXT, updated_at TEXT
        )
    """)
    cur.execute("CREATE TABLE IF NOT EXISTS dq_audit_log (run_id INTEGER PRIMARY KEY AUTOINCREMENT, run_timestamp TEXT, total_line_items INTEGER, valid_mapped_items INTEGER, unmapped_items INTEGER, pipeline_status TEXT)")

    if not os.path.exists(LEADS_CSV):
        return

    processed, unmapped = 0, 0
    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LEADS_CSV, mode="r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            hosp = re.sub(r"^\d+\.\s*", "", r.get("hospital_name", "").strip())
            if not hosp:
                continue
            entries = [e.strip() for e in r.get("interest", "").split(",") if e.strip()] or ["GENERAL:1"]
            for entry in entries:
                entry = entry.split("@", 1) if "@" in entry else entry
                if ":" in entry:
                    raw_c, q_str = entry.split(":", 1)
                    qty = int(q_str.strip()) if q_str.strip().isdigit() else 1
                else:
                    raw_c, qty = entry, 1
                code = normalize_code(raw_c)
                is_valid = 1 if code in valid_codes else 0
                unmapped += (0 if is_valid else 1)
                l_hash = make_lead_hash(hosp, code)
                cur.execute("""
                    INSERT INTO fact_leads (lead_hash, hospital_name, doctor_name, phone, item_code, qty, last_contact_date, status, is_valid_code, first_seen_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(lead_hash) DO UPDATE SET
                        doctor_name = excluded.doctor_name, phone = excluded.phone, qty = excluded.qty,
                        last_contact_date = excluded.last_contact_date, status = excluded.status,
                        is_valid_code = excluded.is_valid_code, updated_at = excluded.updated_at
                """, (l_hash, hosp, r.get("doctor_name", "").strip(), r.get("phone", "").strip(), code, qty, r.get("last_contact_date", "").strip(), r.get("status", "").strip().title(), is_valid, now_ts, now_ts))
                processed += 1

    dq_status = "PASS" if unmapped == 0 else "WARN_UNMAPPED_CODES"
    cur.execute("INSERT INTO dq_audit_log (run_timestamp, total_line_items, valid_mapped_items, unmapped_items, pipeline_status) VALUES (?, ?, ?, ?, ?)",
                (now_ts, processed, processed - unmapped, unmapped, dq_status))
    conn.commit()
    print(f"[2. INCREMENTAL FACT UPSERT] Upserted {processed} line-items | DQ Status: {dq_status} (Unmapped: {unmapped}).")


def export_styled_excel(export_rows):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
    except ImportError:
        return
    wb = Workbook()
    ws = wb.active
    ws.title = "MTS Pipeline Report"
    ws.append(["Report Date", "Global Rank", "Dept Rank", "Hospital Name", "Contact Person", "Status", "Department", "Item Code", "Equipment Name", "Qty", "Est. Deal Value (PKR)", "Dept Share"])
    fill, font = PatternFill(start_color="0B2545", end_color="0B2545", fill_type="solid"), Font(color="FFFFFF", bold=True, size=11)
    for cell in next(iter(ws.iter_rows(min_row=1, max_row=1))):
        cell.fill, cell.font, cell.alignment = fill, font, Alignment(horizontal="center")
    for r in export_rows:
        ws.append(list(r.values()))
    for col in ws.columns:
        ws.column_dimensions[next(iter(col)).column_letter].width = max(len(str(c.value or "")) for c in col) + 4
    wb.save(EXEC_REPORT_XLSX)
    print(f"[3B. EXCEL EXPORT] Saved formatted Excel workbook '{EXEC_REPORT_XLSX}'!")


def run_window_function_analytics(conn):
    cur = conn.cursor()
    print("\n--- SQL WINDOW REPORT 1: GLOBAL & DEPARTMENT RANKING ---")
    cur.execute("""
        WITH line_values AS (
            SELECT f.hospital_name, f.doctor_name, f.status, COALESCE(d.department, 'Unmapped') AS department,
                   f.item_code, COALESCE(d.item_name, f.item_code) AS item_name, f.qty,
                   COALESCE(f.qty * d.est_mts_price_pkr, 0) AS line_value_pkr
            FROM fact_leads f LEFT JOIN dim_equipment d ON f.item_code = d.item_code
        )
        SELECT RANK() OVER (ORDER BY line_value_pkr DESC),
               ROW_NUMBER() OVER (PARTITION BY department ORDER BY line_value_pkr DESC),
               hospital_name, doctor_name, status, department, item_code, item_name, qty, line_value_pkr,
               SUM(line_value_pkr) OVER (PARTITION BY department)
        FROM line_values ORDER BY 1 ASC
    """)
    export_rows, report_date = [], datetime.now().strftime("%Y-%m-%d")
    for rank, d_rank, hosp, doc, status, dept, code, item, qty, val, d_tot in cur.fetchall():
        share = round((val / d_tot) * 100, 1) if d_tot > 0 else 0
        print(f"Global #{rank} (Dept #{d_rank}) | {hosp:<22} | {item:<34} (x{qty}) | PKR {val:,.0f} ({share}% of {dept})")
        export_rows.append({"report_date": report_date, "global_rank": rank, "dept_rank": d_rank, "hospital_name": hosp, "contact_person": doc, "lead_status": status, "department": dept, "item_code": code, "equipment_name": item, "quantity": qty, "est_deal_value_pkr": int(val), "dept_share": f"{share}%"})

    if export_rows:
        with open(EXEC_REPORT_CSV, mode="w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(next(iter(export_rows)).keys()))
            w.writeheader()
            w.writerows(export_rows)
        print(f"\n[3A. CSV EXPORT] Saved '{EXEC_REPORT_CSV}'.")
        export_styled_excel(export_rows)

    print("\n--- SQL AUDIT REPORT 2: PIPELINE HEALTH HISTORY (LAST 5 RUNS) ---")
    cur.execute("SELECT run_id, run_timestamp, total_line_items, valid_mapped_items, unmapped_items, pipeline_status FROM dq_audit_log ORDER BY run_id DESC LIMIT 5")
    for rid, ts, tot, valid, unmapped, status in cur.fetchall():
        print(f"Run #{rid} | {ts} | Total: {tot} | Valid: {valid} | Unmapped: {unmapped} | Status: {status}")


if __name__ == "__main__":
    conn = sqlite3.connect(DB_FILE)
    codes = load_dimension_catalog(conn)
    etl_fact_leads_incremental(conn, codes)
    run_window_function_analytics(conn)
    conn.close()
