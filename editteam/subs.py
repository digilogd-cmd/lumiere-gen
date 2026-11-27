# -*- coding: utf-8 -*-
"""프레임 정확 SRT (예전 영상 build_srt.make_srt 그대로 옮김, 입력만 일반화).
- 문장 경계 청킹(capt.chunk_sentences, SOP 11-0)
- 줄 시작/끝은 대상 영상 소리에서 실측한 실제 발화 시작/끝에 맞추고, 전부 정수 프레임으로 저장
- 숨 쉬는 정도(0.3초 미만) 틈만 붙이고, 그 이상 쉬는 곳은 앞 줄을 발화 끝 + 0.1초에서 내림"""
import math, re
import numpy as np
import capt

JOIN_GAP, HOLD = 0.30, 0.10


def fmt(frame, fps=30):
    ms_total = -(-frame * 1000 // int(fps))   # 올림: 다빈치가 한 프레임 앞으로 내리지 않게
    h, rem = divmod(ms_total, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def make_cards(groups, db, thr, fps=30, hard_max=34):
    """groups: [[{s,e,w}...], ...] (조각마다 따로 청킹) -> [(시작프레임, 끝프레임, 문장)]"""
    n = len(db)

    def onset_near(s, back=0.25, fwd=0.50, quiet=0.12):
        k, q = int(s * 100), int(quiet * 100)
        best = None
        for j in range(max(k - int(back * 100), q), min(k + int(fwd * 100), n)):
            if db[j] > thr and (db[j - q:j] < thr).all():
                if best is None or abs(j - k) < abs(best - k):
                    best = j
        return None if best is None else best / 100

    def onset(s, quiet=0.12, back_max=0.45):
        k, q = int(s * 100), int(quiet * 100)
        if 0 < k < n and db[k] > thr and db[max(k - 3, 0):k].max() > thr:
            for j in range(k, max(k - int(back_max * 100), q) - 1, -1):
                if db[j] > thr and (db[j - q:j] < thr).all():
                    return j / 100
        return onset_near(s)

    def offset(e, back=0.2, fwd=0.4, quiet=0.12):
        k, q = int(e * 100), int(quiet * 100)
        for j in range(max(k - int(back * 100), 1), min(k + int(fwd * 100), n - q)):
            if db[j - 1] >= thr and (db[j:j + q] < thr).all():
                return j / 100
        return None

    chunks = [c for g in groups if g for c in capt.chunk_sentences(g, hard_max=hard_max)]
    if not chunks:
        return []
    found = [onset(s) for s, e, t in chunks]
    deltas = [o - c[0] for o, c in zip(found, chunks) if o is not None]
    med = float(np.median(deltas)) if deltas else 0.0
    starts = [o if o is not None else c[0] + med for o, c in zip(found, chunks)]
    ends = [(offset(e) or e) for s, e, t in chunks]
    snapped = []
    for i, ((s, e, t), st, en) in enumerate(zip(chunks, starts, ends)):
        nxt = starts[i + 1] if i + 1 < len(starts) else 1e9
        en = nxt if nxt - en < JOIN_GAP else min(en + HOLD, nxt)
        fs, fe = math.floor(st * fps), round(max(en, st) * fps)
        snapped.append([fs, max(fe, fs + 1), t.rstrip(",")])
    for i in range(len(snapped) - 1):
        snapped[i + 1][0] = max(snapped[i + 1][0], snapped[i][0])       # 시작이 앞 줄보다 이르면 끌어올림(시간 역전 방지)
        snapped[i + 1][1] = max(snapped[i + 1][1], snapped[i + 1][0] + 1)
        if snapped[i + 1][0] - snapped[i][1] <= 2:
            snapped[i][1] = snapped[i + 1][0]
        if snapped[i][1] > snapped[i + 1][0]:
            snapped[i][1] = snapped[i + 1][0]
    return fix_order(snapped, fps)


def fix_order(cards, fps=30, min_sec=0.3):
    """길이 0·끝<시작 줄 고치기(10/20 1017 rough.srt '재밌죠' 0프레임 줄 — FilmCraft 가 시간 역전으로 읽음).
    다음 줄에서 min_sec 를 빌려 오고, 빌릴 여유가 없으면 다음 줄과 합친다."""
    out = [list(c) for c in cards]
    mn = max(1, round(min_sec * fps))
    i = 0
    while i < len(out):
        if out[i][1] > out[i][0]:
            i += 1
            continue
        if i + 1 < len(out):
            nx = out[i + 1]
            room = nx[1] - max(nx[0], out[i][0])
            if room > 2 * mn:
                nx[0] = max(nx[0], out[i][0]) + mn
                out[i][1] = nx[0]
                i += 1
            else:
                nx[0] = out[i][0]
                nx[2] = (out[i][2] + " " + nx[2]).strip()
                del out[i]
        else:
            out[i][1] = out[i][0] + mn
            i += 1
    return out


def write_srt(cards, path, fps=30):
    with open(path, "w", encoding="utf-8") as f:
        for i, (fs, fe, t) in enumerate(fix_order(cards, fps), 1):
            f.write(f"{i}\n{fmt(fs, fps)} --> {fmt(fe, fps)}\n{t}\n\n")
    return path


def apply_fixes(text, fixes):
    for a, b in fixes:
        text = re.sub(a, b, text) if any(ch in a for ch in "()[]\\^$") else text.replace(a, b)
    return text


# ---------------------------------------------------------------- 자막 줄 다듬기(에디트 subtitle_qc.tidy_cards 에서 옮김, 2026-10-09)
DEP_NOUNS = {"법", "것", "거", "수", "때", "줄", "게", "데", "적", "뿐", "만큼", "지", "듯", "척", "채"}


def _jong(ch):
    o = ord(ch) - 0xAC00
    return o % 28 if 0 <= o < 11172 else -1


def tidy_cards(final, words, cfg, fps):
    """사람이 보기 좋게 자막 줄을 다듬는다(2026-10-07 반영). 반환: 바꾼 내역 문장 목록.
    1) 마침표 빼기(설정 자막.마침표_빼기, 기본 켬) — 숫자 사이 점(1.5)은 그대로
    2) 다음 줄 맨 앞에 떨어진 의존 명사(법·것·수…)를 앞 줄 끝으로 — 경계는 그 낱말이 끝나는 시각
    3) 한 낱말(3글자 이하)만 덩그러니 있는 줄('어떤')은 다음 줄과 합침"""
    log = []
    hm = int((cfg.get("자막") or {}).get("한줄최대", 34))
    if (cfg.get("자막") or {}).get("마침표_빼기", True):
        for c in final:
            t2 = re.sub(r"(?<!\d)[.。](?!\d)", "", c["text"]).strip()
            if t2 != c["text"]:
                c["text"] = t2
    i = 0
    while i < len(final) - 1:
        a, b = final[i], final[i + 1]
        aw, bw = a["text"].split(), b["text"].split()
        if aw and len(bw) >= 2 and bw[0] in DEP_NOUNS and _jong(aw[-1][-1]) in (4, 8) and b["s"] - a["e"] < 1.0:
            w0 = bw[0]
            hit = next((w for w in words if abs(w["s"] - b["s"]) < 1.2 and capt.base_word(w["w"]) == w0), None)
            cut = hit["e"] if hit else b["s"] + (b["e"] - b["s"]) * len(w0) / max(1, len(b["text"]))
            a["text"] = a["text"] + " " + w0; b["text"] = " ".join(bw[1:])
            a["e"] = cut; a["fe"] = int(round(cut * fps)); b["s"] = cut; b["fs"] = a["fe"]
            log.append(f"'{w0}' 앞 줄로 옮김: {a['text']}")
        elif len(aw) == 1 and len(a["text"]) <= 3 and not capt.is_sentence_end(aw[0]) and b["s"] - a["e"] < 3.0                 and len(a["text"]) + 1 + len(b["text"]) <= hm:
            b["text"] = a["text"] + " " + b["text"]; b["s"] = a["s"]; b["fs"] = a["fs"]
            b["before"] = a.get("before", "") + " " + b.get("before", "")
            log.append(f"한 낱말 줄 합침: {b['text']}")
            del final[i]
            continue
        i += 1
    return log

