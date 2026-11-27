# -*- coding: utf-8 -*-
"""생성형 ⑪ 종편: 자막(ASS — 설정의 글꼴·팔레트, 편집형과 같은 다빈치 스타일 상자) + 맨 앞 제목 + 음량 2-pass(-11 LUFS, 피크 ≤ -1).
산출: final.mp4, final.srt, final_info.json, 종편_프레임_확인.jpg"""
import os, subprocess
from .. import design, subs
from ..core import StageError, jdump, jload, probe_video, safe_replace
from ..gates import Gate
from ..gen.common import brief, sdir
from ..finishing import frame_sheet, loudnorm_2pass, measure_loud

LABEL = "종편"
VERSION = 1
DEPS = ["gen_assemble"]
FPS = 30


def inputs(P):
    return [P.cfg["자막"], design.sig(P.cfg), P.cfg["종편"].get("음량_LUFS", -11)]


def build_ass(P, cards, title, W, H, T):
    import srt2ass_davinci as SA
    from PIL import ImageFont
    keep = (SA.W, SA.H, SA.BOX_TOP)
    _f, _p = design.font(P.cfg), design.palette(P.cfg)
    SA.configure(font_file=_f["path"], family=_f["family"], bold=_f["bold"], fs=_f["fs"], pil=_f["pil"], ink_k=_f["ink_k"],
                 ink=_p["ink"], box=_p["box"], box_a=_p["box_a"])
    if SA.FONT is None:
        SA.FONT = ImageFont.truetype(_f["path"], SA.PIL_PX)
    try:
        SA.W, SA.H = W, H
        SA.BOX_TOP = int(H * 0.78) if H > W else keep[2]       # 세로: 아래 22% 위(쇼츠 버튼 피하기)
        head = SA.head()
        ev = SA.events([(c["s"], c["e"], c["text"]) for c in cards])
    finally:
        SA.W, SA.H, SA.BOX_TOP = keep
    fs = 66 if W > H else 70
    acc = _p["accent"].lstrip("#")
    col = "&H00" + acc[4:6] + acc[2:4] + acc[0:2]
    style = (f"Style: Title,{_f['family']},{fs},&H00FFFFFF,&H00FFFFFF,&H00141414,&H64000000,1,0,0,0,100,100,0,0,1,4,2,8,60,60,"
             f"{int(H * (0.08 if W > H else 0.16))},1")
    head = head.replace("\n\n[Events]", "\n" + style + "\n\n[Events]")
    if title:
        ev.append(f"Dialogue: 2,{SA.a(0.5)},{SA.a(min(4.2, T - 0.5))},Title,,0,0,0,,{{\\fad(400,500)\\3c{col}&}}{title}")
    return head + "\n".join(ev) + "\n", SA.fontsdir_filter()


def run(P, d):
    b = brief(P)
    W, H = b["W"], b["H"]
    ad = sdir(P, "gen_assemble")
    asm = jload(os.path.join(ad, "assemble.json"))
    T, lead = asm["T"], asm["lead"]
    cards = [dict(c, s=c["s"] + lead, e=c["e"] + lead) for c in jload(os.path.join(sdir(P, "gen_align"), "cards.json"))]
    from ..gen.plan import script
    title = script(P)["title"]
    srt = os.path.join(d, "final.srt")
    subs.write_srt([(int(c["s"] * FPS), max(int(c["s"] * FPS) + 1, int(round(c["e"] * FPS))), c["text"]) for c in cards], srt, FPS)
    ass, fdir = build_ass(P, cards, title, W, H, T)
    open(os.path.join(d, "final.ass"), "w", encoding="utf-8").write(ass)
    P.ev.progress(10, "음량 맞추기(2-pass)")
    m4a = os.path.join(d, "final_audio.m4a")
    target = float(P.cfg["종편"].get("음량_LUFS", -11))
    loudnorm_2pass(os.path.join(ad, "mix.wav"), m4a, target)
    P.ev.progress(40, "자막 입혀 렌더")
    out = os.path.join(d, "final.mp4")
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(ad, "assembled.mp4"), "-i", m4a,
                        "-filter_complex", f"[0:v]ass=final.ass{fdir},format=yuv420p[v]", "-map", "[v]", "-map", "1:a",
                        "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-c:a", "copy", "-t", f"{T:.3f}", "-r", str(FPS),
                        "-movflags", "+faststart", "final.part.mp4"], cwd=d, capture_output=True)
    if r.returncode != 0:
        raise StageError("종편 렌더 실패: " + r.stderr.decode("utf-8", "replace")[-400:])
    out = safe_replace(os.path.join(d, "final.part.mp4"), out, alt_ok=True)
    lufs, tp = measure_loud(out)
    from ..core import probe_duration
    dur = probe_duration(out)
    w, h, _ = probe_video(out)
    cuts = jload(os.path.join(ad, "cuts.json"), [])
    times = [0.6, T * 0.25, T * 0.5, T * 0.75, T - 1.2] + [(c["s"] + c["e"]) / 2 for c in cuts if c["kind"] == "video"]
    sheet = frame_sheet(out, d, sorted(times))
    if sheet:
        P.ev.preview("final_sheet", P.rel(sheet), "종편 실제 프레임(처음·중간·끝·영상 클립)")
    jdump({"out": out, "dur": dur, "lufs": lufs, "tp": tp, "W": w, "H": h, "title": title, "cards": len(cards), "lead": lead},
          os.path.join(d, "final_info.json"))
    P.ev.output("final", P.rel(out), f"{dur:.1f}초 · {lufs} LUFS")
    G = Gate(P, "gen_final", d)
    G.check("음량(통합 LUFS)", lufs is not None and abs(lufs - target) <= 0.5, f"{lufs}", f"{target}±0.5", "11-2")
    G.check("최대 피크(dBTP)", tp is not None and tp <= -1.0, f"{tp}", "≤ -1.0", "11-2")
    G.check("화면 크기", (w, h) == (W, H), f"{w}x{h}", f"{W}x{H}")
    G.check("길이(대본 목표 ±25%)", abs(dur - b["length"]) <= b["length"] * 0.25 or bool(b.get("script")), f"{dur:.0f}초",
            f"{b['length']:.0f}초 ±25%", hard=False)
    G.finish()
    return {"dur": round(dur, 2), "lufs": lufs, "tp": tp}
