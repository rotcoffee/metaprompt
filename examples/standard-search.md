<!-- 스모크 테스트 산출물 (2026-09-28, --yes 자동 경로). 스킬이 로드하지 않는다. 형식·품질 참고용. -->
<!-- metaprompt tier=standard domain=system mode=worktree baseline="p99 ≤ 200ms (base commit 64997e0 같은-머신 실측치 대비 회귀 0)" generated=2026-09-28
     regenerate: /metaprompt "api/search 엔드포인트 응답 지연 개선, p99 목표 200ms" --tier standard --profile system --mode worktree --from prompts/metaprompt-standard-search.md --out prompts/metaprompt-standard-search.md -->

# 목표

`/api/search` 엔드포인트의 응답 지연 개선(`src/search.js` 의 `search(q, rows)` + `buildFacets(rows)` 를 감싸는 HTTP 핸들러의 꼬리 지연을 내리는 것)을 만들어줘. **p99 ≤ 200ms (base commit 64997e0 같은-머신 실측치 대비 회귀 0)** 수준이어야 한다.
Node.js ≥ 22.12 (`node --test` · `perf_hooks.monitorEventLoopDelay` · ESM 문법 자동 감지) 가 필요하다 — 시작 전 `node -v` 로 확인하고 없으면 멈추고 보고해라. 외부 패키지를 추가하지 말고 node 내장 모듈만 쓴다. 이 저장소에는 HTTP 서버·벤치 하니스·테스트 파일이 **없다** (`package.json` 의 `bench` 스크립트가 가리키는 `bench/run.js` 도 없다 — 사전 결함이지 회귀가 아니다). 그래서 라운드 0 에서 하니스를 먼저 만들어 별도 커밋으로 고정하고, 그 하니스로 base 와 현재를 같은 머신에서 나란히 잰다. 그 실측치가 진짜 기준선이다.

"동작하는 수준"이 아니라 "p99 ≤ 200ms (base commit 64997e0 같은-머신 실측치 대비 회귀 0)과 나란히 놓고 비교해도 밀리지 않는 수준"이 목표다.
이 수준이면 실패다: "event loop p99 가 지속적으로 10ms 를 넘으면 뭔가 블로킹 중이라는 신호다" (tracekit.dev) · "p99 latency doesn't just affect 1% of users — it causes latency spikes for everyone who happens to be waiting behind a slow request" (last9.io). 평균·중앙값만 보고하고 p99·최댓값을 빠뜨린 개선 보고, 등가성 확인 없는 개선 보고는 이 과제에서 수치 자체를 무효로 친다.

## 기준점 상세

- base commit `64997e0` 의 `search(q, rows)` 는 요청마다 rows 전체를 `JSON.stringify` 한 뒤 문자열 포함 여부로 거르는 O(n) 선형 스캔이고, `buildFacets(rows)` 는 호출마다 모든 row 의 키별 카운트를 다시 집계한다. 인덱스·캐시·페이지네이션 없음. 현행 p50/p95/p99/max 는 **어디에도 기록돼 있지 않다** — 첫 순차 항목 "현행 측정"이 그 수치를 만든다.
- Node.js 이벤트 루프 지연의 정상선은 10ms 미만. 50ms 이상이 지속되면 무언가가 루프를 막고 있는 것이고, 그 순간 대기 중인 **모든** 요청의 응답이 함께 밀린다. 출처: last9.io/blog/node-js-key-metrics · tracekit.dev/blog/nodejs-monitoreventloopdelay-eventlooputilization
- 대형 힙의 major GC 정지는 50–200ms — 한 번의 정지가 p99 200ms 예산 전부를 먹을 수 있다. 요청마다 rows 전체를 직렬화하는 현재 구조가 바로 그 GC 압력을 만든다. 출처: 2 와 같음
- HTTP 프레임워크 계층의 참조치: 같은 벤치에서 Fastify 5,618 req/s · p99 71ms, Express 4,231 req/s · p99 94ms. 이 저장소는 `node:http` 를 직접 쓰므로 HTTP 계층은 수십 ms 급 이하이고, 200ms 예산의 병목은 핸들러(`search.js`) 안에 있다고 봐야 한다. 출처: michaelguay.dev/express-vs-fastify-a-performance-benchmark-comparison · fastify.dev/benchmarks
- 측정 방법론: 닫힌 루프(고정 동시성) 부하는 coordinated omission 때문에 서버가 느려질수록 p99 를 **과소보고**한다 (사례에 따라 최대 25배 (출처 미확인: HN 스레드 인용치)). 반드시 열린 루프(고정 도착률)로 잰다. 웜업 반복은 버리고, 반복 간 편차가 10% 이내로 안정된 뒤 수집하며, 3회 이상 반복한다. 출처: news.ycombinator.com/item?id=25240114 · engineering.appfolio.com/appfolio-engineering/2017/5/2/what-about-warmup
- 이 스택의 흔한 안티패턴: 동기 I/O·대형 JSON 직렬화·파국적 백트래킹 정규식의 이벤트 루프 블로킹, 무제한 결과 집합(페이지네이션 부재 → 직렬화·네트워크 지연 증폭), N+1 조회. 출처: dev.to/zyvop/nodejs-performance-profiling-finding-the-bottleneck-before-your-users-do-bnm · dev.to/sanmish4/unbounded-data-fetching-a-silent-performance-anti-pattern-in-api-and-database-layers-1dnk · freecodecamp.org/news/n-plus-one-query-problem

