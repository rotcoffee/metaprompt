# metaprompt

**주제 한 줄 → 다른 세션에서 실행할 프롬프트 파일 하나** (또는 "만들 필요 없음" 한 줄). — Claude Code 플러그인.

```mermaid
---
config:
  flowchart:
    nodeSpacing: 12
    rankSpacing: 28
    wrappingWidth: 400
---
flowchart LR
  T["주제 한 줄"] --> R["자동 라우팅"]
  R -->|skip| S["채팅으로 돌려보냄 · 파일 없음"]
  R -->|precise| P["빨강 테스트 → 종료 코드 · /goal"]
  R -->|creative| C["기준점 + 앞서기 항목 · 검증자"]
  P --> F["프롬프트 파일"]
  C --> F
  F --> N["새 세션에서 실행"]
```

### ✅ 쓸 때 — 크고 채점할 수 있는 작업
- 새 화면·앱·도구를 만든다 → **creative** 프롬프트
- 원인 모를 버그 · 마이그레이션 · 성능 목표 → **precise** 프롬프트

### ❌ 쓰지 않을 때 — 그냥 채팅으로 시킨다
- 오타 · 설정값 하나 같은 **한 줄 수정**, **질문**, **코드 리뷰** → 스킬이 파일 없이 돌려보낸다

가장 가벼운 실행 = 주제 뒤에 `--tier lite` (플러그인 설치 시 이름은 `/metaprompt:metaprompt`):

```
/metaprompt calendar UI, single HTML file --tier lite
```

## 채팅 vs lite 실측

같은 주제 "업무용 캘린더 UI, 단일 HTML 파일" · opus · `--effort medium` · 같은 권한 플래그 · 빈 디렉터리. 채점은 두 결과물을 만든 적 없는 제3 에이전트가 같은 렌더·주입 절차로 ([grade.md](bench/chat-vs-lite/grade.md)).

| 측정 (원자료 `bench/chat-vs-lite/`) | 채팅 | lite (생성+실행) |
|---|---|---|
| 체크리스트 통과 (제3 채점자) | 0/5 | 5/5 |
| 비용 `total_cost_usd` | $1.07 | $2.56 |
| 시간 `duration_ms` | 3분 48초 | 8분 54초 |
| 출력 토큰 `modelUsage` | 27,628 | 56,793 |
| 입력 토큰 (캐시 포함) | 496,017 | 1,340,956 |
| 서브에이전트 | 0 | 1 |

- lite 가 **비용 2.4배 · 시간 2.3배**를 더 썼다. 그 값으로 산 것은 기준점 대비 "앞서기" 항목과 새 컨텍스트 검증자 1회다.
- 체크리스트는 lite 프롬프트의 것이라 채팅 쪽에 불리하다. 채팅 결과물도 주 보기·키보드 생성·일 보기를 **다른 방식으로** 부분 달성했다 (grade.md).
- 표본 1건이다. 작은 과업에서 구조화가 늘 이긴다는 근거가 아니다 — 그래서 한 줄짜리 주제는 skip 으로 돌려보낸다.

## 경로 3개 — 무엇이 켜지고 꺼지나

플래그 없이 판정한다. 두 경로 신호가 팽팽하면 가벼운 쪽(skip < precise < creative). `--route` 로 고정, `--route-only` 는 판정 한 줄만.

| | skip | precise | creative |
|---|---|---|---|
| 파일 | 없음 — 채팅 지시 한 줄 | 있음 | 있음 |
| 기준점 | — | base commit · 명세 조항 | 실명 제품·방법 + 수치 |
| 생성 시 리서치 | — | 0 (저장소 사실만) | 티어 R 만큼 리서처 |
| 먼저 박는 것 | — | 실패하는 회귀 테스트 → 잠금 | `앞서기:` 항목 (기준점에 없는 것) |
| 채점 | — | 종료 코드 + `/goal` 평가자, 검증자는 마지막 1회 | 새 컨텍스트 검증자 매 라운드 (+ standard+ 블라인드 심사자) |
| 종료 | — | 커맨드 종료 코드 0 | 전 항목 Yes (+ 블라인드 점수) |
| 루프 | — | `/goal` | 내부 라운드 |

도메인(product · research · system)은 경로가 아니라 **증거 방법**이다 — 렌더 · 재현/반증 · 계측.

