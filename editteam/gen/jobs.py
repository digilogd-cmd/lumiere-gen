# -*- coding: utf-8 -*-
"""브라우저 작업 목록 — 파이썬 실행기와 Claude(크롬)가 번갈아 일하는 접점.
파일: work/<프로젝트>/브라우저_작업.json
  실행기: 단계가 할 일을 ensure()로 적어 두고, 다 받기 전이면 '브라우저 작업 대기'로 멈춘다.
  Claude: python -m editteam gen-jobs --name <프로젝트>  로 남은 일을 보고, 브라우저_플레이북.md 대로 Flow·AI Studio에서 만든 뒤
          --done <id> --file <받은 파일>  로 등록(이때 이미지·영상은 워터마크를 지워 제자리에 둔다) -> run --name 으로 이어 간다.
상태: 대기 → 진행 → 완료 / 실패(다시 할 것) / 포기(재시도 한도를 넘음 — 단계가 대체 방법을 씀) / 취소(콘티에서 빠짐)"""
import glob, os, shutil, time

from ..core import StageError, jdump, jload, now

FILE = "브라우저_작업.json"
OPEN = ("대기", "진행", "실패")
KINDS = {"image": "이미지", "video": "영상", "voice": "목소리", "music": "음악"}
TOOLS = {"flow": "Google Flow(이미지·영상)", "aistudio": "Google AI Studio(음성 생성)", "flow_music": "Flow Music"}
KEYS = ("프롬프트", "레퍼런스_작업", "화면비", "부가")          # 이것이 바뀌면 다시 만들어야 하는 작업
HERE = os.path.dirname(os.path.abspath(__file__))


def path(P):
    return P.p(FILE)


def load(P):
    return jload(path(P), {"project": P.name, "jobs": []})


def save(P, data):
    data["updated"] = now()
    jdump(data, path(P))


def get(data, jid):
    return next((j for j in data["jobs"] if j["id"] == jid), None)


def _sig(j):
    return [j.get(k) for k in KEYS]


def ensure(P, kind, specs):
    """이 종류(kind)의 작업 목록을 specs 로 맞춘다. 내용(프롬프트·레퍼런스 등)이 그대로면 상태 유지, 바뀌면 다시 '대기'(옛 파일은 _old 로)."""
    data = load(P)
    want = {s["id"]: s for s in specs}
    for j in data["jobs"]:
        if j["종류"] != kind:
            continue
        if j["id"] not in want:
            if j["상태"] != "취소":
                j["상태"], j["메모"] = "취소", "콘티에서 빠짐"
            continue
        s = want.pop(j["id"])
        if _sig(j) != _sig(s):
            _archive(j)
            j.update(s)
            j.update({"상태": "대기", "시도": 0, "받은파일": None, "원본파일": None, "워터마크": None, "메모": "내용이 바뀌어 다시 만듦"})
        else:
            for k in ("순서", "장면", "샷", "설명", "받을위치", "먼저", "레퍼런스"):    # 표시용 값은 새 것으로
                if k in s:
                    j[k] = s[k]
            if j["상태"] == "취소":
                j["상태"] = "완료" if j.get("받은파일") and os.path.exists(j["받은파일"]) else "대기"
            if j["상태"] == "완료" and not (j.get("받은파일") and os.path.exists(j["받은파일"])):
                j.update({"상태": "대기", "메모": "받은 파일이 없어져 다시 받아야 함"})
    for s in want.values():
        j = {"상태": "대기", "시도": 0, "받은파일": None, "원본파일": None, "워터마크": None, "메모": "", "만든시각": now()}
        j.update(s)
        data["jobs"].append(j)
    data["jobs"].sort(key=lambda j: (j.get("순서", 999), j["id"]))
    save(P, data)
    return [j for j in data["jobs"] if j["종류"] == kind and j["상태"] != "취소"]


def _archive(j):
    for k in ("받은파일", "원본파일"):
        f = j.get(k)
        if f and os.path.exists(f):
            od = os.path.join(os.path.dirname(f), "_old")
            os.makedirs(od, exist_ok=True)
            shutil.move(f, os.path.join(od, time.strftime("%H%M%S_") + os.path.basename(f)))


def of_kind(P, kind):
    return [j for j in load(P)["jobs"] if j["종류"] == kind and j["상태"] != "취소"]


def open_jobs(P, kind=None):
    return [j for j in load(P)["jobs"] if j["상태"] in OPEN and (kind is None or j["종류"] == kind)]


def counts(P):
    c = {}
    for j in load(P)["jobs"]:
        c[j["상태"]] = c.get(j["상태"], 0) + 1
    return c


