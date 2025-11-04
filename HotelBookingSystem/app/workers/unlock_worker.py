import asyncio
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.postgres_connection import AsyncSessionLocal
from app.models.sqlalchemy_schemas.bookings import BookingEdits, BookingRoomMap
from app.models.sqlalchemy_schemas.rooms import Rooms


async def unlock_expired_rooms_once():
    now = datetime.utcnow()

    async with AsyncSessionLocal() as db:  # new session per run
        try:
            async with db.begin():  # one clean transaction boundary
                # 1️⃣ Fetch expired edits
                stmt = (
                    select(BookingEdits)
                    .where(BookingEdits.edit_status == "AWAITING_CUSTOMER_RESPONSE")
                    .where(BookingEdits.lock_expires_at <= now)
                )
                res = await db.execute(stmt)
                expired_edits = res.scalars().all()

                for edit in expired_edits:
                    print(f"Unlocking expired edit {edit.edit_id}")

                    # mark edit as expired
                    edit.edit_status = "EXPIRED"
                    db.add(edit)

                    # 2️⃣ Fetch related booking-room maps
                    brm_stmt = select(BookingRoomMap).where(
                        BookingRoomMap.booking_id == edit.booking_id
                    )
                    brm_res = await db.execute(brm_stmt)
                    br_maps = brm_res.scalars().all()

                    for br in br_maps:
                        if getattr(br, "edit_suggested_rooms", None):
                            suggested_room_ids = br.edit_suggested_rooms or []
                            for rid in suggested_room_ids:
                                try:
                                    # mark room as AVAILABLE
                                    rstmt = select(Rooms).where(Rooms.room_id == rid)
                                    rres = await db.execute(rstmt)
                                    room = rres.scalars().first()
                                    if room:
                                        room.room_status = "AVAILABLE"
                                        db.add(room)
                                except Exception as e:
                                    print(f"unlock worker: failed to mark room {rid} available:", e)

                            # clear suggestions after marking
                            br.edit_suggested_rooms = None
                            db.add(br)

            # 3️⃣ Transaction auto-commits here
            await db.commit()

        except Exception as e:
            await db.rollback()
            print("unlock worker error:", e)


async def start_unlock_worker():
    print("Starting unlock worker")
    while True:
        try:
            await unlock_expired_rooms_once()
        except Exception as e:
            print("unlock worker loop error:", e)
        await asyncio.sleep(60)
