# -*- coding: utf-8 -*-
"""SOP 검문소(2026-10-05 감사 후 도입).
감사 결과 SOP 위반의 원인은 (1) 두뇌에게 규칙을 '알려 주기만' 하고 결과를 안 잼, (2) 재고도 경고만 하고 통과,
(3) 규칙 값이 코드에 다르게 들어감 이었다. 그래서 단계가 끝날 때마다 SOP 수치를 코드로 재고:
  - hard 규칙이 어긋나면 그 단계를 실패로 멈춘다(StageError) — '경고만 하고 통과'는 없다.
  - soft 규칙은 '사람 확인 필요'로 남기고 중간 점검/마무리 보고 맨 위에 올린다.
결과는 단계 폴더 검문소.json + events(type=gate) + 프로젝트 폴더 검문소.md(전체 모음)."""
import json, os
from .core import StageError, jdump, jload, now


class Gate:
    def __init__(self, P, stage, d):
        self.P, self.stage, self.d = P, stage, d
        self.items = []

    def check(self, rule, ok, measured="", target="", sop="", hard=True):
        """rule: 사람이 읽는 규칙 이름, measured/target: 잰 값/기준(글자), hard: 어기면 멈춤."""
        it = {"rule": rule, "ok": bool(ok), "measured": str(measured), "target": str(target), "sop": sop, "hard": bool(hard)}
        self.items.append(it)
        if not ok:
            self.P.ev.log(f"{'⛔' if hard else '⚠️'} 검문 {rule}: {measured} (기준 {target}{', SOP ' + sop if sop else ''})",
                          "error" if hard else "warn")
        return bool(ok)

    @property
    def soft_fails(self):
        return [x for x in self.items if not x["ok"] and not x["hard"]]

    def finish(self):
        jdump({"t": now(), "stage": self.stage, "items": self.items}, os.path.join(self.d, f"검문소_{self.stage}.json"))
        self.P.ev.emit(type="gate", stage=self.stage, items=self.items,
                       ok=sum(x["ok"] for x in self.items), total=len(self.items))
        write_summary(self.P)
        bad = [x for x in self.items if not x["ok"] and x["hard"]]
        if bad:
            raise StageError("SOP 검문 실패 — " + "; ".join(f"{x['rule']}: {x['measured']} (기준 {x['target']})" for x in bad))
        return self.items


def all_gates(P):
    """프로젝트 안 모든 단계의 검문 결과(단계 폴더 순)."""
    out = []
    for name in sorted(os.listdir(P.dir)):
        sd = os.path.join(P.dir, name)
        if not os.path.isdir(sd):
            continue
        for f in sorted(os.listdir(sd)):     # 한 단계 폴더에 검문이 여럿일 수 있다(가편 폴더 = 자막 + 가편)
            if f.startswith("검문소") and f.endswith(".json"):
                g = jload(os.path.join(sd, f), {})
                out.append((g.get("stage") or name, g.get("items", [])))
    return out


def write_summary(P):
    L = ["# SOP 검문소 결과", "", "⛔ = 어겨서 멈춘 규칙, ⚠️ = 사람 확인 필요, ✅ = 통과", ""]
    for name, items in all_gates(P):
        ok = sum(x["ok"] for x in items)
        L += [f"## {name} — {ok}/{len(items)} 통과", "", "| | 규칙 | 잰 값 | 기준 | SOP |", "|---|---|---|---|---|"]
        for x in items:
            mark = "✅" if x["ok"] else ("⛔" if x["hard"] else "⚠️")
            L.append(f"| {mark} | {x['rule']} | {x['measured']} | {x['target']} | {x['sop']} |")
        L.append("")
    open(P.p("검문소.md"), "w", encoding="utf-8").write("\n".join(L))