# ---------------------------------------------------------------- 받은 파일 등록
def _wm_image(src, dst):
    """Flow 그림 오른쪽 아래 ✦ 워터마크를 지우고 PNG로(gen/tools/wm_clean.py — 게이트 역산 방식 + 새 투명도 지도 + 테두리 메우기)."""
    from .tools.wm_clean import clean
    p = clean(src, dst)
    return f"제거함(역산+테두리, x{p['x']} y{p['y']} 세기 {p['gain']})" if p else "그림이 작아 그대로"


def _wm_video(src, dst):
    """Flow 영상(Veo) 워터마크: ① 시작 그림에 박혀 있던 ✦(카메라를 따라 움직임) ② 오른쪽 맨 아래 'Veo' 글자(고정).
    둘 다 오른쪽·아래 끝 10% 띠 안에 있어서(720p 실측: ✦ 가운데 91·93px, 'Veo' 글자 끝 37px) 그 띠를 잘라 내고 원래 크기로 되돌린다.
    역산(그림 방식)은 영상에서 어두운 별 자국·덜 지워짐이 생겼고, delogo(게이트 wm_remove_video)는 흐린 네모가 남았다(2026-10-08 비교)."""
    from ..core import probe_video, run as sh
    w, h, _ = probe_video(src)
    vf = f"crop=floor(iw*0.9/2)*2:floor(ih*0.9/2)*2:0:0,scale={w}:{h}:flags=lanczos,setsar=1"
    sh(["ffmpeg", "-y", "-v", "error", "-i", src, "-vf", vf, "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-c:a", "copy", dst], capture_output=True)
    if not os.path.exists(dst) or os.path.getsize(dst) < 1000:
        raise StageError(f"영상 워터마크 제거 실패: {src}")
    return "제거함(오른쪽·아래 10% 잘라 냄 — ✦·Veo 글자)"


def done(P, jid, src, wm=True, note=""):
    """받은 파일을 제자리로(원본은 '받은/' 폴더에 복사, 쓸 파일은 받을위치) + 이미지·영상은 워터마크 제거."""
    data = load(P)
    j = get(data, jid)
    if not j:
        raise StageError(f"작업 '{jid}' 가 없습니다. gen-jobs 로 목록을 보세요.")
    if not os.path.isfile(src):
        raise StageError(f"파일이 없습니다: {src}")
    dst = j["받을위치"]
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    raw_dir = os.path.join(os.path.dirname(os.path.dirname(dst)), "받은")
    os.makedirs(raw_dir, exist_ok=True)
    raw = os.path.join(raw_dir, os.path.splitext(os.path.basename(dst))[0] + os.path.splitext(src)[1].lower())
    if os.path.abspath(raw) != os.path.abspath(src):
        _archive({"받은파일": dst if os.path.exists(dst) else None,
                  "원본파일": j.get("원본파일") if j.get("원본파일") and os.path.abspath(j["원본파일"]) != os.path.abspath(src) else None})
        shutil.copy2(src, raw)
    kind = j["종류"]
    if kind == "image":
        if wm:
            mark = _wm_image(raw, dst)
        else:
            from PIL import Image
            Image.open(raw).convert("RGB").save(dst)
            mark = note or "필요 없음"
    elif kind == "video":
        if wm:
            mark = _wm_video(raw, dst)
        else:
            shutil.copy2(raw, dst); mark = note or "필요 없음"
    else:
        from ..core import run as sh
        if os.path.splitext(raw)[1] == os.path.splitext(dst)[1]:
            shutil.copy2(raw, dst)
        else:
            sh(["ffmpeg", "-y", "-v", "error", "-i", raw, dst], capture_output=True)
        mark = "해당 없음"
    import re
    flow_name = re.sub(r"_\d{14}$", "", os.path.splitext(os.path.basename(src))[0]).replace("_", " ")   # Flow가 붙인 제목(에셋 패널 이름)
    j.update({"상태": "완료", "받은파일": dst, "원본파일": raw, "워터마크": mark, "받은시각": now(), "가져온곳": src,
              "Flow이름": flow_name, "메모": note or j.get("메모", "")})
    # 크롬 다운로드 폴더에 받은 원본은 작업 폴더('받은/')로 복사가 끝났으니 지운다(2026-10-09: 다운로드 폴더에 쌓이지 않게).
    # 다운로드 폴더 안의 파일만 지우고, 시험 파일·다른 곳에서 가져온 파일은 그대로 둔다.
    j["다운로드_정리"] = _remove_download(P, src, raw)
    save(P, data)
    P.ev.emit(type="gen_job", id=jid, state="완료", kind=kind, file=P.rel(dst))
    return j


