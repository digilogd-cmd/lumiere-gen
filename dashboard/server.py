# -*- coding: utf-8 -*-
"""뤼미에르 젠 대시보드 로컬 서버 (http://localhost:8431, 이 PC에서만 접속).
- 실행기 진행 기록 work/<프로젝트>/events.jsonl 을 처음부터 읽어 SSE로 밀어 준다(새로고침해도 그대로 복원).
- 대본으로 만들기(/api/run), 브라우저 작업 표(/api/genjobs), 결과 파일·폴더 열기(/api/open), 설정·엔진 관리·대화창.
실행: python dashboard/server.py  (또는 LUMIERE_GEN_시작.bat)"""
import asyncio, json, os, shutil, subprocess, sys, tempfile, threading, time
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, FileResponse, HTMLResponse, JSONResponse, StreamingResponse
import uvicorn

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import editteam  # noqa: E402  하위 프로세스(ffmpeg·claude 등)가 새 콘솔 창을 띄우지 않게
WORK = os.path.join(ROOT, "work")
PORT = int(os.environ.get("EDITTEAM_PORT", "8431"))   # 뤼미에르 젠 = 8431 (에디트 8430과 동시에 켤 수 있게)
app = FastAPI(title="LUMIÈRE GEN System · 아트고메")

# ── 보안(2026-10-07 출시 점검 A10): 이 PC의 브라우저에서 이 대시보드 페이지로 연 요청만 받는다.
#   - Host 가 localhost/127.0.0.1 이 아니면 거절(DNS 리바인딩 방지)
#   - 바꾸는 요청(POST 등)은 Origin 이 이 대시보드일 때만 + JSON 본문만(다른 사이트의 몰래 보내는 폼·text/plain 요청 차단)
#   - 비밀 파일(.env·설정·대화 세션)은 /files 로 내주지 않음
from fastapi.responses import PlainTextResponse
_HOSTS = {"localhost", "127.0.0.1", "[::1]"}
_SECRET = (".env", "설정.json", "chat_session.txt", "chat_session_dev.txt")


@app.middleware("http")
async def local_only(request: Request, call_next):
    host = (request.headers.get("host") or "").rsplit(":", 1)[0].lower()
    if host not in _HOSTS:
        return PlainTextResponse("허용되지 않은 접속입니다", status_code=403)
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and origin.split("//", 1)[-1].rsplit(":", 1)[0].lower() not in _HOSTS:
            return PlainTextResponse("다른 사이트에서 온 요청은 받지 않습니다", status_code=403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return PlainTextResponse("다른 사이트에서 온 요청은 받지 않습니다", status_code=403)
        ct = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
        if ct and ct != "application/json":
            return PlainTextResponse("JSON 요청만 받습니다", status_code=415)
    if request.url.path.startswith("/files/") and os.path.basename(request.url.path).lower() in _SECRET:
        return PlainTextResponse("비밀 파일은 열 수 없습니다", status_code=403)
    return await call_next(request)


def pdir(name):
    d = os.path.realpath(os.path.join(WORK, name))
    if not d.startswith(os.path.realpath(WORK)) or not os.path.isdir(d):
        raise HTTPException(404, "프로젝트를 찾을 수 없습니다")
    return d


def safe_path(rel):
    """LUMIERE_GEN 폴더 안의 파일만 허용."""
    p = os.path.realpath(os.path.join(ROOT, rel))
    if not p.startswith(os.path.realpath(ROOT)):
        raise HTTPException(403, "허용되지 않은 경로")
    return p


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(open(os.path.join(HERE, "index.html"), encoding="utf-8").read(), headers={"Cache-Control": "no-store"})


@app.get("/manual")
def manual():
    """사용법 설명서(대시보드 아래 '📖 사용법', 설정 창 위)."""
    return FileResponse(os.path.join(HERE, "manual.html"), media_type="text/html", headers={"Cache-Control": "no-cache"})


@app.get("/design/{name}")
def design_file(name: str):
    """설정 창 디자인 미리보기 그림(팔레트·자막 글꼴·썸네일 색) — editteam/design_preview.py 가 만든 것."""
    if "/" in name or "\\" in name or ".." in name or not name.endswith(".jpg"):
        raise HTTPException(404)
    p = os.path.join(HERE, "design", name)
    if not os.path.isfile(p):
        raise HTTPException(404)
    return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "no-cache"})


