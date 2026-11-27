# -*- coding: utf-8 -*-
"""첫 만남(온보딩): 제작 팀장이 사용자의 채널·화풍·분위기·목소리·피할 소재를 묻고, 답을 '내 스타일' 층에 남긴다.
- 설정 창 항목과 겹치는 답(화풍·목소리·길이·화면·색·글꼴)은 설정.json 에(다음 제작이 바로 그 값으로 돈다).
- 말로 한 답(좋아하는 스타일, 하지 말 것 등)은 내_스타일.md(내 스타일 노트)에 — 두뇌(AI)가 판단할 때 같이 읽는다(brains.run).
(2026-10-07: 처음엔 팀장이 인상적으로 인사하고, 스타일·원하는 방향·궁금한 것을 물어 맞춤형 뤼미에르로 시작)"""
import json, os, re, time

from .core import ROOT, USER_SETTINGS, load_config

NOTE = os.path.join(ROOT, "내_스타일.md")

# (id, 질문, 종류, 설정 경로 또는 None, 선택지[(값, 이름)] 또는 None, 도움말)
#   종류: text(한 줄) · long(여러 줄) · choice(하나) · multi(여러 개) · visual(그림 카드, 선택지는 설정 창 것을 씀) · list(쉼표 목록) · file(그림 파일)
QUESTIONS = [
    ("호칭", "먼저, 제가 어떻게 불러 드리면 될까요?", "text", "사용자.호칭", None, "예: 대표님, 민지 님, 감독님"),
    ("채널", "채널 이름을 알려 주세요.", "text", "채널.이름", None, "로고가 없을 때 썸네일 구석에 들어가요. 없으면 비워 두셔도 돼요."),
    ("만들영상", "어떤 영상을 만들고 싶으세요? 주제와 보실 분들을 알려 주세요.", "long", None, None,
     "예: 역사 속 발명 이야기를 짧게 — 초등 고학년과 부모님. 대본과 콘티를 짤 때 이 방향으로 맞춰요."),
    ("화풍", "그림은 어떤 화풍이 좋으세요?", "choice", "생성.화풍",
     [("따뜻한 수채화풍 일러스트", "따뜻한 수채화"), ("극장판 애니메이션풍, 손으로 그린 배경", "극장판 애니메이션"),
      ("연필과 잉크 스케치풍 일러스트", "연필·잉크 스케치"), ("파스텔 톤 동화책 일러스트", "동화책 파스텔"),
      ("시네마틱 디지털 페인팅, 영화 같은 조명", "영화 같은 디지털 페인팅")], "다른 화풍은 설정 창에서 직접 써 넣을 수 있어요. 만들 때마다 바꿀 수도 있어요."),
    ("분위기", "영상 분위기는 어떤 쪽이 좋으세요? (여러 개 골라도 돼요)", "multi", None,
     [("따뜻한", "따뜻하고 다정한"), ("차분한", "차분하고 담담한"), ("긴장감", "긴장감 있는"), ("유쾌한", "밝고 유쾌한"), ("신비로운", "신비롭고 몽환적인")],
     "대본 말투·조명·배경음악에 반영돼요."),
    ("목소리", "내레이션 목소리는 어떤 느낌이 좋으세요?", "choice", "생성.화자_목소리",
     [("Charon, Kore, Puck", "차분하고 낮은 내레이터(Charon)"), ("Kore, Charon, Puck", "또렷하고 단정한 내레이터(Kore)"),
      ("Puck, Kore, Charon", "경쾌하고 밝은 목소리(Puck)")], "Google AI Studio 목소리예요. 화자가 여럿이면 순서대로 다른 목소리를 써요."),
    ("길이", "영상은 보통 몇 분짜리를 만들까요?", "choice", "생성.목표_초",
     [(60, "1분 안팎"), (90, "1분 30초 안팎"), (120, "2분 안팎"), (180, "3분 안팎")], "새로 만들 때마다 바꿀 수 있어요."),
    ("화면", "주로 어디에 올리세요?", "choice", "생성.세로",
     [(False, "유튜브 — 가로 16:9"), (True, "쇼츠·릴스 — 세로 9:16")], "새로 만들기 창에 처음 골라져 있는 화면이에요."),
    ("팔레트", "자막과 제목 색 분위기를 골라 주세요.", "visual", "디자인.팔레트", None, "영상 톤에 맞는 것으로. 나중에 바꿀 수 있어요."),
    ("글꼴", "자막 글꼴은 어떤 느낌이 좋으세요?", "visual", "자막.글꼴", None, ""),
    ("썸네일색", "썸네일 강조 색을 골라 주세요.", "visual", "썸네일.포인트색", None, "썸네일 두 번째 줄(강조 한 줄)에 들어가요."),
    ("좋아하는", "참고하고 싶은 채널·작품·그림 스타일이 있나요?", "long", None, None, "예: 지브리 같은 따뜻한 색감, ○○ 채널처럼 짧고 담백한 내레이션"),
    ("피할것", "영상에 넣지 말았으면 하는 것이 있나요?", "long", None, None,
     "예: 실존 인물 얼굴을 사진처럼 그리지 말 것, 폭력적인 장면, 너무 어두운 화면. 대본·그림 프롬프트를 만들 때 지켜요."),
    ("로고", "채널 로고 그림(PNG)이 있으면 골라 주세요.", "file", "채널.로고", None, "검정 바탕에 흰 심볼이면 가장 잘 보여요. 없으면 건너뛰세요."),
]


