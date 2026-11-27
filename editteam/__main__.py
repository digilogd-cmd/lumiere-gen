# -*- coding: utf-8 -*-
"""뤼미에르 젠 실행기 명령.
  python -m editteam run --topic "주제" [--script 대본.hwp] [--length 90] [--style "화풍"] [--speakers 1] [--vertical]   (새로 만들기)
  python -m editteam run --name <프로젝트>                (브라우저 작업을 등록한 뒤 이어 가기)
  python -m editteam gen-jobs --name <프로젝트> [--done ID --file 파일] ...   (브라우저 작업 목록)
  python -m editteam gen-revise --name <프로젝트> --scene 3 --text "새 대사" / --shot S05a_내용 --prompt "..."
  python -m editteam status --name <프로젝트>
  python -m editteam selftest            (자가 검사: 시험 대본·시험 파일로 13단계, --vertical 이면 세로도)
  앞에 bg 를 붙이면 창 없이 뒤에서 돈다(대화창·대시보드용): python -m editteam bg run --topic ..."""
import argparse, os, sys

# 윈도우 콘솔에서 한국어가 깨지지 않게
for s in (sys.stdout, sys.stderr):
    try:
        s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .core import Project, jdump, jload
from . import runner


def background(argv):
    """python -m editteam bg <명령…> : 실행기를 창 없이 뒤에서 돌리고 바로 돌아온다(대화창 세션·대시보드용).
    출력은 work/<프로젝트>/runner.log."""
    import subprocess
    from .core import ROOT
    name = None
    if "--name" in argv:
        name = argv[argv.index("--name") + 1]
    elif argv and argv[0] == "run":            # 새로 만들기: 이름을 여기서 정해 둔다(대시보드가 바로 찾게)
        from .gen.common import gen_name
        name = gen_name()
        argv = argv + ["--name", name]
    d = os.path.join(ROOT, "work", name or "_기타"); os.makedirs(d, exist_ok=True)
    log = open(os.path.join(d, "runner.log"), "a", encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = None
    for fl in (0x08000000 | 0x00000200 | 0x01000000, 0x08000000 | 0x00000200):   # 부모와 떨어진 프로세스(창 없음)
        try:
            p = subprocess.Popen([sys.executable, "-m", "editteam", *argv], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, env=env, creationflags=fl)
            break
        except OSError:
            continue
    print(f"백그라운드에서 시작했습니다(프로젝트 {name}, PID {p.pid}). 진행은 대시보드에서 보입니다.")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "bg":
        return background(argv[1:])
    from .gen import cli as GC
    ap = argparse.ArgumentParser(prog="editteam", description="LUMIÈRE GEN System (뤼미에르 젠) — 실행기")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="새로 만들기(--topic/--script) 또는 이어 가기(--name)")
    r.add_argument("--name")
    r.add_argument("--until", help="이 단계까지만 실행")
    r.add_argument("--force", default="", help="다시 돌릴 단계(쉼표) — 그 뒤 단계도 함께 다시")
    GC.add_run_args(r)
    GC.add_subparsers(sub)
    c = sub.add_parser("continue", help="이어 가기(run --name 과 같음)")
    c.add_argument("--name", required=True)
    st = sub.add_parser("status", help="단계별 진행 상태")
    st.add_argument("--name", required=True)
    stp = sub.add_parser("selftest", help="자가 검사: 시험 대본·시험 파일로 13단계를 끝까지(브라우저 없이)")
    stp.add_argument("what", nargs="?", default="gen", choices=["gen"], help="(예전 명령 호환: selftest gen)")
    stp.add_argument("--vertical", action="store_true", help="세로 9:16 으로도")
    en = sub.add_parser("engine", help="엔진 관리: status(바뀐 것·되돌리기 지점) / save 이름(지금 상태 저장) / undo [지점](되돌리기) / reset [--all](공장 초기화) / factory 이름(지금을 출고 상태로 — 개발자용)")
    en.add_argument("action", choices=["status", "save", "undo", "reset", "factory"])
    en.add_argument("arg", nargs="?", default="")
    en.add_argument("--all", action="store_true", help="reset 때 내 스타일(설정·프리셋)도 비움(백업은 _보관 에)")
    pf = sub.add_parser("profile", help="내 스타일: show(노트 보기) / note \"덧붙일 말\"(예: 앞으로 화풍은 연필 스케치로) / greeting(첫 인사)")
    pf.add_argument("action", choices=["show", "note", "greeting"])
    pf.add_argument("text", nargs="?", default="")
    se = sub.add_parser("set", help="이 프로젝트에만 쓰는 설정: 키=값 (예: 생성.음악_크기=0.3). 바꾼 뒤 run --name 으로 다시 돌림")
    se.add_argument("--name", required=True)
    se.add_argument("pairs", nargs="*")
    se.add_argument("--clear", action="store_true", help="이 프로젝트 설정을 모두 지움")
    rq = sub.add_parser("request", help="만들 기능 목록에 남기기(지금 명령으로 못 하는 요청)")
    rq.add_argument("--name", default="")
    rq.add_argument("text")
    a = ap.parse_args(argv)

    if a.cmd == "profile":
        from . import profile as PR
        if a.action == "note":
            PR.add_note(a.text); print("내 스타일 노트에 덧붙였어요 — 다음 제작부터 제작팀이 이걸 보고 판단해요")
        elif a.action == "greeting":
            print(PR.greeting())
        else:
            print(PR.note() or "아직 내 스타일 노트가 없어요 — 대시보드에서 첫 만남을 해 주세요")
        return
    if a.cmd == "selftest":
        from .gen.selftest import run as _gst
        r = _gst(vertical=a.vertical)
        print(("✔ 자가 검사 통과" if r["ok"] else "✖ 자가 검사 실패") + f" ({r['sec']}초) · " +
              " · ".join(f"{k} {v.get('dur')}초 {v.get('lufs')} LUFS" for k, v in r.get("runs", {}).items()))
        for b in r["problems"]:
            print("  - " + b)
        sys.exit(0 if r["ok"] else 1)
    if a.cmd == "engine":
        from . import layers as L
        if a.action == "factory":
            print(f"지금 엔진을 출고 상태로 보관했어요(파일 {L.factory_save(a.arg or 'dev')}개)")
        elif a.action == "save":
            print(f"되돌리기 지점: {L.snapshot(a.arg or '직접 저장')}")
        elif a.action == "undo":
            sid = a.arg or (L.list_snapshots()[0]["id"] if L.list_snapshots() else "")
            if not sid:
                print("되돌리기 지점이 없어요"); return
            L.restore(sid); print(f"{sid} 상태로 되돌렸어요. 대시보드를 다시 켜 주세요.")
        elif a.action == "reset":
            L.reset(keep_style=not a.all); print("엔진을 공장 초기 상태로 돌렸어요" + ("(내 스타일은 그대로)" if not a.all else "(내 스타일은 _보관 으로 옮김)") + ". 대시보드를 다시 켜 주세요.")
        else:
            st = L.status()
            print(f"출고 상태: {st['factory']}")
            if st["changes"]:
                c = st["changes"]
                print(f"출고 상태와 다른 엔진 파일 {st['n_changed']}개 — 바뀜 {len(c['changed'])} · 새로 생김 {len(c['added'])} · 없어짐 {len(c['removed'])}")
                for k in ("changed", "added", "removed"):
                    for f in c[k][:15]:
                        print(f"  {dict(changed='바뀜', added='새로', removed='없어짐')[k]}  {f}")
            for x in st["snapshots"][:10]:
                print(f"  지점 {x['id']} · {x['label']} · 출고와 다른 파일 {x['diff']}개")
        return
    if a.cmd == "request":
        from .requests_box import add
        it = add(a.name, a.text)
        print(f"만들 기능 목록에 남겼습니다(#{it['id']}): {it['text']}")
        return
    if a.cmd == "run":
        if not (a.name or a.topic or a.script):
            ap.error("--topic 이나 --script(새로 만들기), 또는 --name(이어 가기)이 필요합니다")
        a.gen = bool(a.gen or a.topic or a.script)      # 예전 명령 호환: --gen 은 있어도 없어도 됨
        res = GC.run(a)
        sys.exit(0 if res in ("done", "waiting", "paused") else 1)
    if a.cmd == "gen-jobs":
        return GC.jobs_cmd(a)
    if a.cmd == "gen-revise":
        return GC.revise_cmd(a)
    P = Project(a.name)
    if a.cmd == "set":
        import json as _j
        cur = {} if a.clear else dict(P.meta.get("cfg") or {})
        for kv in a.pairs:
            if "=" not in kv:
                ap.error(f"키=값 형식이 아닙니다: {kv}")
            k, v = kv.split("=", 1)
            try:
                v = _j.loads(v)
            except ValueError:
                pass
            d = cur
            ks = k.strip().split(".")
            for x in ks[:-1]:
                d = d.setdefault(x, {})
            d[ks[-1]] = v
        P.meta["cfg"] = cur
        P.save_meta()
        print(f"이 프로젝트 설정: {_j.dumps(cur, ensure_ascii=False)} — 반영하려면 run --name {P.name}")
        return
    if a.cmd == "status":
        import json as _j
        last, run_state = {}, None
        if os.path.exists(P.p("events.jsonl")):
            for ln in open(P.p("events.jsonl"), encoding="utf-8"):
                e = _j.loads(ln)
                if e.get("type") == "stage":
                    last[e["stage"]] = e
                elif e.get("type") == "run":
                    run_state = e
        for idx, n, m in runner.stage_list("gen"):
            e = last.get(n, {})
            s_ = {"done": "완료", "error": "오류", "start": "진행 중", "progress": "진행 중"}.get(e.get("state"), "-")
            extra = f" {e.get('pct', '')}% {e.get('msg', '')}" if s_ in ("진행 중", "오류") else ""
            print(f"[{idx:02d}] {m.LABEL:12s} {s_}{extra}")
        if run_state:
            print(f"전체 상태: {run_state.get('state')} {run_state.get('msg', '')} ({run_state.get('t')})")
        return
    if a.cmd == "continue":
        open(P.p("runner.pid"), "w").write(str(os.getpid()))
        sys.exit(0 if runner.run_pipeline(P, part="gen") in ("done", "waiting", "paused") else 1)


if __name__ == "__main__":
    main()
