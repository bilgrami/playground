"""CSV helpers for flattened records.

This module provides utilities for reading and writing CSV files
from flattened JSON records.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def write_csv(
    records: Iterable[Dict[str, Any]],
    output_path: Path | str,
    delimiter: str = ",",
    encoding: str = "utf-8",
) -> None:
    """Write records to CSV with a union of all keys as headers.
    
    Parameters
    ----------
    records : Iterable[Dict[str, Any]]
        Records to write. Each dict represents a row.
    output_path : Path | str
        Path to output CSV file.
    delimiter : str, optional
        CSV delimiter (default: ",").
    encoding : str, optional
        File encoding (default: "utf-8").
        
    Raises
    ------
    OSError
        If the file cannot be written.
    """
    if isinstance(output_path, str):
        output_path = Path(output_path)
        
    rows = list(records)
    if not rows:
        # Write empty CSV with no headers
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("", encoding=encoding)
        return
    
    keys: List[str] = sorted({key for row in rows for key in row.keys()})

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding=encoding) as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, delimiter=delimiter)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in keys})


def read_csv(
    input_path: Path | str,
    delimiter: str = ",",
    encoding: str = "utf-8",
) -> List[Dict[str, Any]]:
    """Read CSV file into list of dictionaries.
    
    Parameters
    ----------
    input_path : Path | str
        Path to input CSV file.
    delimiter : str, optional
        CSV delimiter (default: ",").
    encoding : str, optional
        File encoding (default: "utf-8").
        
    Returns
    -------
    List[Dict[str, Any]]
        List of dictionaries, one per row.
        
    Raises
    ------
    FileNotFoundError
        If the file doesn't exist.
    OSError
        If the file cannot be read.
    """
    if isinstance(input_path, str):
        input_path = Path(input_path)
        
    if not input_path.exists():
        raise FileNotFoundError(f"CSV file not found: {input_path}")
    
    records: List[Dict[str, Any]] = []
    with input_path.open("r", newline="", encoding=encoding) as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        records = list(reader)
    
    return records