@app.get("/crew/{name}")
def crew_file(name: str):
    """로봇 작업반 모션 그래픽(ES 모듈)과 미리보기 페이지."""
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(404)
    p = os.path.join(HERE, "crew", name)
    if not os.path.isfile(p):
        raise HTTPException(404)
    mt = "text/javascript" if name.endswith(".js") else "text/html"
    return FileResponse(p, media_type=mt, headers={"Cache-Control": "no-store"})


@app.get("/api/version")
def version():
    """화면 파일이 바뀌면 값이 바뀐다 -> 열려 있는 대시보드가 알아서 새로고침."""
    return {"v": int(os.path.getmtime(os.path.join(HERE, "index.html")))}


@app.get("/api/projects")
def projects():
    out = []
    for n in sorted(os.listdir(WORK)) if os.path.isdir(WORK) else []:
        ev = os.path.join(WORK, n, "events.jsonl")
        if os.path.exists(ev):
            out.append({"name": n, "mtime": os.path.getmtime(ev)})
    out.sort(key=lambda x: -x["mtime"])
    return out


@app.get("/api/events")
async def events(project: str, request: Request):
    """SSE: 기존 기록 전부 -> {"type":"_synced"} -> 새 줄이 생길 때마다."""
    path = os.path.join(pdir(project), "events.jsonl")

    async def gen():
        pos = 0
        sent_sync = False
        buf = ""
        while True:
            if await request.is_disconnected():
                break
            if os.path.exists(path):
                with open(path, "rb") as f:
                    f.seek(pos)
                    chunk = f.read()
                    pos = f.tell()
                if chunk:
                    buf += chunk.decode("utf-8", "replace")
                    *lines, buf = buf.split("\n")
                    for ln in lines:
                        if ln.strip():
                            yield f"data: {ln}\n\n"
            if not sent_sync:
                sent_sync = True
                yield 'data: {"type":"_synced"}\n\n'
            await asyncio.sleep(0.4)
    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.get("/api/eventlog")
def eventlog(project: str):
    """시연 재생용: 단계마다 '가장 최근에 실제로 돈(이전 결과 재사용이 아닌)' 기록만 모아 단계 순서대로 돌려준다.
    여러 번 이어 돌린 프로젝트도 처음부터 끝까지 한 번에 돈 것처럼 보이되, 모든 줄은 실제 기록 그대로."""
    path = os.path.join(pdir(project), "events.jsonl")
    evs = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    order, runs, cur = [], {}, None
    first_run = next((e for e in evs if e.get("type") == "run" and e.get("state") == "start" and e.get("stages")), None)
    if first_run:
        order = [s["id"] for s in first_run["stages"]]
    for e in evs:
        if e.get("type") == "stage" and e.get("state") == "start":
            cur = e["stage"]; runs.setdefault(cur, []).append([e])
            continue
        if cur and runs.get(cur):
            runs[cur][-1].append(e)
        if e.get("type") == "stage" and e.get("state") in ("done", "error") and e.get("stage") == cur:
            cur = None
    out = [dict(first_run, t=first_run["t"])] if first_run else []
    for sid in order:
        cands = [r for r in runs.get(sid, []) if any(x.get("type") == "stage" and x.get("state") == "done" for x in r)
                 and not any(x.get("type") == "stage" and x.get("state") == "done" and "이전 결과" in (x.get("msg") or "") for x in r)]
        if cands:
            out += cands[-1]
        else:   # 실제로 돈 기록이 없으면(건너뛴 단계 등) 완료 표시만
            done = [x for x in evs if x.get("type") == "stage" and x.get("stage") == sid and x.get("state") == "done"]
            if done:
                out.append(done[-1])
    last_done = [e for e in evs if e.get("type") == "run" and e.get("state") == "done"]
    if last_done:
        out.append(last_done[-1])
    return out


