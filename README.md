# metaprompt

**주제 한 줄 → 서브에이전트·루프로 실행할 프롬프트 파일 하나.** Claude Code 플러그인.

[oneshot-prompt](https://github.com/chanp5660/oneshot-prompt) 의 철학(기준점 고정 · 리서치 선행 · 팬아웃/순차 분리 · 생성자/검증자 분리 · Yes/No 체크리스트 · 숫자 종료 조건)을 그대로 잇되,
**티어로 품질과 토큰 사용량을 맞바꾸고**, **결정 지점마다 사용자에게 확인**하고, 리서치와 환경 조사를 서브에이전트·스크립트에 위임해 컨텍스트를 아끼도록 재구성했다.

프로그램을 만들지 않고, 만든 프롬프트를 실행하지도 않는다. 산출물은 다른 세션에 붙여 넣을 텍스트 파일까지다.

## 설치

```
/plugin marketplace add rotcoffee/metaprompt
/plugin install metaprompt@metaprompt
```

플러그인 시스템 없이 개인 스킬로 쓰려면 클론 후 심링크 하나면 된다.

```bash
git clone https://github.com/rotcoffee/metaprompt ~/metaprompt
ln -s ~/metaprompt/skills/metaprompt ~/.claude/skills/metaprompt
```

설치 확인:

```
/metaprompt --check
```

의존성: Python 3 (표준 라이브러리만) · `${CLAUDE_SKILL_DIR}` 치환을 지원하는 최근 Claude Code. 스크린샷 검증을 쓰는 제품 도메인은 실행 환경에 Chrome 이 있으면 좋다.

플러그인으로 설치했다면 같은 이름의 개인 스킬(`~/.claude/skills/metaprompt`)은 지운다. 둘 다 있으면 트리거가 겹친다.

## 사용

```
/metaprompt <주제> [--tier lite|standard|max] [--profile product|research|system]
                   [--mode greenfield|worktree] [--yes] [--from <이전 프롬프트>]
                   [--benchmark <기준점>] [--rounds N] [--out <경로>]
```

```
/metaprompt 업무용 캘린더 UI, 단일 HTML                 # 체크포인트 3회를 거쳐 standard 로
/metaprompt api/search p99 개선 --tier lite --yes         # 질문 없이 가볍게
/metaprompt --from prompts/metaprompt-calendar.md --tier max   # 리서치 재사용해 티어 승격
```

기본 흐름:

```
0 파싱 · 환경 자동 수집  →  1 체크포인트: 도메인·티어·진행 방식 (+ 상황별 1문항)
→ 2 리서치 (서브에이전트)  →  3 체크포인트: 기준점 선택
→ 4 체크리스트·종료 조건 초안 + 상충 점검  →  체크포인트: 승인/수정
→ 5 조립  →  6 자가점검 → 저장 → 모드별 실행 안내
```

첫 체크포인트에서 "이후는 추천값으로 자동" 을 고르면 나머지를 건너뛴다. `--yes` 는 처음부터 전부 건너뛴다.

## 티어 — 품질과 토큰의 교환

| | lite | standard (기본) | max |
|---|---|---|---|
| 생성 시 리서치 | 서브에이전트 0, 검색 ≤1 | 서브에이전트 1 (sonnet) | 3 병렬 |
| 체크포인트 | 2회 | 3회 | 3회 |
| 프롬프트 예산 | 팬아웃 0 · 2라운드 · 체크리스트 4~5 | 팬아웃 ≤3 · 3라운드 · 6~7 | 팬아웃 ≤5 · 5라운드 · 7~8 + 블라인드 비교 |
| 실행 방법 | `claude` 새 세션에 붙여넣기 | `/loop` + 붙여넣기 | `/loop ultracode` + 붙여넣기 |
| 실행 비용 (추정) | ~1/10 | ~1/3 | oneshot 실측과 같음 |
| 언제 | 내부용 초안 | 남에게 보여줄 것 | 경쟁 제품 옆에 놓일 것, 논문 재현 |

실행 비용은 oneshot 의 실측(단일 HTML UI, 5라운드, 서브에이전트 19개, 약 7시간)을 1 로 둔 상대 추정치다.
어느 티어에서도 기준점 고정, 검증자 분리, Yes/No 체크리스트, 정체 감지, 수용된 제약은 빼지 않는다 — 티어가 깎는 것은 깊이지 구조가 아니다.

생성 단계 실측 (2026-09-28, `--yes`, 서브에이전트 기준):

| 경우 | 토큰 | 시간 |
|---|---|---|
| lite · greenfield · product | 약 91K | 8분 |
| standard · worktree · system | 약 111K + 리서치·조사 에이전트 2개 | 13분 |

## oneshot 과 무엇이 다른가

| | oneshot 0.2.0 | metaprompt |
|---|---|---|
| 스킬 로드 | 라우터 + core.md + 변형 ≈ 35KB 매번 | SKILL.md ≈ 13KB + 도메인 레퍼런스 **하나** + 조립 때 template (worktree 면 +1) |
| 리서치 | 메인 컨텍스트에서 직접 검색 | 서브에이전트가 검색, **40줄 압축 사실**만 반환 |
| 환경 조사 | git 커맨드 6개 + 설정 파일 읽기 | `detect_env.py` 한 번 → JSON, 스킬 로드 시 자동 |
| 사용자 확인 | 최대 2문항, 즉시 진행 | 체크포인트 3회, `--yes` 로 끄기 |
| 품질↔토큰 | 단일 | lite / standard / max |
| 실행 시 컨텍스트 | 규약 없음 | 30줄 보고 · 판정문 파일화 · 실패 항목만 전달 |
| 재생성 | 처음부터 | `--from` 으로 리서치 재사용 |
| 자가점검 | 12항목 | 22항목 + 티어·도메인별 |

## 구조

```
.claude-plugin/          플러그인·마켓플레이스 매니페스트
skills/metaprompt/
  SKILL.md               절차·티어·체크포인트 (약 190줄). 이것만 매번 로드된다
  references/template.md 조립 틀 — [[lite]] [[standard+]] [[max]] [[worktree]] [[greenfield]] 조건 블록
  references/product.md  도메인 네 칸: 기준점 종류 · 체크리스트 원형 · 증거 획득(티어별) · 종료 지표 (+ 팬아웃/순차 · worktree 델타)
  references/research.md
  references/system.md
  references/worktree.md base commit · 회귀 통 · 금지 목록 · 병합 게이트 — worktree 모드에서만
  scripts/detect_env.py  모드·저장소 사실·테스트 커맨드·브라우저·런타임 부재 → JSON. 항상 exit 0
  scripts/check_prompt.py 생성물 자가점검 + --self-test
  fixtures/              티어×모드×도메인 표본 3종. self-test 가 검사한다
examples/                실제 생성된 프롬프트 3종 (스킬이 로드하지 않는다)
```

도메인 레퍼런스가 채우는 네 칸:

| 칸 | product | research | system |
|---|---|---|---|
| 기준점 | 실명 제품 | 보고 수치 + 조건 | 현행 실측치 + SLO |
| 체크리스트 원형 | 지각 속성 수치 | 방법론 게이트 | 깨지면 안 되는 불변식 |
| 검증 증거 | 렌더링 후 픽셀 판정 | 직접 재현 + 반증 | 부하·장애 주입 계측 |
| 종료 지표 | 전 항목 Yes (+ 블라인드 점수) | 유의미 개선 **또는 기각** | 목표 수치 + 회귀 0건 |

## 개발

```bash
python3 skills/metaprompt/scripts/check_prompt.py --self-test      # 구조·픽스처 회귀
python3 skills/metaprompt/scripts/check_prompt.py prompts/*.md     # 생성물 검사
```

티어 수치(라운드 2/3/5, 팬아웃 0/3/5, 정체 2/2/3)는 `SKILL.md` 티어 표, `template.md`, `check_prompt.py` 세 곳이 같아야 한다.
규칙을 바꾸면 픽스처가 먼저 깨진다. 그것이 정상이다.

## 이 도구가 맞지 않는 경우

- 요구사항이 이미 확정된 경우 · 정답이 하나인 작업(버그 수정·마이그레이션) · 탐색 단계 · 채점할 방법이 없는 산출물
- lite 라도 30분은 든다. 5분짜리 확인에는 쓰지 않는다

## 출처

[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). 구조와 규칙은 chanp5660/oneshot-prompt (MIT), 상호작용 방식은 obra/superpowers 의 brainstorming, 스킬 작성 원칙은 Anthropic 의 skill-creator 가이드(점진적 공개, "왜"를 설명하기, 반복 작업은 스크립트로)를 따랐다.

## 라이선스

MIT
