import csv
from pathlib import Path

from app.conversion_models import ConversionOutputFiles
from app.conversion_transform import build_outputs
from app.material_dedup import (
    fetch_existing_material_numbers,
    fetch_existing_material_numbers_from_file,
)
from app.windchill_csv import read_windchill_csv


def write_tab_csv(path: str | Path, rows: list[list[str]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.writer(file_obj, delimiter="\t", quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerows(rows)


def resolve_output_files(
    input_csv: str | Path,
    out_dir: str | Path = ".",
    base_name: str | None = None,
) -> ConversionOutputFiles:
    input_path = Path(input_csv)
    output_dir = Path(out_dir)
    base = base_name or input_path.stem

    return ConversionOutputFiles(
        material_parts=output_dir / f"{base}_00_material_parts.csv",
        parts=output_dir / f"{base}_01_parts.csv",
        bom=output_dir / f"{base}_02_bom.csv",
        purchase_raw=output_dir / f"{base}_03_purchase_raw.csv",
    )


def load_existing_material_numbers(
    env_file: str,
    existing_materials_file: str | None = None,
    skip_material_dedup_query: bool = False,
) -> set[str]:
    if existing_materials_file:
        return fetch_existing_material_numbers_from_file(existing_materials_file)
    if skip_material_dedup_query:
        return set()
    return fetch_existing_material_numbers(env_file)


def validate_column_counts(data: list[list[str]], header: list[str]) -> None:
    header_length = len(header)
    bad_rows = 0
    for idx, row in enumerate(data, start=2):
        if len(row) != header_length:
            bad_rows += 1
            if bad_rows <= 10:
                print(f"WARNING: row #{idx} has {len(row)} cols, header has {header_length}")
    if bad_rows:
        print(f"WARNING: total rows with mismatched columns: {bad_rows}")


def convert_file(
    input_csv: str | Path,
    out_dir: str | Path = ".",
    base_name: str | None = None,
    env_file: str = ".env",
    existing_materials_file: str | None = None,
    skip_material_dedup_query: bool = False,
    debug_check_columns: bool = False,
) -> ConversionOutputFiles:
    header, data = read_windchill_csv(input_csv)
    existing_material_numbers = load_existing_material_numbers(
        env_file=env_file,
        existing_materials_file=existing_materials_file,
        skip_material_dedup_query=skip_material_dedup_query,
    )

    if debug_check_columns:
        validate_column_counts(data, header)

    tables = build_outputs(header, data, existing_material_numbers=existing_material_numbers)
    output_files = resolve_output_files(input_csv=input_csv, out_dir=out_dir, base_name=base_name)

    write_tab_csv(output_files.parts, tables.parts)
    write_tab_csv(output_files.bom, tables.bom)
    write_tab_csv(output_files.purchase_raw, tables.purchase_raw)
    write_tab_csv(output_files.material_parts, tables.material_parts)

    return output_files
