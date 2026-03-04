import re
from collections import defaultdict
from decimal import Decimal

from app.conversion_models import ConversionTables
from app.formatting import cut_50_by_space, dec_to_comma_str, parse_decimal_any
from app.windchill_csv import index_of_first


def build_outputs(
    header: list[str],
    data: list[list[str]],
    existing_material_numbers: set[str] | None = None,
) -> ConversionTables:
    i_level = index_of_first(header, "Structure Level")
    i_number = index_of_first(header, "Number")
    i_name = index_of_first(header, "Name")
    i_qty = index_of_first(header, "Quantity")
    i_region = index_of_first(header, "Region")
    i_weight = index_of_first(header, "Model Weight")
    i_matno = index_of_first(header, "Material Number")
    i_matdesc = index_of_first(header, "Material Description")

    parts: dict[str, dict[str, str]] = {}
    material_parts: dict[str, dict[str, str]] = {}
    bom_rows: list[list[str]] = []
    level_stack: dict[int, str] = {}
    raw_weight_sum: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    region_set: dict[str, set[str]] = defaultdict(set)
    matno_set: dict[str, set[str]] = defaultdict(set)

    header_length = len(header)
    existing_material_numbers = existing_material_numbers or set()

    for row in data:
        if len(row) < header_length:
            row = row + [""] * (header_length - len(row))

        part_no = (row[i_number] or "").strip()
        if not part_no:
            continue

        name_full = (row[i_name] or "").strip()
        weight_raw = (row[i_weight] or "").strip()
        qty_raw = (row[i_qty] or "").strip()
        region = (row[i_region] or "").strip()
        matno = (row[i_matno] or "").strip()
        matdesc = (row[i_matdesc] or "").strip()
        level_raw = (row[i_level] or "").strip()

        if part_no not in parts:
            weight = parse_decimal_any(weight_raw)
            parts[part_no] = {
                "Part Number": part_no,
                "Part Name": cut_50_by_space(name_full, 50),
                "Additional Name For Part In Monitor": name_full,
                "Weight per item": dec_to_comma_str(weight),
            }

        if matno and matno not in existing_material_numbers and matno not in material_parts:
            material_parts[matno] = {
                "Part Number": matno,
                "Part Name": cut_50_by_space(matdesc, 50),
                "Additional Name For Part In Monitor": matdesc,
                "Weight per item": "",
            }

        try:
            level = int(re.sub(r"[^\d-]", "", level_raw)) if level_raw else 0
        except ValueError:
            level = 0

        level_stack[level] = part_no
        for key in list(level_stack.keys()):
            if key > level:
                del level_stack[key]

        if level == 0:
            bom_rows.append(["", part_no, "1"])
        else:
            parent = level_stack.get(level - 1, "")
            qty = parse_decimal_any(qty_raw) or Decimal("0")
            bom_rows.append([parent, part_no, dec_to_comma_str(qty)])

        raw_weight = parse_decimal_any(weight_raw) or Decimal("0")
        raw_weight_sum[part_no] += raw_weight
        if region:
            region_set[part_no].add(region)
        if matno:
            matno_set[part_no].add(matno)

    parts_rows = [["Part Number", "Part Name", "Additional Name For Part In Monitor", "Weight per item"]]
    for part_no in sorted(parts.keys()):
        part = parts[part_no]
        parts_rows.append(
            [
                part["Part Number"],
                part["Part Name"],
                part["Additional Name For Part In Monitor"],
                part["Weight per item"],
            ]
        )

    bom_table = [["New Parent Name", "Child", "Count"], *bom_rows]

    purchase_raw_rows = [["Part Number", "Purchase type", "Material part No", "Qty Of Raw Material"]]
    for part_no in sorted(raw_weight_sum.keys()):
        purchase_type = " | ".join(sorted(region_set.get(part_no, set())))
        material_no = " | ".join(sorted(matno_set.get(part_no, set())))
        purchase_raw_rows.append([part_no, purchase_type, material_no, dec_to_comma_str(raw_weight_sum[part_no])])

    material_parts_rows = [["Part Number", "Part Name", "Additional Name For Part In Monitor", "Weight per item"]]
    for part_no in sorted(material_parts.keys()):
        part = material_parts[part_no]
        material_parts_rows.append(
            [
                part["Part Number"],
                part["Part Name"],
                part["Additional Name For Part In Monitor"],
                part["Weight per item"],
            ]
        )

    return ConversionTables(
        parts=parts_rows,
        bom=bom_table,
        purchase_raw=purchase_raw_rows,
        material_parts=material_parts_rows,
    )
