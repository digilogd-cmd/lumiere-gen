# -*- coding: utf-8 -*-
"""생성형 ④ 그림 [브라우저]: 캐릭터 시트 -> 샷 그림을 Flow(Nano Banana 2, 0크레딧)에서 만든다.
실행기는 작업 목록만 적고 기다린다. Claude가 받아서 gen-jobs --done 으로 등록하면 그때 워터마크를 지워 images/S번호_내용.png 로 둔다.
재시도 한도를 넘어 '포기'한 샷은 같은 장면(없으면 가까운) 샷 그림으로 대신하고 보고서에 남긴다."""
import os
from PIL import Image, ImageDraw
from ..core import jdump
from ..design import font
from ..gates import Gate
from ..gen import jobs as J, plan
from ..gen.common import brief

LABEL = "그림(브라우저)"
VERSION = 1
DEPS = ["gen_board"]


def inputs(P):
    try:
        return [[s["id"], s["프롬프트"], s["레퍼런스_작업"]] for s in plan.image_specs(P)] + [plan.received(P, "image")] + [bool(brief(P).get("fixtures"))]
    except Exception:
        return None


def wm_sheet(pairs, out, box=220):
    """워터마크 제거 전/후 오른쪽 아래 모서리를 나란히(눈으로 확인용)."""
    if not pairs:
        return None
    from PIL import ImageFont
    F = ImageFont.truetype(font("barun")["path"], 15)
    sheet = Image.new("RGB", (box * 2 + 30, (box + 26) * len(pairs)), (24, 24, 26))
    dr = ImageDraw.Draw(sheet)
    for i, (a, b, name) in enumerate(pairs):
        for k, f in enumerate((a, b)):
            im = Image.open(f).convert("RGB")
            w, h = im.size
            sheet.paste(im.crop((w - box, h - box, w, h)), (k * (box + 30), i * (box + 26) + 24))
        dr.text((4, i * (box + 26) + 4), f"{name}  (왼쪽 받은 그대로 / 오른쪽 제거 후)", font=F, fill=(255, 220, 90))
    sheet.save(out, quality=88)
    return out


def run(P, d):
    J.ensure(P, "image", plan.image_specs(P))
    plan.fill_or_wait(P, "image", "그림")
    js = J.of_kind(P, "image")
    shots = [j for j in js if not j.get("부가", {}).get("시트")]
    done = {j["샷"]: j for j in shots if j["상태"] == "완료"}
    subs = []
    for j in shots:
        if j["상태"] == "포기":            # 대신할 그림: 같은 장면 -> 가까운 순서
            cand = sorted(done.values(), key=lambda x: (x.get("장면") != j.get("장면"), abs(x["순서"] - j["순서"])))
            if cand:
                os.makedirs(os.path.dirname(j["받을위치"]), exist_ok=True)
                Image.open(cand[0]["받은파일"]).save(j["받을위치"])
                subs.append({"shot": j["샷"], "from": cand[0]["샷"], "why": j.get("메모", "")})
                P.ev.log(f"샷 {j['샷']} 그림을 못 만들어 {cand[0]['샷']} 그림으로 대신함", "warn")
    info = []
    for j in js:
        f = j["받을위치"]
        ok = os.path.exists(f)
        wh = Image.open(f).size if ok else (0, 0)
        info.append({"id": j["id"], "shot": j["샷"], "file": P.rel(f) if ok else None, "size": list(wh), "wm": j.get("워터마크"),
                     "state": j["상태"], "sheet": bool(j.get("부가", {}).get("시트"))})
    jdump({"images": info, "substituted": subs}, os.path.join(d, "images.json"))
    pairs = [(j["원본파일"], j["받은파일"], j["샷"]) for j in js if j["상태"] == "완료" and j.get("원본파일")
             and str(j.get("워터마크", "")).startswith("제거함")][:8]
    sh = wm_sheet(pairs, os.path.join(d, "워터마크_확인.jpg"))
    if sh:
        P.ev.preview("gen_wm", P.rel(sh), "워터마크 제거 전/후(오른쪽 아래)")
    G = Gate(P, "gen_images", d)
    shot_info = [x for x in info if not x["sheet"]]
    G.check("샷마다 그림 파일", all(x["file"] for x in shot_info), f"{sum(1 for x in shot_info if x['file'])}/{len(shot_info)}", "전부")
    G.check("해상도(짧은 쪽 ≥ 700px)", all(min(x["size"]) >= 700 for x in shot_info if x["file"]),
            ", ".join(f"{x['size'][0]}x{x['size'][1]}" for x in shot_info[:3]) + ("…" if len(shot_info) > 3 else ""), "≥ 700px", hard=False)
    G.check("워터마크 처리 표시", all(x["wm"] for x in info if x["state"] == "완료"),
            f"표시 없음 {sum(1 for x in info if x['state'] == '완료' and not x['wm'])}장", "0장")
    G.check("대신한 그림 없음", not subs, f"{len(subs)}장 대신함", "0장", hard=False)
    G.finish()
    return {"images": len(shot_info), "sheets": len(info) - len(shot_info), "substituted": len(subs)}
