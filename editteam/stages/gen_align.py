# -*- coding: utf-8 -*-
"""생성형 ⑧ 맞춰 보기: 목소리가 확정된 뒤 받아쓰기(faster-whisper)로 단어 시각을 얻고, 대본 글자를 그 시각에 붙인다
(게이트 make_srt.py 강제정렬 방식 — 받아쓰기는 시간이 정확하고 대본은 글자가 정확. 시간을 추정하지 않는다).
-> 자막 카드(마침표 빼기 등 subs.tidy_cards), 장면 경계 시각(컷 배치의 기준)."""
import difflib, os, re
from ..core import jdump, jload
from ..gates import Gate
from ..gen.common import brief, sdir
from ..gen.plan import script
from .. import subs

LABEL = "맞춰 보기(자막 시각)"
VERSION = 1
DEPS = ["gen_voice"]
FPS = 30


def inputs(P):
    return [P.cfg["받아쓰기"]["모델"], P.cfg["자막"].get("마침표_빼기", True), brief(P).get("vertical")]


def norm(s):
    return re.sub(r"[^가-힣0-9a-zA-Z]", "", s or "")


def split_cards(text, maxc):
    """대본 한 줄 -> 자막 카드(문장 끝에서 끊고, 길면 쉼표·띄어쓰기 가운데에서)."""
    out = []
    for sent in [x.strip() for x in re.findall(r"[^.!?…]+[.!?…]*", text) if x.strip()]:
        stack = [sent]
        while stack:
            t = stack.pop(0)
            if len(t) <= maxc:
                out.append(t); continue
            mid = len(t) / 2
            marks = [i for i, c in enumerate(t) if c == "," and 4 <= i <= len(t) - 4] or \
                    [i for i, c in enumerate(t) if c == " " and 4 <= i <= len(t) - 4]
            if not marks:
                out.append(t); continue
            i = min(marks, key=lambda x: abs(x - mid))
            stack[0:0] = [t[:i + 1].strip(), t[i + 1:].strip()]
    return out


def align(words, pieces):
    """words [{s,e,w}], pieces [str] -> ([[s,e]|None], 맞춘 글자 비율)."""
    ac, ao, bc, bo = [], [], [], []
    for i, w in enumerate(words):
        for ch in norm(w["w"]):
            ac.append(ch); ao.append(i)
    for i, p in enumerate(pieces):
        for ch in norm(p):
            bc.append(ch); bo.append(i)
    sm = difflib.SequenceMatcher(None, ac, bc, autojunk=False)
    hit, matched = {}, 0
    for a0, b0, n in sm.get_matching_blocks():
        matched += n
        for k in range(n):
            hit.setdefault(bo[b0 + k], []).append(ao[a0 + k])
    spans = []
    for i in range(len(pieces)):
        ws = sorted(set(hit.get(i, [])))
        spans.append([words[ws[0]]["s"], words[ws[-1]]["e"]] if ws else None)
    return spans, matched / max(1, len(bc))


def run(P, d):
    from ..whisper import load_model, transcribe
    from ..media import extract_wav
    b = brief(P)
    sc = script(P)
    vd = sdir(P, "gen_voice")
    voice = os.path.join(vd, "voice_all.wav")
    w16 = os.path.join(d, "voice16k.wav")
    if os.path.exists(w16):
        os.remove(w16)                 # 목소리를 다시 받았을 때 옛 받아쓰기 재활용 금지(게이트 지침서 §5)
    extract_wav(voice, w16)
    model, dev = load_model(P.cfg["받아쓰기"])
    P.ev.log(f"받아쓰기({P.cfg['받아쓰기']['모델']}, {'GPU' if dev == 'cuda' else 'CPU'})로 목소리 시각 재는 중")
    segs = transcribe(model, w16, P.cfg["받아쓰기"]["언어"])
    words = [{"s": w["s"], "e": w["e"], "w": w["w"].strip()} for s in segs for w in s["words"] if w["w"].strip()]
    jdump(segs, os.path.join(d, "words.json"))
    maxc = 16 if b["vertical"] else int(P.cfg["자막"].get("한줄최대", 34))
    pieces, owner = [], []
    for s in sc["scenes"]:
        for l in s["lines"]:
            for c in split_cards(l["text"], maxc):
                pieces.append(c); owner.append(s["n"])
    spans, ratio = align(words, pieces)
    vdur = jload(os.path.join(vd, "voice.json"), {}).get("dur") or (words[-1]["e"] if words else 0)
    # 못 맞춘 카드는 앞뒤 사이에 글자 수 비례로 끼운다
    i = 0
    while i < len(spans):
        if spans[i] is None:
            j = i
            while j < len(spans) and spans[j] is None:
                j += 1
            t0 = spans[i - 1][1] if i else 0.0
            t1 = spans[j][0] if j < len(spans) else vdur
            tot = sum(len(pieces[k]) for k in range(i, j)) or 1
            acc = t0
            for k in range(i, j):
                dt = (t1 - t0) * len(pieces[k]) / tot
                spans[k] = [acc, acc + dt]; acc += dt
            i = j
        i += 1
    cards = []
    for k, (p, sp, n) in enumerate(zip(pieces, spans, owner)):
        s0, e0 = sp
        nxt = spans[k + 1][0] if k + 1 < len(spans) else vdur
        e0 = nxt if nxt - e0 < 0.3 else min(e0 + 0.12, nxt)
        e0 = max(e0, s0 + 0.5)
        cards.append({"s": round(s0, 3), "e": round(e0, 3), "text": p, "scene": n})
    for a, c in zip(cards, cards[1:]):
        if a["e"] > c["s"]:
            a["e"] = c["s"]
    for c in cards:
        c["fs"], c["fe"] = int(c["s"] * FPS), max(int(c["s"] * FPS) + 1, int(round(c["e"] * FPS)))
    log = subs.tidy_cards(cards, words, P.cfg, FPS)
    for m in log:
        P.ev.log("자막 다듬기: " + m)
    scenes = []
    for s in sc["scenes"]:
        cs = [c for c in cards if c["scene"] == s["n"]]
        if cs:
            scenes.append({"n": s["n"], "s": cs[0]["s"], "e": cs[-1]["e"], "heading": s["heading"]})
    jdump(cards, os.path.join(d, "cards.json"))
    jdump({"scenes": scenes, "voice_dur": vdur, "ratio": round(ratio, 3)}, os.path.join(d, "장면시각.json"))
    srt = os.path.join(d, "subs.srt")
    subs.write_srt([(c["fs"], c["fe"], c["text"]) for c in cards], srt, FPS)
    P.ev.output("gen_align", P.rel(srt), f"자막 {len(cards)}줄 · 대본 일치 {ratio * 100:.0f}%")
    G = Gate(P, "gen_align", d)
    G.check("대본 글자 일치율", ratio >= 0.9, f"{ratio * 100:.0f}%", "≥ 90%", hard=False)
    G.check("장면마다 시각", len(scenes) == len(sc["scenes"]), f"{len(scenes)}/{len(sc['scenes'])}", "전부")
    G.check("장면 순서", all(a["s"] <= b_["s"] for a, b_ in zip(scenes, scenes[1:])), "확인", "시간 순")
    G.check(f"자막 한 줄 최대 {maxc}자", max((len(c["text"]) for c in cards), default=0) <= maxc + 2,
            f"{max((len(c['text']) for c in cards), default=0)}자", f"≤ {maxc}(+2)", hard=False)
    G.finish()
    return {"cards": len(cards), "ratio": round(ratio, 3)}
