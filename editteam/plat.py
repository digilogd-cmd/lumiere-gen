# -*- coding: utf-8 -*-
"""운영체제마다 다른 부품을 한 곳에(2026-11-14, 맥 버전 준비 — 개발팀 "뤼미에르 MAC 버전을 만들어보자").
윈도우 쪽은 예전 코드 그대로 옮겼다(동작이 바뀌면 안 됨). 맥(darwin) 쪽은 아직 이 PC에서 돌려 보지 못했다 — 맥 시험 결과로 고친다.
- 프로세스: pid_alive · pid_cmdline · kill_tree
- 열기: open_path(파일·폴더·주소) · reveal(파일을 폴더에서 골라 보여 주기)
- 화면 글자 읽기: ocr_list(목록.txt → 결과.tsv, 윈도우 = 내장 OCR, 맥 = Vision)
- 알림: toast
- 문서: pptx_to_png · doc_to_text
- 안내 문구: START_FILE(대시보드 켜는 파일 이름), PY(문서에 쓰는 파이썬 명령)"""
import os, subprocess, sys

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools")
START_FILE = "편집팀_시작.bat" if IS_WIN else "편집팀_시작.command"
NOWIN = 0x08000000 if IS_WIN else 0          # CREATE_NO_WINDOW


# ---------------------------------------------------------------- 프로세스
def pid_alive(pid):
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if not pid:
        return False
    if IS_WIN:
        r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True)
        return str(pid) in r.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    try:                                                  # 끝났는데 부모가 거두지 않은 프로세스(좀비)는 산 것으로 치지 않는다
        st = subprocess.run(["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True).stdout.strip()
        return bool(st) and not st.startswith("Z")
    except OSError:
        return True


def pid_cmdline(pid):
    """그 프로세스의 명령줄(없으면 빈 글자). pid 가 재사용된 남의 프로세스인지 가릴 때 쓴다."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return ""
    try:
        if IS_WIN:
            return subprocess.run(["powershell", "-NoProfile", "-Command",
                                   f"[Console]::OutputEncoding=[Text.Encoding]::UTF8; (Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"],
                                  capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
        out = subprocess.run(["ps", "-ww", "-p", str(pid), "-o", "command="], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
        import unicodedata
        return unicodedata.normalize("NFC", out)
    except OSError:
        return ""


def kill_tree(pid):
    """그 프로세스와 자식들을 멈춘다."""
    pid = int(pid)
    if IS_WIN:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        return
    import signal, time
    try:
        pg = os.getpgid(pid)
    except OSError:
        return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            if pg != os.getpgid(0):                       # 실행기는 새 세션으로 띄운다 → 그 묶음째로
                os.killpg(pg, sig)
            else:
                os.kill(pid, sig)
        except OSError:
            return
        for _ in range(20):
            if not pid_alive(pid):
                return
            time.sleep(0.1)


# ---------------------------------------------------------------- 열기
def open_path(target):
    """파일·폴더·주소를 기본 프로그램으로 연다."""
    if IS_WIN:
        os.startfile(target)
    elif IS_MAC:
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target])


def reveal(path):
    """탐색기(파인더)에서 그 파일을 골라 보여 준다."""
    if IS_WIN:
        subprocess.Popen(["explorer", "/select,", path])
    elif IS_MAC:
        subprocess.Popen(["open", "-R", path])
    else:
        open_path(os.path.dirname(path))


def mac_pick_files(title):
    """맥 파일 고르기 창(여러 개). 맥의 tkinter 는 서버의 작업 스레드에서 띄우면 죽는다 → 기본 스크립트 도구로. -> 경로 목록(취소면 빈 목록)."""
    import unicodedata
    q = (title or "").replace("\\", "\\\\").replace('"', '\\"')
    script = (f'set fs to choose file with prompt "{q}" with multiple selections allowed\n'
              'set out to ""\n'
              'repeat with f in fs\n'
              '  set out to out & POSIX path of f & linefeed\n'
              'end repeat\n'
              'return out')
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=600)
    except Exception:
        return []
    if r.returncode != 0:
        return []
    return [unicodedata.normalize("NFC", x) for x in r.stdout.decode("utf-8", "replace").splitlines() if x.strip()]


# ---------------------------------------------------------------- 화면 글자 읽기(OCR)
def ocr_list(lst, out, scale=None):
    """이미지 목록 파일(lst, 한 줄에 한 경로)을 읽어 out(tsv: 이름<TAB>x,y,w,h<TAB>글자, 마지막 줄 DONE)을 만든다. -> 오류 글(없으면 '')."""
    if IS_WIN:
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(TOOLS, "ocr_list.ps1"), "-List", lst, "-Out", out]
        if scale:
            cmd += ["-Scale", str(scale)]
        r = subprocess.run(cmd, capture_output=True)
        return "" if os.path.exists(out) else r.stderr.decode("cp949", "replace")[-300:]
    if IS_MAC:
        r = subprocess.run([sys.executable, os.path.join(TOOLS, "ocr_mac.py"), "--list", lst, "--out", out], capture_output=True)
        return "" if os.path.exists(out) else r.stderr.decode("utf-8", "replace")[-300:]
    return "이 운영체제에서는 화면 글자 읽기를 지원하지 않아요"


# ---------------------------------------------------------------- 알림
def toast(title, body):
    try:
        if IS_WIN:
            import base64
            app = r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"
            esc = lambda s: (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&apos;")
            xml = f'<toast><visual><binding template="ToastGeneric"><text>{esc(title)}</text><text>{esc(body)}</text></binding></visual></toast>'
            ps = ("[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;"
                  "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null;"
                  f"$x = New-Object Windows.Data.Xml.Dom.XmlDocument; $x.LoadXml('{xml}');"
                  f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{app}').Show([Windows.UI.Notifications.ToastNotification]::new($x))")
            enc = base64.b64encode(ps.encode("utf-16-le")).decode()
            r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", enc], capture_output=True, timeout=20,
                               creationflags=0x08000000)
            return r.returncode == 0
        if IS_MAC:
            q = lambda s: (s or "").replace("\\", "\\\\").replace('"', '\\"')
            r = subprocess.run(["osascript", "-e", f'display notification "{q(body)}" with title "{q(title)}"'], capture_output=True, timeout=20)
            return r.returncode == 0
    except Exception:
        pass
    return False


# ---------------------------------------------------------------- 문서
def pptx_to_png(pptx, out):
    """발표 자료를 슬라이드 PNG(1920x1080)로 out 폴더에. -> 오류 글(없으면 ''). 윈도우 = PowerPoint, 맥 = Keynote(기본 앱)."""
    if IS_WIN:
        ps = ("$app = New-Object -ComObject PowerPoint.Application; try { "
              f"$p = $app.Presentations.Open('{pptx}', $true, $false, $false); $p.Export('{out}', 'PNG', 1920, 1080); $p.Close() "
              "} finally { $app.Quit() }")
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], capture_output=True)
        return r.stderr.decode("cp949", "replace")[-300:]
    if IS_MAC:
        import shutil
        q = lambda s: s.replace("\\", "\\\\").replace('"', '\\"')
        sub = os.path.join(out, "_keynote")              # Keynote 는 없는 폴더 이름을 받아 그 안에 name.001.png … 로 내보낸다(slides.py 가 위로 옮김)
        shutil.rmtree(sub, ignore_errors=True)
        script = (f'tell application "Keynote"\n'
                  f'  set d to open (POSIX file "{q(pptx)}")\n'
                  f'  delay 2\n'
                  f'  export d to (POSIX file "{q(sub)}") as slide images with properties {{image format:PNG, skipped slides:false}}\n'
                  f'  close d saving no\n'
                  f'end tell')
        try:
            r = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=300)
        except Exception as e:
            return str(e)
        return r.stderr.decode("utf-8", "replace")[-300:]
    return "이 운영체제에서는 발표 자료를 그림으로 바꾸지 못해요"


def doc_to_text(path):
    """옛 워드(.doc) → 글자. 못 읽으면 None. 윈도우 = MS 워드, 맥 = textutil(기본 도구)."""
    if IS_WIN:
        out = os.path.splitext(path)[0] + "__lumiere_tmp.txt"
        ps = ("$w = New-Object -ComObject Word.Application; $w.Visible = $false; try { "
              f"$d = $w.Documents.Open('{path}', $false, $true); $d.SaveAs2('{out}', 7, $false, '', $false, '', $false, $false, $false, $false, $false, 65001); $d.Close($false) "
              "} finally { $w.Quit() }")
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], capture_output=True)
        if not os.path.exists(out):
            return None
        t = open(out, encoding="utf-8", errors="replace").read()
        os.remove(out)
        return t
    if IS_MAC:
        try:
            r = subprocess.run(["textutil", "-convert", "txt", "-stdout", "-encoding", "UTF-8", path], capture_output=True, timeout=120)
        except Exception:
            return None
        return r.stdout.decode("utf-8", "replace") if r.returncode == 0 and r.stdout else None
    return None
