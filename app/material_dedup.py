import csv
from pathlib import Path


def fetch_existing_material_numbers(env_file: str) -> set[str]:
    from app.config import load_settings
    from app.db.sqlany_client import SQLAnyDBClient

    settings = load_settings(env_file)
    with SQLAnyDBClient(settings) as client:
        _, rows = client.query_select_from_file()

    existing_numbers: set[str] = set()
    for row in rows:
        if not row:
            continue
        material_no = str(row[0]).strip()
        if material_no:
            existing_numbers.add(material_no)
    return existing_numbers


def fetch_existing_material_numbers_from_file(path: str | Path) -> set[str]:
    existing_numbers: set[str] = set()
    with Path(path).open("r", encoding="utf-8", errors="replace", newline="") as file_obj:
        reader = csv.reader(file_obj, delimiter=";")
        next(reader, None)
        for row in reader:
            if not row:
                continue
            material_no = row[0].strip().strip("'").strip()
            if material_no:
                existing_numbers.add(material_no)
    return existing_numbers
