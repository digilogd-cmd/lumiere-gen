# -*- coding: utf-8 -*-
"""생성형 ② 대본: 두뇌 gen_script — 주제로 새로 쓰거나, 사용자 대본은 내용 그대로 장면만 나눈다.
사람이 고친 장면(gen-revise --scene N --text ...)은 두뇌 답 위에 덮어쓴다 -> 목소리부터 다시(콘티·그림은 그대로).
산출: 대본.md, script.json(덮어쓴 것), script_base.json(두뇌 답 그대로 — 콘티가 이것을 봄), music_prompt.json"""
import os
from .. import brains
from ..core import jdump, jload
from ..gates import Gate
from ..gen.brain_tasks import CHARS_PER_SEC, script_text
from ..gen.common import brief

LABEL = "대본"
VERSION = 1
DEPS = ["gen_brief"]


def overrides(P):
    return (jload(P.p("생성_수정.json"), {}) or {}).get("scenes", {})


def inputs(P):
    return [overrides(P), brains.pick(P.cfg, "gen_script")]


def run(P, d):
    b = brief(P)
    inp = {"topic": b["topic"], "script": b["script"], "length": b["length"], "style": b["style"], "speakers": b["speakers"]}
    P.ev.log("대본 만드는 중(두뇌 gen_script)" + (" — 사용자 대본은 내용 그대로, 장면만 나눔" if b["script"] else ""))
    base = brains.run(P, "gen_script", inp, log_dir=d)
    for i, s in enumerate(base["scenes"], 1):
        s["n"] = i
    jdump(base, os.path.join(d, "script_base.json"))
    out = {"title": base["title"], "scenes": [dict(s, lines=[dict(l) for l in s["lines"]]) for s in base["scenes"]]}
    ov = overrides(P)
    for k, txt in ov.items():           # 사람이 고친 장면: 그 장면 대사를 통째로 바꿈(화자는 첫 줄 화자)
        for s in out["scenes"]:
            if str(s["n"]) == str(k):
                sp = s["lines"][0]["speaker"] if s["lines"] else 1
                s["lines"] = [{"speaker": sp, "text": t.strip()} for t in str(txt).split("\n") if t.strip()]
                s["edited"] = True
                P.ev.log(f"장면 {k} 대사를 사람이 고친 문장으로 바꿈")
    full = script_text(out)
    for s in out["scenes"]:
        s["chars"] = len(" ".join(l["text"] for l in s["lines"]))
        s["sec"] = round(s["chars"] / CHARS_PER_SEC, 1)
    out["est_sec"] = round(len(full) / CHARS_PER_SEC, 1)
    out["chars"] = len(full)
    jdump(out, os.path.join(d, "script.json"))
    L = [f"# {out['title']}", "", f"예상 길이 약 {out['est_sec']:.0f}초 · {out['chars']}자 · 장면 {len(out['scenes'])}개", ""]
    for s in out["scenes"]:
        L += [f"## 장면 {s['n']} — {s['heading']}" + (" (사람이 고침)" if s.get("edited") else "") + f" · 약 {s['sec']:.0f}초", ""]
        L += [(f"**화자 {l['speaker']}** " if b["speakers"] > 1 else "") + l["text"] for l in s["lines"]] + [""]
    md = os.path.join(d, "대본.md")
    open(md, "w", encoding="utf-8").write("\n".join(L))
    P.ev.output("gen_script", P.rel(md), f"장면 {len(out['scenes'])}개 · 약 {out['est_sec']:.0f}초")
    # 배경음악 프롬프트도 여기서(대본만 있으면 되므로 — 음악 작업을 그림 작업과 같이 미리 적어 둘 수 있게)
    summ = "\n".join(f"- {s['heading']}: {s['lines'][0]['text'][:60]}" for s in base["scenes"])
    mp = brains.run(P, "gen_music_prompt", {"title": base["title"], "style": b["style"], "length": b["length"], "summary": summ}, log_dir=d)
    jdump(mp, os.path.join(d, "music_prompt.json"))
    G = Gate(P, "gen_script", d)
    G.check("장면 3~15개", 3 <= len(out["scenes"]) <= 15, f"{len(out['scenes'])}개", "3~15")
    G.check("빈 장면 없음", all(s["chars"] > 0 for s in out["scenes"]), f"빈 장면 {sum(1 for s in out['scenes'] if not s['chars'])}개", "0개")
    if not b["script"]:
        G.check("길이 목표 ±15%", abs(out["est_sec"] - b["length"]) <= b["length"] * 0.15, f"약 {out['est_sec']:.0f}초",
                f"{b['length']:.0f}초 ±15%", hard=False)
    G.finish()
    return {"scenes": len(out["scenes"]), "est_sec": out["est_sec"]}
