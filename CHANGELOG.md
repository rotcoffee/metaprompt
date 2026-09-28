# 변경 이력

[Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) · [유의적 버전](https://semver.org/lang/ko/)

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

[0.1.0]: https://github.com/rotcoffee/metaprompt/releases/tag/v0.1.0
