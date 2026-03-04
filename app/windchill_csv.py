import csv
import io
from pathlib import Path


def normalize_windchill_line(line: str) -> str:
    line = line.rstrip("\r\n")
    if not line:
        return ""

    if line.startswith('"') and line.endswith('"'):
        line = line[1:-1]

    return line.replace('""', '"')


def read_windchill_csv(path: str | Path) -> tuple[list[str], list[list[str]]]:
    raw = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    normalized_lines = [normalize_windchill_line(line) for line in raw if line.strip()]
    normalized_text = "\n".join(normalized_lines) + "\n"

    reader = csv.reader(io.StringIO(normalized_text), delimiter=",", quotechar='"')
    rows = list(reader)
    if not rows:
        raise RuntimeError("Р¤Р°Р№Р» РїСѓСЃС‚РѕР№ РёР»Рё РЅРµ СѓРґР°Р»РѕСЃСЊ СЂР°СЃРїР°СЂСЃРёС‚СЊ РїРѕСЃР»Рµ РЅРѕСЂРјР°Р»РёР·Р°С†РёРё.")

    return rows[0], rows[1:]


def index_of_first(header: list[str], name: str) -> int:
    for i, column_name in enumerate(header):
        if column_name == name:
            return i
    raise KeyError(f"РќРµ РЅР°Р№РґРµРЅР° РєРѕР»РѕРЅРєР° '{name}'. Р”РѕСЃС‚СѓРїРЅС‹Рµ РєРѕР»РѕРЅРєРё: {header}")