@app.get("/files/{rel:path}")
def files(rel: str, request: Request):
    p = safe_path(rel)
    if not os.path.isfile(p):
        raise HTTPException(404, "파일 없음")
    if p.lower().endswith((".mp4", ".mov", ".wav", ".m4a")):
        return stream_file(p, request)
    return FileResponse(p)


def stream_file(p, request):
    """영상은 조각마다 파일을 열고 바로 닫으며 보낸다 — 대시보드가 재생 중이어도 실행기가 같은 파일을 새로 바꿀 수 있게
    (윈도우는 열려 있는 파일을 바꾸지 못한다)."""
    size = os.path.getsize(p)
    rng = request.headers.get("range", "")
    start, end = 0, size - 1
    if rng.startswith("bytes="):
        a, _, b = rng[6:].partition("-")
        start = int(a) if a else max(0, size - int(b))
        end = int(b) if (a and b) else size - 1
    end = min(end, size - 1, start + 8 * 1024 * 1024 - 1)    # 한 번에 최대 8MB

    def gen():
        pos = start
        while pos <= end:
            try:
                with open(p, "rb") as f:
                    f.seek(pos)
                    chunk = f.read(min(1024 * 1024, end - pos + 1))
            except OSError:
                return
            if not chunk:
                return
            pos += len(chunk)
            yield chunk
    ctype = {"mp4": "video/mp4", "mov": "video/quicktime", "wav": "audio/wav", "m4a": "audio/mp4"}[p.rsplit(".", 1)[1].lower()]
    return StreamingResponse(gen(), status_code=206, media_type=ctype,
                             headers={"Content-Range": f"bytes {start}-{end}/{size}", "Accept-Ranges": "bytes",
                                      "Content-Length": str(end - start + 1), "Cache-Control": "no-store"})


def detached(cmd, log, env):
    """대시보드를 꺼도 편집이 계속되게: 실행기를 서버와 떨어진 별도 프로세스로(창 없음)."""
    base = 0x08000000 | 0x00000200          # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP (숨은 콘솔 하나 — 자식들도 새 창 안 뜸)
    for fl in (base | 0x01000000, base):     # + CREATE_BREAKAWAY_FROM_JOB (안 되면 빼고)
        try:
            return subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env, creationflags=fl)
        except OSError:
            continue
    return subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, env=env)


def spawn(args, project):
    d = pdir(project) if project else WORK
    log = open(os.path.join(d, "runner.log"), "a", encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = detached([sys.executable, "-m", "editteam", *args], log, env)
    return p.pid


def running(project):
    """이 프로젝트를 돌리는 실행기가 이미 있는지(간단히: runner.pid 파일 + 프로세스 확인)."""
    pf = os.path.join(pdir(project), "runner.pid")
    if not os.path.exists(pf):
        return False
    pid = int(open(pf).read().strip() or 0)
    r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True)
    return str(pid) in r.stdout


@app.post("/api/continue")
async def cont(req: Request):
    b = await req.json()
    if running(b["project"]):
        raise HTTPException(409, "실행기가 아직 돌고 있습니다.")
    pid = spawn(["continue", "--name", b["project"]], b["project"])
    open(os.path.join(pdir(b["project"]), "runner.pid"), "w").write(str(pid))
    return {"ok": True, "pid": pid}


@app.post("/api/run")
async def run(req: Request):
    b = await req.json()
    if True:                             # 뤼미에르 젠: 대본·주제로 만들기
        from editteam.gen.common import gen_name
        if not (b.get("topic") or b.get("script")):
            raise HTTPException(400, "주제나 대본 파일 중 하나는 있어야 해요")
        if b.get("script") and not os.path.exists(b["script"]):
            raise HTTPException(400, "대본 파일을 찾을 수 없어요: " + b["script"])
        name = b.get("name") or gen_name()
        if "/" in name or "\\" in name or ".." in name:
            raise HTTPException(400, "프로젝트 이름이 올바르지 않아요")
        os.makedirs(os.path.join(WORK, name), exist_ok=True)
        args = ["run", "--name", name, "--length", str(float(b.get("length") or 90)), "--speakers", str(int(b.get("speakers") or 1))]
        for k in ("topic", "script", "style"):
            if b.get(k):
                args += ["--" + k, str(b[k])]
        args += ["--vertical"] if b.get("vertical") else ["--horizontal"]
        pid = spawn(args, name)
        open(os.path.join(pdir(name), "runner.pid"), "w").write(str(pid))
        return {"ok": True, "pid": pid, "name": name}
    raise HTTPException(400, "뤼미에르 젠은 주제나 대본으로 만들어요(촬영본 편집은 뤼미에르 에디트에서)")


