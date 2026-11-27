# -*- coding: utf-8 -*-
"""두뇌: 사용자 PC의 Codex CLI(본인 ChatGPT 로그인·구독)를 비대화식으로 부른다.  codex exec --output-schema ...
(2026-10-07: 다른 영상을 코덱스 두뇌로 돌려 Claude와 얼마나 비슷한지 비교해 보고 싶다)
- 샌드박스 read-only, 작업 폴더는 빈 임시 폴더: 판단만 하고 파일·명령은 못 건드린다.
- 그림을 봐야 하는 Task는 그림 파일을 -i 로 붙인다.
- OpenAI 구조화 출력은 스키마가 엄격(모든 속성 required, additionalProperties false)해야 해서 보낼 때 맞춰 바꾼다."""
import copy, json, os, shutil, subprocess, tempfile


def _strict(s):
    """JSON Schema -> OpenAI strict 모드에 맞게(객체마다 모든 속성 required + additionalProperties false).
    원래 선택이던 속성은 null 도 허용해 둔다."""
    s = copy.deepcopy(s)

    def walk(x):
        if isinstance(x, dict):
            if x.get("type") == "object" or "properties" in x:
                props = x.get("properties", {})
                req = set(x.get("required", []))
                for k, v in props.items():
                    walk(v)
                    if k not in req:
                        t = v.get("type")
                        if isinstance(t, str):
                            v["type"] = [t, "null"]
                        elif isinstance(t, list) and "null" not in t:
                            v["type"] = t + ["null"]
                x["required"] = list(props.keys())
                x["additionalProperties"] = False
            for k in ("items", "anyOf", "oneOf", "allOf"):
                if k in x:
                    if isinstance(x[k], list):
                        for y in x[k]:
                            walk(y)
                    else:
                        walk(x[k])
            for k in ("minItems", "maxItems", "minLength", "maxLength", "pattern", "format", "minimum", "maximum"):
                x.pop(k, None)          # strict 모드가 거부하는 제약은 빼고, 대신 Task의 validate 가 검사한다
        return x
    return walk(s)


def _drop_nulls(x):
    if isinstance(x, dict):
        return {k: _drop_nulls(v) for k, v in x.items() if v is not None}
    if isinstance(x, list):
        return [_drop_nulls(v) for v in x]
    return x


def codex_cmd():
    """codex 실행 명령. 1순위: 코덱스 데스크톱 앱에 들어 있는 최신 codex.exe(npm 설치본이 오래되면 새 모델 gpt-6.1-sol 을 못 씀, 2026-10-07 실측).
    그다음 PATH의 codex.cmd/exe, 그것도 없으면(이름이 바뀐 경우 등) npm 설치본(codex.js)을 node로 직접 부른다."""
    import glob
    app = sorted(glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""), "OpenAI", "Codex", "bin", "*", "codex.exe")), key=os.path.getmtime)
    if app:
        return [app[-1]]
    for n in ("codex.cmd", "codex.exe"):
        p = shutil.which(n)
        if p:
            return [p]
    node = shutil.which("node")
    for base in (os.path.join(os.environ.get("APPDATA", ""), "npm"), os.path.dirname(node or "")):
        js = os.path.join(base, "node_modules", "@openai", "codex", "bin", "codex.js")
        if node and os.path.isfile(js):
            return [node, js]
    return None


def user_model():
    """사용자 코덱스 설정(~/.codex/config.toml)의 model 값만 읽는다(나머지 설정·알림은 안 씀)."""
    import re
    p = os.path.join(os.path.expanduser("~"), ".codex", "config.toml")
    try:
        for ln in open(p, encoding="utf-8"):
            m = re.match(r'\s*model\s*=\s*"([^"]+)"', ln)
            if m:
                return m.group(1)
            if ln.strip().startswith("["):
                break
    except OSError:
        pass
    return None


def call(cfg, prompt, schema, system=None, read_dirs=None, images=None):
    exe = codex_cmd()
    if not exe:
        raise RuntimeError("Codex CLI(codex 명령)를 찾을 수 없습니다. 설치·로그인(codex login) 후 다시 시도해 주세요.")
    work = tempfile.mkdtemp(prefix="lumiere_codex_")
    try:
        sp, op = os.path.join(work, "schema.json"), os.path.join(work, "out.json")
        json.dump(_strict(schema), open(sp, "w", encoding="utf-8"), ensure_ascii=False)
        # --ignore-user-config: 사용자 코덱스 설정의 알림·플러그인·기본 모델(ChatGPT 계정에서 안 되는 모델일 수 있음)을 읽지 않는다. 로그인은 그대로 씀
        model = (cfg.get("두뇌") or {}).get("codex_모델") or user_model() or "gpt-5.5"
        effort = (cfg.get("두뇌") or {}).get("codex_생각", "medium")
        cmd = exe + ["exec", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config", "-s", "read-only", "-C", work,
                     "--output-schema", sp, "-o", op, "--color", "never", "-m", model, "-c", f'model_reasoning_effort="{effort}"']
        for im in images or []:
            cmd += ["-i", im]
        cmd += ["-"]
        text = ((system + "\n\n") if system else "") + prompt
        if images:      # 붙인 그림에는 파일 이름이 안 보이므로 순서대로 알려 준다
            text += "\n\n붙인 그림 파일 이름(붙인 순서대로): " + ", ".join(os.path.basename(x) for x in images)
        text += "\n\n(파일을 읽거나 명령을 실행하지 말고, 위 입력만 보고 정해진 JSON 형식으로만 답하세요.)"
        r = subprocess.run(cmd, input=text.encode("utf-8"), capture_output=True, timeout=1800, cwd=work)
        if not os.path.exists(op) and b"not supported" in r.stderr and model != "gpt-5.5":
            # 이 계정·CLI 버전에서 못 쓰는 모델 -> gpt-5.5 로 한 번 더(설정 창에서 모델을 바꿀 수 있음)
            i = cmd.index("-m"); cmd[i + 1] = model = "gpt-5.5"
            r = subprocess.run(cmd, input=text.encode("utf-8"), capture_output=True, timeout=1800, cwd=work)
        raw = open(op, encoding="utf-8").read() if os.path.exists(op) else ""
        if not raw.strip():
            err = r.stderr.decode("utf-8", "replace")[-400:] or r.stdout.decode("utf-8", "replace")[-400:]
            raise RuntimeError(f"Codex 응답이 없습니다: {err}")
        try:
            out = json.loads(raw)
        except ValueError:
            raise RuntimeError(f"Codex 응답을 읽을 수 없습니다: {raw[-300:]}")
        return _drop_nulls(out), {"cost_usd": None, "model": f"codex {model}"}
    finally:
        shutil.rmtree(work, ignore_errors=True)
