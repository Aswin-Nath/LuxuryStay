from fastapi import APIRouter

# Import sub-routers
from .room_types import router as room_types_router
from .rooms import router as rooms_router
from .amenities import router as amenities_router
from .room_images import router as room_images_router


# Common router that bundles the room management routers so main can include a single router
router = APIRouter()

router.include_router(room_types_router)
router.include_router(rooms_router)
router.include_router(amenities_router)
router.include_router(room_images_router)

__all__ = ["router", "room_types_router", "rooms_router", "amenities_router"]
