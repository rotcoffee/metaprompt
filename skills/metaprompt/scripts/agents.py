#!/usr/bin/env python3
"""생성된 프롬프트의 역할 표로 `.claude/agents/mp-*.md` 를 만든다 — 세션을 시작하기 **전에** 돌린다.

    python3 agents.py <프롬프트.md> [--dir <작업 디렉터리>] [--print]

Agent 도구에는 effort 파라미터가 없어서, 역할별 effort 는 에이전트 정의 frontmatter 로만 줄 수 있다.
세션 도중에 만든 정의는 그 세션에 로드되지 않았다 (Claude Code 2.1.285 실측). 그래서 이 스크립트가 따로 있다.
정의 파일은 커밋에 섞이지 않도록 `.git/info/exclude` 에 넣는다. `--print` 는 쓰지 않고 내용만 보여준다.
"""
import io
import os
import re
import subprocess
import sys

MODELS = {"opus", "sonnet", "haiku", "fable"}
EFFORTS = {"low", "medium", "high", "xhigh", "max"}
NONE = {"—", "-", "–", ""}

BODY = {
    "mp-verifier": "너는 검증자다. 체크리스트 항목과 정확성 결함만 판정한다 — 취향 지적은 넣지 않는다. 근거는 커맨드로 얻은 출력뿐이고, 수치는 추정하지 않는다. 판정문은 verdicts/round-N.md 에 남기고 보고는 30줄 이내.",
    "mp-judge": "너는 블라인드 심사자다. 받은 묶음만 보고 주어진 축과 배점으로 채점한다. 정체를 알아봤으면 그렇다고 적는다. 보고는 30줄 이내.",
    "mp-worker": "너는 팬아웃 워커다. 지시된 산출물을 파일로 남기고 경로와 결론만 30줄 이내로 보고한다. 맡은 범위 밖의 파일을 고치지 않는다.",
    "mp-reader": "너는 콜드 리더다. 받은 이미지 한 장만 보고 질문에 답한다. 다른 파일이나 저장소를 열지 않는다.",
}


def parse_roles(text):
    """`| 역할 | 정의 | model | effort | … |` 표의 행들을 dict 로. 들여쓴 표도 읽는다."""
    rows, on = [], False
    for line in text.splitlines():
        t = line.strip()
        if not t.startswith("|"):
            if on and t:
                on = False
            continue
        cells = [c.strip() for c in t.strip("|").split("|")]
        if len(cells) >= 4 and cells[0] == "역할" and cells[2].lower() == "model" and cells[3].lower() == "effort":
            on = True
            continue
        if on and not re.match(r"^:?-{2,}", cells[0]):
            rows.append({"role": cells[0], "name": cells[1], "model": cells[2], "effort": cells[3],
                         "what": cells[4] if len(cells) > 4 else ""})
    return rows


def role_errors(row):
    """역할 행 하나의 모델·effort 결함 목록."""
    errs = []
    m, e = row["model"].strip("` ").lower(), row["effort"].strip("` ").lower()
    if not m:
        errs.append("%s: model 이 비었다" % row["role"])
    elif m not in MODELS and "세션" not in m:
        errs.append("%s: model `%s` 은 별칭(opus·sonnet·haiku·fable)이나 '세션 모델'이 아니다" % (row["role"], row["model"]))
    if m == "haiku":
        if e not in NONE:
            errs.append("%s: haiku 는 effort 미지원인데 `%s` 가 적혀 있다" % (row["role"], row["effort"]))
    elif e in NONE:
        errs.append("%s: effort 가 비었다" % row["role"])
    elif not any(w in EFFORTS for w in re.findall(r"[a-z]+", e)):
        errs.append("%s: effort `%s` 가 low·medium·high·xhigh·max 가 아니다" % (row["role"], row["effort"]))
    elif re.search(r"\b(xhigh|max)\b", e) and "실측" not in row["what"]:
        errs.append("%s: xhigh·max 는 이득을 실측했을 때만 (맡는 일 칸에 근거)" % row["role"])
    return errs


def definition(row):
    name = row["name"].strip("` ")
    lines = ["---", "name: %s" % name,
             "description: metaprompt 역할 — %s. %s" % (row["role"], row["what"] or "생성 프롬프트가 지시하는 일"),
             "model: %s" % row["model"].strip("` ").lower()]
    e = row["effort"].strip("` ").lower()
    if e not in NONE:
        lines.append("effort: %s" % e)
    lines += ["---", BODY.get(name, "지시된 일만 하고 보고는 30줄 이내."), ""]
    return "\n".join(lines)


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    path = args[0]
    d = args[args.index("--dir") + 1] if "--dir" in args else os.getcwd()
    rows = [r for r in parse_roles(io.open(path, encoding="utf-8").read()) if r["name"].strip("` ").startswith("mp-")]
    if not rows:
        print("FAIL 역할 표에 mp-* 정의 행이 없다: %s" % path)
        return 1
    errs = [e for r in rows for e in role_errors(r)]
    if errs:
        print("FAIL 역할 표 결함\n  " + "\n  ".join(errs))
        return 1
    if "--print" in args:
        for r in rows:
            print("# .claude/agents/%s.md\n%s" % (r["name"].strip("` "), definition(r)))
        return 0
    out = os.path.join(d, ".claude", "agents")
    os.makedirs(out, exist_ok=True)
    for r in rows:
        io.open(os.path.join(out, r["name"].strip("` ") + ".md"), "w", encoding="utf-8").write(definition(r))
        print("wrote %s/%s.md  (model=%s effort=%s)" % (out, r["name"].strip("` "), r["model"], r["effort"]))
    try:
        ex = subprocess.run(["git", "-C", d, "rev-parse", "--git-path", "info/exclude"],
                            capture_output=True, text=True, timeout=10).stdout.strip()
        if ex:
            ex = ex if os.path.isabs(ex) else os.path.join(d, ex)
            cur = io.open(ex, encoding="utf-8").read() if os.path.exists(ex) else ""
            if "/.claude/agents/" not in cur:
                os.makedirs(os.path.dirname(ex), exist_ok=True)
                io.open(ex, "a", encoding="utf-8").write("\n/.claude/agents/\n")
                print("excluded /.claude/agents/ via %s" % ex)
    except Exception:
        pass
    print("이제 이 디렉터리에서 세션을 시작한다 — 이미 열린 세션에는 로드되지 않는다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
