# -*- coding: utf-8 -*-
"""프로젝트 하나에서 두뇌를 몇 번 불렀고 얼마나 걸렸고 얼마 들었는지(단계 폴더의 brain_calls.jsonl 모음).
판매용: 고객이 OpenAI·Gemini 키를 쓸 때 비용을 바로 보여 주기 위함. Claude(구독 로그인)는 '참고 금액'."""
import glob, json, os

TASK_KO = {"content_cuts": "내용 컷", "hook_pick": "후킹 인트로", "motion_copy": "모션 문구", "titles_desc": "제목·설명",
           "shorts_plan": "쇼츠 기획", "subtitle_review": "자막 검수", "restructure_plan": "구성 재편집",
           "crop_check": "쇼츠 크롭 검수"}


def summary(pdir):
    rows = {}
    for f in glob.glob(os.path.join(pdir, "*", "brain_calls.jsonl")):
        for ln in open(f, encoding="utf-8"):
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            k = r.get("task")
            x = rows.setdefault(k, {"task": k, "name": TASK_KO.get(k, k), "calls": 0, "sec": 0.0, "cost": 0.0, "fail": 0, "brain": r.get("brain")})
            x["calls"] += 1 + len(r.get("errors") or []) - (0 if r.get("ok") else 1)
            x["sec"] += r.get("sec") or 0
            x["cost"] += r.get("cost_usd") or 0
            x["fail"] += 0 if r.get("ok") else 1
            x["brain"] = r.get("brain")
    items = sorted(rows.values(), key=lambda x: -x["sec"])
    tot = {"calls": sum(x["calls"] for x in items), "sec": round(sum(x["sec"] for x in items), 1),
           "cost": round(sum(x["cost"] for x in items), 3), "fail": sum(x["fail"] for x in items)}
    for x in items:
        x["sec"] = round(x["sec"], 1); x["cost"] = round(x["cost"], 3)
    return {"items": items, "total": tot}


def line(pdir):
    s = summary(pdir)["total"]
    if not s["calls"]:
        return "두뇌 사용: 없음"
    return f"두뇌 {s['calls']}번 · {s['sec'] / 60:.1f}분 · 약 ${s['cost']:.2f}" + (f" · 실패 {s['fail']}" if s["fail"] else "")
