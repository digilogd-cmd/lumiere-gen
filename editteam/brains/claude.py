# -*- coding: utf-8 -*-
"""두뇌: 사용자 PC의 Claude Code(본인 로그인·구독)를 headless로 부른다.  claude -p --json-schema ...
도구는 전부 끈다(--tools ""): 판단만 하고 파일·명령은 못 건드린다.
작업 폴더는 임시 폴더로 둔다 — 상위 폴더의 CLAUDE.md(다른 자동화 지시)를 읽지 않게."""
import json, os, shutil, subprocess, tempfile


def call(cfg, prompt, schema, system=None, read_dirs=None):
    exe = shutil.which("claude") or shutil.which("claude.cmd")
    if not exe:
        raise RuntimeError("Claude Code(claude 명령)를 찾을 수 없습니다. 설치·로그인 후 다시 시도해 주세요.")
    cmd = [exe, "-p", "--output-format", "json", "--json-schema", json.dumps(schema, ensure_ascii=False),
           "--no-session-persistence", "--model", cfg["두뇌"].get("claude_모델", "sonnet")]
    if read_dirs:   # 그림을 봐야 하는 Task(크롭 검수 등): 그 폴더만 읽기 허용
        cmd += ["--tools", "Read", "--allowedTools", "Read", "--add-dir", *read_dirs]
    else:
        cmd += ["--tools", ""]
    if system:
        cmd += ["--append-system-prompt", system]
    r = subprocess.run(cmd, input=prompt.encode("utf-8"), capture_output=True, timeout=1800, cwd=tempfile.gettempdir())
    txt = r.stdout.decode("utf-8", "replace")
    try:
        d = json.loads(txt)
    except ValueError:
        raise RuntimeError(f"Claude 응답을 읽을 수 없습니다: {(txt or r.stderr.decode('utf-8', 'replace'))[-300:]}")
    if d.get("is_error"):
        raise RuntimeError(f"Claude 오류: {str(d.get('result'))[:300]}")
    out = d.get("structured_output")
    if out is None:
        out = json.loads(d.get("result") or "null")
    model = ",".join((d.get("modelUsage") or {}).keys())
    return out, {"cost_usd": d.get("total_cost_usd"), "model": model}
