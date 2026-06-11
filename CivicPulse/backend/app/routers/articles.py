from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Article, EngagementEvent, User
from ..schemas import ArticleOut, EngagementIn

router = APIRouter(prefix="/api/articles", tags=["articles"])


@router.get("", response_model=list[ArticleOut])
def feed(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Article)
        .where(Article.published.is_(True))
        .order_by(Article.published_at.desc())
        .limit(min(limit, 100))
        .offset(offset)
    )
    return list(rows)


@router.get("/{article_id}", response_model=ArticleOut)
def get_article(article_id: int, db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if article is None or not article.published:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.post("/{article_id}/events")
def record_event(article_id: int, payload: EngagementIn, db: Session = Depends(get_db)):
    if db.get(Article, article_id) is None:
        raise HTTPException(status_code=404, detail="Article not found")
    if db.get(User, payload.user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    db.add(EngagementEvent(user_id=payload.user_id, article_id=article_id, event=payload.event))
    db.commit()
    return {"ok": True}
