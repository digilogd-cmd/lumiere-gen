# -*- coding: utf-8 -*-
"""자막 공통 도구: 교정표 + 문장경계 기준 청킹(SOP 11-0).
2026-09-27: 새 영상은 chunk() 대신 chunk_sentences()를 쓸 것(문장 끝에서 무조건 끊기 + 절 경계 분할).
줄 타이밍(실제 발화 시작/끝 실측, 숨 틈만 붙이기, 프레임 정확 SRT)은 예전 영상_srt.py 참고.
새 영상 작업 시 이 파일을 해당 영상 폴더로 복사해서 FIX/MERGE/DROP_TOKENS/DROP_RANGES만 그 영상에
맞게 채워 넣을 것 — chunk() 로직 자체는 웬만하면 건드리지 말고, 개선점이 생기면 여기(공통도구)에도
반드시 같이 반영해서 다음 영상부터 자동으로 적용되게 할 것."""
import json, os, re
WORK = os.path.dirname(os.path.abspath(__file__))

# 이 영상에서 ASR이 잘못 알아들은 단어 교정표. 예: {"엉모르고": "멋모르고"}
FIX = {}
# 연속한 두 토큰을 하나로 합쳐야 하는 경우: (앞토큰, 뒤토큰, 합친결과, (시작초, 끝초) 범위)
# 예: 한 단어가 ASR에서 매번 다르게 잘려 들리면 여기서 하나로 합친다.
MERGE = []
DROP_TOKENS = set()      # 군말이라 자막에서 통째로 뺄 단어(예: "어...")
DROP_RANGES = []         # 말 더듬(거짓 시작) 등 통째로 뺄 시간 구간: [(180.2, 182.0), ...]


def words():
    segs = json.load(open(os.path.join(WORK, "medium.json"), encoding="utf-8"))
    raw = [dict(w, w=w["w"].strip()) for s in segs for w in s["words"]]
    out, i = [], 0
    while i < len(raw):
        w = raw[i]
        hit = None
        for a, b, new, (lo, hi) in MERGE:
            if i + 1 < len(raw) and w["w"] == a and raw[i + 1]["w"] == b and lo <= w["s"] <= hi:
                hit = (new, raw[i + 1]["e"])
        if hit:
            out.append({"s": w["s"], "e": hit[1], "w": hit[0]}); i += 2; continue
        i += 1
        if w["w"] in DROP_TOKENS or any(a <= w["s"] < b for a, b in DROP_RANGES):
            continue
        t = FIX.get(w["w"], w["w"]).rstrip(".!")
        if t:
            out.append({"s": w["s"], "e": w["e"], "w": t})
    return out


# 문장이 실제로 끝나는 어미 패턴(SOP 11-0: 글자수가 아니라 이 지점에서 끊는다). "니다"는
# 습니다/ㅂ니다/합니다/됩니다/줍니다 등 격식체 전부를 포괄하기 위해 일반형으로 잡는다.
SENT_END_RE = re.compile(
    r"(니다|았다|었다|였다|한다|된다|없다|있다|같다|겠다|구나"
    r"|거든요|니까요|는데요|다고요|을까요|ㄹ까요|까요|군요|네요|구요|해요|이에요|예요|고요|어요|아요|여요|려요|게요|죠)$"
)
# 주의: 단독 "까"/"니까"는 넣지 않는다 — "관심이 많으니까 [다음 절]"처럼 연결어미로 쓰이는 경우가
# 훨씬 많아서 문장이 안 끝났는데 끊어버리는 오탐이 났다(2026-09-23 실제로 발견하고 수정).
CONNECTORS = {"그리고", "그래서", "그런데", "근데", "하지만", "그러니까", "그러면", "그러나", "그래도"}
# 2026-09-25 검수 중 발견: hard_max에 걸려 강제로 끊을 때 CONNECTORS(그리고/그래서 등, 절 맨 앞에
# 오는 접속사)만 찾다 보니, 그마저 없으면 "목적어를/주어가" 바로 뒤나 "관형형" 바로 뒤처럼 문법적으로
# 말이 안 끊기는 자리에서 그냥 잘라버렸다("AI를" | "접할 수 있지 않을까", "만드는" | "데는 하루..." 등
# 실제 방영본에서 여러 건 발견). 동사 연결어미(-고/-며/-서/-는데/-니까 등)로 끝나는 자리는 그 자체로
# 절 경계라 그 뒤에서 끊어도 문장이 안 깨진다 — 이 패턴도 강제 컷 지점 탐색에 포함시킨다.
# "~에서"(장소 조사)가 "-서"로 끝나 오탐되는 것만 부정형 lookbehind로 제외.
SAFE_BREAK_RE = re.compile(r"(고|며|는데|니까|면|거나|든지|길래|다가|(?<!에)서)$")
# "-고 싶다/싶어요", "-고 있다/있습니다"처럼 "-고" 뒤에 보조동사가 바로 붙는 경우는 같은
# 서술어 하나라 끊으면 안 된다 ("몇 개의 에이전트를 데리고 회사를 굴려보고" | "싶다 그런
# 사람들이..."에서 실제로 발견, 2026-09-24 "구사하고" | "있습니다..."(진행형) 추가 발견).
AUX_AFTER = re.compile(r"^(싶|있)")


