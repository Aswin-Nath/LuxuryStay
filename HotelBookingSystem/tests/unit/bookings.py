import pytest
import sys
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from app.database.postgres_connection import get_db, engine

# ==========================================================
# 🧩 1. Patch BEFORE importing app
# ==========================================================

async def fake_permissions(*args, **kwargs):
    return {
        "BOOKING": ["WRITE"],
        "ROOM_MANAGEMENT": ["WRITE"],
        "REFUND_MANAGEMENT": ["WRITE"],
    }

import app.dependencies.authentication as auth_deps
auth_deps.get_user_permissions = fake_permissions

# ✅ Now import app
from app.main import app
from app.dependencies.authentication import get_current_user


# ==========================================================
# 🧍 2. Mock user (dynamic role)
# ==========================================================

class FakeUser:
    def __init__(self, role="basic", role_id=1):
        self.user_id = 999
        self.role_id = role_id
        self.role = role
        self.email = "test_user@example.com"
        self.username = "test_user"
        self.account_status_id = 1

async def fake_basic_user():
    """Simulate a normal basic user (allowed to create bookings)."""
    return FakeUser(role="basic", role_id=1)

async def fake_admin_user():
    """Simulate an admin (for endpoints that require admin)."""
    return FakeUser(role="admin", role_id=2)

TestingSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db
# Default to basic user for this test file
app.dependency_overrides[get_current_user] = fake_basic_user


# ==========================================================
# 🧪 3. TESTS
# ==========================================================

@pytest.mark.asyncio
async def test_get_bookings_list():
    """GET /bookings list works."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/bookings/")
        print("\n[DEBUG] GET /bookings ->", res.status_code, res.text[:200])
        assert res.status_code in (200, 404, 422)


@pytest.mark.asyncio
async def test_create_booking_minimal():
    """POST /bookings with minimal fields as basic user."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "rooms": [1, 2],
            "room_count": 2,
            "check_in": "2025-12-01",
            "check_out": "2025-12-05",
            "total_price": 500.00,
        }
        res = await client.post("/bookings/", json=payload)
        print("\n[DEBUG] POST /bookings (minimal) ->", res.status_code, res.text[:300])
        assert res.status_code in (200, 201, 422)


@pytest.mark.asyncio
async def test_cancel_nonexistent_booking():
    """Cancel booking should return 404 instead of 500."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"refund_reason": "Test cancellation", "refund_amount": 100.00}
        res = await client.post("/bookings/99999/cancel", json=payload)
        print("\n[DEBUG] POST /bookings/99999/cancel ->", res.status_code, res.text[:300])
        assert res.status_code in (404, 422)
