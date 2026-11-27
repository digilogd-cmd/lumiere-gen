# -*- coding: utf-8 -*-
"""두뇌: OpenAI API (사용자 본인 키, .env 의 OPENAI_API_KEY). config.yaml 두뇌.openai_모델."""
import os
from ._openai_compat import chat_json, load_env


def call(cfg, prompt, schema, system=None):
    load_env()
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(".env 에 OPENAI_API_KEY 가 없습니다.")
    return chat_json("https://api.openai.com/v1", cfg["두뇌"].get("openai_모델", "gpt-4.1"), key, prompt, schema, system)
