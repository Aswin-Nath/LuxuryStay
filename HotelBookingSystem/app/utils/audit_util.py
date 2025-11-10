from typing import Any, Dict, Optional

from app.services.audit_service import create_audit
from app.schemas.pydantic_models.audit_log import AuditLogModel


async def log_audit(
    entity: str,
    entity_id: str,
    action: str,
    old_value: Optional[Dict[str, Any]] = None,
    new_value: Optional[Dict[str, Any]] = None,
    changed_by_user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Convenience wrapper to create an AuditLogModel and persist it.

    Parameters are lenient — pass whatever is available from the route.
    """
    payload = AuditLogModel(
        entity=entity,
        entity_id=entity_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        changed_by_user_id=changed_by_user_id,
        ip_address=ip_address,
        user_id=user_id,
    )
    return await create_audit(payload)
