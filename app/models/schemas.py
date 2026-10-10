from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ContentType = Literal["blog", "linkedin", "instagram", "email", "twitter"]
Tone = Literal["professional", "friendly", "technical", "persuasive", "casual"]
Audience = Literal["beginners", "developers", "business", "general"]
Length = Literal["short", "medium", "long"]


class AuthIn(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=6, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str


class GenerateIn(BaseModel):
    topic: str = Field(min_length=3, max_length=500)
    content_type: ContentType = "blog"
    tone: Tone = "professional"
    audience: Audience = "general"
    length: Length = "medium"
    keywords: list[str] = Field(default_factory=list, max_length=10)
    use_rag: bool = False
    versions: int = Field(default=1, ge=1, le=3)
    extra_instructions: str = Field(default="", max_length=1000)


class RewriteIn(BaseModel):
    content_id: int
    instruction: str = Field(min_length=3, max_length=500)  # e.g. "make it shorter"


class ReviewIn(BaseModel):
    content: str = Field(min_length=20)
    content_type: ContentType = "blog"
    topic: str = "general"
    audience: Audience = "general"
    tone: Tone = "professional"


class ContentUpdate(BaseModel):
    generated_content: str | None = None
    status: Literal["draft", "approved"] | None = None


class FeedbackIn(BaseModel):
    content_id: int
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=1000)


class ContentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    topic: str
    content_type: str
    tone: str
    audience: str
    length: str
    keywords: list
    title: str
    generated_content: str
    hashtags: list
    seo_keywords: list
    meta_description: str
    plan: dict
    review: dict
    sources: list
    trace: list
    status: str
    parent_id: int | None
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_s: float
    created_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    chunks: int
    created_at: datetime
