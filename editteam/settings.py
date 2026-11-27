# -*- coding: utf-8 -*-
"""대시보드 [설정] 창에서 고칠 수 있는 항목 목록 + 읽기/저장(뤼미에르 젠).
값은 LUMIERE_GEN/설정.json 에 저장되고 load_config()가 config.yaml 위에 덮어쓴다.
키·비밀번호는 여기서 받지 않는다(작업지시서: 키는 사용자 PC의 .env 에만) — 키가 있는지만 보여 준다."""
import json, os, shutil
from .core import ROOT, USER_SETTINGS, load_config
from . import design as _D

# (경로, 제목, 종류, 선택지[(값, 이름)] 또는 None, 도움말, 묶음)
FIELDS = [
    ("두뇌.기본", "두뇌(판단하는 AI)", "select",
     [("claude", "Claude — 내 Claude Code 로그인(추가 비용 없음)"), ("codex", "Codex — 내 ChatGPT 로그인(코덱스 CLI, 추가 비용 없음·시험 중)"),
      ("openai", "OpenAI — 내 API 키(.env, 쓴 만큼 요금)"),
      ("gemini", "Gemini — 내 API 키(.env)"), ("local", "내 PC 모델 — Ollama·LM Studio(무료, 느림)")],
     "대본·콘티(샷 설계)·음악 프롬프트·제목과 설명을 판단하는 AI", "두뇌"),
    ("두뇌.claude_모델", "Claude 모델", "select", [("sonnet", "Sonnet — 기본(빠르고 정확)"), ("opus", "Opus — 가장 꼼꼼(느림)"), ("haiku", "Haiku — 가장 빠름")],
     "", "두뇌"),
    ("두뇌.codex_모델", "Codex 모델", "text", None, "비우면 내 코덱스 설정의 모델(예: gpt-6.1-sol). 안 되는 모델이면 gpt-5.5로 자동 대체", "두뇌"),
    ("두뇌.openai_모델", "OpenAI 모델", "text", None, "예: gpt-4.1", "두뇌"),
    ("두뇌.gemini_모델", "Gemini 모델", "text", None, "예: gemini-2.5-flash", "두뇌"),
    ("두뇌.local_주소", "내 PC 모델 주소", "text", None, "Ollama 기본: http://localhost:11434/v1", "두뇌"),
    ("두뇌.local_모델", "내 PC 모델 이름", "text", None, "예: qwen2.5:14b", "두뇌"),
    ("디자인.팔레트", "컬러 팔레트 — 자막·모션그래픽", "visual",
     [(k, f"{k} {v['name']}", v["desc"], f"/design/pal_{k}.jpg") for k, v in _D.PALETTES.items()],
     "영상 톤에 맞춰 고르세요. 자막 상자·모션 카드·인트로·REPORT가 모두 같은 색 묶음을 씁니다.", "디자인"),
    ("자막.글꼴", "자막 글꼴", "visual",
     [(k, v["name"], v["desc"], f"/design/font_{k}.jpg") for k, v in _D.FONTS.items()],
     "글꼴마다 글자 높이를 똑같이 맞춰 두었어요(무료·상업 이용 가능 글꼴).", "디자인"),
    ("썸네일.포인트색", "썸네일 포인트 색", "visual",
     [(k, v[0], v[2], f"/design/thumb_{k}.jpg") for k, v in _D.THUMB_COLORS.items()],
     "썸네일 두 번째 줄(강조 한 줄)에 들어가는 색", "디자인"),
    ("생성.화풍", "기본 화풍", "text", None, "예: 따뜻한 수채화풍 일러스트, 극장판 애니메이션, 연필 스케치. [대본으로 만들기] 창에서 바꿀 수 있어요", "생성"),
    ("생성.목표_초", "기본 영상 길이", "select", [(60, "1분"), (90, "1분 30초(기본)"), (120, "2분"), (180, "3분")], "[＋ 새로 만들기] 창에 처음 들어가는 길이", "생성"),
    ("생성.세로", "기본 화면", "select", [(False, "가로 16:9(유튜브)"), (True, "세로 9:16(쇼츠·릴스)")], "[＋ 새로 만들기] 창에 처음 골라져 있는 화면", "생성"),
    ("생성.화자_목소리", "화자 목소리(AI Studio)", "list", None, "쉼표로 화자 1, 2, 3… 순서. 예: Charon, Kore, Puck", "생성"),
    ("생성.영상_클립_한도", "움직이는 장면(Veo) 한도", "select", [(0, "만들지 않음 — 그림 확대로만"), (2, "2클립"), (4, "4클립(기본)"), (6, "6클립")],
     "Flow 영상은 크레딧을 씁니다(Veo 3.1 Lite 1클립 10크레딧, 2026-10-08 기준)", "생성"),
    ("생성.음악_한도", "음악 곡 수 한도", "select", [(1, "1곡"), (3, "3곡(기본)")], "Flow Music 으로 만들 곡 수", "생성"),
    ("생성.음악_크기", "배경음악 크기", "select", [(0.3, "작게"), (0.42, "보통(기본)"), (0.55, "크게")], "말하는 동안은 자동으로 더 작아져요", "생성"),
    ("생성.다운로드_폴더", "크롬 다운로드 폴더", "text", None, "비우면 크롬 설정에서 자동으로 찾아요", "생성"),
    ("알림.켜기", "끝나면 윈도우 알림", "select", [(True, "켜기"), (False, "끄기")], "편집이 끝나거나 확인할 차례가 되면 알림", "알림"),
    ("개발자.모드", "키우기 모드(개발자 모드)", "select", [(False, "끄기 — 정해진 명령으로만 편집"), (True, "켜기 — 내 Claude가 뤼미에르 코드를 고쳐 새 기능을 만듦(Opus)")],
     "켜면 대화창에서 '이런 기능 만들어 줘'가 됩니다. 고치기 전 상태가 자동 저장되고, 아래 '엔진 관리'에서 되돌리기·초기화·자가 검사를 할 수 있어요.", "키우기"),
    ("팀장.이름", "편집 팀장 이름", "text", None, "대화창에서 인사하고 이야기하는 AI의 이름(기본: 루이 — 뤼미에르 형제의 루이 뤼미에르)", "채널"),
    ("채널.이름", "채널 이름", "text", None, "", "채널"),
    ("채널.로고", "채널 로고(PNG)", "text", None, "썸네일 좌하단에 들어가는 실제 로고 파일", "채널"),
]


