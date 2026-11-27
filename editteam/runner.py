# -*- coding: utf-8 -*-
"""단계 순서대로 실행 + 이어하기.
단계마다 stage_XX_이름/done.json 에 입력 해시를 남기고, 다음 실행 때 해시가 같으면 건너뛴다.
해시 = 단계 이름·버전 + 그 단계가 밝힌 입력(설정값·수정 요청 등) + 앞 단계(DEPS)의 해시."""
import importlib, os, time, traceback
from .core import Project, StageError, hash_of, jdump, jload, Timer, ts_long

from .parts import PARTS
ORDER = PARTS["gen"]["order"]


def stage_mod(name):
    return importlib.import_module(f".stages.{name}", __package__)


def stage_list(part="gen"):
    return [(i + 1, n, stage_mod(n)) for i, n in enumerate(PARTS[part]["order"])]


def stage_hash(P, name, cache):
    if name in cache:
        return cache[name]
    m = stage_mod(name)
    deps = [stage_hash(P, d, cache) for d in getattr(m, "DEPS", [])]
    h = hash_of(name, getattr(m, "VERSION", 1), m.inputs(P) if hasattr(m, "inputs") else None, deps)
    cache[name] = h
    return h


def run_pipeline(P, until=None, force=(), part="gen"):
    ev = P.ev
    total = Timer()
    cache = {}
    if not P.meta.get("started"):
        P.meta["started"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        P.save_meta()
    ev.emit(type="run", state="start", project=P.name, screen=os.path.basename(P.meta.get("screen", "")),
            face=os.path.basename(P.meta.get("face", "")), mode=P.meta.get("mode"), upload=P.meta.get("upload"),
            part=part, part_label=PARTS[part]["label"],
            stages=[{"id": n, "label": m.LABEL} for _, n, m in stage_list(part)])
    forced = set(force)
    for idx, name, m in stage_list(part):
        d = P.stage_dir(idx, name)
        h = stage_hash(P, name, cache)
        if any(dp in forced for dp in getattr(m, "DEPS", [])):     # --force 한 단계의 뒤 단계도 다시(2026-10-18: 대본만 다시 짜고 콘티는 옛것 그대로 쓰던 버그)
            forced.add(name)
        done = jload(os.path.join(d, "done.json"))
        ev.stage_name = name
        if getattr(m, "SKIP_IF", None) and m.SKIP_IF(P):
            ev.stage(name, "done", 100, f"{m.LABEL} — 이번 모드에선 건너뜀")
            jdump({"hash": h, "summary": {"skipped": True}}, os.path.join(d, "done.json"))
            continue
        if done and done.get("hash") == h and name not in forced:
            ev.stage(name, "done", 100, f"{m.LABEL} — 이전 결과 사용")
            if hasattr(m, "replay"):
                m.replay(P, d, done.get("summary", {}))
            continue
        print(f"\n▶ [{idx:02d}] {m.LABEL}", flush=True)
        ev.stage(name, "start", 0, m.LABEL)
        t = Timer()
        try:
            summary = m.run(P, d) or {}
        except Checkpoint as c:
            ev.stage(name, "progress", 100, str(c))
            ev.checkpoint("waiting", str(c))
            ev.emit(type="run", state="waiting", msg=str(c), part=part)
            print(f"\n⏸ 중간 점검: {c}", flush=True)
            _notify(P, "waiting", str(c))
            return "waiting"
        except StageError as e:
            ev.stage(name, "error", None, str(e))
            ev.emit(type="run", state="error", stage=name, msg=str(e), part=part)
            print(f"\n✖ {m.LABEL} 실패: {e}", flush=True)
            _notify(P, "error", f"{m.LABEL}: {e}")
            return "error"
        except Exception as e:  # 예상 못 한 오류도 한국어 안내 + 원문 꼬리
            tb = traceback.format_exc()
            open(os.path.join(d, "error.txt"), "w", encoding="utf-8").write(tb)
            msg = f"예상하지 못한 오류가 났습니다({type(e).__name__}: {e}). 자세한 내용: {P.rel(os.path.join(d, 'error.txt'))}"
            ev.stage(name, "error", None, msg)
            ev.emit(type="run", state="error", stage=name, msg=msg, part=part)
            print(tb, flush=True)
            _notify(P, "error", f"{m.LABEL}: 예상하지 못한 오류")
            return "error"
        jdump({"hash": h, "summary": summary, "sec": round(time.time() - t.t0, 1)}, os.path.join(d, "done.json"))
        ev.stage(name, "done", 100, f"{m.LABEL} 완료 ({t})")
        if until and name == until:
            ev.emit(type="run", state="paused", msg=f"{m.LABEL}까지 실행", part=part)
            return "paused"
    try:                                    # 완성 파일을 work/<프로젝트>/완성/ 한 곳에 모음
        from .deliver import collect
        cdir, _got = collect(P)
        ev.output("deliver", P.rel(cdir), "완성 폴더")
        print(f"  완성 폴더: {cdir}", flush=True)
    except Exception as e:
        ev.log(f"완성 폴더 정리 실패(결과 파일은 그대로 있어요): {e}", "warn")
    ev.emit(type="run", state="done", msg=f"{PARTS[part]['label']} 완료 ({total})", part=part)
    print(f"\n✔ 전체 완료 ({total})", flush=True)
    _notify(P, "done", f"{PARTS[part]['label']} 완료 ({total})")
    return "done"


def _notify(P, state, msg):
    if P.meta.get("selftest"):          # 자가 검사는 윈도우 알림 안 띄움
        return
    try:
        from .notify import notify
        notify(P, state, msg)
    except Exception:
        pass


class Checkpoint(Exception):
    """중간 점검에서 멈출 때 올린다(오류 아님)."""
