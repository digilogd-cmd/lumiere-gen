# -*- coding: utf-8 -*-
"""LUMIÈRE 디자인 고르기 — 컬러 팔레트 A~E(자막·모션그래픽), 썸네일 포인트 색 7가지, 자막 글꼴 4가지.
대시보드 [설정]에서 그림을 보고 고른다(미리보기: dashboard/design/*.jpg, design_preview.py 로 실제 엔진이 그림).
글꼴은 모두 무료·상업 이용 가능(OFL)이라 kits/fonts 에 같이 넣는다(라이선스 원문 OFL_*.txt).
'팬톤' 이름·색 번호는 상표·라이선스 문제로 쓰지 않는다(2026-10-07)."""
import os
from .core import ROOT, hash_of

KIT_FONTS = os.path.join(ROOT, "kits", "fonts")

# accent=강조(제목바 선·숫자·포인트), accent2=보조, ink=자막 글자, box=자막 상자, box_a=상자 진하기(ASS 알파 00=불투명~FF=투명),
# card=모션 카드 바탕, sub=카드 보조 글자, motion=모션 종류별 색(기존 config 모션.* 자리)
PALETTES = {
    "A": dict(name="시그니처 앰버", desc="어두운 방·화면 녹화·IT 튜토리얼 (지금까지의 기본)",
              accent="#ffc629", accent2="#ff2d2d", ink="#ffffff", box="#090909", box_a=0x6F, card="#0c0e14", sub="#c9ced8",
              motion=dict(빨강="#ff2d2d", 노랑="#ffc629", 파랑="#4f8cff", 초록="#22c55e", 주황="#ff8a3d")),
    "B": dict(name="쿨 테크 블루", desc="흰 화면·문서가 많은 영상·비즈니스",
              accent="#36d6e7", accent2="#2f7bff", ink="#ffffff", box="#0b1426", box_a=0x40, card="#0b1426", sub="#b9c8de",
              motion=dict(빨강="#ff4d6d", 노랑="#36d6e7", 파랑="#2f7bff", 초록="#2ee6a6", 주황="#7aa7ff")),
    "C": dict(name="웜 테라코타", desc="따뜻한 조명·뷰티·요리·라이프",
              accent="#e07a5f", accent2="#f2c38b", ink="#fff6ea", box="#2a1e17", box_a=0x48, card="#2a1e17", sub="#e9d6bf",
              motion=dict(빨강="#d9534f", 노랑="#f2c38b", 파랑="#81b29a", 초록="#a3c585", 주황="#e07a5f")),
    "D": dict(name="비비드 팝", desc="쇼츠·예능·게임·엔터",
              accent="#ff3ea5", accent2="#c6f432", ink="#ffffff", box="#14001f", box_a=0x40, card="#14001f", sub="#d9c8ef",
              motion=dict(빨강="#ff3e6c", 노랑="#c6f432", 파랑="#7b61ff", 초록="#3ef0a0", 주황="#ff3ea5")),
    "E": dict(name="모노 시네마", desc="인터뷰·다큐·브랜드·고급스러운 톤",
              accent="#e63946", accent2="#d9d9d9", ink="#ffffff", box="#000000", box_a=0x50, card="#0d0d0d", sub="#a8a8a8",
              motion=dict(빨강="#e63946", 노랑="#f1f1f1", 파랑="#bfbfbf", 초록="#e63946", 주황="#f1f1f1")),
}

THUMB_COLORS = {
    "red":    ("레드", "#eb2828", "기본 — 가장 강한 주목"),
    "yellow": ("옐로", "#ffd400", "어두운 사진에서 가장 잘 보임"),
    "orange": ("오렌지", "#ff7a00", "따뜻하고 활기찬"),
    "lime":   ("라임", "#b8f400", "테크·게임·새로움"),
    "cyan":   ("시안", "#00d1ff", "IT·차분한 신뢰감"),
    "pink":   ("핫핑크", "#ff3ea5", "뷰티·엔터·젊은 톤"),
    "violet": ("바이올렛", "#a66bff", "AI·미래·몽환적"),
}

# 자막 글꼴: file, family(ASS), bold(ASS Bold), fs(libass 크기), pil(PIL 크기), ink_k — calibrate()가 글자 높이 38px에 맞춘 값
FONTS = {
    "barun":   dict(name="나눔바른고딕", desc="다빈치 기본 스타일 — 단정하고 잘 읽힘", file="NanumBarunGothicBold.ttf",
                    family="NanumBarunGothic", bold=1, fs=48, pil=43, ink_k=0.975),
    "pretend": dict(name="프리텐다드", desc="모던·깔끔 — 요즘 앱 같은 느낌", file="Pretendard-Bold.otf",
                    family="Pretendard", bold=1, fs=48, pil=43, ink_k=0.975),
    "blackhan": dict(name="검은고딕", desc="굵고 강렬 — 예능·쇼츠", file="BlackHanSans-Regular.ttf",
                     family="Black Han Sans", bold=0, fs=48, pil=43, ink_k=0.975),
    "jua":     dict(name="주아", desc="둥글고 귀여움 — 브이로그·일상", file="Jua-Regular.ttf",
                    family="Jua", bold=0, fs=48, pil=43, ink_k=0.975),
}
FONT_METRICS = os.path.join(KIT_FONTS, "_자막글꼴_보정.json")   # calibrate() 결과(있으면 위 fs/pil/ink_k를 덮어씀)


