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
                    ["node", "python3", "docker", "k6", "wrk", "hey", "ab", "hyperfine", "uv"]}
    out["today"] = sh("date +%F")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # 절대 비정상 종료하지 않는다
        print(json.dumps({"mode": "unknown", "error": str(e)}, ensure_ascii=False))
