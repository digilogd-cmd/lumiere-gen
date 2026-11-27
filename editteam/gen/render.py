# -*- coding: utf-8 -*-
"""생성형 영상·소리 부품.
- render_timeline: 샷(그림·영상 클립)을 시각표대로 이어 붙인 영상. 그림은 천천히 확대·이동(켄 번즈), 컷 사이 디졸브, 처음·끝 페이드.
  프레임을 파이썬(OpenCV)에서 직접 그려 ffmpeg 로 흘려보낸다 — 길이가 프레임 단위로 정확(소리와 길이 차 0).
- mix_voice_music: 목소리 + 음악(사이드체인 덕킹: 말하는 동안만 음악을 누름, 게이트 mix_music.py 방식). 목소리는 앞 여백만큼 늦추고
  영상 끝까지 apad(게이트 EP02 끝 8초 잘림 사고 방지).
- local_tts: AI Studio 를 못 쓸 때 윈도우 내장 한국어 음성(Microsoft Heami)으로 임시 내레이션.
- synth_pad: 음악을 못 받을 때 잔잔한 패드 합성(외부 곡 다운로드 안 함)."""
import math, os, re, subprocess, tempfile
import numpy as np

from ..core import StageError, probe_duration, run as sh


def _imread(path):
    import cv2
    im = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)
    if im is None:
        raise StageError(f"그림을 읽을 수 없습니다: {path}")
    return im


def cover(im, w, h):
    import cv2
    ih, iw = im.shape[:2]
    k = max(w / iw, h / ih)
    nw, nh = max(w, int(math.ceil(iw * k))), max(h, int(math.ceil(ih * k)))
    r = cv2.resize(im, (nw, nh), interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_CUBIC)
    x, y = (nw - w) // 2, (nh - h) // 2
    return r[y:y + h, x:x + w]


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


MOVES = ["in", "left", "out", "right"]
K = 1.25            # 바탕 그림을 화면보다 25% 크게 준비(확대해도 흐려지지 않게)
ZMAX = 1.12


