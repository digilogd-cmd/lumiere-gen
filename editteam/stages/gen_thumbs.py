# -*- coding: utf-8 -*-
"""생성형 ⑫ 썸네일·제목·설명: 두뇌 titles_desc(편집형과 같은 Task — 자막 문장을 받아쓰기 대신 줌)로 제목 3종·썸네일 문구 3종·요약·해시태그.
썸네일은 편집형 롱폼 템플릿(th_render.long_thumb — 얼굴 피하기 포함)에 받은 그림을 사진으로. 세로 영상이면 세로 썸네일도.
설명 끝에 'AI로 제작한 영상입니다'를 코드로 붙인다(빠뜨리지 않게)."""
import os
from PIL import Image
from .. import brains, design
from ..core import jdump, jload
from ..gates import Gate
from ..gen.common import brief, sdir
from ..gen.plan import board, script
from ..thumbs import detect_face, long_thumb, short_face, MIN

LABEL = "썸네일·제목·설명"
VERSION = 1
DEPS = ["gen_final"]
AI_NOTE = "※ 이 영상의 그림·영상·음악·목소리는 AI로 제작한 영상입니다."


def inputs(P):
    return [jload(P.p("썸네일_문구.json"), {}), (P.cfg.get("썸네일") or {}).get("포인트색", "red"), P.cfg["채널"].get("로고"),
            P.cfg["채널"].get("이름"), brains.pick(P.cfg, "titles_desc")]


def pick_photos(P, n=3):
    """썸네일 사진: 인물이 나오는 클로즈업 -> 미디엄 -> 나머지 순(서로 다른 샷)."""
    img_dir = os.path.join(sdir(P, "gen_images"), "images")
    rank = lambda s: (0 if s.get("chars") else 1, 0 if "close" in s["camera"].lower() else (1 if "medium" in s["camera"].lower() else 2))
    shots = [s for s in sorted(board(P)["shots"], key=rank) if os.path.exists(os.path.join(img_dir, s["id"] + ".png"))]
    return [os.path.join(img_dir, s["id"] + ".png") for s in shots[:n]]


def run(P, d):
    design.set_thumb_color(P.cfg)
    b, sc = brief(P), script(P)
    cards = jload(os.path.join(sdir(P, "gen_align"), "cards.json"))
    sents = [{"id": i + 1, "s": c["s"], "e": c["e"], "text": c["text"]} for i, c in enumerate(cards)]
    chan = (P.cfg.get("채널") or {}).get("이름", "") or "이 채널"
    meta = brains.run(P, "titles_desc", {"channel": chan, "sentences": sents, "hook": sents[0]["text"] if sents else "",
                                         "prev_titles": []}, log_dir=d)
    ov = jload(P.p("썸네일_문구.json"), {}) or {}
    lines_all = [ov.get(str(i + 1)) or [x for x in (t["line1"], t["line2"], t.get("line3", "")) if x.strip()] for i, t in enumerate(meta["thumbs"][:3])]
    logo = P.cfg["채널"].get("로고") or ""
    photos = pick_photos(P, 3)
    log = []
    for i, (lines, ph) in enumerate(zip(lines_all, photos * 3), 1):
        photo = Image.open(ph).convert("RGB")
        r = long_thumb(os.path.join(d, f"썸네일_{i}.jpg"), photo, lines, logo, "face", detect_face(photo), chan=(P.cfg.get("채널") or {}).get("이름", ""))
        r.update(lines=lines, photo=os.path.basename(ph))
        log.append(r)
        sm = r["file"][:-4] + "_s.jpg"
        Image.open(r["file"]).resize((480, 270)).save(sm, quality=85)
        P.ev.preview("thumb", P.rel(sm), f"썸네일 {i} · {' '.join(lines)}")
    vert = None
    if b["vertical"] and photos:
        vert = short_face(os.path.join(d, "썸네일_세로.jpg"), Image.open(photos[0]).convert("RGB"), lines_all[0][:2], [], logo)
    open(os.path.join(d, "제목.txt"), "w", encoding="utf-8").write("\n".join(f"{i + 1}. {t}" for i, t in enumerate(meta["titles"])) + "\n")
    desc = [meta["summary"].strip(), "", " ".join(meta.get("hashtags", [])), "", AI_NOTE]
    open(os.path.join(d, "설명.txt"), "w", encoding="utf-8").write("\n".join(desc) + "\n")
    jdump({"titles": meta["titles"], "thumbs": lines_all, "log": log, "vertical": vert}, os.path.join(d, "thumbs.json"))
    P.ev.output("gen_thumbs", P.rel(os.path.join(d, "썸네일_1.jpg")), f"썸네일 {len(log)}종 · 제목 {len(meta['titles'])}종")
    G = Gate(P, "gen_thumbs", d)
    G.check("썸네일 파일 3종", len(log) == 3 and all(os.path.exists(r["file"]) for r in log), f"{len(log)}종", "3종")
    for i, r in enumerate(log, 1):
        G.check(f"썸네일 {i}: 글자 크기 {MIN} 이상", r["min_ok"], ", ".join(map(str, r["sizes"])), f"≥ {MIN}", "6-0", hard=False)
        G.check(f"썸네일 {i}: 사진 쪽으로 안 넘침", not r["fit_over"], "넘침" if r["fit_over"] else "안 넘침", "안 넘침", "6-0", hard=False)
        G.check(f"썸네일 {i}: 한 줄 10자 이내", all(len(x.replace(" ", "")) <= 10 for x in r["lines"]),
                " / ".join(f"{len(x.replace(' ', ''))}자" for x in r["lines"]), "≤ 10자", "6-0", hard=False)
    G.check("설명에 AI 제작 표기", AI_NOTE in open(os.path.join(d, "설명.txt"), encoding="utf-8").read(), "있음", "있음")
    if vert:
        G.check("세로 썸네일 안전영역", vert["safe_ok"], f"제목 끝 {int(vert['text_bottom'])}", "320~1600", "11-4-V", hard=False)
    G.finish()
    return {"thumbs": len(log), "titles": len(meta["titles"])}