## 티어 — 크기와 토큰

신호가 없으면 lite. "공개·팀·배포" → standard, "출시·경쟁 제품 옆·논문·SOTA" → max. `--tier` 로 고정.

| 키 (lite/standard/max) | 값 |
|---|---|
| 라운드 상한 | M 2/3/5 |
| 동시 팬아웃 | K 0/3/5 |
| 정체 판정 연속 라운드 | S 2/2/3 |
| 체크리스트 항목 | C 4-5 / 6-7 / 7-8 |
| 생성 시 리서치 에이전트 (creative) | R 0/1/3 |
| 체크포인트 | Q 1/2/2 |

티어가 깎는 것은 깊이다. 기준점 · 채점자 분리 · Yes/No 체크리스트 · 정체 감지 · 수용된 제약은 lite 에도 남는다.

## 역할별 모델·effort

- Agent 도구에는 effort 파라미터가 없다 → effort 는 에이전트 정의 frontmatter 로만 준다.
- 세션 도중 만든 정의는 그 세션에 로드되지 않는다 → 생성된 프롬프트의 역할 표를 `scripts/agents.py` 가 **세션 시작 전에** `.claude/agents/mp-*.md` 로 만든다.
- 스킬 자신의 리서처·스카우트는 플러그인 `agents/` 에 있다.
- 모델은 ID 가 아니라 별칭(opus · sonnet · haiku)으로만 적는다 — 별칭 해석은 제공자마다 다르다.

값의 **유일한 출처**는 [`references/contract.md`](skills/metaprompt/references/contract.md) 다. 여기엔 표를 옮기지 않는다.

```bash
python3 <skill_dir>/scripts/agents.py prompts/metaprompt-<슬러그>.md   # 역할 정의 — 세션 시작 전에
claude --effort <메인 effort>
```

## 기능 스위치 — 프롬프트마다 값과 이유 한 줄

- **agent teams** — 대화형 · standard+ · 서로 반박해야 하는 독립 흐름 ≥3 일 때만 ON. 약 7배 토큰이라 그 외 OFF.
- **Workflow** — 사람이 `ultracode` 를 치고 독립 증거 실행 ≥5 일 때만 ON. 코어 빌드는 제외.
- **루프** — 우선순위대로: 검증 실행 한 번이 ≥15분 → `/loop`(간격 ≥20분) · 종료가 종료 코드 → `/goal` · 그 외 내부 라운드.

## 설치

```
/plugin marketplace add rotcoffee/metaprompt
/plugin install metaprompt@metaprompt
```

플러그인 시스템 없이 개인 스킬로:

```bash
git clone https://github.com/rotcoffee/metaprompt ~/metaprompt
ln -s ~/metaprompt/skills/metaprompt ~/.claude/skills/metaprompt
```

확인: `/metaprompt --check`. 플러그인으로 설치했다면 같은 이름의 개인 스킬(`~/.claude/skills/metaprompt`)은 지운다 — 트리거가 겹친다.

## 사용

`/metaprompt <주제> [--tier lite|standard|max] [--route creative|precise] [--route-only] [--profile product|research|system] [--mode greenfield|worktree] [--yes] [--from <이전 프롬프트>] [--out <경로>]`

## 개발

```bash
python3 skills/metaprompt/scripts/check_prompt.py --self-test   # 구조·픽스처·음성 케이스
python3 skills/metaprompt/scripts/check_prompt.py --repo .      # 버전 3곳 · README 수치 · 실측 원자료 대조
python3 skills/metaprompt/scripts/check_prompt.py prompts/*.md  # 생성물 검사
```

티어 수치·역할·스위치는 `contract.md` 한 곳에만 둔다 — 검사기가 그 표를 파싱한다.

## 맞지 않는 경우

- 한 문장으로 설명되는 수정 · 단순 질의응답 · 코드 리뷰 · 탐색 — 스킬이 skip 으로 돌려보낸다
- 채점할 방법이 없는 산출물

## 출처

[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). 구조와 규칙은 chanp5660/oneshot-prompt (MIT), 상호작용 방식은 obra/superpowers 의 brainstorming, 스킬 작성 원칙은 Anthropic 의 skill-creator 가이드(점진적 공개, "왜"를 설명하기, 반복 작업은 스크립트로)를 따랐다.

## 라이선스

MIT
