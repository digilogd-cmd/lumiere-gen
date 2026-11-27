# -*- coding: utf-8 -*-
"""소리·영상 공통 계산(AI 필요 없음): wav 뽑기, 10ms 소리 크기 곡선, 무음 찾기, 경계 맞추기."""
import os, wave
import numpy as np
from .core import safe_replace, run



def imread(path):
    """한글 경로도 읽히게(윈도우 OpenCV는 한글 경로를 못 연다)."""
    import cv2
    return cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)


def imwrite(path, im, params=None):
    """한글 경로에도 저장되게."""
    import cv2
    ok, buf = cv2.imencode(os.path.splitext(path)[1] or ".jpg", im, params or [])
    if ok:
        buf.tofile(path)
    return ok

def extract_wav(src, dst, sr=16000, ch=1):
    if not os.path.exists(dst):
        tmp = dst + ".part.wav"
        run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vn", "-ac", str(ch), "-ar", str(sr), "-c:a", "pcm_s16le", tmp])
        safe_replace(tmp, dst)
    return dst


def read_wav(path, mmap=False):
    """(샘플 배열 int16 [n, ch], 샘플레이트). mmap이면 큰 파일도 메모리에 다 안 올림."""
    w = wave.open(path)
    sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
    if mmap:
        # wav 헤더 뒤 data 위치 찾기
        with open(path, "rb") as f:
            head = f.read(4096)
        off = head.find(b"data") + 8
        a = np.memmap(path, dtype=np.int16, mode="r", offset=off, shape=(n * ch,))
    else:
        a = np.frombuffer(w.readframes(n), dtype=np.int16)
    return a.reshape(-1, ch), sr


def write_wav(path, a, sr):
    a = np.clip(a, -32768, 32767).astype(np.int16)
    if a.ndim == 1:
        a = a[:, None]
    with wave.open(path, "wb") as w:
        w.setnchannels(a.shape[1]); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(a.tobytes())


def db_curve(wav16):
    """10ms마다 소리 크기(dB)와 발화 기준값 thr(바닥 소음 30% 분위 + 15dB, 롱폼 스크립트들과 같은 기준)."""
    a, sr = read_wav(wav16)
    a = a[:, 0].astype(np.float32)
    hop = sr // 100
    n = len(a) // hop
    db = 20 * np.log10(np.sqrt((a[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1)
    return db, float(np.percentile(db, 30) + 15)


def quiet_runs(db, thr, below=-3.0, min_len=1.5, start=0.0, end=None):
    """thr+below 보다 조용한 구간 [(s, e)] (초)."""
    q = db < thr + below
    n = len(db) if end is None else min(len(db), int(end * 100))
    out, j = [], int(start * 100)
    m = int(min_len * 100)
    while j < n:
        if q[j]:
            k = j
            while k < n and q[k]:
                k += 1
            if k - j >= m:
                out.append((j / 100, k / 100))
            j = k
        else:
            j += 1
    return out


def snap_quiet(db, t, lo, hi):
    """t+lo ~ t+hi 사이에서 가장 조용한 10ms 지점."""
    a, b = int(round((t + lo) * 100)), int(round((t + hi) * 100))
    a, b = max(a, 0), min(b, len(db) - 1)
    if b <= a:
        return t
    return (a + int(np.argmin(db[a:b + 1]))) / 100


def thumb_jpg(src_img_bgr, path, width=480):
    """대시보드 미리보기용 작은 jpg(가로 480)."""
    import cv2
    h, w = src_img_bgr.shape[:2]
    im = cv2.resize(src_img_bgr, (width, int(h * width / w)), interpolation=cv2.INTER_AREA)
    imwrite(path, im, [cv2.IMWRITE_JPEG_QUALITY, 82])
    return path


def grab_frame(video, t, path=None, width=None):
    """영상 t초 한 장(BGR). path가 있으면 jpg로도 저장."""
    import cv2
    import subprocess
    vf = f"scale={width}:-2" if width else "null"
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, t):.3f}", "-i", video, "-frames:v", "1", "-vf", vf,
                        "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    if not r.stdout:
        return None
    im = cv2.imdecode(np.frombuffer(r.stdout, np.uint8), cv2.IMREAD_COLOR)
    if path is not None and im is not None:
        imwrite(path, im, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return im



# 파일 안 메타데이터로 '카메라 vs 화면 녹화' 판단(2026-10-07: 해상도 말고 파일 형식으로 — 작은 화면 녹화도 있으니까)
# ffmpeg 서명(Lavf)은 편집해서 다시 저장한 파일에도 붙어서 판단 근거로 쓰지 않는다.
CAM_TAGS = ("com.android.", "com.samsung.", "com.apple.quicktime.make", "com.apple.quicktime.model", "com.apple.quicktime.location",
            "make", "model", "location", "location-eng", "com.xiaomi.", "com.huawei.", "firmware")
CAM_MAKERS = ("gopro", "dji", "sony", "canon", "nikon", "panasonic", "fujifilm", "insta360", "apple", "samsung", "iphone", "galaxy", "pixel", "blackmagic")
SCREEN_SIGNS = ("avc coding", "obs studio", "obs ", "bandicam", "camtasia", "sharex", "screen", "xbox", "game bar", "gamedvr", "nvidia", "shadowplay",
                "geforce", "radeon", "relive", "clipchamp", "loom", "snagit", "quicktime player", "screenflow", "capcut")


def video_tags(path):
    """ffprobe 컨테이너·영상 스트림 태그(소문자 키: 값)."""
    import json, subprocess
    try:
        o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags:stream_tags:stream=codec_type",
                            "-of", "json", path], capture_output=True, text=True, encoding="utf-8", timeout=20).stdout
        j = json.loads(o or "{}")
    except Exception:
        return {}
    tags = {k.lower(): str(v) for k, v in ((j.get("format") or {}).get("tags") or {}).items()}
    for st in j.get("streams") or []:
        for k, v in (st.get("tags") or {}).items():
            tags.setdefault(k.lower(), str(v))
    return tags


