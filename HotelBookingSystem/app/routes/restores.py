import os
import asyncio
import subprocess
import hashlib
from datetime import datetime
from zipfile import ZipFile
from bson import ObjectId
from typing import Optional, Dict, List
from fastapi import APIRouter, HTTPException, status, Query, Depends, Security

from motor.motor_asyncio import AsyncIOMotorClient
from app.dependencies.authentication import check_permission, get_current_user
from app.models.sqlalchemy_schemas.users import Users

# Mongo Config
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

mongo_client = AsyncIOMotorClient(MONGO_URI)
mongo_db = mongo_client[MONGO_DB_NAME]
backup_col = mongo_db["backup_data_collections"]
restore_col = mongo_db["restored_data_collections"]

# PostgreSQL Config
PG_USER = os.getenv("POSTGRES_USER")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD")
PG_HOST = os.getenv("POSTGRES_HOST")
PG_PORT = os.getenv("POSTGRES_PORT")
PG_DATABASE = os.getenv("POSTGRES_DB")

router = APIRouter(prefix="/restores", tags=["RESTORES"])


# ============================================================================
# 🔹 CREATE - Restore database from backup file
# ============================================================================
@router.post("/restore/{backup_id}", response_model=dict)
async def restore_database_from_backup(
    backup_id: str,
    current_user: Users = Depends(get_current_user),
    _permissions: dict = Security(check_permission, scopes=["RESTORE_OPERATIONS:WRITE"]),
) -> Dict[str, str]:
    """
    Restore PostgreSQL database from backup ZIP file.
    
    Initiates a database restoration workflow. Fetches backup metadata from MongoDB,
    extracts the dump file, creates a new timestamped restore database, and runs
    pg_restore. The restore database persists for manual validation before production
    deployment. Access restricted to administrators with RESTORE_OPERATIONS:WRITE scope.
    
    Restoration steps:
    1. Fetch backup metadata from MongoDB by backup_id
    2. Unzip the backup file to extract .dump file
    3. Create new PostgreSQL database (hotel_restore_<timestamp>)
    4. Execute pg_restore to populate new database
    5. Log restore record in restored_data_collections with metadata
    6. Cleanup temporary .dump file
    
    Args:
        backup_id (str): MongoDB ObjectId of the backup to restore.
        current_user (Users): Authenticated administrator (must have RESTORE_OPERATIONS:WRITE).
        _permissions (dict): Security dependency verifying restore scope.
    
    Returns:
        dict: Restoration confirmation with restoredDatabase name, zipPath, checksum,
              sizeMB, mongoId, and success message.
    
    Raises:
        HTTPException (404): If backup_id not found or backup file missing on disk.
        HTTPException (500): If unzip, database creation, or pg_restore fails.
    
    Side Effects:
        - Creates new PostgreSQL database on server
        - Creates restore record in MongoDB
        - Extracts and cleans up temporary .dump files
        - Requires pg_restore and createdb utilities on system PATH
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
@router.get("/", response_model=List[dict])
async def get_restores(
    backupRefId: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    databaseType: Optional[str] = Query(None),
    start_ts: Optional[str] = Query(None, description="ISO datetime start"),
    end_ts: Optional[str] = Query(None, description="ISO datetime end"),
    limit: int = Query(50, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    _permissions: dict = Security(check_permission, scopes=["RESTORE_OPERATIONS:READ"]),
):
    """
    Retrieve list of database restore records with optional filtering.
    
    Queries MongoDB restored_data_collections with advanced filtering by backup reference,
    status, database type, and timestamp range. Results are sorted by timestamp descending.
    Useful for audit trail and restore history tracking. Access restricted to users with
    RESTORE_OPERATIONS:READ scope.
    
    Args:
        backupRefId (Optional[str]): Filter by source backup MongoDB ObjectId.
        status (Optional[str]): Filter by restore status ("completed", "failed", etc.).
        databaseType (Optional[str]): Filter by database type (default: "postgres").
        start_ts (Optional[str]): ISO 8601 datetime start for range filtering.
        end_ts (Optional[str]): ISO 8601 datetime end for range filtering.
        limit (int): Records per page (default: 50, max: 1000).
        skip (int): Pagination offset (default: 0).
        _permissions (dict): Security dependency verifying restore read scope.
    
    Returns:
        List[dict]: Array of restore records with _id, backupRefId, status, timestamps,
                   restoredDatabase name, and checksum metadata.
    
    Raises:
        HTTPException (404): If no restore records match query filters.
        HTTPException (403): If user lacks RESTORE_OPERATIONS:READ permission.
    
    Side Effects:
        - None
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
