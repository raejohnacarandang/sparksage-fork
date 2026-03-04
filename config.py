from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

# Discord
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Provider selection
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()

# Free providers
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-r1:free")

# Paid providers (optional)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Bot settings
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1024"))
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "You are SparkSage, a helpful and friendly AI assistant in a Discord server. "
    "Be concise, helpful, and engaging.",
)

# Dashboard settings
DATABASE_PATH = os.getenv("DATABASE_PATH", "sparksage.db")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8000"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
JWT_SECRET = os.getenv("JWT_SECRET", "sparksage-dev-secret-change-me")


def _build_providers() -> dict:
    """Build the PROVIDERS dict from current module-level variables."""
    return {
        "gemini": {
            "name": "Google Gemini",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "api_key": GEMINI_API_KEY,
            "model": GEMINI_MODEL,
            "free": True,
        },
        "groq": {
            "name": "Groq",
            "base_url": "https://api.groq.com/openai/v1",
            "api_key": GROQ_API_KEY,
            "model": GROQ_MODEL,
            "free": True,
        },
        "openrouter": {
            "name": "OpenRouter",
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": OPENROUTER_API_KEY,
            "model": OPENROUTER_MODEL,
            "free": True,
        },
        "anthropic": {
            "name": "Anthropic Claude",
            "base_url": "https://api.anthropic.com/v1/",
            "api_key": ANTHROPIC_API_KEY,
            "model": ANTHROPIC_MODEL,
            "free": False,
        },
        "openai": {
            "name": "OpenAI",
            "base_url": "https://api.openai.com/v1",
            "api_key": OPENAI_API_KEY,
            "model": OPENAI_MODEL,
            "free": False,
        },
    }


# Provider configs — all use the OpenAI-compatible SDK
PROVIDERS = _build_providers()

# Build the free fallback chain (order matters)
FREE_FALLBACK_CHAIN = ["gemini", "groq", "openrouter"]

# Provider pricing (cost per 1k tokens in USD)
PROVIDER_PRICING = {
    "gemini": {
        "input_cost_per_1k":  0.0,
        "output_cost_per_1k": 0.0,
        "monthly_budget":     0.0,
        "free":               True,
    },
    "groq": {
        "input_cost_per_1k":  0.0,
        "output_cost_per_1k": 0.0,
        "monthly_budget":     0.0,
        "free":               True,
    },
    "openrouter": {
        "input_cost_per_1k":  0.0,
        "output_cost_per_1k": 0.0,
        "monthly_budget":     0.0,
        "free":               True,
    },
    "anthropic": {
        "input_cost_per_1k":  0.003,   # claude-sonnet-4-6 input
        "output_cost_per_1k": 0.015,   # claude-sonnet-4-6 output
        "monthly_budget":     50.0,
        "free":               False,
    },
    "openai": {
        "input_cost_per_1k":  0.00015,  # gpt-4o-mini input
        "output_cost_per_1k": 0.0006,   # gpt-4o-mini output
        "monthly_budget":     50.0,
        "free":               False,
    },
}


def reload_from_db(db_config: dict[str, str]):
    """Reload module-level config variables from DB values."""
    import config

    mapping = {
        "DISCORD_TOKEN": str,
        "AI_PROVIDER": lambda v: v.lower(),
        "GEMINI_API_KEY": str,
        "GEMINI_MODEL": str,
        "GROQ_API_KEY": str,
        "GROQ_MODEL": str,
        "OPENROUTER_API_KEY": str,
        "OPENROUTER_MODEL": str,
        "ANTHROPIC_API_KEY": str,
        "ANTHROPIC_MODEL": str,
        "OPENAI_API_KEY": str,
        "OPENAI_MODEL": str,
        "BOT_PREFIX": str,
        "MAX_TOKENS": int,
        "SYSTEM_PROMPT": str,
        "ADMIN_PASSWORD": str,
        "DISCORD_CLIENT_ID": str,
        "DISCORD_CLIENT_SECRET": str,
        "JWT_SECRET": str,
    }

    for key, converter in mapping.items():
        if key in db_config and db_config[key]:
            setattr(config, key, converter(db_config[key]))

    config.PROVIDERS = config._build_providers()
