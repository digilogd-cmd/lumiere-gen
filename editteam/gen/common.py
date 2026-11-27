# -*- coding: utf-8 -*-
"""생성형 공통: 설정(생성.*), 프로젝트 안내 정보(brief), 크롬 다운로드 폴더 찾기, 화면 크기."""
import sys
import datetime, json, os

from ..core import jload


def gcfg(cfg):
    g = dict(cfg.get("생성") or {})
    g.setdefault("화풍", "따뜻한 수채화풍 일러스트")
    g.setdefault("목표_초", 90)
    g.setdefault("화자_목소리", ["Charon", "Kore", "Puck"])
    g.setdefault("영상_클립_한도", 4)
    g.setdefault("음악_한도", 3)
    g.setdefault("이미지_한도", 30)
    g.setdefault("재시도_한도", 2)
    g.setdefault("다운로드_폴더", "")
    g.setdefault("디졸브_초", 0.4)
    g.setdefault("음악_크기", 0.42)
    g.setdefault("앞_여백_초", 0.6)
    g.setdefault("뒤_여백_초", 2.5)
    return g


def gen_name():
    return "생성_" + datetime.datetime.now().strftime("%m%d_%H%M")


def is_gen(P):
    return bool(P.meta.get("gen"))


def brief(P):
    """gen_brief 단계가 만든 brief.json(없으면 project.json 의 gen 값)."""
    from ..parts import dir_name
    b = jload(os.path.join(P.p(dir_name("gen_brief")), "brief.json"))
    return b or dict(P.meta.get("gen") or {})


def size_of(vertical):
    return (1080, 1920) if vertical else (1920, 1080)


def sdir(P, name):
    """생성형 단계 폴더(work/<프로젝트>/gen_NN_이름)."""
    return P.stage_dir(0, name)


def chrome_download_dir():
    """크롬 설정(Preferences)에서 다운로드 폴더를 읽는다. 못 찾으면 사용자 '다운로드' 폴더."""
    if sys.platform == "darwin":                   # 맥 크롬 설정 위치
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Google", "Chrome")
    else:
        base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data")
    cands = []
    if os.path.isdir(base):
        for prof in ["Default"] + sorted(x for x in os.listdir(base) if x.startswith("Profile ")):
            pf = os.path.join(base, prof, "Preferences")
            if os.path.exists(pf):
                try:
                    d = (json.load(open(pf, encoding="utf-8")).get("download") or {}).get("default_directory")
                    if d and os.path.isdir(d):
                        cands.append((os.path.getmtime(pf), d))
                except (OSError, ValueError):
                    pass
    if cands:
        return sorted(cands)[-1][1]
    d = os.path.join(os.path.expanduser("~"), "Downloads")
    return d if os.path.isdir(d) else ""


def download_dir(cfg):
    d = gcfg(cfg).get("다운로드_폴더") or ""
    return d if d and os.path.isdir(d) else chrome_download_dir()


def recent_downloads(cfg, n=10, exts=(".png", ".jpg", ".jpeg", ".webp", ".mp4", ".wav", ".mp3", ".m4a")):
    d = download_dir(cfg)
    if not d:
        return []
    fs = [os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(exts)]
    fs = [f for f in fs if os.path.isfile(f) and not f.endswith((".crdownload", ".tmp"))]
    return sorted(fs, key=os.path.getmtime, reverse=True)[:n]
