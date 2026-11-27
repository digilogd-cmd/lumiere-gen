# -*- coding: utf-8 -*-
"""썸네일 그리기 공용 부품(롱폼형 1280x720 + 세로 1080x1920). 글자 최소 100px, 얼굴 피하기, 포인트 색 한 줄.
(뤼미에르 에디트의 stages/th_render.py 에서 생성형이 쓰는 그리기 함수만 옮김 — 2026-10-09 젠 분리 정리)"""
import os, re
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from .core import ROOT
import thumb_v3 as tv
import thumb_shorts as ts_


LOGOS = os.path.join(ROOT, "내_로고")          # 내 스타일 층: 쇼츠 썸네일에 얹을 도구·브랜드 로고(상표 로고는 제품에 넣지 않음)


W, H = 1080, 1920


MIN = 100            # SOP 6-0 글자 최소 크기(1280x720 / 1080 폭 공통 절대 픽셀)


def pil(bgr):
    import cv2
    return Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


def sized(text, start, max_w):
    """fit_size 로 줄이되 SOP 최소 100 아래로는 안 내린다(넘치면 기록)."""
    s = tv.fit_size(text, max_w=max_w, start=start)
    return max(MIN, min(start, s)), s < MIN


def text_w(text, size):
    """thumb_v3.fit_size 와 같은 방식으로 잰 글자 폭(px)."""
    from PIL import ImageFont
    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    f = ImageFont.truetype(tv.BLACK_HAN, size)
    return int(sum(d.textlength(ch, font=f) for ch in text[:-1]) * tv.TRACKING + d.textlength(text[-1], font=f)) if text else 0


