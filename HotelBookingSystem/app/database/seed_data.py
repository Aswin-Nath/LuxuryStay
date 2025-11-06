import asyncio
from sqlalchemy import text
from app.database.postgres_connection import engine


ROLES = [
    (1, 'customer', 'Can Book Rooms'),
    (2, 'super_admin', 'Main Man'),
    (3, 'normal_admin', 'second main man'),
]

PERMISSIONS = [
    (5, 'BOOKING', 'READ'),
    (6, 'BOOKING', 'WRITE'),
    (7, 'BOOKING', 'DELETE'),
    (8, 'BOOKING', 'MANAGE'),
    (9, 'BOOKING', 'APPROVE'),
    (10, 'BOOKING', 'EXECUTE'),
    (11, 'ADMIN_CREATION', 'READ'),
    (12, 'ADMIN_CREATION', 'WRITE'),
    (13, 'ADMIN_CREATION', 'DELETE'),
    (14, 'ADMIN_CREATION', 'MANAGE'),
    (15, 'ADMIN_CREATION', 'APPROVE'),
    (16, 'ADMIN_CREATION', 'EXECUTE'),
    (17, 'ROOM_MANAGEMENT', 'READ'),
    (18, 'ROOM_MANAGEMENT', 'WRITE'),
    (19, 'ROOM_MANAGEMENT', 'DELETE'),
    (20, 'ROOM_MANAGEMENT', 'MANAGE'),
    (21, 'ROOM_MANAGEMENT', 'APPROVE'),
    (22, 'ROOM_MANAGEMENT', 'EXECUTE'),
    (23, 'PAYMENT_PROCESSING', 'READ'),
    (24, 'PAYMENT_PROCESSING', 'WRITE'),
    (25, 'PAYMENT_PROCESSING', 'DELETE'),
    (26, 'PAYMENT_PROCESSING', 'MANAGE'),
    (27, 'PAYMENT_PROCESSING', 'APPROVE'),
    (28, 'PAYMENT_PROCESSING', 'EXECUTE'),
    (29, 'REFUND_APPROVAL', 'READ'),
    (30, 'REFUND_APPROVAL', 'WRITE'),
    (31, 'REFUND_APPROVAL', 'DELETE'),
    (32, 'REFUND_APPROVAL', 'MANAGE'),
    (33, 'REFUND_APPROVAL', 'APPROVE'),
    (34, 'REFUND_APPROVAL', 'EXECUTE'),
    (35, 'CONTENT_MANAGEMENT', 'READ'),
    (36, 'CONTENT_MANAGEMENT', 'WRITE'),
    (37, 'CONTENT_MANAGEMENT', 'DELETE'),
    (38, 'CONTENT_MANAGEMENT', 'MANAGE'),
    (39, 'CONTENT_MANAGEMENT', 'APPROVE'),
    (40, 'CONTENT_MANAGEMENT', 'EXECUTE'),
    (41, 'ISSUE_RESOLUTION', 'READ'),
    (42, 'ISSUE_RESOLUTION', 'WRITE'),
    (43, 'ISSUE_RESOLUTION', 'DELETE'),
    (44, 'ISSUE_RESOLUTION', 'MANAGE'),
    (45, 'ISSUE_RESOLUTION', 'APPROVE'),
    (46, 'ISSUE_RESOLUTION', 'EXECUTE'),
    (47, 'NOTIFICATION_HANDLING', 'READ'),
    (48, 'NOTIFICATION_HANDLING', 'WRITE'),
    (49, 'NOTIFICATION_HANDLING', 'DELETE'),
    (50, 'NOTIFICATION_HANDLING', 'MANAGE'),
    (51, 'NOTIFICATION_HANDLING', 'APPROVE'),
    (52, 'NOTIFICATION_HANDLING', 'EXECUTE'),
    (53, 'ANALYTICS_VIEW', 'READ'),
    (54, 'ANALYTICS_VIEW', 'WRITE'),
    (55, 'ANALYTICS_VIEW', 'DELETE'),
    (56, 'ANALYTICS_VIEW', 'MANAGE'),
    (57, 'ANALYTICS_VIEW', 'APPROVE'),
    (58, 'ANALYTICS_VIEW', 'EXECUTE'),
    (59, 'BACKUP_OPERATIONS', 'READ'),
    (60, 'BACKUP_OPERATIONS', 'WRITE'),
    (61, 'BACKUP_OPERATIONS', 'DELETE'),
    (62, 'BACKUP_OPERATIONS', 'MANAGE'),
    (63, 'BACKUP_OPERATIONS', 'APPROVE'),
    (64, 'BACKUP_OPERATIONS', 'EXECUTE'),
    (65, 'RESTORE_OPERATIONS', 'READ'),
    (66, 'RESTORE_OPERATIONS', 'WRITE'),
    (67, 'RESTORE_OPERATIONS', 'DELETE'),
    (68, 'RESTORE_OPERATIONS', 'MANAGE'),
    (69, 'RESTORE_OPERATIONS', 'APPROVE'),
    (70, 'RESTORE_OPERATIONS', 'EXECUTE'),
    (71, 'OFFER_MANAGEMENT', 'READ'),
    (72, 'OFFER_MANAGEMENT', 'WRITE'),
    (73, 'OFFER_MANAGEMENT', 'DELETE'),
    (74, 'OFFER_MANAGEMENT', 'MANAGE'),
    (75, 'OFFER_MANAGEMENT', 'APPROVE'),
    (76, 'OFFER_MANAGEMENT', 'EXECUTE'),
]

