from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Users ----------

class UserRegister(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    zip_code: str = Field(min_length=5, max_length=10)
    name: str | None = None
    email: str | None = None
    phone: str | None = None


class UserUpdate(BaseModel):
    zip_code: str | None = None
    name: str | None = None
    email: str | None = None
    phone: str | None = None


class UserOut(ORMModel):
    id: int
    device_id: str
    zip_code: str
    name: str | None
    email: str | None
    phone: str | None
    created_at: datetime


class DeviceTokenIn(BaseModel):
    token: str = Field(min_length=8, max_length=200)


# ---------- Representatives ----------

class Representative(BaseModel):
    bioguide_id: str
    name: str
    role: Literal["senator", "representative"]
    party: str | None = None
    state: str
    district: int | None = None
    phone: str | None = None
    contact_form_url: str | None = None
    website: str | None = None
    office_address: str | None = None
    photo_url: str | None = None


class RepLookupOut(BaseModel):
    zip: str
    state: str
    districts: list[int]
    representatives: list[Representative]


# ---------- Articles ----------

class ArticleOut(ORMModel):
    id: int
    title: str
    source: str | None
    url: str
    summary: str | None
    admin_note: str | None
    image_url: str | None
    tags: list
    published: bool
    published_at: datetime | None
    created_at: datetime


class ArticleCreate(BaseModel):
    title: str
    url: str
    source: str | None = None
    summary: str | None = None
    admin_note: str | None = None
    image_url: str | None = None
    tags: list[str] = []
    published: bool = True
    article_text: str | None = None  # optional raw text used for AI summarization


class ArticleUpdate(BaseModel):
    title: str | None = None
    url: str | None = None
    source: str | None = None
    summary: str | None = None
    admin_note: str | None = None
    image_url: str | None = None
    tags: list[str] | None = None
    published: bool | None = None


class EngagementIn(BaseModel):
    user_id: int
    event: Literal["view", "read", "share", "action_open"]


# ---------- Messages to Congress ----------

class MessageDraftIn(BaseModel):
    user_id: int
    article_id: int
    rep_bioguide_id: str
    thoughts: str = Field(min_length=1, max_length=4000)


class MessageDraftOut(BaseModel):
    subject: str
    body: str


class MessageCreate(BaseModel):
    user_id: int
    article_id: int | None = None
    rep_bioguide_id: str
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1)
    delivery_method: Literal["call", "email", "webform"] = "webform"


class MessageOut(ORMModel):
    id: int
    user_id: int
    article_id: int | None
    rep_bioguide_id: str
    rep_name: str
    rep_role: str | None
    rep_state: str | None
    subject: str
    body: str
    delivery_method: str
    status: str
    office_reply: str | None
    replied_at: datetime | None
    created_at: datetime


class MessageReplyIn(BaseModel):
    office_reply: str = Field(min_length=1)


# ---------- Candidates / actions ----------

class CandidateOut(ORMModel):
    id: int
    name: str
    office: str
    state: str
    party: str | None
    blurb: str | None
    website: str | None
    donate_url: str | None
    photo_url: str | None


class CandidateCreate(BaseModel):
    name: str
    office: str
    state: str = Field(min_length=2, max_length=2)
    party: str | None = None
    blurb: str | None = None
    website: str | None = None
    donate_url: str | None = None
    photo_url: str | None = None
    active: bool = True


class VoterRegistrationOut(BaseModel):
    state: str
    register_url: str
    check_url: str
    note: str | None = None


# ---------- Admin: push + dashboards ----------

class PushIn(BaseModel):
    article_id: int | None = None
    title: str = Field(min_length=1, max_length=200)
    note: str = Field(min_length=1, max_length=1000)


class PushResult(BaseModel):
    sent: int
    failed: int
    detail: str | None = None


class ArticleEngagementRow(BaseModel):
    article_id: int
    title: str
    published: bool
    views: int
    reads: int
    shares: int
    action_opens: int
    messages_sent: int


class OfficeContactRow(BaseModel):
    rep_bioguide_id: str
    rep_name: str
    rep_role: str | None
    rep_state: str | None
    message_count: int
    replied_count: int
    last_contacted: datetime | None
