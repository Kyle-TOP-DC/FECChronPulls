"""Demo content so a fresh install has something on screen."""
from sqlalchemy import select

from .database import SessionLocal
from .models import Article, Candidate, utcnow

_DEMO_ARTICLES = [
    {
        "title": "What the New AI Safety Bill Would Actually Do",
        "source": "Tech Oversight Daily",
        "url": "https://www.congress.gov/",
        "summary": (
            "A bipartisan bill would require frontier AI developers to run pre-deployment "
            "safety evaluations and report results to a new federal office. Supporters say "
            "it codifies practices leading labs already follow; critics worry about "
            "compliance costs for startups."
        ),
        "admin_note": "This is the bill we expect a committee vote on this month — worth a close read.",
        "tags": ["ai-safety", "legislation"],
    },
    {
        "title": "Super PACs Are Spending Big on AI Policy Races",
        "source": "Tech Oversight Daily",
        "url": "https://www.fec.gov/data/",
        "summary": (
            "Independent-expenditure committees focused on AI policy have raised tens of "
            "millions this cycle, concentrating spending in a handful of competitive "
            "primaries. Disclosure filings show most spending on digital ads."
        ),
        "admin_note": "Follow the money: this connects directly to our FEC tracker work.",
        "tags": ["elections", "money-in-politics"],
    },
]

_DEMO_CANDIDATES = [
    {
        "name": "Sample Candidate",
        "office": "U.S. House, CA-11",
        "state": "CA",
        "party": "Nonpartisan example",
        "blurb": "Demo entry — replace via the admin dashboard with real endorsed candidates.",
        "website": "https://example.org",
    },
]


def seed_demo_data() -> None:
    db = SessionLocal()
    try:
        if db.scalar(select(Article.id).limit(1)) is None:
            for item in _DEMO_ARTICLES:
                db.add(Article(**item, published=True, published_at=utcnow()))
        if db.scalar(select(Candidate.id).limit(1)) is None:
            for item in _DEMO_CANDIDATES:
                db.add(Candidate(**item))
        db.commit()
    finally:
        db.close()
