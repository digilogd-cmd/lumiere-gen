# -*- coding: utf-8 -*-
"""아트고메 채널 공식 썸네일 템플릿 (2026-09-23 확정).
기준 레퍼런스: 채널 자체 히트작 'AI가 거짓말했다'(sanjA0cHWgA) + 에포크한남 채널의 통일된 워드마크.
- 사진은 흐리지 않고 또렷하게, 화면 55~60%를 채운다(블러/글로우 배경 폐기).
- 오른쪽은 완전 블랙 패널, 텍스트는 흰색 + 레드 포인트 1곳만(다른 색 난립 금지).
- 모든 영상에 같은 위치/스타일의 브랜드 워드마크(아트고메)를 고정으로 넣어 시리즈 통일감을 만든다.
- 컬러 배지(노랑/초록 등)는 영상마다 색이 달라져 통일성을 해치므로 여기서는 쓰지 않는다.
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(os.path.dirname(os.path.dirname(HERE)), "kits", "fonts")   # LUMIERE_GEN/kits/fonts (OFL 글꼴)
BLACK_HAN = os.path.join(FONTS, "BlackHanSans-Regular.ttf")
PRETENDARD_BLACK = os.path.join(FONTS, "Pretendard-Black.otf")
W, H = 1280, 720
INK = (8, 8, 9)
WHITE = (250, 250, 252)
RED = (235, 40, 40)


def desaturate(im, factor=0.45, darken=0.12):
    """채도를 낮추고 살짝 어둡게 해서 고급스러운 톤으로(쨍한 원색 사진 보정용)."""
    from PIL import ImageEnhance
    rgb = im.convert("RGB")
    rgb = ImageEnhance.Color(rgb).enhance(factor)
    if darken:
        rgb = ImageEnhance.Brightness(rgb).enhance(1 - darken)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.06)
    return rgb


def cover(im, w, h, fx=0.5, fy=0.5):
    s = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    l = int((im.width - w) * fx)
    t = int((im.height - h) * fy)
    return im.crop((l, t, l + w, t + h))


def base(photo, split=0.58, fx=0.5, fy=0.4, darken=0.20, feather=300, desat=0.62, side="right"):
    """사진(또렷, 채도 낮춤) 한쪽 + 나머지 완전 블랙, 경계는 넓고 부드러운(ease) 그라데이션으로.
    side='right'(기본, 2026-09-23 확정 — 타이틀 왼쪽/사진 오른쪽 통일) 또는 'left'.
    feather를 짧게 주면(예전 90px) 사진이 '툭' 끊긴 느낌이 나서 기본값을 크게 올렸다."""
    im = Image.new("RGBA", (W, H), (*INK, 255))
    if desat:
        photo = desaturate(photo, factor=1 - desat)

    if side == "left":
        split_x = int(W * split)
        photo_w = min(W, split_x + feather)
        p = cover(photo, photo_w, H, fx, fy).convert("RGBA")
        if darken:
            p = Image.alpha_composite(p, Image.new("RGBA", p.size, (0, 0, 0, int(255 * darken))))
        mask = Image.new("L", p.size, 255)
        md = ImageDraw.Draw(mask)
        fade_w = photo_w - split_x
        for i in range(fade_w):
            t = i / fade_w
            eased = 1 - (t * t * (3 - 2 * t))
            md.line([(split_x + i, 0), (split_x + i, H)], fill=int(255 * eased))
        if photo_w < p.width:
            md.rectangle([photo_w, 0, p.width, H], fill=0)
        im.paste(p, (0, 0), mask)
    else:
        black_w = int(W * split)
        photo_x0 = max(0, black_w - feather)
        photo_w = W - photo_x0
        p = cover(photo, photo_w, H, fx, fy).convert("RGBA")
        if darken:
            p = Image.alpha_composite(p, Image.new("RGBA", p.size, (0, 0, 0, int(255 * darken))))
        mask = Image.new("L", p.size, 255)
        md = ImageDraw.Draw(mask)
        fade_w = black_w - photo_x0
        for i in range(fade_w):
            t = i / fade_w
            eased = t * t * (3 - 2 * t)  # 0(검정쪽) -> 1(사진쪽) 부드러운 커브
            md.line([(i, 0), (i, H)], fill=int(255 * eased))
        im.paste(p, (photo_x0, 0), mask)
    return im


def logo_mark(im, logo_path, corner="bl", margin=34, height=77):
    """개발팀이 준 실제 로고 PNG(검정 배경+흰색 심볼)를 알파 마스크로 바꿔서 합성한다.
    좌우 여백을 먼저 잘라내고(content bbox) 높이 기준으로 리사이즈."""
    src = Image.open(logo_path).convert("L")
    bbox = src.point(lambda p: 255 if p > 24 else 0).getbbox()
    src = src.crop(bbox) if bbox else src
    w = int(src.width * height / src.height)
    alpha = src.resize((w, height), Image.LANCZOS)
    white = Image.new("RGBA", alpha.size, (255, 255, 255, 0))
    white.putalpha(alpha)
    x = margin if corner == "bl" else W - margin - w
    y = H - margin - height
    im.alpha_composite(white, (x, y))


TRACKING = 0.94  # 2026-09-23: 자간 기본 축소 — 0.8은 한글이 겹쳐서 0.94로 재조정


def impact_text(im, xy, text, size, fill, outline=(0, 0, 0), outline_w=None, font=BLACK_HAN, anchor="la", tracking=TRACKING, ss=1):
    """2026-09-25 세 차례 근본 원인을 파고든 끝에 확정된 버전(개발팀이 "더하면"이 "더히면"처럼 보인다고
    지적한 걸 계기로 발견).
    1차: "렌더링 순서(자간 겹침)" 문제라고 생각해서 outline-먼저/fill-나중 두 번에 나눠 그리는 방식으로
    고쳤는데도 "하"의 삐침이 계속 사라짐.
    2차: 진짜 원인은 **사방으로 글자를 복제해서 찍는 "외곽선(스트로크)" 방식 자체가, 삐침처럼 원래
    획에 아주 가깝게 붙은 가는 요소를 다른 방향 복제본과 뭉개버린다**는 것 — PIL 기본
    `stroke_width`(심지어 1px)로도, 크기를 140까지 키워도 똑같이 재현됨을 직접 확인했다. 그래서
    사방 스탬프 대신 **단일 방향 드롭섀도우**(옛 SOP의 glow_text 방식과 동일)로 바꿨다 — 사방 확장이
    아니라 단순 평행이동이라 획 사이 좁은 틈을 메우지 않는다.
    3차: "혹시 모르니" 붙여뒀던 `ss`배 슈퍼샘플링+LANCZOS 축소가 **오히려** 그 가는 삐침을 그림자와
    겹쳐 뭉갠다는 걸 뒤늦게 발견해서 기본값을 다시 `ss=1`(슈퍼샘플링 없음)로 되돌렸다 — 애초에
    근본 원인이 아니었던 걸 붙였다가 새로운 문제를 만든 사례라 기록해 둔다."""
    f = ImageFont.truetype(font, size * ss)
    shadow_off = (round(size * 0.05) or 1) * ss
    probe = ImageDraw.Draw(Image.new("RGBA", (4, 4)))

    if tracking == 1.0 or anchor != "la":
        bbox = probe.textbbox((0, 0), text, font=f, anchor=anchor)
    else:
        cx = 0.0
        for ch in text[:-1]:
            cx += probe.textlength(ch, font=f) * tracking
        cx += probe.textlength(text[-1], font=f)
        asc, desc = f.getmetrics()
        bbox = (0, 0, cx, asc + desc)

    pad = shadow_off * 2 + 8
    w_big = int(bbox[2] - bbox[0]) + pad * 2
    h_big = int(bbox[3] - bbox[1]) + pad * 2
    layer = Image.new("RGBA", (w_big, h_big), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ox, oy = pad - bbox[0], pad - bbox[1]

    if tracking == 1.0 or anchor != "la":
        ld.text((ox + shadow_off, oy + shadow_off), text, font=f, fill=outline, anchor=anchor)
        ld.text((ox, oy), text, font=f, fill=fill, anchor=anchor)
    else:
        positions, cx = [], ox
        for ch in text:
            positions.append((ch, cx))
            cx += ld.textlength(ch, font=f) * tracking
        for ch, px in positions:
            ld.text((px + shadow_off, oy + shadow_off), ch, font=f, fill=outline, anchor=anchor)
        for ch, px in positions:
            ld.text((px, oy), ch, font=f, fill=fill, anchor=anchor)

    small = layer.resize((max(1, w_big // ss), max(1, h_big // ss)), Image.LANCZOS)
    paste_x = int(round(xy[0] - pad / ss))
    paste_y = int(round(xy[1] - pad / ss))
    if im.mode != "RGBA":
        im.putalpha(255) if im.mode == "RGB" else None
    im.alpha_composite(small, (paste_x, paste_y))
    return (paste_x, paste_y, paste_x + small.width, paste_y + small.height)


def fit_size(text, max_w, start=240, min_size=40, font=BLACK_HAN, tracking=TRACKING):
    im = Image.new("RGB", (10, 10))
    d = ImageDraw.Draw(im)
    size = start
    while size > min_size:
        f = ImageFont.truetype(font, size)
        w = sum(d.textlength(ch, font=f) for ch in text[:-1]) * tracking + d.textlength(text[-1], font=f)
        if w <= max_w:
            return size
        size -= 2
    return min_size


def stacked_lines(im, x, y_start, lines, gap_ratio=1.12, outline=(0, 0, 0), font=BLACK_HAN):
    y = y_start
    for text, size, fill in lines:
        f = ImageFont.truetype(font, size)
        ascent, descent = f.getmetrics()
        impact_text(im, (x, y), text, size, fill=fill, outline=outline, font=font)
        y += int((ascent + descent) * gap_ratio)
    return y


def brand_mark(im, corner="bl", margin=34, text="", size=27, color=(235, 235, 238)):
    """로고 그림이 없을 때 썸네일 구석에 넣는 채널 이름 글자(워드마크). 이름이 비면 아무것도 안 그린다."""
    if not text:
        return
    f = ImageFont.truetype(PRETENDARD_BLACK, size)
    d = ImageDraw.Draw(im)
    bb = d.textbbox((0, 0), text, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    if corner == "bl":
        x, y = margin, H - margin - th
    else:
        x, y = W - margin - tw, H - margin - th
    # 점 하나 + 대문자풍 워드마크로 로고 느낌만 살짝
    d.ellipse([x - 16, y + th / 2 - 4, x - 8, y + th / 2 + 4], fill=RED)
    d.text((x, y - bb[1]), text, font=f, fill=color)