## 작업 격리

이 작업은 `../repo-metaprompt-api-search-p99` 안에서만 한다.
브랜치 `metaprompt/api-search-p99` · base commit `64997e004c58c15867a614893886057155e4f572` · 기준 브랜치 `main`.

깨면 안 되는 바닥: base commit 시점에 통과하던 것은 전부 그대로 통과해야 한다.
확인 커맨드: `npm test`

아래는 worktree 밖의 공유 상태다. **건드리지 마라.**

- `git push`, 태그 생성, `main` 로의 병합
- 실제 DB·마이그레이션 실행, 외부 API 쓰기 호출
- `.env`, 로컬 설정, 빌드·패키지 캐시, 전역 패키지 설치
- 포트: worktree 서버는 `43117`, base 비교 서버는 `43118` 만 쓴다. 다른 포트를 열지 마라
- 측정 중 같은 머신에서 다른 빌드·테스트·개발 서버·`npm install` 을 돌리지 않는다. 측정 직전 `uptime` 과 `ps -eo pid,pcpu,comm --sort=-pcpu | head -5` 로 확인하고 결과를 판정문에 남긴다
- 부모 저장소(`repo/`)와 그 상위 `scratchpad/`·형제 디렉터리에 파일을 쓰지 않는다. 유일한 예외는 검증 절의 `../base-perf` 이고, 측정이 끝나면 제거한다
- `package.json` 의 기존 `scripts`(`test`·`build`·`bench`) 를 지우거나 이름을 바꾸지 않는다. `"type": "module"` 추가는 허용, `dependencies`·`devDependencies` 추가는 금지
- 벤치 데이터셋은 `bench/data/` 안에 시드 고정으로 생성한다. 저장소 밖 데이터·외부 네트워크 호출 없음
- 하니스 커밋 이후 `bench/**`·`test/**` 는 동결이다. 고쳐야 한다면 최적화 커밋과 섞지 말고 멈추고 보고해라

건드려야만 목표에 도달할 수 있다면 **멈추고 보고해라.** 임의로 진행하지 마라.

## 실행 예산 (tier: standard)

- 라운드 상한 **3**. 팬아웃 서브에이전트는 동시에 최대 **3개**.
- 서브에이전트 보고는 **30줄 이내**로 받아라. 코드·로그·스크린샷 전체를 부모 컨텍스트로 올리지 마라.
  상세는 파일에 두고 경로와 결론만 보고한다. 컨텍스트가 길어질수록 뒤 라운드의 판단이 흐려진다.