PUNCT_TAIL = ".?!…,\"'”’)"


def base_word(word):
    """끝에 붙은 문장부호를 뗀 말. 2026-10-05 감사: large-v3 재전사는 "있어요." "거죠?"처럼 부호를 붙여 줘서
    `$`로 고정한 어미 패턴이 못 잡았다 -> 한 줄에 두 문장이 섞인 줄이 6.6% 나왔다."""
    return word.rstrip(PUNCT_TAIL)


# 접속사에 '요'만 붙은 말(근데요/그래서요)은 말을 이어 가는 군말이라 문장 끝이 아니다
_YO_NOT_END = {c + "요" for c in ("그리고", "그래서", "그런데", "근데", "그러니까", "그러면", "그래도", "하지만", "아니")}


def is_sentence_end(word):
    b = base_word(word)
    if SENT_END_RE.search(b):
        return True
    # "-요"로 끝나는 말은 거의 다 문장 끝(달라요·나와요·봐요 …) — 접속사+요만 뺀다
    if re.search(r"[가-힣]요$", b) and b not in _YO_NOT_END:
        return True
    # 받아쓰기가 마침표/물음표를 찍었고 어미가 종결형이면 문장 끝
    if re.search(r"[.?!]$", word.rstrip("\"'”’)")) and re.search(r"(다|요|죠|까|가|야|지|네|냐|래|자|라)$", b):
        return True
    return False


# 2026-09-27 전수검수에서 문장 끝인데 못 잡던 어미들: "안녕하세요", "라이브에요", "귀찮았나봐요",
# "생각하냐", "준비해라", "해보자", "아니다", "됐다", "싶다"(인용문 끝), "했다"
SENT_END_EXTRA_RE = re.compile(r"(세요|에요|봐요|봐봐|해라|하라|보자|하자|아니다|됐다|했다|싶다)$")
# "~냐/~야"는 "살아있냐 이게 살았냐 라는 앱"처럼 인용 안에서도 흔해서 뒤에 0.3초 이상 쉴 때만 문장 끝으로 본다
SENT_END_GATED_RE = re.compile(r"(냐|중이야)$")
# 문장 끝 어미 뒤에 이게 오면 인용이라 문장이 안 끝난 것("~겠구나 | 라는 걸" 방지)
QUOTE_HEAD_RE = re.compile(r"^(라는|라고|이라는|하면서|라며)")
LONG_PAUSE = 1.5  # 이 이상 쉬면 문장 중간이라도 끊는다(20초짜리 줄 방지)
# 그 뒤에서 끊어도 되는 연결어미 추가분(chunk_sentences 전용): -는지/-지만/-더니/-게끔/-아니라/-ㄴ데류/-ㄹ까
SAFE_BREAK_RE = re.compile(r"(고|며|데|니까|면|거나|든지|길래|다가|(?<!에)서|는지|지만|더니|게끔|아니라|(?<![니아])까)$")
# 그 뒤에서 끊으면 어색한 꼬리: 관형형(-은/-는/-한/-할/-된/-던 ...), 목적·소유·동반 조사, "~라고/~다고"
# ("-는/-은"은 주제 조사 "코덱스는"과 관형형 "돌리는"을 구분 못 해서 넣지 않음 - 넣으면 "거는 | 그 앱한테는"
#  같은 멀쩡한 자리를 막고 "하나 | 더"처럼 더 나쁜 데서 끊었다)
BAD_TAIL_RE = re.compile(r"(를|을|의|와|과|랑|한|할|된|될|던|운|인|라고|다고|라는|수가|수도|려는|하는|되는|있는|없는)$")
BAD_TAIL_WORDS = {"이", "그", "저", "이런", "그런", "저런", "어떤", "모든", "다른", "여러", "몇", "좀", "약간의",
                  "뭐", "막", "잘", "더", "안", "못", "또", "딱", "어떻게", "이렇게", "그렇게", "하나", "다시", "셋", "둘"}
