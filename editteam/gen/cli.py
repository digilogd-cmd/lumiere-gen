# -*- coding: utf-8 -*-
"""생성형 명령(__main__ 에서 부름).
  python -m editteam run --gen --topic "주제" [--script 대본.hwp] [--length 90] [--style "따뜻한 수채화"] [--speakers 1] [--vertical]
  python -m editteam run --name <프로젝트>                      (브라우저 작업을 등록한 뒤 이어 가기)
  python -m editteam gen-jobs --name <프로젝트> [--all] [--done ID --file 파일|latest] [--fail ID --note 이유] [--start ID] [--reset ID] [--downloads]
  python -m editteam gen-revise --name <프로젝트> --scene 3 --text "새 대사"   /   --shot S05_내용 --prompt "새 프롬프트" """
import os, sys

from ..core import Project, StageError, jdump, jload, user_settings
from .. import runner
from . import jobs as J
from .common import gcfg, gen_name, recent_downloads


def add_run_args(r):
    r.add_argument("--gen", action="store_true", help="(예전 명령 호환 — 없어도 됨)")
    r.add_argument("--topic", default="", help="생성형: 주제")
    r.add_argument("--script", default="", help="생성형: 대본 파일(txt·md·docx·hwp·hwpx) — 내용은 그대로, 장면만 나눔")
    r.add_argument("--length", type=float, default=0, help="생성형: 목표 길이(초)")
    r.add_argument("--style", default="", help="생성형: 화풍 예) 따뜻한 수채화풍 일러스트")
    r.add_argument("--speakers", type=int, default=0, help="생성형: 화자 수(1~4)")
    r.add_argument("--vertical", action="store_true", help="세로 9:16")
    r.add_argument("--horizontal", action="store_true", help="가로 16:9 (안 주면 설정 '생성.세로' 기본값)")
    r.add_argument("--fixtures", default="", help="생성형 시험 모드: 브라우저 작업을 이 폴더의 시험 파일로 자동 완료")
    r.add_argument("--voice", choices=["browser", "local"], default=None, help="생성형: local = 윈도우 내장 음성으로 임시 내레이션")
    r.add_argument("--music", choices=["browser", "local"], default=None, help="생성형: local = 키트 배경음으로")


def add_subparsers(sub):
    gj = sub.add_parser("gen-jobs", help="생성형 브라우저 작업 목록 보기·등록(Claude가 크롬으로 만든 결과)")
    gj.add_argument("--name", required=True)
    gj.add_argument("--all", action="store_true", help="끝난 작업도 보기")
    gj.add_argument("--json", action="store_true", help="작업 목록을 JSON 으로")
    gj.add_argument("--done", default="", help="완료 등록할 작업 id")
    gj.add_argument("--file", default="", help="받은 파일 경로(latest = 크롬 다운로드 폴더의 가장 최근 파일)")
    gj.add_argument("--fail", default="", help="실패 표시할 작업 id")
    gj.add_argument("--note", default="", help="실패 이유·메모")
    gj.add_argument("--start", default="", help="진행 중으로 표시할 작업 id")
    gj.add_argument("--reset", default="", help="다시 대기로 돌릴 작업 id")
    gj.add_argument("--downloads", action="store_true", help="크롬 다운로드 폴더의 최근 파일 보기")
    gv = sub.add_parser("gen-revise", help="생성형 고치기: 장면 대사(-> 목소리부터 다시) / 샷 프롬프트(-> 그 샷 그림만 다시)")
    gv.add_argument("--name", required=True)
    gv.add_argument("--scene", default="", help="장면 번호")
    gv.add_argument("--text", default="", help="그 장면의 새 대사(줄바꿈은 \\n)")
    gv.add_argument("--shot", default="", help="샷 id 예) S05a_형제_공장")
    gv.add_argument("--prompt", default="", help="그 샷의 새 프롬프트(영어 한 문단)")
    gv.add_argument("--clear", action="store_true", help="고친 것 모두 지우기(처음 두뇌 답으로)")
    gv.add_argument("--no-run", action="store_true", help="반영만 하고 실행하지 않음")


def is_gen_project(name):
    if not name:
        return False
    from ..core import ROOT
    return bool((jload(os.path.join(ROOT, "work", name, "project.json"), {}) or {}).get("gen"))


