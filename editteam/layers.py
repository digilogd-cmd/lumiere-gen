# -*- coding: utf-8 -*-
"""두 층: 뤼미에르 엔진(우리가 관리·업데이트) / 내 스타일(사용자 것). 되돌리기 지점과 공장 초기화.
(2026-10-07: "고객도 자기 스타일로 키워 가며 쓰고, 꼬이면 초기화 버튼 하나로 싹 풀 수 있게")

- 엔진: editteam/ · dashboard/ · kits/ · config.yaml · CLAUDE.md · README.txt · LUMIERE_GEN_시작.bat  ← 사용자의 Claude가 고쳐도 됨(되돌리기 가능)
- 내 스타일: 설정.json · 프리셋/ · 자막_교정표.yaml · 기능요청.jsonl · .env  ← 초기화해도 기본은 남김
- 작업물: work/  ← 절대 건드리지 않음

보관 위치: _보관/공장초기.zip (출고 상태 전체 + 파일 해시 목록) · _보관/되돌리기/<시각>_<이름>.zip (공장 상태와 달라진 엔진 파일만)."""
import hashlib, io, json, os, re, shutil, time, zipfile

from .core import ROOT

ENGINE_DIRS = ("editteam", "dashboard", "kits")
ENGINE_FILES = ("config.yaml", "CLAUDE.md", "README.txt", "LUMIERE_GEN_시작.bat", "LUMIERE_GEN_시작.command")   # .command = 맥
STYLE_PATHS = ("설정.json", "내_스타일.md", "프리셋", "자막_교정표.yaml", "내_로고", "기능요청.jsonl", ".env")
SKIP = re.compile(r"(__pycache__|\.pyc$|\.tmp$|\.log$|\.restore$|chat_session|_rows_.*\.json$|_t_rows\.json$|node_modules)")
KEEP = os.path.join(ROOT, "_보관")
FACTORY = os.path.join(KEEP, "공장초기.zip")
SNAPS = os.path.join(KEEP, "되돌리기")
MAX_SNAPS = 40


def engine_files():
    out = []
    for d in ENGINE_DIRS:
        for base, dirs, files in os.walk(os.path.join(ROOT, d)):
            dirs[:] = [x for x in dirs if not SKIP.search(x)]
            for f in files:
                p = os.path.join(base, f)
                rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
                if not SKIP.search(rel):
                    out.append(rel)
    out += [f for f in ENGINE_FILES if os.path.isfile(os.path.join(ROOT, f))]
    return sorted(out)


