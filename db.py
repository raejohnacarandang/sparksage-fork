from __future__ import annotations

import os
import json
import aiosqlite

DATABASE_PATH = os.getenv("DATABASE_PATH", "sparksage.db")

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    """Return the shared database connection, creating it if needed."""
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DATABASE_PATH)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
    return _db


async def init_db():
    """Create tables if they don't exist."""
    db = await get_db()
    await db.executescript(
        """
        CREATE TABLE IF NOT EXISTS config (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT    NOT NULL,
            role       TEXT    NOT NULL,
            content    TEXT    NOT NULL,
            provider   TEXT,
            created_at TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_conv_channel ON conversations(channel_id);

        CREATE TABLE IF NOT EXISTS sessions (
            token      TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS wizard_state (
            id           INTEGER PRIMARY KEY CHECK (id = 1),
            completed    INTEGER NOT NULL DEFAULT 0,
            current_step INTEGER NOT NULL DEFAULT 0,
            data         TEXT    NOT NULL DEFAULT '{}'
        );

        INSERT OR IGNORE INTO wizard_state (id) VALUES (1);

        CREATE TABLE IF NOT EXISTS faqs (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id       TEXT NOT NULL,
            question       TEXT NOT NULL,
            answer         TEXT NOT NULL,
            match_keywords TEXT NOT NULL,
            times_used     INTEGER DEFAULT 0,
            created_by     TEXT,
            created_at     TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS command_permissions (
            command_name TEXT NOT NULL,
            guild_id     TEXT NOT NULL,
            role_id      TEXT NOT NULL,
            PRIMARY KEY (command_name, guild_id, role_id)
        );

        CREATE TABLE IF NOT EXISTS analytics (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
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
            created_at     TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS channel_prompts (
            channel_id    TEXT PRIMARY KEY,
            guild_id      TEXT NOT NULL,
            system_prompt TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scheduled_messages (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id       TEXT NOT NULL,
            channel_id     TEXT NOT NULL,
            message        TEXT NOT NULL,
            scheduled_time TEXT NOT NULL,
            created_by     TEXT,
            sent           INTEGER DEFAULT 0,
            created_at     TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS guild_config (
            guild_id TEXT NOT NULL,
            key      TEXT NOT NULL,
            value    TEXT NOT NULL,
            PRIMARY KEY (guild_id, key)
        );
        """
    )
    await db.commit()

    # Migrations: add new columns to existing tables (safe to run multiple times)
    migrations = [
        ("analytics", "input_tokens INTEGER"),
        ("analytics", "output_tokens INTEGER"),
        ("analytics", "estimated_cost REAL"),
    ]
    for table, col_def in migrations:
        try:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
            await db.commit()
        except Exception:
            pass  # Column already exists


# =============================================================================
# Global config helpers
# =============================================================================

async def get_config(key: str, default: str | None = None) -> str | None:
    """Get a global config value from the database."""
    db = await get_db()
    cursor = await db.execute("SELECT value FROM config WHERE key = ?", (key,))
    row = await cursor.fetchone()
    return row["value"] if row else default


async def get_all_config() -> dict[str, str]:
    """Return all global config key-value pairs."""
    db = await get_db()
    cursor = await db.execute("SELECT key, value FROM config")
    rows = await cursor.fetchall()
    return {row["key"]: row["value"] for row in rows}


