# db_async.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os
import urllib.parse
load_dotenv()

user=os.getenv("POSTGRES_USER")
host=os.getenv("POSTGRES_HOST")
password=urllib.parse.quote_plus(os.getenv("POSTGRES_PASSWORD"))
db_name=os.getenv("POSTGRES_DB")

DATABASE_URL = f'postgresql+asyncpg://{user}:{password}@{host}:1024/{db_name}'

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_size=50,
    max_overflow=200,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session