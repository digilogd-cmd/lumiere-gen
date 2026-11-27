# -*- coding: utf-8 -*-
"""생성형 ⑩ 조립: 목소리로 잰 장면 시각에 맞춰 컷을 배치한다(게이트 원칙: 목소리가 확정되기 전엔 컷 길이를 정하지 않는다).
- 장면 안의 샷은 콘티의 weight 비율로 나눔(한 컷 최소 1.6초 — 모자라면 그 장면의 덜 중요한 그림 샷을 뺌)
- 영상 클립(Veo)은 그대로(구간에 맞춰 0.7~1.5배 속도 + 모자라면 마지막 프레임 유지), 나머지 그림은 켄 번즈, 디졸브 0.4초
- 소리: 목소리(앞 여백만큼 늦춤, 영상 끝까지 apad) + 음악(사이드체인 덕킹)
산출: assembled.mp4(무음), mix.wav, cuts.json"""
import os
from ..core import jdump, jload, probe_duration
from ..gates import Gate
from ..gen.common import brief, gcfg, sdir
from ..gen.plan import board
from ..gen.render import MOVES, mix_voice_music, render_timeline

LABEL = "조립"
VERSION = 1
DEPS = ["gen_music"]
FPS = 30
MIN_CUT = 1.6


def inputs(P):
    g = gcfg(P.cfg)
    return [g["디졸브_초"], g["음악_크기"], g["앞_여백_초"], g["뒤_여백_초"]]


def plan_cuts(scenes, shots, lead, T, vids):
    """-> [(시작, 끝, 소스)] 0~T 빈틈없이."""
    cuts = []
    for k, sc in enumerate(scenes):
        s0 = 0.0 if k == 0 else lead + sc["s"]
        s1 = T if k == len(scenes) - 1 else lead + scenes[k + 1]["s"]
        sh = [x for x in shots if x["scene"] == sc["n"]] or ([] if cuts else shots[:1])
        if not sh:                 # 그림이 없는 장면: 앞 컷을 늘린다
            cuts[-1][1] = round(s1, 3)
            continue
        while len(sh) > 1 and (s1 - s0) / len(sh) < MIN_CUT:      # 너무 짧으면 그림 샷부터 뺀다(가벼운 것 먼저)
            drop = min([x for x in sh if not x.get("veo")] or sh, key=lambda x: float(x.get("weight") or 1))
            sh.remove(drop)
        tw = sum(max(0.2, float(x.get("weight") or 1)) for x in sh) or 1
        t = s0
        for i, x in enumerate(sh):
            e = s1 if i == len(sh) - 1 else t + (s1 - s0) * max(0.2, float(x.get("weight") or 1)) / tw
            cuts.append([round(t, 3), round(e, 3), x])
            t = e
    out, mi = [], 0
    for s, e, x in cuts:
        if x["id"] in vids:
            src = {"kind": "video", "file": vids[x["id"]], "shot": x["id"]}
        else:
            src = {"kind": "image", "file": x["_img"], "shot": x["id"], "move": MOVES[mi % len(MOVES)]}
            mi += 1
        out.append((s, e, src))
    return out


def run(P, d):
    b, g = brief(P), gcfg(P.cfg)
    W, H = b["W"], b["H"]
    al = jload(os.path.join(sdir(P, "gen_align"), "장면시각.json"))
    voice = os.path.join(sdir(P, "gen_voice"), "voice_all.wav")
    vdur = probe_duration(voice)
    lead, tail = float(g["앞_여백_초"]), float(g["뒤_여백_초"])
    T = round((lead + vdur + tail) * FPS) / FPS
    bd = board(P)
    img_dir = os.path.join(sdir(P, "gen_images"), "images")
    shots = []
    for x in bd["shots"]:
        x = dict(x, _img=os.path.join(img_dir, f"{x['id']}.png"))
        if os.path.exists(x["_img"]):
            shots.append(x)
    from ..core import ROOT
    vids = {c["shot"]: os.path.join(ROOT, c["file"])            # video.json 의 file 은 P.rel(LUMIERE_GEN 기준) 경로
            for c in jload(os.path.join(sdir(P, "gen_video"), "video.json"), {"clips": []})["clips"] if c.get("file")}
    slots = plan_cuts(al["scenes"], shots, lead, T, vids)
    jdump([{"s": s, "e": e, "shot": src["shot"], "kind": src["kind"], "move": src.get("move")} for s, e, src in slots], os.path.join(d, "cuts.json"))
    P.ev.log(f"컷 {len(slots)}개 배치(영상 클립 {sum(1 for s in slots if s[2]['kind'] == 'video')}개) · 전체 {T:.1f}초 = 앞 {lead}초 + 목소리 {vdur:.1f}초 + 뒤 {tail}초")
    out = os.path.join(d, "assembled.mp4")
    render_timeline(slots, out, W, H, FPS, dissolve=float(g["디졸브_초"]), progress=lambda u: P.ev.progress(5 + 75 * u, f"조립 렌더 {u * 100:.0f}%"))
    mi = jload(os.path.join(sdir(P, "gen_music"), "music.json"), {})
    music = os.path.join(ROOT, mi["file"]) if mi.get("file") else None
    mix = os.path.join(d, "mix.wav")
    P.ev.progress(85, "목소리 + 음악(덕킹)")
    mres = mix_voice_music(voice, music, T, lead, float(g["음악_크기"]), mix)
    vd_, ad_ = probe_duration(out), probe_duration(mix)
    jdump({"T": T, "lead": lead, "tail": tail, "voice_dur": round(vdur, 3), "video_dur": round(vd_, 3), "audio_dur": round(ad_, 3), "mix": mres,
           "cuts": len(slots)}, os.path.join(d, "assemble.json"))
    P.ev.output("gen_assemble", P.rel(out), f"{vd_:.1f}초 · 컷 {len(slots)}개")
    G = Gate(P, "gen_assemble", d)
    G.check("영상·소리 길이 차", abs(vd_ - ad_) <= 0.1, f"영상 {vd_:.2f}초 / 소리 {ad_:.2f}초", "≤ 0.1초")
    G.check("끝 잘림 없음(목소리가 영상 안에 다 들어감)", ad_ >= lead + vdur - 0.05 and vd_ >= lead + vdur - 0.05,
            f"목소리 끝 {lead + vdur:.2f}초 / 영상 {vd_:.2f}초", "목소리 끝 ≤ 영상 길이")
    G.check("한 컷 최소 길이", min(e - s for s, e, _ in slots) >= MIN_CUT - 0.3, f"{min(e - s for s, e, _ in slots):.1f}초", f"≥ {MIN_CUT}초", hard=False)
    G.finish()
    return {"T": T, "cuts": len(slots)}
