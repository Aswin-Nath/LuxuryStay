from __future__ import with_statement
import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool
from alembic import context

from app.database.postgres_connection import Base  # import your metadata (Base = declarative_base())
from app.database.postgres_connection import DATABASE_URL  # if you store DB URL in your config/env loader

# ----------------------------------------------------------------------
# Alembic Config setup
# ----------------------------------------------------------------------
config = context.config
fileConfig(config.config_file_name)

# Point Alembic to your SQLAlchemy models' metadata
target_metadata = Base.metadata

# ----------------------------------------------------------------------
# Get database URL dynamically (preferred for .env)
# ----------------------------------------------------------------------
def get_url():
    return DATABASE_URL  # e.g. postgresql+asyncpg://postgres:aswinnath%40123@localhost:5432/hotel_booking_system


# ----------------------------------------------------------------------
# Offline migrations (no DB connection)
# ----------------------------------------------------------------------
def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ----------------------------------------------------------------------
# Online (async) migrations
# ----------------------------------------------------------------------
async def run_migrations_online():
    """Run migrations in 'online' mode with async engine."""
    connectable = create_async_engine(get_url(), poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


# ----------------------------------------------------------------------
# Entrypoint
# ----------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
