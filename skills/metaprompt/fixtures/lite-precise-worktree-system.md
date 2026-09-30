<!-- metaprompt route=precise tier=lite domain=system mode=worktree baseline="base commit 9c1e2d4 · 주문 합계 명세 §3.2" generated=2026-09-30
     regenerate: /metaprompt "할인과 쿠폰을 같이 쓰면 주문 합계가 가끔 1원 틀리는 버그" --route precise --tier lite --profile system --mode worktree --from prompts/metaprompt-order-total.md --out prompts/metaprompt-order-total.md -->
<!-- 형식 표본. 수치는 예시다. -->

# 목표

할인과 쿠폰을 같이 적용한 주문의 합계가 1원 틀리는 버그를 고쳐줘. 기준은 **base commit 9c1e2d4 · 주문 합계 명세 §3.2** 이고, 완료는 의견이 아니라 종료 코드가 판정한다.
Python 3.12 · 의존성 추가 없음 · 공개 함수 `order_total(order)` 의 시그니처 유지.

완료 = `pytest tests/test_total_rounding.py -q` 와 `pytest -q` 가 exit 0, 그리고 먼저 쓴 회귀 테스트가 고쳐지지 않은 채로 통과.
증상만 가리는 수정(합계 뒤에서 1원 보정·예외 삼키기)이나 테스트를 고쳐 통과시킨 것은 실패다.

## 기준점 상세

