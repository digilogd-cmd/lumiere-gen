# -*- coding: utf-8 -*-
"""편집팀 실행기 공통 부품: 프로젝트 폴더, 진행 기록(events.jsonl), 단계 이어하기(입력 해시), 설정.
규격은 작업지시서 단계 2. 대시보드는 events.jsonl 한 파일만 읽으면 현재 상태를 전부 복원할 수 있어야 한다."""
import datetime, hashlib, json, os, subprocess, sys, threading, time
import yaml

PKG = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(PKG)                      # LUMIERE_GEN
TOOLS = os.path.join(PKG, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


USER_SETTINGS = os.path.join(ROOT, "설정.json")   # 대시보드 [설정]에서 바꾼 값(config.yaml 위에 덮어씀)


def deep_merge(base, over):
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def user_settings():
    if os.path.exists(USER_SETTINGS):
        with open(USER_SETTINGS, encoding="utf-8") as f:
            return json.load(f)
    return {}


# 프로젝트를 나중에 다시 불러와도(수정·쇼츠) 처음 편집 때 설정 그대로 — 단, 이것들은 항상 지금 설정을 따른다
LIVE_SETTINGS = ("두뇌", "알림", "개발자")


def settings_for_project(snapshot):
    """처음 편집 때 저장해 둔 설정(snapshot) + 지금 설정 중 LIVE_SETTINGS."""
    import copy
    cur = user_settings()
    u = copy.deepcopy(snapshot)
    for k in LIVE_SETTINGS:
        if k in cur:
            u[k] = cur[k]
        else:
            u.pop(k, None)
    return u


def load_config(path=None, user=None):
    """config.yaml 위에 사용자 설정(설정.json, 또는 user로 준 것)을 덮어쓴다."""
    path = path or os.path.join(ROOT, "config.yaml")
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    deep_merge(cfg, user if user is not None else user_settings())
    from .design import apply           # 컬러 팔레트(디자인.팔레트) -> 모션.* 색
    return apply(cfg)


def jdump(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def safe_replace(src, dst, tries=20, alt_ok=False, wait_s=0, ev=None):
    """윈도우에서 재생기 등이 파일을 잡고 있으면 교체가 막힌다 -> 잠깐씩 기다리며 다시 시도.
    wait_s 면 그만큼 더 기다리며 15초마다 '재생을 닫아 주세요'를 알린다(가편처럼 사람이 보고 있을 수 있는 큰 파일, 2026-10-07 두 번 실패).
    alt_ok 면(완성 영상처럼 사람이 보고 있을 수 있는 파일) 끝내 막힐 때 '이름_시각.mp4'로 새로 저장하고 그 경로를 돌려준다."""
    import time as _t
    t_end = _t.time() + max(tries * 0.5, wait_s)
    last = 0
    while True:
        try:
            os.replace(src, dst)
            return dst
        except PermissionError:
            if _t.time() > t_end:
                break
            if ev is not None and _t.time() - last > 15:
                last = _t.time()
                ev.log(f"'{os.path.basename(dst)}'가 다른 곳(영상 재생기·탐색기 미리보기·완성 폴더)에서 열려 있어 기다리는 중이에요. 재생을 닫아 주세요.", "warn")
            _t.sleep(0.5)
    if alt_ok:
        base, ext = os.path.splitext(dst)
        alt = f"{base}_{_t.strftime('%H%M%S')}{ext}"
        os.replace(src, alt)
        return alt
    raise StageError(f"'{os.path.basename(dst)}' 파일이 다른 프로그램(대시보드 영상 재생기·탐색기 미리보기 등)에서 열려 있어 바꿀 수 없습니다. "
                     "재생을 닫고 다시 실행해 주세요.")


def jload(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ts(t):
    """초 -> 사람이 읽는 시각 m:ss.s"""
    t = max(0.0, float(t))
    return f"{int(t // 60)}:{t % 60:04.1f}"


def ts_long(t):
    t = max(0, int(round(t)))
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60}:{t % 60:02d}"


class Events:
    """events.jsonl 기록기. 여러 스레드(병렬 렌더)에서 불러도 줄이 섞이지 않게 잠금."""

    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.stage_name = None

    def emit(self, **kw):
        kw = {"t": now(), **kw}
        line = json.dumps(kw, ensure_ascii=False)
        with self.lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        return kw

    # --- 편의 함수 (작업지시서 단계 2 규격)
    def stage(self, stage, state, pct=None, msg=""):
        d = {"type": "stage", "stage": stage, "state": state, "msg": msg}
        try:
            from .parts import part_of
            d["part"] = part_of(stage)
        except Exception:
            pass
        if pct is not None:
            d["pct"] = int(max(0, min(100, pct)))
        self.emit(**d)

    def progress(self, pct, msg=""):
        self.stage(self.stage_name, "progress", pct, msg)

    def log(self, text, level="info", stage=None):
        print(f"  {text}", flush=True)
        self.emit(type="log", stage=stage or self.stage_name, level=level, text=text)

    def stat(self, key, value):
        self.emit(type="stat", key=key, value=value)

    def cut(self, src_s, src_e, kind, label, **extra):
        self.emit(type="cut", src_s=round(src_s, 2), src_e=round(src_e, 2), kind=kind, label=label, **extra)

    def preview(self, kind, path, caption=""):
        self.emit(type="preview", kind=kind, path=path, caption=caption)

    def output(self, key, path, meta=""):
        self.emit(type="output", key=key, path=path, meta=meta)

    def checkpoint(self, state, msg=""):
        self.emit(type="checkpoint", state=state, msg=msg)


class Project:
    """work/<프로젝트>/ 폴더 하나 = 촬영본 하나."""

    def __init__(self, name, cfg=None, root=None):
        self.name = name
        self.dir = os.path.join(root or os.path.join(ROOT, "work"), name)
        os.makedirs(self.dir, exist_ok=True)
        self.ev = Events(os.path.join(self.dir, "events.jsonl"))
        self.meta_path = os.path.join(self.dir, "project.json")
        self.meta = jload(self.meta_path, {})
        self._meta0 = json.loads(json.dumps(self.meta))       # 읽을 때 모습 — save_meta 가 '내가 바꾼 키만' 쓰게
        if cfg is None and self.meta.get("settings_at_start") is not None:
            # 다시 불러온 프로젝트: 다른 영상 편집하며 바꾼 설정(팔레트·글꼴 등)이 이 영상에 섞이지 않게 처음 설정으로
            cfg = load_config(user=settings_for_project(self.meta["settings_at_start"]))
        self.cfg = cfg or load_config()
        if self.meta.get("script_keywords"):
            self.cfg = dict(self.cfg, _대본_키워드=self.meta["script_keywords"])
        if self.meta.get("cfg"):            # 이 프로젝트에만 쓰는 설정(예: {"PIP": {"보일때": "camera"}})
            import copy
            self.cfg = deep_merge(copy.deepcopy(self.cfg), self.meta["cfg"])
            from .design import apply
            self.cfg = apply(self.cfg)

    def save_meta(self):
        """디스크 최신본 + 이 객체가 바꾼 키만 합쳐 저장한다(2026-10-18 에디트 예전 영상: 창·프로세스 여럿이 각자 읽은 meta 를
        통째로 써서 다른 창이 넣은 값이 사라졌던 일 — 에디트·젠·쇼츠 공통 수정). 같은 키를 둘이 바꾸면 나중 저장이 이긴다."""
        disk = jload(self.meta_path, {})
        base = self._meta0
        for k in set(base) | set(self.meta):
            if k not in self.meta:
                if k in base:
                    disk.pop(k, None)               # 내가 지운 키
            elif k not in base or base[k] != self.meta[k]:
                disk[k] = self.meta[k]              # 내가 넣거나 바꾼 키
        jdump(disk, self.meta_path)
        self.meta.clear(); self.meta.update(disk)          # 같은 dict 를 쥐고 있는 코드가 있어도 그대로 보이게
        self._meta0 = json.loads(json.dumps(disk))

    def p(self, *a):
        return os.path.join(self.dir, *a)

    def rel(self, path):
        """대시보드에 넘길 경로(프로젝트 폴더 기준 상대 경로, 슬래시)."""
        try:
            return os.path.relpath(path, ROOT).replace("\\", "/")
        except ValueError:
            return path

    def stage_dir(self, idx, name):
        """단계 폴더. 번호(idx)는 옛 호출과의 호환용이고, 실제 폴더 이름은 parts.py 의 파트·순서로 정한다."""
        from .parts import dir_name
        d = self.p(dir_name(name))
        os.makedirs(d, exist_ok=True)
        return d

    def revisions(self):
        """중간 점검 답(살리기·줌 빼기·추가 컷). revise 명령이 쓴다."""
        return jload(self.p("revisions.json"), {"restore": [], "unzoom": [], "extra_cuts": [], "unblur": []})


def file_sig(path):
    """큰 촬영본은 내용 해시 대신 경로·크기·수정 시각으로 신원 확인."""
    st = os.stat(path)
    return f"{os.path.abspath(path)}|{st.st_size}|{int(st.st_mtime)}"


def hash_of(*parts):
    h = hashlib.sha1()
    for p in parts:
        h.update(json.dumps(p, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8"))
    return h.hexdigest()[:16]


def run(cmd, **kw):
    """외부 명령 실행. 실패하면 사람이 읽을 수 있는 한국어 오류로 바꿔 올린다."""
    kw.setdefault("check", True)
    try:
        return subprocess.run(cmd, **kw)
    except subprocess.CalledProcessError as e:
        tail = ""
        if getattr(e, "stderr", None):
            tail = (e.stderr if isinstance(e.stderr, str) else e.stderr.decode("utf-8", "replace"))[-600:]
        raise StageError(f"명령 실행 실패({os.path.basename(str(cmd[0]))}, 종료 코드 {e.returncode}). {tail}".strip())
    except FileNotFoundError:
        raise StageError(f"'{cmd[0]}' 프로그램을 찾을 수 없습니다. 설치되어 있는지 확인해 주세요.")


class StageError(Exception):
    """사람이 읽을 수 있는 한국어 원인을 담는 오류."""


def probe_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        raise StageError(f"영상 길이를 읽을 수 없습니다: {path}")


def probe_video(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                        "-of", "json", path], capture_output=True, text=True)
    s = json.loads(r.stdout)["streams"][0]
    a, b = s["r_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), float(a) / float(b)


class Timer:
    def __init__(self):
        self.t0 = time.time()

    def __str__(self):
        d = time.time() - self.t0
        return f"{d:.0f}초" if d < 90 else f"{d / 60:.1f}분"
