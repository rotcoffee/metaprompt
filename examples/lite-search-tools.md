<!-- 스모크 테스트 산출물 (2026-09-28, --yes). node 와 부하 생성기가 없는 머신에서 만들어져 사전조건 절에 그 사실이 박혀 있다. 스킬이 로드하지 않는다. -->
<!-- metaprompt tier=lite domain=system mode=worktree baseline="base 64997e0 의 api/search 실측치(라운드 0 계측) → p99 ≤ 200ms" generated=2026-09-28
     regenerate: /metaprompt "api/search 응답 지연 개선, p99 목표 200ms" --tier lite --profile system --mode worktree --from prompts/metaprompt-search-latency.md --out prompts/metaprompt-search-latency.md -->

# 목표

`api/search` 응답 지연 개선(브랜치 `metaprompt/api-search-p99` 에 라운드별 커밋 · 재현 가능한 벤치 하니스 · 판정문)을 만들어줘. **base commit 64997e0 의 api/search 실측치(라운드 0 에서 같은 하니스로 계측) 대비 p99 ≤ 200ms** 수준이어야 한다.
스택: Node.js. `package.json` scripts 는 test=`node --test`, bench=`node bench/run.js` 이지만 `bench/` 디렉터리·HTTP 진입점·데이터셋·테스트 파일이 저장소에 없다 — `src/search.js` 의 순수 함수 `search(q, rows)` · `buildFacets(rows)` 뿐이다. 측정은 같은 머신 · 같은 하니스 · 같은 부하 프로파일로 base 와 HEAD 를 나란히 잰다.

"동작하는 수준"이 아니라 "같은 부하 프로파일에서 계측한 값이 p99 200ms 이하에 닿는 수준"이 목표다.
실패의 정의: 부하 중 p99(3회 반복 중 최댓값)가 200ms 를 넘거나, 목표에 닿았지만 개선 전후 응답이 달라졌거나, 측정 없이 코드를 고친 라운드가 하나라도 있으면 실패다. (리서치에서 확보한 리뷰 표현 없음 — system 도메인 기본 정의)

## 기준점 상세

- (저장소 확인) `search()` 는 요청마다 rows 전체를 `JSON.stringify` 한 뒤 `includes(q)` 로 필터하고, `buildFacets()` 는 rows 전체의 모든 키를 다시 센다 — 요청당 O(N·K) 동기 작업, 인덱스·캐시·사전계산 없음. rows 가 수만 건이면 이 둘이 곧 이벤트 루프 점유 시간이다.
- Node 요청 핸들러 안의 동기 `JSON.stringify` / `JSON.parse` 는 이벤트 루프를 점유해 그 동안 **다른 모든 요청**을 막는다 — 400KB 급 객체 직렬화 하나가 동시 요청 전체의 꼬리 지연이 된다 — 출처: https://dev.to/axiom_agent/your-nodejs-api-was-fast-now-its-slow-heres-how-to-diagnose-it-5b17 (검색 요약에서 확인, 원문 대조 안 함)
- 이벤트 루프 지연 p99 가 10ms 를 꾸준히 넘으면 핫패스에 동기 CPU 작업이 있는 것이다. `perf_hooks.monitorEventLoopDelay()` 히스토그램(p50/p99)으로 직접 잰다 — 출처: https://dev.to/zyvop/nodejs-performance-profiling-finding-the-bottleneck-before-your-users-do-bnm (검색 요약에서 확인, 원문 대조 안 함)
- 큰 인메모리 배열 생성·문자열 연결로 할당이 폭증하면 꼬리 지연이 V8 GC 정지와 겹친다. 이벤트 루프는 조율만 하고 CPU 작업(JSON 변환 등)은 워커 스레드·프로세스 풀로 보낸다 — 출처: https://medium.com/@bhagyarana80/top-10-node-js-p99-killers-and-fixes-that-stick-835aacfdc658 (검색 요약에서 확인, 원문 대조 안 함)
- 참고 처리량: 단일 프로세스 `node:http` hello-world 는 수만 req/s, Fastify ≈ 70k req/s vs Express ≈ 15~20k req/s 급 (출처 미확인). 즉 50k 건 필터+파셋에서 p99 가 200ms 를 넘는다면 병목은 프레임워크가 아니라 요청당 O(N) 작업이다.
- 부하 프로파일 기본값 — 실제 트래픽 형태를 확인하지 못해 이 프롬프트가 정한 값이며, 실측 프로파일이 있으면 교체한다: 동시성 32 · 60초 · 워밍업 10초 · rows 50,000건(시드 고정) · 쿼리 200개 고정 목록(적중률 높은 것·낮은 것 반반) (출처 미확인)

