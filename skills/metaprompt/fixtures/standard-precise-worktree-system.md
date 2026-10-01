<!-- metaprompt route=precise tier=standard domain=system mode=worktree baseline="현행 p99 812ms → 목표 180ms" generated=2026-09-30
     regenerate: /metaprompt "api/search 응답 지연 개선" --route precise --tier standard --profile system --mode worktree --from prompts/metaprompt-search-latency.md --out prompts/metaprompt-search-latency.md -->
<!-- 형식 표본. oneshot-prompt(MIT) 의 worktree 픽스처를 개작했다. 수치는 예시다. -->

# 목표

`api/search` 엔드포인트의 응답 지연을 줄여줘. 기준은 **현행 p99 812ms → 목표 180ms** 이고, 완료는 의견이 아니라 종료 코드가 판정한다.
스택·런타임·의존성 버전은 현행 그대로 유지한다.

완료 = `python3 bench/check_p99.py --max-ms 180 --runs 3` 와 `make test` 가 exit 0, 그리고 먼저 쓴 회귀 테스트가 고쳐지지 않은 채로 통과.
p99 가 목표에 닿아도 오류율이 올라가거나 응답이 달라지면 실패다. 측정 없이 고친 라운드가 있어도 실패다.

## 기준점 상세

- 현행 p50 74ms / p95 310ms / p99 812ms (동시성 64, 5분 유지, 워밍업 60초 제외)
- 현행 처리량 1,240 rps, 오류율 0.02%
- 프로파일 결과 전체 시간의 61% 가 `build_facets()` 의 중복 집계에 있음
- 피크는 오전 9시대, 동시성 90, 짧은 쿼리에 분포가 몰림

## 작업 격리

이 작업은 `../svc-metaprompt-search-latency` 안에서만 한다. 브랜치 `metaprompt/search-latency` · base commit `4f2a91c0d3e6b7a8f9c1d2e3f4a5b6c7d8e9f0a1` · 기준 브랜치 `main`.
깨면 안 되는 바닥: base commit 에서 통과하던 것은 전부 그대로 통과해야 한다. 확인 커맨드: `make test`

아래는 worktree 밖의 공유 상태다. **건드리지 마라.**

- `git push`, 태그 생성, `main` 로의 병합
- 실제 DB·마이그레이션 실행, 외부 API 쓰기 호출
- `.env`, 로컬 설정, 빌드·패키지 캐시, 전역 패키지 설치
- 측정 중 같은 머신에서 다른 빌드·테스트·개발 서버를 돌리지 않는다. 포트는 18080 (8080 은 부모 프로세스가 점유)

건드려야만 목표에 도달할 수 있다면 **멈추고 보고해라.**

## 실행 예산 (route: precise · tier: standard)

- 메인 세션 effort **medium** · model **opus** — `claude --model opus --effort medium` 로 시작한다 (도중에는 `/effort medium`). 세션 모델이 다르면 시작하지 말고 알린다. xhigh·max 는 이득을 실측하지 않았으면 쓰지 않는다.
- 라운드 상한 **3**. 팬아웃 서브에이전트는 동시에 최대 **3개**.
- 역할 — effort 는 에이전트 정의 frontmatter 로만 지정된다 (Agent 호출에는 effort 가 없다). 세션 **시작 전에** `python3 <metaprompt>/scripts/agents.py <이 파일>` 이 아래 표로 `.claude/agents/mp-*.md` 를 만든다. 정의가 로드되지 않았으면 호출에 model 만 지정하고, effort 가 세션값을 상속했다고 판정문에 적는다.

  | 역할 | 정의 | model | effort | 맡는 일 |
  |---|---|---|---|---|
  | 메인 세션 (오케스트레이터·빌더) | — | opus | medium | 진단 → 변경 → 재측정 |
  | 검증자 | mp-verifier | opus | high | 마지막 라운드 1회, 정확성만 |
  | 워커 | mp-worker | sonnet | low | 부하 생성기 · 관측 지표 · 런북 |

- 기능 스위치:
  - agent teams **OFF** — 병목이 `build_facets()` 한 경로로 좁혀져 있어 경쟁 가설이 3개가 안 되고, 변경은 한 번에 하나씩 순차다.
  - Workflow **OFF** — 증거 실행은 벤치 3회 + 장애 주입 1개로 5개 미만이다.
  - 루프 **/goal ON** — 완료가 벤치 스크립트와 테스트의 종료 코드라 새 컨텍스트 평가자가 판정할 수 있다. 15분 지속 부하 동안은 백그라운드로 돌리고 기다린다.
  - `/goal` 줄 (첫 입력): `/goal prompts/metaprompt-search-latency.md 를 읽고 따른다. 완료: python3 bench/check_p99.py --max-ms 180 --runs 3 와 make test 가 exit 0 으로 출력되고 git diff <red SHA>..HEAD -- bench/check_p99.py 가 비어 있음. 또는 3 라운드 후 멈추고 보고`
