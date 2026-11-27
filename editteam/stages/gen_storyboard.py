# -*- coding: utf-8 -*-
"""생성형 ⑤ 스토리보드: 받은 그림으로 콘티_스토리보드.jpg(샷 번호·대사 요약·예상 길이) + 스토리보드.md.
(Flow 스토리보드 스튜디오는 입력 자동화가 안 돼서 쓰지 않는다 — 지침서 §6)"""
import os
from PIL import Image, ImageDraw, ImageFont
from ..design import font
from ..gates import Gate
from ..gen.common import sdir
from ..gen.plan import board, script

LABEL = "스토리보드"
VERSION = 1
DEPS = ["gen_images"]


def inputs(P):
    return []


def est_times(sc, bd):
    """대본 글자 수로 장면별 예상 길이 -> 샷마다 weight 비율로 나눈 예상 초."""
    from ..gen.brain_tasks import CHARS_PER_SEC
    out = {}
    for s in sc["scenes"]:
        sec = len(" ".join(l["text"] for l in s["lines"])) / CHARS_PER_SEC
        sh = [x for x in bd["shots"] if x["scene"] == s["n"]]
        tw = sum(max(0.2, float(x.get("weight") or 1)) for x in sh) or 1
        for x in sh:
            out[x["id"]] = sec * max(0.2, float(x.get("weight") or 1)) / tw
    return out


def sheet(P, out, cols=4, tw=440):
    bd, sc = board(P), script(P)
    img_dir = os.path.join(sdir(P, "gen_images"), "images")
    est = est_times(sc, bd)
    heads = {s["n"]: s for s in sc["scenes"]}
    f = font("barun")["path"]
    F0, F1, F2 = ImageFont.truetype(f, 26), ImageFont.truetype(f, 20), ImageFont.truetype(f, 16)
    shots = bd["shots"]
    th = int(tw * 9 / 16)
    cell_h = th + 78
    rows = (len(shots) + cols - 1) // cols
    W = cols * (tw + 16) + 16
    im = Image.new("RGB", (W, rows * (cell_h + 16) + 70), (22, 22, 24))
    dr = ImageDraw.Draw(im)
    dr.text((16, 18), f"{sc['title']} — 콘티 스토리보드 · 샷 {len(shots)}개 · 예상 {sum(est.values()):.0f}초", font=F0, fill=(255, 210, 90))
    for i, s in enumerate(shots):
        x, y = 16 + (i % cols) * (tw + 16), 70 + (i // cols) * (cell_h + 16)
        p = os.path.join(img_dir, f"{s['id']}.png")
        if os.path.exists(p):
            t = Image.open(p).convert("RGB")
            k = max(tw / t.width, th / t.height)
            t = t.resize((int(t.width * k) + 1, int(t.height * k) + 1))
            l0, t0 = (t.width - tw) // 2, (t.height - th) // 2
            im.paste(t.crop((l0, t0, l0 + tw, t0 + th)), (x, y))
        else:
            dr.rectangle((x, y, x + tw, y + th), outline=(160, 60, 60), width=2)
        dr.text((x, y + th + 6), ("[영상] " if s.get("veo") else "") + f"{s['id']}  ~{est.get(s['id'], 0):.1f}초", font=F1, fill=(255, 255, 255))
        line = (heads.get(s["scene"], {}).get("lines") or [{"text": ""}])[0]["text"]
        dr.text((x, y + th + 34), (s.get("label") or "")[:28], font=F2, fill=(200, 200, 205))
        dr.text((x, y + th + 56), ("“" + line[:24] + "…”") if line else "", font=F2, fill=(150, 150, 160))
    im.save(out, quality=88)
    return est


def run(P, d):
    out = os.path.join(d, "콘티_스토리보드.jpg")
    est = sheet(P, out)
    bd, sc = board(P), script(P)
    L = [f"# 스토리보드 — {sc['title']}", "", "그림 확인: `콘티_스토리보드.jpg`. 실제 컷 길이는 목소리를 받은 뒤(맞춰 보기 단계) 정해진다.", ""]
    for s in sc["scenes"]:
        L += [f"## 장면 {s['n']} — {s['heading']}", ""] + [f"> {l['text']}" for l in s["lines"]] + [""]
        for x in [x for x in bd["shots"] if x["scene"] == s["n"]]:
            L.append(f"- {'🎬' if x.get('veo') else '🖼'} **{x['id']}** (~{est.get(x['id'], 0):.1f}초) {x.get('label', '')} — {x['camera']}")
        L.append("")
    open(os.path.join(d, "스토리보드.md"), "w", encoding="utf-8").write("\n".join(L))
    P.ev.output("gen_storyboard", P.rel(out), f"샷 {len(bd['shots'])}개")
    P.ev.preview("gen_storyboard", P.rel(out), "콘티 스토리보드")
    G = Gate(P, "gen_storyboard", d)
    G.check("스토리보드 그림", os.path.exists(out), "있음" if os.path.exists(out) else "없음", "있음", hard=False)
    G.finish()
    return {"shots": len(bd["shots"])}
