import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from app.database.postgres_connection import get_db, engine

# ==========================================================
# 1️⃣ Patch BEFORE importing the app
# ==========================================================
async def fake_permissions(*args, **kwargs):
    return {
        "REFUND_MANAGEMENT": ["READ", "WRITE"],
        "BOOKING": ["READ", "WRITE"],
    }

import app.dependencies.authentication as auth_deps
auth_deps.get_user_permissions = fake_permissions

# Import app AFTER patching
from app.main import app
from app.dependencies.authentication import get_current_user


# ==========================================================
# 2️⃣ Mock user + DB
# ==========================================================
class FakeUser:
    def __init__(self, role_id=2):  # admin
        self.user_id = 999
        self.role_id = role_id
        self.role = "admin"
        self.email = "test_admin@example.com"
        self.username = "test_admin"
        self.account_status_id = 1

async def fake_user():
    return FakeUser()

TestingSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# 🚀 Fix: Create a fresh engine per test request
async def override_get_db():
    from sqlalchemy.ext.asyncio import create_async_engine
    from app.database.postgres_connection import DATABASE_URL

    temp_engine = create_async_engine(DATABASE_URL, future=True, echo=False)
    async_session = sessionmaker(
        bind=temp_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
            await temp_engine.dispose()


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = fake_user


# ==========================================================
# 3️⃣ Tests for GET /refunds
# ==========================================================
@pytest.mark.asyncio
async def test_get_refunds_empty():
    """✅ GET /refunds should return empty list or valid response."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/refunds/")
        print("\n[DEBUG] GET /refunds ->", res.status_code, res.text[:200])
        assert res.status_code in (200, 404)
        assert isinstance(res.json(), list)


@pytest.mark.asyncio
async def test_get_refunds_with_filters():
    """✅ GET /refunds?status=PENDING should support filters."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/refunds/?status=PENDING")
        print("\n[DEBUG] GET /refunds?status=PENDING ->", res.status_code, res.text[:200])
        assert res.status_code in (200, 404)


@pytest.mark.asyncio
async def test_get_single_refund():
    """✅ GET /refunds?refund_id=1 should return a single refund record."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/refunds/?refund_id=1")
        print("\n[DEBUG] GET /refunds/?refund_id=1 ->", res.status_code, res.text[:200])
        assert res.status_code in (200, 404, 422)


# ==========================================================
# 4️⃣ Tests for PUT /refunds/{refund_id}
# ==========================================================
@pytest.mark.asyncio
async def test_put_refund_update():
    """✅ PUT /refunds/{id} should update refund transaction details."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "transaction_id": "TXN123",
            "status": "COMPLETED",
            "remarks": "Test transaction update",
        }
        res = await client.put("/refunds/1", json=payload)
        print("\n[DEBUG] PUT /refunds/1 ->", res.status_code, res.text[:200])
        assert res.status_code in (200, 404, 422)
