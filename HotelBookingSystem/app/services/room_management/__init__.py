"""Service package for room_management domain.
Expose service modules here for convenience imports if needed.
"""

from .rooms_service import (
    create_room,
    list_rooms,
    get_room,
    update_room,
    change_room_status,
    delete_room,
)

from .amenities_service import (
    create_amenity,
    list_amenities,
    get_amenity,
    delete_amenity,
)

from .room_amenities_service import (
    map_amenity,
    get_amenities_for_room,
    unmap_amenity,
)

from .room_types_service import (
    create_room_type,
    list_room_types,
    get_room_type,
    update_room_type,
    soft_delete_room_type,
)