@app.get("/api/genjobs")
def gen_jobs(project: str):
    """생성형 브라우저 작업 목록(대시보드 표)."""
    path = os.path.join(pdir(project), "브라우저_작업.json")
    if not os.path.exists(path):
        return {"jobs": []}
    d = json.load(open(path, encoding="utf-8"))
    rel = lambda f: os.path.relpath(f, ROOT).replace("\\", "/") if f and os.path.exists(f) else None
    return {"jobs": [{"id": j["id"], "kind": j["종류"], "shot": j.get("샷"), "state": j["상태"], "desc": j.get("설명", ""), "note": j.get("메모", ""),
                      "preview": rel(j.get("받은파일")) if j["종류"] == "image" else None} for j in d.get("jobs", [])]}


@app.get("/api/brainstats")
def brain_stats(project: str):
    from editteam import brainstats as BS
    s = BS.summary(pdir(project))
    s["line"] = BS.line(pdir(project))
    return s


@app.get("/api/presets")
def get_presets():
    from editteam import settings as ST
    return ST.presets()


@app.post("/api/presets")
async def post_presets(req: Request):
    from editteam import settings as ST
    b = await req.json()
    fn = {"save": ST.preset_save, "load": ST.preset_load, "delete": ST.preset_delete}.get(b.get("action"))
    if not fn:
        raise HTTPException(400, "알 수 없는 동작")
    ok, msg = fn(b.get("name", ""))
    if not ok:
        raise HTTPException(400, msg)
    return {"ok": True, "name": msg}


@app.get("/api/requests")
def get_requests():
    from editteam import requests_box as RB
    from editteam import layers
    return {"items": RB.items(), "dev": dev_mode(), "team_email": RB.TEAM_EMAIL, "version": (layers.factory_info() or {}).get("version", "")}


@app.post("/api/requests")
async def post_requests(req: Request):
    from editteam import requests_box as RB
    b = await req.json()
    if not RB.set_status(b.get("id", ""), b.get("status", "")):
        raise HTTPException(400, "없는 요청이거나 상태 값이 맞지 않습니다")
    return {"ok": True}


@app.get("/api/settings")
def get_settings():
    from editteam import settings as ST
    return ST.read()


@app.post("/api/settings")
async def post_settings(req: Request):
    from editteam import settings as ST
    b = await req.json()
    ok, errs = ST.save(b.get("values", {}))
    if not ok:
        raise HTTPException(400, " / ".join(errs))
    return {"ok": True}


# ---------------------------------------------------------------- Claude 연결(싱크) · 첫 만남(온보딩)
CLAUDE_ST = {"checked": 0, "installed": None, "ok": None, "msg": "확인 전", "version": ""}


def check_claude(force=False):
    """Claude Code 가 있고 로그인돼서 실제로 답하는지(짧은 시험 호출, 10분 동안은 결과 재사용)."""
    if not force and time.time() - CLAUDE_ST["checked"] < 600 and CLAUDE_ST["ok"] is not None:
        return CLAUDE_ST
    exe = shutil.which("claude") or shutil.which("claude.cmd")
    CLAUDE_ST.update(checked=time.time(), installed=bool(exe))
    if not exe:
        CLAUDE_ST.update(ok=False, msg="Claude Code 가 설치돼 있지 않아요(README.txt 1단계)")
        return CLAUDE_ST
    try:
        v = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
        r = subprocess.run([exe, "-p", "OK 라고만 답하세요", "--output-format", "json", "--model", "haiku", "--tools", "",
                            "--no-session-persistence"], capture_output=True, timeout=120, cwd=tempfile.gettempdir())
        d = json.loads(r.stdout.decode("utf-8", "replace") or "{}")
        ok = not d.get("is_error") and bool(d.get("result"))
        CLAUDE_ST.update(ok=ok, version=v, msg="연결됨" if ok else f"로그인이 필요해요: {str(d.get('result') or r.stderr.decode('utf-8', 'replace'))[:120]}")
    except Exception as e:
        CLAUDE_ST.update(ok=False, msg=f"확인하지 못했어요: {type(e).__name__}")
    return CLAUDE_ST