class Still:
    """그림 한 장의 켄 번즈. u(0~1) -> 프레임."""

    def __init__(self, path, W, H, move):
        self.W, self.H, self.move = W, H, move
        self.B = cover(_imread(path), int(W * K), int(H * K))

    def frame(self, u):
        import cv2
        e = ease(u)
        W, H = self.W, self.H
        bw, bh = self.B.shape[1], self.B.shape[0]
        if self.move == "in":
            z = 1.0 + (ZMAX - 1.0) * e; dx = 0.0
        elif self.move == "out":
            z = ZMAX - (ZMAX - 1.0) * e; dx = 0.0
        else:
            z = 1.07; dx = (1 - 2 * e) if self.move == "left" else (2 * e - 1)
        ww, wh = bw / z, bh / z
        cx = bw / 2 + dx * (bw - ww) / 2 * 0.9
        cy = bh / 2
        s = W / ww
        M = np.float32([[s, 0, -(cx - ww / 2) * s], [0, s, -(cy - wh / 2) * s]])
        return cv2.warpAffine(self.B, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


class Clip:
    """영상 클립: 구간 길이에 맞춰 속도를 0.7~1.5배로 바꾸고 모자라면 마지막 프레임을 늘린 임시 파일을 만들어 차례로 읽는다."""

    def __init__(self, path, W, H, dur, fps, tmpdir):
        import cv2
        cd = probe_duration(path)
        f = min(1.5, max(0.7, dur / max(0.1, cd)))
        self.tmp = os.path.join(tmpdir, f"_clip_{abs(hash((path, dur))) % 10 ** 8}.mp4")
        vf = (f"setpts={f:.5f}*PTS,fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"tpad=stop_mode=clone:stop_duration={dur + 1:.3f},trim=duration={dur + 0.5:.3f},setsar=1")
        sh(["ffmpeg", "-y", "-v", "error", "-i", path, "-vf", vf, "-an", "-c:v", "libx264", "-crf", "14", "-preset", "fast", self.tmp],
           capture_output=True)
        self.cap = cv2.VideoCapture(self.tmp)
        self.last = None
        self.speed = f

    def next(self):
        ok, fr = self.cap.read()
        if ok:
            self.last = fr
        return self.last

    def close(self):
        self.cap.release()
        try:
            os.remove(self.tmp)
        except OSError:
            pass


def plan_segments(slots, dissolve):
    """slots: [(시작, 끝, 소스dict)] 이어진 구간 -> 보이는 시간(디졸브만큼 다음 구간과 겹침)."""
    segs = []
    for i, (s, e, src) in enumerate(slots):
        ee = e + (dissolve if i < len(slots) - 1 else 0)
        segs.append({"s": s, "e": ee, "src": src})
    return segs


def render_timeline(slots, out, W, H, fps=30, dissolve=0.4, fade_in=0.5, fade_out=1.2, progress=None):
    """slots: [(시작초, 끝초, {"kind": "image"|"video", "file":..., "move":...})] (0부터 빈틈없이). 반환: 프레임 수."""
    if not slots:
        raise StageError("이어 붙일 샷이 없습니다")
    T = slots[-1][1]
    N = int(round(T * fps))
    segs = plan_segments(slots, dissolve)
    tmpdir = os.path.dirname(os.path.abspath(out))
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
           "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out + ".part.mp4"]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    live = {}

    def src_of(i):
        if i not in live:
            sg = segs[i]
            if sg["src"]["kind"] == "video":
                live[i] = Clip(sg["src"]["file"], W, H, sg["e"] - sg["s"], fps, tmpdir)
            else:
                live[i] = Still(sg["src"]["file"], W, H, sg["src"].get("move", "in"))
        return live[i]

    def get(i, t):
        sg = segs[i]
        o = src_of(i)
        if isinstance(o, Clip):
            return o.next()
        return o.frame((t - sg["s"]) / max(1e-3, sg["e"] - sg["s"]))

    try:
        for n in range(N):
            t = n / fps
            act = [i for i, sg in enumerate(segs) if sg["s"] <= t < sg["e"]] or [len(segs) - 1]
            if len(act) == 1:
                fr = get(act[0], t)
            else:
                a, b = act[0], act[-1]
                fa, fb = get(a, t), get(b, t)
                al = min(1.0, max(0.0, (t - segs[b]["s"]) / max(1e-3, dissolve)))
                fr = (fa.astype(np.float32) * (1 - al) + fb.astype(np.float32) * al).astype(np.uint8)
            g = min(1.0, t / fade_in if fade_in else 1.0, (T - t) / fade_out if fade_out else 1.0)
            if g < 1.0:
                fr = (fr.astype(np.float32) * max(0.0, g)).astype(np.uint8)
            p.stdin.write(fr.tobytes())
            for i in [i for i in live if segs[i]["e"] < t - 0.1]:      # 다 쓴 소스 정리
                o = live.pop(i)
                if isinstance(o, Clip):
                    o.close()
            if progress and n % 60 == 0:
                progress(n / N)
        p.stdin.close()
        err = p.stderr.read().decode("utf-8", "replace")
        if p.wait() != 0:
            raise StageError("영상 조립 렌더 실패: " + err[-400:])
    finally:
        for o in live.values():
            if isinstance(o, Clip):
                o.close()
    os.replace(out + ".part.mp4", out)
    return N


# ---------------------------------------------------------------- 소리
def measure_lufs(path):
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", path, "-vn", "-af", "ebur128", "-f", "null", "-"], capture_output=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr.decode("utf-8", "replace"))
    return float(m[-1]) if m else None


DUCK = "threshold=0.02:ratio=9:attack=25:release=450:makeup=1"


def mix_voice_music(voice, music, T, lead, level, out, fade_in=2.0, fade_out=3.0):
    """-> out(48kHz 스테레오 wav, 길이 정확히 T초). music 이 None 이면 목소리만."""
    lead_ms = int(round(lead * 1000))
    vf = (f"[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,adelay={lead_ms}|{lead_ms},"
          f"apad=whole_dur={T:.3f},atrim=0:{T:.3f}")
    if not music:
        sh(["ffmpeg", "-y", "-v", "error", "-i", voice, "-filter_complex", vf + ",alimiter=limit=0.95[a]", "-map", "[a]",
            "-t", f"{T:.3f}", "-c:a", "pcm_s16le", "-ar", "48000", out], capture_output=True)
        return {"music_gain_db": None}
    vl, ml = measure_lufs(voice), measure_lufs(music)
    gain = ((vl if vl is not None else -20) + 20 * math.log10(max(0.05, level))) - (ml if ml is not None else -20)
    gain = max(-30.0, min(12.0, gain))
    fc = (vf + ",asplit=2[voice][key];"
          f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=0:{T:.3f},asetpts=N/SR/TB,volume={gain:.2f}dB,"
          f"afade=t=in:st=0:d={fade_in},afade=t=out:st={max(0.0, T - fade_out):.3f}:d={fade_out}[m];"
          f"[m][key]sidechaincompress={DUCK}[d];"
          f"[voice][d]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95,atrim=0:{T:.3f}[a]")
    sh(["ffmpeg", "-y", "-v", "error", "-i", voice, "-stream_loop", "-1", "-i", music, "-filter_complex", fc, "-map", "[a]",
        "-t", f"{T:.3f}", "-c:a", "pcm_s16le", "-ar", "48000", out], capture_output=True)
    return {"music_gain_db": round(gain, 1), "voice_lufs": vl, "music_lufs": ml}


def local_tts(text, out, voice="Heami", rate=0):
    """윈도우 내장 한국어 음성으로 임시 내레이션(wav). 'Microsoft Heami' — 이 PC에 설치 확인(기획서 7장)."""
    tdir = tempfile.mkdtemp(prefix="lumiere_tts_")
    tf = os.path.join(tdir, "t.txt")
    open(tf, "w", encoding="utf-8").write(text)
    ps = os.path.join(tdir, "s.ps1")
    open(ps, "w", encoding="utf-8-sig").write(
        "Add-Type -AssemblyName System.Speech\n"
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer\n"
        f"$v = $s.GetInstalledVoices() | Where-Object {{ $_.VoiceInfo.Name -like '*{voice}*' }} | Select-Object -First 1\n"
        "if ($v) { $s.SelectVoice($v.VoiceInfo.Name) }\n"
        f"$s.Rate = {int(rate)}\n"
        f"$s.SetOutputToWaveFile('{os.path.abspath(out)}')\n"
        f"$s.Speak([IO.File]::ReadAllText('{tf}', [Text.Encoding]::UTF8))\n"
        "$s.Dispose()\n")
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps], capture_output=True)
    if not os.path.exists(out) or os.path.getsize(out) < 2000:
        raise StageError("윈도우 음성 합성 실패: " + r.stderr.decode("cp949", "replace")[-300:])
    return out


