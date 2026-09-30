#!/usr/bin/env python3
"""채팅 vs lite 실측 원자료 → summary.json + README 표.

    python3 bench/chat-vs-lite/summarize.py        # 이 디렉터리의 *.json 과 grade.md 를 읽는다

`usage` 는 서브에이전트를 빼므로 쓰지 않는다. 토큰은 `modelUsage` 를 모델별로 합산하고, 비용·시간은 `total_cost_usd`·`duration_ms`.
lite 쪽은 프롬프트 생성 + 실행의 합이다. 체크리스트 통과 수는 grade.md 의 `SCORE chat=a/n lite=b/n` 줄에서.
`check_prompt.py --repo` 가 summary.json 을 원자료와 다시 대조하고, readme_cells 가 README 에 그대로 있는지 본다.
"""
import io
import json
import os
import re

D = os.path.dirname(os.path.abspath(__file__))
SIDES = [("chat", "채팅", ["chat.json"]), ("lite", "lite (생성+실행)", ["lite-gen.json", "lite-run.json"])]


def load(fn):
    return json.load(io.open(os.path.join(D, fn), encoding="utf-8"))


def tally(files):
    t = {"cost_usd": 0.0, "duration_ms": 0, "input_tokens": 0, "output_tokens": 0, "turns": 0, "subagents": 0, "models": set()}
    for fn in files:
        d = load(fn)
        t["cost_usd"] += d["total_cost_usd"]
        t["duration_ms"] += d["duration_ms"]
        t["turns"] += d.get("num_turns", 0)
        t["subagents"] += (d.get("subagent_stats") or {}).get("spawned", 0)
        for m, u in d["modelUsage"].items():
            t["input_tokens"] += u["inputTokens"] + u["cacheReadInputTokens"] + u["cacheCreationInputTokens"]
            t["output_tokens"] += u["outputTokens"]
            t["models"].add(m)
    t["models"] = sorted(t["models"])
    return t


def mmss(ms):
    s = round(ms / 1000)
    return "%d분 %02d초" % (s // 60, s % 60)


def main():
    grade = io.open(os.path.join(D, "grade.md"), encoding="utf-8").read() if os.path.exists(os.path.join(D, "grade.md")) else ""
    m = re.search(r"SCORE\s+chat=(\d+)/(\d+)\s+lite=(\d+)/(\d+)", grade)
    score = {"chat": "%s/%s" % m.group(1, 2), "lite": "%s/%s" % m.group(3, 4)} if m else {}
    sides, rows = [], {}
    for key, label, files in SIDES:
        if not all(os.path.exists(os.path.join(D, f)) for f in files):
            continue
        t = tally(files)
        cells = {"in": "{:,}".format(t["input_tokens"]), "out": "{:,}".format(t["output_tokens"]),
                 "cost": "$%.2f" % t["cost_usd"], "time": mmss(t["duration_ms"]), "score": score.get(key, "—"),
                 "agents": str(t["subagents"])}
        rows[key] = cells
        sides.append({"name": key, "label": label, "raw": files, "cost_usd": round(t["cost_usd"], 6),
                      "duration_ms": t["duration_ms"], "input_tokens": t["input_tokens"], "output_tokens": t["output_tokens"],
                      "turns": t["turns"], "subagents": t["subagents"], "models": t["models"], "checklist": score.get(key),
                      "readme_cells": [cells["out"], cells["cost"], cells["time"]] + ([cells["score"]] if key in score else [])})
    json.dump({"sides": sides}, io.open(os.path.join(D, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if len(rows) == 2:
        c, l = rows["chat"], rows["lite"]
        print("| 측정 (원자료 `bench/chat-vs-lite/`) | 채팅 | lite (생성+실행) |")
        print("|---|---|---|")
        for k, name in [("score", "체크리스트 통과 (제3 채점자)"), ("cost", "비용 `total_cost_usd`"), ("time", "시간 `duration_ms`"),
                        ("out", "출력 토큰 `modelUsage`"), ("in", "입력 토큰 (캐시 포함)"), ("agents", "서브에이전트")]:
            print("| %s | %s | %s |" % (name, c[k], l[k]))


if __name__ == "__main__":
    main()
