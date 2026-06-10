from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Article, CongressMessage, User
from ..schemas import MessageCreate, MessageDraftIn, MessageDraftOut, MessageOut
from ..services import congress, summarize

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.post("/draft", response_model=MessageDraftOut)
def draft(payload: MessageDraftIn, db: Session = Depends(get_db)):
    user = db.get(User, payload.user_id)
    article = db.get(Article, payload.article_id)
    rep = congress.get_member(payload.rep_bioguide_id)
    if user is None or article is None:
        raise HTTPException(status_code=404, detail="User or article not found")
    if rep is None:
        raise HTTPException(status_code=404, detail="Representative not found")
    subject, body = summarize.draft_message(user, article, rep, payload.thoughts)
    return MessageDraftOut(subject=subject, body=body)


@router.post("", response_model=MessageOut)
def create_message(payload: MessageCreate, db: Session = Depends(get_db)):
    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.article_id is not None and db.get(Article, payload.article_id) is None:
        raise HTTPException(status_code=404, detail="Article not found")
    rep = congress.get_member(payload.rep_bioguide_id)
    if rep is None:
        raise HTTPException(status_code=404, detail="Representative not found")

    message = CongressMessage(
        user_id=user.id,
        article_id=payload.article_id,
        rep_bioguide_id=rep.bioguide_id,
        rep_name=rep.name,
        rep_role=rep.role,
        rep_state=rep.state,
        subject=payload.subject,
        body=payload.body,
        delivery_method=payload.delivery_method,
        status="sent",
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.get("", response_model=list[MessageOut])
def list_messages(user_id: int, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(CongressMessage)
        .where(CongressMessage.user_id == user_id)
        .order_by(CongressMessage.created_at.desc())
    )
    return list(rows)
