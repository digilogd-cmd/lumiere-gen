# -*- coding: utf-8 -*-
"""생성형 두뇌 Task(대본·콘티·음악 프롬프트). brains/tasks.py 의 TASKS 에 등록된다.
- 두뇌는 '판단'만 한다(장면 나누기·샷 고르기·장면 묘사). Flow에 넣을 최종 프롬프트는 코드(gen/prompts.py)가 조립한다 —
  스타일 머리말·인물 외형·인원수·글자 금지를 빼먹는 일이 없게(지침서 §6, 스킬 ai-visual-prompt-craft 3원칙)."""
import difflib, json, re

SYSTEM = ("당신은 한국어 이야기·설명 영상을 기획하는 베테랑 연출가입니다. 내레이션 대본, 장면 나누기, 샷(그림) 설계를 합니다. "
          "사용자가 준 대본이 있으면 내용을 바꾸지 않습니다. 실존 인물·역사는 확실한 사실만 쓰고 지어내지 않습니다. "
          "답은 요청한 JSON 형식으로만 합니다.")

CHARS_PER_SEC = 7.0      # 한국어 내레이션 속도(글자/초, 띄어쓰기 포함) — 게이트 EP01 950자≈120초, EP03 1800자≈275초 사이


def norm(s):
    return re.sub(r"[^가-힣0-9a-zA-Z]", "", s or "")


# ---------------------------------------------------------------- gen_script
def p_script(inp):
    tgt = int(inp["length"])
    n_chars = int(tgt * CHARS_PER_SEC)
    sp = int(inp.get("speakers", 1))
    who = "화자 1명(내레이터)" if sp == 1 else f"화자 {sp}명(speaker 1~{sp}, 1번이 내레이터)"
    base = (f"아래 **사용자 대본**을 영상 내레이션 대본으로 정리해 주세요. 내용·문장은 그대로 두고(낱말을 바꾸거나 요약하지 말 것) "
            f"장면 나누기와 말하기 좋은 끊기만 하세요. 숫자만 한글로 풀어 씁니다(1895년 → 천팔백구십오 년).\n\n사용자 대본:\n{inp['script']}"
            if inp.get("script") else
            f"주제: {inp['topic']}\n이 주제로 이야기·설명 영상의 내레이션 대본을 새로 써 주세요.")
    return f"""{base}

조건
- 영상 길이 목표 {tgt}초 → 대본 전체 약 {n_chars}자(띄어쓰기 포함, ±15%). 사용자 대본이 있으면 길이는 그 대본 그대로.
- 장면(scene) {max(3, min(15, round(tgt / 15)))}개 안팎(3~15). 장면 = 같은 장소·같은 생각의 덩어리. 장면마다 heading(10자 안팎 한국어 제목).
- {who}. 각 장면의 lines 는 말하는 순서대로 [{{speaker, text}}]. 한 줄은 1~3문장.
- 듣기 좋게: 한 문장 40자 안팎, 어려운 말은 쉬운 말로. 숫자는 한글로 풀어 씁니다(TTS가 읽는 그대로 자막에도 나감).
- 무대 지시([웃음] 등)·괄호 설명·이모지 금지. 말로 읽을 글자만.
- 실존 인물·역사는 확실한 사실만. 모르면 쓰지 않습니다.
- title: 영상 제목(20자 안팎), hook: 첫 장면 첫 문장이 끌어당기는 힘이 있게.
- style: {inp.get('style') or ''}"""


S_SCRIPT = {"type": "object", "properties": {
    "title": {"type": "string"},
    "scenes": {"type": "array", "items": {"type": "object", "properties": {
        "n": {"type": "integer"}, "heading": {"type": "string"},
        "lines": {"type": "array", "items": {"type": "object", "properties": {"speaker": {"type": "integer"}, "text": {"type": "string"}},
                                             "required": ["speaker", "text"]}}},
        "required": ["n", "heading", "lines"]}}},
    "required": ["title", "scenes"]}


def script_text(out):
    return " ".join(l["text"] for s in out.get("scenes", []) for l in s.get("lines", []))


def v_script(out, inp):
    sc = out.get("scenes", [])
    if not 3 <= len(sc) <= 15:
        return f"장면은 3~15개여야 합니다(지금 {len(sc)}개)"
    sp = int(inp.get("speakers", 1))
    for s in sc:
        if not s.get("lines") or not "".join(l["text"] for l in s["lines"]).strip():
            return f"장면 {s.get('n')} 가 비었습니다"
        for l in s["lines"]:
            if not 1 <= int(l["speaker"]) <= sp:
                return f"장면 {s['n']}: 화자 번호 {l['speaker']} 는 1~{sp} 이어야 합니다"
            if re.search(r"[\[\]()（）]", l["text"]):
                return f"장면 {s['n']}: 괄호·지시어 금지 — {l['text'][:30]}"
    full = script_text(out)
    if inp.get("script"):
        r = difflib.SequenceMatcher(None, norm(inp["script"]), norm(full), autojunk=False).ratio()
        if r < 0.85:
            return f"사용자 대본과 내용이 너무 다릅니다(일치율 {r:.2f}). 문장을 바꾸지 말고 장면만 나눠 주세요"
    else:
        est = len(full) / CHARS_PER_SEC
        if not 0.75 * inp["length"] <= est <= 1.25 * inp["length"]:
            return f"길이가 목표와 너무 다릅니다(예상 {est:.0f}초, 목표 {inp['length']}초 — 약 {int(inp['length'] * CHARS_PER_SEC)}자로)"
    return None


