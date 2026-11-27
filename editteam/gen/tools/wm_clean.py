# -*- coding: utf-8 -*-
"""Flow 그림 ✦ 워터마크 지우기(생성형, 2026-10-08).
게이트 wm_remove.py(투명도 지도 _wm_alpha.npy 역산)를 1376x768 그림에 쓰면 별 테두리·안쪽이 희미하게 남았다(시험 A 확대 확인).
그래서 이 PC의 Flow 1K 그림 107장(시험 A + 게이트 EP01~03)에서 별 자리를 맞춰 겹쳐 투명도 지도를 새로 뽑았다(_wm_alpha_flow1k.npy, 64x64).
  1) 오른쪽 아래 140px 안에서 별 모양을 찾고(고주파 템플릿 맞춤)
  2) 세기(gain)는 '복원한 별 안쪽 평균색 = 바로 바깥 고리 평균색'이 되게 고르고(배경 밝기마다 세기가 다름)
  3) 원본 = (결과 - 255a)/(1-a) 로 되돌린 뒤 별 테두리 얇은 띠만 인페인트로 메운다."""
import os
import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
P = 64


def _maps():
    al0 = np.load(os.path.join(HERE, "_wm_alpha_flow1k.npy")).astype(np.float32)
    m = (al0 > 0.03).astype(np.uint8)
    k = np.ones((3, 3), np.uint8)
    inner = al0 > 0.5 * al0.max()
    ring = cv2.dilate(m, k, iterations=4).astype(bool) & ~cv2.dilate(m, k, iterations=1).astype(bool)
    edge = (cv2.dilate(m, k, iterations=2) - cv2.erode(m, k, iterations=1)) * 255
    return al0, inner, ring, edge


def clean(src, dst):
    """-> {"x","y","gain"} (찾은 자리) / 그림이 너무 작으면 None(그대로 저장)."""
    al0, inner, ring, edge = _maps()
    a = np.asarray(Image.open(src).convert("RGB"), np.float32)
    h, w = a.shape[:2]
    if w < 300 or h < 300:
        Image.fromarray(a.astype(np.uint8)).save(dst)
        return None
    g_ = cv2.cvtColor(a.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    reg = g_[h - 140:, w - 140:]
    hp = reg - cv2.GaussianBlur(reg, (0, 0), 6)
    r = cv2.matchTemplate(hp, (al0 - al0.mean()).astype(np.float32), cv2.TM_CCOEFF)
    _, _, _, loc = cv2.minMaxLoc(r)
    x0, y0 = w - 140 + loc[0], h - 140 + loc[1]
    best = None
    for g in np.arange(0.5, 1.6, 0.05):
        al = np.clip(al0 * g, 0, 0.95)[..., None]
        rr = np.clip((a[y0:y0 + P, x0:x0 + P] - 255 * al) / np.maximum(1 - al, 1e-3), 0, 255)
        d = np.abs(rr[inner].mean(0) - rr[ring].mean(0)).sum()
        if best is None or d < best[0]:
            best = (d, float(g), rr)
    a[y0:y0 + P, x0:x0 + P] = best[2]
    out = a.astype(np.uint8)
    mask = np.zeros((h, w), np.uint8)
    mask[y0:y0 + P, x0:x0 + P] = edge
    out = cv2.cvtColor(cv2.inpaint(cv2.cvtColor(out, cv2.COLOR_RGB2BGR), mask, 2, cv2.INPAINT_TELEA), cv2.COLOR_BGR2RGB)
    Image.fromarray(out).save(dst)
    return {"x": int(x0), "y": int(y0), "gain": round(best[1], 2)}
