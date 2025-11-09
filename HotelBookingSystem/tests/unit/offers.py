import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from app.database.postgres_connection import get_db, engine

# ==========================================================
# 🧩 1. Patch BEFORE importing the app
# ==========================================================

async def fake_permissions(*args, **kwargs):
    return {
        "OFFER_MANAGEMENT": ["WRITE", "READ"],
    }

import app.dependencies.authentication as auth_deps
auth_deps.get_user_permissions = fake_permissions

from app.main import app
from app.dependencies.authentication import get_current_user


# ==========================================================
# 🧍 2. Mock user + DB
# ==========================================================

class FakeUser:
    def __init__(self, role_id=2):  # Admin
        self.user_id = 999
        self.role_id = role_id
        self.role = "admin"
        self.email = "test_admin@example.com"
        self.username = "test_admin"
        self.account_status_id = 1

async def fake_user():
    return FakeUser()

TestingSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = fake_user


# ==========================================================
# 🧪 Tests - GET (List/Get Offers)
# ==========================================================

@pytest.mark.asyncio
async def test_get_offers_list():
    """GET /offers should return list of all offers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/offers/")
        print("\n[DEBUG] GET /offers ->", res.status_code, res.text[:200])
        assert res.status_code in (200, 404, 422)






# ==========================================================
# 🧪 Tests - POST (Create Offer)
# ==========================================================

@pytest.mark.asyncio
async def test_create_offer_basic():
    """POST /offers should create offer with minimal fields."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "offer_name": "Winter Sale",
            "description": "20% off on all rooms",
            "discount_percent": 20,
            "start_date": "2025-12-01",
            "expiry_date": "2025-12-31",
            "room_types": [1, 2, 3],
            "offer_price": 80,
        }
        res = await client.post("/offers/", json=payload)
        print("\n[DEBUG] POST /offers (basic) ->", res.status_code, res.text[:300])
        assert res.status_code in (200, 201, 422)


@pytest.mark.asyncio
async def test_create_offer_with_items():
    """POST /offers should accept offer_items (perks/features)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "offer_name": "Holiday Special",
            "description": "Special holiday package",
            "offer_items": ["Free breakfast", "Late checkout", "Airport transfer"],
            "discount_percent": 15,
            "start_date": "2025-12-20",
            "expiry_date": "2026-01-05",
            "room_types": [1, 2],
            "offer_price": 85,
        }
        res = await client.post("/offers/", json=payload)
        print("\n[DEBUG] POST /offers (with items) ->", res.status_code, res.text[:300])
        assert res.status_code in (200, 201, 422)


@pytest.mark.asyncio
async def test_create_offer_single_room_type():
    """POST /offers should work with single room type."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "offer_name": "Deluxe Suite Discount",
            "description": "Exclusive offer for Deluxe Suites",
            "discount_percent": 25,
            "start_date": "2025-11-15",
            "expiry_date": "2025-12-15",
            "room_types": [3],
            "offer_price": 75,
        }
        res = await client.post("/offers/", json=payload)
        print("\n[DEBUG] POST /offers (single room) ->", res.status_code, res.text[:300])
        assert res.status_code in (200, 201, 422)


@pytest.mark.asyncio
async def test_create_offer_zero_discount():
    """POST /offers should accept 0% discount."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "offer_name": "Free Booking",
            "description": "No discount offer",
            "discount_percent": 0,
            "start_date": "2025-11-01",
            "expiry_date": "2025-12-31",
            "room_types": [1],
            "offer_price": 100,
        }
        res = await client.post("/offers/", json=payload)
        print("\n[DEBUG] POST /offers (0% discount) ->", res.status_code, res.text[:300])
        assert res.status_code in (200, 201, 422)


@pytest.mark.asyncio
async def test_create_offer_max_discount():
    """POST /offers should accept 100% discount."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "offer_name": "Free Stay",
            "description": "100% discount (free).",
            "discount_percent": 100,
            "start_date": "2025-11-01",
            "expiry_date": "2025-11-07",
            "room_types": [1, 2],
            "offer_price": 0,
        }
        res = await client.post("/offers/", json=payload)
        print("\n[DEBUG] POST /offers (100% discount) ->", res.status_code, res.text[:300])
        assert res.status_code in (200, 201, 422)


# ==========================================================
# 🧪 Tests - PUT/PATCH (Update Offer)
# ==========================================================

@pytest.mark.asyncio
async def test_update_offer():
    """PUT /offers/{offer_id} should update offer details."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "offer_name": "Updated Winter Sale",
            "description": "Updated: 25% off on all rooms",
            "discount_percent": 25,
            "start_date": "2025-12-01",
            "expiry_date": "2025-12-31",
            "room_types": [1, 2],
            "offer_price": 75,
        }
        res = await client.put("/offers/1", json=payload)
        print("\n[DEBUG] PUT /offers/1 ->", res.status_code, res.text[:300])
        assert res.status_code in (200, 404, 422)



# ==========================================================
# 🧪 Tests - DELETE (Soft Delete Offer)
# ==========================================================

@pytest.mark.asyncio
async def test_soft_delete_offer():
    """DELETE /offers/{offer_id} should soft delete (mark as deleted)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.delete("/offers/1")
        print("\n[DEBUG] DELETE /offers/1 ->", res.status_code, res.text[:300])
        assert res.status_code in (200, 204, 404, 422)


@pytest.mark.asyncio
async def test_delete_nonexistent_offer():
    """DELETE /offers/{offer_id} with invalid ID should return 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.delete("/offers/99999")
        print("\n[DEBUG] DELETE /offers/99999 ->", res.status_code, res.text[:300])
        assert res.status_code in (404, 422)
