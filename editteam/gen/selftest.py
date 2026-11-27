# -*- coding: utf-8 -*-
"""생성형 자가 검사(시험 B): 브라우저 없이 kits/gen_selftest 의 시험 대본 + 시험 파일(실제 Flow·AI Studio에서 받아 워터마크를 지운 것)로
생성형 13단계를 끝까지 돌려 판정한다.  python -m editteam selftest gen [--vertical]
- 코드는 매번 처음부터 실제로 돈다(done.json·작업 목록·받은 파일·렌더 결과를 지움). 두뇌 답은 입력이 같으면 저장해 둔 것을 다시 쓴다.
- 판정: 13단계 완료 + 멈추는(hard) 검문소 통과 + 완성 파일·길이·음량·화면 크기. 결과는 _보관/자가검사_gen.json, 대시보드 '엔진 관리'."""
import glob, json, os, shutil, time

from ..core import ROOT, Project, jdump, jload, probe_duration, probe_video, user_settings

KIT = os.path.join(ROOT, "kits", "gen_selftest")
RESULT = os.path.join(ROOT, "_보관", "자가검사_gen.json")
CLEAN = ("브라우저_작업.json", "생성_수정.json", "결과_요약.md", "검문소.md")
CLEAN_DIRS = ("gen_04_images/images", "gen_04_images/받은", "gen_06_video/video", "gen_06_video/받은", "gen_07_voice/voice",
              "gen_07_voice/받은", "gen_09_music/music", "gen_09_music/받은", "완성")


def one(name, vertical):
    from .. import runner
    from ..gates import all_gates
    P = Project(name)
    for f in glob.glob(os.path.join(P.dir, "gen_*", "done.json")) + glob.glob(os.path.join(P.dir, "gen_*", "검문소_*.json")):
        os.remove(f)
    for f in CLEAN:
        if os.path.exists(P.p(f)):
            os.remove(P.p(f))
    for d in CLEAN_DIRS:
        shutil.rmtree(P.p(*d.split("/")), ignore_errors=True)
    for pat in ("gen_10_assemble/*.mp4", "gen_10_assemble/*.wav", "gen_11_final/*.mp4", "gen_12_thumbs/*.jpg", "gen_07_voice/*.wav"):
        for f in glob.glob(os.path.join(P.dir, *pat.split("/"))):
            os.remove(f)
    P.meta.update({"gen": {"topic": "", "script_path": os.path.join(KIT, "대본.md"), "length": 75, "style": "따뜻한 수채화풍 일러스트",
                           "speakers": 1, "vertical": vertical, "fixtures": os.path.join(KIT, "fixtures")},
                   "mode": "gen", "upload": "never", "selftest": True, "settings_at_start": user_settings()})
    P.save_meta()
    P = Project(name)
    open(P.p("runner.pid"), "w").write(str(os.getpid()))
    res, err = None, ""
    try:
        res = runner.run_pipeline(P, part="gen")
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    bad = []
    if res != "done":
        last = [json.loads(l) for l in open(P.p("events.jsonl"), encoding="utf-8")][-40:] if os.path.exists(P.p("events.jsonl")) else []
        msg = next((e.get("msg") for e in reversed(last) if e.get("state") in ("error", "waiting")), "")
        bad.append(f"끝까지 못 감({res or err}) {msg}".strip())
    bad += [f"[{n}] {x['rule']}: {x['measured']}" for n, it in all_gates(P) for x in it if not x["ok"] and x.get("hard", True)]
    fi = jload(os.path.join(P.p("gen_11_final"), "final_info.json"), {})
    out = os.path.join(P.dir, "완성", "1_완성본.mp4")
    W, H = (1080, 1920) if vertical else (1920, 1080)
    info = {"dur": None, "lufs": fi.get("lufs"), "size": None}
    if res == "done":
        if not os.path.exists(out):
            bad.append("완성 폴더에 완성본이 없음")
        else:
            info["dur"] = round(probe_duration(out), 2)
            w, h, _ = probe_video(out)
            info["size"] = f"{w}x{h}"
            if not 40 <= info["dur"] <= 150:
                bad.append(f"완성본 길이가 이상함({info['dur']}초)")
            if (w, h) != (W, H):
                bad.append(f"화면 크기 {w}x{h} (기준 {W}x{H})")
        if fi.get("lufs") is None or abs(float(fi["lufs"]) + 11) > 1.0:
            bad.append(f"음량이 기준에서 벗어남({fi.get('lufs')} LUFS)")
    soft = sum(1 for _, it in all_gates(P) for x in it if not x["ok"] and not x.get("hard", True))
    return dict(info, ok=not bad, problems=bad, soft_warns=soft, final=os.path.relpath(out, ROOT).replace(os.sep, "/") if not bad else None)


def run(vertical=False):
    t0 = time.time()
    runs = {"가로": one("_자가검사_gen", False)}
    if vertical:
        runs["세로"] = one("_자가검사_gen_세로", True)
    probs = [f"{k}: {p}" for k, r in runs.items() for p in r["problems"]]
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "ok": not probs, "problems": probs, "runs": runs, "sec": round(time.time() - t0),
           "soft_warns": sum(r["soft_warns"] for r in runs.values())}
    os.makedirs(os.path.dirname(RESULT), exist_ok=True)
    jdump(out, RESULT)
    return out


def last():
    return jload(RESULT, None)
