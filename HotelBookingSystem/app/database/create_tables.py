import asyncio
from app.database.postgres_connection import engine, Base

# ✅ Import *all* models here to register them with Base.metadata
from app.models.sqlalchemy_schemas import (
    authentication,
    bookings,
    images,
        reviews,
    offers,
    permissions,
    roles,
    rooms,
    status_utility,
    users,
    tax_utility,
    issues,
    payment_method,
    payments,
    notifications,
    refunds,
)

async def init_models():
    async with engine.begin() as conn:
        # Drop this line if you don’t want to recreate tables each time
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init_models())