def detect_face(photo):
    """사진에서 가장 큰 정면 얼굴 [x,y,w,h] (없으면 None)."""
    try:
        import cv2, numpy as np
        g = cv2.cvtColor(np.asarray(photo.convert("RGB")), cv2.COLOR_RGB2GRAY)
        cc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        f = cc.detectMultiScale(g, 1.1, 5, minSize=(max(40, g.shape[1] // 20),) * 2)
        return [int(v) for v in max(f, key=lambda r: r[2])] if len(f) else None
    except Exception:
        return None


def long_thumb(path, photo, lines, logo, kind, face_box=None, chan=""):
    """SOP 6-0. kind=face|screen."""
    face_l = None                      # 썸네일 안 얼굴 왼쪽 끝(x) — 글자가 여기를 넘지 않게
    if kind == "face":
        fx = 0.5
        if not face_box:
            face_box = detect_face(photo)
        split = 0.58
        if face_box:
            # tv.cover 의 fx 는 '왼쪽 시작 비율'이다(가운데가 아님 — 2026-10-07 예전 영상 글자가 안경을 가림).
            # 얼굴 가운데가 썸네일 오른쪽(80%~)에 오게 fx 를 거꾸로 계산하고, 글자가 최소 크기로도 얼굴 앞에 안 들어가면
            # 사진 시작점(split)을 오른쪽으로 밀어 얼굴을 더 오른쪽으로 보낸다.
            feather = 300
            for split, target in ((0.58, 0.80), (0.63, 0.84), (0.68, 0.88)):
                x0 = max(0, int(tv.W * split) - feather); pw = tv.W - x0
                k = max(pw / photo.width, tv.H / photo.height); sw = photo.width * k
                cx = (face_box[0] + face_box[2] / 2) * k
                fx = min(1.0, max(0.0, (x0 + cx - tv.W * target) / max(1.0, sw - pw)))
                face_l = int(x0 + (face_box[0] - face_box[2] * 0.25) * k - (sw - pw) * fx)   # 얼굴 인식 상자는 안경·귀보다 좁아서 25% 넓게
                if all(text_w(t, MIN) <= face_l - 30 - 56 for t in lines):
                    break
        im = tv.base(photo, split=split, fx=fx, fy=0.3).convert("RGBA")   # feather 300 / darken .20 / desat .62 (기본값)
    else:   # 실제 화면: 글자가 많아 더 어둡게 누르고 채도 더 낮춤(예전 영상 3번 썸네일 값)
        im = tv.base(photo, split=0.55, fx=0.5, fy=0.2, darken=0.55, desat=0.4).convert("RGBA")
        split = 0.55
    x, y = 56, 120
    used, over = [], False
    for i, text in enumerate(lines):
        max_w = int(tv.W * split) + 40
        if face_l is not None:         # 얼굴 왼쪽 끝 30px 앞까지만
            max_w = min(max_w, face_l - 30 - x)
        size, o = sized(text, 112 if i == 0 else 140, max_w)
        over |= o; used.append(size)
        # SOP 6-0: 흰색 + 레드 포인트 '한 곳'(2026-10-05 감사: 2·3줄이 모두 빨강이었음). 앱 로고(파랑·주황)도 넣지 않는다 — 색은 흰+레드만.
        y = tv.stacked_lines(im, x, y, [(text, size, tv.RED if i == 1 else tv.WHITE)], gap_ratio=1.16)
    if logo and os.path.exists(logo):
        tv.logo_mark(im, logo, "bl")
    else:
        tv.brand_mark(im, "bl", text=chan)          # 로고가 없으면 채널 이름(그것도 없으면 아무것도 안 그림)
    im.convert("RGB").save(path, quality=95, subsampling=0)
    return {"file": path, "sizes": used, "min_ok": min(used) >= MIN, "fit_over": over, "text_bottom": y, "logo": bool(logo and os.path.exists(logo)),
            "red_lines": int(len(lines) > 1), "text_x": x, "face_left": face_l,
            "text_right": max([x + text_w(t, sz) for t, sz in zip(lines, used)], default=x)}


def short_bg(still):
    s = still.crop((0, 0, still.width, int(still.height * 0.82)))
    k = H / s.height; s = s.resize((int(s.width * k) + 1, H), Image.LANCZOS)
    x = max(0, (s.width - W) // 2)
    return ImageEnhance.Brightness(s.crop((x, 0, x + W, H)).filter(ImageFilter.GaussianBlur(22))).enhance(0.7)


def card(im, c, w, xy, r=26):
    c = c.resize((w, int(c.height * w / c.width)), Image.LANCZOS).convert("RGBA")
    if c.height > 1480 - xy[1]:      # 아래 안전영역(1600) 안
        c = c.crop((0, 0, c.width, 1480 - xy[1]))
    m = Image.new("L", c.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, *c.size), r, fill=255)
    sh = Image.new("RGBA", (c.width + 80, c.height + 80), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((40, 50, 40 + c.width, 50 + c.height), r, fill=(0, 0, 0, 170))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)), (xy[0] - 40, xy[1] - 40))
    im.paste(c, xy, m)
    return xy[1] + c.height


def app_logos(im, files, y):
    for i, f in enumerate(files):
        L = Image.open(os.path.join(LOGOS, f)).convert("RGBA").resize((150, 150), Image.LANCZOS)
        s = Image.new("RGBA", (190, 190), (0, 0, 0, 0)); ImageDraw.Draw(s).rounded_rectangle((20, 26, 170, 176), 34, fill=(0, 0, 0, 120))
        x = W - 195 - i * 175
        im.alpha_composite(s.filter(ImageFilter.GaussianBlur(10)), (x - 20, y - 20)); im.alpha_composite(L, (x, y))


TITLE_TOP = 345


def short_title(im, lines):
    used, over = [], False
    y = TITLE_TOP   # 인스타 그리드 안전영역 y 320~1600 (11-4-V)
    for i, text in enumerate(lines):
        size, o = sized(text, 120 if i == 0 else 150, 980)
        over |= o; used.append(size)
        y = tv.stacked_lines(im, 56, y, [(text, size, tv.WHITE if i == 0 else tv.RED)], gap_ratio=1.04)
    return y, used, over


def short_classic(path, still, crop, lines, logos, logo):
    im = short_bg(still).convert("RGBA")
    ts_.top_shade(im, height=900, alpha=190)
    y_end, used, over = short_title(im, lines)
    x, y, w, h = crop
    c = still.crop((x, y, x + w, y + h))
    cw = 940 if c.width >= c.height else 700
    cy = max(int(y_end) + 60, 820)
    bottom = card(im, c, cw, ((W - cw) // 2, cy))
    app_logos(im, logos, cy - 110)
    if logo and os.path.exists(logo):
        ts_.logo_mark(im, logo, "bl")
    im.convert("RGB").save(path, quality=95, subsampling=0)
    # 2026-10-05 감사: 예전 safe_ok 는 상수 비교라 늘 참이었다 -> 실제 위치로 잰다
    return {"file": path, "sizes": used, "min_ok": min(used) >= MIN, "fit_over": over, "text_top": TITLE_TOP, "text_bottom": y_end,
            "card_bottom": bottom, "safe_ok": TITLE_TOP >= 320 and bottom <= 1600 and y_end <= 1600 and cy - 110 >= 320}


def short_face(path, face_img, lines, logos, logo):
    p = ImageEnhance.Color(face_img).enhance(0.88)
    p = p.resize((W, int(p.height * W / p.width)), Image.LANCZOS)
    bg = p.crop((0, 0, W, max(1, int(p.height * 0.25)))).resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(30))
    im = bg.convert("RGBA")
    m = Image.linear_gradient("L").resize((W, p.height)).point(lambda v: min(255, int(v * 6)))
    im.paste(p, (0, H - p.height), m)
    ts_.top_shade(im, height=900, alpha=175)
    y_end, used, over = short_title(im, lines)
    app_logos(im, logos, 1180)
    if logo and os.path.exists(logo):
        ts_.logo_mark(im, logo, "bl")
    im.convert("RGB").save(path, quality=95, subsampling=0)
    return {"file": path, "sizes": used, "min_ok": min(used) >= MIN, "fit_over": over, "text_top": TITLE_TOP, "text_bottom": y_end,
            "safe_ok": TITLE_TOP >= 320 and y_end <= 1600 and y_end < 1180}

