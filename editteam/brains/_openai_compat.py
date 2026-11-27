# -*- coding: utf-8 -*-
"""OpenAI 호환 /chat/completions 로 JSON 받기(OpenAI·Gemini·Ollama·LM Studio 공통)."""
import json, os, re, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_env():
    """LUMIERE_GEN/.env 의 KEY=VALUE 를 환경변수로(이미 있으면 그대로)."""
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8"):
            m = re.match(r"\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$", ln)
            if m and m.group(1) not in os.environ:
                os.environ[m.group(1)] = m.group(2).strip().strip('"')


def chat_json(base, model, key, prompt, schema, system=None, timeout=1800):
    msgs = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt + "\n\n반드시 다음 JSON 스키마에 맞는 JSON 하나만 출력하세요:\n" + json.dumps(schema, ensure_ascii=False)}]
    body = {"model": model, "messages": msgs, "temperature": 0.2,
            "response_format": {"type": "json_schema", "json_schema": {"name": "out", "schema": schema}}}
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {key}"} if key else {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode("utf-8"))
    txt = d["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", txt, re.S)
    out = json.loads(m.group(0) if m else txt)
    return out, {"cost_usd": None, "model": model}