- 턴 종료 규약: 텍스트만 있는 턴 종료는 완료가 아니다. 종료 조건 미달이고 라운드 상한 전이면 남은 체크리스트 항목을 다시 적고 이어 간다. 사람 입력 없는 자동 재개는 연속 2회까지 — 그 뒤엔 멈추고 남은 항목을 보고한다.
- 서브에이전트 보고는 **30줄 이내**. 코드·로그 전체를 부모 컨텍스트로 올리지 말고 파일 경로와 결론만. 검증자·심사자는 **포그라운드로** 호출해 판정을 받은 뒤 다음 단계로 간다 — 백그라운드로 띄우고 턴을 끝내면 `-p` 에서는 세션이 거기서 끝난다.
- 판정문은 `verdicts/round-N.md`. 다음 라운드에는 **실패 항목만** 넘기고, 통과 항목의 근거는 다시 읽지 않는다.
- 라운드마다 커밋한다 (`round N: <한 줄 요약>`).
- 검증 증거 범위: 재측정 3회 · 등가성 1만 건 · 장애 주입 1개 · 지속 부하 15분 · 롤백 실제 실행

## 사전조건 (검증 도구)

라운드 0 에서 확인한다. 사용자 공간 설치(pip·바이너리)는 직접 하고, 시스템 수준(드라이버·apt·docker)이면 **멈추고 사용자에게 요청**한다. 도구 없이 상상으로 채점하지 마라.

| 도구 | 확인 | 없을 때 |
|---|---|---|
| node ≥ 18 (`make test`) | `node --version` | nvm 으로 사용자 공간 설치 |
| 부하 생성기 hey (또는 k6·wrk·ab) | `which hey k6 wrk ab` | GitHub 릴리스 바이너리를 `~/.local/bin` 에 |
| python3 (벤치 판정·등가성 대조) | `python3 --version` | 시스템 수준 — 멈추고 요청 |

## 병렬로 진행할 것 (서브에이전트 팬아웃)

서로 독립적이다. 각각 `mp-worker` 에 배분해 동시에 진행해.

- 부하 생성기 작성 (현행 트래픽 분포 재현, 포트 18080)
- 관측 지표 정비 (구간별 타이밍 계측 추가)
- 런북·롤백 절차 문서 초안

## 순차로 진행할 것 (쪼개지 마)

1. **빨강 먼저** — `bench/check_p99.py` 에 목표를 assert 하는 벤치 판정 스크립트를 쓰고, 고치기 전에 `python3 bench/check_p99.py --max-ms 180 --runs 3` 가 exit ≠ 0 임을 확인해 `round 0: red` 로 커밋한다. 그 SHA 를 판정문에 적는다.
2. 이후 `bench/check_p99.py` 는 수정하지 않는다 — `git diff <red SHA>..HEAD -- bench/check_p99.py` 가 비어야 한다. 판정 스크립트가 틀렸다고 판단되면 멈추고 보고한다.
3. 원인 지점을 고친다 → `python3 bench/check_p99.py --max-ms 180 --runs 3` exit 0 → `make test` exit 0.

외부 리서치는 하지 않는다 — 기준점은 base commit 과 명세다.
병목 진단 → 변경 → 재측정은 한 에이전트가 처음부터 끝까지 맡아. 변경은 한 번에 하나씩, 각각 재측정한다.
이유: 같은 시스템 상태와 같은 측정 기준선에 쓴다. 여러 최적화를 동시에 넣으면 무엇이 효과였는지 알 수 없다. 측정 없이 최적화하지 마라.

## 검증

만드는 에이전트와 **별개의** 검증을 둔다. 자기가 만든 걸 자기가 채점하지 마.
1차 판정은 먼저 잠긴 벤치 판정 스크립트의 종료 코드다 — 만든 쪽이 판정 기준을 바꿀 수 없다. `/goal` 평가자가 턴마다 출력을 읽고, 마지막 라운드에 `mp-verifier` 가 한 번 새 컨텍스트로 정확성만 본다: 판정 스크립트가 p99 를 실제로 계측하는가, diff 가 증상만 가리는가(캐시로 벤치만 빠르게).
보고 범위는 **아래 체크리스트 항목과 정확성 결함으로 한정**한다 — 새 컨텍스트 리뷰어는 결과가 멀쩡해도 뭔가를 보고하는 경향이 있다. 취향 지적은 판정에 넣지 않는다. 근거 없는 pass 는 무효다.

