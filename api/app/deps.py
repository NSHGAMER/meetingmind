from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_token
from .services.hindsight_gateway import MemoryGateway, get_gateway
from .services.llm import LLMClient, get_llm_client

bearer = HTTPBearer(auto_error=False)


def get_memory() -> MemoryGateway:
    return get_gateway()


def get_llm() -> LLMClient:
    return get_llm_client()


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not creds:
        raise HTTPException(401, "Not authenticated")
    uid = decode_token(creds.credentials)
    user = db.get(User, uid) if uid else None
    if not user:
        raise HTTPException(401, "Invalid or expired token")
    return user


def owned(db: Session, model, obj_id: int, user: User):
    """Fetch a row only if it belongs to the user; 404 (not 403) so existence is not leaked."""
    obj = db.get(model, obj_id)
    if not obj or obj.user_id != user.id:
        raise HTTPException(404, f"{model.__name__} not found")
    return obj