## 작업 격리

**사전조건**: 이 프롬프트를 만든 머신에는 `node` 런타임이 없어 `npm test` 를 돌릴 수 없었다. 실행 세션은 시작 전에 `node --version` 이 성공하는지 확인하고, 아니면 **시작하지 않는다** — 회귀 통이 돌지 않는 환경에서 라운드를 시작하면 첫 라운드가 통째로 낭비된다.

이 작업은 `../repo-metaprompt-api-search-p99` 안에서만 한다.
브랜치 `metaprompt/api-search-p99` · base commit `64997e004c58c15867a614893886057155e4f572` · 기준 브랜치 `main`.

깨면 안 되는 바닥: base commit 시점에 통과하던 것은 전부 그대로 통과해야 한다.
확인 커맨드: `npm test`
(base 에 테스트 파일이 없어 스위트가 비어 있을 수 있다. 라운드 0 에서 base 의 `npm test` 실제 결과를 기록하고, 빈 스위트면 그 사실을 판정문에 적는다 — 빈 스위트는 회귀 근거가 되지 못하므로 등가성 항목이 그 역할을 대신한다.)

아래는 worktree 밖의 공유 상태다. **건드리지 마라.**

- `git push`, 태그 생성, `main` 로의 병합
- 실제 DB·마이그레이션 실행, 외부 API 쓰기 호출
- `.env`, 로컬 설정, 빌드·패키지 캐시, 전역 패키지 설치
- 측정 중 같은 머신에서 다른 빌드·테스트·개발 서버를 돌리지 않는다 — 측정 전 `ps -eo pid,pcpu,cmd | grep -E 'node|npm'` 로 확인하고 판정문에 보고
- 포트는 worktree 전용: HEAD 서버 `3971`, base 서버 `3972`. 부모 저장소나 다른 프로세스가 쓰는 포트를 점유하지 않는다
- 부모 저장소의 `node_modules` · 캐시를 공유하지 않는다. 데이터셋은 커밋하지 않고 시드로 생성한다 (`bench/out/` 의 결과 JSON 만 커밋)

건드려야만 목표에 도달할 수 있다면 **멈추고 보고해라.** 임의로 진행하지 마라.

## 실행 예산 (tier: lite)

- 라운드 상한 **2**. 팬아웃 없음 — 빌더 하나, 검증자 하나.
- 서브에이전트 보고는 **30줄 이내**로 받아라. 코드·로그·스크린샷 전체를 부모 컨텍스트로 올리지 마라.
  상세는 파일에 두고 경로와 결론만 보고한다. 컨텍스트가 길어질수록 뒤 라운드의 판단이 흐려진다.
- 검증자 판정문은 `verdicts/round-N.md` 에 저장한다. 다음 라운드 작업 지시는 **실패 항목만** 추려서 넘긴다.
  통과 항목의 근거는 다시 읽지 않는다.
- 라운드마다 커밋한다 (`round N: <한 줄 요약>`). 커밋이 없으면 중간 상태 복원도, 개선 전후 비교도 못 한다.
- 검증 증거 범위: lite 세트 — 반복 3회 · 등가성 1,000건 · 장애 주입 생략 · 지속 부하 5분 · 롤백은 문서 확인만

## 사전조건 (검증 도구)

라운드 0 에서 아래를 확인한다. 없으면 사용자 공간 설치(pip·npx·바이너리)는 직접 하고, 시스템 수준(드라이버·apt·docker)이면 **멈추고 사용자에게 설치를 요청**한다.
무인 실행 중이면 판정문에 "도구 없음"을 적고 멈춘다. 도구 없이 상상으로 채점하지 마라.

이 프롬프트를 만든 머신에서 **없었던 것**: `node` 런타임, 부하 생성기(k6·hey·wrk·ab·locust 전부 없음). 실행 세션은 다른 머신일 수 있으므로 아래를 전부 다시 확인한다.