근거는 **base commit `4f2a91c0d3e6b7a8f9c1d2e3f4a5b6c7d8e9f0a1` 대비 diff 와 실제 실행 결과**뿐이다. 커밋 메시지와 만든 쪽의 자기 보고는 근거가 아니다.

    git diff 4f2a91c0d3e6b7a8f9c1d2e3f4a5b6c7d8e9f0a1...HEAD
    make test

**직접 증거를 확보한 뒤 판정해라. 추정하지 마라.**

```
검증자는 코드를 읽고 빨라졌을 것이라고 판단하지 마라. 계측한 값만 근거로 인정한다.

  git worktree add ../base-perf 4f2a91c0d3e6b7a8f9c1d2e3f4a5b6c7d8e9f0a1
  # ../base-perf 와 현재 worktree 를 같은 부하 프로파일로 각각 측정. 끝나면 git worktree remove ../base-perf

1. 동일 조건 재측정: p50/p95/p99/최악값을 표로. 3회, 분산도 함께.
2. 등가성 확인: 개선 전후 동일 입력 1만 건의 출력을 대조해라.
3. 장애 주입: 의존 서비스 지연 1개를 주입하고 무너지는 방식을 관찰해라.
4. 지속 부하: 15분 유지하며 메모리·핸들 누수를 확인해라.
5. 롤백 실행: 실제로 되돌려서 성공하는지 확인해라.
```

회귀 통 — 체크리스트와 **별도로** 전 항목 Yes 여야 한다:

- [ ] base commit `4f2a91c0d3e6b7a8f9c1d2e3f4a5b6c7d8e9f0a1` 에서 통과하던 것이 전부 통과하는가 (`make test` exit 0)
- [ ] `git diff --stat 4f2a91c0d3e6b7a8f9c1d2e3f4a5b6c7d8e9f0a1...HEAD` 의 변경 파일이 전부 범위 안인가
- [ ] 변경된 공개 인터페이스의 호출부가 전부 갱신됐는가 (`grep` 결과로)
- [ ] 벤치마크 하니스·부하 생성기가 red 커밋 이후 변경되지 않았는가

체크리스트 — 전 항목 Yes 여야 통과:

- [ ] 회귀 테스트가 red 커밋에서 exit ≠ 0, HEAD 에서 exit 0 인가 (`python3 bench/check_p99.py --max-ms 180 --runs 3`)
- [ ] red 이후 `bench/check_p99.py` 의 diff 가 0줄인가
- [ ] 오류율이 base 대비 증가하지 않았는가 (같은 부하 3회)
- [ ] 개선 전후 동일 입력 1만 건의 출력이 바이트 단위로 일치하는가
- [ ] 15분 부하 유지 시 메모리 사용량이 단조 증가하지 않는가
- [ ] 롤백 절차를 실제로 실행해 성공했는가

판정문 `verdicts/round-N.md` 형식:

- 항목별 **pass/fail 과 근거**(측정값·라인 번호·종료 코드).
- **수용된 제약**: 과제 전제상 원리적으로 해결 불가능한 지적은 실패가 아니라 여기에 적는다. 실패로 세면 정체 감지가 잘못 발동한다.
- 남은 격차가 **요구사항 자체에서 강제된 것인지** 한 문단. 교환된 것(메모리 증가 등)을 명시한다.

## 종료 조건

`python3 bench/check_p99.py --max-ms 180 --runs 3` 와 `make test` 의 종료 코드 0 · 잠금 diff 비어 있음 · 체크리스트 전 항목 Yes · base 대비 회귀 0건 · 최대 3라운드.
미달이면 지적된 항목만 다시 만들어 재검증한다. 3라운드까지 못 닿으면 멈추고 남은 항목과 이유를 보고한다.

검증자의 **판정**은 받아들이되 **처방**은 체크리스트 전체와 대조한다 — 한 항목을 고치며 다른 항목을 깨는 교환은 손해다.
같은 지적이 2라운드 연속 반복되면 접근이 틀린 것이다. 멈추고 보고한다 (수용된 제약은 세지 않는다).

## 완료 후

전 항목 Yes 여도 **병합하지 마라.** 브랜치 `metaprompt/search-latency` 의 최종 커밋 · 마지막 `verdicts/round-N.md` · `git diff --stat 4f2a91c0d3e6b7a8f9c1d2e3f4a5b6c7d8e9f0a1...HEAD` 요약을 남기고 멈춘다.
기준 브랜치가 움직였으면 최신 `main` 을 머지하고 **회귀 통만** 다시 돌려 판정문에 덧붙인다. **병합 여부는 사람이 판정문을 읽고 결정한다.**