def _remove_download(P, src, raw):
    from .common import download_dir
    dd = download_dir(P.cfg)
    try:
        if not dd or os.path.normcase(os.path.dirname(os.path.abspath(src))) != os.path.normcase(os.path.abspath(dd)):
            return "다운로드 폴더 밖 — 그대로 둠"
        if not (os.path.isfile(raw) and os.path.getsize(raw) == os.path.getsize(src)):
            return "작업 폴더 복사본 확인 안 됨 — 그대로 둠"
        os.remove(src)
        return "지움(작업 폴더 '받은/'에 복사본)"
    except OSError as e:
        return f"못 지움({e.__class__.__name__}) — 그대로 둠"


def fail(P, jid, note, limit=2):
    data = load(P)
    j = get(data, jid)
    if not j:
        raise StageError(f"작업 '{jid}' 가 없습니다")
    j["시도"] = int(j.get("시도", 0)) + 1
    j["메모"] = note
    j["상태"] = "포기" if j["시도"] >= limit else "실패"
    save(P, data)
    P.ev.emit(type="gen_job", id=jid, state=j["상태"], kind=j["종류"], note=note)
    return j


def set_state(P, jid, state, note=""):
    data = load(P)
    j = get(data, jid)
    if not j:
        raise StageError(f"작업 '{jid}' 가 없습니다")
    j["상태"] = state
    if state == "대기":
        j["시도"] = 0
    if note:
        j["메모"] = note
    save(P, data)
    return j


# ---------------------------------------------------------------- 시험 모드(브라우저 없이) — kits/gen_selftest/fixtures
def autofill(P, kind, fixtures):
    """대기 중인 작업을 시험 파일로 자동 완료(자가 검사·시험 B). 시험 파일은 이미 워터마크를 지운 것만 둔다."""
    pats = {"image": ("images", (".png", ".jpg", ".jpeg")), "video": ("video", (".mp4",)), "voice": ("voice", (".wav",)),
            "music": ("music", (".wav", ".mp3", ".m4a"))}
    sub, exts = pats[kind]
    pool = sorted(f for f in glob.glob(os.path.join(fixtures, sub, "*")) if f.lower().endswith(exts))
    if kind == "image":
        sheets = sorted(f for f in glob.glob(os.path.join(fixtures, "sheets", "*")) if f.lower().endswith(exts))
    n = 0
    for i, j in enumerate([j for j in of_kind(P, kind)]):
        if j["상태"] not in OPEN:
            continue
        src_pool = sheets if (kind == "image" and j.get("부가", {}).get("시트") and sheets) else pool
        if not src_pool:
            fail(P, j["id"], "시험 파일 없음", limit=1)
            continue
        idx = int(j.get("순서", i)) if kind != "voice" else i
        done(P, j["id"], src_pool[idx % len(src_pool)], wm=False, note="시험 파일(이미 워터마크 제거됨)")
        n += 1
    return n


# ---------------------------------------------------------------- 보기
def table(P, show_all=False):
    data = load(P)
    L = []
    c = counts(P)
    L.append(f"브라우저 작업 — {P.name}: " + " · ".join(f"{k} {v}" for k, v in c.items()))
    for j in data["jobs"]:
        if not show_all and j["상태"] in ("완료", "취소"):
            continue
        L.append("")
        L.append(f"[{j['상태']}] {j['id']}  ({KINDS.get(j['종류'], j['종류'])} · {TOOLS.get(j['도구'], j['도구'])}"
                 + (f" · 장면 {j['장면']}" if j.get("장면") else "") + (f" · 시도 {j['시도']}" if j.get("시도") else "") + ")")
        if j.get("설명"):
            L.append(f"  설명: {j['설명']}")
        if j.get("먼저"):
            L.append(f"  먼저 끝낼 작업: {', '.join(j['먼저'])}")
        if j.get("레퍼런스"):
            names = {x["id"]: x.get("Flow이름") for x in data["jobs"]}
            L.append("  레퍼런스로 붙일 그림(Flow 에셋 패널에서 이 이름 → 미리보기로 확인 → 프롬프트에 추가, 순서대로): " + " / ".join(
                f"{r['이름']}" + (f" = Flow 이름 '{names.get(r.get('작업'))}'" if names.get(r.get("작업")) else " (아직 안 만듦)") for r in j["레퍼런스"]))
        for k, v in (j.get("부가") or {}).items():
            if k not in ("시트",):
                L.append(f"  {k}: {v}")
        L.append(f"  화면비: {j.get('화면비', '')}" if j.get("화면비") else "")
        L.append("  프롬프트:\n    " + str(j["프롬프트"]).replace("\n", "\n    "))
        if j.get("메모"):
            L.append(f"  메모: {j['메모']}")
        L.append(f"  등록: python -m editteam gen-jobs --name {P.name} --done {j['id']} --file \"<받은 파일>\"")
    return "\n".join(x for x in L if x is not None)