| 도구 | 확인 | 없을 때 |
|---|---|---|
| `node` ≥ 20 (서비스 런타임 · `npm test` · 하니스 실행) — **생성 머신에 없었음** | `node --version && npm --version` | 대체 없음 — 회귀 통이 돌지 않으면 시작하지 않는다. 사용자 공간: `nvm install --lts` · 시스템 수준: `sudo apt-get install -y nodejs` (멈추고 사용자에게 요청) |
| 부하 생성기 하나 — k6 / hey / wrk / ab / locust — **생성 머신에 전부 없었음** | `which k6 hey wrk ab locust` | 사용자 공간: `pip install locust` 또는 hey GitHub 릴리스 바이너리를 `~/.local/bin` 에 · 시스템 수준: `sudo apt-get install -y apache2-utils` (ab) · 대체: 라운드 0 에서 `bench/load.py` (python asyncio + httpx 간이 부하기, `uv run --with httpx`) 를 하니스에 포함하고 판정문에 "간이 부하기 사용"을 명시 |
| `python3` (등가성 대조 `bench/equiv.py` · 간이 부하기) | `python3 --version` | 생성 머신에 있었음. 없으면 시스템 수준 — 멈추고 사용자에게 요청 |
| `git worktree` (base 나란히 측정) | `git worktree list` | git 2.5+ 에 포함. 없으면 시스템 수준 |
| `docker` (격리 인스턴스 — 이 저장소는 외부 DB·캐시·큐가 없어 **필요 없을 가능성이 높다**) | `docker info` | 생성 머신에 있었음. 라운드 0 에서 외부 의존이 발견되면 그때만 필요 — 없으면 인메모리 대체 + 판정문에 "실 인스턴스 미검증" 명시 |
| `ps` · `awk` (RSS 표본 · 동시 프로세스 확인) | `ps --version` | 배포판 기본 도구. 없으면 시스템 수준 |

## 순차로 진행할 것 (쪼개지 마)

아래 전부를 빌더 하나가 순서대로 처리한다. 병렬화하지 마라 — 이 티어는 이음매를 다시 붙일 예산이 없다.
"하니스 작성 → base 측정 → 병목 진단 → 변경 하나 → 재측정" 코어는 한 에이전트가 처음부터 끝까지 맡아.
이유: 모두 같은 측정 기준선(라운드 0 하니스 · 같은 데이터셋 시드 · 같은 부하 프로파일)과 같은 `src/search.js` · `bench/` 파일에 쓰기를 한다. 여러 최적화를 동시에 넣으면 무엇이 효과였는지 영원히 알 수 없다 — **변경은 한 번에 하나씩, 각각 재측정.** 측정 없이 최적화하지 마라.
여기를 병렬로 쪼개면 부분별로는 그럴싸해 보여도 이음매에서 버그가 난다.

라운드 0 (하니스 — 코드 최적화 금지):
1. 사전조건 표를 전부 확인하고 결과를 `verdicts/round-0.md` 에 적는다.
2. 기존 모듈 조사 후 재사용: `src/search.js` 의 공개 함수, `package.json` scripts, CI(`.github/workflows/ci.yml` = `npm test`). 이미 있는 것을 다시 만들지 않는다.
3. 하니스 작성 — `package.json` 이 가리키는 경로 그대로: `bench/run.js` (측정 오케스트레이션), `bench/server.js` (`node:http` 최소 서버 — `GET /api/search?q=` 가 `search(q, rows)` 를 호출; 저장소에 HTTP 진입점이 없으므로 측정용으로 추가하되 `src/` 의 공개 인터페이스는 바꾸지 않는다), `bench/data.js` (시드 고정 rows 50,000건 생성), `bench/queries.txt` (쿼리 200개), `bench/equiv.py` (base·HEAD 응답 deep-equal 대조), 부하 생성기가 없을 때만 `bench/load.py`. `npm run bench` 가 p50/p95/p99/최악값/req/s/오류율을 JSON 으로 `bench/out/` 에 남기게 한다.
4. `git commit -m "round 0: bench harness"` — 이 커밋 SHA 가 하니스 불변의 기준이다. 이후 라운드에서 `bench/` 를 고치면 base 도 새 하니스로 다시 측정한다.
5. base 측정: 검증 절의 블록대로 `../repo-base-perf` 를 만들고 같은 하니스로 base 를 3회 잰다. 현행 p50·p95·p99·최악값·오류율·RSS 를 `verdicts/round-0.md` 의 기준점 표에 적는다. **이 표가 없으면 라운드 1 을 시작하지 않는다.**

라운드 1~2 (각 라운드에 변경 하나):
6. 프로파일링: `node --cpu-prof bench/server.js` 로 부하 중 프로파일을 뜨고 `perf_hooks.monitorEventLoopDelay()` p99 를 기록한다. 최상위 병목 **하나**를 함수·라인으로 지목한다.
7. 그 병목 하나만 고친다 (후보 예: rows 를 요청마다 직렬화하는 대신 색인·사전계산, 파셋 사전계산과 무효화, 응답 직렬화 크기 축소). 고친 뒤 `npm test` 와 `bench/equiv.py` 를 먼저 돌린다.
8. 재측정 3회 → 커밋 (`round N: <변경 한 줄>`) → 검증자에게 넘긴다.