def leader(cfg=None):
    cfg = cfg or load_config()
    return ((cfg.get("팀장") or {}).get("이름") or "오귀스트").strip()


def greeting(cfg=None):
    n = leader(cfg)
    return (f"안녕하세요, 뤼미에르 젠 제작 팀장 {n}입니다.\n"
            "뤼미에르 젠은 최초의 영화를 만든 뤼미에르 형제를 생각하며, 이야기만으로 영상을 만들어 내는 완전히 새로운 제작 시스템을 지향합니다.\n"
            "사용할수록 더욱 진화하는 제작 시스템, 뤼미에르 젠에 오신 것을 환영합니다.\n\n"
            "당신의 이야기를 영상으로 밝혀 드리기 전에, 몇 가지만 여쭤볼게요. 답해 주시는 대로 저와 제작팀이 당신의 스타일에 맞춰 움직입니다.")


def done():
    return os.path.exists(NOTE)


def note():
    return open(NOTE, encoding="utf-8").read() if os.path.exists(NOTE) else ""


def questions():
    """설정 창의 그림 선택지(팔레트·글꼴·썸네일 색)를 붙여서 돌려준다."""
    from . import settings as ST
    vis = {f["path"]: f for f in ST.read()["fields"] if f["kind"] == "visual"}
    out = []
    for qid, q, kind, path, opts, help_ in QUESTIONS:
        it = {"id": qid, "q": q, "kind": kind, "path": path, "help": help_,
              "options": [{"v": a, "t": b} for a, b in opts] if opts else None}
        if kind == "visual" and path in vis:
            it["options"] = vis[path]["options"]; it["value"] = vis[path]["value"]
        out.append(it)
    return out


def _set(d, path, v):
    ks = path.split(".")
    for k in ks[:-1]:
        d = d.setdefault(k, {})
    d[ks[-1]] = v


def save(answers):
    """answers: {질문id: 값}. 설정.json 에 반영할 것은 반영하고, 전체 문답을 내_스타일.md 로."""
    from . import settings as ST
    vals = {}
    for qid, q, kind, path, opts, help_ in QUESTIONS:
        a = answers.get(qid)
        if a in (None, "", []) or not path:
            continue
        vals[path] = ", ".join(a) if (kind == "list" and isinstance(a, list)) else a
    fields = {f[0] for f in ST.FIELDS}
    ok, errs = ST.save({k: v for k, v in vals.items() if k in fields})
    # 설정 창 밖의 값(호칭)은 설정.json 에 직접
    cur = json.load(open(USER_SETTINGS, encoding="utf-8")) if os.path.exists(USER_SETTINGS) else {}
    if answers.get("호칭"):
        _set(cur, "사용자.호칭", str(answers["호칭"]).strip())
    tmp = USER_SETTINGS + ".tmp"
    json.dump(cur, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, USER_SETTINGS)
    # 내 스타일 노트
    L = ["# 내 스타일 노트", "", f"> 첫 만남에서 제작 팀장 {leader()}에게 들려준 이야기({time.strftime('%Y-%m-%d')}). 제작팀 AI(대본·콘티·음악·제목)가 판단할 때 함께 읽어요.",
         "> 이 파일은 직접 고쳐도 되고, 대화창에서 \"내 스타일 노트에 ○○ 추가해 줘\"라고 해도 돼요.", ""]
    for qid, q, kind, path, opts, help_ in QUESTIONS:
        a = answers.get(qid)
        if a in (None, "", []):
            continue
        if kind == "visual":           # 그림 고르기 답은 코드값(B, pretend) 대신 이름(B 쿨 테크 블루, 프리텐다드)으로
            opts = [(o[0], o[1]) for f in ST.FIELDS if f[0] == path for o in f[3]]
        if opts:
            name = dict((str(x), y) for x, y in opts)
            a = ", ".join(name.get(str(x), str(x)) for x in a) if isinstance(a, list) else name.get(str(a), str(a))
        elif isinstance(a, list):
            a = ", ".join(map(str, a))
        if kind == "file":
            a = os.path.basename(str(a))
        L += [f"## {q}", str(a).strip(), ""]
    open(NOTE, "w", encoding="utf-8").write("\n".join(L))
    return {"ok": ok, "errors": errs, "saved": len(vals)}


def add_note(text):
    """대화 중에 알게 된 스타일을 노트에 덧붙인다."""
    if not os.path.exists(NOTE):
        open(NOTE, "w", encoding="utf-8").write("# 내 스타일 노트\n\n")
    with open(NOTE, "a", encoding="utf-8") as f:
        f.write(f"\n## 추가 ({time.strftime('%Y-%m-%d')})\n{text.strip()}\n")


# 두뇌가 스타일 노트를 같이 읽는 판단들(만드는 방향에 영향을 주는 것만)
STYLE_TASKS = ("titles_desc", "gen_script", "gen_board", "gen_music_prompt")

def for_brain(max_chars=2500):
    t = note().strip()
    if not t:
        return ""
    t = "\n".join(l for l in t.split("\n") if not l.startswith(">"))
    return "\n\n[이 채널의 제작 스타일 노트 — 사용자가 직접 알려 준 취향(화풍·분위기·목소리·피할 것). 판단할 때 우선해서 따를 것]\n" + t[:max_chars]
