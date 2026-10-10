from functools import lru_cache

from app.agents.content_agent import ContentAgent
from app.services.llm_service import LLMService
from app.services.rag_service import RagService


@lru_cache
def get_llm() -> LLMService:
    return LLMService()


@lru_cache
def get_rag() -> RagService:
    return RagService()


@lru_cache
def get_agent() -> ContentAgent:
    return ContentAgent(get_llm(), get_rag())
