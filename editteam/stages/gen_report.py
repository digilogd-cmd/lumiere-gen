# -*- coding: utf-8 -*-
"""생성형 ⑬ 마무리 보고: 결과_요약.md(만든 것·길이·음량·브라우저 작업·대신한 것·확인 필요) + 완성/ 폴더(gen/deliver.collect_gen)."""
import os
from .. import brainstats
from ..core import jload, ts_long
from ..gates import all_gates
from ..gen import jobs as J
from ..gen.common import brief, sdir

LABEL = "마무리 보고"
VERSION = 1
DEPS = ["gen_thumbs"]


def inputs(P):
    return []


def run(P, d):
    b = brief(P)
    rd = lambda n, f, dflt=None: jload(os.path.join(sdir(P, n), f), dflt if dflt is not None else {})
    sc, fi, asm = rd("gen_script", "script.json"), rd("gen_final", "final_info.json"), rd("gen_assemble", "assemble.json")
    im, vd, vo, mu, al = rd("gen_images", "images.json"), rd("gen_video", "video.json"), rd("gen_voice", "voice.json"), rd("gen_music", "music.json"), rd("gen_align", "장면시각.json")
    th = rd("gen_thumbs", "thumbs.json")
    js = J.load(P)["jobs"]
    gates = all_gates(P)
    g_ok = sum(x["ok"] for _, it in gates for x in it); g_all = sum(len(it) for _, it in gates)
    g_bad = [(n, x) for n, it in gates for x in it if not x["ok"]]
    done = lambda k: [j for j in js if j["종류"] == k and j["상태"] == "완료"]
    real = lambda k: [j for j in done(k) if not str(j.get("메모", "")).startswith(("시험 파일", "임시 음성"))]
    L = [f"# {sc.get('title', P.name)} — 생성형 결과", "",
         f"- 의뢰: {'대본 파일 ' + os.path.basename(b['script_file']) if b.get('script_file') else '주제 ' + b['topic']} · {b['style']} · "
         f"{'세로 9:16' if b['vertical'] else '가로 16:9'} · 화자 {b['speakers']}명" + (" · **시험 모드(브라우저 대신 시험 파일)**" if b.get("fixtures") else ""),
         f"- 완성본: {ts_long(fi.get('dur', 0))} ({fi.get('dur', 0):.1f}초) · {fi.get('W')}x{fi.get('H')} · 소리 {fi.get('lufs')} LUFS / 피크 {fi.get('tp')} dBTP",
         f"- 대본 장면 {len(sc.get('scenes', []))}개 · 자막 {fi.get('cards')}줄 · 대본 글자 일치 {al.get('ratio', 0) * 100:.0f}%",
         f"- 컷 {asm.get('cuts')}개(그림 {len([x for x in im.get('images', []) if not x.get('sheet')])}장 · 영상 클립 {len([c for c in vd.get('clips', []) if c.get('file')])}개)"
         f" · 목소리 {vo.get('dur')}초 · 음악 {mu.get('source')}",
         f"- 브라우저 작업: 그림 {len(real('image'))} · 영상 {len(real('video'))} · 목소리 {len(real('voice'))} · 음악 {len(real('music'))} (실제 Flow·AI Studio에서 받은 것)",
         f"- 쓴 크레딧: 영상(Veo) {len(real('video'))}클립 · 음악 {len(real('music'))}곡",
         f"- {brainstats.line(P.dir)}",
         f"- 검문소: {g_ok}/{g_all} 통과" + (f" · 확인 필요 {len(g_bad)}개" if g_bad else ""), "",
         "## 결과 파일 (완성/ 폴더)", "- 1_완성본.mp4 · 1_자막.srt · 2_제목_후보.txt · 2_설명.txt · 3_썸네일_1~3.jpg · 5_콘티_스토리보드.jpg", "",
         "## 제목 후보"] + [f"{i + 1}. {t}" for i, t in enumerate(th.get("titles", []))] + ["", "## 대신한 것·임시로 둔 것"]
    alt = [f"- 샷 {s['shot']} 그림 → {s['from']} 그림으로 대신({s.get('why', '')})" for s in im.get("substituted", [])]
    alt += [f"- 샷 {c['shot']} 영상 클립 없음 → 그림 + 켄 번즈({c.get('why', '')})" for c in vd.get("clips", []) if not c.get("file")]
    alt += [f"- 목소리 {x} — 임시 음성(윈도우 Heami). AI Studio 음성으로 바꾸려면 그 작업을 다시 하고 run" for x in vo.get("temporary", [])]
    if mu.get("source") and mu["source"] != "Flow Music":
        alt.append(f"- 배경음악 — {mu['source']}")
    L += alt or ["- 없음"]
    L += ["", "## 검문소에서 걸린 것"] + ([f"- [{n}] {x['rule']}: {x['measured']} (기준 {x['target']})" for n, x in g_bad] or ["- 없음"])
    L += ["", "## 업로드", "뤼미에르는 자동으로 올리지 않아요. `완성/` 폴더의 파일을 직접 올려 주세요. 유튜브에 올릴 때 'AI로 만든 콘텐츠' 항목을 체크해 주세요."]
    path = P.p("결과_요약.md")
    open(path, "w", encoding="utf-8").write("\n".join(L) + "\n")
    P.ev.output("report", P.rel(path), "결과 요약")
    return {"gate_fail": len(g_bad)}
