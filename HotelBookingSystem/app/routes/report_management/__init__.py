from fastapi import APIRouter

from .admin_reports import router as admin_router
from .customer_reports import router as customer_router
# Common router that bundles the room management routers so main can include a single router
router = APIRouter()


router.include_router(admin_router)
router.include_router(customer_router)