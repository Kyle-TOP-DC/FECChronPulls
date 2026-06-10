from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DeviceToken, User
from ..schemas import DeviceTokenIn, UserOut, UserRegister, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/register", response_model=UserOut)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.device_id == payload.device_id))
    if user is None:
        user = User(device_id=payload.device_id)
        db.add(user)
    user.zip_code = payload.zip_code
    if payload.name is not None:
        user.name = payload.name
    if payload.email is not None:
        user.email = payload.email
    if payload.phone is not None:
        user.phone = payload.phone
    db.commit()
    db.refresh(user)
    return user


def _get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    user = _get_user(db, user_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/device-token")
def add_device_token(user_id: int, payload: DeviceTokenIn, db: Session = Depends(get_db)):
    user = _get_user(db, user_id)
    existing = db.scalar(select(DeviceToken).where(DeviceToken.token == payload.token))
    if existing is None:
        db.add(DeviceToken(user_id=user.id, token=payload.token))
    else:
        existing.user_id = user.id
    db.commit()
    return {"ok": True}
