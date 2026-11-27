# -*- coding: utf-8 -*-
"""생성형 ③ 콘티: 두뇌 gen_board 가 장면마다 샷(인물·인원수·카메라·조명·감정·영상 여부)을 정하고,
코드가 Flow용 최종 영어 프롬프트를 조립한다(gen/prompts.py — 스타일 머리말·인물 외형·인원수·글자 금지 고정).
사람이 고친 샷 프롬프트(gen-revise --shot S05 --prompt ...)는 그 샷만 바꾼다(그 샷 그림 작업만 다시).
끝나면 그림·영상·목소리·음악 브라우저 작업을 한꺼번에 적어 둔다(gen/plan.register_all)."""
import os
from .. import brains
from ..core import jdump, jload
from ..gates import Gate
from ..gen import plan
from ..gen.common import brief, gcfg, sdir
from ..gen.prompts import shot_prompt

LABEL = "콘티"
VERSION = 1
DEPS = ["gen_script"]


def overrides(P):
    return (jload(P.p("생성_수정.json"), {}) or {}).get("shots", {})


def inputs(P):
    return [overrides(P), brains.pick(P.cfg, "gen_board"), gcfg(P.cfg)["영상_클립_한도"], gcfg(P.cfg)["이미지_한도"]]


def run(P, d):
    b = brief(P)
    g = gcfg(P.cfg)
    base = jload(os.path.join(sdir(P, "gen_script"), "script_base.json"))       # 사람이 고친 대사가 아니라 처음 대본(그림은 그대로 두려고)
    from ..gen.brain_tasks import CHARS_PER_SEC
    scenes = [{"n": s["n"], "heading": s["heading"], "lines": s["lines"],
               "sec": len(" ".join(l["text"] for l in s["lines"])) / CHARS_PER_SEC} for s in base["scenes"]]
    total = sum(s["sec"] for s in scenes)
    n = max(len(scenes), round(total / 7.5))
    veo_max = int(g["영상_클립_한도"])
    inp = {"scenes": scenes, "style": b["style"], "aspect": b["aspect"], "length": total, "n_shots_lo": max(len(scenes), n - 2),
           "n_shots_hi": n + 2, "veo_max": veo_max, "veo_n": min(veo_max, max(1, round(total / 30))), "img_max": int(g["이미지_한도"])}
    P.ev.log(f"콘티 만드는 중(두뇌 gen_board) — 샷 {inp['n_shots_lo']}~{inp['n_shots_hi']}개, 영상 클립 {inp['veo_n']}개")
    bd = brains.run(P, "gen_board", inp, log_dir=d)
    sh = bd["style_header"].strip()
    if "photorealistic" not in sh.lower():
        sh += " NOT photorealistic, NOT 3D render."
    bd["style_header"] = sh
    ov = overrides(P)
    nv = 0
    for s in bd["shots"]:
        if s.get("veo"):
            nv += 1
            if nv > veo_max:            # 한도 넘는 영상 샷은 그림 + 켄 번즈로
                s["veo"] = False
        s["prompt"] = shot_prompt(bd, s, b["aspect"])
        if s["id"] in ov:
            s["prompt"] = " ".join(str(ov[s["id"]]).split())
            if not s["prompt"].startswith(sh[:40]):        # 사람이 쓴 문장에도 스타일 머리말은 붙인다
                s["prompt"] = sh + " " + s["prompt"]
            s["edited"] = True
            P.ev.log(f"샷 {s['id']} 프롬프트를 사람이 고친 문장으로")
    jdump(bd, os.path.join(d, "board.json"))
    L = [f"# 콘티 — {base['title']}", "", f"화풍: {b['style']} · {b['aspect']} · 샷 {len(bd['shots'])}개 · 영상(Veo) {sum(1 for s in bd['shots'] if s['veo'])}개", "",
         "## 스타일 머리말(모든 프롬프트 맨 앞)", sh, "", "## 인물"]
    L += [f"- **{c['name']}** ({c['key']}): {c['look']}" for c in bd["characters"]] or ["- (반복 인물 없음)"]
    for sc in scenes:
        L += ["", f"## 장면 {sc['n']} — {sc['heading']} (약 {sc['sec']:.0f}초)"]
        for s in [s for s in bd["shots"] if s["scene"] == sc["n"]]:
            L += [f"- **{s['id']}** {'🎬 영상' if s['veo'] else '🖼 그림'} · {s['label']} · {s['camera']} · 인물 {', '.join(s['chars']) or '없음'} ({s['people']}명)",
                  f"  - {s['prompt']}"] + ([f"  - 움직임: {s['motion']}"] if s["veo"] else [])
    md = os.path.join(d, "콘티.md")
    open(md, "w", encoding="utf-8").write("\n".join(L) + "\n")
    P.ev.output("gen_board", P.rel(md), f"샷 {len(bd['shots'])}개")
    nj = plan.register_all(P)
    P.ev.log(f"브라우저 작업 {nj}개를 적어 둠(그림·영상·목소리·음악) — 브라우저_작업.json")
    G = Gate(P, "gen_board", d)
    G.check("샷마다 프롬프트·스타일 머리말", all(s["prompt"].startswith(sh[:40]) for s in bd["shots"]),
            f"{sum(1 for s in bd['shots'] if s['prompt'].startswith(sh[:40]))}/{len(bd['shots'])}", "전부")
    G.check("인원수 명시", all(("people" in s["prompt"] or "person" in s["prompt"]) for s in bd["shots"]),
            f"{sum(1 for s in bd['shots'] if 'people' in s['prompt'] or 'person' in s['prompt'])}/{len(bd['shots'])}", "전부", hard=False)
    G.check("영상(Veo) 샷 한도", sum(1 for s in bd["shots"] if s["veo"]) <= veo_max, f"{sum(1 for s in bd['shots'] if s['veo'])}개", f"≤ {veo_max}")
    G.check("그림 장수 한도", len(bd["shots"]) + len(bd["characters"]) <= int(g["이미지_한도"]),
            f"{len(bd['shots']) + len(bd['characters'])}장", f"≤ {g['이미지_한도']}")
    G.check("줄바꿈 없는 한 문단", all("\n" not in s["prompt"] for s in bd["shots"]), "확인", "한 문단")
    G.finish()
    return {"shots": len(bd["shots"]), "veo": sum(1 for s in bd["shots"] if s["veo"]), "chars": len(bd["characters"])}