def _sha(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def manifest():
    return {rel: _sha(os.path.join(ROOT, rel)) for rel in engine_files()}


def factory_manifest():
    if not os.path.exists(FACTORY):
        return None
    with zipfile.ZipFile(FACTORY) as z:
        return json.loads(z.read("_manifest.json").decode("utf-8"))


def factory_save(version="dev"):
    """지금 엔진을 '공장 초기 상태'로 보관(출고·업데이트 때 개발자가 부름).
    이전 출고본은 _보관/이전출고/ 에 남긴다 — 되돌리기 지점은 출고본과의 차이만 담아서, 출고본을 덮으면 옛 지점으로 못 돌아가기 때문
    (2026-10-09 젠 정리 때 'gen-0.1-분리직후'를 덮어 정리 전 지점이 쓸모없어진 일)."""
    os.makedirs(KEEP, exist_ok=True)
    if os.path.exists(FACTORY):
        old = factory_info() or {}
        bak = os.path.join(KEEP, "이전출고")
        os.makedirs(bak, exist_ok=True)
        import shutil as _sh
        _sh.copy2(FACTORY, os.path.join(bak, f"공장초기_{old.get('version', '이전')}_{time.strftime('%Y%m%d_%H%M%S')}.zip"))
    man = manifest()
    tmp = FACTORY + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in man:
            z.write(os.path.join(ROOT, rel), rel)
        z.writestr("_manifest.json", json.dumps(man, ensure_ascii=False))
        z.writestr("_info.json", json.dumps({"version": version, "t": time.strftime("%Y-%m-%d %H:%M:%S")}, ensure_ascii=False))
    os.replace(tmp, FACTORY)
    return len(man)


def factory_info():
    if not os.path.exists(FACTORY):
        return None
    with zipfile.ZipFile(FACTORY) as z:
        return json.loads(z.read("_info.json").decode("utf-8"))


def changes():
    """공장 상태와 비교: 바뀐·새로 생긴·없어진 엔진 파일."""
    fm = factory_manifest() or {}
    cur = manifest()
    return {"changed": sorted(k for k in cur if k in fm and cur[k] != fm[k]),
            "added": sorted(k for k in cur if k not in fm),
            "removed": sorted(k for k in fm if k not in cur)}


# ---------------------------------------------------------------- 되돌리기 지점
def snapshot(label="직접 저장"):
    """지금 엔진 상태를 저장(공장 상태와 달라진 파일만 + 전체 목록). 같은 상태면 새로 안 만든다."""
    os.makedirs(SNAPS, exist_ok=True)
    fm = factory_manifest() or {}
    cur = manifest()
    last = list_snapshots()[:1]
    if last and last[0]["state"] == _state(cur):
        return last[0]["id"]
    sid = time.strftime("%Y%m%d_%H%M%S") + "_" + re.sub(r'[\\/:*?"<>|\s]+', "_", label)[:30]
    with zipfile.ZipFile(os.path.join(SNAPS, sid + ".zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for rel, h in cur.items():
            if fm.get(rel) != h:
                z.write(os.path.join(ROOT, rel), rel)
        z.writestr("_manifest.json", json.dumps(cur, ensure_ascii=False))
        z.writestr("_info.json", json.dumps({"label": label, "t": time.strftime("%Y-%m-%d %H:%M:%S"), "state": _state(cur),
                                             "diff": sum(1 for r, h in cur.items() if fm.get(r) != h)}, ensure_ascii=False))
    for old in list_snapshots()[MAX_SNAPS:]:
        os.remove(os.path.join(SNAPS, old["id"] + ".zip"))
    return sid


def _state(man):
    return hashlib.sha1(json.dumps(man, sort_keys=True).encode()).hexdigest()[:12]


def list_snapshots():
    if not os.path.isdir(SNAPS):
        return []
    out = []
    for f in sorted(os.listdir(SNAPS), reverse=True):
        if f.endswith(".zip"):
            try:
                with zipfile.ZipFile(os.path.join(SNAPS, f)) as z:
                    info = json.loads(z.read("_info.json").decode("utf-8"))
                out.append({"id": f[:-4], **info})
            except (zipfile.BadZipFile, KeyError):
                continue
    return out


def _write_engine(target_manifest, sources):
    """엔진 파일을 target_manifest 상태로 맞춘다. sources: [ZipFile,...] 앞에서부터 찾음."""
    cur = manifest()
    for rel, h in target_manifest.items():
        if cur.get(rel) == h:
            continue
        for z in sources:
            if rel in z.namelist():
                p = os.path.join(ROOT, rel)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with z.open(rel) as src, open(p + ".restore", "wb") as dst:
                    shutil.copyfileobj(src, dst)
                os.replace(p + ".restore", p)
                break
    for rel in cur:                      # 그 상태에는 없던 엔진 파일은 지운다(사용자 Claude가 새로 만든 파일 등)
        if rel not in target_manifest:
            try:
                os.remove(os.path.join(ROOT, rel))
            except OSError:
                pass


def restore(sid):
    """되돌리기 지점으로. 되돌리기 전 지금 상태도 지점으로 남긴다(되돌리기를 되돌릴 수 있게)."""
    path = os.path.join(SNAPS, sid + ".zip")
    if not os.path.exists(path) or not os.path.exists(FACTORY):
        raise FileNotFoundError("되돌리기 지점 또는 공장 초기 상태 파일이 없어요")
    snapshot("되돌리기 전 자동 저장")
    with zipfile.ZipFile(path) as zs, zipfile.ZipFile(FACTORY) as zf:
        target = json.loads(zs.read("_manifest.json").decode("utf-8"))
        _write_engine(target, [zs, zf])
    return len(target)


def reset(keep_style=True):
    """공장 초기화: 엔진을 출고 상태로. keep_style=False 면 내 스타일(설정·프리셋·교정표)도 비운다. work/(작업물)는 그대로."""
    if not os.path.exists(FACTORY):
        raise FileNotFoundError("공장 초기 상태 파일(_보관/공장초기.zip)이 없어요")
    snapshot("초기화 전 자동 저장")
    with zipfile.ZipFile(FACTORY) as zf:
        target = json.loads(zf.read("_manifest.json").decode("utf-8"))
        _write_engine(target, [zf])
    if not keep_style:
        bak = os.path.join(KEEP, "내스타일_" + time.strftime("%Y%m%d_%H%M%S"))
        os.makedirs(bak, exist_ok=True)
        for rel in STYLE_PATHS:
            if rel == ".env":            # 키 파일은 지우지 않는다(다시 넣기 번거롭고 비밀값이라 옮기지도 않음)
                continue
            p = os.path.join(ROOT, rel)
            if os.path.exists(p):
                shutil.move(p, os.path.join(bak, rel))
    return len(target)


def status():
    ch = changes() if os.path.exists(FACTORY) else None
    return {"factory": factory_info(), "changes": ch, "n_changed": (len(ch["changed"]) + len(ch["added"]) + len(ch["removed"])) if ch else None,
            "snapshots": list_snapshots()[:20]}


# ---------------------------------------------------------------- 내 스타일 내보내기·가져오기(스타일 팩)
EXPORTS = os.path.join(KEEP, "내보내기")
PACK_STYLE = ("설정.json", "내_스타일.md", "프리셋", "자막_교정표.yaml", "내_로고")     # .env(키)·기능요청은 절대 안 넣음


def export_style(name="내 스타일"):
    """스타일 팩(.zip): 내 설정·프리셋·자막 교정표 + 출고 상태와 다른 엔진 파일(내 Claude가 고친 코드)."""
    os.makedirs(EXPORTS, exist_ok=True)
    safe = re.sub(r'[\/:*?"<>|\s]+', "_", name)[:30] or "내스타일"
    path = os.path.join(EXPORTS, f"스타일팩_{safe}_{time.strftime('%Y%m%d_%H%M%S')}.zip")
    ch = changes() if os.path.exists(FACTORY) else {"changed": [], "added": [], "removed": []}
    files = []
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in PACK_STYLE:
            p = os.path.join(ROOT, rel)
            if os.path.isfile(p):
                z.write(p, "style/" + rel); files.append(rel)
            elif os.path.isdir(p):
                for f in os.listdir(p):
                    if os.path.isfile(os.path.join(p, f)):
                        z.write(os.path.join(p, f), f"style/{rel}/{f}"); files.append(f"{rel}/{f}")
        for rel in ch["changed"] + ch["added"]:
            if rel.endswith(".env") or "/.env" in rel:
                continue
            z.write(os.path.join(ROOT, rel), "engine/" + rel)
        z.writestr("_pack.json", json.dumps({"name": name, "t": time.strftime("%Y-%m-%d %H:%M:%S"), "factory": (factory_info() or {}).get("version"),
                                             "style": files, "engine": ch["changed"] + ch["added"], "removed": ch["removed"]}, ensure_ascii=False, indent=1))
    return path


def pack_info(path):
    with zipfile.ZipFile(path) as z:
        info = json.loads(z.read("_pack.json").decode("utf-8"))
    info["same_factory"] = info.get("factory") == (factory_info() or {}).get("version")
    return info


def import_style(path, style=True, engine=False):
    """스타일 팩 가져오기. 먼저 지금 상태를 저장하고, 덮어쓸 내 스타일 파일은 _보관/가져오기전_<시각>/ 에 백업.
    engine=True 면 팩 안의 코드도 엔진에 넣는다(다른 사람 팩은 믿을 수 있을 때만)."""
    snapshot("스타일 가져오기 전 자동 저장")
    info = pack_info(path)
    bak = os.path.join(KEEP, "가져오기전_" + time.strftime("%Y%m%d_%H%M%S"))
    n_style = n_eng = 0
    with zipfile.ZipFile(path) as z:
        for m in z.namelist():
            if m.startswith("style/") and style and not m.endswith("/"):
                rel = m[6:]
                if rel.endswith(".env") or ".." in rel.split("/") or os.path.isabs(rel) or rel.split("/")[0] not in PACK_STYLE:
                    continue                      # 내 스타일 자리 밖(경로 넘나들기 등)은 무시
                p = os.path.join(ROOT, rel)
                if os.path.exists(p):
                    os.makedirs(os.path.dirname(os.path.join(bak, rel)), exist_ok=True)
                    shutil.copy2(p, os.path.join(bak, rel))
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with z.open(m) as s_, open(p, "wb") as d_:
                    shutil.copyfileobj(s_, d_)
                n_style += 1
            elif m.startswith("engine/") and engine and not m.endswith("/"):
                rel = m[7:]
                top = rel.split("/")[0]
                if ".." in rel.split("/") or os.path.isabs(rel) or (top not in ENGINE_DIRS and rel not in ENGINE_FILES):      # 엔진 자리 밖으로는 못 쓰게
                    continue
                p = os.path.join(ROOT, rel)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with z.open(m) as s_, open(p + ".restore", "wb") as d_:
                    shutil.copyfileobj(s_, d_)
                os.replace(p + ".restore", p)
                n_eng += 1
    if engine:
        for rel in info.get("removed", []):
            if rel.split("/")[0] in ENGINE_DIRS and os.path.exists(os.path.join(ROOT, rel)):
                os.remove(os.path.join(ROOT, rel))
    return {"style": n_style, "engine": n_eng, "same_factory": info["same_factory"], "name": info.get("name")}
