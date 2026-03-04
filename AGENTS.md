# Project Context

## Purpose

This project converts a Windchill multi-level BOM CSV export into Monitor ERP import files with `.csv` extension and TAB delimiter.
The codebase is already split into CLI, service, transform, parsing, and SQL adapter modules to support future migration to a web service.

The current workflow produces:

- `_00_material_parts.csv`: material master rows from `Material Number` + `Material Description`
- `_01_parts.csv`: parts from `Number` + `Name`
- `_02_bom.csv`: BOM structure from `Structure Level`
- `_03_purchase_raw.csv`: purchase/raw rows with `Qty Of Raw Material` based on summed `Model Weight`

## Current SQL Anywhere Usage

- SQL Anywhere connection settings are loaded through `app/config.py`
- `app/config.py` first loads optional `.env`, then can use optional local fallback values from `app/conf.py`
- The SQL file path is taken from `QUERY_FILE`
- `sql/query.sql` is expected to return existing material or part numbers from Monitor
- `app/material_dedup.py` loads existing numbers from SQL Anywhere or from an exported file
- `app/conversion_service.py` uses that result to exclude already existing `Material Number` values from `_00_material_parts.csv`
- Deduplication of SQL result rows is done in Python via `set()`

## Important Files

- `convert.py`: thin CLI entry point
- `app/conversion_cli.py`: CLI parser and console output
- `app/conversion_service.py`: orchestration layer used by CLI and future web/API entry points
- `app/conversion_transform.py`: main conversion logic
- `app/conversion_models.py`: dataclasses for outputs
- `app/windchill_csv.py`: Windchill CSV normalization and parsing
- `app/formatting.py`: helper functions for text and decimal formatting
- `app/material_dedup.py`: loading existing material numbers from DB or export file
- `app/config.py`: SQL Anywhere settings loader
- `app/conf.py`: optional local fallback settings file for credentials, ignored by git
- `app/db/sqlany_client.py`: SQL Anywhere client and query-file execution
- `sql/query.sql`: query used to fetch existing material numbers
- `.env`: local SQL Anywhere credentials and query file path

## Data Assumptions

- Windchill CSV lines are wrapped in outer quotes and use doubled quotes inside
- The first `Quantity` column is BOM quantity
- `Model Weight` may contain `kg` suffix and is parsed as decimal
- `_03_purchase_raw.csv` must contain weight, not BOM quantity
- `_00_material_parts.csv` must keep `Weight per item` empty

## Practical Notes

- SQL-related imports are kept inside `app/material_dedup.py` functions so conversion can still run without DB dependencies when using `--skip-material-dedup-query`
- If SQL Anywhere dependencies are installed and settings are valid, the default path is to query the server before generating `_00_material_parts.csv`
- `app/conf.py` is optional and should not be committed; `.gitignore` excludes it
- If needed, existing material numbers can be loaded from an exported query result file using `--existing-materials-file`
- For future web-server migration, prefer reusing `app.conversion_service.convert_file()` instead of duplicating CLI logic

## Typical Run

With SQL dedup:

```bash
python3 convert.py 2058600_Energy_Storage_Unit_FREEN-BSL-N_0.24_multiLevelBOM_2025-02-26.csv --out-dir TSV --base-name out
```

Without SQL dedup:

```bash
python3 convert.py 2058600_Energy_Storage_Unit_FREEN-BSL-N_0.24_multiLevelBOM_2025-02-26.csv --out-dir TSV --base-name out --skip-material-dedup-query
```
