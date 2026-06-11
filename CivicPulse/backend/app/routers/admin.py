from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import (
    Article,
    Candidate,
    CongressMessage,
    DeviceToken,
    EngagementEvent,
    PushLog,
    utcnow,
)
from ..schemas import (
    ArticleCreate,
    ArticleEngagementRow,
    ArticleOut,
    ArticleUpdate,
    CandidateCreate,
    CandidateOut,
    MessageOut,
    MessageReplyIn,
    OfficeContactRow,
    PushIn,
    PushResult,
)
from ..services import apns, summarize

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# ---------- Article curation ----------

@router.get("/articles", response_model=list[ArticleOut])
def all_articles(db: Session = Depends(get_db)):
    return list(db.scalars(select(Article).order_by(Article.created_at.desc())))


@router.post("/articles", response_model=ArticleOut)
def create_article(payload: ArticleCreate, db: Session = Depends(get_db)):
    summary = payload.summary
    if not summary and payload.article_text:
        summary = summarize.summarize_article(payload.title, payload.source, payload.article_text)
    article = Article(
        title=payload.title,
        url=payload.url,
        source=payload.source,
        summary=summary,
        admin_note=payload.admin_note,
        image_url=payload.image_url,
        tags=payload.tags,
        published=payload.published,
        published_at=utcnow() if payload.published else None,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


@router.patch("/articles/{article_id}", response_model=ArticleOut)
def update_article(article_id: int, payload: ArticleUpdate, db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("published") and not article.published:
        article.published_at = utcnow()
    for field, value in data.items():
        setattr(article, field, value)
    db.commit()
    db.refresh(article)
    return article


@router.delete("/articles/{article_id}")
def delete_article(article_id: int, db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    article.published = False
    db.commit()
    return {"ok": True, "detail": "Article unpublished"}


# ---------- Push notifications ----------

@router.post("/push", response_model=PushResult)
def send_push(payload: PushIn, db: Session = Depends(get_db)):
    if payload.article_id is not None and db.get(Article, payload.article_id) is None:
        raise HTTPException(status_code=404, detail="Article not found")
    tokens = [t for (t,) in db.execute(select(DeviceToken.token))]
    sent, failed = apns.send_push(tokens, payload.title, payload.note, payload.article_id)
    db.add(
        PushLog(
            article_id=payload.article_id,
            title=payload.title,
            note=payload.note,
            sent_count=sent,
            failed_count=failed,
        )
    )
    db.commit()
    detail = None if apns.configured() else "APNs not configured — push logged only"
    return PushResult(sent=sent, failed=failed, detail=detail)


# ---------- Dashboards ----------

@router.get("/stats/engagement", response_model=list[ArticleEngagementRow])
def engagement_stats(db: Session = Depends(get_db)):
    event_counts = dict()
    rows = db.execute(
        select(EngagementEvent.article_id, EngagementEvent.event, func.count())
        .group_by(EngagementEvent.article_id, EngagementEvent.event)
    )
    for article_id, event, count in rows:
        event_counts.setdefault(article_id, {})[event] = count

    message_counts = dict(
        db.execute(
            select(CongressMessage.article_id, func.count())
            .where(CongressMessage.article_id.is_not(None))
            .group_by(CongressMessage.article_id)
        ).all()
    )

    out = []
    for article in db.scalars(select(Article).order_by(Article.created_at.desc())):
        counts = event_counts.get(article.id, {})
        out.append(
            ArticleEngagementRow(
                article_id=article.id,
                title=article.title,
                published=article.published,
                views=counts.get("view", 0),
                reads=counts.get("read", 0),
                shares=counts.get("share", 0),
                action_opens=counts.get("action_open", 0),
                messages_sent=message_counts.get(article.id, 0),
            )
        )
    return out


@router.get("/stats/contacts", response_model=list[OfficeContactRow])
def contact_stats(db: Session = Depends(get_db)):
    rows = db.execute(
        select(
            CongressMessage.rep_bioguide_id,
            CongressMessage.rep_name,
            CongressMessage.rep_role,
            CongressMessage.rep_state,
            func.count(),
            func.sum(case((CongressMessage.status == "replied", 1), else_=0)),
            func.max(CongressMessage.created_at),
        ).group_by(
            CongressMessage.rep_bioguide_id,
            CongressMessage.rep_name,
            CongressMessage.rep_role,
            CongressMessage.rep_state,
        )
    )
    out = []
    for bioguide, name, role, state, count, replied, last in rows:
        out.append(
            OfficeContactRow(
                rep_bioguide_id=bioguide,
                rep_name=name,
                rep_role=role,
                rep_state=state,
                message_count=count,
                replied_count=int(replied or 0),
                last_contacted=last,
            )
        )
    out.sort(key=lambda r: r.message_count, reverse=True)
    return out


@router.get("/messages", response_model=list[MessageOut])
def office_messages(rep_bioguide_id: str | None = None, db: Session = Depends(get_db)):
    query = select(CongressMessage).order_by(CongressMessage.created_at.desc())
    if rep_bioguide_id:
        query = query.where(CongressMessage.rep_bioguide_id == rep_bioguide_id)
    return list(db.scalars(query))


@router.post("/messages/{message_id}/reply", response_model=MessageOut)
def log_office_reply(message_id: int, payload: MessageReplyIn, db: Session = Depends(get_db)):
    message = db.get(CongressMessage, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    message.office_reply = payload.office_reply
    message.status = "replied"
    message.replied_at = datetime.now(timezone.utc)
    db.commit()

    # Let the constituent know their office wrote back.
    tokens = [
        t for (t,) in db.execute(
            select(DeviceToken.token).where(DeviceToken.user_id == message.user_id)
        )
    ]
    apns.send_push(
        tokens,
        f"Reply from {message.rep_name}'s office",
        payload.office_reply[:150],
        message.article_id,
    )
    db.refresh(message)
    return message


# ---------- Candidates ----------

@router.post("/candidates", response_model=CandidateOut)
def create_candidate(payload: CandidateCreate, db: Session = Depends(get_db)):
    candidate = Candidate(**payload.model_dump())
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.delete("/candidates/{candidate_id}")
def deactivate_candidate(candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate.active = False
    db.commit()
    return {"ok": True}
