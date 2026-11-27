# -*- coding: utf-8 -*-
"""두뇌: Google Gemini API (사용자 본인 키, .env 의 GEMINI_API_KEY). OpenAI 호환 주소를 쓴다."""
import os
from ._openai_compat import chat_json, load_env


def call(cfg, prompt, schema, system=None):
    load_env()
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError(".env 에 GEMINI_API_KEY 가 없습니다.")
    return chat_json("https://generativelanguage.googleapis.com/v1beta/openai", cfg["두뇌"].get("gemini_모델", "gemini-2.5-flash"),
                     key, prompt, schema, system)
