from __future__ import annotations

import time
from collections import defaultdict, deque

# Default limits
RATE_LIMIT_USER = 10   # requests per minute per user
RATE_LIMIT_GUILD = 30  # requests per minute per guild

# Storage: {key: deque of timestamps}
_user_windows: dict[str, deque] = defaultdict(deque)
_guild_windows: dict[str, deque] = defaultdict(deque)


def _check_limit(windows: dict, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
    """
    Sliding window rate limiter.
    Returns (allowed, seconds_until_reset).
    """
    now = time.time()
    window = windows[key]

    # Remove timestamps outside the window
    while window and now - window[0] > window_seconds:
        window.popleft()

    if len(window) >= limit:
        # Rate limited — calculate when oldest request expires
        reset_in = int(window_seconds - (now - window[0])) + 1
        return False, reset_in

    # Allow — record this request
    window.append(now)
    return True, 0


def check_user_limit(user_id: str, limit: int = RATE_LIMIT_USER) -> tuple[bool, int]:
    """Check if user is within rate limit. Returns (allowed, seconds_until_reset)."""
    return _check_limit(_user_windows, user_id, limit)


def check_guild_limit(guild_id: str, limit: int = RATE_LIMIT_GUILD) -> tuple[bool, int]:
    """Check if guild is within rate limit. Returns (allowed, seconds_until_reset)."""
    return _check_limit(_guild_windows, guild_id, limit)


def check_rate_limits(user_id: str, guild_id: str | None) -> tuple[bool, str]:
    """
    Combined check for both user and guild limits.
    Returns (allowed, error_message).
    """
    user_allowed, user_reset = check_user_limit(user_id)
    if not user_allowed:
        return False, f"⏱️ You're sending too many requests. Please wait {user_reset}s before trying again."

    if guild_id:
        guild_allowed, guild_reset = check_guild_limit(guild_id)
        if not guild_allowed:
            return False, f"⏱️ This server is sending too many requests. Please wait {guild_reset}s."

    return True, ""


def get_user_usage(user_id: str) -> dict:
    """Get current usage stats for a user."""
    now = time.time()
    window = _user_windows[user_id]
    while window and now - window[0] > 60:
        window.popleft()
    return {
        "requests_used": len(window),
        "limit": RATE_LIMIT_USER,
        "remaining": max(0, RATE_LIMIT_USER - len(window)),
    }