import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .routers import actions, admin, articles, messages, reps, users
from .seed import seed_demo_data
from .services import congress

logging.basicConfig(level=logging.INFO)

ADMIN_DIR = Path(__file__).resolve().parent.parent / "admin"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    congress.load_data()
    seed_demo_data()
    yield


app = FastAPI(title="CivicPulse API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(reps.router)
app.include_router(articles.router)
app.include_router(messages.router)
app.include_router(actions.router)
app.include_router(admin.router)

# Admin dashboard (single-page app) at /admin
app.mount("/admin", StaticFiles(directory=str(ADMIN_DIR), html=True), name="admin")


@app.get("/")
def root():
    return {"app": "CivicPulse", "docs": "/docs", "admin": "/admin"}
