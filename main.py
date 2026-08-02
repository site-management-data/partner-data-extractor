from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

from partner_extractor.config import get_settings
from partner_extractor.sources import load_sources
from partner_extractor.transform import filter_partner_data
from partner_extractor.workbook import write_workbook


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a partner-specific Excel data extract from Zite reports."
    )
    parser.add_argument(
        "--local-dir",
        type=Path,
        help=(
            "Use raw Excel exports in this directory instead of downloading "
            "the configured Zite report URLs."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()

    try:
        raw = load_sources(settings, args.local_dir)
        sheets = filter_partner_data(raw, settings)
        output = write_workbook(sheets, settings)
    except (requests.RequestException, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Created: {output.resolve()}")
    for name, dataframe in sheets.items():
        print(f"  {name}: {len(dataframe):,} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
