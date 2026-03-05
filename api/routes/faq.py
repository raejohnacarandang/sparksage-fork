from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from api.auth import decode_token
import db

router = APIRouter()
security = HTTPBearer()

def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload

class FAQCreate(BaseModel):
    guild_id: str
    question: str
    answer: str
    match_keywords: str
    created_by: str = "dashboard"

@router.get("")
async def list_faqs(guild_id: str = "", _=Depends(require_auth)):
    try:
        if guild_id:
            return await db.get_faqs(guild_id)
        pool = await db.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM faqs ORDER BY id DESC")
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
async def create_faq(item: FAQCreate, _=Depends(require_auth)):
    try:
        faq_id = await db.add_faq(
            guild_id=item.guild_id,
            question=item.question,
            answer=item.answer,
            keywords=item.match_keywords,
            created_by=item.created_by,
        )
        return {"id": faq_id, **item.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{faq_id}")
async def delete_faq(faq_id: int, _=Depends(require_auth)):
    try:
        pool = await db.get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("DELETE FROM faqs WHERE id = $1", faq_id)
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail=f"FAQ {faq_id} not found")
        return {"deleted": True, "id": faq_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))