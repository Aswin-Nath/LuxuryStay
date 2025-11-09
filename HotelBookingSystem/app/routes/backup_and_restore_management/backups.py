import os
import subprocess
import asyncio
import hashlib
from datetime import datetime
from zipfile import ZipFile
from typing import Optional, Dict, List
from fastapi import APIRouter, HTTPException, status, Query, Depends

from motor.motor_asyncio import AsyncIOMotorClient
from app.dependencies.authentication import ensure_not_basic_user, get_current_user
from app.models.sqlalchemy_schemas.users import Users
from app.services.backup_restore_service.backup_service import list_backups

# ───────────────────────────────
# Configuration
# ───────────────────────────────
BACKUP_ROOT_DIR = os.getenv("POSTGRES_BACKUP_DIR", "./db_backups")
ZIP_ROOT_DIR = os.getenv("POSTGRES_ZIP_DIR", "./db_zip_backups")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "hotel_booking_system")

PG_USER = os.getenv("POSTGRES_USER", "postgres")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = os.getenv("POSTGRES_PORT", "1024")
PG_DATABASE = os.getenv("POSTGRES_DB", "hotel_booking_system")

router = APIRouter(prefix="/backups", tags=["BACKUPS"])

# Mongo client
mongo_client = AsyncIOMotorClient(MONGO_URI)
mongo_db = mongo_client[MONGO_DB_NAME]
backup_col = mongo_db["backup_data_collections"]


# ============================================================================
# 🔹 CREATE - Create a new database backup (PostgreSQL + metadata)
# ============================================================================
# ───────────────────────────────
# CREATE BACKUP (with user context)
# ───────────────────────────────
@router.post("/create", response_model=dict)
async def create_database_backup(
    snapshot_name: Optional[str] = Query(default=None, description="Name for the snapshot"),
    trigger_type: Optional[str] = Query(default="manual", description="manual or scheduled"),
    current_user: Users = Depends(get_current_user),
    _ok: bool = Depends(ensure_not_basic_user)
) -> Dict[str, str]:
    """
    Create a PostgreSQL backup (.zip), calculate checksum, and log metadata in MongoDB.
    The `initiatedBy` field is automatically set to the authenticated user's user_id.
    """

    if not PG_DATABASE:
        raise HTTPException(status_code=400, detail="POSTGRES_DB not configured in environment")

    os.makedirs(BACKUP_ROOT_DIR, exist_ok=True)
    os.makedirs(ZIP_ROOT_DIR, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    snapshot_name = snapshot_name or f"snapshot_{timestamp}"

    dump_filename = f"{snapshot_name}.dump"
    zip_filename = f"{snapshot_name}.zip"

    dump_path = os.path.join(BACKUP_ROOT_DIR, dump_filename)
    zip_path = os.path.join(ZIP_ROOT_DIR, zip_filename)

    # Construct pg_dump command
    dump_cmd = [
        "pg_dump",
        "-U", PG_USER,
        "-h", PG_HOST,
        "-p", PG_PORT,
        "-F", "c",
        "-b",
        "-v",
        "-f", dump_path,
        PG_DATABASE,
    ]

    env = os.environ.copy()
    if PG_PASSWORD:
        env["PGPASSWORD"] = PG_PASSWORD

    # Run pg_dump safely (Windows-safe)
    def run_pg_dump():
        result = subprocess.run(dump_cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(result.stderr.strip())

    await asyncio.to_thread(run_pg_dump)

    # Compress dump → zip
    try:
        with ZipFile(zip_path, "w") as zipf:
            zipf.write(dump_path, arcname=os.path.basename(dump_path))
        os.remove(dump_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to zip backup: {str(e)}")

    # Compute metadata
    size_mb = round(os.path.getsize(zip_path) / (1024 * 1024), 2)
    checksum = hashlib.sha256(open(zip_path, "rb").read()).hexdigest()
    completed_at = datetime.utcnow()

    # Insert record in Mongo
    record = {
        "snapshotName": snapshot_name,
        "initiatedBy": str(current_user.user_id),
        "triggerType": trigger_type,
        "scheduleType": None,
        "databaseType": "postgres",
        "collectionsIncluded": [],
        "storagePath": os.path.abspath(zip_path),
        "sizeMB": size_mb,
        "checksum": checksum,
        "status": "completed",
        "timestamp": completed_at,
        "completedAt": completed_at,
        "details": {
            "durationSec": 0,
            "compression": "zip",
            "retentionDays": 30,
            "verified": True
        },
    }

    try:
        result = await backup_col.insert_one(record)
        record["_id"] = str(result.inserted_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MongoDB insert failed: {str(e)}")

    return {
        "message": "Backup created successfully",
        "snapshotName": snapshot_name,
        "zipPath": os.path.abspath(zip_path),
        "sizeMB": size_mb,
        "checksum": checksum,
        "initiatedBy": current_user.user_id,
        "mongoId": record["_id"],
        "database": PG_DATABASE,
    }


# ============================================================================
# 🔹 READ - Fetch list of database backups with filters
# ============================================================================
# ───────────────────────────────
# GET BACKUPS
# ───────────────────────────────
@router.get("/", response_model=List[dict])
async def get_backups(
    snapshotName: Optional[str] = Query(None),
    triggerType: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    databaseType: Optional[str] = Query(None),
    start_ts: Optional[str] = Query(None, description="ISO datetime string (start)"),
    end_ts: Optional[str] = Query(None, description="ISO datetime string (end)"),
    limit: int = Query(50, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    _ok: bool = Depends(ensure_not_basic_user),
):
    """List backups with optional filters and pagination."""
    results = await list_backups(
        snapshotName=snapshotName,
        triggerType=triggerType,
        status=status,
        databaseType=databaseType,
        start_ts=start_ts,
        end_ts=end_ts,
        limit=limit,
        skip=skip,
    )
    return results
