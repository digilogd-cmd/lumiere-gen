# -*- coding: utf-8 -*-
"""마무리 공용 부품: 음량 2-pass 맞추기, 음량 재기, 실제 프레임 시트.
(뤼미에르 에디트의 stages/final.py 에서 생성형이 쓰는 것만 옮김 — 2026-10-09 젠 분리 정리)"""
import os, re, subprocess
import numpy as np
from .core import run as sh, ts


def loudnorm_2pass(wav, out, target):
    """목표 음량 맞추기: (소리 차이가 크면 먼저 압축) + 이득 + 4배 오버샘플 리미터를 걸고 재서(통합 LUFS·true peak) 고치기를 반복 -> AAC 한 번.
    1-pass loudnorm은 -12.5 목표에 -13.8(2026-10-05), 아주 작은 소리(-33 LUFS, 휴대폰 마이크)는 리미터만으로 피크 +2.8dB(2026-10-07)."""
    def meas(af):
        r = subprocess.run(["ffmpeg", "-v", "info", "-i", wav, "-af", af + ",ebur128=peak=true", "-f", "null", "-"], capture_output=True)
        t = r.stderr.decode("utf-8", "replace")
        m = re.findall(r"I:\s+(-?[\d.]+) LUFS", t)
        pk = re.findall(r"Peak:\s+(-?[\d.]+|-inf) dBFS", t)
        return (float(m[-1]) if m else None), (float(pk[-1]) if pk and pk[-1] != "-inf" else None)
    i0, p0 = meas("anull")
    comp = ""
    if i0 is not None and p0 is not None and p0 - i0 > 22:      # 피크와 평균 차이가 너무 크면(멀리서 녹음된 소리) 먼저 고르게
        comp = "acompressor=threshold=0.06:ratio=4:attack=5:release=150:makeup=1,"
    g = target - (i0 if i0 is not None else target)
    lim = 0.71
    chain = lambda: f"{comp}volume={g:.2f}dB,aresample=192000,alimiter=limit={lim:.3f}:attack=2:release=80:level=false,aresample=48000"
    for _ in range(6):
        i1, p1 = meas(chain())
        if i1 is None:
            break
        ok_i, ok_p = abs(i1 - target) <= 0.2, (p1 is None or p1 <= -1.8)
        if ok_i and ok_p:
            break
        if not ok_p:
            lim *= 10 ** ((-2.0 - p1) / 20)          # 피크가 넘친 만큼 리미터 문턱을 낮춤
        g += target - i1
    sh(["ffmpeg", "-y", "-v", "error", "-i", wav, "-af", chain(), "-c:a", "aac", "-b:a", "256k", out])


def measure_loud(path):
    """(통합 LUFS, 최대 true peak dBTP) — 인코딩 끝난 파일을 직접 잰다."""
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", path, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True)
    t = r.stderr.decode("utf-8", "replace")
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", t)
    p = re.findall(r"Peak:\s+(-?[\d.]+|-inf) dBFS", t)
    lufs = float(m[-1]) if m else None
    tp = float(p[-1]) if p and p[-1] != "-inf" else None
    return lufs, tp


def frame_sheet(path, d, times, cols=4):
    """실제 렌더 결과에서 프레임을 뽑아 한 장으로(검수용)."""
    import cv2
    from .media import imwrite
    ims = []
    for i, t in enumerate(times[:40]):
        f = os.path.join(d, f"_sheet_{i:02d}.jpg")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{max(0, t):.2f}", "-i", path, "-frames:v", "1", "-vf", "scale=480:-2", f],
                       capture_output=True)
        if os.path.exists(f):
            im = cv2.imdecode(np.fromfile(f, np.uint8), cv2.IMREAD_COLOR)
            os.remove(f)
            if im is not None:
                cv2.putText(im, ts(t), (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                ims.append(im)
    if not ims:
        return None
    h, w = ims[0].shape[:2]
    while len(ims) % cols:
        ims.append(np.zeros((h, w, 3), np.uint8))
    rows = [np.hstack([cv2.resize(x, (w, h)) for x in ims[i:i + cols]]) for i in range(0, len(ims), cols)]
    out = os.path.join(d, "종편_프레임_확인.jpg")
    imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 82])
    return out

