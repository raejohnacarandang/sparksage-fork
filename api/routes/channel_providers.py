from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from api.deps import get_current_user
import db

router = APIRouter()

class ChannelProviderSet(BaseModel):
    channel_id: str
    provider: str

@router.get("")
async def list_channel_providers(_=Depends(get_current_user)):
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT key, value FROM config WHERE key LIKE 'CHANNEL_PROVIDER_%'"
        )
    return [{"channel_id": r["key"].replace("CHANNEL_PROVIDER_", ""), "provider": r["value"]} for r in rows]

@router.post("")
async def set_channel_provider(body: ChannelProviderSet, _=Depends(get_current_user)):
    await db.set_config(f"CHANNEL_PROVIDER_{body.channel_id}", body.provider)
    return {"success": True, "channel_id": body.channel_id, "provider": body.provider}

@router.delete("/{channel_id}")
async def delete_channel_provider(channel_id: str, _=Depends(get_current_user)):
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM config WHERE key = $1", f"CHANNEL_PROVIDER_{channel_id}")
    return {"deleted": True, "channel_id": channel_id}