from __future__ import annotations

from fastapi import APIRouter, Depends
from api.deps import get_current_user
import db as database

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
async def get_summary(_: dict = Depends(get_current_user)):
    """Get analytics summary."""
    pool = await database.get_pool()
    async with pool.acquire() as db:
        by_type_rows = await db.fetch(
            "SELECT event_type, COUNT(*) as count FROM analytics GROUP BY event_type"
        )
        by_type = {row["event_type"]: row["count"] for row in by_type_rows}

        daily_rows = await db.fetch(
            """SELECT DATE(created_at) as day, COUNT(*) as count
               FROM analytics
               GROUP BY day
               ORDER BY day DESC
               LIMIT 30"""
        )
        daily = list(reversed([dict(r) for r in daily_rows]))

        provider_rows = await db.fetch(
            """SELECT provider, COUNT(*) as count
               FROM analytics
               WHERE provider IS NOT NULL
               GROUP BY provider
               ORDER BY count DESC"""
        )
        providers = [dict(r) for r in provider_rows]

        total_row = await db.fetchrow("SELECT COUNT(*) as total FROM conversations")
        total_messages = total_row["total"] if total_row else 0

        latency_row = await db.fetchrow(
            "SELECT AVG(latency_ms) as avg_latency FROM analytics WHERE latency_ms IS NOT NULL"
        )
        avg_latency = (
            round(latency_row["avg_latency"], 1)
            if latency_row and latency_row["avg_latency"]
            else None
        )

    return {
        "by_type": by_type,
        "daily": daily,
        "providers": providers,
        "total_messages": total_messages,
        "avg_latency_ms": avg_latency,
    }


PROVIDER_PRICING = {
    "gemini":      {"input": 0.0,       "output": 0.0,       "note": "Free tier"},
    "groq":        {"input": 0.0,       "output": 0.0,       "note": "Free tier"},
    "openrouter":  {"input": 0.0,       "output": 0.0,       "note": "Free tier"},
    "anthropic":   {"input": 0.000015,  "output": 0.000075,  "note": "Paid"},
    "openai":      {"input": 0.000010,  "output": 0.000030,  "note": "Paid"},
}


@router.get("/costs")
async def get_costs(_: dict = Depends(get_current_user)):
    """Get cost breakdown per provider."""
    pool = await database.get_pool()
    async with pool.acquire() as db:
        rows = await db.fetch(
            """SELECT provider,
               COUNT(*) as requests,
               SUM(COALESCE(tokens_used, 0)) as total_tokens
               FROM analytics
               WHERE provider IS NOT NULL
               GROUP BY provider"""
        )

    costs = []
    for row in rows:
        provider = row["provider"]
        pricing = PROVIDER_PRICING.get(provider, {"input": 0.0, "output": 0.0, "note": "Unknown"})
        tokens = row["total_tokens"] or 0
        estimated_cost = tokens * pricing["output"]
        costs.append({
            "provider": provider,
            "requests": row["requests"],
            "total_tokens": tokens,
            "estimated_cost_usd": round(estimated_cost, 6),
            "pricing_note": pricing["note"],
        })

    return {"costs": costs}


@router.get("/history")
async def get_history(_: dict = Depends(get_current_user)):
    """Get full analytics event history (last 100)."""
    pool = await database.get_pool()
    async with pool.acquire() as db:
        rows = await db.fetch(
            """SELECT event_type, guild_id, channel_id, user_id, provider, latency_ms, created_at
               FROM analytics
               ORDER BY id DESC
               LIMIT 100"""
        )
    return {"events": [dict(r) for r in rows]}