PERMISSION_ROLE_MAP = [
    # from snapshot: (role_id, permission_id) pairs
    (3, 72),
    (2, 20), (2, 25), (2, 26), (2, 27), (2, 11), (2, 39), (2, 17), (2, 66), (2, 33),
    (2, 57), (2, 31), (2, 34), (2, 12), (2, 10), (2, 18), (2, 64), (2, 71), (2, 72),
    (2, 47), (2, 46), (2, 15), (2, 73), (2, 56), (2, 40), (2, 13), (2, 21), (2, 5),
    (2, 19), (2, 65), (2, 52), (2, 37), (2, 32), (2, 24), (2, 55), (2, 68), (2, 38),
    (2, 8), (2, 48), (2, 28), (2, 30), (2, 62), (2, 67), (2, 50), (2, 51), (2, 76),
    (2, 69), (2, 42), (2, 59), (2, 74), (2, 6), (2, 29), (2, 41), (2, 16), (2, 54),
    (2, 36), (2, 53), (2, 23), (2, 44), (2, 58), (2, 49), (2, 22), (2, 70), (2, 45),
    (2, 60), (2, 75), (2, 43), (2, 61), (2, 14), (2, 35), (2, 63), (2, 9), (2, 7),
    (1, 5), (1, 6),
]


async def seed_roles(conn):
    for role_id, name, desc in ROLES:
        await conn.execute(
            text(
                """
                INSERT INTO roles_utility (role_id, role_name, role_description)
                VALUES (:role_id, :name, :desc)
                ON CONFLICT (role_id) DO NOTHING
                """
            ),
            {"role_id": role_id, "name": name, "desc": desc},
        )


async def seed_permissions(conn):
    for pid, resource, ptype in PERMISSIONS:
        await conn.execute(
            text(
                """
                INSERT INTO permissions (permission_id, resource, permission_type)
                VALUES (:pid, :resource, :ptype)
                ON CONFLICT (permission_id) DO NOTHING
                """
            ),
            {"pid": pid, "resource": resource, "ptype": ptype},
        )


async def seed_permission_role_map(conn):
    for role_id, permission_id in PERMISSION_ROLE_MAP:
        await conn.execute(
            text(
                """
                INSERT INTO permission_role_map (role_id, permission_id)
                VALUES (:role_id, :permission_id)
                ON CONFLICT (role_id, permission_id) DO NOTHING
                """
            ),
            {"role_id": role_id, "permission_id": permission_id},
        )


async def seed_dummy_user(conn):
    # This will create one dummy user only if the email is not already present.
    email = 'aswinnathte125@gmail.com'
    # The hashed password is copied from an existing snapshot; change as needed.
    hashed_password = (
        '84d58d799b936bc6bfd14fa281ff9a6a$9d5978ff545970e5d9de1b89aaa3c5f07e8ed79669ec9355ad335851289f0cbb'
    )

    await conn.execute(
        text(
            """
            INSERT INTO users (role_id, full_name, dob, gender, email, phone_number, hashed_password, last_password_updated, loyalty_points, created_by, status_id, is_deleted, created_at, updated_at, profile_image_url)
            SELECT :role_id, :full_name, NULL, :gender, :email, :phone, :hashed_password, now(), 0, NULL, 1, false, now(), now(), NULL
            WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = :email)
            """
        ),
        {
            "role_id": 1,
            "full_name": 'aswin',
            "gender": 'Other',
            "email": email,
            "phone": '1111122552',
            "hashed_password": hashed_password,
        },
    )


async def main():
    async with engine.begin() as conn:
        await seed_roles(conn)
        await seed_permissions(conn)
        await seed_permission_role_map(conn)
        await seed_dummy_user(conn)


if __name__ == '__main__':
    asyncio.run(main())