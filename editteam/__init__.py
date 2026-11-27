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