def get_path(cfg, path):
    cur = cfg
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def brain_status():
    """두뇌마다 지금 쓸 수 있는지(키 값은 절대 내보내지 않고 있다/없다만)."""
    env = {}
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8"):
            if "=" in ln and not ln.lstrip().startswith("#"):
                k, v = ln.split("=", 1)
                env[k.strip()] = bool(v.strip().strip('"'))
    has = lambda k: bool(os.environ.get(k)) or env.get(k, False)
    return {"claude": bool(shutil.which("claude") or shutil.which("claude.cmd")),
            "codex": bool(__import__("editteam.brains.codex", fromlist=["codex_cmd"]).codex_cmd()),
            "openai": has("OPENAI_API_KEY"), "gemini": has("GEMINI_API_KEY"), "local": True}


def read():
    cfg = load_config()
    out = []
    for path, label, kind, opts, help_, group in FIELDS:
        v = get_path(cfg, path)
        if path == "썸네일.구성" and v is None:
            v = "mix"
        if path == "편집.기본_방식" and v is None:
            v = "checkpoint"
        DEF = {"종편.목표_분": 0, "편집.내용컷_강도": "normal", "PIP.켜기": True, "PIP.보일때": "always", "PIP.위치": "bl", "쇼츠.배속": 1.5,
               "쇼츠.기획_개수": 8, "쇼츠.썸네일": "classic", "알림.켜기": True, "채널.주제": "", "개발자.모드": False,
               "디자인.팔레트": "A", "자막.글꼴": "barun", "썸네일.포인트색": "red"}
        if v is None and path in DEF:
            v = DEF[path]
        if kind == "list":
            v = ", ".join(v or []) if isinstance(v, list) else (v or "")
        out.append({"path": path, "label": label, "kind": kind, "options": [{"v": o[0], "t": o[1], "d": o[2] if len(o) > 2 else "", "img": o[3] if len(o) > 3 else ""} for o in opts] if opts else None,
                    "help": help_, "group": group, "value": v})
    return {"fields": out, "brains": brain_status()}


