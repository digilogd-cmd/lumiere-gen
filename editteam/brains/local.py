# -*- coding: utf-8 -*-
"""두뇌: 내 PC의 로컬 AI (Ollama / LM Studio 의 OpenAI 호환 주소). 인터넷·키 없이 돈다.
config.yaml 두뇌.local_주소 / local_모델."""
from ._openai_compat import chat_json


def call(cfg, prompt, schema, system=None):
    b = cfg["두뇌"]
    return chat_json(b.get("local_주소", "http://localhost:11434/v1"), b.get("local_모델", "qwen2.5:14b"), None,
                     prompt, schema, system)