def media_kind(path):
    """'camera' | 'screen' | None(모름). 근거 문장도 같이."""
    t = video_tags(path)
    dev = [k for k in t if k.startswith(CAM_TAGS)]
    blob = " ".join(f"{k}={v}" for k, v in t.items()).lower()
    if dev:
        return "camera", "촬영 기기 정보(" + ", ".join(dev[:2]) + ")"
    if any(m in blob for m in CAM_MAKERS) and ("handler_name" in t or "encoder" in t):
        mk = next(m for m in CAM_MAKERS if m in blob)
        if mk not in ("apple",) or "quicktime.make" in blob:
            return "camera", f"카메라 제조사 표시({mk})"
    sig = next((x for x in SCREEN_SIGNS if x in blob), None)
    if sig:
        return "screen", f"녹화 프로그램 표시({sig})"
    return None, "기기·녹화 프로그램 정보 없음"

CAM_SIZES = {(1280, 720), (1920, 1080), (2560, 1440), (3840, 2160), (4096, 2160), (1440, 1080), (2704, 1520), (2720, 1530),
             (720, 1280), (1080, 1920), (1440, 2560), (2160, 3840)}


def video_size(path):
    import subprocess
    try:
        o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                            "-of", "csv=p=0", path], capture_output=True, text=True, timeout=20).stdout
        w, h = [int(x) for x in o.strip().strip(",").split(",")[:2]]
        return w, h
    except Exception:
        return None


def looks_like_screen(path):
    """화면 녹화인지(2026-10-07: 이름에 '녹화'가 없어 카메라로 잘못 분류됨). 순서: 파일 메타데이터 > 이름 > 해상도(마지막 수단)."""
    import re
    n = os.path.basename(path)
    k, _ = media_kind(path)                 # 1순위: 파일 안 메타데이터(기기 정보 / 녹화 프로그램)
    if k:
        return k == "screen"
    if re.search(r"(?<!\d)\d{8}_\d{6}", n):     # 휴대폰 카메라 이름 형식
        return False
    if re.search(r"녹음|녹화|화면|screen|record|캡처|capture|obs", n, re.I):
        return True
    s = video_size(path)                    # 마지막 수단(정보가 하나도 없을 때만) — 꼬리표를 눌러 바꿀 수 있음
    return bool(s) and s not in CAM_SIZES
