from __future__ import annotations

import os
import json
import asyncio
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL", "")

_pool: asyncpg.Pool | None = None


async def reset_pool() -> None:
    """Close and discard the current pool so the next get_pool() call
    creates a fresh one bound to the currently running event loop.
    Call this at the start of any new event loop that needs DB access."""
    global _pool
    if _pool is not None:
        try:
            await _pool.close()
        except Exception:
            pass
        _pool = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=3)
    return _pool

async def init_db():
    pool = await get_pool()
    async with pool.acquire() as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
        )
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id         SERIAL PRIMARY KEY,
                channel_id TEXT    NOT NULL,
                role       TEXT    NOT NULL,
                content    TEXT    NOT NULL,
                provider   TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_conv_channel ON conversations(channel_id);"
        )
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT PRIMARY KEY,
                user_id    TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMPTZ NOT NULL
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS wizard_state (
                id           INTEGER PRIMARY KEY CHECK (id = 1),
                completed    INTEGER NOT NULL DEFAULT 0,
                current_step INTEGER NOT NULL DEFAULT 0,
                data         TEXT    NOT NULL DEFAULT '{}'
            );
        """)
        await db.execute(
            "INSERT INTO wizard_state (id) VALUES (1) ON CONFLICT DO NOTHING;"
        )
        await db.execute("""
            CREATE TABLE IF NOT EXISTS faqs (
                id             SERIAL PRIMARY KEY,
                guild_id       TEXT NOT NULL,
                question       TEXT NOT NULL,
                answer         TEXT NOT NULL,
                match_keywords TEXT NOT NULL,
                times_used     INTEGER DEFAULT 0,
                created_by     TEXT,
                created_at     TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS command_permissions (
                command_name TEXT NOT NULL,
                guild_id     TEXT NOT NULL,
                role_id      TEXT NOT NULL,
                PRIMARY KEY (command_name, guild_id, role_id)
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                id             SERIAL PRIMARY KEY,
                event_type     TEXT NOT NULL,
                guild_id       TEXT,
                channel_id     TEXT,
                user_id        TEXT,
                provider       TEXT,
                tokens_used    INTEGER,
                latency_ms     INTEGER,
                input_tokens   INTEGER,
                output_tokens  INTEGER,
                estimated_cost REAL,
                created_at     TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channel_prompts (
                channel_id    TEXT PRIMARY KEY,
                guild_id      TEXT NOT NULL,
                system_prompt TEXT NOT NULL
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_messages (
                id             SERIAL PRIMARY KEY,
                guild_id       TEXT NOT NULL,
                channel_id     TEXT NOT NULL,
                message        TEXT NOT NULL,
                scheduled_time TIMESTAMPTZ NOT NULL,
                created_by     TEXT,
                sent           INTEGER DEFAULT 0,
                created_at     TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id TEXT NOT NULL,
                key      TEXT NOT NULL,
                value    TEXT NOT NULL,
                PRIMARY KEY (guild_id, key)
            );
        """)
        await db.execute("""
    CREATE TABLE IF NOT EXISTS dashboard_users (
        discord_id TEXT PRIMARY KEY,
        username   TEXT NOT NULL,
        avatar     TEXT,
        role       TEXT NOT NULL DEFAULT 'viewer',
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
""")

# -----------------------------------------------------------------
        # Migrations — safe to run on every startup
        # -----------------------------------------------------------------
        await db.execute("""
            ALTER TABLE conversations
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
        """)
        await db.execute("""
            UPDATE conversations SET created_at = NOW() WHERE created_at IS NULL;
        """)
# =============================================================================
# Global config helpers
# =============================================================================

async def get_config(key: str, default: str | None = None) -> str | None:
    pool = await get_pool()
    async with pool.acquire() as db:
        row = await db.fetchrow("SELECT value FROM config WHERE key = $1", key)
        return row["value"] if row else default


async def get_all_config() -> dict[str, str]:
    pool = await get_pool()
    async with pool.acquire() as db:
        rows = await db.fetch("SELECT key, value FROM config")
        return {row["key"]: row["value"] for row in rows}


async def set_config(key: str, value: str):
    pool = await get_pool()
    async with pool.acquire() as db:
        await db.execute(
            "INSERT INTO config (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            key, value,
        )


async def set_config_bulk(data: dict[str, str]):
    pool = await get_pool()
    async with pool.acquire() as db:
        await db.executemany(
            "INSERT INTO config (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            list(data.items()),
        )


async def sync_env_to_db():
    import config as cfg
    env_keys = {
        "DISCORD_TOKEN": cfg.DISCORD_TOKEN or "",
        "AI_PROVIDER": cfg.AI_PROVIDER,
        "GEMINI_API_KEY": cfg.GEMINI_API_KEY or "",
        "GEMINI_MODEL": cfg.GEMINI_MODEL,
        "GROQ_API_KEY": cfg.GROQ_API_KEY or "",
        "GROQ_MODEL": cfg.GROQ_MODEL,
        "OPENROUTER_API_KEY": cfg.OPENROUTER_API_KEY or "",
        "OPENROUTER_MODEL": cfg.OPENROUTER_MODEL,
        "ANTHROPIC_API_KEY": cfg.ANTHROPIC_API_KEY or "",
        "ANTHROPIC_MODEL": cfg.ANTHROPIC_MODEL,
        "OPENAI_API_KEY": cfg.OPENAI_API_KEY or "",
        "OPENAI_MODEL": cfg.OPENAI_MODEL,
        "BOT_PREFIX": cfg.BOT_PREFIX,
        "MAX_TOKENS": str(cfg.MAX_TOKENS),
        "SYSTEM_PROMPT": cfg.SYSTEM_PROMPT,
    }
    pool = await get_pool()
    async with pool.acquire() as db:
        for key, value in env_keys.items():
            await db.execute(
                "INSERT INTO config (key, value) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                key, value,
            )


async def sync_db_to_env():
    from dotenv import set_key
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    all_config = await get_all_config()
    for key, value in all_config.items():
        set_key(env_path, key, value)


# =============================================================================
# Guild config helpers
# =============================================================================

async def get_guild_config(guild_id: str, key: str, default: str | None = None) -> str | None:
    pool = await get_pool()
    async with pool.acquire() as db:
        row = await db.fetchrow(
            "SELECT value FROM guild_config WHERE guild_id = $1 AND key = $2",
            guild_id, key,
        )
        if row:
            return row["value"]
    return await get_config(key, default)


async def set_guild_config(guild_id: str, key: str, value: str):
    pool = await get_pool()
    async with pool.acquire() as db:
        await db.execute(
            "INSERT INTO guild_config (guild_id, key, value) VALUES ($1, $2, $3) "
            "ON CONFLICT (guild_id, key) DO UPDATE SET value = EXCLUDED.value",
            guild_id, key, value,
        )


async def get_all_guild_config(guild_id: str) -> dict[str, str]:
    global_cfg = await get_all_config()
    pool = await get_pool()
    async with pool.acquire() as db:
        rows = await db.fetch(
            "SELECT key, value FROM guild_config WHERE guild_id = $1", guild_id
        )
        guild_cfg = {row["key"]: row["value"] for row in rows}
    return {**global_cfg, **guild_cfg}


async def delete_guild_config(guild_id: str, key: str):
    pool = await get_pool()
    async with pool.acquire() as db:
        await db.execute(
            "DELETE FROM guild_config WHERE guild_id = $1 AND key = $2", guild_id, key
        )


async def reset_guild_config(guild_id: str):
    pool = await get_pool()
    async with pool.acquire() as db:
        await db.execute("DELETE FROM guild_config WHERE guild_id = $1", guild_id)


# =============================================================================
# Conversation helpers
# =============================================================================

async def add_message(channel_id: str, role: str, content: str, provider: str | None = None):
    pool = await get_pool()
    async with pool.acquire() as db:
        await db.execute(
            "INSERT INTO conversations (channel_id, role, content, provider) VALUES ($1, $2, $3, $4)",
            channel_id, role, content, provider,
        )


async def get_messages(channel_id: str, limit: int = 20) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as db:
        rows = await db.fetch(
            "SELECT role, content, provider, created_at FROM conversations "
            "WHERE channel_id = $1 ORDER BY id DESC LIMIT $2",
            channel_id, limit,
        )
    return [dict(row) for row in reversed(rows)]


async def clear_messages(channel_id: str):
    pool = await get_pool()
    async with pool.acquire() as db:
        await db.execute("DELETE FROM conversations WHERE channel_id = $1", channel_id)


async def list_channels() -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as db:
        rows = await db.fetch(
            """SELECT channel_id, COUNT(*) as message_count, MAX(created_at) as last_active
               FROM conversations GROUP BY channel_id ORDER BY last_active DESC"""
        )
    return [dict(row) for row in rows]


# =============================================================================
# Wizard helpers
# =============================================================================

async def get_wizard_state() -> dict:
    pool = await get_pool()
    async with pool.acquire() as db:
        row = await db.fetchrow(
            "SELECT completed, current_step, data FROM wizard_state WHERE id = 1"
        )
    return {
        "completed": bool(row["completed"]),
        "current_step": row["current_step"],
        "data": json.loads(row["data"]),
    }


async def set_wizard_state(
    completed: bool | None = None,
    current_step: int | None = None,
    data: dict | None = None,
):
    pool = await get_pool()
    async with pool.acquire() as db:
        if completed is not None:
            await db.execute(
                "UPDATE wizard_state SET completed = $1 WHERE id = 1", int(completed)
            )
        if current_step is not None:
            await db.execute(
                "UPDATE wizard_state SET current_step = $1 WHERE id = 1", current_step
            )
        if data is not None:
            await db.execute(
                "UPDATE wizard_state SET data = $1 WHERE id = 1", json.dumps(data)
            )


# =============================================================================
# Session helpers
# =============================================================================

async def create_session(token: str, user_id: str, expires_at: str):
    from datetime import datetime
    pool = await get_pool()
    async with pool.acquire() as db:
        expires_dt = datetime.fromisoformat(expires_at)
        await db.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES ($1, $2, $3)",
            token, user_id, expires_dt,
        )


async def validate_session(token: str) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as db:
        row = await db.fetchrow(
            "SELECT user_id, expires_at FROM sessions WHERE token = $1 AND expires_at > NOW()",
            token,
        )
    return dict(row) if row else None


async def delete_session(token: str):
    pool = await get_pool()
    async with pool.acquire() as db:
        await db.execute("DELETE FROM sessions WHERE token = $1", token)


async def close_db():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


# =============================================================================
# Analytics helpers
# =============================================================================

def _calculate_cost(provider: str, input_tokens: int, output_tokens: int) -> float:
    try:
        import config as cfg
        pricing = cfg.PROVIDER_PRICING.get(provider, {})
        input_cost = (input_tokens / 1000) * pricing.get("input_cost_per_1k", 0.0)
        output_cost = (output_tokens / 1000) * pricing.get("output_cost_per_1k", 0.0)
        return round(input_cost + output_cost, 8)
    except Exception:
        return 0.0


async def log_event(
    event_type: str,
    guild_id: str | None = None,
    channel_id: str | None = None,
    user_id: str | None = None,
    username: str | None = None,   # ← idagdag ito
    provider: str | None = None,
    tokens_used: int | None = None,
    latency_ms: int | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
):
    estimated_cost = None
    if provider and input_tokens is not None and output_tokens is not None:
        estimated_cost = _calculate_cost(provider, input_tokens, output_tokens)

    pool = await get_pool()
    async with pool.acquire() as db:
        await db.execute(
            """INSERT INTO analytics
               (event_type, guild_id, channel_id, user_id, username, provider,
                tokens_used, latency_ms, input_tokens, output_tokens, estimated_cost)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)""",
            event_type, guild_id, channel_id, user_id, username, provider,
            tokens_used, latency_ms, input_tokens, output_tokens, estimated_cost,
        )


async def get_analytics_summary(guild_id: str | None = None) -> dict:
    pool = await get_pool()
    async with pool.acquire() as db:
        if guild_id:
            by_type_rows = await db.fetch(
                "SELECT COUNT(*) as total, event_type FROM analytics WHERE guild_id = $1 GROUP BY event_type",
                guild_id,
            )
            daily_rows = await db.fetch(
                "SELECT DATE(created_at) as day, COUNT(*) as count FROM analytics "
                "WHERE guild_id = $1 GROUP BY day ORDER BY day DESC LIMIT 30",
                guild_id,
            )
            provider_rows = await db.fetch(
                "SELECT provider, COUNT(*) as count, "
                "SUM(COALESCE(input_tokens,0)) as total_input_tokens, "
                "SUM(COALESCE(output_tokens,0)) as total_output_tokens, "
                "SUM(COALESCE(estimated_cost,0)) as total_cost "
                "FROM analytics WHERE provider IS NOT NULL AND guild_id = $1 GROUP BY provider",
                guild_id,
            )
        else:
            by_type_rows = await db.fetch(
                "SELECT COUNT(*) as total, event_type FROM analytics GROUP BY event_type"
            )
            daily_rows = await db.fetch(
                "SELECT DATE(created_at) as day, COUNT(*) as count FROM analytics "
                "GROUP BY day ORDER BY day DESC LIMIT 30"
            )
            provider_rows = await db.fetch(
                "SELECT provider, COUNT(*) as count, "
                "SUM(COALESCE(input_tokens,0)) as total_input_tokens, "
                "SUM(COALESCE(output_tokens,0)) as total_output_tokens, "
                "SUM(COALESCE(estimated_cost,0)) as total_cost "
                "FROM analytics WHERE provider IS NOT NULL GROUP BY provider"
            )

    return {
        "by_type": {row["event_type"]: row["total"] for row in by_type_rows},
        "daily": [dict(row) for row in daily_rows],
        "providers": [dict(row) for row in provider_rows],
    }


# =============================================================================
# FAQ helpers
# =============================================================================

async def add_faq(guild_id: str, question: str, answer: str, keywords: str, created_by: str) -> int:
    pool = await get_pool()
    async with pool.acquire() as db:
        row = await db.fetchrow(
            "INSERT INTO faqs (guild_id, question, answer, match_keywords, created_by) "
            "VALUES ($1, $2, $3, $4, $5) RETURNING id",
            guild_id, question, answer, keywords, created_by,
        )
    return row["id"]


async def get_faqs(guild_id: str) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as db:
        rows = await db.fetch(
            "SELECT * FROM faqs WHERE guild_id = $1 ORDER BY id DESC", guild_id
        )
    return [dict(row) for row in rows]


async def delete_faq(faq_id: int, guild_id: str) -> bool:
    pool = await get_pool()
    async with pool.acquire() as db:
        result = await db.execute(
            "DELETE FROM faqs WHERE id = $1 AND guild_id = $2", faq_id, guild_id
        )
    return result == "DELETE 1"


async def increment_faq_usage(faq_id: int):
    pool = await get_pool()
    async with pool.acquire() as db:
        await db.execute(
            "UPDATE faqs SET times_used = times_used + 1 WHERE id = $1", faq_id
        )


# =============================================================================
# Permission helpers
# =============================================================================

async def get_allowed_roles(command_name: str, guild_id: str) -> list[str]:
    pool = await get_pool()
    async with pool.acquire() as db:
        rows = await db.fetch(
            "SELECT role_id FROM command_permissions WHERE command_name = $1 AND guild_id = $2",
            command_name, guild_id,
        )
    return [row["role_id"] for row in rows]


async def get_command_permissions(guild_id: str) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as db:
        rows = await db.fetch(
            "SELECT command_name, role_id FROM command_permissions "
            "WHERE guild_id = $1 ORDER BY command_name",
            guild_id,
        )
    return [dict(row) for row in rows]


async def add_command_permission(command_name: str, guild_id: str, role_id: str):
    pool = await get_pool()
    async with pool.acquire() as db:
        await db.execute(
            "INSERT INTO command_permissions (command_name, guild_id, role_id) "
            "VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
            command_name, guild_id, role_id,
        )


async def remove_command_permission(command_name: str, guild_id: str, role_id: str) -> bool:
    pool = await get_pool()
    async with pool.acquire() as db:
        result = await db.execute(
            "DELETE FROM command_permissions WHERE command_name = $1 AND guild_id = $2 AND role_id = $3",
            command_name, guild_id, role_id,
        )
    return result == "DELETE 1"


# =============================================================================
# Channel prompt helpers
# =============================================================================

async def get_channel_prompt(channel_id: str) -> str | None:
    pool = await get_pool()
    async with pool.acquire() as db:
        row = await db.fetchrow(
            "SELECT system_prompt FROM channel_prompts WHERE channel_id = $1", channel_id
        )
    return row["system_prompt"] if row else None


async def set_channel_prompt(channel_id: str, guild_id: str, system_prompt: str):
    pool = await get_pool()
    async with pool.acquire() as db:
        await db.execute(
            "INSERT INTO channel_prompts (channel_id, guild_id, system_prompt) VALUES ($1, $2, $3) "
            "ON CONFLICT (channel_id) DO UPDATE SET system_prompt = EXCLUDED.system_prompt",
            channel_id, guild_id, system_prompt,
        )


async def delete_channel_prompt(channel_id: str):
    pool = await get_pool()
    async with pool.acquire() as db:
        await db.execute(
            "DELETE FROM channel_prompts WHERE channel_id = $1", channel_id
        )


async def list_channel_prompts(guild_id: str) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as db:
        rows = await db.fetch(
            "SELECT channel_id, system_prompt FROM channel_prompts WHERE guild_id = $1",
            guild_id,
        )
    return [dict(row) for row in rows]