from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from api.auth import decode_token
from utils.rate_limiter import get_active_users, get_active_guilds
import config

router = APIRouter()
security = HTTPBearer()

def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload

@router.get("/api/quota/stats")
async def get_quota_stats(_=Depends(require_auth)):
    """Get current rate limit usage for all active users and guilds."""
    user_limit = getattr(config, "RATE_LIMIT_USER", 10)
    guild_limit = getattr(config, "RATE_LIMIT_GUILD", 30)

    stats = []

    for entry in get_active_users():
        stats.append({
            "id": entry["user_id"],
            "type": "user",
            "requests_used": entry["count"],
            "limit": user_limit,
            "remaining": max(0, user_limit - entry["count"]),
        })

    for entry in get_active_guilds():
        stats.append({
            "id": entry["guild_id"],
            "type": "guild",
            "requests_used": entry["count"],
            "limit": guild_limit,
            "remaining": max(0, guild_limit - entry["count"]),
        })

    return stats