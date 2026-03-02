from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from api.auth import decode_token

router = APIRouter()
security = HTTPBearer()


def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


class ReviewRequest(BaseModel):
    content: str


@router.post("")
async def review(body: ReviewRequest, _=Depends(require_auth)):
    if not body.content:
        return {"error": "Content required"}
    try:
        import providers
        response, provider_name = providers.chat(
            messages=[{"role": "user", "content": f"Review this code and provide detailed feedback on bugs, style, and improvements:\n\n```\n{body.content}\n```"}],
            system_prompt="You are an expert code reviewer. Provide clear, actionable feedback.",
        )
        return {"result": response, "provider": provider_name}
    except Exception as e:
        return {"error": str(e)}