def save(values):
    """values: {경로: 값}. 목록에 있는 항목만, 종류에 맞게 검사해서 설정.json 에 저장."""
    spec = {f[0]: f for f in FIELDS}
    cur = json.load(open(USER_SETTINGS, encoding="utf-8")) if os.path.exists(USER_SETTINGS) else {}
    errs = []
    for path, v in values.items():
        if path not in spec:
            continue
        _, label, kind, opts, *_ = spec[path]
        if kind in ("select", "visual"):
            allowed = {str(o[0]): o[0] for o in opts}
            if str(v) not in allowed:
                errs.append(f"{label}: 고를 수 없는 값"); continue
            v = allowed[str(v)]
        elif kind == "number":
            try:
                v = float(v); v = int(v) if v == int(v) else v
            except (TypeError, ValueError):
                errs.append(f"{label}: 숫자를 넣어 주세요"); continue
            if v < 0 or v > 600:
                errs.append(f"{label}: 0~600 사이로"); continue
        elif kind == "list":
            v = [x.strip() for x in str(v).replace(chr(10), ",").split(",") if x.strip()][:60]
        else:
            v = str(v).strip()
        d = cur
        ks = path.split(".")
        for k in ks[:-1]:
            d = d.setdefault(k, {})
        d[ks[-1]] = v
    if errs:
        return False, errs
    tmp = USER_SETTINGS + ".tmp"
    json.dump(cur, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, USER_SETTINGS)
    return True, []


# ---------------------------------------------------------------- 프리셋(장르·채널별 설정 묶음)
PRESETS = os.path.join(ROOT, "프리셋")
SKIP_IN_PRESET = ("채널.이름", "채널.로고", "채널.자료페이지")


def _safe(name):
    import re
    return re.sub(r'[\/:*?"<>|]', "", (name or "").strip())[:40]


def presets():
    os.makedirs(PRESETS, exist_ok=True)
    out = [{"name": "기본(출고 설정)", "builtin": True}]
    for f in sorted(os.listdir(PRESETS)):
        if f.endswith(".json"):
            out.append({"name": f[:-5], "builtin": False})
    return out


def preset_save(name):
    n = _safe(name)
    if not n or n.startswith("기본("):
        return False, "프리셋 이름을 정해 주세요"
    cfg = load_config()
    vals = {f[0]: get_path(cfg, f[0]) for f in FIELDS if f[0] not in SKIP_IN_PRESET}
    os.makedirs(PRESETS, exist_ok=True)
    json.dump(vals, open(os.path.join(PRESETS, n + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return True, n


def preset_load(name):
    """프리셋을 지금 설정으로. 기본 프리셋 = 채널 정보만 남기고 나머지는 config.yaml 기본값."""
    import copy
    cur = json.load(open(USER_SETTINGS, encoding="utf-8")) if os.path.exists(USER_SETTINGS) else {}
    # 설정 창 항목(FIELDS)만 비우고(채널 정보는 남김) 나머지 내 스타일 값(블러 패턴·입력폴더·보고서 폴더 등)은 그대로
    new = copy.deepcopy(cur)
    for path, *_ in FIELDS:
        if path in SKIP_IN_PRESET:
            continue
        d, ks = new, path.split(".")
        for k in ks[:-1]:
            d = d.get(k) if isinstance(d, dict) else None
            if d is None:
                break
        if isinstance(d, dict):
            d.pop(ks[-1], None)
    if not name.startswith("기본("):
        f = os.path.join(PRESETS, _safe(name) + ".json")
        if not os.path.exists(f):
            return False, "프리셋을 찾을 수 없습니다"
        for path, v in json.load(open(f, encoding="utf-8")).items():
            if v is None:
                continue
            d = new
            ks = path.split(".")
            for k in ks[:-1]:
                d = d.setdefault(k, {})
            d[ks[-1]] = v
    tmp = USER_SETTINGS + ".tmp"
    json.dump(new, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, USER_SETTINGS)
    return True, name


def preset_delete(name):
    f = os.path.join(PRESETS, _safe(name) + ".json")
    if os.path.exists(f):
        os.remove(f)
        return True, name
    return False, "없는 프리셋"
