#!/usr/bin/env python3
"""생성된 메타프롬프트가 자가점검 항목을 만족하는지 기계적으로 검사한다.

    python3 check_prompt.py <프롬프트.md> [...] [--tier lite|standard|max] [--mode greenfield|worktree]
    python3 check_prompt.py --self-test      스킬 구조 · 계약 단일화 · 픽스처 · 음성 케이스
    python3 check_prompt.py --repo [<루트>]   버전 3곳 일치 · README 수치 정합 · 실측 원자료 대조 (CI)

경로·티어·모드·도메인은 첫 줄의 `<!-- metaprompt route=… tier=… domain=… mode=… -->` 에서 읽고, 플래그가 오면 덮어쓴다.
티어 수치와 역할→모델·effort 는 references/contract.md 의 표를 파싱한다 — 수치를 이 파일에 다시 적지 않는다.
oneshot-prompt(chanp5660, MIT) 의 tests/check_prompt.py 를 경로·티어 인식형으로 개작했다.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from agents import parse_roles, role_errors  # noqa: E402

TIERS = ("lite", "standard", "max")
MODEL_ID = r"\bclaude-(opus|sonnet|haiku|fable|instant)\b|\bclaude-\d+-\d+"  # claude-opus-5-5 · claude-3-5-… (경로의 claude-1000 은 아님)
MARKERS = r"(creative|precise|lite|standard\+|max|worktree|greenfield)"
BASE_LITE_BYTES = 36828  # lite·product·greenfield 경로 상한. 0.2.0 은 35,121 B — 0.3.1 에서 기본기·콜드 패스·모델 고정·크기 skip 규칙(bench/lab-2026-09-30.md 실측)을 넣으며 올렸다
LITE_PATH = ["SKILL.md", "references/contract.md", "references/creative.md", "references/product.md", "references/template.md"]


def _read(p):
    return io.open(p, encoding="utf-8").read()


def contract():
    """contract.md → {"tier": {키: {lite,standard,max}}, "roles": [...]}."""
    s = _read(os.path.join(SKILL, "references/contract.md"))
    tier = {}
    for m in re.finditer(r"^\|\s*([MKSCRQ])\s[^|]*\|([^|]+)\|([^|]+)\|([^|]+)\|", s, re.M):
        vals = [v.strip() for v in m.groups()[1:]]
        tier[m.group(1)] = dict(zip(TIERS, vals))
    return {"tier": tier, "roles": parse_roles(s)}


C = contract()


def _num(key, tier, idx=0):
    v = C["tier"].get(key, {}).get(tier, "")
    parts = re.findall(r"\d+", v)
    return int(parts[idx]) if len(parts) > idx else None


def _has(s, *pats):
    return any(re.search(p, s, re.M | re.S) for p in pats)


def _unfenced(s):
    """코드 펜스 안의 줄 머리 `#` 을 가린다 — 증거 블록의 bash 주석을 절 제목으로 읽지 않게."""
    out, fence = [], None
    for line in s.split("\n"):
        f = re.match(r"^\s*(`{3,}|~{3,})", line)
        if f and (fence is None or f.group(1)[0] == fence[0] and len(f.group(1)) >= len(fence)):
            fence = None if fence else f.group(1)
        elif fence and line.lstrip().startswith("#"):
            line = line.replace("#", "\u2317", 1)
        out.append(line)
    return "\n".join(out)


def _section(s, heading):
    m = re.search(r"^#{1,3}\s*%s[^\n]*\n(.*?)(?=^#{1,3}\s|\Z)" % heading, _unfenced(s), re.M | re.S)
    return m.group(1).replace("\u2317", "#") if m else ""


def _meta(s):
    m = re.search(r"<!--\s*metaprompt\s+([^>]*?)-->", s, re.S)
    meta = {}
    if m:
        for k, v in re.findall(r"(\w+)=(\"[^\"]*\"|\S+)", m.group(1)):
            meta[k] = v.strip('"')
    return meta


def _checklist_items(s):
    body = _section(s, "검증")
    if "체크리스트 — 전 항목" in body:
        body = body.split("체크리스트 — 전 항목", 1)[-1]
    return re.findall(r"^\s*-\s*\[\s*\]\s*(.+)$", body, re.M)


def _switch(s, name):
    m = re.search(r"^\s*-\s*%s\s*\*\*([^*]+)\*\*\s*—\s*\S" % name, s, re.M)
    return m.group(1).strip() if m else None


def _roles(s):
    return parse_roles(_section(s, "실행 예산"))


def _contract_row(name):
    return next((r for r in C["roles"] if r["name"].strip("` ") == name), None)


def _roles_match_contract(s):
    for r in _roles(s):
        n = r["name"].strip("` ")
        c = _contract_row(n)
        if n.startswith("mp-") and (not c or c["model"] != r["model"] or c["effort"] != r["effort"]):
            return False
    return True


def _baseline_token(s):
    b = re.sub(r"[\"'`*()\[\]]", " ", _meta(s).get("baseline", "")).split()
    return b[0] if b else "\0"


# (이름, 판정 함수(s, tier, mode, domain, route), 실패 시 안내)
COMMON = [
    ("헤더 메타", lambda s, t, m, d, r: all(k in _meta(s) for k in ("route", "tier", "domain", "mode")) and r in ("creative", "precise"),
     "첫 줄에 <!-- metaprompt route=creative|precise tier=… domain=… mode=… --> 가 없다. 경로가 없으면 검사도 재생성도 기준을 잃는다."),
    ("기준점이 구체적", lambda s, t, m, d, r: re.search(r"\d", _section(s, "기준점 상세")) is not None,
     "기준점 상세에 수치가 없다. '업계 최고' 는 기준점이 아니다."),
    ("사실 3개 이상", lambda s, t, m, d, r: len(re.findall(r"^\s*[-*]\s+\S", _section(s, "기준점 상세"), re.M)) >= 3,
     "기준점 상세에 `-` 불릿이 3개 미만이다. lite 라도 (출처 미확인) 을 달고 3개는 넣는다."),
    ("실행 예산 섹션", lambda s, t, m, d, r: _has(s, r"^#{1,3}\s*실행 예산"),
     "실행 예산 섹션이 없다. 티어가 박혀 있지 않으면 받는 모델이 자기 기준으로 팬아웃한다."),
    ("메인 세션 effort", lambda s, t, m, d, r: _has(s, r"메인 세션 effort\s*\*\*(low|medium|high|xhigh|max)\*\*") and _has(s, r"--effort\s+(low|medium|high)"),
     "메인 세션의 권장 effort(`claude --effort <값>`)가 없다. Opus 5.5 기본은 medium 이고 경로마다 다르다."),
    ("메인 세션 model", lambda s, t, m, d, r: _has(s, r"claude --model\s+(opus|sonnet|haiku|fable)\b"),
     "시작 커맨드에 `--model <별칭>` 이 없다. 빼면 계정 기본 모델로 떠서 빌더가 검증자보다 작은 모델이 된다 (실측)."),
    ("역할 표 model·effort", lambda s, t, m, d, r: bool(_roles(s)) and not any(role_errors(x) for x in _roles(s)),
     "실행 예산의 역할 표가 없거나, model·effort 가 빠졌거나 잘못된 행이 있다 (haiku 는 effort '—')."),
    ("역할 표 = contract", lambda s, t, m, d, r: _roles_match_contract(s),
     "역할 표의 mp-* 행이 contract.md 의 model·effort 와 다르다. 값은 contract 에서만 가져온다."),
    ("effort 지정 방법", lambda s, t, m, d, r: _has(s, r"frontmatter") and _has(s, r"agents\.py|\.claude/agents"),
     "effort 를 에이전트 정의 frontmatter 로 준다는 방법(agents.py·.claude/agents)이 없다. Agent 호출에는 effort 가 없다."),
    ("모델 ID 하드코딩 없음", lambda s, t, m, d, r: not re.search(MODEL_ID, s),
     "`claude-…` 모델 ID 가 있다. 별칭 해석은 제공자마다 다르다 — 역할과 별칭으로 적는다."),
    ("스위치 agent teams", lambda s, t, m, d, r: (_switch(s, "agent teams") or "") in ("ON", "OFF"),
     "`- agent teams **ON|OFF** — 이유` 줄이 없다."),
    ("스위치 Workflow", lambda s, t, m, d, r: (_switch(s, "Workflow") or "") in ("ON", "OFF"),
     "`- Workflow **ON|OFF** — 이유` 줄이 없다."),
    ("스위치 루프", lambda s, t, m, d, r: re.search(r"ON|OFF", _switch(s, "루프") or "") is not None,
     "`- 루프 **/goal ON | 내부 라운드 (/goal·/loop OFF) | /loop ON** — 이유` 줄이 없다."),
    ("턴 종료 규약", lambda s, t, m, d, r: _has(s, r"텍스트만 있는 턴") and _has(s, r"자동 재개[^\n]*\d\s*회"),
     "무인 루프 완료 규약(텍스트만 있는 턴은 완료 아님 · 남은 체크리스트 재주입 · 자동 재개 상한)이 없다."),
    ("검증 보고 범위", lambda s, t, m, d, r: re.search(r"보고 범위[^\n]*체크리스트[^\n]*정확성", _section(s, "검증")) is not None,
     "검증자의 보고 범위를 체크리스트 항목과 정확성으로 한정하는 문장이 없다. 새 컨텍스트 리뷰어는 멀쩡해도 뭔가를 보고한다."),
    ("과잉 검증 문구 없음", lambda s, t, m, d, r: not re.search(r"double[- ]?check|한 번 더 검증|재차 검증|다시 한 번 확인", s, re.I),
     "'double-check'·'한 번 더 검증' 류 문구가 있다. Opus 5.x 에서 과잉 검증을 부른다."),
    ("사전조건 섹션", lambda s, t, m, d, r: re.search(r"^\|", _section(s, "사전조건"), re.M) is not None,
     "사전조건(검증 도구) 섹션이나 그 표가 없다."),
    ("보고 30줄 규약", lambda s, t, m, d, r: _has(s, r"30줄"), "서브에이전트 보고 30줄 제한이 없다."),
    ("판정문 파일 규약", lambda s, t, m, d, r: _has(s, r"verdicts/round"), "판정문 verdicts/round-N.md 규약이 없다."),
    ("순차 섹션", lambda s, t, m, d, r: _has(s, r"순차로 진행할 것"), "순차 통이 없다."),
    ("순차 이유 명시", lambda s, t, m, d, r: "이유" in _section(s, "순차로 진행할 것"),
     "순차 항목에 이유가 없다. 이유가 없으면 받는 모델이 효율을 이유로 쪼갠다."),
    ("검증자 분리", lambda s, t, m, d, r: _has(s, r"별개의?\*{0,2}\s*검증", r"자기가 만든 걸 자기가 채점"),
     "생성자와 채점자를 분리하는 문장이 없다."),
    ("검증 증거 획득 방법", lambda s, t, m, d, r: _has(_section(s, "검증"),
        r"(google-chrome|chromium|python|node|curl|pytest|bash|make |npm |cargo |go test|git |재현|계측|측정|렌더|exit)"),
     "검증 섹션에 실행 가능한 증거 획득 방법이 없다."),
    ("체크리스트 개수", lambda s, t, m, d, r: len(_checklist_items(s)) >= (_num("C", t) or 4),
     "체크리스트 항목이 contract 의 C 최소치 미만이다."),
    ("체크리스트가 Yes/No", lambda s, t, m, d, r: not any(re.search(r"(좋은가|예쁜가|자연스러운가|잘 동작하는가|보기 좋은가|괜찮은가)\s*$", i)
                                                        for i in _checklist_items(s)),
     "'좋은가'로 끝나는 항목이 있다. 측정 가능한 문장으로 다시 써라."),
    ("종료 조건에 숫자", lambda s, t, m, d, r: re.search(r"\d", _section(s, "종료 조건")) is not None, "종료 조건에 숫자가 없다."),
    ("라운드 상한", lambda s, t, m, d, r: _has(s, r"최대\s*\d+\s*라운드"), "라운드 상한이 없다."),
    ("정체 감지", lambda s, t, m, d, r: _has(s, r"\d\s*라운드\s*연속"), "정체 감지 문단이 없다."),
    ("수용된 제약 규약", lambda s, t, m, d, r: _has(s, r"수용된 제약"), "수용된 제약 규약이 없다."),
    ("처방 대조", lambda s, t, m, d, r: _has(s, r"처방"), "검증자의 처방을 체크리스트 전체와 대조하라는 문장이 없다."),
    ("완료 후 절차", lambda s, t, m, d, r: _has(s, r"^#{1,3}\s*완료 후"), "완료 후 무엇을 남기고 멈출지가 없다."),
    ("자리표시자 잔존 없음", lambda s, t, m, d, r: "{{" not in s, "템플릿 자리표시자 {{...}} 가 남아 있다."),
    ("조건 표식 잔존 없음", lambda s, t, m, d, r: not re.search(r"\[\[/?%s\]\]" % MARKERS, s), "템플릿 조건 표식 [[...]] 이 남아 있다."),
]

TIER = [
    ("팬아웃 섹션 (티어)", lambda s, t, m, d, r: (t == "lite") != _has(s, r"병렬로 진행할 것"),
     "lite 는 팬아웃 섹션이 없어야 하고, standard·max 는 있어야 한다."),
    ("라운드 상한 ≤ contract M", lambda s, t, m, d, r: int(re.search(r"최대\s*(\d+)\s*라운드", s).group(1)) <= (_num("M", t) or 5),
     "라운드 상한이 contract 의 M 을 넘는다. --rounds 로 의도한 것이면 헤더의 tier 를 올려라."),
    ("팬아웃 ≤ contract K", lambda s, t, m, d, r: t == "lite" or all(int(k) <= (_num("K", t) or 5)
                                                                   for k in re.findall(r"최대\s*\*\*(\d+)개\*\*", s)),
     "팬아웃 동시 수가 contract 의 K 를 넘는다."),
    ("lite 는 teams·Workflow OFF", lambda s, t, m, d, r: t != "lite" or (_switch(s, "agent teams") != "ON" and _switch(s, "Workflow") != "ON"),
     "lite 에서 agent teams 나 Workflow 가 ON 이다. contract 의 ON 조건(standard+)을 어긴다."),
]

ROUTE = {
    "creative": [
        ("앞서기 항목", lambda s, t, m, d, r: any(i.startswith("앞서기") and _baseline_token(s) in i for i in _checklist_items(s)),
         "체크리스트에 '앞서기: <기준점>에는 없는 …' 항목이 없다 (기준점 이름 포함). 따라잡기만 하면 복제품이 나온다."),
        ("기본기 항목", lambda s, t, m, d, r: any(i.startswith("기본기") for i in _checklist_items(s)) and _has(_section(s, "검증"), r"콜드 패스"),
         "체크리스트에 '기본기: …' 항목이나 검증 절의 콜드 패스가 없다. 빌더는 프롬프트를 닫힌 명세로 읽어 주제가 함의하는 기본기를 뺀다 (실측)."),
        ("범위 밖 문구 없음", lambda s, t, m, d, r: not re.search(r"범위 밖", s.split("## 검증")[0].replace("범위 밖이 아니다", "")),
         "목표·예산 절에 '범위 밖' 문장이 있다. 적힌 제외는 그 축의 상한이 된다 (실측: 좁은 폭). 증거 범위만 줄이고 제품 범위는 줄이지 않는다."),
    ],
    "precise": [
        ("빨강 먼저", lambda s, t, m, d, r: _has(s, r"round 0: red") and _has(s, r"exit\s*(≠|!=)\s*0"),
         "실패하는 회귀 테스트를 먼저 쓰고 exit ≠ 0 을 확인해 `round 0: red` 로 커밋하는 단계가 없다."),
        ("테스트 잠금", lambda s, t, m, d, r: _has(s, r"git diff\s*<?red"),
         "red 이후 테스트 파일이 바뀌지 않았음을 보는 `git diff <red SHA>..HEAD -- <테스트>` 가 없다."),
        ("종료 = 종료 코드", lambda s, t, m, d, r: re.search(r"종료 코드|exit 0", _section(s, "종료 조건")) is not None,
         "종료 조건이 테스트 커맨드의 종료 코드가 아니다."),
        ("리서치 서브에이전트 0", lambda s, t, m, d, r: not any(re.search(r"리서|research", x["role"] + x["name"], re.I) for x in _roles(s))
                                                    and not re.search(r"리서치|조사", _section(s, "병렬로 진행할 것")),
         "precise 인데 리서치 역할이나 리서치 팬아웃이 있다. 기준점은 base commit·명세다."),
        ("/goal 줄", lambda s, t, m, d, r: "/goal" not in (_switch(s, "루프") or "") or _has(s, r"`/goal\s+\S"),
         "루프가 /goal 인데 첫 입력으로 쓸 `/goal <조건>` 줄이 없다."),
    ],
}

DOMAIN = {
    "product": [("렌더 검증", lambda s, t, m, d, r: _has(s, r"렌더"), "제품 도메인인데 실제 렌더링 지시가 없다.")],
    "research": [("기각 경로", lambda s, t, m, d, r: _has(s, r"기각"), "연구 도메인인데 기각 종료 경로가 없다.")],
    "system": [("등가성·회귀 0건", lambda s, t, m, d, r: _has(s, r"등가성|동일 입력") and _has(s, r"회귀 0건"),
                "시스템 도메인인데 등가성 확인 또는 회귀 0건 조건이 없다.")],
}

WORKTREE = [
    ("작업 격리 섹션", lambda s, t, m, d, r: _has(s, r"^#{1,3}\s*작업 격리"), "작업 격리 섹션이 없다."),
    ("base commit SHA", lambda s, t, m, d, r: re.search(r"base commit\s*`?[0-9a-f]{7,40}", s) is not None, "base commit SHA 가 없다."),
    ("회귀 통 분리", lambda s, t, m, d, r: _has(s, r"회귀 통") and len(re.findall(r"^\s*-\s*\[\s*\]", _section(s, "검증").split("체크리스트 — 전 항목")[0], re.M)) >= 3,
     "회귀 통이 없거나 3항목 미만이다."),
    ("공유 상태 금지 목록", lambda s, t, m, d, r: _has(s, r"건드리지 마라") and _has(s, r"git push"), "worktree 밖 공유 상태 금지 목록이 없다."),
    ("검증자 diff 근거", lambda s, t, m, d, r: _has(s, r"git diff\s+[0-9a-f]{7,}"), "검증자가 base commit 대비 diff 를 보도록 지정돼 있지 않다."),
    ("병합은 사람이", lambda s, t, m, d, r: _has(s, r"병합하지 마", r"병합 여부는 사람"), "스스로 병합하지 않도록 막는 문장이 없다."),
]


def run_checks(s, tier=None, mode=None):
    meta = _meta(s)
    tier = tier or meta.get("tier", "standard")
    mode = mode or meta.get("mode", "greenfield")
    domain, route = meta.get("domain", ""), meta.get("route", "")
    checks = COMMON + TIER + ROUTE.get(route, []) + DOMAIN.get(domain, []) + (WORKTREE if mode == "worktree" else [])
    out = []
    for name, fn, hint in checks:
        try:
            ok = bool(fn(s, tier, mode, domain, route))
        except Exception:
            ok = False
        out.append((name, ok, hint))
    return (tier, mode, domain, route), out


def check_prompt(path, tier=None, mode=None):
    (tier, mode, domain, route), res = run_checks(_read(path), tier, mode)
    print("%s  (route=%s tier=%s mode=%s domain=%s)" % (path, route or "?", tier, mode, domain or "?"))
    for name, ok, _ in res:
        print("  %s %s" % ("PASS" if ok else "FAIL", name))
    n = len(_checklist_items(_read(path)))
    if n > (_num("C", tier, 1) or 8) + 1:
        print("  WARN 체크리스트가 %d개다. contract 의 C 상한을 넘으면 상충 위험이 급격히 커진다." % n)
    for name, ok, hint in res:
        if not ok:
            print("    → %s: %s" % (name, hint))
    return all(ok for _, ok, _ in res)


# 음성 케이스 — (픽스처 접두어, 이름, 변형 함수, 잡혀야 하는 검사 이름)
NEGATIVE = [
    ("lite-creative", "effort 칸 비우기", lambda s: re.sub(r"(\|\s*mp-verifier\s*\|\s*opus\s*\|)\s*high\s*\|", r"\1  |", s), "역할 표 model·effort"),
    ("lite-creative", "contract 와 다른 effort", lambda s: re.sub(r"(\|\s*mp-verifier\s*\|\s*opus\s*\|)\s*high\s*\|", r"\1 low |", s), "역할 표 = contract"),
    ("lite-creative", "haiku 에 effort", lambda s: s.replace("| mp-verifier | opus | high |", "| mp-verifier | haiku | high |"), "역할 표 model·effort"),
    ("lite-creative", "모델 ID 하드코딩", lambda s: s.replace("| mp-verifier | opus |", "| mp-verifier | claude-opus-5-5 |"), "모델 ID 하드코딩 없음"),
    ("lite-creative", "역할 표 삭제", lambda s: re.sub(r"(?m)^\s*\|\s*역할\s*\|.*\n(\s*\|.*\n)*", "", s), "역할 표 model·effort"),
    ("lite-creative", "effort 지정 방법 삭제", lambda s: s.replace("frontmatter", "설정"), "effort 지정 방법"),
    ("lite-creative", "메인 effort 삭제", lambda s: re.sub(r"(?m)^- 메인 세션 effort.*\n", "", s), "메인 세션 effort"),
    ("lite-creative", "teams 줄 삭제", lambda s: re.sub(r"(?m)^\s*- agent teams.*\n", "", s), "스위치 agent teams"),
    ("lite-creative", "Workflow 이유 삭제", lambda s: re.sub(r"(?m)^(\s*- Workflow \*\*\w+\*\*).*$", r"\1", s), "스위치 Workflow"),
    ("lite-creative", "루프 줄 삭제", lambda s: re.sub(r"(?m)^\s*- 루프 \*\*.*\n", "", s), "스위치 루프"),
    ("lite-creative", "lite 에서 teams ON", lambda s: re.sub(r"agent teams \*\*OFF\*\*", "agent teams **ON**", s), "lite 는 teams·Workflow OFF"),
    ("lite-creative", "턴 종료 규약 삭제", lambda s: re.sub(r"(?m)^- 턴 종료 규약.*\n", "", s), "턴 종료 규약"),
    ("lite-creative", "보고 범위 삭제", lambda s: re.sub(r"(?m)^보고 범위는.*\n", "", s), "검증 보고 범위"),
    ("lite-creative", "double-check 문구", lambda s: s.replace("## 종료 조건", "결과는 double-check 해라.\n\n## 종료 조건", 1), "과잉 검증 문구 없음"),
    ("lite-creative", "앞서기 항목 삭제", lambda s: re.sub(r"(?m)^- \[ \] 앞서기.*\n", "", s), "앞서기 항목"),
    ("lite-creative", "기본기 항목 삭제", lambda s: re.sub(r"(?m)^- \[ \] 기본기.*\n", "", s), "기본기 항목"),
    ("lite-creative", "콜드 패스 삭제", lambda s: s.replace("콜드 패스", "사전 점검"), "기본기 항목"),
    ("lite-creative", "범위 밖 문장", lambda s: s.replace("## 기준점 상세", "좁은 폭은 이번 티어 범위 밖이다.\n\n## 기준점 상세", 1), "범위 밖 문구 없음"),
    ("lite-creative", "시작 커맨드에서 모델 삭제", lambda s: s.replace("claude --model opus --effort", "claude --effort"), "메인 세션 model"),
    ("lite-creative", "경로 없는 헤더", lambda s: s.replace("route=creative ", "", 1), "헤더 메타"),
    ("lite-creative", "자리표시자 잔존", lambda s: s.replace("## 기준점 상세\n", "## 기준점 상세\n\n- {{사실}}\n", 1), "자리표시자 잔존 없음"),
    ("lite-precise", "빨강 먼저 삭제", lambda s: s.replace("round 0: red", "round 0: 테스트"), "빨강 먼저"),
    ("lite-precise", "테스트 잠금 삭제", lambda s: re.sub(r"git diff\s*<?red[^`\n]*", "git status", s), "테스트 잠금"),
    ("lite-precise", "종료 조건을 의견으로", lambda s: re.sub(r"(?ms)(^## 종료 조건\n).*?(?=^## )", r"\1검증자가 만족하면 끝 · 최대 2라운드.\n\n", s), "종료 = 종료 코드"),
    ("lite-precise", "리서처 역할 추가", lambda s: s.replace("| mp-verifier | opus | high |", "| 리서처 | researcher | sonnet | low | 기준점 조사 |\n  | 검증자 | mp-verifier | opus | high |", 1), "리서치 서브에이전트 0"),
    ("lite-precise", "/goal 줄 삭제", lambda s: re.sub(r"(?m)^.*`/goal .*\n", "", s), "/goal 줄"),
    ("standard-precise", "팬아웃에 리서치", lambda s: s.replace("## 병렬로 진행할 것 (서브에이전트 팬아웃)\n", "## 병렬로 진행할 것 (서브에이전트 팬아웃)\n\n- 외부 리서치: 유사 사례 조사\n", 1), "리서치 서브에이전트 0"),
    ("lite-creative", "구 형식 모델 ID", lambda s: s.replace("| mp-verifier | opus |", "| mp-verifier | claude-3-5-sonnet |"), "모델 ID 하드코딩 없음"),
    ("lite-creative", "펜스 속 # 주석 뒤 앞서기 삭제", lambda s: re.sub(r"(?m)^- \[ \] 앞서기.*\n", "", s.replace("```\n검증자는", "```\n# 캡처\n검증자는", 1)), "앞서기 항목"),
    ("standard-precise", "팬아웃 K 초과", lambda s: re.sub(r"최대 \*\*\d+개\*\*", "최대 **9개**", s), "팬아웃 ≤ contract K"),
]


def _fixtures():
    fx_dir = os.path.join(SKILL, "fixtures")
    return sorted(os.path.join(fx_dir, f) for f in os.listdir(fx_dir) if f.endswith(".md")) if os.path.isdir(fx_dir) else []


def _line(ok, msg):
    print("  %s %s" % ("PASS" if ok else "FAIL", msg))
    return ok


REQUIRED = ["SKILL.md", "references/contract.md", "references/creative.md", "references/precise.md", "references/template.md",
            "references/product.md", "references/research.md", "references/system.md", "references/worktree.md",
            "references/tools.md", "scripts/detect_env.py", "scripts/agents.py"]
TEMPLATE_HEADINGS = ["# 목표", "## 기준점 상세", "## 작업 격리", "## 실행 예산", "## 사전조건", "## 병렬로 진행할 것",
                     "## 순차로 진행할 것", "## 검증", "## 종료 조건", "## 완료 후"]


def self_test():
    ok = True
    print("-- 구조")
    for p in REQUIRED:
        ok &= _line(os.path.exists(os.path.join(SKILL, p)), p)

    print("-- SKILL.md")
    sk = _read(os.path.join(SKILL, "SKILL.md"))
    fm = re.match(r"^---\n(.*?)\n---\n", sk, re.S)
    f = fm.group(1) if fm else ""
    ok &= _line(bool(fm), "프론트매터")
    name = re.search(r"^name:\s*(\S+)", f, re.M)
    ok &= _line(bool(name) and name.group(1) == os.path.basename(SKILL), "name == 디렉터리명")
    desc = "".join(re.findall(r'^(?:description|when_to_use):\s*"(.*)"\s*$', f, re.M))
    ok &= _line(0 < len(desc) <= 1536, "description + when_to_use %d자 (1,536 이하)" % len(desc))
    for key, label in [("쓰지 않음", "when_to_use 에 사용 금지 조건"), ("--tier", "argument-hint 에 --tier"),
                       ("--route-only", "argument-hint 에 --route-only")]:
        ok &= _line(key in f, label)
    eff = re.search(r"^effort:\s*(\S+)", f, re.M)
    ok &= _line(not eff or eff.group(1) in ("low", "medium", "high"), "스킬 effort 가 low·medium·high")
    lines = sk.count("\n")
    ok &= _line(lines < 500, "SKILL.md %d줄 (500 미만)" % lines)
    for route in ("skip", "precise", "creative", "--route-only"):
        ok &= _line(route in sk, "라우팅 규칙에 %s" % route)

    print("-- 계약 단일화 (contract.md)")
    for k in "MKSCRQ":
        ok &= _line(all(_num(k, t) is not None for t in TIERS), "티어 키 %s 세 칸 %s" % (k, "/".join(C["tier"].get(k, {}).values())))
    ok &= _line(_num("M", "lite") <= _num("M", "standard") <= _num("M", "max"), "M 이 티어 순으로 단조")
    ok &= _line(len(C["roles"]) >= 5, "역할 표 %d행" % len(C["roles"]))
    for r in C["roles"]:
        ok &= _line(not role_errors(r), "역할 %s: model=%s effort=%s" % (r["role"], r["model"], r["effort"]))
    skill_files = [os.path.join(dp, fn) for dp, _, fns in os.walk(SKILL) for fn in fns if fn.endswith(".md") and "fixtures" not in dp]
    tiers_dup = [p for p in skill_files if not p.endswith("contract.md") and re.search(r"\|\s*2\s*\|\s*3\s*\|\s*5\s*\|", _read(p))]
    ok &= _line(not tiers_dup, "티어 수치 표가 contract 밖에 없다 %s" % [os.path.relpath(p, SKILL) for p in tiers_dup])
    roles_dup = [p for p in skill_files if not p.endswith("contract.md") and re.search(r"\|\s*mp-verifier\s*\|\s*opus", _read(p))]
    ok &= _line(not roles_dup, "역할→모델 표가 contract 밖에 없다 %s" % [os.path.relpath(p, SKILL) for p in roles_dup])
    ids = [os.path.relpath(p, SKILL) for p in skill_files if re.search(MODEL_ID, _read(p))]
    ok &= _line(not ids, "스킬 파일에 모델 ID 하드코딩 0건 %s" % ids)
    plug = os.path.join(os.path.dirname(os.path.dirname(SKILL)), "agents")
    for fn in ("researcher.md", "scout.md"):
        p = os.path.join(plug, fn)
        if not os.path.exists(p):
            ok &= _line(False, "플러그인 agents/%s" % fn)
            continue
        t = _read(p)
        c = _contract_row(fn[:-3]) or {}
        mm = re.search(r"^model:\s*(\S+)", t, re.M)
        ee = re.search(r"^effort:\s*(\S+)", t, re.M)
        ok &= _line(bool(mm and ee) and mm.group(1) == c.get("model") and ee.group(1) == c.get("effort"),
                    "플러그인 agents/%s frontmatter == contract (%s/%s)" % (fn, c.get("model"), c.get("effort")))

    print("-- template")
    tpl = _read(os.path.join(SKILL, "references/template.md"))
    opens = re.findall(r"\[\[%s\]\]" % MARKERS, tpl)
    closes = re.findall(r"\[\[/%s\]\]" % MARKERS, tpl)
    ok &= _line(sorted(opens) == sorted(closes), "조건 표식 균형 (%d/%d)" % (len(opens), len(closes)))
    for mk in ("creative", "precise"):
        ok &= _line(mk in opens, "조건 표식 [[%s]] 존재" % mk)
    for h in TEMPLATE_HEADINGS:
        ok &= _line(h in tpl, "섹션 %s" % h)
    for key in ("agent teams **", "Workflow **", "루프 **", "메인 세션 effort", "텍스트만 있는 턴", "보고 범위는", "앞서기:", "기본기:", "콜드 패스", "claude --model", "round 0: red"):
        ok &= _line(key in tpl, "template 에 `%s`" % key)

    print("-- lite 토큰 예산 (lite · product · greenfield 경로가 읽는 파일)")
    total = sum(os.path.getsize(os.path.join(SKILL, p)) for p in LITE_PATH)
    ok &= _line(total <= BASE_LITE_BYTES, "%s = %d B (base %d B 이하)" % (" + ".join(os.path.basename(p) for p in LITE_PATH), total, BASE_LITE_BYTES))

    print("-- 픽스처")
    fxs = _fixtures()
    ok &= _line(len(fxs) >= 3, "픽스처 %d개 (3 이상)" % len(fxs))
    routes = {_meta(_read(p)).get("route") for p in fxs}
    ok &= _line({"creative", "precise"} <= routes, "픽스처가 두 경로를 모두 덮는다 %s" % sorted(x for x in routes if x))
    for p in fxs:
        print("  -- 픽스처 %s" % os.path.basename(p))
        ok &= _line(check_prompt(p), "픽스처 %s 전 항목 통과" % os.path.basename(p))

    print("-- 음성 케이스 (누락을 FAIL 로 잡는가)")
    for prefix, label, mutate, expect in NEGATIVE:
        src = next((p for p in fxs if os.path.basename(p).startswith(prefix)), None)
        if not src:
            ok &= _line(False, "음성 %s — 픽스처 %s* 없음" % (label, prefix))
            continue
        s = _read(src)
        m = mutate(s)
        _, res = run_checks(m)
        caught = m != s and any(n == expect and not good for n, good, _ in res)
        ok &= _line(caught, "음성 %s → '%s' FAIL" % (label, expect))
    return ok


def repo_check(root):
    ok = True
    print("-- 버전 3곳")
    pj = json.load(io.open(os.path.join(root, ".claude-plugin/plugin.json"), encoding="utf-8"))["version"]
    mj = json.load(io.open(os.path.join(root, ".claude-plugin/marketplace.json"), encoding="utf-8"))["metadata"]["version"]
    cl = re.search(r"^## \[(\d+\.\d+\.\d+)\]", _read(os.path.join(root, "CHANGELOG.md")), re.M)
    cl = cl.group(1) if cl else None
    ok &= _line(pj == mj == cl, "plugin.json %s · marketplace.json %s · CHANGELOG %s" % (pj, mj, cl))

    print("-- README 수치 정합")
    rd = _read(os.path.join(root, "README.md"))
    n = rd.count("\n")
    ok &= _line(n <= 150, "README %d줄 (150 이하)" % n)
    total = sum(os.path.getsize(os.path.join(SKILL, p)) for p in LITE_PATH)
    for claim in re.findall(r"lite[^\n|]*?([\d,]{5,})\s*B", rd):
        ok &= _line(int(claim.replace(",", "")) in (total, BASE_LITE_BYTES), "README 의 lite 바이트 %s == 실측 %d 또는 base %d" % (claim, total, BASE_LITE_BYTES))
    for k in ("M", "K"):
        want = "/".join(str(_num(k, t)) for t in TIERS)
        if re.search(r"\b%s\b\s*\d+/\d+/\d+" % k, rd):
            ok &= _line(re.search(r"\b%s\b\s*%s\b" % (k, re.escape(want)), rd) is not None, "README 의 %s 수치 == contract %s" % (k, want))
    sm = os.path.join(root, "bench/chat-vs-lite/summary.json")
    if os.path.exists(sm):
        print("-- 실측 원자료 대조")
        summ = json.load(io.open(sm, encoding="utf-8"))
        for side in summ["sides"]:
            tot = {"cost": 0.0, "ms": 0, "in": 0, "out": 0}
            for fn in side["raw"]:
                d = json.load(io.open(os.path.join(root, "bench/chat-vs-lite", fn), encoding="utf-8"))
                tot["cost"] += d["total_cost_usd"]
                tot["ms"] += d["duration_ms"]
                for u in d["modelUsage"].values():
                    tot["in"] += u["inputTokens"] + u["cacheReadInputTokens"] + u["cacheCreationInputTokens"]
                    tot["out"] += u["outputTokens"]
                ok &= _line(not d.get("permission_denials"), "%s permission_denials 비어 있음" % fn)
            same = (round(tot["cost"], 2) == round(side["cost_usd"], 2) and tot["ms"] == side["duration_ms"]
                    and tot["in"] == side["input_tokens"] and tot["out"] == side["output_tokens"])
            ok &= _line(same, "%s: 원자료 합 $%.2f · %dms · in %d · out %d == summary" % (side["name"], tot["cost"], tot["ms"], tot["in"], tot["out"]))
            for cell in side["readme_cells"]:
                ok &= _line(cell in rd, "README 표에 `%s`" % cell)
    return ok


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    if "--self-test" in args:
        ok = self_test()
        print("\n%s self-test" % ("PASS" if ok else "FAIL"))
        return 0 if ok else 1
    if "--repo" in args:
        i = args.index("--repo")
        root = args[i + 1] if i + 1 < len(args) else os.path.dirname(os.path.dirname(SKILL))
        ok = repo_check(os.path.abspath(root))
        print("\n%s repo" % ("PASS" if ok else "FAIL"))
        return 0 if ok else 1
    tier = mode = None
    files = []
    i = 0
    while i < len(args):
        if args[i] in ("--tier", "--mode"):
            if args[i] == "--tier":
                tier = args[i + 1]
            else:
                mode = args[i + 1]
            i += 2
        else:
            files.append(args[i])
            i += 1
    ok = True
    for f in files:
        ok &= check_prompt(f, tier, mode)
        print()
    print("%s %d파일" % ("PASS" if ok else "FAIL", len(files)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
