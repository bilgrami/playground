"""Command-line interface for JSON flattening."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from .csv_io import write_csv
from .flattener import flatten_json, flatten_records


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input", required=True, type=Path, help="Path to JSON input")
    parser.add_argument("--output", required=True, type=Path, help="Path to output CSV/JSON")
    parser.add_argument("--sep", default=".", help="Key separator")
    parser.add_argument("--list-policy", default="index", choices=["index", "join"], help="List handling")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Flatten JSON to CSV or JSON.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    flat_parser = subparsers.add_parser("flatten", help="Flatten into a single record")
    _add_common_args(flat_parser)

    records_parser = subparsers.add_parser("records", help="Explode arrays into records")
    _add_common_args(records_parser)
    records_parser.add_argument("--explode", action="append", default=[], help="List path to explode")

    args = parser.parse_args(argv)
    data = _load_json(args.input)

    if args.command == "flatten":
        record = flatten_json(data, sep=args.sep, list_policy=args.list_policy)
        if args.output.suffix.lower() == ".csv":
            write_csv([record], args.output)
        else:
            _write_json(args.output, record)
        return 0

    records = flatten_records(
        data,
        explode_paths=args.explode,
        sep=args.sep,
        list_policy=args.list_policy,
    )
    if args.output.suffix.lower() == ".csv":
        write_csv(records, args.output)
    else:
        _write_json(args.output, records)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
