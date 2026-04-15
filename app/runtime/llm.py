from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.core.config import OPENAI_MODEL, OPENAI_API_KEY, OPENAI_BASE_URL


def get_llm(temperature: float = 0):
    kwargs = {
        "model": OPENAI_MODEL,
        "temperature": temperature,
        "api_key": OPENAI_API_KEY,
    }

    if OPENAI_BASE_URL:
        kwargs["base_url"] = OPENAI_BASE_URL

    return ChatOpenAI(**kwargs)