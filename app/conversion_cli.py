import argparse
import os

from app.conversion_service import convert_file


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv", help="Windchill export CSV path")
    parser.add_argument("--out-dir", default=".", help="Output directory")
    parser.add_argument("--base-name", default=None, help="Base name for outputs (default: input file stem)")
    parser.add_argument("--env-file", default=".env", help="Env file with SQL Anywhere settings")
    parser.add_argument(
        "--existing-materials-file",
        default=None,
        help="CSV export of existing materials from query.sql (semicolon-delimited, first column = material number)",
    )
    parser.add_argument(
        "--skip-material-dedup-query",
        action="store_true",
        help="Do not query SQL Anywhere for existing Material Number values before generating material parts TSV",
    )
    parser.add_argument(
        "--debug-check-columns",
        action="store_true",
        help="Print a warning if some data rows have different column count than header after parsing",
    )
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    output_files = convert_file(
        input_csv=args.input_csv,
        out_dir=args.out_dir,
        base_name=args.base_name,
        env_file=args.env_file,
        existing_materials_file=args.existing_materials_file,
        skip_material_dedup_query=args.skip_material_dedup_query,
        debug_check_columns=args.debug_check_columns,
    )

    print("OK:")
    print(" -", os.fspath(output_files.parts))
    print(" -", os.fspath(output_files.bom))
    print(" -", os.fspath(output_files.purchase_raw))
    print(" -", os.fspath(output_files.material_parts))
