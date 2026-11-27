# -*- coding: utf-8 -*-
"""두뇌(AI) 바꿔 끼우기 (작업지시서 단계 4).
실행기의 계산(ffmpeg·받아쓰기·소리 분석·렌더)은 AI 없이 돈다. 판단이 필요한 일만 Task로 모아 여기로 보낸다.
모든 두뇌는 같은 함수  run(task, input) -> dict  를 쓰고, 출력은 Task마다 정한 JSON 스키마로 고정한다.
- 스키마가 안 맞거나 검증(validate)이 실패하면 1번 다시 시도, 그래도 안 되면 BrainFailed -> 단계가 "사람 확인 필요"로 표시.
- config.yaml 두뇌.task별 로 Task마다 다른 두뇌를 고를 수 있다."""
import importlib, json, os, time
from ..core import jdump, now
from . import tasks as T


class BrainFailed(Exception):
    pass


def pick(cfg, task):
    b = cfg["두뇌"]
    return (b.get("task별") or {}).get(task) or b.get("기본", "claude")


def run(P, task, inp, log_dir=None, brain=None):
    """P: Project(설정·기록용). 결과 dict. 호출 기록은 log_dir/brain_<task>.json 에 남긴다(비용·시간 비교용)."""
    spec = T.TASKS[task]
    name = brain or pick(P.cfg, task)
    # 같은 Task·같은 입력·같은 두뇌면 이전 답을 그대로(다시 돌릴 때마다 제목·쇼츠가 바뀌지 않게, 비용 0)
    from ..core import hash_of, jload
    from ..profile import STYLE_TASKS, for_brain          # 내 스타일 노트(첫 만남에서 들은 취향)를 편집 방향 판단에 같이 준다
    style = for_brain() if task in STYLE_TASKS else ""
    ck = hash_of(task, inp, name, P.cfg["두뇌"].get("claude_모델") if name == "claude" else P.cfg["두뇌"].get(f"{name}_모델"), style)
    cp = os.path.join(log_dir, f"cache_exact_{task}.json") if log_dir else None
    if cp and ck in (jload(cp, {}) or {}):
        P.ev.log(f"두뇌 답 재사용({task}: 입력이 이전과 같음)")
        return jload(cp)[ck]
    mod = importlib.import_module(f".{name}", __package__)
    prompt = spec["prompt"](inp) + style
    schema = spec["schema"]
    errors, t0, out, meta = [], time.time(), None, {}
    for attempt in range(2):
        p = prompt if not errors else prompt + "\n\n[이전 답의 문제]\n" + errors[-1] + "\n위 문제를 고쳐서 다시 답하세요."
        try:
            if spec.get("files"):
                if name == "codex":     # 코덱스는 그림 파일을 직접 붙인다(-i)
                    dd = os.path.dirname(inp["sheet"])
                    ims = [inp["sheet"]] + [os.path.join(dd, f) for f in inp.get("files", []) if os.path.join(dd, f) != inp["sheet"]]
                    out, meta = mod.call(P.cfg, p, schema, system=spec.get("system", T.SYSTEM), images=[x for x in ims if os.path.isfile(x)])
                elif name != "claude":
                    raise RuntimeError(f"{name} 두뇌는 그림 보기 Task를 지원하지 않습니다")
                else:
                    out, meta = mod.call(P.cfg, p, schema, system=spec.get("system", T.SYSTEM), read_dirs=[os.path.dirname(inp["sheet"])])
            else:
                out, meta = mod.call(P.cfg, p, schema, system=spec.get("system", T.SYSTEM))
            err = spec["validate"](out, inp) if spec.get("validate") else None
        except Exception as e:  # 두뇌 프로그램 자체 오류(로그인 만료 등)
            err = f"{type(e).__name__}: {e}"
            out = None
        if not err:
            break
        errors.append(err)
        P.ev.log(f"두뇌({name}) {task} 답 검증 실패 → {'다시 시도' if attempt == 0 else '사람 확인 필요'}: {err[:120]}", "warn")
    rec = {"t": now(), "task": task, "brain": name, "sec": round(time.time() - t0, 1), "errors": errors,
           "cost_usd": meta.get("cost_usd"), "model": meta.get("model"), "ok": not (errors and len(errors) == 2)}
    if log_dir:
        jdump({"record": rec, "output": out}, os.path.join(log_dir, f"brain_{task}.json"))
        hist = os.path.join(log_dir, "brain_calls.jsonl")
        with open(hist, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if not rec["ok"]:
        raise BrainFailed(f"{task}: {errors[-1]}")
    if cp:
        c = jload(cp, {}) or {}
        c[ck] = out
        jdump(c, cp)
    return out
