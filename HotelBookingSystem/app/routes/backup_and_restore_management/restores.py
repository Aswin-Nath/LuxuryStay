import os
import asyncio
import subprocess
import hashlib
from datetime import datetime
from zipfile import ZipFile
from bson import ObjectId
from typing import Optional, Dict, List
from fastapi import APIRouter, HTTPException, status, Query, Depends

from motor.motor_asyncio import AsyncIOMotorClient
from app.dependencies.authentication import ensure_not_basic_user, get_current_user
from app.models.sqlalchemy_schemas.users import Users

# Mongo Config
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "hotel_booking_system")

mongo_client = AsyncIOMotorClient(MONGO_URI)
mongo_db = mongo_client[MONGO_DB_NAME]
backup_col = mongo_db["backup_data_collections"]
restore_col = mongo_db["restored_data_collections"]

# PostgreSQL Config
PG_USER = os.getenv("POSTGRES_USER", "postgres")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = os.getenv("POSTGRES_PORT", "1024")
PG_DATABASE = os.getenv("POSTGRES_DB", "hotel_booking_system")

router = APIRouter(prefix="/restores", tags=["RESTORES"])


# ============================================================================
# 🔹 CREATE - Restore database from backup file
# ============================================================================
# ───────────────────────────────
# POST: RESTORE DATABASE
# ───────────────────────────────
@router.post("/restore/{backup_id}", response_model=dict)
async def restore_database_from_backup(
    backup_id: str,
    current_user: Users = Depends(get_current_user),
    _ok: bool = Depends(ensure_not_basic_user),
) -> Dict[str, str]:
    """
    Restore PostgreSQL database from backup ZIP file.
    Steps:
      1. Fetch backup metadata from MongoDB.
      2. Unzip the .zip to extract .dump file.
      3. Create a new restore DB (hotel_restore_<timestamp>).
      4. Run pg_restore into it.
      5. Log the restore details in restored_data_collections.
    """

    # Step 1: Fetch backup record
    backup = await backup_col.find_one({"_id": ObjectId(backup_id)})
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")

    zip_path = backup.get("storagePath")
    if not zip_path or not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="Backup file missing on disk")

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    restore_db_name = f"{PG_DATABASE}_restore_{timestamp}"
    dump_extract_path = zip_path.replace(".zip", ".dump")

    # Step 2: Extract .dump file
    try:
        with ZipFile(zip_path, "r") as zipf:
            zipf.extractall(os.path.dirname(zip_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unzip backup: {str(e)}")

    # Step 3: Create new database
    create_db_cmd = [
        "createdb",
        "-U", PG_USER,
        "-h", PG_HOST,
        "-p", PG_PORT,
        restore_db_name,
    ]
    env = os.environ.copy()
    if PG_PASSWORD:
        env["PGPASSWORD"] = PG_PASSWORD

    def run_createdb():
        result = subprocess.run(create_db_cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(result.stderr.strip())

    await asyncio.to_thread(run_createdb)

    # Step 4: Restore .dump file
    restore_cmd = [
        "pg_restore",
        "-U", PG_USER,
        "-h", PG_HOST,
        "-p", PG_PORT,
        "-d", restore_db_name,
        "-v",
        dump_extract_path,
    ]

    def run_pg_restore():
        result = subprocess.run(restore_cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(result.stderr.strip())

    await asyncio.to_thread(run_pg_restore)

    # Step 5: Compute metadata
    checksum = hashlib.sha256(open(zip_path, "rb").read()).hexdigest()
    size_mb = round(os.path.getsize(zip_path) / (1024 * 1024), 2)
    completed_at = datetime.utcnow()

    # Step 6: Cleanup temp .dump file
    try:
        os.remove(dump_extract_path)
    except Exception:
        pass

    # Step 7: Log restore record
    restore_record = {
        "backupRefId": str(backup_id),
        "initiatedBy": str(current_user.user_id),
        "databaseType": "postgres",
        "restoredDatabase": restore_db_name,
        "sourcePath": zip_path,
        "sizeMB": size_mb,
        "checksum": checksum,
        "status": "completed",
        "timestamp": completed_at,
        "completedAt": completed_at,
        "details": {
            "durationSec": 0,
            "compression": "zip",
            "verified": True
        },
    }

    try:
        result = await restore_col.insert_one(restore_record)
        restore_record["_id"] = str(result.inserted_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log restore: {str(e)}")

    return {
        "message": "Database restored successfully",
        "restoredDatabase": restore_db_name,
        "backupRefId": backup_id,
        "zipPath": zip_path,
        "checksum": checksum,
        "sizeMB": size_mb,
        "mongoId": restore_record["_id"],
    }


# ============================================================================
# 🔹 READ - Fetch list of database restore records
# ============================================================================
# ───────────────────────────────
# GET: LIST RESTORES
# ───────────────────────────────
@router.get("/", response_model=List[dict])
async def get_restores(
    backupRefId: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    databaseType: Optional[str] = Query(None),
    start_ts: Optional[str] = Query(None, description="ISO datetime start"),
    end_ts: Optional[str] = Query(None, description="ISO datetime end"),
    limit: int = Query(50, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    _ok: bool = Depends(ensure_not_basic_user),
):
    """
    Fetch list of restore records from MongoDB with optional filters.
    """

    query = {}

    if backupRefId:
        query["backupRefId"] = backupRefId
    if status:
        query["status"] = status
    if databaseType:
        query["databaseType"] = databaseType
    if start_ts and end_ts:
        query["timestamp"] = {
            "$gte": datetime.fromisoformat(start_ts),
            "$lte": datetime.fromisoformat(end_ts)
        }

    cursor = restore_col.find(query).sort("timestamp", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=None)

    for doc in docs:
        doc["_id"] = str(doc["_id"])
        doc["timestamp"] = doc["timestamp"].isoformat() if doc.get("timestamp") else None
        doc["completedAt"] = doc["completedAt"].isoformat() if doc.get("completedAt") else None

    if not docs:
        raise HTTPException(status_code=404, detail="No restore records found")

    return docs
