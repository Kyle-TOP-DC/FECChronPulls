from fastapi import Header, HTTPException

from .config import ADMIN_TOKEN


def require_admin(x_admin_token: str = Header(default="")) -> None:
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")