def calibrate():
    """글꼴마다 libass 실제 렌더로 한글 글자 높이 38px(다빈치 실측)에 맞는 fs, 박스 폭 계산용 pil·ink_k를 구해 저장."""
    import json, subprocess, tempfile
    import numpy as np
    from PIL import Image, ImageFont
    txt = "한글자막높이맞추기시험문장입니다"
    out = {}
    tmp = tempfile.mkdtemp()
    fdir = KIT_FONTS.replace(chr(92), "/").replace(":", chr(92) + ":")

    def ink(fid, fs):
        f = FONTS[fid]
        ass = os.path.join(tmp, "c.ass")
        lines = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080", "", "[V4+ Styles]",
                 "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
                 f"Style: T,{f['family']},{fs},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,{f['bold']},0,0,0,100,100,0,0,1,0,0,5,0,0,0,1", "",
                 "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
                 "Dialogue: 0,0:00:00.00,0:00:05.00,T,,0,0,0,,{" + chr(92) + "pos(960,540)}" + txt, ""]
        open(ass, "w", encoding="utf-8").write(chr(10).join(lines))
        png = os.path.join(tmp, "c.png")
        a = ass.replace(chr(92), "/").replace(":", chr(92) + ":")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=1920x1080:d=1", "-vf",
                        f"ass='{a}':fontsdir='{fdir}'", "-frames:v", "1", png], check=True)
        m = np.asarray(Image.open(png).convert("L")) > 100
        ys, xs = np.where(m)
        return ys.max() - ys.min() + 1, xs.max() - xs.min() + 1

    for fid, f in FONTS.items():
        h, _ = ink(fid, 48)
        fs = round(48 * 38 / h)
        h2, w2 = ink(fid, fs)
        pf = os.path.join(KIT_FONTS, f["file"])
        best = None
        for px in range(30, 70):
            F = ImageFont.truetype(pf, px)
            bb = F.getbbox(txt)
            if best is None or abs((bb[3] - bb[1]) - h2 * 43 / 38) < abs(best[1] - h2 * 43 / 38):
                best = (px, bb[3] - bb[1])
        pil = best[0]
        ink_k = round(w2 / ImageFont.truetype(pf, pil).getlength(txt), 4)
        out[fid] = {"fs": fs, "pil": pil, "ink_k": float(ink_k), "measured_h": int(h2), "measured_w": int(w2)}
    # 나눔바른고딕은 다빈치 실제 영상에서 잰 값(fs48·pil43·ink_k .975)이 기준 — 다른 글꼴은 이 기준에 대한 비율로 맞춘다
    b = dict(out["barun"])
    for fid, o in out.items():
        o["fs"] = int(round(48 * o["fs"] / b["fs"]))
        o["pil"] = int(round(43 * o["pil"] / b["pil"]))
        o["ink_k"] = round(0.975 * o["ink_k"] / b["ink_k"], 4)
    json.dump(out, open(FONT_METRICS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return out


def _d(cfg):
    return cfg.get("디자인") or {}


def palette_id(cfg):
    p = str(_d(cfg).get("팔레트") or "A").upper()
    return p if p in PALETTES else "A"


def palette(cfg):
    return PALETTES[palette_id(cfg)]


def thumb_color_id(cfg):
    c = (cfg.get("썸네일") or {}).get("포인트색") or "red"
    return c if c in THUMB_COLORS else "red"


def thumb_rgb(cfg):
    h = THUMB_COLORS[thumb_color_id(cfg)][1]
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def set_thumb_color(cfg):
    """썸네일 그리는 모듈(thumb_v3)의 포인트 색을 설정값으로. 썸네일 단계 시작 때 부른다."""
    import thumb_v3
    thumb_v3.RED = thumb_rgb(cfg)
    return thumb_v3.RED


def font_id(cfg):
    f = (cfg.get("자막") or {}).get("글꼴") or "barun"
    return f if f in FONTS else "barun"


def font(cfg_or_id):
    fid = cfg_or_id if isinstance(cfg_or_id, str) else font_id(cfg_or_id)
    f = dict(FONTS[fid])
    try:
        import json
        f.update(json.load(open(FONT_METRICS, encoding="utf-8")).get(fid, {}))
    except (OSError, ValueError):
        pass
    f["path"] = os.path.join(KIT_FONTS, f["file"])
    return f


def apply(cfg):
    """팔레트 색을 config 모션.* 에 넣는다(기존 accent() 코드가 그대로 쓰도록). load_config가 부른다."""
    cfg.setdefault("모션", {}).update(palette(cfg)["motion"])
    return cfg


def kit_vars(cfg):
    """HyperFrames 키트(모션·REPORT·타이틀)에 넘길 팔레트 변수."""
    p = palette(cfg)
    m = p["motion"]
    return {"pal_accent": p["accent"], "pal_accent2": p["accent2"], "pal_ink": p["ink"], "pal_card": p["card"], "pal_muted": p["sub"],
            "pal_c1": m["파랑"], "pal_c2": m["주황"], "pal_c3": m["빨강"]}


def sig(cfg):
    return hash_of(palette_id(cfg), font_id(cfg), thumb_color_id(cfg), PALETTES[palette_id(cfg)])[:8]


# ---------------------------------------------------------------- 읽기 쉬운지(검문소)
def _lum(hexc):
    r, g, b = (int(hexc.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def blend(fg_hex, alpha, bg_rgb):
    """상자 색(fg, 불투명도 alpha 0~1)이 배경 bg_rgb 위에 깔렸을 때 실제 색."""
    f = [int(fg_hex.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{int(round(alpha * a + (1 - alpha) * b)):02x}" for a, b in zip(f, bg_rgb))


def box_opacity(p):
    return 1 - p["box_a"] / 255
