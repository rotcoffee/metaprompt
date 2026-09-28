#!/usr/bin/env python3
"""생성된 메타프롬프트가 자가점검 항목을 만족하는지 기계적으로 검사한다.

    python3 check_prompt.py <프롬프트.md> [...] [--tier lite|standard|max] [--mode greenfield|worktree]
    python3 check_prompt.py --self-test            스킬 디렉터리 구조와 픽스처를 검사

티어·모드·도메인은 프롬프트 첫 줄의 `<!-- metaprompt tier=… domain=… mode=… -->` 에서 읽고, 플래그가 오면 덮어쓴다.
모델이 "다 넣었다"고 믿는 것과 실제로 들어간 것은 다르다. 이 스크립트가 그 차이를 잡는다.
oneshot-prompt(chanp5660, MIT) 의 tests/check_prompt.py 를 티어 인식형으로 개작했다.
"""
import io
import os
import re
import sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIER_MAX_ROUNDS = {"lite": 2, "standard": 3, "max": 5}
TIER_MIN_ITEMS = {"lite": 4, "standard": 6, "max": 7}


def _has(s, *pats):
    return any(re.search(p, s, re.M | re.S) for p in pats)


def _section(s, heading):
    """'## heading' 부터 다음 '## ' 전까지."""
    m = re.search(r"^#{1,3}\s*%s[^\n]*\n(.*?)(?=^#{1,3}\s|\Z)" % heading, s, re.M | re.S)
    return m.group(1) if m else ""


def _meta(s):
    m = re.search(r"<!--\s*metaprompt\s+([^>]*?)-->", s, re.S)
    meta = {}
    if m:
        for k, v in re.findall(r"(\w+)=(\"[^\"]*\"|\S+)", m.group(1)):
            meta[k] = v.strip('"')
    return meta


def _checklist_items(s):
    """도메인 체크리스트 항목 (회귀 통 제외)."""
    body = _section(s, "검증")
    if "회귀 통" in body:
        body = body.split("체크리스트 — 전 항목", 1)[-1]
    return re.findall(r"^\s*-\s*\[\s*\]\s*(.+)$", body, re.M)


# (이름, 판정 함수(s, tier, mode, domain), 실패 시 안내)
COMMON = [
    ("헤더 메타", lambda s, t, m, d: all(k in _meta(s) for k in ("tier", "domain", "mode")),
     "첫 줄에 <!-- metaprompt tier=… domain=… mode=… --> 가 없다. 재생성·티어 승격의 기준이 사라진다."),
    ("기준점이 구체적", lambda s, t, m, d: _has(s, r"기준점 상세") and re.search(r"\d", _section(s, "기준점 상세")) is not None,
     "기준점 상세에 수치가 없다. '업계 최고' 같은 표현은 기준점이 아니다."),
    ("리서치 사실 3개 이상", lambda s, t, m, d: len(re.findall(r"^\s*[-*]\s+\S", _section(s, "기준점 상세"), re.M)) >= 3,
     "기준점 상세에 `-`/`*` 불릿이 3개 미만이다 (번호 목록은 세지 않는다). lite 라도 (출처 미확인) 표시를 달고 3개는 넣는다."),
    ("실행 예산 섹션", lambda s, t, m, d: _has(s, r"^#{1,3}\s*실행 예산"),
     "실행 예산 섹션이 없다. 티어가 프롬프트에 박혀 있지 않으면 받는 모델이 자기 기준으로 팬아웃한다."),
    ("사전조건 섹션", lambda s, t, m, d: _has(s, r"^#{1,3}\s*사전조건") and re.search(r"^\|", _section(s, "사전조건"), re.M) is not None,
     "사전조건(검증 도구) 섹션이나 그 표가 없다. 실행 세션이 도구 없이 상상으로 채점하게 된다."),
    ("보고 30줄 규약", lambda s, t, m, d: _has(s, r"30줄"),
     "서브에이전트 보고를 30줄로 제한하는 문장이 없다. 부모 컨텍스트가 라운드마다 부푼다."),
    ("판정문 파일 규약", lambda s, t, m, d: _has(s, r"verdicts/round"),
     "판정문을 verdicts/round-N.md 에 남기는 규약이 없다. 실패 항목만 넘기는 절약이 불가능해진다."),
    ("순차 섹션", lambda s, t, m, d: _has(s, r"순차로 진행할 것"),
     "순차 통이 없다."),
    ("순차 이유 명시", lambda s, t, m, d: "이유" in _section(s, "순차로 진행할 것"),
     "순차 항목에 이유가 없다. 이유가 없으면 받는 모델이 효율을 이유로 쪼갠다."),
    ("검증자 분리", lambda s, t, m, d: _has(s, r"별개의?\s*검증", r"자기가 만든 걸 자기가 채점"),
     "생성자와 검증자를 분리하는 문장이 없다."),
    ("검증 증거 획득 방법", lambda s, t, m, d: _has(_section(s, "검증"),
        r"(google-chrome|chromium|firefox|python|node|curl|pytest|bash|make |npm |cargo |go test|git worktree|재현|계측|측정|렌더)"),
     "검증자가 증거를 어떻게 얻는지 실행 가능한 방법이 검증 섹션에 없다. 비우면 검증자가 상상으로 채점한다."),
    ("체크리스트 개수", lambda s, t, m, d: len(_checklist_items(s)) >= TIER_MIN_ITEMS.get(t, 5),
     "체크리스트 항목이 티어 최소치(lite 4 · standard 6 · max 7) 미만이다."),
    ("체크리스트가 Yes/No", lambda s, t, m, d: not any(re.search(r"(좋은가|예쁜가|자연스러운가|잘 동작하는가|보기 좋은가|괜찮은가)\s*$", i)
                                                  for i in _checklist_items(s)),
     "'좋은가'로 끝나는 항목이 있다. 측정 가능한 문장으로 다시 써라."),
    ("종료 조건에 숫자", lambda s, t, m, d: re.search(r"\d", _section(s, "종료 조건")) is not None,
     "종료 조건에 숫자(지표·라운드 상한)가 없다."),
    ("라운드 상한", lambda s, t, m, d: _has(s, r"최대\s*\d+\s*라운드"),
     "라운드 상한이 없다. 무한 루프로 비용이 샌다."),
    ("정체 감지", lambda s, t, m, d: _has(s, r"\d\s*라운드\s*연속"),
     "정체 감지 문단이 없다. 같은 자리를 맴돌며 토큰만 태우는 경우가 실패보다 훨씬 비싸다."),
    ("수용된 제약 규약", lambda s, t, m, d: _has(s, r"수용된 제약"),
     "수용된 제약 규약이 없다. 해결 불가능한 지적이 정체 감지를 잘못 발동시킨다."),
    ("처방 대조", lambda s, t, m, d: _has(s, r"처방"),
     "검증자의 처방을 체크리스트 전체와 대조하라는 문장이 없다. 한 항목을 고치며 다른 항목을 깬다."),
    ("완료 후 절차", lambda s, t, m, d: _has(s, r"^#{1,3}\s*완료 후"),
     "완료 후 무엇을 남기고 멈출지가 없다."),
    ("자리표시자 잔존 없음", lambda s, t, m, d: "{{" not in s,
     "템플릿 자리표시자 {{...}} 가 채워지지 않은 채 남아 있다."),
    ("조건 표식 잔존 없음", lambda s, t, m, d: not re.search(r"\[\[/?(lite|standard\+|max|worktree|greenfield)\]\]", s),
     "템플릿 조건 표식 [[...]] 이 출력에 남아 있다."),
]