## 검증

만드는 에이전트와 **별개의** 검증 에이전트를 둬. 자기가 만든 걸 자기가 채점하지 마.
검증자는 아주 가혹한 비평가여야 하고, 기본 태도는 거부다.

검증자는 **base commit `64997e004c58c15867a614893886057155e4f572` 대비 diff 와 실제 실행 결과물**만 근거로 삼아라.
라운드 커밋 메시지와 만든 에이전트의 자기 보고는 근거가 아니다.

    git diff 64997e004c58c15867a614893886057155e4f572...HEAD
    npm test

**검증자는 다음 방법으로 직접 증거를 확보한 뒤 판정해라. 추정하지 마라.**

검증자는 코드를 읽고 빨라졌을 것이라고 판단하지 마라. **계측한 값만 근거로 인정한다.**

    # 측정 전: 같은 머신에 다른 빌드·테스트·개발 서버가 없는지 확인하고 판정문에 붙인다
    ps -eo pid,pcpu,rss,cmd | grep -E 'node|npm' | grep -v grep

    # base 를 같은 하니스(라운드 0 커밋의 bench/)로 나란히 잰다
    git worktree add ../repo-base-perf 64997e004c58c15867a614893886057155e4f572
    cp -r bench ../repo-base-perf/bench
    (cd ../repo-base-perf && PORT=3972 node bench/server.js &)   # base
    PORT=3971 node bench/server.js &                               # HEAD

    # 부하 — 설치된 것 하나를 쓴다. 60초 · 동시성 32 · 워밍업 10초는 결과에서 제외
    hey -z 60s -c 32 -o csv "http://127.0.0.1:3971/api/search?q=$(sed -n 1p bench/queries.txt)" > bench/out/head-run1.csv
    # 또는  ab -t 60 -c 32 "http://127.0.0.1:3971/api/search?q=..."   /   k6 run -e PORT=3971 bench/load.js
    # 또는 (부하 생성기가 없을 때만)  uv run --with httpx python3 bench/load.py --port 3971 --c 32 --duration 60 --warmup 10 --queries bench/queries.txt --out bench/out/head-run1.json
    # 같은 커맨드를 PORT/출력만 바꿔 base(3972) 에도. 각각 3회 (run1~3). 그다음 순서를 바꿔(HEAD→base) 한 번 더 돌려 순서 효과를 확인한다.

    git worktree remove ../repo-base-perf   # 끝나면 정리

1. 동일 조건 재측정: 같은 부하·같은 하드웨어·같은 워밍업으로 base 와 HEAD 의 p50/p95/p99/최악값/req/s/오류율을 표로. 3회 반복, 3회의 분산(최소~최대)도 함께. 판정에는 **3회 중 p99 최댓값**을 쓴다.
2. 등가성 확인: `python3 bench/equiv.py --base http://127.0.0.1:3972 --head http://127.0.0.1:3971 --queries bench/queries.txt --n 1000` — 동일 입력 1,000건에 대해 응답 JSON 을 파싱해 `hits`(순서 포함)와 `facets` 가 deep-equal 인지 대조한다. 불일치 건수와 첫 불일치 예시를 판정문에. 성능은 정확성을 깎아 얻을 수 있으므로 이 확인 없이는 어떤 수치도 무효다.
3. 장애 주입: lite 에서는 생략한다. 판정문에 "장애 주입 미실시(lite)" 를 수용된 제약으로 적는다.
4. 지속 부하: 5분 유지(동시성 32)하며 10초마다 `ps -o rss= -p <HEAD PID>` 를 기록한다. 첫 1분 평균과 마지막 1분 평균 RSS 를 판정문에.
5. 롤백: lite 에서는 문서 확인만 — `verdicts/rollback.md` 에 `git revert` 단위(라운드 커밋 SHA)와 되돌린 뒤 `npm test` · `npm run bench` 재실행 절차가 적혀 있는지 확인한다.

측정 환경을 재현할 수 없으면 그 범위를 판정문에 명시하고 어떤 수치가 추정인지 구분해라.

회귀 통 — 도메인 항목과 **별도로** 전 항목 Yes 여야 한다:

- [ ] base commit `64997e004c58c15867a614893886057155e4f572` 에서 통과하던 것이 전부 그대로 통과하는가 (`npm test`)
- [ ] `git diff --stat 64997e004c58c15867a614893886057155e4f572...HEAD` 의 변경 파일이 전부 이 주제의 범위 안인가 (`src/search.js` · `bench/` · `verdicts/` · `package.json` scripts 이외가 있으면 No)
- [ ] 변경된 공개 인터페이스의 호출부가 저장소 전체에서 갱신됐는가 (`grep -rn "search(\|buildFacets(" --include=*.js .` 결과로 보여라 — `search(q, rows)` · `buildFacets(rows)` 시그니처가 바뀌었으면 No)
- [ ] 벤치마크 하니스·부하 생성기·측정 스크립트(`bench/`)가 라운드 0 커밋 대비 변경되지 않았는가 (변경했다면 base 도 새 하니스로 다시 측정했고 그 수치가 판정문에 있는가)

체크리스트 — 전 항목 Yes여야 통과:

- [ ] 같은 부하 프로파일(동시성 32 · 60초 · 워밍업 10초 · rows 50,000 · 쿼리 200개)에서 3회 반복 측정한 HEAD 의 p99 최댓값이 200ms 이하이면서, 오류율(비 2xx + 타임아웃)이 base 대비 증가하지 않았는가
- [ ] 동일 입력 1,000건에 대해 base 와 HEAD 의 응답을 파싱한 `hits`(순서 포함)와 `facets` 가 전부 deep-equal 인가 (불일치 0건)
- [ ] 동시성 32 로 5분 지속 부하 동안 HEAD 의 RSS 가 단조 증가하지 않는가 (마지막 1분 평균이 첫 1분 평균의 110% 이하)
- [ ] p50 · p95 · 최악값 · req/s 중 어느 하나도 base 보다 나빠지지 않았고, 교환된 자원(RSS · CPU · 시작 시간 · 사전계산 메모리)이 판정문에 수치로 명시됐는가
- [ ] `verdicts/rollback.md` 에 라운드 커밋 단위의 `git revert` 절차와 되돌린 뒤 재검증 커맨드가 적혀 있는가

검증자는 아래 형식으로 `verdicts/round-N.md` 에 남겨라.

- 항목별 **pass/fail 과 근거**(측정값·라인 번호·재현된 수치). 근거 없는 pass 는 무효다.
- **수용된 제약**: 이 과제의 전제상 원리적으로 해결 불가능한 지적은 실패가 아니라 여기에 적어라.
  실패로 집계하면 정체 감지 규칙이 잘못 발동한다.
- 남은 격차가 **요구사항 자체에서 강제된 것인지** 한 문단으로 답해라.
- 점수는 보조 신호다. 항목별 판정과 근거 수치가 1차 결론이다.

## 종료 조건

체크리스트 전 항목 Yes + 회귀 통 전 항목 Yes + api/search p99(3회 반복 최댓값)가 200ms 이하 + 개선 전 대비 회귀 0건 · 최대 2라운드.
미달이면 지적된 항목만 다시 만들어서 재검증해.
2라운드까지 통과 못 하면 멈추고, 남은 미달 항목과 그 이유를 보고해.
병목이 다른 곳(예: 하니스 서버 자체·머신 한계)에 있음을 계측으로 보였다면 "개선 여지 없음"도 정당한 종료다 — 그 계측을 판정문에 남기고 멈춘다.

검증자의 **판정**은 받아들이되 **처방**은 체크리스트 전체와 대조해라. 한 항목을 고치려다 다른
항목을 깨는 제안이 나올 수 있다. 통과 조건은 전 항목 Yes이므로 그런 교환은 손해다.

같은 지적이 2라운드 연속 반복되면 접근 방식이 틀린 것이다. 멈추고 보고해.
(수용된 제약으로 분류된 항목은 이 카운트에서 제외한다.)

## 완료 후

전 항목 Yes 에 도달해도 **병합하지 마라.** 아래를 남기고 멈춘다.

- 브랜치 `metaprompt/api-search-p99` 의 최종 커밋
- 마지막 판정문 `verdicts/round-N.md` (항목별 pass/fail 과 근거 수치, 수용된 제약)
- `git diff --stat 64997e004c58c15867a614893886057155e4f572...HEAD` 요약

기준 브랜치가 그사이 움직였으면 최신 `main` 를 머지한 뒤 **회귀 통만 다시 돌려**
결과를 판정문에 덧붙여라. 여기서 깨지면 전 항목 Yes 가 아니다.

미달로 끝나도 브랜치를 지우지 마라. **병합 여부는 사람이 판정문을 읽고 결정한다.**
