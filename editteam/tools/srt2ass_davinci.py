# -*- coding: utf-8 -*-
"""SRT -> ASS, 개발팀이 다빈치에서 넣는 롱폼 자막 스타일 그대로 (2026-10-03: "마지막 렌더링 때 자막 스타일을 내가 다빈치에서 넣는 스타일로,
크기와 배경 음영도 맞춰서").
실측(예전 영상 뉴스레터.mp4 vs 뉴스레터_무자막본.mp4 같은 프레임 차이, 1920x1080):
- 글꼴: 나눔바른고딕 Bold (후보 9종 중 글자 모양 일치도 최고 IoU 0.74), 흰색, 테두리·그림자 없음
- 글자 높이(한글 위~아래) 39px, 한 줄(줄바꿈 없이 길게)
- 박스: 검정(약 RGB 9) 불투명도 약 53%, 높이 58px(y 901~959), 좌우 여백 14~18px, 모서리 반경 약 8px, 가로 가운데
사용: python srt2ass_davinci.py 입력.srt 출력.ass   -> ffmpeg -vf "ass=출력.ass"
FS(libass 글자 크기)는 calibrate()로 실제 렌더 글자 높이가 39px이 되게 맞춘 값."""
import os, re, sys
from PIL import ImageFont

W, H = 1920, 1080
# 나눔바른고딕(OFL — 재배포 가능)을 kits/fonts 에 같이 넣어 둔다. 고객 PC에 설치돼 있지 않아도 되게(2026-10-07 출시 점검 A3)
KIT_FONTS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "kits", "fonts")
FONT_FILE = next((p for p in (os.path.join(KIT_FONTS, "NanumBarunGothicBold.ttf"), "C:/Windows/Fonts/NanumBarunGothicBold.ttf")
                  if os.path.exists(p)), os.path.join(KIT_FONTS, "NanumBarunGothicBold.ttf"))
FONT_NAME = "NanumBarunGothic"
FS = 48            # libass 크기 — 실측 보정: FS48에서 글자 높이 38px·폭 994px (다빈치 39px·997px)
PIL_PX = 43        # 박스 폭 계산용 PIL 크기
INK_K = 0.975      # libass FS48 실제 잉크 폭 / PIL 43 글자 폭 (994/1020)
BOX_TOP, BOX_H = 901, 58
PADL, PADR, R = 15, 17, 8
ALPHA = "&H6F&"    # 실제 영상 프레임에서 다빈치 박스 진하기에 맞춤(박스 여백 밝기 86.5 -> 다빈치 42.7, 0x6F 42.9). 측정 불투명도 약 53%
BOX_COLOR = "&H090909&"
TXT_COLOR = "&H00FFFFFF"   # 글자 색(&HAABBGGRR) — 팔레트로 바뀜
BOLD = 1
BS = chr(92)
try:
    FONT = ImageFont.truetype(FONT_FILE, PIL_PX)
except OSError:          # 글꼴이 없으면 쓰는 쪽(final.py)이 다른 한국어 글꼴로 바꿔 끼운다
    FONT = None


def configure(font_file=None, family=None, bold=None, fs=None, pil=None, ink_k=None, ink=None, box=None, box_a=None):
    """글꼴·색 바꾸기(LUMIÈRE 설정 자막.글꼴 · 디자인.팔레트 — editteam/design.py). 안 준 값은 그대로(다빈치 기본)."""
    global FONT_FILE, FONT_NAME, BOLD, FS, PIL_PX, INK_K, FONT, TXT_COLOR, BOX_COLOR, ALPHA
    if font_file and os.path.exists(font_file):
        FONT_FILE, FONT_NAME = font_file, family or FONT_NAME
        BOLD = BOLD if bold is None else int(bold)
        FS, PIL_PX, INK_K = fs or FS, pil or PIL_PX, ink_k or INK_K
        FONT = ImageFont.truetype(FONT_FILE, PIL_PX)
    hx = lambda c: "&H" + c.lstrip("#")[4:6].upper() + c.lstrip("#")[2:4].upper() + c.lstrip("#")[0:2].upper()
    if ink:
        TXT_COLOR = "&H00" + hx(ink)[2:]
    if box:
        BOX_COLOR = hx(box) + "&"
    if box_a is not None:
        ALPHA = f"&H{int(box_a):02X}&"


