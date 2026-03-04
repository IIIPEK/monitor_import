import re
from decimal import Decimal, InvalidOperation


def cut_50_by_space(s: str, limit: int = 50) -> str:
    s = (s or "").strip()
    if len(s) <= limit:
        return s

    chunk = s[:limit]
    if " " in chunk:
        cut = chunk.rsplit(" ", 1)[0].rstrip()
        return cut if cut else chunk
    return chunk


def parse_decimal_any(s: str) -> Decimal | None:
    if s is None:
        return None

    s = s.strip()
    if not s:
        return None

    s = re.sub(r"(?i)\s*-\s*kg\s*$", "", s)
    s = re.sub(r"(?i)\s*kg\s*$", "", s)
    s = s.strip()

    match = re.search(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", s)
    if not match:
        return None

    num = match.group(0)
    try:
        return Decimal(num)
    except InvalidOperation:
        try:
            return Decimal(str(float(num)))
        except Exception:
            return None


def dec_to_comma_str(d: Decimal | None) -> str:
    if d is None:
        return ""

    try:
        s = format(d, "f")
    except Exception:
        s = str(d)

    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s.replace(".", ",")
