# -*- coding: utf-8 -*-
"""아트고메 편집팀 실행기."""
import subprocess as _sp
import sys as _sys

# 윈도우: 실행기가 띄우는 ffmpeg·파워셸·npx·claude 등이 매번 새 콘솔 창을 열어 화면을 가로채지 않게,
# 모든 하위 프로세스에 '창 없음'(CREATE_NO_WINDOW)을 기본으로 붙인다(2026-10-03: "터미널 창이 껐다 켜졌다 해서 다른 작업을 못 한다").
if _sys.platform == "win32" and not getattr(_sp.Popen, "_editteam_nowindow", False):
    _orig_init = _sp.Popen.__init__

    def _init(self, *a, **kw):
        fl = kw.get("creationflags", 0) or 0
        if not fl & 0x00000008:                      # DETACHED_PROCESS 와는 같이 못 씀
            kw["creationflags"] = fl | 0x08000000    # CREATE_NO_WINDOW
        _orig_init(self, *a, **kw)
    _sp.Popen.__init__ = _init
    _sp.Popen._editteam_nowindow = True

# 맥·리눅스(2026-11-14 맥 버전 준비): 엔진 곳곳의 윈도우용 creationflags 는 여기서 한 번에 푼다.
#  - creationflags 는 윈도우에만 있는 인자(다른 OS 에선 오류) → 뺀다. '부모와 떨어진 프로세스'(0x200) 표시가 있었으면 새 세션으로.
#  - shell=True + 명령 목록(["npx", …])은 윈도우에선 통째로 실행되지만 다른 OS 에선 첫 낱말만 실행된다 → 목록이면 셸 없이.
if _sys.platform != "win32" and not getattr(_sp.Popen, "_editteam_posix", False):
    _orig_init_p = _sp.Popen.__init__

    def _init_p(self, *a, **kw):
        fl = kw.pop("creationflags", 0) or 0
        if fl & 0x00000200:
            kw.setdefault("start_new_session", True)
        args = a[0] if a else kw.get("args")
        if kw.get("shell") and isinstance(args, (list, tuple)):
            kw["shell"] = False
        _orig_init_p(self, *a, **kw)
    _sp.Popen.__init__ = _init_p
    _sp.Popen._editteam_posix = True

    if _sys.platform == "darwin":                   # Finder 에서 켠 앱은 PATH 에 Homebrew 가 없다 → ffmpeg·node·npx 를 못 찾는 일 방지
        import os as _os
        _p = _os.environ.get("PATH", "")
        _os.environ["PATH"] = _os.pathsep.join([d for d in ("/opt/homebrew/bin", "/usr/local/bin") if d not in _p.split(_os.pathsep)] + [_p])

    import unicodedata as _ud                     # 맥 파일 이름의 풀어 쓴 한글(NFD)을 붙여 쓴 한글(NFC)로 — 프로젝트 이름 비교가 어긋나지 않게
    _sys.argv[:] = [_ud.normalize("NFC", x) for x in _sys.argv]