async def set_config(key: str, value: str):
    """Set a global config value."""
    db = await get_db()
    await db.execute(
        "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    await db.commit()


async def set_config_bulk(data: dict[str, str]):
    """Set multiple global config values at once."""
    db = await get_db()
    await db.executemany(
        "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        list(data.items()),
    )
    await db.commit()


async def sync_env_to_db():
    """Seed the DB config table from current environment / .env values."""
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
    db = await get_db()
    for key, value in env_keys.items():
        await db.execute(
            "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
            (key, value),
        )
    await db.commit()


async def sync_db_to_env():
    """Write DB config back to the .env file."""
    from dotenv import dotenv_values, set_key

    env_path = os.path.join(os.path.dirname(__file__), ".env")
    all_config = await get_all_config()
    for key, value in all_config.items():
        set_key(env_path, key, value)


# =============================================================================
# Guild config helpers (per-server settings)
# =============================================================================

async def get_guild_config(guild_id: str, key: str, default: str | None = None) -> str | None:
    """Get a guild-specific config value, falling back to global config."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT value FROM guild_config WHERE guild_id = ? AND key = ?",
        (guild_id, key),
    )
    row = await cursor.fetchone()
    if row:
        return row["value"]
    return await get_config(key, default)


async def set_guild_config(guild_id: str, key: str, value: str):
    """Set a guild-specific config value."""
    db = await get_db()
    await db.execute(
        "INSERT INTO guild_config (guild_id, key, value) VALUES (?, ?, ?) "
        "ON CONFLICT(guild_id, key) DO UPDATE SET value = excluded.value",
        (guild_id, key, value),
    )
    await db.commit()


async def get_all_guild_config(guild_id: str) -> dict[str, str]:
    """Get all config for a guild, merged with global (guild overrides global)."""
    global_cfg = await get_all_config()
    db = await get_db()
    cursor = await db.execute(
        "SELECT key, value FROM guild_config WHERE guild_id = ?",
        (guild_id,),
    )
    rows = await cursor.fetchall()
    guild_cfg = {row["key"]: row["value"] for row in rows}
    return {**global_cfg, **guild_cfg}


async def delete_guild_config(guild_id: str, key: str):
    """Delete a guild-specific config value (reverts to global default)."""
    db = await get_db()
    await db.execute(
        "DELETE FROM guild_config WHERE guild_id = ? AND key = ?",
        (guild_id, key),
    )
    await db.commit()


async def reset_guild_config(guild_id: str):
    """Reset ALL guild-specific config (revert everything to global defaults)."""
    db = await get_db()
    await db.execute("DELETE FROM guild_config WHERE guild_id = ?", (guild_id,))
    await db.commit()


# =============================================================================
# Conversation helpers
# =============================================================================

async def add_message(channel_id: str, role: str, content: str, provider: str | None = None):
    """Add a message to conversation history."""
    db = await get_db()
    await db.execute(
        "INSERT INTO conversations (channel_id, role, content, provider) VALUES (?, ?, ?, ?)",
        (channel_id, role, content, provider),
    )
    await db.commit()


async def get_messages(channel_id: str, limit: int = 20) -> list[dict]:
    """Get recent messages for a channel."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT role, content, provider, created_at FROM conversations "
        "WHERE channel_id = ? ORDER BY id DESC LIMIT ?",
        (channel_id, limit),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in reversed(rows)]


async def clear_messages(channel_id: str):
    """Delete all messages for a channel."""
    db = await get_db()
    await db.execute("DELETE FROM conversations WHERE channel_id = ?", (channel_id,))
    await db.commit()


