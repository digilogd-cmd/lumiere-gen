# -*- coding: utf-8 -*-
"""생성형 ⑨ 음악 [브라우저]: Flow Music 으로 본편 배경음악 1곡(곡 수 한도 생성.음악_한도).
받은 곡은 music/본편.wav. 못 받으면(포기) 키트 기본 배경음(kits/audio/기본_배경음.wav) 또는 잔잔한 패드 합성으로 대신(외부 곡 다운로드 금지)."""
import os
from ..core import ROOT, jdump, probe_duration, run as sh
from ..gates import Gate
from ..gen import jobs as J, plan
from ..gen.common import brief, gcfg
from ..gen.render import synth_pad

LABEL = "음악(브라우저)"
VERSION = 1
DEPS = ["gen_align"]
KIT_BGM = os.path.join(ROOT, "kits", "audio", "기본_배경음.wav")


def inputs(P):
    try:
        return [[s["id"], s["프롬프트"]] for s in plan.music_specs(P)] + [plan.received(P, "music")] + [bool(brief(P).get("fixtures")), (P.meta.get("gen") or {}).get("music")]
    except Exception:
        return None


def fallback(P, d, why):
    out = os.path.join(d, "music", "본편.wav")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(KIT_BGM):
        sh(["ffmpeg", "-y", "-v", "error", "-i", KIT_BGM, "-ac", "2", "-ar", "48000", out], capture_output=True)
        src = "키트 기본 배경음(반복)"
    else:
        synth_pad(out, max(30.0, brief(P)["length"] + 5))
        src = "패드 합성"
    P.ev.log(f"배경음악 대체: {src} — {why}", "warn")
    return out, src


def run(P, d):
    J.ensure(P, "music", plan.music_specs(P))
    mode = (P.meta.get("gen") or {}).get("music")
    src = None
    if mode == "local":
        for j in J.open_jobs(P, "music"):
            J.set_state(P, j["id"], "포기", "설정으로 대체 음악 사용")
    plan.fill_or_wait(P, "music", "음악")
    js = J.of_kind(P, "music")
    got = [j for j in js if j["상태"] == "완료" and os.path.exists(j["받을위치"])]
    if got:
        out, src = got[0]["받을위치"], "Flow Music"
    else:
        out, src = fallback(P, d, (js[0].get("메모") if js else "") or "음악 작업 없음")
    dur = probe_duration(out)
    lim = int(gcfg(P.cfg)["음악_한도"])
    jdump({"file": P.rel(out), "dur": round(dur, 2), "source": src, "songs": len(js)}, os.path.join(d, "music.json"))
    P.ev.output("gen_music", P.rel(out), f"{dur:.0f}초 · {src}")
    G = Gate(P, "gen_music", d)
    G.check("음악 길이 측정", dur > 5, f"{dur:.1f}초", "> 5초")
    G.check("음악 곡 수 한도", len(js) <= lim, f"{len(js)}곡", f"≤ {lim}")
    G.check("Flow Music 곡 사용", src == "Flow Music", src, "Flow Music", hard=False)
    G.finish()
    return {"dur": round(dur, 1), "source": src}
