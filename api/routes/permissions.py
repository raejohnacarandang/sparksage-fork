from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from api.auth import decode_token
import db

router = APIRouter()
security = HTTPBearer()

def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload

class PermissionCreate(BaseModel):
    command_name: str
    guild_id: str
    role_id: str

@router.get("")
async def list_permissions(guild_id: str = "", _=Depends(require_auth)):
    """List all command permissions, or filter by guild_id."""
    try:
        if guild_id:
            perms = await db.get_command_permissions(guild_id)
        else:
            pool = await db.get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT command_name, guild_id, role_id FROM command_permissions ORDER BY command_name"
                )
            perms = [dict(r) for r in rows]
        return perms
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
async def add_permission(item: PermissionCreate, _=Depends(require_auth)):
    """Add a role restriction to a command."""
    try:
        await db.add_command_permission(item.command_name, item.guild_id, item.role_id)
        return {"success": True, **item.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("")
async def remove_permission(item: PermissionCreate, _=Depends(require_auth)):
    """Remove a role restriction from a command."""
    try:
        removed = await db.remove_command_permission(item.command_name, item.guild_id, item.role_id)
        if not removed:
            raise HTTPException(status_code=404, detail="Permission not found")
        return {"deleted": True, **item.model_dump()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))