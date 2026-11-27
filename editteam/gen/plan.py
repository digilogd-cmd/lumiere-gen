# -*- coding: utf-8 -*-
"""콘티(board.json)·대본(script.json) -> 브라우저 작업 목록. 콘티가 끝나면 그림·영상·목소리·음악 작업을 한꺼번에 적어 둔다
(Claude가 크롬 창 한 번에 몰아서 하게). 각 [브라우저] 단계도 자기 몫을 다시 맞춘다(같은 내용이면 상태 유지)."""
import hashlib, os

from ..core import jload
from . import jobs as J
from .common import brief, gcfg, sdir
from .prompts import sheet_prompt, shot_prompt, video_prompt, voice_text


def h(s):
    return hashlib.sha1(str(s).encode("utf-8")).hexdigest()[:10]


def board(P):
    return jload(os.path.join(sdir(P, "gen_board"), "board.json"))


def script(P):
    return jload(os.path.join(sdir(P, "gen_script"), "script.json"))


def image_specs(P):
    b, bd = brief(P), board(P)
    out_dir = os.path.join(sdir(P, "gen_images"), "images")
    specs, sheets = [], {}
    for i, c in enumerate(bd.get("characters", [])):
        jid = f"sheet_{c['key']}"
        pr = sheet_prompt(bd, c, b["aspect"])
        sheets[c["key"]] = {"id": jid, "name": c["name"], "file": os.path.join(out_dir, f"_시트_{c['key']}.png"), "sig": h(pr)}
        specs.append({"id": jid, "종류": "image", "도구": "flow", "장면": None, "샷": f"_시트_{c['key']}", "순서": i + 1,
                      "설명": f"캐릭터 시트 — {c['name']}({c['key']}). 이후 샷에서 레퍼런스로 붙인다(새 업로드 아님: Flow 라이브러리에 남은 이 생성 그림)",
                      "프롬프트": pr, "레퍼런스": [], "레퍼런스_작업": [], "먼저": [], "화면비": b["aspect"], "부가": {"시트": True},
                      "받을위치": sheets[c["key"]]["file"]})
    for k, s in enumerate(bd["shots"]):
        refs = [sheets[x] for x in s.get("chars", []) if x in sheets]
        specs.append({"id": f"img_{s['id']}", "종류": "image", "도구": "flow", "장면": s["scene"], "샷": s["id"], "순서": 10 + k,
                      "설명": s.get("label", ""), "프롬프트": s["prompt"],
                      "레퍼런스": [{"이름": f"{r['name']} 캐릭터 시트 (작업 {r['id']}, 순서대로 image {n + 1})", "작업": r["id"], "파일": r["file"]}
                                for n, r in enumerate(refs)],
                      "레퍼런스_작업": [[r["id"], r["sig"]] for r in refs], "먼저": [r["id"] for r in refs], "화면비": b["aspect"],
                      "부가": {}, "받을위치": os.path.join(out_dir, f"{s['id']}.png")})
    return specs


def video_specs(P):
    bd = board(P)
    lim = int(gcfg(P.cfg)["영상_클립_한도"])
    out_dir = os.path.join(sdir(P, "gen_video"), "video")
    img_dir = os.path.join(sdir(P, "gen_images"), "images")
    specs = []
    for k, s in enumerate([s for s in bd["shots"] if s.get("veo")][:lim]):
        specs.append({"id": f"vid_{s['id']}", "종류": "video", "도구": "flow", "장면": s["scene"], "샷": s["id"], "순서": 100 + k,
                      "설명": f"그림 -> 영상(Veo). 시작 프레임 = 샷 {s['id']} 그림. " + s.get("label", ""),
                      "프롬프트": video_prompt(bd, s),
                      "레퍼런스": [{"이름": f"샷 {s['id']} 그림(시작 프레임 — Flow 라이브러리의 그 생성 그림)", "작업": f"img_{s['id']}",
                                  "파일": os.path.join(img_dir, f"{s['id']}.png")}],
                      "레퍼런스_작업": [[f"img_{s['id']}", h(s["prompt"])]], "먼저": [f"img_{s['id']}"], "화면비": brief(P)["aspect"],
                      "부가": {"크레딧": "영상 1클립(한도 안에서)"}, "받을위치": os.path.join(out_dir, f"{s['id']}.mp4")})
    return specs


