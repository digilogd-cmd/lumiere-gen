# -*- coding: utf-8 -*-
"""Flow·AI Studio에 넣을 최종 문장 조립(두뇌 답 -> 프롬프트). 규칙은 코드로 고정한다:
- 모든 그림 프롬프트 맨 앞 = 스타일 머리말(화풍 고정)            (스킬 3원칙 3, 지침서 §6)
- 인물은 레퍼런스 + 겉모습 구조를 못박고 금지어(마르게·노숙자처럼 변하는 것 방지)   (지침서 §6 ★)
- 인원수 못박기, 글자 나올 소재엔 NO writing, '흰 배경' 금지, 줄바꿈 없는 한 문단        (지침서 §6)"""
import re

NO_TEXT = "NO writing, no letters, no words, no signs with text, no captions."
KEEP_FACE = "Keep faces recognizably identical to the reference images; appearance changes only by expression, NOT thinner, NOT older, NOT a different person."
KEEP_ANIMAL = ("Keep each animal recognizably identical to the reference images — same breed, coat color, ear shape and markings; "
               "NOT a different breed, NOT a different animal.")


def kind(ch):
    """인물 종류(영어 명사). 사람이면 'person', 동물이면 'golden retriever dog' 같은 것(두뇌 board.characters[].kind, 2026-10-18 — 없으면 사람)."""
    k = (ch.get("kind") or "").strip()
    return k if k and k.lower() not in ("person", "human", "man", "woman") else "person"


def one_line(s):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s.replace("white background", "plain warm paper background")


def frame_word(aspect):
    return "tall 9:16 vertical framing with the subject centered" if aspect == "9:16" else "wide 16:9 cinematic framing"


def sheet_prompt(board, ch, aspect):
    k = kind(ch)
    if k == "person":
        return one_line(f"{board['style_header']} Character design sheet of one person, {ch['key']}: {ch['look']}. "
                        f"Two views side by side on a plain warm beige paper background: a full-body front view and a head-and-shoulders "
                        f"three-quarter view, calm neutral face with relaxed eyebrows and closed mouth, soft even daylight. "
                        f"Only this one person. {NO_TEXT} {frame_word(aspect)}.")
    return one_line(f"{board['style_header']} Character design sheet of one {k}, {ch['key']}: {ch['look']}. "
                    f"Two views side by side on a plain warm beige paper background: a full-body side view standing on four legs and a head "
                    f"three-quarter view, calm relaxed expression, soft even daylight. "
                    f"Only this one {k}, no people. {NO_TEXT} {frame_word(aspect)}.")


def shot_prompt(board, shot, aspect):
    chars = {c["key"]: c for c in board.get("characters", [])}
    refs = [chars[k] for k in shot.get("chars", []) if k in chars]
    parts = [board["style_header"]]
    if refs:
        keep = " ".join(x for x in (KEEP_ANIMAL if any(kind(c) != "person" for c in refs) else "",
                                    KEEP_FACE if any(kind(c) == "person" for c in refs) else "") if x)
        parts.append("Use the attached reference images for character design: " +
                     " ".join(f"Image {i + 1} is {c['key']}, {c['look']}." for i, c in enumerate(refs)) + " " + keep)
    parts.append("Scene: " + shot["scene_desc"].rstrip(".") + ".")
    if shot.get("emotion"):
        parts.append(shot["emotion"].rstrip(".") + ".")
    n = int(shot.get("people") or len(refs))
    if refs and any(kind(c) != "person" for c in refs):     # 동물이 주인공인 샷 — 'person/people' 대신 실제 이름으로 수를 못박음
        names = [kind(c) for c in refs]
        parts.append(f"Exactly these {len(refs)} characters in the frame: " + ", ".join(f"{c['key']} ({names[i]})" for i, c in enumerate(refs)) + ". "
                     + ("No people in the frame." if not any(x == "person" for x in names) else ""))
        n = None
    if n is None:
        pass
    elif n <= 0:
        parts.append("No people in the frame.")
    elif refs and n == len(refs):
        parts.append("Only this one person in the frame." if n == 1 else f"Only these {n} people in the frame.")
    else:
        parts.append(f"Exactly {n} {'person' if n == 1 else 'people'} in the frame.")
    parts.append(shot["camera"].rstrip(".") + ".")
    parts.append(shot["lighting"].rstrip(".") + ".")
    if shot.get("no_text", True):
        parts.append(NO_TEXT)
    parts.append(frame_word(aspect) + ".")
    return one_line(" ".join(parts))


def video_prompt(board, shot):
    return one_line(f"{shot['motion'].rstrip('.')}. Keep the exact art style, colors and character designs of the first frame; "
                    f"faces stay identical. Gentle natural motion, no sudden cuts, no morphing. {NO_TEXT} No camera shake.")


def voice_text(scenes, speakers):
    """AI Studio Text 모드에 그대로 붙여 넣을 글: 'Speaker 1: 대사' 줄(장면 사이 빈 줄 없음 — 빈 줄은 Composer가 블록을 나눔)."""
    out = []
    for s in scenes:
        for l in s["lines"]:
            out.append(f"Speaker {int(l['speaker'])}: {l['text'].strip()}")
    return "\n".join(out)
