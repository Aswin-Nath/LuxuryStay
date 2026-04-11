from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
load_dotenv()


MONGO_URL = os.getenv("MONGO_URL")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

if not MONGO_URL or not MONGO_DB_NAME:
    raise ValueError("Mongo env vars not set")

# Connection with proper timeouts to avoid 30-second delays
client = AsyncIOMotorClient(
    MONGO_URL,
    serverSelectionTimeoutMS=5000,      # 5 seconds instead of 30
    socketTimeoutMS=10000,               # 10 seconds for socket operations
    connectTimeoutMS=5000,               # 5 seconds to connect
    maxPoolSize=50,                      # Connection pool size
    minPoolSize=10,                      # Minimum connections
    retryWrites=True,
    retryReads=True
)

database = client[MONGO_DB_NAME]

def get_database():
    return database