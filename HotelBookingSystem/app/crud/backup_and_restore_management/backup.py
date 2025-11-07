from typing import Any, Dict, List, Optional
from datetime import datetime
from pymongo import DESCENDING
from app.database.mongo_connnection import get_database


# ==========================================================
# 🔹 CREATE BACKUP ENTRY
# ==========================================================

async def insert_backup_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a backup record and return the inserted document."""
    db = get_database()
    collection = db.backup_data_collections
    result = await collection.insert_one(payload)
    inserted = await collection.find_one({"_id": result.inserted_id})
    return inserted


# ==========================================================
# 🔹 FETCH BACKUPS
# ==========================================================

async def fetch_backup_records(
    snapshotName: Optional[str] = None,
    triggerType: Optional[str] = None,
    status: Optional[str] = None,
    databaseType: Optional[str] = None,
    start_ts: Optional[str] = None,
    end_ts: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
) -> List[Dict[str, Any]]:
    """Retrieve backup records from MongoDB based on filters."""
    db = get_database()
    collection = db.backup_data_collections
    filt: Dict[str, Any] = {}

    if snapshotName:
        filt["snapshotName"] = {"$regex": snapshotName, "$options": "i"}
    if triggerType:
        filt["triggerType"] = triggerType
    if status:
        filt["status"] = status
    if databaseType:
        filt["databaseType"] = databaseType

    # Timestamp range filter
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
        .sort("timestamp", DESCENDING)
        .skip(int(skip))
        .limit(int(limit))
    )

    results = []
    async for doc in cursor:
        results.append(doc)
    return results