# 줄 맨 앞에 오면 어색한 말: 의존명사(거/것/수/때/데/줄/만큼/식), 인용 조사, 앞 명사에 붙는 동사("업데이트 | 할")
# "거의"(부사)는 의존명사 "거"가 아니라서 제외
BAD_HEAD_RE = re.compile(r"^(거(?!의)|걸$|것|수$|수가|수도|때|데|줄|만큼|식으로|라는|라고|하는데|하면$"
                         r"|할$|한$|하는$|된$|될$|되는$|해$|하고$|있는$|있기|쓸$)")


def _text(c):
    return (" ".join(x["w"] for x in c)
            .replace(" ,", ",").replace(" %", "%").replace(" .", ".").replace(" -", "-"))


def chunk_sentences(ws, hard_max=34, min_side=6):
    """2026-09-27("문장이 끝나고 다음 문장이 시작되는 게 한 줄에 같이 있으면 이상하다")으로
    도입한 새 청킹. 기존 chunk()는 문장 끝이어도 글자수(16)나 pause(0.16초)가 안 차면 안 끊어서
    "그렇게 하고 있습니다 지금 클로드랑..."처럼 두 문장이 한 줄에 섞였다.
    1) 먼저 문장 끝 어미에서 무조건 끊는다(글자수·pause 무관) -> 한 줄에 두 문장이 절대 안 섞임.
    2) hard_max보다 긴 문장만 다시 나눈다. 나누는 자리 우선순위:
       0.5초 이상 쉰 곳 > 접속사 앞 > 연결어미(-고/-는데/-면 등) 뒤 > 0.25초 이상 쉰 곳 > 그 외,
       같은 순위면 양쪽 길이가 비슷한 곳. 양쪽 다 min_side자 이상(한두 글자 꼬리 방지)."""
    sents, cur = [], []
    for i, w in enumerate(ws):
        cur.append(w)
        nxt = ws[i + 1] if i + 1 < len(ws) else None
        gap = (nxt["s"] - w["e"]) if nxt else 999
        b = base_word(w["w"])
        end = is_sentence_end(w["w"]) or SENT_END_EXTRA_RE.search(b) \
            or (SENT_END_GATED_RE.search(b) and gap >= 0.3)
        if end and nxt and QUOTE_HEAD_RE.match(base_word(nxt["w"])):
            end = False
        if end or gap >= LONG_PAUSE:
            sents.append(cur); cur = []
    if cur:
        sents.append(cur)

    def split(c):
        if len(_text(c)) <= hard_max or len(c) < 2:
            return [c]
        best = None
        for j in range(1, len(c)):
            L, R = _text(c[:j]), _text(c[j:])
            if len(L) < min_side or len(R) < min_side:
                continue
            prev, nxt = c[j - 1]["w"], c[j]["w"]
            # "-고 싶다/있다"처럼 보조동사 앞은 한 서술어라 절대 안 끊는다
            if re.search(r"고$", prev) and AUX_AFTER.match(nxt):
                continue
            gap = c[j]["s"] - c[j - 1]["e"]
            bad = BAD_TAIL_RE.search(prev) or prev in BAD_TAIL_WORDS or BAD_HEAD_RE.match(nxt)
            # 문법적 절 경계를 pause보다 우선(말하다 멈칫한 자리가 "안티 | 전문인데"처럼 구 중간인 경우가 많았음)
            if bad:
                pri = 4
            elif prev in CONNECTORS:  # "근데"가 "-데"로 끝나 연결어미로 오인되던 것 방지(접속사 뒤는 우대 안 함)
                pri = 3
            elif nxt in CONNECTORS or prev.endswith(",") or (SAFE_BREAK_RE.search(prev) and not AUX_AFTER.match(nxt)):
                pri = 0
            elif gap >= 0.5:
                pri = 1
            elif gap >= 0.25:
                pri = 2
            else:
                pri = 3
            key = (pri, abs(len(L) - len(R)))
            if best is None or key < best[0]:
                best = (key, j)
        if best is None:
            return [c]
        j = best[1]
        return split(c[:j]) + split(c[j:])

    out = [p for s in sents for p in split(s)]
    # 접속사(그리고/그래서/근데 ...)가 줄 끝에 남으면 다음 줄 맨 앞으로 ("만들어지는데 그래서 |" 방지)
    for i in range(len(out) - 1):
        while (len(out[i]) > 1 and out[i][-1]["w"] in CONNECTORS
               and len(_text([out[i][-1]] + out[i + 1])) <= hard_max):
            out[i + 1].insert(0, out[i].pop())
    return [(c[0]["s"], c[-1]["e"], _text(c)) for c in out if c]