async def list_channels() -> list[dict]:
    """List all channels with message counts."""
    db = await get_db()
    cursor = await db.execute(
        """
        SELECT channel_id, COUNT(*) as message_count, MAX(created_at) as last_active
        FROM conversations
        GROUP BY channel_id
        ORDER BY last_active DESC
        """
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


# =============================================================================
# Wizard helpers
# =============================================================================

async def get_wizard_state() -> dict:
    """Get the wizard state."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT completed, current_step, data FROM wizard_state WHERE id = 1"
    )
    row = await cursor.fetchone()
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
    """Update wizard state fields."""
    db = await get_db()
    updates = []
    params = []
    if completed is not None:
        updates.append("completed = ?")
        params.append(int(completed))
    if current_step is not None:
        updates.append("current_step = ?")
        params.append(current_step)
    if data is not None:
        updates.append("data = ?")
        params.append(json.dumps(data))
    if updates:
        await db.execute(
            f"UPDATE wizard_state SET {', '.join(updates)} WHERE id = 1", params
        )
        await db.commit()


# =============================================================================
# Session helpers
# =============================================================================

async def create_session(token: str, user_id: str, expires_at: str):
    """Store a session token."""
    db = await get_db()
    await db.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires_at),
    )
    await db.commit()


async def validate_session(token: str) -> dict | None:
    """Validate a session token, return session data or None."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT user_id, expires_at FROM sessions "
        "WHERE token = ? AND expires_at > datetime('now')",
        (token,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def delete_session(token: str):
    """Delete a session."""
    db = await get_db()
    await db.execute("DELETE FROM sessions WHERE token = ?", (token,))
    await db.commit()


async def close_db():
    """Close the database connection."""
    global _db
    if _db:
        await _db.close()
        _db = None


# =============================================================================
# Analytics helpers
# =============================================================================

def _calculate_cost(provider: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate estimated cost based on provider pricing."""
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
    provider: str | None = None,
    tokens_used: int | None = None,
    latency_ms: int | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
):
    """Log an analytics event with optional token tracking and cost calculation."""
    estimated_cost = None
    if provider and input_tokens is not None and output_tokens is not None:
        estimated_cost = _calculate_cost(provider, input_tokens, output_tokens)

    db = await get_db()
    await db.execute(
        """INSERT INTO analytics
           (event_type, guild_id, channel_id, user_id, provider,
            tokens_used, latency_ms, input_tokens, output_tokens, estimated_cost)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (event_type, guild_id, channel_id, user_id, provider,
         tokens_used, latency_ms, input_tokens, output_tokens, estimated_cost),
    )
    await db.commit()


async def get_analytics_summary(guild_id: str | None = None) -> dict:
    db = await get_db()
    where = "WHERE guild_id = ?" if guild_id else ""
    params = (guild_id,) if guild_id else ()

    cursor = await db.execute(
        f"SELECT COUNT(*) as total, event_type FROM analytics {where} GROUP BY event_type",
        params,
    )
    by_type = {row["event_type"]: row["total"] for row in await cursor.fetchall()}

    cursor2 = await db.execute(
        f"""SELECT DATE(created_at) as day, COUNT(*) as count
            FROM analytics {where}
            GROUP BY day ORDER BY day DESC LIMIT 30""",
        params,
    )
    daily = [dict(r) for r in await cursor2.fetchall()]

    where2 = "WHERE provider IS NOT NULL" + (" AND guild_id = ?" if guild_id else "")
    cursor3 = await db.execute(
        f"""SELECT provider,
                   COUNT(*) as count,
                   SUM(COALESCE(input_tokens, 0)) as total_input_tokens,
                   SUM(COALESCE(output_tokens, 0)) as total_output_tokens,
                   SUM(COALESCE(estimated_cost, 0)) as total_cost
            FROM analytics {where2}
            GROUP BY provider""",
        (guild_id,) if guild_id else (),
    )
    providers = [dict(r) for r in await cursor3.fetchall()]

    return {"by_type": by_type, "daily": daily, "providers": providers}


# =============================================================================
# FAQ helpers
# =============================================================================

async def add_faq(guild_id: str, question: str, answer: str, keywords: str, created_by: str) -> int:
    db = await get_db()
    cursor = await db.execute(
        "INSERT INTO faqs (guild_id, question, answer, match_keywords, created_by) VALUES (?, ?, ?, ?, ?)",
        (guild_id, question, answer, keywords, created_by),
    )
    await db.commit()
    return cursor.lastrowid


async def get_faqs(guild_id: str) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM faqs WHERE guild_id = ? ORDER BY id DESC",
        (guild_id,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def delete_faq(faq_id: int, guild_id: str) -> bool:
    db = await get_db()
    cursor = await db.execute(
        "DELETE FROM faqs WHERE id = ? AND guild_id = ?",
        (faq_id, guild_id),
    )
    await db.commit()
    return cursor.rowcount > 0


async def increment_faq_usage(faq_id: int):
    db = await get_db()
    await db.execute(
        "UPDATE faqs SET times_used = times_used + 1 WHERE id = ?", (faq_id,)
    )
    await db.commit()


# =============================================================================
# Permission helpers
# =============================================================================

async def get_allowed_roles(command_name: str, guild_id: str) -> list[str]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT role_id FROM command_permissions WHERE command_name = ? AND guild_id = ?",
        (command_name, guild_id),
    )
    rows = await cursor.fetchall()
    return [row["role_id"] for row in rows]


async def get_command_permissions(guild_id: str) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT command_name, role_id FROM command_permissions "
        "WHERE guild_id = ? ORDER BY command_name",
        (guild_id,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def add_command_permission(command_name: str, guild_id: str, role_id: str):
    db = await get_db()
    await db.execute(
        "INSERT OR IGNORE INTO command_permissions (command_name, guild_id, role_id) VALUES (?, ?, ?)",
        (command_name, guild_id, role_id),
    )
    await db.commit()


async def remove_command_permission(command_name: str, guild_id: str, role_id: str) -> bool:
    db = await get_db()
    cursor = await db.execute(
        "DELETE FROM command_permissions WHERE command_name = ? AND guild_id = ? AND role_id = ?",
        (command_name, guild_id, role_id),
    )
    await db.commit()
    return cursor.rowcount > 0


# =============================================================================
# Channel prompt helpers
# =============================================================================

async def get_channel_prompt(channel_id: str) -> str | None:
    db = await get_db()
    cursor = await db.execute(
        "SELECT system_prompt FROM channel_prompts WHERE channel_id = ?",
        (channel_id,),
    )
    row = await cursor.fetchone()
    return row["system_prompt"] if row else None


async def set_channel_prompt(channel_id: str, guild_id: str, system_prompt: str):
    db = await get_db()
    await db.execute(
        """INSERT INTO channel_prompts (channel_id, guild_id, system_prompt) VALUES (?, ?, ?)
           ON CONFLICT(channel_id) DO UPDATE SET system_prompt = excluded.system_prompt""",
        (channel_id, guild_id, system_prompt),
    )
    await db.commit()


async def delete_channel_prompt(channel_id: str):
    db = await get_db()
    await db.execute("DELETE FROM channel_prompts WHERE channel_id = ?", (channel_id,))
    await db.commit()


async def list_channel_prompts(guild_id: str) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT channel_id, system_prompt FROM channel_prompts WHERE guild_id = ?",
        (guild_id,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]