# -*- coding: utf-8 -*-
"""두뇌가 필요한 일(Task) 정의: 입력 -> 프롬프트, 출력 JSON 스키마, 결과 검증.
뤼미에르 젠: 대본·콘티·음악 프롬프트(gen/brain_tasks.py) + 제목·썸네일 문구·설명(titles_desc, 자막 문장을 번호와 함께 줌).
(촬영본 편집 Task — 내용 컷·후킹·모션·자막 검수·쇼츠·재구성·크롭 — 는 뤼미에르 에디트에만 있음, 2026-10-09 분리 정리)"""
import json

SYSTEM = ("당신은 한국어 유튜브 영상의 베테랑 기획·편집자입니다. 주어진 자막·대본만 근거로 판단하고, 없는 말을 지어내지 않습니다. "
          "답은 요청한 JSON 형식으로만 합니다.")


def mmss(t):
    t = max(0, float(t))
    return f"{int(t // 60)}:{int(t % 60):02d}"


def lines(sents):
    return "\n".join(f"[{s['id']}] {mmss(s['s'])} {s['text']}" for s in sents)


def _ids(inp):
    return {s["id"] for s in inp["sentences"]}


# 썸네일 문구 원칙(2026-10-21, 공용 지식 공용 지식 노트 의 1~3절) — 롱폼 썸네일·쇼츠 커버 공통
THUMB_RULES = """- 썸네일 문구: 2~4단어, 한 줄 10자 이내(작게 보여도 읽히게), 흰색 줄 + 포인트 색 줄.
- [반드시] 썸네일마다 **보는 사람이 얻는 것** 하나를 보여 주세요 — 받는 것(방법·목록·도구·프롬프트·코드)이나 보는 사람 쪽 결과
  (이렇게 하면 무엇이 된다·몇 분이 줄어든다·전 → 후). 안 되는 문구: 사실만 알리기, 말하는 사람 자기 이야기("제가 요즘 ~"), 배경 설명.
  "이 문구만 보고 '그래서 나한테 뭐?'"로 스스로 점검하세요. 받아쓰기에 실제로 있는 것만(지어내지 말 것).
- [반드시] 호기심 갭: 썸네일과 짝 제목은 **같은 약속을 다른 각도로** — 썸네일은 보여 주기(결과·숫자·대비·한 단어),
  제목은 설명하기(검색어 + 이야기). 썸네일 글자를 제목에 그대로 되풀이하지 마세요.
- 썸네일 → 제목 → 영상 첫 화면이 하나의 약속으로 이어지게."""


def p_titles(inp):
    hook = inp.get("hook", "")
    return f"""유튜브 롱폼 영상의 제목·썸네일 문구·설명을 만들어 주세요. 채널: {inp['channel']}.
- titles: 제목 3종(A/B 테스트용, 각 40자 이내, 서로 다른 각도: 결과형/방법형/호기심형). 날짜 문구 금지.
- thumbs: 썸네일 큰 글씨 3종. line1 흰색(7자 안팎), line2 포인트 색 하나(핵심 6자 이내), line3 흰색(필요할 때만, 없으면 빈 문자열). thumbs[n] 은 titles[n] 과 짝.
  포인트 색은 line2 한 곳뿐. 느낌표는 써도 되지만 남발하지 말 것(한 문구에 하나).
- summary: 설명란 첫 3~4문장 요약(지어내지 말 것).
- hashtags: 5~8개(#포함).
{THUMB_RULES}
  영상 첫 화면(후킹 인트로)은 이 말로 시작합니다: {hook} — 썸네일·제목이 약속한 것을 이 첫 화면이 바로 갚는지 확인하세요.
목차는 실행기가 실제 시각으로 따로 만듭니다.

이전 쇼츠 제목: {json.dumps(inp.get('prev_titles', []), ensure_ascii=False)}

받아쓰기(최종본):
{lines(inp['sentences'])}"""


S_TITLES = {"type": "object", "properties": {
    "titles": {"type": "array", "items": {"type": "string"}},
    "thumbs": {"type": "array", "items": {"type": "object", "properties": {"line1": {"type": "string"}, "line2": {"type": "string"},
                                                                          "line3": {"type": "string"}}, "required": ["line1", "line2", "line3"]}},
    "summary": {"type": "string"}, "hashtags": {"type": "array", "items": {"type": "string"}},
    "chapters": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "title": {"type": "string"}},
                                            "required": ["id", "title"]}}},
    "required": ["titles", "thumbs", "summary", "hashtags", "chapters"]}


def p_titles_full(inp):
    return p_titles(inp) + "\n\nchapters: 목차 5~10개. 각 목차가 시작하는 문장 번호(id)와 짧은 제목(15자). 첫 목차는 맨 첫 문장."


def v_titles(out, inp):
    if len(out.get("titles", [])) < 3 or len(out.get("thumbs", [])) < 3:
        return "제목·썸네일 문구는 각 3종"
    ids = _ids(inp)
    for c in out.get("chapters", []):
        if c["id"] not in ids:
            return f"목차의 없는 문장 번호 {c['id']}"
    return None


TASKS = {
    "titles_desc": dict(prompt=p_titles_full, schema=S_TITLES, validate=v_titles),
}

# 생성형: 대본·콘티·음악 프롬프트 — 정의는 editteam/gen/brain_tasks.py
from ..gen.brain_tasks import GEN_TASKS
TASKS.update(GEN_TASKS)
