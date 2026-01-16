"""MongoDB integration for flattened JSON records.

This module provides utilities for ingesting flattened JSON records
into MongoDB collections with proper type inference and error handling.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pymongo import MongoClient
    from pymongo.collection import Collection
    from pymongo.database import Database
    from pymongo.errors import PyMongoError
except ImportError:
    raise ImportError(
        "pymongo is required for MongoDB integration. "
        "Install it with: pip install pymongo"
    )


def infer_type(value: str) -> Any:
    """Infer Python type from string value.
    
    Attempts to convert string values to appropriate Python types:
    - Empty strings -> None
    - "true"/"false" -> bool
    - Numbers -> int or float
    - Everything else -> str
    
    Parameters
    ----------
    value : str
        String value to infer type for.
        
    Returns
    -------
    Any
        Inferred value (None, bool, int, float, or str).
    """
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


def ingest_csv_to_mongodb(
    csv_records: List[Dict[str, Any]],
    mongo_uri: str = "mongodb://localhost:27017",
    database_name: str = "flattening",
    collection_name: str = "records",
    batch_size: int = 1000,
    drop_collection: bool = False,
) -> int:
    """Ingest CSV records into MongoDB collection.
    
    Parameters
    ----------
    csv_records : List[Dict[str, Any]]
        Records to ingest (from CSV or flattened JSON).
    mongo_uri : str, optional
        MongoDB connection URI (default: "mongodb://localhost:27017").
    database_name : str, optional
        Database name (default: "flattening").
    collection_name : str, optional
        Collection name (default: "records").
    batch_size : int, optional
        Number of documents to insert per batch (default: 1000).
    drop_collection : bool, optional
        Whether to drop existing collection before insert (default: False).
        
    Returns
    -------
    int
        Number of documents inserted.
        
    Raises
    ------
    PyMongoError
        If MongoDB operation fails.
    ValueError
        If invalid parameters are provided.
    """
    if not csv_records:
        return 0
    
    if batch_size < 1:
        raise ValueError(f"batch_size must be positive, got {batch_size}")
    
    try:
        client: MongoClient = MongoClient(mongo_uri)
        db: Database = client[database_name]
        collection: Collection = db[collection_name]
        
        if drop_collection:
            collection.drop()
        
        # Convert string values to appropriate types
        documents: List[Dict[str, Any]] = []
        for record in csv_records:
            doc = {
                key: infer_type(value) if isinstance(value, str) else value
                for key, value in record.items()
            }
            documents.append(doc)
        
        # Insert in batches
        inserted_count = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            result = collection.insert_many(batch)
            inserted_count += len(result.inserted_ids)
        
        client.close()
        return inserted_count
        
    except PyMongoError as e:
        raise PyMongoError(f"Failed to ingest records into MongoDB: {e}") from e


def query_mongodb(
    mongo_uri: str = "mongodb://localhost:27017",
    database_name: str = "flattening",
    collection_name: str = "records",
    filter_dict: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Query MongoDB collection and return results.
    
    Parameters
    ----------
    mongo_uri : str, optional
        MongoDB connection URI (default: "mongodb://localhost:27017").
    database_name : str, optional
        Database name (default: "flattening").
    collection_name : str, optional
        Collection name (default: "records").
    filter_dict : Optional[Dict[str, Any]], optional
        MongoDB filter query (default: None for all documents).
    limit : Optional[int], optional
        Maximum number of documents to return (default: None for no limit).
        
    Returns
    -------
    List[Dict[str, Any]]
        List of documents matching the query.
        
    Raises
    ------
    PyMongoError
        If MongoDB operation fails.
    """
    try:
        client: MongoClient = MongoClient(mongo_uri)
        db: Database = client[database_name]
        collection: Collection = db[collection_name]
        
        cursor = collection.find(filter_dict or {})
        if limit:
            cursor = cursor.limit(limit)
        
        results = list(cursor)
        client.close()
        return results
        
    except PyMongoError as e:
        raise PyMongoError(f"Failed to query MongoDB: {e}") from e
