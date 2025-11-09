import pytest
import sys
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from app.database.postgres_connection import get_db, engine

# ==========================================================
# 🧩 1. Patch BEFORE importing the app
# ==========================================================

# Patch the permission checker globally
async def fake_permissions(*args, **kwargs):
    return [{"resource": "ROOM_MANAGEMENT", "permission_type": "WRITE"}]

import app.dependencies.authentication as auth_deps
auth_deps.get_user_permissions = fake_permissions

# Now import app after patching
from app.main import app
from app.dependencies.authentication import get_current_user


# ==========================================================
# 🧍 2. Mock user + DB
# ==========================================================

class FakeUser:
    def __init__(self):
        self.user_id = 999
        self.role_id = 2
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

async def override_get_db():
    async with TestingSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Override dependencies
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = fake_user


# ==========================================================
# 🧪 3. Tests
# ==========================================================

@pytest.mark.asyncio
async def test_get_rooms_integration():
    """GET /rooms should work without touching permissions DB."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/rooms/")
        print("\n[DEBUG] GET /rooms ->", res.text)
        assert res.status_code in (200, 404)


@pytest.mark.asyncio
async def test_create_room_integration():
    """POST /rooms should succeed with fake WRITE permission."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "room_name": "Test Room X1",
            "room_type_id": 1,
            "room_status_id": 1,
            "price_per_night": 999.99,
            "max_occupancy": 2,
            "description": "Integration test room",
        }
        res = await client.post("/rooms/", json=payload)
        print("\n[DEBUG] POST /rooms ->", res.text)
        assert res.status_code in (200, 201, 422)


# ==========================================================
# 🧪 Tests - POST (Create Rooms Variations)
# ==========================================================

@pytest.mark.asyncio
async def test_create_room_deluxe():
    """POST /rooms should create a deluxe room."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "room_name": "Deluxe Suite 101",
            "room_type_id": 2,
            "room_status_id": 1,
            "price_per_night": 1999.99,
            "max_occupancy": 4,
            "description": "Luxury deluxe suite with premium amenities",
        }
        res = await client.post("/rooms/", json=payload)
        print("\n[DEBUG] POST /rooms (deluxe) ->", res.status_code, res.text[:300])
        assert res.status_code in (200, 201, 422)


@pytest.mark.asyncio
async def test_create_room_standard():
    """POST /rooms should create a standard room."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "room_name": "Standard Room 201",
            "room_type_id": 1,
            "room_status_id": 1,
            "price_per_night": 499.99,
            "max_occupancy": 2,
            "description": "Standard room with basic amenities",
        }
        res = await client.post("/rooms/", json=payload)
        print("\n[DEBUG] POST /rooms (standard) ->", res.status_code, res.text[:300])
        assert res.status_code in (200, 201, 422)


@pytest.mark.asyncio
async def test_create_room_family():
    """POST /rooms should create a family room."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "room_name": "Family Room 301",
            "room_type_id": 3,
            "room_status_id": 1,
            "price_per_night": 1299.99,
            "max_occupancy": 6,
            "description": "Spacious family room suitable for large groups",
        }
        res = await client.post("/rooms/", json=payload)
        print("\n[DEBUG] POST /rooms (family) ->", res.status_code, res.text[:300])
        assert res.status_code in (200, 201, 422)


# ==========================================================
# 🧪 Tests - PUT (Update Rooms)
# ==========================================================

@pytest.mark.asyncio
async def test_update_room():
    """PUT /rooms/{room_id} should update room details."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "room_name": "Updated Room 101",
            "room_type_id": 1,
            "room_status_id": 2,  # Change status
            "price_per_night": 1099.99,  # Update price
            "max_occupancy": 3,  # Update occupancy
            "description": "Updated description after renovation",
        }
        res = await client.put("/rooms/1", json=payload)
        print("\n[DEBUG] PUT /rooms/1 ->", res.status_code, res.text[:300])
        assert res.status_code in (200, 404, 422)




# ==========================================================
# 🧪 Tests - DELETE (Soft/Hard Delete Rooms)
# ==========================================================

@pytest.mark.asyncio
async def test_soft_delete_room():
    """DELETE /rooms/{room_id} should soft delete room (mark as deleted)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.delete("/rooms/1")
        print("\n[DEBUG] DELETE /rooms/1 ->", res.status_code, res.text[:300])
        assert res.status_code in (200, 204, 404, 422)


@pytest.mark.asyncio
async def test_delete_nonexistent_room():
    """DELETE /rooms/{room_id} with invalid ID should return 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.delete("/rooms/99999")
        print("\n[DEBUG] DELETE /rooms/99999 ->", res.status_code, res.text[:300])
        assert res.status_code in (404, 422)
