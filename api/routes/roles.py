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

ROLE_TABLE = """
CREATE TABLE IF NOT EXISTS dashboard_users (
    discord_id  TEXT PRIMARY KEY,
    username    TEXT NOT NULL,
    avatar      TEXT,
    role        TEXT NOT NULL DEFAULT 'viewer',
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);
"""


async def init_roles_table():
    db = await database.get_db()
    await db.execute(ROLE_TABLE)
    await db.commit()


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
    db = await database.get_db()
    cursor = await db.execute(
        "SELECT discord_id, username, avatar, role, created_at FROM dashboard_users ORDER BY role, username"
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@router.get("/api/roles/me")
async def get_my_role(payload=Depends(require_auth)):
    """Get current user's role."""
    discord_id = payload.get("discord_id") or payload.get("sub")
    if not discord_id:
        return {"role": "viewer", "permissions": ROLE_PERMISSIONS["viewer"]}

    db = await database.get_db()
    cursor = await db.execute(
        "SELECT role FROM dashboard_users WHERE discord_id = ?",
        (str(discord_id),),
    )
    row = await cursor.fetchone()
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

    db = await database.get_db()
    await db.execute(
        """INSERT INTO dashboard_users (discord_id, username, avatar, role)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(discord_id) DO UPDATE SET
               username = excluded.username,
               avatar = excluded.avatar,
               role = excluded.role,
               updated_at = datetime('now')""",
        (body.discord_id, body.username, body.avatar, body.role),
    )
    await db.commit()
    return {"message": f"User {body.username} set to {body.role}"}


@router.patch("/api/roles/users/{discord_id}")
async def update_role(discord_id: str, body: UserRole, _=Depends(require_auth)):
    """Update a user's role."""
    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {ROLES}")

    db = await database.get_db()
    cursor = await db.execute(
        "UPDATE dashboard_users SET role = ?, updated_at = datetime('now') WHERE discord_id = ?",
        (body.role, discord_id),
    )
    await db.commit()

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": f"Role updated to {body.role}"}


@router.delete("/api/roles/users/{discord_id}")
async def remove_user(discord_id: str, _=Depends(require_auth)):
    """Remove a user from the dashboard."""
    db = await database.get_db()
    await db.execute(
        "DELETE FROM dashboard_users WHERE discord_id = ?",
        (discord_id,),
    )
    await db.commit()
    return {"message": "User removed"}