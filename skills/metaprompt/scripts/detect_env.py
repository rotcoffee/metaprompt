#!/usr/bin/env python3
"""실행 모드와 저장소 사실을 JSON 한 덩어리로 낸다.

모델이 git 커맨드 여섯 개를 돌리고 package.json·Makefile 을 읽는 대신 이 스크립트 한 번이면 된다.
항상 exit 0 — 스킬의 인라인 셸(`!`) 에서 호출되므로 실패하면 스킬 자체가 열리지 않는다.
"""
import json
import os
import re
import shutil
import subprocess
import sys


def sh(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except Exception:
        return ""


def read(path, limit=200_000):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read(limit)
    except Exception:
        return ""


def main():
    cwd = os.getcwd()
    out = {"cwd": cwd}
    args = sys.argv[1:]
    if "--skill-dir" in args:
        d = args[args.index("--skill-dir") + 1] if args.index("--skill-dir") + 1 < len(args) else ""
        out["skill_dir"] = os.path.realpath(d) if d else ""
    else:
        out["skill_dir"] = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    root = sh("git rev-parse --show-toplevel 2>/dev/null")
    out["mode"] = "worktree" if root else "greenfield"

    if root:
        out.update({
            "repo_root": root,
            "repo_name": os.path.basename(root),
            "head": sh("git rev-parse HEAD 2>/dev/null"),
            "head_short": sh("git rev-parse --short HEAD 2>/dev/null"),
            "branch": sh("git branch --show-current 2>/dev/null") or "(detached)",
            "dirty_count": len([l for l in sh("git status --porcelain 2>/dev/null").splitlines() if l.strip()]),
            "worktree_count": len(sh("git worktree list 2>/dev/null").splitlines()),
        })

        cmds = {"test": [], "build": [], "bench": [], "lint": []}

        pj = os.path.join(root, "package.json")
        if os.path.exists(pj):
            try:
                scripts = json.loads(read(pj)).get("scripts", {})
                if os.path.exists(os.path.join(root, "pnpm-lock.yaml")):
                    pm = "pnpm"
                elif os.path.exists(os.path.join(root, "yarn.lock")):
                    pm = "yarn"
                elif os.path.exists(os.path.join(root, "bun.lockb")) or os.path.exists(os.path.join(root, "bun.lock")):
                    pm = "bun run"
                else:
                    pm = "npm run"
                for name in scripts:
                    for key in cmds:
                        if name == key or name.startswith(key + ":"):
                            cmds[key].append("%s %s" % ("npm" if pm == "npm run" and name == "test" else pm, name))
            except Exception:
                pass

        mk = read(os.path.join(root, "Makefile"))
        if mk:
            for target in re.findall(r"^([A-Za-z][\w-]*)\s*:", mk, re.M):
                for key in cmds:
                    if target == key or target.startswith(key + "-") or target.startswith(key + "_"):
                        cmds[key].append("make " + target)

        py = read(os.path.join(root, "pyproject.toml"))
        if py or os.path.exists(os.path.join(root, "pytest.ini")) or os.path.exists(os.path.join(root, "tox.ini")):
            cmds["test"].append("pytest")
            if "ruff" in py:
                cmds["lint"].append("ruff check .")
        if os.path.exists(os.path.join(root, "Cargo.toml")):
            cmds["test"].append("cargo test")
            cmds["bench"].append("cargo bench")
        if os.path.exists(os.path.join(root, "go.mod")):
            cmds["test"].append("go test ./...")
            cmds["bench"].append("go test -bench . ./...")

        ci = []
        wf = os.path.join(root, ".github", "workflows")
        if os.path.isdir(wf):
            for fn in sorted(os.listdir(wf)):
                if fn.endswith((".yml", ".yaml")):
                    for line in read(os.path.join(wf, fn)).splitlines():
                        m = re.match(r"\s*-?\s*run:\s*(.+)", line)
                        if m and re.search(r"test|pytest|jest|vitest|bench|lint|tox", m.group(1)):
                            ci.append(m.group(1).strip())

        out["commands"] = {k: sorted(set(v)) for k, v in cmds.items() if v}
        if ci:
            out["ci_run_lines"] = sorted(set(ci))[:8]

        markers = {
            "package.json": "node", "pyproject.toml": "python", "requirements.txt": "python",
            "Cargo.toml": "rust", "go.mod": "go", "pom.xml": "java", "build.gradle": "java",
            "Gemfile": "ruby", "composer.json": "php", "Dockerfile": "docker", "docker-compose.yml": "docker",
        }
        out["stack"] = sorted({v for k, v in markers.items() if os.path.exists(os.path.join(root, k))})

        warnings = []
        need = {"npm": "node", "pnpm": "node", "yarn": "node", "bun": "bun", "pytest": "python3", "cargo": "cargo", "go ": "go", "make": "make"}
        for cmd in out["commands"].get("test", []):
            for prefix, binary in need.items():
                if cmd.startswith(prefix) and not shutil.which(binary):
                    warnings.append("테스트 커맨드 `%s` 를 찾았지만 런타임 `%s` 가 없다" % (cmd, binary))
        if warnings:
            out["warnings"] = warnings

    browsers = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "firefox"]
    out["browser"] = next((shutil.which(b) for b in browsers if shutil.which(b)), None)
    out["tools"] = {t: bool(shutil.which(t)) for t in
                    ["node", "npx", "python3", "uv", "pip", "docker", "k6", "wrk", "hey", "ab", "hyperfine",
                     "locust", "nvidia-smi", "nvcc", "xvfb-run", "cargo", "go", "make"]}

    # 파이썬 패키지 — import 하지 않고 존재만 본다 (torch import 는 수 초 걸린다)
    try:
        import importlib.util as iu
        out["python_packages"] = {m: iu.find_spec(m) is not None for m in
                                  ["torch", "transformers", "playwright", "pytest", "sklearn", "numpy", "locust"]}
    except Exception:
        out["python_packages"] = {}

    # Playwright 브라우저 바이너리 (python·node 공통 캐시)
    pw_cache = os.path.expanduser("~/.cache/ms-playwright")
    out["playwright_browsers"] = sorted(os.listdir(pw_cache)) if os.path.isdir(pw_cache) else []

    # GPU
    gpu = {"nvidia_smi": bool(shutil.which("nvidia-smi")), "count": 0, "names": []}
    if gpu["nvidia_smi"]:
        names = [l.split(":", 1)[1].split("(")[0].strip() for l in sh("nvidia-smi -L").splitlines() if l.startswith("GPU")]
        gpu["count"], gpu["names"] = len(names), names[:4]
    out["gpu"] = gpu

    # 시스템 정보 — 설치 커맨드 선택용
    out["os"] = {"platform": sh("uname -s") or "unknown", "arch": sh("uname -m"),
                 "distro": sh(". /etc/os-release 2>/dev/null && echo $ID"), "sudo": bool(shutil.which("sudo")),
                 "brew": bool(shutil.which("brew")), "apt": bool(shutil.which("apt-get"))}
    # Claude Code — 버전 · 실행 방식 · 기능 플래그 · effort. 스위치(agent teams·Workflow·루프) 판정에 쓴다
    ver = re.search(r"\d+\.\d+\.\d+", sh("claude --version 2>/dev/null"))
    env = os.environ
    entry = env.get("CLAUDE_CODE_ENTRYPOINT", "")
    out["claude"] = {
        "version": ver.group(0) if ver else None,
        "entrypoint": entry or None,
        "interactive": entry == "cli" and env.get("CLAUDE_CODE_SESSION_ATTENDED", "1") != "0",
        "features": {
            "agent_teams": env.get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS") == "1",
            "workflows_disabled": env.get("CLAUDE_CODE_DISABLE_WORKFLOWS") == "1",
            "goal_checkin_minutes": env.get("CLAUDE_CODE_GOAL_CHECKIN_MINUTES"),
        },
    }
    settings = {}
    try:
        settings = json.loads(read(os.path.expanduser("~/.claude/settings.json")) or "{}")
    except Exception:
        pass
    out["effort"] = {"session": env.get("CLAUDE_EFFORT") or settings.get("effortLevel"),
                     "settings": settings.get("effortLevel"), "model": settings.get("model")}
    agents_dir = os.path.join(cwd, ".claude", "agents")
    out["project_agents"] = sorted(f[:-3] for f in os.listdir(agents_dir) if f.endswith(".md")) if os.path.isdir(agents_dir) else []
    out["today"] = sh("date +%F")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # 절대 비정상 종료하지 않는다
        print(json.dumps({"mode": "unknown", "error": str(e)}, ensure_ascii=False))