@app.get("/api/claude")
def claude_status(force: int = 0):
    from editteam import profile as PR
    st = dict(check_claude(bool(force)))
    st.update(style_synced=PR.done(), leader=PR.leader())
    return st


@app.get("/api/onboarding")
def onboarding_get():
    from editteam import profile as PR
    return {"done": PR.done(), "leader": PR.leader(), "greeting": PR.greeting(), "questions": PR.questions()}


@app.post("/api/onboarding")
async def onboarding_post(req: Request):
    from editteam import profile as PR
    b = await req.json()
    if b.get("action") == "pick_logo":
        import asyncio

        def dlg():
            with PICK_LOCK:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
                try:
                    return filedialog.askopenfilename(parent=root, title="채널 로고(PNG)", filetypes=[("그림", "*.png *.jpg *.jpeg")])
                finally:
                    root.destroy()
        p = await asyncio.get_event_loop().run_in_executor(None, dlg)
        return {"ok": bool(p), "path": os.path.normpath(p) if p else ""}
    r = PR.save(b.get("answers") or {})
    if not r["ok"]:
        raise HTTPException(400, " / ".join(r["errors"]))
    return {"ok": True, **r}


@app.get("/api/engine")
def engine_status():
    """설정 창 '엔진 관리': 출고 상태와 다른 파일, 되돌리기 지점."""
    from editteam import layers
    st = layers.status()
    if st["changes"]:
        st["changes"] = {k: v[:30] for k, v in st["changes"].items()}
    from editteam.gen import selftest as gst          # 자가 검사(시험 대본·시험 파일로 13단계)
    st["selftest_gen"] = gst.last()
    st["selftest_gen_running"] = running("_자가검사_gen") if os.path.isdir(pdir("_자가검사_gen")) else False
    return st


def restart_server_later():
    """엔진 파일이 바뀌었으니 대시보드를 새 코드로 다시 켠다(2초 뒤 새 서버, 이 서버는 곧 종료)."""
    ps = (f"Start-Sleep -Seconds 2; Start-Process -WindowStyle Hidden -FilePath '{sys.executable}' "
          f"-ArgumentList 'dashboard\server.py' -WorkingDirectory '{ROOT}'")
    subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps], creationflags=0x08000000)
    threading.Timer(0.8, lambda: os._exit(0)).start()


@app.post("/api/engine")
async def engine_action(req: Request):
    """save(지금 저장) / restore(지점으로 되돌리기) / reset(공장 초기화). 편집이 돌고 있으면 막는다."""
    from editteam import layers
    b = await req.json()
    act = b.get("action")
    if act in ("restore", "reset") and any(running(n) for n in os.listdir(WORK) if os.path.isdir(os.path.join(WORK, n))):
        raise HTTPException(409, "편집이 돌고 있어요. 끝난 뒤에 해 주세요.")
    if act == "save":
        return {"ok": True, "id": layers.snapshot(b.get("label") or "직접 저장")}
    if act in ("selftest", "selftest_gen"):
        if os.path.isdir(pdir("_자가검사_gen")) and running("_자가검사_gen"):
            raise HTTPException(409, "생성형 자가 검사가 이미 돌고 있어요")
        os.makedirs(os.path.join(WORK, "_자가검사_gen"), exist_ok=True)
        pid = spawn(["selftest", "gen", "--vertical"], "_자가검사_gen")
        open(os.path.join(pdir("_자가검사_gen"), "runner.pid"), "w").write(str(pid))
        return {"ok": True, "started": True}
    if act == "export":
        path = layers.export_style(b.get("name") or "내 스타일")
        subprocess.Popen(["explorer", "/select,", path])
        return {"ok": True, "path": path}
    if act == "import_pick":
        import asyncio

        def dlg():
            with PICK_LOCK:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
                try:
                    return filedialog.askopenfilename(parent=root, title="가져올 스타일 팩(.zip)", filetypes=[("스타일 팩", "*.zip")])
                finally:
                    root.destroy()
        path = await asyncio.get_event_loop().run_in_executor(None, dlg)
        if not path:
            return {"ok": False}
        try:
            return {"ok": True, "path": os.path.normpath(path), "info": layers.pack_info(path)}
        except Exception:
            raise HTTPException(400, "스타일 팩이 아니에요(.zip 안에 _pack.json 이 없음)")
    if act == "import":
        r = layers.import_style(b["path"], style=bool(b.get("style", True)), engine=bool(b.get("engine")))
        if b.get("engine"):
            restart_server_later()
            return {"ok": True, "restart": True, **r}
        return {"ok": True, **r}
    if act == "restore":
        layers.restore(b["id"])
    elif act == "reset":
        layers.reset(keep_style=not b.get("all"))
    else:
        raise HTTPException(400, "알 수 없는 동작")
    restart_server_later()
    return {"ok": True, "restart": True}


