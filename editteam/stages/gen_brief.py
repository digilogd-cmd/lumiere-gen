# -*- coding: utf-8 -*-
"""생성형 ① 의뢰서: run --gen 으로 받은 주제·대본 파일·길이·화풍·화자 수·가로/세로를 brief.json 으로.
대본 파일은 txt·md·docx·hwp·hwpx(materials.read_text 재사용)."""
import os
from ..core import StageError, jdump
from ..gates import Gate
from ..gen.common import gcfg, size_of

LABEL = "의뢰서"
VERSION = 1
DEPS = []


def inputs(P):
    """대본 파일은 경로가 아니라 내용으로 알아본다 — 폴더를 옮겨도(2026-10-09 젠 분리 때처럼) 처음부터 다시 돌지 않게."""
    import hashlib
    g = dict(P.meta.get("gen") or {})
    sp = g.get("script_path")
    sig = hashlib.sha1(open(sp, "rb").read()).hexdigest()[:16] if sp and os.path.exists(sp) else None
    g.pop("script_path", None)
    g.pop("fixtures", None)          # 시험 파일 폴더 경로도 위치가 아니라 '시험 모드인지'만
    return [g, sig, bool((P.meta.get("gen") or {}).get("fixtures"))]


def run(P, d):
    g = dict(P.meta.get("gen") or {})
    G0 = gcfg(P.cfg)
    script = ""
    sp = g.get("script_path")
    if sp:
        if not os.path.exists(sp):
            raise StageError(f"대본 파일이 없습니다: {sp}")
        from ..materials import read_text
        script = read_text(sp).strip()
        if sp.lower().endswith(".md"):          # 마크다운 제목·인용 표시는 읽을 말이 아님
            import re
            lines = [l for l in script.splitlines() if not l.lstrip().startswith(("#", "<!--", "---"))]
            script = "\n".join(re.sub(r"^\s*[>*-]\s*", "", l) for l in lines).strip()
    vertical = bool(g.get("vertical"))
    W, H = size_of(vertical)
    b = {"topic": (g.get("topic") or "").strip(), "script": script, "script_file": sp or "",
         "length": float(g.get("length") or G0["목표_초"]), "style": (g.get("style") or G0["화풍"]).strip(),
         "speakers": int(g.get("speakers") or 1), "vertical": vertical, "aspect": "9:16" if vertical else "16:9", "W": W, "H": H,
         "fixtures": g.get("fixtures") or ""}
    jdump(b, os.path.join(d, "brief.json"))
    P.ev.log(f"의뢰서: {'대본 ' + str(len(script)) + '자' if script else '주제 ' + b['topic']} · {b['length']:.0f}초 · {b['style']} · "
             f"화자 {b['speakers']}명 · {'세로 9:16' if vertical else '가로 16:9'}" + (" · 시험 모드(시험 파일로 브라우저 작업 대신)" if b["fixtures"] else ""))
    G = Gate(P, "gen_brief", d)
    G.check("주제나 대본 중 하나", bool(b["topic"] or script), "주제 있음" if b["topic"] else ("대본 있음" if script else "둘 다 없음"), "하나 이상")
    G.check("화자 수 1~4", 1 <= b["speakers"] <= 4, b["speakers"], "1~4")
    G.check("길이 20~600초", 20 <= b["length"] <= 600, f"{b['length']:.0f}초", "20~600초", hard=False)
    G.finish()
    return {"chars": len(script), "length": b["length"], "vertical": vertical}
