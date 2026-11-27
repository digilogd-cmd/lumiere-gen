# -*- coding: utf-8 -*-
"""만들 기능 목록(예전 이름: 새 기능 요청함): 대화창(일반 모드)이 지금 명령으로 못 하는 요청을 쌓아 둔다.
뤼미에르는 사용자가 자기 Claude로 키워 가는 시스템이라(2026-10-07), 이 목록은 '내 Claude가 만들 일'이다 — 개발자 모드를 켜면 대화창 Claude가 보고 만든다.
원하면 항목을 뤼미에르 팀(TEAM_EMAIL)에 메일로 보낼 수 있다(사용자가 누를 때만, 자동 전송 없음). 파일: 기능요청.jsonl (한 줄 = 한 요청)."""
import json, os, time, uuid
from .core import ROOT

PATH = os.path.join(ROOT, "기능요청.jsonl")
STATUS = {"대기": "대기", "진행": "진행", "완료": "완료", "보류": "보류", "팀에 보냄": "팀에 보냄"}
TEAM_EMAIL = "artgourmet.official@gmail.com"     # 뤼미에르 팀(아트고메) 의견 받는 메일


def items():
    if not os.path.exists(PATH):
        return []
    out = []
    for ln in open(PATH, encoding="utf-8"):
        try:
            out.append(json.loads(ln))
        except ValueError:
            pass
    return out[::-1]


def add(project, text):
    it = {"id": uuid.uuid4().hex[:8], "t": time.strftime("%Y-%m-%dT%H:%M:%S"), "project": project, "text": text.strip(), "status": "대기"}
    with open(PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(it, ensure_ascii=False) + chr(10))
    return it


def set_status(rid, status):
    if status not in STATUS:
        return False
    rows = items()[::-1]
    hit = False
    for r in rows:
        if r["id"] == rid:
            r["status"] = status; r["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S"); hit = True
    if hit:
        tmp = PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.writelines(json.dumps(r, ensure_ascii=False) + chr(10) for r in rows)
        os.replace(tmp, PATH)
    return hit