def fontsdir_filter():
    """ffmpeg ass 필터에 줄 fontsdir(kits/fonts) — 윈도우 경로의 ':' 를 필터 문법에 맞게 이스케이프."""
    return ":fontsdir='" + KIT_FONTS.replace(chr(92), "/").replace(":", chr(92) + ":") + "'"


def t(s):
    h, m, r = s.split(":"); sec, ms = r.replace(".", ",").split(",")
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000


def a(sec):
    sec = max(0, sec)
    return f"{int(sec // 3600)}:{int(sec % 3600 // 60):02d}:{sec % 60:05.2f}"


def rrect(w, h, r):
    k = r * 0.5523
    return (f"m {r} 0 l {w-r} 0 b {w-r+k:.1f} 0 {w} {r-k:.1f} {w} {r} l {w} {h-r} "
            f"b {w} {h-r+k:.1f} {w-r+k:.1f} {h} {w-r} {h} l {r} {h} "
            f"b {r-k:.1f} {h} 0 {h-r+k:.1f} 0 {h-r} l 0 {r} b 0 {r-k:.1f} {r-k:.1f} 0 {r} 0")


def head():
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Txt,{FONT_NAME},{FS},{TXT_COLOR},{TXT_COLOR},&H00000000,&H00000000,{BOLD},0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: Box,{FONT_NAME},{FS},&H00000000,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def events(cards):
    """cards: [(시작초, 끝초, 문장)] -> ASS 이벤트 줄들."""
    out = []
    for st, en, text in cards:
        text = " ".join(text.split())
        if not text:
            continue
        tw = FONT.getlength(text) * INK_K
        bw = int(round(tw + PADL + PADR)); x = int(round((W - bw) / 2))
        cy = BOX_TOP + BOX_H / 2 - 1  # 다빈치 글자 윗선 y 908에 맞춤
        out.append(f"Dialogue: 0,{a(st)},{a(en)},Box,,0,0,0,,{{{BS}pos({x},{BOX_TOP}){BS}an7{BS}1c{BOX_COLOR}{BS}1a{ALPHA}{BS}bord0{BS}shad0{BS}p1}}{rrect(bw, BOX_H, R)}{{{BS}p0}}")
        out.append(f"Dialogue: 1,{a(st)},{a(en)},Txt,,0,0,0,,{{{BS}pos({W // 2 + (PADL - PADR) // 2},{cy:.0f}){BS}an5}}{text}")
    return out


def read_srt(path):
    txt = open(path, encoding="utf-8-sig").read().strip()
    cards = []
    for blk in re.split(r"\n\s*\n", txt):
        ln = blk.strip().splitlines()
        if len(ln) < 3 or "-->" not in ln[1]:
            continue
        s, e = [x.strip() for x in ln[1].split("-->")]
        cards.append((t(s), t(e), " ".join(ln[2:])))
    return cards


def convert(src, dst):
    open(dst, "w", encoding="utf-8").write(head() + "\n".join(events(read_srt(src))) + "\n")


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])


def label_lines(items, accent="#ffc629", fs=58):
    """화면 오른쪽 위 큰 글자 띠(revise --label). items: [(시작초, 끝초, 글자)]. 색 띠(팔레트 강조색) 위 글자, 밝은 띠면 검정 글자.
    반환: (Style 줄, Dialogue 줄들) — head() 결과의 [Events] 앞에 Style 줄을 끼워 넣어 쓴다."""
    h = accent.lstrip("#")
    r_, g_, b_ = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    dark = 0.2126 * r_ + 0.7152 * g_ + 0.0722 * b_ > 0.6
    txt = "&H00111111" if dark else "&H00FFFFFF"
    box = "&H00" + h[4:6].upper() + h[2:4].upper() + h[0:2].upper()
    style = (f"Style: Label,{FONT_NAME},{fs},{txt},{txt},{box},{box},{BOLD},0,0,0,100,100,0,0,3,14,0,9,0,0,0,1")
    ev = [f"Dialogue: 2,{a(st)},{a(en)},Label,,0,0,0,,{{{BS}an9{BS}pos({W - 72},{68}){BS}fad(300,300)}}{t_}"
          for st, en, t_ in items if t_ and en > st]
    return style, ev