# ---------------------------------------------------------------- gen_board
CAMERAS = ["Extreme wide shot", "Wide shot", "Medium wide shot", "Medium shot", "Medium close-up", "Close-up", "Extreme close-up",
           "Low angle", "High angle", "Bird's eye view", "Over-the-shoulder shot", "Dutch angle", "Insert shot"]


def p_board(inp):
    sc = "\n".join(f"[장면 {s['n']}] {s['heading']} (약 {s['sec']:.0f}초)\n" + "\n".join(f"  - {l['text']}" for l in s["lines"])
                   for s in inp["scenes"])
    return f"""아래 내레이션 대본으로 **샷(그림) 목록**을 설계해 주세요. 그림은 Google Flow(이미지 모델)로 만들고, 영상은 이 그림들을 이어 붙여 만듭니다.
화풍: {inp['style']} / 화면: {inp['aspect']} / 전체 {inp['length']:.0f}초

1) style_header: 모든 그림 프롬프트 맨 앞에 붙일 영어 화풍 고정 문장(1~2문장). 화풍·질감·색감을 실제 미술 용어로, 끝에 "NOT photorealistic, NOT 3D render" 포함.
2) characters: 반복해서 나오는 인물(0~4명). key 는 영어 대문자(예: AUGUSTE), name 은 한국어 이름,
   look 은 영어로 **겉모습 구조만**(나이·체형·얼굴형·머리 모양과 색·수염·옷과 색·소품) — 감정·피곤함 같은 말은 넣지 않음(얼굴이 변함).
   두 인물이 헷갈리지 않게 머리·수염·옷 색을 확실히 다르게.
   kind 는 영어 명사 — 사람이면 "person", 동물·생물이면 그 이름(예: "golden retriever dog", "black cat"). **주제에 동물이 주인공이면 사람으로 바꾸지 말 것.**
   사용자 노트(내 스타일)에 주인공이 정해져 있으면(예: 우리 집 골든 두 마리) 그 수·종류 그대로.
3) shots: 샷 {inp['n_shots_lo']}~{inp['n_shots_hi']}개(장면마다 1~3개, 장면 길이에 비례). 시간 순서대로.
   - id: "S" + 장면 두 자리 + 샷 문자 + "_" + 한국어 내용 2~3낱말(띄어쓰기 대신 _), 예: S01a_리옹_공장, S03b_형제_실험실
   - scene: 장면 번호. chars: 이 샷에 나오는 인물(동물 포함) key 목록. people: 화면 속 사람 수(동물은 세지 않음)(인물 key 외 군중이면 그 수, 군중은 0 대신 정확히 쓰기 어려우면 chars 수).
   - scene_desc: 영어 한두 문장 — 장소·시간·누가 어디서 무엇을. 인물 외모는 쓰지 말 것(코드가 look 을 붙임).
   - camera: 실제 촬영 용어({', '.join(CAMERAS)}) + 필요하면 렌즈·구도. 샷 크기를 다양하게(와이드·미디엄·클로즈업·인서트 섞기).
   - lighting: 조명 용어(Rembrandt lighting, soft window light, golden hour backlight, Low-key 등) + 색감.
   - emotion: 인물이 있으면 감정 이름 대신 눈·눈썹·입 움직임 순서(영어 한 문장). 없으면 빈 문자열.
   - no_text: 간판·신문·라벨·종이처럼 글자가 생길 소재가 있으면 true(그림 속 한글·영어 글자는 깨져 나옴).
   - veo: 움직이는 영상 클립으로 만들 핵심 샷이면 true — 정확히 {inp['veo_n']}개(영상 크레딧 한도 {inp['veo_max']}). 움직임이 의미 있는 샷(사람·기계·군중이 움직임)으로.
   - motion: veo 샷만, 영어 한 문장 — 카메라 움직임(slow dolly in, gentle pan left 등) + 무엇이 어떻게 움직이는지. 아니면 빈 문자열.
   - weight: 장면 안에서 이 샷이 차지할 시간 비율(1=보통, 2=두 배).
   - label: 한국어 한 줄 설명(콘티에 표시).
4) 인물 일관성: 같은 인물은 같은 key 로. 사진 재현이 아니라 그림체.
5) 세로 화면(9:16)이면 인물이 가운데 오는 구도로.

대본:
{sc}"""


