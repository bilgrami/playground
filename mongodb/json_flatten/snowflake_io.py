"""Snowflake integration for flattened JSON records.

This module provides utilities for ingesting flattened JSON records
into Snowflake data warehouse with proper schema handling and type conversion.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

try:
    import snowflake.connector
    from snowflake.connector import DictCursor
    from snowflake.connector.errors import ProgrammingError
except ImportError:
    raise ImportError(
        "snowflake-connector-python is required for Snowflake integration. "
        "Install it with: pip install snowflake-connector-python"
    )


def infer_snowflake_type(value: Any) -> str:
    """Infer Snowflake SQL type from Python value.
    
    Parameters
    ----------
    value : Any
        Python value to infer type for.
        
    Returns
    -------
    str
        Snowflake SQL type name.
    """
    if value is None:
        return "VARIANT"  # Use VARIANT for nullable fields
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int):
        return "NUMBER"
    if isinstance(value, float):
        return "FLOAT"
    if isinstance(value, str):
        # Try to detect if it's a JSON string
        if value.startswith("{") or value.startswith("["):
            try:
                json.loads(value)
                return "VARIANT"
            except (json.JSONDecodeError, ValueError):
                pass
        # Check if it looks like a date/timestamp
        if len(value) > 10 and ("T" in value or "-" in value):
            return "TIMESTAMP_NTZ"
        return "VARCHAR"
    return "VARIANT"


def create_table_schema(
    records: List[Dict[str, Any]],
    table_name: str,
    schema_name: Optional[str] = None,
) -> str:
    """Generate CREATE TABLE SQL statement from records.
    
    Parameters
    ----------
    records : List[Dict[str, Any]]
        Sample records to infer schema from.
    table_name : str
        Name of the table to create.
    schema_name : Optional[str], optional
        Schema name (default: None for default schema).
        
    Returns
    -------
    str
        CREATE TABLE SQL statement.
    """
    if not records:
        raise ValueError("Cannot create schema from empty records")
    
    # Collect all keys and infer types
    all_keys: Dict[str, str] = {}
    for record in records:
        for key, value in record.items():
            if key not in all_keys:
                all_keys[key] = infer_snowflake_type(value)
            else:
                # Use VARIANT if types conflict
                current_type = all_keys[key]
                new_type = infer_snowflake_type(value)
                if current_type != new_type:
                    all_keys[key] = "VARIANT"
    
    # Build column definitions
    columns = []
    for key, sql_type in sorted(all_keys.items()):
        # Escape column names that might be reserved keywords
        escaped_key = f'"{key}"' if not key.replace("_", "").isalnum() else key
        columns.append(f"{escaped_key} {sql_type}")
    
    schema_prefix = f"{schema_name}." if schema_name else ""
    columns_sql = ",\n    ".join(columns)
    
    return f"""CREATE TABLE IF NOT EXISTS {schema_prefix}{table_name} (
    {columns_sql}
)"""


def ingest_csv_to_snowflake(
    csv_records: List[Dict[str, Any]],
    account: str,
    user: str,
    password: str,
    warehouse: str,
    database: str,
    schema: str,
    table_name: str,
    role: Optional[str] = None,
    create_table: bool = True,
    batch_size: int = 10000,
) -> int:
    """Ingest CSV records into Snowflake table.
    
    Parameters
    ----------
    csv_records : List[Dict[str, Any]]
        Records to ingest (from CSV or flattened JSON).
    account : str
        Snowflake account identifier.
    user : str
        Snowflake username.
    password : str
        Snowflake password.
    warehouse : str
        Snowflake warehouse name.
    database : str
        Snowflake database name.
    schema : str
        Snowflake schema name.
    table_name : str
        Target table name.
    role : Optional[str], optional
        Snowflake role (default: None).
    create_table : bool, optional
        Whether to create table if it doesn't exist (default: True).
    batch_size : int, optional
        Number of rows per INSERT statement (default: 10000).
        
    Returns
    -------
    int
        Number of rows inserted.
        
    Raises
    ------
    ProgrammingError
        If Snowflake operation fails.
    ValueError
        If invalid parameters are provided.
    """
    if not csv_records:
        return 0
    
    if batch_size < 1:
        raise ValueError(f"batch_size must be positive, got {batch_size}")
    
    try:
        conn = snowflake.connector.connect(
            account=account,
            user=user,
            password=password,
            warehouse=warehouse,
            database=database,
            schema=schema,
            role=role,
        )
        
        cursor = conn.cursor()
        
        # Create table if needed
        if create_table:
            create_sql = create_table_schema(csv_records, table_name, schema)
            cursor.execute(create_sql)
        
        # Prepare data for insertion
        all_keys = sorted({key for record in csv_records for key in record.keys()})
        escaped_keys = [f'"{k}"' if not k.replace("_", "").isalnum() else k for k in all_keys]
        columns_sql = ", ".join(escaped_keys)
        
        # Insert in batches
        inserted_count = 0
        for i in range(0, len(csv_records), batch_size):
            batch = csv_records[i : i + batch_size]
            values_list = []
            
            for record in batch:
                values = []
                for key in all_keys:
                    value = record.get(key, None)
                    if value is None:
                        values.append("NULL")
                    elif isinstance(value, (int, float)):
                        values.append(str(value))
                    elif isinstance(value, bool):
                        values.append("TRUE" if value else "FALSE")
                    elif isinstance(value, str):
                        # Escape single quotes
                        escaped = value.replace("'", "''")
                        values.append(f"'{escaped}'")
                    else:
                        # Convert to JSON string for VARIANT
                        json_str = json.dumps(value).replace("'", "''")
                        values.append(f"'{json_str}'")
                
                values_list.append(f"({', '.join(values)})")
            
            insert_sql = f"""
                INSERT INTO {schema}.{table_name} ({columns_sql})
                VALUES {', '.join(values_list)}
            """
            cursor.execute(insert_sql)
            inserted_count += len(batch)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return inserted_count
        
    except ProgrammingError as e:
        raise ProgrammingError(f"Failed to ingest records into Snowflake: {e}") from e


def query_snowflake(
    account: str,
    user: str,
    password: str,
    warehouse: str,
    database: str,
    schema: str,
    query: str,
    role: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Execute SQL query against Snowflake and return results.
    
    Parameters
    ----------
    account : str
        Snowflake account identifier.
    user : str
        Snowflake username.
    password : str
        Snowflake password.
    warehouse : str
        Snowflake warehouse name.
    database : str
        Snowflake database name.
    schema : str
        Snowflake schema name.
    query : str
        SQL query to execute.
    role : Optional[str], optional
        Snowflake role (default: None).
        
    Returns
    -------
    List[Dict[str, Any]]
        Query results as list of dictionaries.
        
    Raises
    ------
    ProgrammingError
        If Snowflake operation fails.
    """
    try:
        conn = snowflake.connector.connect(
            account=account,
            user=user,
            password=password,
            warehouse=warehouse,
            database=database,
            schema=schema,
            role=role,
        )
        
        cursor: DictCursor = conn.cursor(DictCursor)
        cursor.execute(query)
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return results
        
    except ProgrammingError as e:
        raise ProgrammingError(f"Failed to query Snowflake: {e}") from e
