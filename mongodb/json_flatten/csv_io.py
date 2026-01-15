"""CSV helpers for flattened records."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, Iterable, List


def write_csv(records: Iterable[Dict[str, Any]], output_path: Path) -> None:
    """Write records to CSV with a union of all keys as headers."""
    rows = list(records)
    keys: List[str] = sorted({key for row in rows for key in row.keys()})

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in keys})