def voice_sessions(scenes):
    """AI Studio 는 한 번에 화자 2명까지 -> 화자가 3명 넘게 섞이면 순서대로 나눈다(게이트 EP03 세션 A·B)."""
    sess, cur, who = [], [], set()
    for s in scenes:
        for l in s["lines"]:
            if l["speaker"] not in who and len(who) == 2:
                sess.append(cur); cur, who = [], set()
            who.add(l["speaker"])
            cur.append({"n": s["n"], "heading": s["heading"], "lines": [l]})
    if cur:
        sess.append(cur)
    return sess


def voice_specs(P):
    b, sc = brief(P), script(P)
    voices = gcfg(P.cfg)["화자_목소리"]
    out_dir = os.path.join(sdir(P, "gen_voice"), "voice")
    specs = []
    for i, ss in enumerate(voice_sessions(sc["scenes"]), 1):
        who = sorted({l["speaker"] for s in ss for l in s["lines"]})
        specs.append({"id": f"voice_{i}", "종류": "voice", "도구": "aistudio", "장면": None, "샷": None, "순서": 200 + i,
                      "설명": f"내레이션 {i}번 묶음 (화자 {', '.join(map(str, who))}) — Text 모드에 통째로 붙여넣고 Composer 로 전환",
                      "프롬프트": voice_text(ss, b["speakers"]), "레퍼런스": [], "레퍼런스_작업": [], "먼저": [], "화면비": None,
                      "부가": {"모델": "gemini-3.1-flash-tts-preview (Temperature 1)",
                             "목소리": ", ".join(f"Speaker {w} = {voices[(w - 1) % len(voices)]}" for w in who),
                             "Scene(장면 설명)": f"{sc['title']} — 차분하고 따뜻한 다큐멘터리 내레이션",
                             "Director's note": "비워 둠(채우면 톤이 바뀜 — 게이트 확정)", "주소": "https://aistudio.google.com/generate-speech (project= 붙이지 말 것)"},
                      "받을위치": os.path.join(out_dir, f"voice_{i}.wav")})
    return specs


def music_specs(P):
    b = brief(P)
    mp = jload(os.path.join(sdir(P, "gen_script"), "music_prompt.json"), {})
    if not mp:
        return []
    return [{"id": "music_main", "종류": "music", "도구": "flow_music", "장면": None, "샷": None, "순서": 300,
             "설명": f"본편 배경음악 1곡 — {mp.get('mood', '')}", "프롬프트": mp["prompt"], "레퍼런스": [], "레퍼런스_작업": [], "먼저": [],
             "화면비": None, "부가": {"길이": f"{b['length']:.0f}초 이상이면 좋음(짧으면 반복해서 씀)", "곡 수 한도": gcfg(P.cfg)["음악_한도"]},
             "받을위치": os.path.join(sdir(P, "gen_music"), "music", "본편.wav")}]


def received(P, kind):
    """이 종류 작업의 받은 상태(다시 등록하면 받은시각이 바뀌어 그 단계부터 다시 돈다)."""
    return [[j["id"], j["상태"], j.get("받은시각"), j.get("워터마크")] for j in J.of_kind(P, kind)]


def register_all(P):
    n = 0
    for kind, f in (("image", image_specs), ("video", video_specs), ("voice", voice_specs), ("music", music_specs)):
        n += len(J.ensure(P, kind, f(P)))
    return n


def fill_or_wait(P, kind, label):
    """시험 모드면 시험 파일로 채우고, 아니면 남은 작업이 있을 때 '브라우저 작업 대기'로 멈춘다."""
    from ..runner import Checkpoint
    b = brief(P)
    if b.get("fixtures"):
        n = J.autofill(P, kind, b["fixtures"])
        if n:
            P.ev.log(f"시험 모드: {label} 작업 {n}개를 시험 파일로 채움")
    left = J.open_jobs(P, kind)
    if left:
        allopen = J.open_jobs(P)
        P.ev.emit(type="gen_jobs", state="waiting", kind=kind, n=len(allopen),
                  jobs=[{"id": j["id"], "kind": j["종류"], "shot": j.get("샷"), "state": j["상태"], "desc": j.get("설명", "")} for j in allopen])
        raise Checkpoint(f"브라우저 작업 {len(allopen)}개 대기({label} {len(left)}개 포함) — Claude 창에서 '생성 작업 해 줘'라고 말해 주세요")