- 검증자 판정문은 `verdicts/round-N.md` 에 저장한다. 다음 라운드 작업 지시는 **실패 항목만** 추려서 넘긴다.
  통과 항목의 근거는 다시 읽지 않는다.
- 라운드마다 커밋한다 (`round N: <한 줄 요약>`). 커밋이 없으면 중간 상태 복원도, 개선 전후 비교도 못 한다.
- 검증 증거 범위: 동일 조건 재측정 3회 + 순서 교차 1회 · 등가성 대조 1만 건 · 장애 주입 1개(자원 고갈) · 지속 부하 15분 · 롤백 실제 실행

## 병렬로 진행할 것 (서브에이전트 팬아웃)

아래 항목은 서로 독립적이다. 각각 별도 서브에이전트에 배분해서 동시에 진행해.
셋은 라운드 0 에서만 돈다. 공통 계약(파일 경로·환경변수·출력 JSON 키)을 아래에 못 박았으니 서로 물어보지 말고 계약대로 만든다. 통합·커밋은 순차 코어가 한다.

- **하니스 A — 서버·부하 생성기·데이터셋** (`bench/server.js` · `bench/run.js` · `bench/data/gen.js` · `bench/profile.json`). `node:http` 만 사용. 서버: `GET /api/search?q=<질의>` → `SEARCH_IMPL` 환경변수 경로(기본 `../src/search.js`)에서 `search`/`buildFacets` 를 `import()` 하고, 시작 시 `bench/data/rows.json`(`gen.js` 가 시드 42 로 만드는 20,000 행, 각 행 6~8개 키)을 한 번 로드해 `{ "hits": search(q, rows), "facets": buildFacets(rows) }` 를 JSON 으로 응답. `PORT` 환경변수. `perf_hooks.monitorEventLoopDelay({ resolution: 10 })` 를 켜고 `GET /__metrics` 로 `{ "loopDelayP99Ms", "loopDelayMaxMs", "heapUsed", "rss", "errors" }` 를 노출. 부하 생성기: **열린 루프 고정 도착률**(setTimeout 스케줄, 기본 `--rate 50` req/s · `--duration 60` 초), `bench/profile.json` 의 질의 4종 가중 혼합(한 글자 25% · 흔한 토큰 40% · 매치 0건 20% · 빈 문자열 15%), 처음 `--warmup 30` 초는 폐기, 결과를 `bench/results/<label>.json` 에 `{ "p50", "p95", "p99", "max", "count", "errors", "byCase": { "<case>": { "p99", "max" } }, "loopDelayP99Ms" }` (ms 단위)로 저장. 옵션 `--port --rate --duration --warmup --label`.
- **하니스 B — 등가성 대조기·지속 부하** (`bench/equiv.js` · `bench/soak.js`). `equiv.js`: 시드 7 로 질의 10,000 건 생성(4종 케이스 혼합), `SEARCH_A`·`SEARCH_B` 환경변수 경로의 두 구현을 `import()` 해 같은 `bench/data/rows.json` 에 대해 `search(q, rows)`·`buildFacets(rows)` 결과를 `JSON.stringify` 로 바이트 비교, `bench/results/equiv.json` 에 `{ "total", "mismatches", "firstMismatch": { "q", "aHead", "bHead" } }` 기록, mismatches > 0 이면 exit 1. `soak.js`: `run.js` 를 `--duration 900` 으로 돌리며 10초마다 `/__metrics` 의 `heapUsed`·`rss` 를 `bench/results/soak.json` 에 시계열로 기록하고 첫 5분·마지막 5분 평균을 함께 출력.
- **문서·런북** (`bench/README.md`). 측정 조건(머신·`node -v`·데이터셋 시드·프로파일·포트 43117/43118), 라운드별 측정 절차(검증 절의 커맨드를 그대로), **롤백 절차**를 실행 가능한 커맨드로: `git checkout -b rollback-check && git revert --no-edit <최적화 커밋 범위> && npm test && node bench/run.js --port 43117 --label rollback && git checkout metaprompt/api-search-p99 && git branch -D rollback-check`. 하니스 계약(위 A·B 의 파일·환경변수·JSON 키)을 표로 한 번 더 적는다.

