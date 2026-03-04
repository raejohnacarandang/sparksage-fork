from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from api.auth import decode_token
import db as database

router = APIRouter()
security = HTTPBearer()

# Role hierarchy
ROLES = ["viewer", "moderator", "admin"]

ROLE_PERMISSIONS = {
    "admin": [
        "/dashboard",
        "/dashboard/providers",
        "/dashboard/settings",
        "/dashboard/conversations",
        "/dashboard/review",
        "/dashboard/analytics",
        "/dashboard/costs",
        "/dashboard/faq",
        "/dashboard/plugins",
        "/dashboard/permissions",
        "/dashboard/digest",
        "/dashboard/moderation",
        "/dashboard/channel-prompts",
        "/dashboard/channel-providers",
        "/dashboard/quota",
    ],
    "moderator": [
        "/dashboard",
        "/dashboard/analytics",
        "/dashboard/faq",
        "/dashboard/permissions",
        "/dashboard/moderation",
        "/dashboard/conversations",
    ],
    "viewer": [
        "/dashboard",
        "/dashboard/analytics",
    ],
}


def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


class UserRole(BaseModel):
    discord_id: str
    role: str


class UpsertUser(BaseModel):
    discord_id: str
    username: str
    avatar: str | None = None
    role: str = "viewer"


@router.get("/api/roles/users")
async def list_users(_=Depends(require_auth)):
    """List all dashboard users with their roles."""
    pool = await database.get_pool()
    async with pool.acquire() as db:
        rows = await db.fetch(
            "SELECT discord_id, username, avatar, role, created_at FROM dashboard_users ORDER BY role, username"
        )
    return [dict(row) for row in rows]


@router.get("/api/roles/me")
async def get_my_role(payload=Depends(require_auth)):
    """Get current user's role."""
    discord_id = payload.get("discord_id") or payload.get("sub")
    if not discord_id:
        return {"role": "viewer", "permissions": ROLE_PERMISSIONS["viewer"]}

    pool = await database.get_pool()
    async with pool.acquire() as db:
        row = await db.fetchrow(
            "SELECT role FROM dashboard_users WHERE discord_id = $1",
            str(discord_id),
        )
    role = row["role"] if row else "viewer"
    return {
        "role": role,
        "permissions": ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["viewer"]),
    }


@router.post("/api/roles/users")
async def upsert_user(body: UpsertUser, _=Depends(require_auth)):
    """Add or update a dashboard user."""
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {ROLES}")

    pool = await database.get_pool()
    async with pool.acquire() as db:
        await db.execute(
            """INSERT INTO dashboard_users (discord_id, username, avatar, role)
               VALUES ($1, $2, $3, $4)
               ON CONFLICT (discord_id) DO UPDATE SET
                   username = EXCLUDED.username,
                   avatar   = EXCLUDED.avatar,
                   role     = EXCLUDED.role,
                   updated_at = NOW()""",
            body.discord_id, body.username, body.avatar, body.role,
        )
    return {"message": f"User {body.username} set to {body.role}"}


@router.patch("/api/roles/users/{discord_id}")
async def update_role(discord_id: str, body: UserRole, _=Depends(require_auth)):
    """Update a user's role."""
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {ROLES}")

    pool = await database.get_pool()
    async with pool.acquire() as db:
        result = await db.execute(
            "UPDATE dashboard_users SET role = $1, updated_at = NOW() WHERE discord_id = $2",
            body.role, discord_id,
        )

    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": f"Role updated to {body.role}"}


@router.delete("/api/roles/users/{discord_id}")
async def remove_user(discord_id: str, _=Depends(require_auth)):
    """Remove a user from the dashboard."""
    pool = await database.get_pool()
    async with pool.acquire() as db:
        await db.execute(
            "DELETE FROM dashboard_users WHERE discord_id = $1",
            discord_id,
        )
    return {"message": "User removed"}