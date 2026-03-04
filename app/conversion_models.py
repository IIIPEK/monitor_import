from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConversionOutputFiles:
    material_parts: Path
    parts: Path
    bom: Path
    purchase_raw: Path


@dataclass(frozen=True)
class ConversionTables:
    parts: list[list[str]]
    bom: list[list[str]]
    purchase_raw: list[list[str]]
    material_parts: list[list[str]]