## 순차로 진행할 것 (쪼개지 마)

하니스 통합·커밋 → 현행 측정 → 프로파일링 → 변경 1개 → 재측정 의 코어는 한 에이전트가 처음부터 끝까지 맡아.
이유: 같은 `src/search.js` 와 같은 측정 기준선(`bench/results/`, `../base-perf`, 포트 43117/43118)에 쓰기를 한다. 여러 최적화를 동시에 넣으면 무엇이 효과였는지 영원히 알 수 없다. 변경은 한 번에 하나, 각각 재측정.
여기를 병렬로 쪼개면 부분별로는 그럴싸해 보여도 이음매에서 버그가 난다.

**측정 없이 최적화하지 마라.** 추측으로 고치지 말고 프로파일이 가리키는 최상위 병목 하나만 고친다.

0. 하니스 통합 (라운드 0): 팬아웃 산출물을 붙여 `node bench/data/gen.js && npm run bench` 가 돌게 한다. `package.json` 에 `"type": "module"` 을 추가한다 (`src/search.js` 가 `export` 문법인데 이 필드가 없다 — 사전 결함). `test/search.test.js` 에 `node:test` 로 `search`·`buildFacets` 의 고정 입력 5건 스냅샷 테스트를 넣는다. 커밋 `round 0: bench harness` → 이 커밋 SHA 를 `HARNESS_SHA` 로 `verdicts/round-0.md` 첫 줄에 적는다. 이후 `bench/**`·`test/**` 는 동결.
1. 현행 측정 (라운드 0): base 의 `npm test` 종료 코드를 `../base-perf` 에서 기록한다 (base 에는 테스트 파일이 0개다 — 그 상태가 바닥이다). 검증 절의 측정 커맨드로 base 서버(43118)와 현재 서버(43117)를 각 3회 + 순서 교차 1회 잰다. 라운드 0 에서는 `src/search.js` 가 base 와 같으므로 두 결과가 오차 범위(p99 편차 10%) 안에 있어야 한다 — 벗어나면 하니스가 잘못된 것이니 최적화로 넘어가지 마라. base 의 p50/p95/p99/max 표를 `verdicts/round-0.md` 에 남긴다.
2. 프로파일링: `PORT=43117 node --cpu-prof --cpu-prof-dir=bench/results/prof bench/server.js` 로 부하 중 CPU 프로파일을 뜨고, 상위 3 핫스팟(함수·self time 비율)을 `verdicts/profile-round-N.md` 에 적는다.
3. 변경 1개: 최상위 병목 하나만 `src/search.js` 안에서 고친다. 후보 순서 — (a) 요청마다 rows 전체를 `JSON.stringify` 하는 대신 rows identity 기준으로 정규화된 검색 문자열을 1회 만들어 재사용(WeakMap 캐시) (b) `buildFacets` 를 rows identity 기준으로 메모이즈 (c) 결과 직렬화 크기 축소. 공개 시그니처 `search(q, rows)`·`buildFacets(rows)` 와 반환 형태는 그대로. 커밋 `round N: <무엇을 왜>`.
4. 재측정 후 검증자에게 넘긴다. 미달이면 2 로 돌아가 **다음** 병목 하나. 한 라운드에 변경 하나.

## 검증

만드는 에이전트와 **별개의** 검증 에이전트를 둬. 자기가 만든 걸 자기가 채점하지 마.
검증자는 아주 가혹한 비평가여야 하고, 기본 태도는 거부다.

검증자는 **base commit `64997e004c58c15867a614893886057155e4f572` 대비 diff 와 실제 실행 결과물**만 근거로 삼아라.
라운드 커밋 메시지와 만든 에이전트의 자기 보고는 근거가 아니다.

    git diff 64997e004c58c15867a614893886057155e4f572...HEAD
    npm test

**검증자는 다음 방법으로 직접 증거를 확보한 뒤 판정해라. 추정하지 마라.**