@app.post("/api/deliver")
async def deliver(req: Request):
    """[📁 완성 폴더]: 완성 파일을 work/<프로젝트>/완성/ 에 모으고 탐색기로 연다."""
    from editteam.core import Project
    from editteam.deliver import collect
    b = await req.json()
    if not os.path.isdir(pdir(b["project"])):
        raise HTTPException(404, "프로젝트가 없어요")
    out, got = collect(Project(b["project"]))
    os.startfile(out)
    return {"ok": True, "path": out, "files": got}


@app.post("/api/open")
async def open_path(req: Request):
    b = await req.json()
    p = safe_path(b["path"])
    target = p if b.get("file") else (p if os.path.isdir(p) else os.path.dirname(p))
    if b.get("select") and os.path.isfile(p):
        subprocess.Popen(["explorer", "/select,", p])
    else:
        os.startfile(target)
    return {"ok": True}


# ---------------------------------------------------------------- 단계 3.5: 대화창 ↔ Claude Code headless 세션
import threading, shutil
CHAT_BUSY = {}
CHAT_SYS = ("너는 LUMIÈRE GEN(뤼미에르 젠) — 대본·주제로 영상을 만들어 내는 생성형 시스템 — 대시보드의 대화창이다. 이 폴더의 CLAUDE.md 규칙을 따른다. 지금 보고 있는 프로젝트: {p}. "
            "답은 쉬운 한국어로 3문장 안팎. 고를 일이 있으면 마지막 줄에 [선택: A | B] 형식. "
            "실행이 멈췄거나 오류를 물으면 먼저 work/{p}/runner.log 끝부분과 events.jsonl의 error 줄을 읽고 그 내용대로 설명할 것. "
            "허용되지 않은 명령은 승인창 없이 막힌다 — 막혔다고 '설치가 안 됐다' 같은 결론을 내리지 말 것. "
            "실행기 명령으로 안 되는 새 기능·코드 수정이 필요하면 python -m editteam request --name {p} \"요청 내용\" 으로 "
            "'만들 기능 목록'에 남기고, 사용자에게 '지금 기능으론 안 돼서 만들 기능 목록에 남겼어요. 설정에서 키우기 모드를 켜면 제가 직접 만들어 드릴 수 있어요'라고 알릴 것.")
ALLOWED = ["Read", "Glob", "Grep", "Bash(python -m editteam:*)", "Bash(python -m editteam *)"]
# 키우기 모드(설정 개발자.모드): 사용자의 Claude가 뤼미에르 코드를 직접 고쳐 자기 스타일로 키운다(고치기 전 자동 저장 — layers.py)
CHAT_SYS_DEV = ("너는 LUMIÈRE GEN(뤼미에르 젠)의 키우기 모드 대화창이다 — 사용자의 제작 스타일에 맞게 뤼미에르 젠 코드를 고쳐 키운다. 이 폴더의 CLAUDE.md '키우기 모드' 절을 따른다. "
                "지금 프로젝트: {p}. 제작팀 코드(editteam/, dashboard/, kits/)를 직접 고쳐 새 기능을 만들 수 있다. "
                "새 규칙은 프롬프트에만 쓰지 말고 품질 검사(editteam/gates.py)에서 재는 코드까지 넣을 것. 고친 뒤 python -m editteam selftest gen 으로 자가 검사할 것. "
                "업로드·원본 삭제·외부 전송·비밀값 출력은 하지 않는다. 답은 쉬운 한국어로 짧게.")