- base 9c1e2d4 에서 `pytest -q` 는 212 passed, 0 failed (지금 깨진 것은 없다)
- 재현: 정가 9,990원 × 3개, 10% 할인 후 1,000원 쿠폰 → 기대 25,973원, 실제 25,974원 (출처: 이슈 #481)
- 명세 §3.2: 할인은 품목별로 적용해 원 단위 내림, 쿠폰은 할인 합계 뒤 한 번 — 계산 순서가 합계에 영향을 준다
- `order_total` 호출부 7곳 (`grep -rn "order_total(" src/`)

## 작업 격리

이 작업은 `../shop-metaprompt-order-total` 안에서만 한다. 브랜치 `metaprompt/order-total` · base commit `9c1e2d4a7b3f5e6d8c0a1b2c3d4e5f6a7b8c9d0e` · 기준 브랜치 `main`.
깨면 안 되는 바닥: base commit 에서 통과하던 것은 전부 그대로 통과해야 한다. 확인 커맨드: `pytest -q`

아래는 worktree 밖의 공유 상태다. **건드리지 마라.**

- `git push`, 태그 생성, `main` 로의 병합
- 실제 DB·마이그레이션 실행, 외부 API 쓰기 호출
- `.env`, 로컬 설정, 빌드·패키지 캐시, 전역 패키지 설치
- `fixtures/prices.json` (다른 테스트들이 공유하는 가격 데이터)

건드려야만 목표에 도달할 수 있다면 **멈추고 보고해라.**

## 실행 예산 (route: precise · tier: lite)

- 메인 세션 effort **medium** — `claude --effort medium` 으로 시작한다 (도중에는 `/effort medium`). xhigh·max 는 이득을 실측하지 않았으면 쓰지 않는다.
- 라운드 상한 **2**. 팬아웃 없음 — 빌더는 메인 세션 하나다. 혼자 끝낼 수 있는 일을 위임하지 마라.
- 역할 — effort 는 에이전트 정의 frontmatter 로만 지정된다 (Agent 호출에는 effort 가 없다). 세션 **시작 전에** `python3 <metaprompt>/scripts/agents.py <이 파일>` 이 아래 표로 `.claude/agents/mp-*.md` 를 만든다. 정의가 로드되지 않았으면 호출에 model 만 지정하고, effort 가 세션값을 상속했다고 판정문에 적는다.

  | 역할 | 정의 | model | effort | 맡는 일 |
  |---|---|---|---|---|
  | 메인 세션 (오케스트레이터·빌더) | — | 세션 모델 | medium | 빨강 → 수정 → 초록 |
  | 검증자 | mp-verifier | opus | high | 마지막 라운드 1회, 정확성만 |

- 기능 스위치:
  - agent teams **OFF** — 원인 후보가 `pricing.py` 한 파일의 계산 순서에 몰린 순차 작업이다.
  - Workflow **OFF** — 증거는 pytest 두 번이다. 묶을 독립 실행이 없다.
  - 루프 **/goal ON** — 완료가 종료 코드라 새 컨텍스트 평가자가 판정할 수 있고 `-p` 에서도 돈다.
  - `/goal` 줄 (첫 입력): `/goal prompts/metaprompt-order-total.md 를 읽고 따른다. 완료: pytest tests/test_total_rounding.py -q 와 pytest -q 가 exit 0 으로 출력되고 git diff <red SHA>..HEAD -- tests/test_total_rounding.py 가 비어 있음. 또는 2 라운드 후 멈추고 보고`
- 턴 종료 규약: 텍스트만 있는 턴 종료는 완료가 아니다. 종료 조건 미달이고 라운드 상한 전이면 남은 체크리스트 항목을 다시 적고 이어 간다. 사람 입력 없는 자동 재개는 연속 2회까지 — 그 뒤엔 멈추고 남은 항목을 보고한다.
- 서브에이전트 보고는 **30줄 이내**. 코드·로그 전체를 부모 컨텍스트로 올리지 말고 파일 경로와 결론만.
- 판정문은 `verdicts/round-N.md`. 다음 라운드에는 **실패 항목만** 넘기고, 통과 항목의 근거는 다시 읽지 않는다.
- 라운드마다 커밋한다 (`round N: <한 줄 요약>`).
- 검증 증거 범위: 회귀 테스트 red/green 종료 코드 · 전체 스위트 · 동일 입력 1천 건 등가성

## 사전조건 (검증 도구)

라운드 0 에서 확인한다. 사용자 공간 설치(pip·바이너리)는 직접 하고, 시스템 수준(드라이버·apt·docker)이면 **멈추고 사용자에게 요청**한다. 도구 없이 상상으로 채점하지 마라.

| 도구 | 확인 | 없을 때 |
|---|---|---|
| python3 ≥ 3.12 | `python3 --version` | 시스템 수준 — 멈추고 요청 |
| pytest | `python3 -m pytest --version` | `uv pip install pytest` |

## 순차로 진행할 것 (쪼개지 마)

1. **빨강 먼저** — `tests/test_total_rounding.py` 에 증상·명세를 검사하는 회귀 테스트를 쓰고, 고치기 전에 `pytest tests/test_total_rounding.py -q` 가 exit ≠ 0 임을 확인해 `round 0: red` 로 커밋한다. 그 SHA 를 판정문에 적는다.
2. 이후 `tests/test_total_rounding.py` 는 수정하지 않는다 — `git diff <red SHA>..HEAD -- tests/test_total_rounding.py` 가 비어야 한다. 테스트가 틀렸다고 판단되면 멈추고 보고한다.
3. 원인 지점을 고친다 → `pytest tests/test_total_rounding.py -q` exit 0 → `pytest -q` exit 0.

외부 리서치는 하지 않는다 — 기준점은 base commit 과 명세다.
아래 전부를 메인 세션이 순서대로 처리한다. 이 티어는 이음매를 다시 붙일 예산이 없다.
재현 테스트 · `pricing.py` 의 계산 순서 수정 · 호출부 확인은 한 에이전트가 처음부터 끝까지 맡아.
이유: 같은 계산 함수와 같은 반올림 규칙에 쓴다. 쪼개면 부분별로는 그럴싸해도 이음매에서 버그가 난다.

## 검증

만드는 에이전트와 **별개의** 검증을 둔다. 자기가 만든 걸 자기가 채점하지 마.
1차 판정은 먼저 잠긴 테스트의 종료 코드다 — 만든 쪽이 테스트를 바꿀 수 없다. `/goal` 평가자가 턴마다 출력을 읽고, 마지막 라운드에 `mp-verifier` 가 한 번 새 컨텍스트로 정확성만 본다: 테스트가 명세를 실제로 검사하는가, diff 가 증상만 가리는가.
보고 범위는 **아래 체크리스트 항목과 정확성 결함으로 한정**한다 — 새 컨텍스트 리뷰어는 결과가 멀쩡해도 뭔가를 보고하는 경향이 있다. 취향 지적은 판정에 넣지 않는다. 근거 없는 pass 는 무효다.

근거는 **base commit `9c1e2d4a7b3f5e6d8c0a1b2c3d4e5f6a7b8c9d0e` 대비 diff 와 실제 실행 결과**뿐이다. 커밋 메시지와 만든 쪽의 자기 보고는 근거가 아니다.

    git diff 9c1e2d4a7b3f5e6d8c0a1b2c3d4e5f6a7b8c9d0e...HEAD
    pytest -q

**직접 증거를 확보한 뒤 판정해라. 추정하지 마라.**

```
git checkout <red SHA> && pytest tests/test_total_rounding.py -q; echo "red exit=$?"      # ≠ 0 이어야 한다
git checkout metaprompt/order-total && pytest tests/test_total_rounding.py -q; echo "green exit=$?"
pytest -q; echo "suite exit=$?"
git worktree add ../base-eq 9c1e2d4a7b3f5e6d8c0a1b2c3d4e5f6a7b8c9d0e
python3 scripts/eq_check.py --base ../base-eq --head . --n 1000   # 할인·쿠폰 없는 동일 입력 1천 건의 합계가 같은지
git worktree remove ../base-eq
```

회귀 통 — 체크리스트와 **별도로** 전 항목 Yes 여야 한다:

- [ ] base commit `9c1e2d4a7b3f5e6d8c0a1b2c3d4e5f6a7b8c9d0e` 에서 통과하던 것이 전부 통과하는가 (`pytest -q` exit 0)
- [ ] `git diff --stat 9c1e2d4a7b3f5e6d8c0a1b2c3d4e5f6a7b8c9d0e...HEAD` 의 변경 파일이 전부 범위 안인가
- [ ] 변경된 공개 인터페이스의 호출부가 전부 갱신됐는가 (`grep` 결과로)
- [ ] 할인·쿠폰이 없는 주문에서 동일 입력 1천 건의 합계가 base 와 같은가 (등가성, 회귀 0건)

체크리스트 — 전 항목 Yes 여야 통과:

- [ ] 회귀 테스트가 red 커밋에서 exit ≠ 0, HEAD 에서 exit 0 인가 (`pytest tests/test_total_rounding.py -q`)
- [ ] red 이후 `tests/test_total_rounding.py` 의 diff 가 0줄인가
- [ ] 수정이 명세 §3.2 의 계산 순서(품목별 할인 내림 → 쿠폰 1회)에 있고, 합계 뒤 보정이 아닌가
- [ ] 이슈 #481 의 재현 입력이 25,973원을 내는가

판정문 `verdicts/round-N.md` 형식:

- 항목별 **pass/fail 과 근거**(측정값·라인 번호·종료 코드).
- **수용된 제약**: 과제 전제상 원리적으로 해결 불가능한 지적은 실패가 아니라 여기에 적는다. 실패로 세면 정체 감지가 잘못 발동한다.
- 남은 격차가 **요구사항 자체에서 강제된 것인지** 한 문단.

## 종료 조건

`pytest tests/test_total_rounding.py -q` 와 `pytest -q` 의 종료 코드 0 · 잠금 diff 비어 있음 · 체크리스트 전 항목 Yes · 최대 2라운드.
미달이면 지적된 항목만 다시 만들어 재검증한다. 2라운드까지 못 닿으면 멈추고 남은 항목과 이유를 보고한다.

검증자의 **판정**은 받아들이되 **처방**은 체크리스트 전체와 대조한다 — 한 항목을 고치며 다른 항목을 깨는 교환은 손해다.
같은 지적이 2라운드 연속 반복되면 접근이 틀린 것이다. 멈추고 보고한다 (수용된 제약은 세지 않는다).

## 완료 후

전 항목 Yes 여도 **병합하지 마라.** 브랜치 `metaprompt/order-total` 의 최종 커밋 · 마지막 `verdicts/round-N.md` · `git diff --stat 9c1e2d4a7b3f5e6d8c0a1b2c3d4e5f6a7b8c9d0e...HEAD` 요약을 남기고 멈춘다.
기준 브랜치가 움직였으면 최신 `main` 을 머지하고 **회귀 통만** 다시 돌려 판정문에 덧붙인다. **병합 여부는 사람이 판정문을 읽고 결정한다.**
