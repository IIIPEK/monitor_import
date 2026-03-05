# monitor_import

Utilities for converting Windchill CSV exports into Monitor ERP import files with `.csv` extension and TAB delimiter.

The project is now split into small modules so the same conversion flow can be reused from:

- CLI via `convert.py`
- service code via `app.conversion_service.convert_file()`
- web app via FastAPI without duplicating conversion logic

## What It Generates

The converter creates four tab-delimited CSV files:

- `_00_material_parts.csv`: material items from `Material Number` and `Material Description`
- `_01_parts.csv`: parts from Windchill `Number` and `Name`
- `_02_bom.csv`: BOM structure from `Structure Level`
- `_03_purchase_raw.csv`: purchase/raw data where `Qty Of Raw Material` is the summed `Model Weight`

## Requirements

- Python 3.10+
- SQL Anywhere client access for live deduplication against Monitor

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Environment

The converter supports SQL Anywhere settings from:

- environment variables
- optional `.env`
- optional local fallback file `app/conf.py`

`.env` is optional. If present, it is loaded before fallback values from `app/conf.py`.

Configure `.env` if you want external settings:

```env
SQLANY_UID=...
SQLANY_PWD=...
SQLANY_SERVERNAME=...
SQLANY_DBN=...
SQLANY_ASTART=No
SQLANY_HOST=...
QUERY_FILE=sql/query.sql
```

`QUERY_FILE` should point to a SQL file that returns existing material numbers already present in Monitor.
If `QUERY_FILE` is not set, the default is `sql/query.sql`.

Current expected query shape:

```sql
Select Distinct
_Part.PartNumber as PartPartNumber,
_Part.Description as PartDescription,
_Part.ExtraDescription
from monitor.Part as _Part
WHERE (_Part.Type IN (0)) AND _Part.Status <> 99 and _Part.PartNumber LIKE '1003___'
Order by PartPartNumber ASC;
```

Only the first column is used for deduplication.

## Input Expectations

The Windchill export is expected to contain these columns:

- `Structure Level`
- `Number`
- `Name`
- `Quantity`
- `Region`
- `Model Weight`
- `Material Number`
- `Material Description`

The file format is the Windchill variant where each row is wrapped in outer quotes and inner quotes are doubled.

## Usage

Run with live SQL Anywhere deduplication:

```bash
python3 convert.py INPUT.csv --out-dir TSV --base-name out
```

Run without hitting SQL Anywhere:

```bash
python3 convert.py INPUT.csv --out-dir TSV --base-name out --skip-material-dedup-query
```

Run using a saved export of the SQL query instead of live DB access:

```bash
python3 convert.py INPUT.csv --out-dir TSV --base-name out --existing-materials-file existing_materials.csv
```

For `--existing-materials-file`, the expected format is semicolon-delimited with the material number in the first column, for example:

```text
PartPartNumber;PartDescription;ExtraDescription
'1003612';'Armatuur ISO 6935-2-6 B500CWR';
'1003611';'Armatuur ISO 6935-2-10 B500CWR';
```

## Web App

Run web server:

```bash
uvicorn run_web:app --reload
```

Open:

- `http://127.0.0.1:8000/` (conversion UI)
- `http://127.0.0.1:8000/healthz` (healthcheck)

Current web features:

- Login/logout with cookie session
- Profile page for changing own password
- Admin page for creating users and changing any user password
- File upload + convert + ZIP download
- Dedup modes: skip, SQL Anywhere, existing-materials-file
- Conversion job logging (`conversion_jobs` table)

Bootstrap admin is created automatically on first startup if no admin exists:

- `BOOTSTRAP_ADMIN_LOGIN` (default: `admin`)
- `BOOTSTRAP_ADMIN_PASSWORD` (default: `admin`)

Database config:

- `DATABASE_URL` (default: `sqlite:///./data/web.db`)
- `SESSION_SECRET` for session signing

## Migrations (Alembic)

The web schema is versioned with Alembic.

```bash
alembic upgrade head
```

Current initial migration creates:

- `users`
- `conversion_jobs`

## Output Notes

- Files use `.csv` extension because Monitor import accepts only `.txt` and `.csv`
- Data is still TAB-delimited, not comma-delimited
- `_01_parts.csv` includes `Weight per item` from `Model Weight`
- `_03_purchase_raw.csv` uses summed weight, not BOM quantity
- `_00_material_parts.csv` leaves `Weight per item` empty
- `_00_material_parts.csv` excludes material numbers already returned by `sql/query.sql`

## Project Layout

- `convert.py`: CLI entry point
- `app/conversion_cli.py`: argument parsing and CLI output
- `app/conversion_service.py`: orchestration layer for reading input, loading dedup data, writing outputs
- `app/conversion_transform.py`: pure transformation logic from parsed Windchill rows to output tables
- `app/conversion_models.py`: dataclasses for output paths and generated tables
- `app/windchill_csv.py`: Windchill CSV normalization and parsing
- `app/formatting.py`: string trimming and decimal parsing/formatting helpers
- `app/material_dedup.py`: loading existing material numbers from SQL Anywhere or exported file
- `app/config.py`: SQL Anywhere settings loading from env, optional `.env`, and optional local fallback config
- `app/conf.py`: optional local fallback settings file, ignored by git
- `app/db/sqlany_client.py`: SQL Anywhere client
- `app/web/`: FastAPI web app (routers, templates, auth, db, models)
- `alembic/`: database migrations for web schema
- `run_web.py`: web app entry point for uvicorn
- `sql/query.sql`: deduplication query
- `TSV/`: generated files

## Reuse From Code

If you want to call the converter from another module or from a future web server, use:

```python
from app.conversion_service import convert_file

output_files = convert_file(
    input_csv="INPUT.csv",
    out_dir="TSV",
    base_name="out",
    skip_material_dedup_query=True,
)
```

`output_files` contains the generated paths for:

- material parts
- parts
- BOM
- purchase/raw
