# 변경 이력

[Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) · [유의적 버전](https://semver.org/lang/ko/)

## [0.3.0] - 2026-09-30

### 추가

- **경로 라우팅** — 플래그 없이 skip / precise / creative 로 가른다. 애매하면 가벼운 쪽. skip 은 파일을 만들지 않고 채팅 지시 한 줄로 돌려보낸다. `--route-only` 는 판정 한 줄만
- **precise 경로** — 실패하는 회귀 테스트 먼저(`round 0: red`) · 테스트 잠금(`git diff <red>..HEAD`) · 종료 조건 = 종료 코드 · `/goal` 루프 · 외부 리서치 0
- **creative 경로** — 체크리스트에 `앞서기:` 항목(기준점에 없는 것을 실명·증거로) 필수
- **역할별 모델·effort** — `references/contract.md` 한 곳에 표. 생성 프롬프트에 역할 표를 넣고 `scripts/agents.py` 가 세션 시작 전에 `.claude/agents/mp-*.md` 로 만든다. 스킬 자신의 리서처·스카우트는 플러그인 `agents/`
- **기능 스위치** — agent teams · Workflow · 루프(/goal · /loop · 내부 라운드)의 값과 이유를 프롬프트마다 한 줄씩
- Opus 5.5 규약 — 메인 세션 권장 effort, 턴 종료 규약(자동 재개 2회 상한), 검증자 보고 범위 한정, 과잉 검증 문구 금지
- `detect_env.py` 에 `claude`(버전·실행 방식·기능 플래그) · `effort` · `project_agents` 키
- `check_prompt.py --repo` — 버전 3곳 일치 · README 수치 정합 · 실측 원자료 대조. self-test 에 음성 케이스 24건 · 계약 단일화 · lite 경로 바이트 예산
- `bench/chat-vs-lite/` — 같은 주제를 채팅과 lite 로 돌린 실측 원자료

### 변경

- 티어 수치·역할·스위치를 `contract.md` 로 단일화 (SKILL.md · template · 검사기 · README 중복 제거). 체크포인트 lite 1회 · standard·max 2회
- 도메인(product·research·system)은 경로가 아니라 증거 방법으로 재정의. fixtures 를 경로별 4종으로 옮김
- 0.2.0 형식의 `examples/*.md` 는 `examples/legacy/` 로 (CI 대상 아님)

## [0.2.0] - 2026-09-28

### 추가

- **검증 도구 점검 (체크포인트 1½)** — 도메인의 필수 검증 도구(헤드리스 브라우저, GPU 드라이버 + torch, 부하 생성기, 테스트 런타임)가 환경에 없으면 설치 여부를 묻는다.
  사용자 공간 설치(pip·npx·바이너리)는 확인 후 스킬이 실행하고 재확인, 시스템 수준(드라이버·apt·docker)은 커맨드를 보여주고 사용자가 실행. GPU 가 없으면 CPU 축소가 첫 옵션
- `references/tools.md` — 도메인 × 신호 → 필수 도구 · 확인 · 설치 · 대체 표. 빠진 도구가 있을 때만 로드
- 생성 프롬프트에 **`## 사전조건 (검증 도구)`** 절 — 실행 세션이 라운드 0 에서 확인하고, 없으면 설치하거나 멈추고 요청. 도구 없이 채점하지 않는다
- `detect_env.py` 가 GPU(`nvidia-smi -L`), 파이썬 패키지(torch·transformers·playwright·pytest 등, import 없이 존재만), Playwright 브라우저 캐시, OS·패키지 관리자를 보고한다
- `check_prompt.py` 에 사전조건 절 검사 추가 (23항목)

## [0.1.0] - 2026-09-28

oneshot-prompt 0.2.0 을 재구성한 첫 공개판.

### 추가

- **티어** `--tier lite|standard|max` — 라운드 2/3/5, 팬아웃 0/3/5, 체크리스트 4~5/6~7/7~8, 검증 증거 범위, 리서치 깊이가 함께 움직인다
- **체크포인트 3회** — 도메인·티어·진행 방식 / 기준점 선택 / 체크리스트·종료 조건. `--yes` 로 전부 생략, 첫 체크포인트에서 "이후 자동" 선택 가능
- **리서치 위임** — sonnet 서브에이전트가 검색하고 40줄 압축 사실만 반환. worktree 는 Explore 에이전트가 저장소 조사
- **`scripts/detect_env.py`** — 모드·base commit·테스트 커맨드·브라우저·런타임 부재를 JSON 으로. 스킬 로드 시 자동 실행
- **실행 시 컨텍스트 규약** — 서브에이전트 보고 30줄, 판정문 `verdicts/round-N.md`, 다음 라운드엔 실패 항목만
- **`--from`** — 이전 프롬프트의 리서치·체크리스트를 재사용해 티어 승격. 헤더 `regenerate:` 줄
- **`--check`** — 설치 확인
- **`scripts/check_prompt.py`** — 22항목 + 티어·도메인별 검사, `--self-test` 로 스킬 자체 회귀 검사
- 단일 SKILL.md + 도메인 레퍼런스 점진 로드 (oneshot 의 라우터 + 변형 3종 + core.md 구조를 대체)

### 유지

기준점 고정, 리서치 사실 ≥3, 팬아웃/순차 분리와 이유, 생성자/검증자 분리, 증거 획득 커맨드, Yes/No 체크리스트, 숫자 종료 조건, 정체 감지, 수용된 제약, worktree 회귀 통·금지 목록·병합 게이트.

[0.3.0]: https://github.com/rotcoffee/metaprompt/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/rotcoffee/metaprompt/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/rotcoffee/metaprompt/releases/tag/v0.1.0