ALLOWED_DEV = ["Read", "Glob", "Grep", "Edit", "Write", "Bash(python:*)", "Bash(python *)", "Bash(pip install:*)", "Bash(ffmpeg:*)",
               "Bash(ffprobe:*)", "Bash(node --check:*)", "Bash(ls:*)", "Bash(cat:*)", "Bash(tail:*)", "Bash(grep:*)"]


def persona():
    """대화창 Claude = 뤼미에르 편집 팀장(이름·사용자 호칭은 설정, 내 스타일 노트가 있으면 그걸 기준으로)."""
    from editteam import profile as PR
    from editteam.core import load_config
    cfg = load_config()
    who = ((cfg.get("사용자") or {}).get("호칭") or "").strip()
    t = f"너는 뤼미에르 젠 제작 팀장 {PR.leader(cfg)}다(따뜻하고 자신감 있는 영화 현장 팀장 말투). "
    t += f"사용자를 '{who}'라고 부른다. " if who else "사용자를 정중하게 부른다. "
    t += ("사용자의 제작 취향(화풍·분위기·목소리·피할 소재)은 내_스타일.md(내 스타일 노트)에 있다 — 필요하면 읽고, 사용자가 새 취향을 말하면 python -m editteam profile note \"...\" 로 남긴다. "
          if PR.done() else "아직 첫 만남(내 스타일 설정)을 안 했다 — 기회가 되면 화면 위 '첫 만남 하기'를 권한다. ")
    return t


def dev_mode():
    try:
        from editteam.core import load_config
        return bool((load_config().get("개발자") or {}).get("모드"))
    except Exception:
        return False


