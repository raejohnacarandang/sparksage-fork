from __future__ import annotations

import os
import json
import sys
import zipfile
import tempfile
import io
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from api.auth import decode_token
import db as database

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


def _write_plugin_to_disk(name: str, cog: str, code: str):
    """Write plugin code from DB to disk so bot can load it."""
    plugin_dir = os.path.join(PLUGINS_DIR, name)
    os.makedirs(plugin_dir, exist_ok=True)
    cog_path = os.path.join(plugin_dir, cog)
    with open(cog_path, "w", encoding="utf-8") as f:
        f.write(code)
    # Ensure __init__.py exists
    init_path = os.path.join(plugin_dir, "__init__.py")
    if not os.path.exists(init_path):
        open(init_path, "w").close()


@router.get("/api/plugins")
async def list_plugins(_=Depends(require_auth)):
    """List all plugins from DB and filesystem."""
    bot = _get_bot()
    loaded = set(bot.extensions.keys()) if bot else set()

    # Get DB plugins
    db_plugins = await database.list_db_plugins()
    db_names = {p["name"] for p in db_plugins}

    # Also scan filesystem for legacy plugins
    fs_plugins = []
    if os.path.isdir(PLUGINS_DIR):
        for folder in os.listdir(PLUGINS_DIR):
            folder_path = os.path.join(PLUGINS_DIR, folder)
            manifest_path = os.path.join(folder_path, "manifest.json")
            if os.path.isdir(folder_path) and os.path.exists(manifest_path) and folder not in db_names:
                try:
                    with open(manifest_path, "r") as f:
                        manifest = json.load(f)
                    cog_name = manifest["cog"].replace(".py", "")
                    ext_name = f"plugins.{folder}.{cog_name}"
                    fs_plugins.append({
                        "name": manifest.get("name", folder),
                        "version": manifest.get("version", "1.0.0"),
                        "author": manifest.get("author", "community"),
                        "description": manifest.get("description", ""),
                        "cog": manifest.get("cog", ""),
                        "enabled": ext_name in loaded,
                        "source": "filesystem",
                    })
                except Exception:
                    continue

    # Merge DB plugins with live enabled status
    result = []
    for p in db_plugins:
        ext_name = f"plugins.{p['name']}.{p['cog'].replace('.py', '')}"
        result.append({
            **p,
            "enabled": ext_name in loaded,
            "source": "database",
            "installed_at": p["installed_at"].isoformat() if p.get("installed_at") else None,
        })

    return result + fs_plugins


@router.post("/api/plugins/upload")
async def upload_plugin(file: UploadFile = File(...), _=Depends(require_auth)):
    """Upload a ZIP file containing manifest.json and cog .py file."""
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="File must be a .zip archive")

    contents = await file.read()

    try:
        with zipfile.ZipFile(io.BytesIO(contents)) as zf:
            names = zf.namelist()

            # Find manifest.json
            manifest_files = [n for n in names if n.endswith("manifest.json")]
            if not manifest_files:
                raise HTTPException(status_code=400, detail="No manifest.json found in ZIP")

            manifest_data = json.loads(zf.read(manifest_files[0]).decode("utf-8"))

            # Validate manifest
            required = ["name", "version", "cog"]
            for field in required:
                if field not in manifest_data:
                    raise HTTPException(status_code=400, detail=f"manifest.json missing field: {field}")

            plugin_name = manifest_data["name"]
            cog_file = manifest_data["cog"]

            # Find cog .py file
            cog_files = [n for n in names if n.endswith(cog_file)]
            if not cog_files:
                raise HTTPException(status_code=400, detail=f"Cog file '{cog_file}' not found in ZIP")

            cog_code = zf.read(cog_files[0]).decode("utf-8")

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")

    # Save to DB
    await database.init_plugins_table()
    await database.save_plugin(
        name=plugin_name,
        version=manifest_data.get("version", "1.0.0"),
        author=manifest_data.get("author", "community"),
        description=manifest_data.get("description", ""),
        cog=cog_file,
        code=cog_code,
        manifest=json.dumps(manifest_data),
    )

    # Write to disk so bot can load it
    _write_plugin_to_disk(plugin_name, cog_file, cog_code)

    return {
        "message": f"Plugin '{plugin_name}' installed successfully",
        "plugin": {
            "name": plugin_name,
            "version": manifest_data.get("version"),
            "author": manifest_data.get("author"),
            "description": manifest_data.get("description"),
            "cog": cog_file,
        }
    }


@router.post("/api/plugins/{name}/enable")
async def enable_plugin(name: str, _=Depends(require_auth)):
    bot = _get_bot()
    if not bot:
        raise HTTPException(status_code=503, detail="Bot is not running")

    # Try to restore from DB if not on disk
    plugin_row = await database.get_plugin_code(name)
    if plugin_row:
        _write_plugin_to_disk(name, plugin_row["cog"], plugin_row["code"])

    ext_name = None
    # Find ext_name from filesystem
    plugin_dir = os.path.join(PLUGINS_DIR, name)
    manifest_path = os.path.join(plugin_dir, "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        cog_name = manifest["cog"].replace(".py", "")
        ext_name = f"plugins.{name}.{cog_name}"
    elif plugin_row:
        cog_name = plugin_row["cog"].replace(".py", "")
        ext_name = f"plugins.{name}.{cog_name}"
    else:
        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")

    if ext_name in bot.extensions:
        return {"message": f"Plugin '{name}' is already enabled"}

    parent_dir = os.path.dirname(PLUGINS_DIR)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    try:
        await bot.load_extension(ext_name)
        bot.loop.create_task(bot.tree.sync())
        await database.set_plugin_enabled(name, True)
        return {"message": f"Plugin '{name}' enabled successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/plugins/{name}/disable")
async def disable_plugin(name: str, _=Depends(require_auth)):
    bot = _get_bot()
    if not bot:
        raise HTTPException(status_code=503, detail="Bot is not running")

    plugin_dir = os.path.join(PLUGINS_DIR, name)
    manifest_path = os.path.join(plugin_dir, "manifest.json")

    if os.path.exists(manifest_path):
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        cog_name = manifest["cog"].replace(".py", "")
        ext_name = f"plugins.{name}.{cog_name}"
    else:
        plugin_row = await database.get_plugin_code(name)
        if not plugin_row:
            raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")
        cog_name = plugin_row["cog"].replace(".py", "")
        ext_name = f"plugins.{name}.{cog_name}"

    if ext_name not in bot.extensions:
        return {"message": f"Plugin '{name}' is not enabled"}

    try:
        await bot.unload_extension(ext_name)
        bot.loop.create_task(bot.tree.sync())
        await database.set_plugin_enabled(name, False)
        return {"message": f"Plugin '{name}' disabled successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/plugins/{name}")
async def delete_plugin(name: str, _=Depends(require_auth)):
    """Remove a plugin from DB and disk."""
    bot = _get_bot()

    # Disable first if enabled
    if bot:
        plugin_dir = os.path.join(PLUGINS_DIR, name)
        manifest_path = os.path.join(plugin_dir, "manifest.json")
        if os.path.exists(manifest_path):
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
            ext_name = f"plugins.{name}.{manifest['cog'].replace('.py', '')}"
            if ext_name in bot.extensions:
                await bot.unload_extension(ext_name)
                bot.loop.create_task(bot.tree.sync())

    await database.delete_plugin(name)
    return {"message": f"Plugin '{name}' deleted"}