S_BOARD = {"type": "object", "properties": {
    "style_header": {"type": "string"},
    "characters": {"type": "array", "items": {"type": "object", "properties": {
        "key": {"type": "string"}, "name": {"type": "string"}, "look": {"type": "string"}, "kind": {"type": "string"}},
        "required": ["key", "name", "look"]}},
    "shots": {"type": "array", "items": {"type": "object", "properties": {
        "id": {"type": "string"}, "scene": {"type": "integer"}, "chars": {"type": "array", "items": {"type": "string"}},
        "people": {"type": "integer"}, "scene_desc": {"type": "string"}, "camera": {"type": "string"}, "lighting": {"type": "string"},
        "emotion": {"type": "string"}, "no_text": {"type": "boolean"}, "veo": {"type": "boolean"}, "motion": {"type": "string"},
        "weight": {"type": "number"}, "label": {"type": "string"}},
        "required": ["id", "scene", "chars", "people", "scene_desc", "camera", "lighting", "emotion", "no_text", "veo", "motion", "weight", "label"]}}},
    "required": ["style_header", "characters", "shots"]}

SHOT_ID = re.compile(r"^S\d{2}[a-z]_[^\s/\\:*?\"<>|]+$")


def v_board(out, inp):
    scenes = {s["n"] for s in inp["scenes"]}
    keys = {c["key"] for c in out.get("characters", [])}
    shots = out.get("shots", [])
    if not inp["n_shots_lo"] - 2 <= len(shots) <= inp["n_shots_hi"] + 2:
        return f"샷은 {inp['n_shots_lo']}~{inp['n_shots_hi']}개여야 합니다(지금 {len(shots)}개)"
    if len(shots) + len(keys) > inp["img_max"]:
        return f"그림 수(샷 {len(shots)} + 캐릭터 시트 {len(keys)})가 한도 {inp['img_max']}장을 넘습니다"
    seen = set()
    for s in shots:
        if not SHOT_ID.match(s["id"]):
            return f"샷 id 형식 오류: {s['id']} (예: S03b_형제_실험실)"
        if s["id"] in seen:
            return f"샷 id 중복: {s['id']}"
        seen.add(s["id"])
        if s["scene"] not in scenes:
            return f"{s['id']}: 없는 장면 {s['scene']}"
        bad = [k for k in s["chars"] if k not in keys]
        if bad:
            return f"{s['id']}: characters 에 없는 인물 {bad}"
        if not s["scene_desc"].strip():
            return f"{s['id']}: scene_desc 가 비었습니다"
        if s["veo"] and not s["motion"].strip():
            return f"{s['id']}: veo 샷은 motion 이 필요합니다"
    miss = scenes - {s["scene"] for s in shots}
    if miss:
        return f"샷이 없는 장면: {sorted(miss)}"
    nv = sum(1 for s in shots if s["veo"])
    if nv > inp["veo_max"]:
        return f"영상(veo) 샷이 {nv}개 — 한도 {inp['veo_max']}개 이하로"
    if inp["veo_n"] and nv == 0:
        return f"영상(veo) 샷을 {inp['veo_n']}개 골라 주세요"
    if "photorealistic" not in out.get("style_header", "").lower():
        return "style_header 끝에 NOT photorealistic 을 넣어 주세요"
    return None


# ---------------------------------------------------------------- gen_music_prompt
def p_music(inp):
    return f"""이 영상의 배경음악을 Google Flow Music(음악 생성)으로 만들려 합니다. 영어 프롬프트를 써 주세요.
영상: {inp['title']} / 화풍: {inp['style']} / 길이 약 {inp['length']:.0f}초 / 내레이션이 계속 깔림(음악은 밑에서 받쳐 주는 역할).
- prompt: 영어 한 문단 — 장르·악기·템포(BPM)·분위기, "instrumental, no vocals, no lyrics", 내레이션을 가리지 않게 "soft, sparse, background score".
- mood: 한국어 한 줄(사람이 읽을 설명).
대본 요약:
{inp['summary']}"""


S_MUSIC = {"type": "object", "properties": {"prompt": {"type": "string"}, "mood": {"type": "string"}}, "required": ["prompt", "mood"]}


def v_music(out, inp):
    p = out.get("prompt", "").lower()
    if "no vocals" not in p and "instrumental" not in p:
        return "prompt 에 instrumental, no vocals 를 넣어 주세요"
    return None


GEN_TASKS = {
    "gen_script": dict(prompt=p_script, schema=S_SCRIPT, validate=v_script, system=SYSTEM),
    "gen_board": dict(prompt=p_board, schema=S_BOARD, validate=v_board, system=SYSTEM),
    "gen_music_prompt": dict(prompt=p_music, schema=S_MUSIC, validate=v_music, system=SYSTEM),
}