def chat_log(project, **kw):
    kw.setdefault("t", time.strftime("%Y-%m-%dT%H:%M:%S"))
    with open(os.path.join(pdir(project), "chat.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")


def chat_worker(project, text):
    d = pdir(project)
    dev = dev_mode()
    sid_path = os.path.join(d, "chat_session_dev.txt" if dev else "chat_session.txt")   # 모드마다 다른 대화(권한이 다르므로)
    sid = open(sid_path).read().strip() if os.path.exists(sid_path) else ""
    exe = shutil.which("claude") or shutil.which("claude.cmd")
    if dev:
        try:                            # 코드를 고치기 전에 되돌리기 지점(설정 창 '엔진 관리'에서 되돌림)
            from editteam import layers
            layers.snapshot("대화 전 " + text[:24])
        except Exception:
            pass
        cmd = [exe, "-p", "--output-format", "stream-json", "--verbose", "--model", "opus",
               "--append-system-prompt", persona() + CHAT_SYS_DEV.format(p=project), "--permission-mode", "acceptEdits",
               "--allowedTools", *ALLOWED_DEV, "--disallowedTools", "WebFetch", "WebSearch"]
    else:
        cmd = [exe, "-p", "--output-format", "stream-json", "--verbose", "--model", "sonnet",
               "--append-system-prompt", persona() + CHAT_SYS.format(p=project), "--allowedTools", *ALLOWED,
               "--disallowedTools", "Write", "Edit", "WebFetch", "WebSearch"]
    if sid:
        cmd += ["--resume", sid]
    try:
        p = subprocess.Popen(cmd, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        p.stdin.write(text.encode("utf-8")); p.stdin.close()
        for raw in p.stdout:
            try:
                e = json.loads(raw.decode("utf-8", "replace"))
            except ValueError:
                continue
            if e.get("type") == "system" and e.get("subtype") == "init" and e.get("session_id"):
                open(sid_path, "w").write(e["session_id"])
            elif e.get("type") == "assistant":
                for c in e["message"].get("content", []):
                    if c.get("type") == "text" and c["text"].strip():
                        chat_log(project, role="assistant", text=c["text"])
                    elif c.get("type") == "tool_use":
                        inp = c.get("input", {})
                        chat_log(project, role="tool", text=inp.get("command") or inp.get("file_path") or inp.get("pattern") or c["name"])
            elif e.get("type") == "result":
                chat_log(project, role="done", cost=e.get("total_cost_usd"), error=e.get("is_error"))
        p.wait()
        if p.returncode not in (0, None):
            err = p.stderr.read().decode("utf-8", "replace")[-300:]
            chat_log(project, role="error", text="Claude 실행 오류: " + (err or f"종료 코드 {p.returncode}") +
                     " — Claude Code 로그인이 되어 있는지 확인해 주세요.")
    except Exception as ex:
        chat_log(project, role="error", text=f"대화창 연결 실패: {ex}")
    finally:
        CHAT_BUSY[project] = False


@app.post("/api/chat")
async def chat(req: Request):
    b = await req.json()
    project, text = b["project"], (b.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "보낼 말이 없습니다")
    if CHAT_BUSY.get(project):
        raise HTTPException(409, "앞 질문에 답하는 중이에요. 잠시만요.")
    CHAT_BUSY[project] = True
    chat_log(project, role="user", text=text)
    threading.Thread(target=chat_worker, args=(project, text), daemon=True).start()
    return {"ok": True}


@app.get("/api/chat/stream")
async def chat_stream(project: str, request: Request):
    path = os.path.join(pdir(project), "chat.jsonl")

    async def gen():
        pos, buf = 0, ""
        while not await request.is_disconnected():
            if os.path.exists(path):
                with open(path, "rb") as f:
                    f.seek(pos); chunk = f.read(); pos = f.tell()
                if chunk:
                    buf += chunk.decode("utf-8", "replace")
                    *lines, buf = buf.split("\n")
                    for ln in lines:
                        if ln.strip():
                            yield f"data: {ln}\n\n"
            yield f'data: {{"role":"_busy","busy":{str(bool(CHAT_BUSY.get(project))).lower()}}}\n\n'
            await asyncio.sleep(0.5)
    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


STT = {"model": None, "lock": threading.Lock()}


@app.post("/api/stt")
async def stt(req: Request):
    """마이크 녹음(webm 등) -> 로컬 faster-whisper 받아쓰기(인터넷 안 씀)."""
    import tempfile
    data = await req.body()
    td = tempfile.mkdtemp(prefix="et_stt_")
    src, wav = os.path.join(td, "in.webm"), os.path.join(td, "in.wav")
    open(src, "wb").write(data)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-ac", "1", "-ar", "16000", wav], check=True)

    def work():
        with STT["lock"]:
            if STT["model"] is None:
                from faster_whisper import WhisperModel
                STT["model"] = WhisperModel("small", device="cpu", compute_type="int8")
            segs, _ = STT["model"].transcribe(wav, language="ko", vad_filter=True)
            return " ".join(s.text.strip() for s in segs)
    text = await asyncio.get_event_loop().run_in_executor(None, work)
    shutil.rmtree(td, ignore_errors=True)
    return {"text": text}


PICK_LOCK = threading.Lock()


@app.post("/api/pick")
async def pick_files():
    """이 PC의 파일 선택 창을 띄워 고른 대본 파일 경로를 돌려준다(브라우저는 실제 경로를 못 주므로)."""
    import asyncio

    def dlg():
        with PICK_LOCK:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
            try:
                paths = filedialog.askopenfilenames(parent=root, title="대본 파일 고르기",
                                                    filetypes=[("대본", "*.txt *.md *.docx *.doc *.hwp *.hwpx *.rtf"), ("모든 파일", "*.*")])
            finally:
                root.destroy()
            return [os.path.normpath(x) for x in paths]
    paths = await asyncio.get_event_loop().run_in_executor(None, dlg)
    out = []
    for p in paths:
        try:
            it = {"path": p, "name": os.path.basename(p), "size": os.path.getsize(p), "mtime": os.path.getmtime(p)}
            out.append(it)
        except OSError:
            pass
    return out


threading.Thread(target=check_claude, daemon=True).start()     # 켜질 때 Claude 연결을 미리 확인(대시보드 '연결됨' 표시)


if __name__ == "__main__":
    print(f"LUMIÈRE GEN System (뤼미에르 젠): http://localhost:{PORT}")
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