def synth_pad(out, dur, sr=48000, seed=7):
    """잔잔한 패드(외부 곡 없이). 4개 화음을 천천히 바꾸며 부드럽게."""
    from ..media import write_wav
    rng = np.random.default_rng(seed)
    n = int(dur * sr)
    t = np.arange(n) / sr
    chords = [[220.0, 277.18, 329.63], [196.0, 246.94, 293.66], [174.61, 220.0, 261.63], [196.0, 246.94, 329.63]]
    seg = 8.0
    y = np.zeros(n, np.float32)
    for k in range(int(math.ceil(dur / seg)) + 1):
        c = chords[k % len(chords)]
        s0 = int(max(0, (k * seg - 1.5) * sr)); s1 = min(n, int((k + 1) * seg * sr + 1.5 * sr))
        if s0 >= n:
            break
        tt = t[s0:s1]
        env = np.minimum(1, np.minimum((tt - tt[0]) / 2.0, (tt[-1] - tt) / 2.0)).clip(0, 1)
        for f in c:
            for det in (-0.6, 0.6):
                y[s0:s1] += (np.sin(2 * np.pi * (f + det) * tt + rng.uniform(0, 6)) * env * 0.05).astype(np.float32)
    y = np.convolve(y, np.ones(24) / 24, mode="same")
    st = np.stack([y, np.roll(y, 300)], 1)
    st = st / max(1e-6, np.abs(st).max()) * 0.5
    write_wav(out, (st * 32767).astype(np.int16), sr)
    return out
