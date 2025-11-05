import os
from dotenv import load_dotenv
from redis.asyncio import from_url
from fastapi import FastAPI

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")

redis = None  # global reference

async def connect_redis(app: FastAPI):
    global redis
    redis = from_url(REDIS_URL, decode_responses=True)
    # quick health check
    try:
        pong = await redis.ping()
        if pong:
            print("✅ Connected to Upstash Redis")
    except Exception as e:
        print("❌ Redis connection failed:", e)

async def disconnect_redis(app: FastAPI):
    global redis
    if redis:
        await redis.close()
        print("🛑 Redis disconnected")