def run(a):
    name = a.name or gen_name()
    P = Project(name)
    g = dict(P.meta.get("gen") or {})
    if a.gen:
        upd = {"topic": a.topic or g.get("topic", ""), "script_path": os.path.abspath(a.script) if a.script else g.get("script_path", ""),
               "length": a.length or g.get("length") or gcfg(P.cfg)["목표_초"], "style": a.style or g.get("style", ""),
               "speakers": a.speakers or g.get("speakers") or 1,
               "vertical": True if a.vertical else False if a.horizontal else bool(g.get("vertical", gcfg(P.cfg).get("세로", False))),
               "fixtures": os.path.abspath(a.fixtures) if a.fixtures else g.get("fixtures", "")}
        g.update(upd)
    if a.voice:
        g["voice"] = a.voice
    if a.music:
        g["music"] = a.music
    if not g:
        raise SystemExit(f"생성형 프로젝트가 아닙니다: {name}")
    P.meta["gen"] = g
    P.meta["mode"] = "gen"
    P.meta["upload"] = "never"
    if "settings_at_start" not in P.meta:
        P.meta["settings_at_start"] = user_settings()
    P.save_meta()
    P = Project(name)
    open(P.p("runner.pid"), "w").write(str(os.getpid()))
    print(f"생성형 시작: {name} — {g.get('topic') or os.path.basename(g.get('script_path', ''))}")
    res = runner.run_pipeline(P, until=a.until, force=tuple(x for x in a.force.split(",") if x), part="gen")
    if res == "waiting":
        print("\n" + J.table(P))
    return res


def jobs_cmd(a):
    P = Project(a.name)
    lim = int(gcfg(P.cfg)["재시도_한도"])
    if a.downloads:
        for f in recent_downloads(P.cfg, 15):
            import time
            print(f"{time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(f)))}  {f}")
        return
    try:
        if a.done:
            f = a.file
            if f in ("", "latest"):
                rec = recent_downloads(P.cfg, 1)
                if not rec:
                    raise StageError("크롬 다운로드 폴더에서 최근 파일을 못 찾았습니다. --file 로 경로를 주세요")
                f = rec[0]
            j = J.done(P, a.done, os.path.abspath(f), note=a.note)
            print(f"완료 등록: {j['id']} ← {f}\n  → {j['받은파일']} (워터마크: {j['워터마크']})\n  크롬 다운로드 폴더 원본: {j.get('다운로드_정리', '-')}")
        elif a.fail:
            j = J.fail(P, a.fail, a.note or "실패", limit=lim)
            print(f"{j['id']}: {j['상태']} (시도 {j['시도']}/{lim}) — {j['메모']}" + (" → 단계가 대체 방법을 씁니다" if j["상태"] == "포기" else " → 다시 해 보세요"))
        elif a.start:
            J.set_state(P, a.start, "진행", a.note); print(f"{a.start}: 진행 중")
        elif a.reset:
            J.set_state(P, a.reset, "대기", a.note or "다시 만들기"); print(f"{a.reset}: 대기로 돌림")
        elif a.json:
            import json
            print(json.dumps(J.load(P), ensure_ascii=False, indent=1))
        else:
            print(J.table(P, show_all=a.all))
            left = J.open_jobs(P)
            print(f"\n남은 작업 {len(left)}개." + (" 다 끝나면: python -m editteam bg run --name " + P.name if left else
                                             " 모두 끝났어요 — 이어 가기: python -m editteam bg run --name " + P.name))
    except StageError as e:
        print(f"✖ {e}")
        sys.exit(1)


def revise_cmd(a):
    P = Project(a.name)
    rv = {} if a.clear else (jload(P.p("생성_수정.json"), {}) or {})
    if a.scene:
        rv.setdefault("scenes", {})[str(int(a.scene))] = a.text.replace("\\n", "\n")
        print(f"장면 {a.scene} 대사를 바꿉니다 → 목소리부터 다시(목소리 작업이 다시 생겨요)")
    if a.shot:
        rv.setdefault("shots", {})[a.shot] = a.prompt
        print(f"샷 {a.shot} 프롬프트를 바꿉니다 → 그 샷 그림 작업만 다시")
    jdump(rv, P.p("생성_수정.json"))
    P.ev.emit(type="revise", gen=rv)
    if a.no_run:
        return
    open(P.p("runner.pid"), "w").write(str(os.getpid()))
    res = runner.run_pipeline(P, part="gen")
    if res == "waiting":
        print("\n" + J.table(P))
    sys.exit(0 if res in ("done", "waiting", "paused") else 1)
