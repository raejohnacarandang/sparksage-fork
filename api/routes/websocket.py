from __future__ import annotations

import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# Connected WebSocket clients
_clients: list[WebSocket] = []


async def broadcast(data: dict):
    """Send data to all connected WebSocket clients."""
    dead = []
    for ws in _clients:
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _clients.remove(ws)


@router.websocket("/ws/stats")
async def stats_websocket(websocket: WebSocket):
    """WebSocket endpoint that streams real-time bot stats every 3 seconds."""
    await websocket.accept()
    _clients.append(websocket)
    try:
        while True:
            try:
                stats = _get_stats()
                await websocket.send_json(stats)
            except Exception as e:
                await websocket.send_json({"error": str(e)})

            # Wait 3 seconds, but also listen for client messages (ping/pong)
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=3.0)
            except asyncio.TimeoutError:
                pass  # No message from client — that's fine, just continue loop

    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _clients:
            _clients.remove(websocket)


def _get_stats() -> dict:
    """Get current bot stats."""
    try:
        import bot as bot_module
        b = bot_module.bot

        if not b or not b.is_ready():
            return {"online": False}

        return {
            "online": True,
            "latency_ms": round(b.latency * 1000, 1) if b.latency >= 0 else None,
            "guild_count": len(b.guilds),
            "guilds": [
                {
                    "id": str(g.id),
                    "name": g.name,
                    "member_count": g.member_count,
                }
                for g in b.guilds
            ],
            "username": str(b.user) if b.user else None,
        }
    except Exception as e:
        return {"online": False, "error": str(e)}