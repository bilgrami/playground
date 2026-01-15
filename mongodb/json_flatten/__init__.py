"""JSON flattening toolkit for data engineers and data scientists.

This package provides tools for flattening complex JSON structures,
converting them to CSV format, and ingesting them into MongoDB and Snowflake.
"""

from .csv_io import read_csv, write_csv
from .flattener import flatten_json, flatten_records

try:
    from .mongodb_io import ingest_csv_to_mongodb, query_mongodb
except ImportError:
    # pymongo not available
    pass

try:
    from .snowflake_io import (
        create_table_schema,
        ingest_csv_to_snowflake,
        query_snowflake,
    )
except ImportError:
    # snowflake-connector-python not available
    pass

__all__ = [
    "flatten_json",
    "flatten_records",
    "write_csv",
    "read_csv",
]