def chunk(ws, max_len=16, hard_max=34, pause_gap=0.16, join_gap=1.0):
    """실제로 끊는 지점은 문장이 끝나는 어미 + 발화 사이 pause다(글자수는 그 판단을 보조할 뿐).
    hard_max를 넘도록 길어져도 문장이 안 끝나면, 최근 접속사(그리고/그래서/근데 등) 앞이나 연결어미
    (-고/-며/-는데 등) 뒤에서 끊는 걸 우선하고, 그마저 없으면 그제서야 그 자리에서 강제로 끊는다."""
    out, cur = [], []

    def text(c):
        # 2026-09-24 발견: "53.6"/"50-60%"처럼 whisper가 소수점·범위 하이픈을 별도 토큰으로 잘라서
        # 붙이면 "53 .6"/"50 -60%"처럼 공백이 낀다 - 숫자 서식이므로 항상 붙인다.
        return (" ".join(x["w"] for x in c)
                .replace(" ,", ",").replace(" %", "%")
                .replace(" .", ".").replace(" -", "-"))

    for i, w in enumerate(ws):
        cur.append(w)
        t = text(cur)
        next_gap = (ws[i + 1]["s"] - w["e"]) if i + 1 < len(ws) else 999
        if is_sentence_end(w["w"]) and (next_gap > pause_gap or len(t) >= max_len):
            out.append(cur); cur = []
            continue
        if len(t) >= hard_max:
            cut_before = None  # 접속사 앞에서 끊기(접속사는 다음 줄로)
            for j in range(len(cur) - 1, 0, -1):
                if cur[j]["w"] in CONNECTORS:
                    cut_before = j
                    break
            cut_after = None  # 연결어미 뒤에서 끊기(그 단어까지는 이번 줄에)
            for j in range(len(cur) - 1, 0, -1):
                if SAFE_BREAK_RE.search(cur[j]["w"]) and not (j + 1 < len(cur) and AUX_AFTER.match(cur[j + 1]["w"])):
                    cut_after = j
                    break
            before_len = cut_before if (cut_before and cut_before >= 2) else -1
            after_len = (cut_after + 1) if (cut_after is not None and cut_after >= 1) else -1
            if before_len < 0 and after_len < 0:
                out.append(cur); cur = []
            elif before_len >= after_len:
                out.append(cur[:before_len]); cur = cur[before_len:]
            else:
                out.append(cur[:after_len]); cur = cur[after_len:]
    if cur:
        out.append(cur)
    # 접속사(그리고/그래서 등)가 줄 맨 끝에 덩그러니 남는 경우 다음 줄 맨 앞으로 옮긴다
    # (접속사는 원래 다음 절을 여는 말이라 끝에 남으면 어색하다 — 검수 중 실제로 여러 건 발견).
    for i in range(len(out) - 1):
        while len(out[i]) > 1 and out[i][-1]["w"] in CONNECTORS:
            out[i + 1].insert(0, out[i].pop())
    for i in range(len(out) - 1):
        while len(out[i]) > 1 and len(out[i][-1]["w"]) <= 1 and len(text([out[i][-1]] + out[i + 1])) <= hard_max + 6:
            out[i + 1].insert(0, out[i].pop())
    result = [(c[0]["s"], c[-1]["e"], text(c)) for c in out if c]
    # 2026-09-25: 다빈치에서 보니 줄 사이가 뜨면 자막이 있다 없다 깜빡여서 정신없다 —
    # 다음 줄까지 간격이 1초 미만이면(진짜 긴 pause가 아니면) 이번 줄 끝을 다음 줄 시작 직전까지
    # 늘려서 안 떨어지게 붙인다. 1초 이상 벌어진 건 진짜 쉬는 구간이니 그대로 둔다.
    for i in range(len(result) - 1):
        a, b, t = result[i]
        next_start = result[i + 1][0]
        if next_start - b < join_gap:
            result[i] = (a, next_start, t)
    return result
