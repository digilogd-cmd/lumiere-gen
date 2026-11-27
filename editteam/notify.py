# -*- coding: utf-8 -*-
"""작업이 끝나거나 멈추면 윈도우 알림(토스트). 대시보드를 안 보고 있어도 알 수 있게. 설정 '알림' 끄면 조용히.
PowerShell 기본 기능(Windows.UI.Notifications)만 써서 추가 설치가 없다. 실패해도 편집에는 영향 없음."""
import base64, subprocess, sys

APP = r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"


def toast(title, body):
    if sys.platform != "win32":          # 맥 = 알림 센터(plat.py)
        from .plat import toast as _t
        return _t(title, body)
    esc = lambda s: (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&apos;")
    xml = f'<toast><visual><binding template="ToastGeneric"><text>{esc(title)}</text><text>{esc(body)}</text></binding></visual></toast>'
    ps = ("[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;"
          "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null;"
          f"$x = New-Object Windows.Data.Xml.Dom.XmlDocument; $x.LoadXml('{xml}');"
          f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{APP}').Show([Windows.UI.Notifications.ToastNotification]::new($x))")
    enc = base64.b64encode(ps.encode("utf-16-le")).decode()
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", enc], capture_output=True, timeout=20,
                           creationflags=0x08000000)
        return r.returncode == 0
    except Exception:
        return False


def notify(P, state, msg):
    if not (P.cfg.get("알림") or {}).get("켜기", True):
        return
    title = {"done": "✔ 편집 완료", "waiting": "⏸ 확인할 차례예요", "error": "✖ 편집이 멈췄어요"}.get(state, "편집팀")
    toast(f"{title} — {P.name}", msg + "  (대시보드 localhost:8431)")