검증자는 코드를 읽고 빨라졌을 것이라고 판단하지 마라. **계측한 값만 근거로 인정한다.**

    git worktree add ../base-perf 64997e004c58c15867a614893886057155e4f572   # 이미 있으면 생략
    uptime; ps -eo pid,pcpu,comm --sort=-pcpu | head -5                        # 경합 프로세스 없음을 판정문에 남긴다
    node bench/data/gen.js                                                     # rows.json (시드 42) — 이미 있으면 생략
    SEARCH_IMPL=../base-perf/src/search.js PORT=43118 node bench/server.js &  # base
    PORT=43117 node bench/server.js &                                          # 현재
    for i in 1 2 3; do
      node bench/run.js --port 43118 --label base-$i
      node bench/run.js --port 43117 --label cur-$i
    done
    node bench/run.js --port 43117 --label cur-x; node bench/run.js --port 43118 --label base-x   # 순서 교차
    kill %1 %2
    git worktree remove ../base-perf   # 모든 라운드가 끝나면 정리

1. 동일 조건 재측정: 같은 부하 프로파일(50 req/s · 60초 · 웜업 30초 폐기 · 질의 4종 혼합)·같은 머신으로 base/현재 각 3회 + 순서 교차 1회. `bench/results/{base,cur}-*.json` 의 p50/p95/p99/max 를 표로, 반복 간 p99 (최대−최소)/중앙값 을 분산으로 함께. 10% 를 넘으면 웜업을 늘려 다시 잰다.
2. 등가성 확인: `SEARCH_A=../base-perf/src/search.js SEARCH_B=./src/search.js node bench/equiv.js` → `bench/results/equiv.json` 의 `mismatches` 가 0 이어야 한다. 성능은 정확성을 깎아 얻을 수 있으므로 이 확인 없이는 어떤 수치도 무효다.
3. 장애 주입 1개 (자원 고갈): `PORT=43117 node --max-old-space-size=64 bench/server.js &` 로 힙 상한을 64MB 로 낮춘 채 `node bench/run.js --port 43117 --label cur-heap64` 를 돌린다. 프로세스 종료 0회 · HTTP 5xx 0건이어야 하고, p99 악화 폭은 판정문에 "교환된 것"으로 적는다. 조용히 빈 결과를 내는 것이 가장 나쁘다 — `cur-heap64` 의 케이스별 `count` 가 정상 실행과 같은지 대조해라.
4. 지속 부하: `node bench/soak.js --port 43117 --duration 900` (15분). `bench/results/soak.json` 에서 마지막 5분의 `heapUsed`·`rss` 평균이 첫 5분 평균의 1.2배 이하여야 한다.
5. 롤백 실행: `bench/README.md` 의 롤백 커맨드를 **실제로 실행**한다 (`rollback-check` 브랜치에서 최적화 커밋을 revert → `npm test` → `node bench/run.js --port 43117 --label rollback` → 원래 브랜치 복귀). 실행 로그를 `verdicts/rollback-round-N.log` 에 남긴다.

측정 환경을 재현할 수 없으면 그 범위를 판정문에 명시하고 어떤 수치가 추정인지 구분해라.

회귀 통 — 도메인 항목과 **별도로** 전 항목 Yes 여야 한다:

- [ ] base commit `64997e004c58c15867a614893886057155e4f572` 에서 통과하던 것이 전부 그대로 통과하는가 (`npm test`) — base 에는 테스트 파일이 0개이므로 라운드 0 에 기록한 base 의 종료 코드가 바닥이고, 이후 라운드는 exit 0 이면서 `test/search.test.js` 전부 통과여야 한다
- [ ] `git diff --stat 64997e004c58c15867a614893886057155e4f572...HEAD` 의 변경 파일이 전부 이 주제의 범위 안인가 (`src/search.js` · `bench/**` · `test/**` · `package.json` 의 `type` 필드 · `verdicts/**` 외에는 없어야 한다)
- [ ] 변경된 공개 인터페이스의 호출부가 저장소 전체에서 갱신됐는가 (`grep -rn "search(\|buildFacets(" --include=*.js .` 결과로 보여라). `search(q, rows)`·`buildFacets(rows)` 의 export 이름·인자 순서·반환 형태를 바꾸지 않는 것이 기본이다
- [ ] 벤치 하니스·부하 생성기·측정 스크립트 자체가 하니스 커밋 이후 변경되지 않았는가 (`git diff --stat <HARNESS_SHA>...HEAD -- bench/ test/` 가 비어 있는가). 변경했다면 base 도 새 하니스로 다시 측정했고 그 결과가 판정문에 있는가

