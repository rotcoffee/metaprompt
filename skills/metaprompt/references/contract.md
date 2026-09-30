# contract — 경로 × 티어 설계표 (수치·역할·스위치의 단일 출처)

SKILL.md · template.md · README 는 이 파일을 가리키기만 한다. `check_prompt.py` 가 아래 표를 파싱하므로 첫 열 키를 바꾸면 검사기가 먼저 깨진다.

## 경로 — 작업 성격. 판정 규칙은 SKILL.md 0절 (플래그 없이, 애매하면 가벼운 쪽 skip < precise < creative)

| 경로 | 기준점 | 생성 시 리서치 | 검증 | 종료 | 루프 |
|---|---|---|---|---|---|
| skip | — | — | — | 프롬프트 없이 채팅 지시 한 줄 | — |
| precise | base commit · 명세 | 0 (저장소 사실만) | 먼저 실패하는 회귀 테스트 → 잠금 | 커맨드 종료 코드 0 | `/goal` |
| creative | 실명 제품·방법 + 수치 | 티어 R | 렌더·재현·계측 + 앞서기 항목 | 전 항목 Yes (+블라인드 점수) | 내부 라운드 |

도메인(product · research · system)은 경로가 아니라 **증거 방법**이다 — 렌더 · 재현/반증 · 계측. 경로와 독립이다 (precise×system = 성능 목표, creative×research = 새 방법, precise×research = 보고 수치 재현).

## 티어 — 크기. 판정 신호는 SKILL.md 0절 (신호가 없으면 lite)

| 키 | lite | standard | max |
|---|---|---|---|
| M 라운드 상한 | 2 | 3 | 5 |
| K 동시 팬아웃 | 0 | 3 | 5 |
| S 정체 판정 연속 라운드 | 2 | 2 | 3 |
| C 체크리스트 항목 | 4-5 | 6-7 | 7-8 |
| R 생성 시 리서치 에이전트 (creative) | 0 | 1 | 3 |
| Q 체크포인트 (AskUserQuestion 호출) | 1 | 2 | 2 |

## 역할 — 모델 · effort

Agent 도구에는 effort 파라미터가 없다. effort 는 에이전트 정의 frontmatter 로만 준다. 세션 도중 만든 정의는 그 세션에 로드되지 않으므로(2.1.285 실측) **세션 시작 전에** 만든다 — 생성 프롬프트는 `scripts/agents.py` 로, 이 스킬 자신은 플러그인 `agents/` 로. 모델은 별칭으로만 적는다.

| 역할 | 정의 | model | effort | 언제 |
|---|---|---|---|---|
| 메인 세션 (오케스트레이터·빌더) | — | 세션 모델 | precise medium · creative lite medium, standard+ high | 항상. `claude --effort <값>` |
| 검증자 | mp-verifier | opus | high | creative 매 라운드 · precise 마지막 1회 |
| 심사자 | mp-judge | opus | medium | creative standard+ 블라인드 비교 |
| 워커 | mp-worker | sonnet | low | K ≥ 1 인 팬아웃·측정 |
| 콜드 리더 | mp-reader | haiku | — | README·첫 화면 캡처 한 장 판독 (Haiku 는 effort 미지원) |
| 리서처 | researcher | sonnet | low | 생성 시 creative standard+ (플러그인 agents/) |
| 스카우트 | scout | sonnet | low | 생성 시 worktree standard+ (플러그인 agents/) |

혼자 끝낼 수 있는 일은 위임하지 않는다 — 같은 모델의 낮은 effort 가 작은 모델 위임보다 쌌다. 비용의 지렛대는 에이전트 수다. xhigh·max 는 이득을 실측했을 때만.

## 기능 스위치 — 프롬프트마다 값과 이유를 한 줄씩

| 스위치 | ON 조건 (전부) | 그 외 | 근거 |
|---|---|---|---|
| agent teams | 대화형 · standard+ · 서로 다른 파일을 맡은 독립 흐름 ≥3 이 서로 반박해야 한다 (경쟁 가설 디버깅 · creative 발산 단계) | OFF | 실험 기능 · 약 7배 토큰 · `-p` 에서 팀 없음 · 순차/같은 파일/의존 많은 작업 금지 |
| Workflow | 대화형에서 사람이 `ultracode` 를 친다 · 서로 독립인 증거 실행 ≥5 · 코어 빌드 제외 · run 당 25 에이전트 미만 | OFF | `-p` 에서 키워드 무동작 · 25 에이전트/1.5M 토큰 경고 |
| 루프 | 위에서부터 첫 번째: ① 검증 실행 한 번이 ≥15분(학습·지속 부하·CI) → `/loop` 간격 ≥20분 ② 종료가 커맨드 종료 코드 → `/goal` (새 Haiku 평가자가 턴마다 판정, `-p` 동작) | 내부 라운드 | `/goal` 의 유휴 체크인은 3회에서 멈춘다 · `/loop` 는 발화마다 전체 컨텍스트를 보낸다 |

턴 종료 규약 (모든 경로): 텍스트만 있는 턴 종료는 완료가 아니다. 미달 항목이 남았고 상한 전이면 남은 체크리스트를 다시 적고 이어 간다. 자동 재개는 연속 2회까지.
