from typing import Any, Dict, List, Optional
from datetime import datetime
from app.database.mongo_connnection import get_database


# ==========================================================
# 🔹 CREATE RESTORE ENTRY
# ==========================================================

async def insert_restore_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a new restore record into MongoDB."""
    db = get_database()
    collection = db.restored_data_collections
    result = await collection.insert_one(payload)
    inserted = await collection.find_one({"_id": result.inserted_id})
    return inserted


# ==========================================================
# 🔹 LIST RESTORE RECORDS
# ==========================================================

async def fetch_restore_records(
    backupRefId: Optional[str] = None,
    status: Optional[str] = None,
    databaseType: Optional[str] = None,
    start_ts: Optional[str] = None,
    end_ts: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
) -> List[Dict[str, Any]]:
    """Retrieve restore records based on filters."""
    db = get_database()
    collection = db.restored_data_collections

    filt: Dict[str, Any] = {}
    if backupRefId:
        filt["backupRefId"] = backupRefId
    if status:
        filt["status"] = status
    if databaseType:
        filt["databaseType"] = databaseType

    # Optional time range filter
    if start_ts or end_ts:
        ts_filter: Dict[str, Any] = {}
        try:
            if start_ts:
                ts_filter["$gte"] = datetime.fromisoformat(start_ts)
            if end_ts:
                ts_filter["$lte"] = datetime.fromisoformat(end_ts)
        except Exception:
            ts_filter = {}
        if ts_filter:
            filt["timestamp"] = ts_filter

    cursor = (
        collection.find(filt)
        .sort("timestamp", -1)
        .skip(int(skip))
        .limit(int(limit))
    )

    results = []
    async for doc in cursor:
        results.append(doc)
    return results
