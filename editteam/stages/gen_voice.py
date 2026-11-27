# -*- coding: utf-8 -*-
"""생성형 ⑦ 목소리 [브라우저]: AI Studio 음성 생성(gemini TTS, Composer)으로 내레이션. 화자 2명씩 묶음(세션)으로.
- 재시도 한도를 넘으면(Run 클릭이 안 먹는 등) 윈도우 내장 한국어 음성(Microsoft Heami)으로 '임시 음성'을 만든다(기획서 7장).
- 묶음들을 0.6초 쉬고 이어 voice_all.wav (48kHz 모노). 무음만 있거나 끝이 잘리면 멈춘다."""
import os, re
import numpy as np
from ..core import jdump, run as sh
from ..gates import Gate
from ..gen import jobs as J, plan
from ..gen.common import brief
from ..gen.render import local_tts
from ..media import read_wav, write_wav

LABEL = "목소리(브라우저)"
VERSION = 1
DEPS = ["gen_video"]
GAP = 0.6
SR = 48000


def inputs(P):
    try:
        return [[s["id"], s["프롬프트"], s["부가"]] for s in plan.voice_specs(P)] + [plan.received(P, "voice")] + [bool(brief(P).get("fixtures")), (P.meta.get("gen") or {}).get("voice")]
    except Exception:
        return None


def env_db(a, sr, win=0.01):
    n = int(sr * win)
    m = len(a) // n
    x = a[:m * n].astype(np.float32).reshape(m, n) / 32768.0
    return 20 * np.log10(np.sqrt((x ** 2).mean(1)) + 1e-9)


def run(P, d):
    J.ensure(P, "voice", plan.voice_specs(P))
    use_local = (P.meta.get("gen") or {}).get("voice") == "local"
    for j in J.of_kind(P, "voice"):           # 임시 음성: 설정으로 고른 경우 또는 브라우저에서 포기한 경우
        if (use_local and j["상태"] in J.OPEN) or j["상태"] == "포기":
            txt = "\n".join(re.sub(r"^Speaker \d+:\s*", "", l) for l in j["프롬프트"].splitlines())
            tmp = os.path.join(d, f"_local_{j['id']}.wav")
            P.ev.log(f"{j['id']}: 윈도우 내장 음성(Heami)으로 임시 내레이션을 만듭니다", "warn")
            local_tts(txt, tmp)
            J.done(P, j["id"], tmp, wm=False, note="임시 음성(윈도우 Heami) — AI Studio 음성으로 바꿀 것")
    plan.fill_or_wait(P, "voice", "목소리")
    js = sorted(J.of_kind(P, "voice"), key=lambda j: j["순서"])
    parts = []
    for j in js:
        tmp = os.path.join(d, f"_{j['id']}_48k.wav")
        sh(["ffmpeg", "-y", "-v", "error", "-i", j["받을위치"], "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", tmp], capture_output=True)
        a, _ = read_wav(tmp)
        os.remove(tmp)
        parts.append(a[:, 0])
    gap = np.zeros(int(GAP * SR), np.int16)
    allv = np.concatenate([x for p in parts for x in (p, gap)][:-1]) if parts else np.zeros(1, np.int16)
    out = os.path.join(d, "voice_all.wav")
    write_wav(out, allv, SR)
    dur = len(allv) / SR
    db = env_db(allv, SR)
    peak = float(db.max()) if len(db) else -120
    voiced = np.where(db > peak - 35)[0]
    longest = 0.0
    if len(voiced):
        gaps = np.diff(voiced)
        longest = float(gaps.max() * 0.01) if len(gaps) else 0.0
    tail = float(db[-5:].max()) if len(db) >= 5 else peak
    from ..gen.plan import script
    est = script(P)["est_sec"]
    temp = [j["id"] for j in js if "임시 음성" in (j.get("메모") or "")]
    info = {"file": P.rel(out), "dur": round(dur, 2), "parts": [{"id": j["id"], "dur": round(len(p) / SR, 2), "note": j.get("메모", "")} for j, p in zip(js, parts)],
            "peak_db": round(peak, 1), "longest_silence": round(longest, 2), "tail_db": round(tail, 1), "temporary": temp}
    jdump(info, os.path.join(d, "voice.json"))
    P.ev.output("gen_voice", P.rel(out), f"{dur:.1f}초" + (" · 임시 음성" if temp else ""))
    G = Gate(P, "gen_voice", d)
    G.check("소리가 있음(무음 아님)", peak > -40 and len(voiced) > 100, f"최대 {peak:.0f} dBFS", "> -40 dBFS")
    G.check("중간에 긴 무음 없음", longest < 4.0, f"가장 긴 쉼 {longest:.1f}초", "< 4초")
    G.check("끝이 잘리지 않음(마지막 0.05초 조용)", tail < peak - 25, f"끝 {tail:.0f} dBFS (최대 {peak:.0f})", "최대보다 25dB 이상 작게")
    G.check("길이 목표 ±20%", abs(dur - est) <= est * 0.2, f"{dur:.0f}초", f"예상 {est:.0f}초 ±20%", hard=False)
    G.check("임시 음성 아님", not temp, f"임시 음성 {len(temp)}개" if temp else "AI Studio 음성", "AI Studio 음성", hard=False)
    G.finish()
    return {"dur": round(dur, 2), "temporary": len(temp)}