TIER = [
    ("팬아웃 섹션 (티어)", lambda s, t, m, d: (t == "lite") != _has(s, r"병렬로 진행할 것"),
     "lite 는 팬아웃 섹션이 없어야 하고, standard·max 는 있어야 한다."),
    ("라운드 상한 ≤ 티어", lambda s, t, m, d: int(re.search(r"최대\s*(\d+)\s*라운드", s).group(1)) <= TIER_MAX_ROUNDS.get(t, 5)
        if re.search(r"최대\s*(\d+)\s*라운드", s) else False,
     "라운드 상한이 티어 상한(lite 2 · standard 3 · max 5)을 넘는다. --rounds 로 의도한 것이면 헤더의 tier 를 올려라."),
]

DOMAIN = {
    "product": [("렌더 검증", lambda s, t, m, d: _has(s, r"렌더"), "제품 도메인인데 실제 렌더링 지시가 없다.")],
    "research": [("기각 경로", lambda s, t, m, d: _has(s, r"기각"), "연구 도메인인데 기각 종료 경로가 없다. 가설이 틀려도 루프가 계속 고치려 든다.")],
    "system": [("등가성·회귀 0건", lambda s, t, m, d: _has(s, r"등가성|동일 입력") and _has(s, r"회귀 0건"),
                "시스템 도메인인데 등가성 확인 또는 회귀 0건 조건이 없다. 정확성을 깎아 얻은 속도를 막지 못한다.")],
}

WORKTREE = [
    ("작업 격리 섹션", lambda s, t, m, d: _has(s, r"^#{1,3}\s*작업 격리"),
     "작업 격리 섹션이 없다. worktree 경로·브랜치·base commit 이 없으면 격리가 말뿐이다."),
    ("base commit SHA", lambda s, t, m, d: re.search(r"base commit\s*`?[0-9a-f]{7,40}", s) is not None,
     "base commit SHA 가 없다. 회귀를 판정할 기준이 사라진다."),
    ("회귀 통 분리", lambda s, t, m, d: _has(s, r"회귀 통") and len(re.findall(r"^\s*-\s*\[\s*\]", _section(s, "검증").split("체크리스트 — 전 항목")[0], re.M)) >= 3,
     "회귀 통이 없거나 3항목 미만이다. 기존 저장소에서는 깨뜨릴 것이 있고, 도메인 통과 따로 세야 한다."),
    ("공유 상태 금지 목록", lambda s, t, m, d: _has(s, r"건드리지 마라") and _has(s, r"git push"),
     "worktree 밖 공유 상태에 대한 금지 목록이 없다. worktree 는 파일만 격리한다."),
    ("검증자 diff 근거", lambda s, t, m, d: _has(s, r"git diff\s+[0-9a-f]{7,}"),
     "검증자가 base commit 대비 diff 를 보도록 지정돼 있지 않다."),
    ("병합은 사람이", lambda s, t, m, d: _has(s, r"병합하지 마", r"병합 여부는 사람"),
     "프롬프트가 스스로 병합하지 않도록 막는 문장이 없다."),
]


