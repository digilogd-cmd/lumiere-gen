# -*- coding: utf-8 -*-
"""생성형 ⑥ 영상 클립 [브라우저]: 콘티에서 고른 핵심 샷만 Flow 영상(Veo, 그림 -> 영상). 크레딧 한도(생성.영상_클립_한도) 안에서.
받은 클립은 워터마크를 지워(delogo) video/S번호.mp4. 못 만든(포기) 샷은 조립 때 그림 + 켄 번즈로."""
import os
from ..core import jdump, probe_duration, probe_video
from ..gates import Gate
from ..gen import jobs as J, plan
from ..gen.common import brief, gcfg

LABEL = "영상 클립(브라우저)"
VERSION = 1
DEPS = ["gen_storyboard"]


def inputs(P):
    try:
        return [[s["id"], s["프롬프트"], s["레퍼런스_작업"]] for s in plan.video_specs(P)] + [plan.received(P, "video")] + [bool(brief(P).get("fixtures")), gcfg(P.cfg)["영상_클립_한도"]]
    except Exception:
        return None


def run(P, d):
    J.ensure(P, "video", plan.video_specs(P))
    plan.fill_or_wait(P, "video", "영상")
    js = J.of_kind(P, "video")
    info = []
    for j in js:
        f = j["받을위치"]
        if j["상태"] == "완료" and os.path.exists(f):
            w, h, fps = probe_video(f)
            info.append({"shot": j["샷"], "file": P.rel(f), "dur": round(probe_duration(f), 2), "size": [w, h], "fps": round(fps, 2), "wm": j.get("워터마크")})
        else:
            info.append({"shot": j["샷"], "file": None, "fallback": "그림 + 켄 번즈", "why": j.get("메모", "")})
            P.ev.log(f"샷 {j['샷']} 영상 클립 없음 -> 그림 + 켄 번즈로", "warn")
    jdump({"clips": info}, os.path.join(d, "video.json"))
    lim = int(gcfg(P.cfg)["영상_클립_한도"])
    got = [x for x in info if x.get("file")]
    G = Gate(P, "gen_video", d)
    G.check("영상 크레딧 한도", len(js) <= lim, f"{len(js)}클립", f"≤ {lim}")
    G.check("받은 클립 길이 1초 이상", all(x["dur"] >= 1.0 for x in got), ", ".join(f"{x['dur']}초" for x in got) or "없음", "≥ 1초")
    G.check("받은 클립 해상도(짧은 쪽 ≥ 480px)", all(min(x["size"]) >= 480 for x in got),
            ", ".join(f"{x['size'][0]}x{x['size'][1]}" for x in got) or "없음", "≥ 480px")
    G.check("워터마크 처리 표시", all(x.get("wm") for x in got), f"표시 없음 {sum(1 for x in got if not x.get('wm'))}개", "0개")
    G.check("못 만든 클립 없음", len(got) == len(info), f"{len(info) - len(got)}개 켄 번즈로 대체", "0개", hard=False)
    G.finish()
    return {"clips": len(got), "fallback": len(info) - len(got)}
