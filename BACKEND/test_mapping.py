from app.schemas.pydantic_models.room import RoomTypeCreate

# Test frontend payload mapping
payload = RoomTypeCreate(
    room_type_name="Deluxe",
    occupancy_limit_adults=3,
    occupancy_limit_children=2,
    price_per_night=5000,
    square_ft=450,
    description="Nice deluxe room",
    amenities=[1, 2, 3]
)

# Check if fields are mapped correctly
dumped = payload.model_dump(exclude={'amenities'})
print("Mapped data for DB:", dumped)
print("\nField mapping verification:")
print(f"  room_type_name -> type_name: {dumped.get('type_name')}")
print(f"  occupancy_limit_adults -> max_adult_count: {dumped.get('max_adult_count')}")
print(f"  occupancy_limit_children -> max_child_count: {dumped.get('max_child_count')}")
print(f"  square_ft: {dumped.get('square_ft')}")
print(f"  price_per_night: {dumped.get('price_per_night')}")