체크리스트 — 전 항목 Yes여야 통과:

- [ ] 등가성: base `64997e0` 와 현재 구현에 동일 입력 1만 건을 넣었을 때 `search()`·`buildFacets()` 출력이 `JSON.stringify` 바이트 단위로 일치하는가 (`bench/results/equiv.json` 의 `mismatches` == 0)
- [ ] 측정 안정성: base/현재 각 3회 반복의 p99 편차(최대−최소)가 중앙값의 10% 이내이고, 순서 교차 측정(`cur-x`·`base-x`)에서도 base 와 현재의 우열이 뒤집히지 않는가
- [ ] 부하 중 이벤트 루프 지연 p99 가 10ms 이하인가 (`bench/results/cur-*.json` 의 `loopDelayP99Ms`, 3회 모두)
- [ ] 오류(HTTP 5xx·타임아웃·미처리 예외)가 base 와 같은 0건인가 (`errors` == 0, 3회 모두) — 하나라도 늘면 실패
- [ ] 케이스별 p99 가 4종(한 글자·흔한 토큰·매치 0건·빈 문자열) 모두 보고되고, 전 케이스의 `max` 가 1,000ms 이하인가 (major GC 정지 50–200ms 급 스파이크가 꼬리를 먹지 않는가)
- [ ] 지속 부하 15분에서 `heapUsed`·`rss` 가 단조 증가하지 않는가 (마지막 5분 평균 ≤ 첫 5분 평균 × 1.2, 둘 다)
- [ ] 힙 상한 64MB 자원 고갈 주입에서 프로세스 크래시 0회·5xx 0건이고, 롤백 커맨드를 실제 실행해 `npm test` 와 `run.js --label rollback` 이 다시 통과·측정됐는가 (`verdicts/rollback-round-N.log` 존재)

검증자는 아래 형식으로 `verdicts/round-N.md` 에 남겨라.

- 항목별 **pass/fail 과 근거**(측정값·라인 번호·재현된 수치). 근거 없는 pass 는 무효다.
- **수용된 제약**: 이 과제의 전제상 원리적으로 해결 불가능한 지적은 실패가 아니라 여기에 적어라.
  실패로 집계하면 정체 감지 규칙이 잘못 발동한다. (예: base 에 테스트 파일이 없어 "base 통과 집합"이 비어 있는 것, 이 머신에서 재현 불가한 하드웨어 조건)
- 남은 격차가 **요구사항 자체에서 강제된 것인지** 한 문단으로 답해라.
- 점수는 보조 신호다. 항목별 판정과 근거 수치가 1차 결론이다.
- **교환된 것**을 따로 적어라: 목표에 도달했더라도 메모리·시작 시간·코드 복잡도 중 무엇을 얼마나 내줬는지 수치로.

## 종료 조건

체크리스트 7항목 전 항목 Yes + 회귀 통 4항목 전 항목 Yes + 고정 부하 프로파일(50 req/s · 60초 · 질의 4종 혼합)에서 현재 구현의 p99 3회 중앙값이 200ms 이하 + base commit `64997e0` 대비 회귀 0건(오류·max·메모리·`npm test` 어느 것도 악화 없음) · 최대 3라운드.
미달이면 지적된 항목만 다시 만들어서 재검증해.
3라운드까지 통과 못 하면 멈추고, 남은 미달 항목과 그 이유를 보고해.
개선 여지가 없다는 결론도 정당하다 — 병목이 `search.js` 밖(하니스·HTTP 계층·머신)에 있음을 계측으로 보였다면 그것으로 종료하고 근거 수치를 판정문에 남긴다.

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