def check_prompt(path, tier=None, mode=None):
    s = io.open(path, encoding="utf-8").read()
    meta = _meta(s)
    tier = tier or meta.get("tier", "standard")
    mode = mode or meta.get("mode", "greenfield")
    domain = meta.get("domain", "")
    print("%s  (tier=%s mode=%s domain=%s)" % (path, tier, mode, domain or "?"))
    checks = COMMON + TIER + DOMAIN.get(domain, []) + (WORKTREE if mode == "worktree" else [])
    fails = []
    for name, fn, hint in checks:
        try:
            ok = bool(fn(s, tier, mode, domain))
        except Exception:
            ok = False
        print("  %s %s" % ("PASS" if ok else "FAIL", name))
        if not ok:
            fails.append((name, hint))
    n = len(_checklist_items(s))
    if n > 9:
        print("  WARN 도메인 체크리스트가 %d개다. 8개를 넘으면 상충 위험이 급격히 커진다." % n)
    for name, hint in fails:
        print("    → %s: %s" % (name, hint))
    return not fails


REQUIRED = ["SKILL.md", "references/template.md", "references/product.md", "references/research.md",
            "references/system.md", "references/worktree.md", "references/tools.md", "scripts/detect_env.py"]
TEMPLATE_HEADINGS = ["# 목표", "## 기준점 상세", "## 작업 격리", "## 실행 예산", "## 사전조건", "## 병렬로 진행할 것",
                     "## 순차로 진행할 것", "## 검증", "## 종료 조건", "## 완료 후"]


def self_test():
    ok = True
    for p in REQUIRED:
        e = os.path.exists(os.path.join(SKILL, p))
        print("  %s %s" % ("PASS" if e else "FAIL", p))
        ok &= e

    sk = io.open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8").read()
    fm = re.match(r"^---\n(.*?)\n---\n", sk, re.S)
    if not fm:
        print("  FAIL SKILL.md 프론트매터 없음")
        ok = False
    else:
        f = fm.group(1)
        name = re.search(r"^name:\s*(\S+)", f, re.M)
        good = name and name.group(1) == os.path.basename(SKILL)
        print("  %s SKILL.md name == 디렉터리명" % ("PASS" if good else "FAIL"))
        ok &= bool(good)
        for key, label in [("사용 금지", "description 에 사용 금지 조건"), ("--tier", "argument-hint 에 --tier")]:
            hit = key in f
            print("  %s SKILL.md %s" % ("PASS" if hit else "FAIL", label))
            ok &= hit
    lines = sk.count("\n")
    print("  %s SKILL.md %d줄 (500 이하)" % ("PASS" if lines <= 500 else "FAIL", lines))
    ok &= lines <= 500

    tpl = io.open(os.path.join(SKILL, "references/template.md"), encoding="utf-8").read()
    opens = re.findall(r"\[\[(lite|standard\+|max|worktree|greenfield)\]\]", tpl)
    closes = re.findall(r"\[\[/(lite|standard\+|max|worktree|greenfield)\]\]", tpl)
    bal = sorted(opens) == sorted(closes)
    print("  %s template 조건 표식 균형 (%d/%d)" % ("PASS" if bal else "FAIL", len(opens), len(closes)))
    ok &= bal
    for h in TEMPLATE_HEADINGS:
        hit = h in tpl
        print("  %s template 섹션 %s" % ("PASS" if hit else "FAIL", h))
        ok &= hit

    fx_dir = os.path.join(SKILL, "fixtures")
    fxs = sorted(f for f in os.listdir(fx_dir) if f.endswith(".md")) if os.path.isdir(fx_dir) else []
    if not fxs:
        print("  FAIL fixtures/ 에 픽스처가 없다")
        ok = False
    for f in fxs:
        print("  -- 픽스처 %s" % f)
        r = check_prompt(os.path.join(fx_dir, f))
        print("  %s 픽스처 %s 전 항목 통과" % ("PASS" if r else "FAIL", f))
        ok &= r
    return ok


def main():
    args = sys.argv[1:]
    if not args or args == ["-h"] or args == ["--help"]:
        print(__doc__)
        return 2
    if "--self-test" in args:
        ok = self_test()
        print("\n%s self-test" % ("PASS" if ok else "FAIL"))
        return 0 if ok else 1
    tier = mode = None
    files = []
    i = 0
    while i < len(args):
        if args[i] == "--tier":
            tier = args[i + 1]; i += 2
        elif args[i] == "--mode":
            mode = args[i + 1]; i += 2
        else:
            files.append(args[i]); i += 1
    ok = True
    for f in files:
        ok &= check_prompt(f, tier, mode)
        print()
    print("%s %d파일" % ("PASS" if ok else "FAIL", len(files)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
