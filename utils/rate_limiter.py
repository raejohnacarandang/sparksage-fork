from __future__ import annotations

import time
from collections import defaultdict

# Sliding-window rate limiter
# Stores timestamps of recent requests per user and per guild

_user_requests: dict[str, list[float]] = defaultdict(list)
_guild_requests: dict[str, list[float]] = defaultdict(list)

RATE_WINDOW = 60  # seconds


def check_rate_limit(user_id: str, guild_id: str | None) -> str | None:
    """
    Sliding-window rate limiter.
    Returns a friendly error message if rate limited, else None.
    Limits are read from config at call time so dashboard changes take effect immediately.
    """
    import config

    now = time.monotonic()
    user_limit = int(getattr(config, "RATE_LIMIT_USER", 10))
    guild_limit = int(getattr(config, "RATE_LIMIT_GUILD", 30))

    # Drop timestamps outside the window
    _user_requests[user_id] = [
        t for t in _user_requests[user_id] if now - t < RATE_WINDOW
    ]
    if guild_id:
        _guild_requests[guild_id] = [
            t for t in _guild_requests[guild_id] if now - t < RATE_WINDOW
        ]

    # Check user limit
    if len(_user_requests[user_id]) >= user_limit:
        remaining = int(RATE_WINDOW - (now - _user_requests[user_id][0]))
        return (
            f"⏳ You're sending too many requests! "
            f"Please wait **{remaining}s** before trying again. "
            f"(Limit: {user_limit} requests/min)"
        )

    # Check guild limit
    if guild_id and len(_guild_requests[guild_id]) >= guild_limit:
        remaining = int(RATE_WINDOW - (now - _guild_requests[guild_id][0]))
        return (
            f"⏳ This server has hit the request limit! "
            f"Please wait **{remaining}s** before trying again. "
            f"(Limit: {guild_limit} requests/min per server)"
        )

    # Record this request
    _user_requests[user_id].append(now)
    if guild_id:
        _guild_requests[guild_id].append(now)

    return None


def get_active_users(window: int = 60) -> list[dict]:
    """Return list of users with request counts in the last `window` seconds."""
    now = time.monotonic()
    result = []
    for user_id, timestamps in _user_requests.items():
        recent = [t for t in timestamps if now - t < window]
        if recent:
            result.append({"user_id": user_id, "count": len(recent)})
    return sorted(result, key=lambda x: x["count"], reverse=True)


def get_active_guilds(window: int = 60) -> list[dict]:
    """Return list of guilds with request counts in the last `window` seconds."""
    now = time.monotonic()
    result = []
    for guild_id, timestamps in _guild_requests.items():
        recent = [t for t in timestamps if now - t < window]
        if recent:
            result.append({"guild_id": guild_id, "count": len(recent)})
    return sorted(result, key=lambda x: x["count"], reverse=True)