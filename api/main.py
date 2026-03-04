from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import (
    auth, config, providers, bot, conversations, wizard,
    review, analytics, costs, plugins, permissions,
    channel_prompts, quota, faq, websocket,
)

import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    await db.sync_env_to_db()
    yield
    await db.close_db()


def create_app() -> FastAPI:
    app = FastAPI(title="SparkSage API", version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            # Local development
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "ws://localhost:3000",
            "ws://127.0.0.1:3000",
            # Vercel frontend — HTTP and WebSocket
            "https://sparksage-fork.vercel.app",
            "wss://sparksage-fork.vercel.app",
            # Railway backend (needed for same-origin API calls)
            "https://sparksage-fork-production.up.railway.app",
            "wss://sparksage-fork-production.up.railway.app",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router,            prefix="/api/auth",            tags=["auth"])
    app.include_router(config.router,          prefix="/api/config",          tags=["config"])
    app.include_router(providers.router,       prefix="/api/providers",       tags=["providers"])
    app.include_router(bot.router,             prefix="/api/bot",             tags=["bot"])
    app.include_router(conversations.router,   prefix="/api/conversations",   tags=["conversations"])
    app.include_router(wizard.router,          prefix="/api/wizard",          tags=["wizard"])
    app.include_router(review.router,          prefix="/api/review",          tags=["review"])
    app.include_router(analytics.router)
    app.include_router(costs.router)
    app.include_router(plugins.router)
    app.include_router(permissions.router,     prefix="/api/permissions",     tags=["permissions"])
    app.include_router(channel_prompts.router, prefix="/api/channel-prompts", tags=["channel-prompts"])
    app.include_router(quota.router)
    app.include_router(faq.router,             prefix="/api/faqs",            tags=["faqs"])
    app.include_router(websocket.router)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    return app