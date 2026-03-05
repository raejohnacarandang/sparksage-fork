from __future__ import annotations

import os
import json
import sys
import asyncio
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from api.auth import decode_token

router = APIRouter()
security = HTTPBearer()

PLUGINS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "plugins")


def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


def _get_bot():
    try:
        import bot as bot_module
        return bot_module.bot
    except Exception:
        return None


def _get_all_plugins(loaded_extensions: set = None) -> list[dict]:
    plugins = []
    if not os.path.isdir(PLUGINS_DIR):
        return plugins

    loaded_extensions = loaded_extensions or set()

    for folder in os.listdir(PLUGINS_DIR):
        folder_path = os.path.join(PLUGINS_DIR, folder)
        manifest_path = os.path.join(folder_path, "manifest.json")
        if os.path.isdir(folder_path) and os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)
                cog_name = manifest["cog"].replace(".py", "")
                ext_name = f"plugins.{folder}.{cog_name}"
                manifest["enabled"] = ext_name in loaded_extensions
                manifest["folder"] = folder
                manifest["ext_name"] = ext_name
                plugins.append(manifest)
            except (json.JSONDecodeError, KeyError):
                continue
    return plugins


@router.get("/api/plugins")
async def list_plugins(_=Depends(require_auth)):
    bot = _get_bot()
    loaded = set(bot.extensions.keys()) if bot else set()
    return _get_all_plugins(loaded)


@router.post("/api/plugins/{name}/enable")
async def enable_plugin(name: str, _=Depends(require_auth)):
    bot = _get_bot()
    if not bot:
        raise HTTPException(status_code=503, detail="Bot is not running")

    plugins = _get_all_plugins(set(bot.extensions.keys()))
    plugin = next((p for p in plugins if p["name"].lower() == name.lower()), None)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")

    ext_name = plugin["ext_name"]

    if ext_name in bot.extensions:
        return {"message": f"Plugin '{name}' is already enabled"}

    # Add plugin parent dir to path
    plugin_dir = os.path.join(PLUGINS_DIR, plugin["folder"])
    parent_dir = os.path.dirname(plugin_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    try:
        await bot.load_extension(ext_name)
        # Schedule sync as background task to avoid aiohttp context issues
        bot.loop.create_task(bot.tree.sync())
        return {"message": f"Plugin '{name}' enabled successfully"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/plugins/{name}/disable")
async def disable_plugin(name: str, _=Depends(require_auth)):
    bot = _get_bot()
    if not bot:
        raise HTTPException(status_code=503, detail="Bot is not running")

    plugins = _get_all_plugins(set(bot.extensions.keys()))
    plugin = next((p for p in plugins if p["name"].lower() == name.lower()), None)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")

    ext_name = plugin["ext_name"]

    if ext_name not in bot.extensions:
        return {"message": f"Plugin '{name}' is not enabled"}

    try:
        await bot.unload_extension(ext_name)
        # Schedule sync as background task
        bot.loop.create_task(bot.tree.sync())
        return {"message": f"Plugin '{name}' disabled successfully"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
