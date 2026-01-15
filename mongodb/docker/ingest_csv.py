"""Load a CSV file into MongoDB."""

from __future__ import annotations

import csv
import os
from typing import Any, Dict

from pymongo import MongoClient


def _infer(value: str) -> Any:
    if value == "":
        return None
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def main() -> None:
    mongo_uri = os.environ.get("MONGO_URI", "mongodb://mongo:27017")
    mongo_db = os.environ.get("MONGO_DB", "flattening")
    mongo_collection = os.environ.get("MONGO_COLLECTION", "records")
    csv_path = os.environ.get("CSV_PATH", "/data/input.csv")

    client = MongoClient(mongo_uri)
    collection = client[mongo_db][mongo_collection]

    docs: list[Dict[str, Any]] = []
    with open(csv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            docs.append({key: _infer(value) for key, value in row.items()})

    if docs:
        collection.insert_many(docs)
        print(f"Inserted {len(docs)} documents into {mongo_db}.{mongo_collection}")
    else:
        print("No records to insert")


if __name__ == "__main__":
    main()
