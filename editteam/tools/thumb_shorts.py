# -*- coding: utf-8 -*-
"""아트고메 쇼츠(세로 9:16) 공식 썸네일 템플릿 (2026-09-23 도입, 2026-09-24 최종 확정).
가로형(thumb_v3)과 같은 규칙: 사진 또렷하게(채도 낮춤) + 화이트/레드 Black Han Sans 타이틀 + 고정 로고.
세로는 화면이 좁아서 좌/우 분할 대신 사진을 풀블리드로 꽉 채우고, 화면 위쪽에 그라데이션을 깔아
가로형 썸네일과 동일한 타이틀 스타일(둥근 자막 박스 아님)을 얹는다."""
import os
from PIL import Image, ImageDraw
import thumb_v3 as tv
# (longform_caption 은 이 모듈에서 안 씀 — 맑은 고딕 의존 제거)

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920
INK, WHITE, RED = tv.INK, tv.WHITE, tv.RED


def base_full(photo, fx=0.5, fy=0.35, desat=0.62, darken=0.18):
    """세로 화면 전체를 사진으로 채운다(풀블리드, 좌우 분할 없음)."""
    if desat:
        photo = tv.desaturate(photo, factor=1 - desat)
    p = tv.cover(photo, W, H, fx, fy).convert("RGBA")
    if darken:
        p = Image.alpha_composite(p, Image.new("RGBA", p.size, (0, 0, 0, int(255 * darken))))
    im = Image.new("RGBA", (W, H), (*INK, 255))
    im.alpha_composite(p)
    return im


def top_shade(im, height=560, alpha=170, ease=1.4):
    """상단(제목 패널이 얹히는 구간)을 살짝 더 어둡게 그라데이션 — 패널 없이도 글자가 뜨게."""
    grad = Image.new("RGBA", im.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for y in range(height):
        a = int(alpha * (1 - y / height) ** ease)
        gd.line([(0, y), (W, y)], fill=(*INK, a))
    im.alpha_composite(grad)


def logo_mark(im, logo_path, corner="bl", margin=44, height=72):
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


def build(photo, lines, logo_path, fx=0.5, fy=0.3, out=None, top_y=260, gap_ratio=1.02, shade_height=820, shade_alpha=200):
    """2026-09-24 3차 재조정: "쇼츠 자막"이 아니라 "가로형 썸네일의 타이틀 스타일"을
    말한 것이었음 — 화이트+레드 Black Han Sans 임팩트 타이틀을 화면 위쪽에, 그 아래를 그라데이션으로
    어둡게 눌러서 얹는다(둥근 자막 박스 방식은 폐기). 사진은 풀블리드 그대로, 제목은 가이드라인(안전
    영역)에 잘리지 않을 최소한의 여백만 두고 최대한 위쪽에 배치한다.
    lines: [(text, size, fill), ...] — tv.stacked_lines에 그대로 전달, 보통 화이트 1줄 + 레드 1줄."""
    im = base_full(photo, fx=fx, fy=fy, darken=0.0)
    top_shade(im, height=shade_height, alpha=shade_alpha)
    tv.stacked_lines(im, 56, top_y, lines, gap_ratio=gap_ratio)
    logo_mark(im, logo_path, "bl")
    if out:
        im.convert("RGB").save(os.path.join(HERE, out), quality=95, subsampling=0)
    return im
