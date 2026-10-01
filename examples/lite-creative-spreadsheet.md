<!-- metaprompt route=creative tier=lite domain=product mode=greenfield baseline="Google Sheets" generated=2026-09-30
     regenerate: /metaprompt "스프레드시트 UI, 단일 HTML 파일" --route creative --tier lite --profile product --mode greenfield --from prompts/metaprompt-spreadsheet-ui.md --out prompts/metaprompt-spreadsheet-ui.md -->

# 목표

브라우저에서 파일 하나(`spreadsheet.html`)로 열리는 스프레드시트 UI 를 만들어줘. **Google Sheets** 을 넘어서는 수준이어야 한다.
제약: HTML·CSS·JS 가 모두 이 파일 하나 안에 있다. 외부 CDN·폰트·빌드 도구·npm 없이 `file://` 로 열어서 동작한다 (node 가 없는 환경).

"동작하는 수준"이 아니라 "Google Sheets과 나란히 놓아도 밀리지 않고, 선택한 셀의 참조 셀과 의존 셀을 격자 위에 바로 그려 주는 수식 추적에서는 앞서는 수준"이 목표다.
이 파일은 명세가 아니라 **바닥**이다 — 적히지 않은 것도 주제를 들은 사용자가 기대하면 만들고, 적힌 수치는 하한이다.
실패의 정의: `<table contenteditable>` 을 깔아 놓은 튜토리얼 예제나 Jspreadsheet CE 기본 데모와 화면·조작감이 구분되지 않으면 실패다.

## 기준점 상세

- Google Sheets: 스프레드시트 하나당 셀 상한 1,000만 개, 열 상한 18,278개(ZZZ) (출처 미확인)
- Google Sheets: 새 시트 기본 격자는 1,000행 × 26열(A–Z) (출처 미확인)
- Google Sheets: 수식 바·셀 안 편집·채우기 핸들·Ctrl+Z/Ctrl+Y·시스템 클립보드 TSV 붙여넣기 지원 (출처 미확인)
- Google Sheets: Excel 의 "참조되는 셀 추적 / 참조하는 셀 추적"(Trace Precedents/Dependents) 화살표에 해당하는 기본 기능이 없다 — 수식 셀을 편집할 때만 참조 범위에 색 테두리가 뜬다 (출처 미확인)
- Google Sheets: 계정·네트워크가 필요하다. 오프라인 모드는 Chrome 확장과 사전 설정이 있어야 한다 (출처 미확인)

## 실행 예산 (route: creative · tier: lite)

- 메인 세션 effort **medium** · model **opus** — `claude --model opus --effort medium` 로 시작한다 (도중에는 `/effort medium`). 세션 모델이 다르면 시작하지 말고 알린다. xhigh·max 는 이득을 실측하지 않았으면 쓰지 않는다.
- 라운드 상한 **2**. 팬아웃 없음 — 빌더는 메인 세션 하나다. 혼자 끝낼 수 있는 일을 위임하지 마라.
- 역할 — effort 는 에이전트 정의 frontmatter 로만 지정된다 (Agent 호출에는 effort 가 없다). 세션 **시작 전에** `python3 <metaprompt>/scripts/agents.py <이 파일>` 이 아래 표로 `.claude/agents/mp-*.md` 를 만든다. 정의가 로드되지 않았으면 호출에 model 만 지정하고, effort 가 세션값을 상속했다고 판정문에 적는다.

  | 역할 | 정의 | model | effort | 맡는 일 |
  |---|---|---|---|---|
  | 메인 세션 (오케스트레이터·빌더) | — | opus | medium | 설계·구현 전부, 라운드 커밋 |
  | 검증자 | mp-verifier | opus | high | 매 라운드 새 컨텍스트로 콜드 패스 + 렌더·실입력 증거 판정 |

- 기능 스위치:
  - agent teams **OFF** — lite 에 빌더 하나, 한 파일 산출물이라 조율할 흐름이 없다.
  - Workflow **OFF** — 증거 실행이 콜드 패스 + 캡처 2장으로 5개 미만이고 lite 다.
  - 루프 **내부 라운드 (/goal·/loop OFF)** — 완료 판정이 종료 코드가 아니라 검증자의 렌더 판단이라 `/goal` 의 Haiku 평가자가 대신할 수 없고, 검증 한 번이 15분보다 짧다.
- 턴 종료 규약: 텍스트만 있는 턴 종료는 완료가 아니다. 종료 조건 미달이고 라운드 상한 전이면 남은 체크리스트 항목을 다시 적고 이어 간다. 사람 입력 없는 자동 재개는 연속 2회까지 — 그 뒤엔 멈추고 남은 항목을 보고한다.
- 서브에이전트 보고는 **30줄 이내**. 코드·로그·스크린샷 전체를 부모 컨텍스트로 올리지 말고 파일 경로와 결론만.
- 판정문은 `verdicts/round-N.md`. 다음 라운드에는 **실패 항목만** 넘기고, 통과 항목의 근거는 다시 읽지 않는다.
- 라운드마다 커밋한다 (`round N: <한 줄 요약>`).
- 검증 증거 범위: 실입력 콜드 패스 1회 + 캡처 2장(기본 화면 1440폭 · 수식 추적을 켠 상태) + 텍스트 색 3쌍 대비비.

## 사전조건 (검증 도구)

라운드 0 에서 확인한다. 사용자 공간 설치(pip·바이너리)는 직접 하고, 시스템 수준(드라이버·apt·docker)이면 **멈추고 사용자에게 요청**한다. 도구 없이 상상으로 채점하지 마라.

| 도구 | 확인 | 없을 때 |
|---|---|---|
| Chrome (헤드리스 렌더·CDP) | `google-chrome --version` | 시스템 설치 필요 — 멈추고 사용자에게 요청 |
| python3 | `python3 --version` | 시스템 설치 필요 — 멈추고 사용자에게 요청 |
| uv (websockets 일회성 실행) | `uv --version` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` (사용자 공간) |
| websockets (CDP 실입력) | `uv run --with websockets python -c "import websockets"` | uv 가 자동 설치. pip 는 없다 — `pip install` 을 쓰지 마라 |
| node · playwright | 없음 (환경 확인됨) | 쓰지 않는다. CDP 는 python `websockets` 로 직접 구동 |

## 순차로 진행할 것 (쪼개지 마)

아래 전부를 메인 세션이 순서대로 처리한다. 이 티어는 이음매를 다시 붙일 예산이 없다.

1. 컬러·타이포·스페이싱 토큰(CSS 변수)과 격자 골격 — 행/열 머리글 고정, 1,000행 × 26열을 가상 스크롤로.
2. 셀 모델 · 선택/편집 상태 머신 · 키보드 이동 · 수식 바.
3. 수식 파서와 의존 그래프 · 재계산 · 오류값.
4. 수식 추적 오버레이 (의존 그래프를 격자 좌표 위에 그린다).
5. 클립보드 · 실행 취소 · 저장(localStorage) · 좁은 폭.

셀 모델·의존 그래프·격자 좌표계·선택 상태는 한 에이전트가 처음부터 끝까지 맡아.
이유: 재계산, 추적 오버레이, 가상 스크롤, 실행 취소가 모두 같은 셀 저장소와 같은 행/열 좌표계에 쓴다. 쪼개면 부분별로는 그럴싸해도 이음매에서 버그가 난다.

## 검증

만드는 에이전트와 **별개의** 검증을 둔다. 자기가 만든 걸 자기가 채점하지 마.
`mp-verifier` 를 매 라운드 새 컨텍스트로 띄운다. 판정은 아래 커맨드로 얻은 증거만.
검증자는 체크리스트를 읽기 **전에** 주제 한 줄("스프레드시트 UI, 단일 HTML 파일")만 아는 사용자로서 결과물을 써 본다 (콜드 패스). 기대했는데 안 되는 것이 **기본기 누락**이다.
보고 범위는 **아래 체크리스트 항목과 정확성 결함·기본기 누락으로 한정**한다 — 새 컨텍스트 리뷰어는 결과가 멀쩡해도 뭔가를 보고하는 경향이 있다. 취향 지적은 판정에 넣지 않는다. 근거 없는 pass 는 무효다.

**직접 증거를 확보한 뒤 판정해라. 추정하지 마라.**

검증자는 결과물을 **실제로 렌더링해서 픽셀을 보고** 판정해라. CSS 를 읽고 화면을 상상하지 마라.
콜드 패스는 **실제 입력**으로 한다: `--remote-debugging-port` 로 띄운 Chrome 에 CDP `Input.dispatchMouseEvent`·`dispatchKeyEvent`·`Input.insertText` (python `websockets`). 핵심 과업을 처음부터 해 본다 — 값 입력 → 수식 입력 → 참조 셀 수정 후 재계산 확인 → 복사·붙여넣기 → 되돌리기 → 새로고침 뒤 상태 → 390 폭. 주입한 `dispatchEvent` 는 실제 입력이 아니다.

    # 기본 화면 캡처
    google-chrome --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
      --virtual-time-budget=5000 --window-size=1440,987 --screenshot=verdicts/round-N-base.png "file://$PWD/spreadsheet.html"

    # 실입력 콜드 패스 — CDP 로 띄우고 검증자가 쓴 스크립트로 구동
    google-chrome --headless=new --disable-gpu --no-sandbox --remote-debugging-port=9222 \
      --user-data-dir=/tmp/mp-chrome --window-size=1440,987 "file://$PWD/spreadsheet.html" &
    curl -s http://127.0.0.1:9222/json      # webSocketDebuggerUrl 확인
    uv run --with websockets python verdicts/cdp_pass.py   # 입력·Page.captureScreenshot·Runtime.evaluate 로 측정

- 뷰포트 크기는 가정하지 말고 스크립트로 `innerWidth`·`innerHeight` 를 읽는다 (Chrome 버전마다 다르다).
- 다른 상태(수식 추적 켬·좁은 폭)는 원본 **사본**에 스크립트를 주입해 만들거나 CDP 실입력으로 만든 뒤 캡처한다. 원본은 수정하지 마라.
- 헤드리스 창은 500px 보다 좁아지지 않는다. 390 폭은 사본을 `<iframe width=390>` 에 넣어 잰다. "스크롤 없이 들어오는가"는 PNG 가 아니라 스크립트로 `innerHeight` 와 요소 위치를 비교한다.
- 대비비·재계산 시간은 스크립트(`getComputedStyle`·`performance.now`)로 계산해 값을 보고한다. 렌더 도구가 없으면 판정문에 명시한다.
- 새로고침 뒤 상태는 CDP `Page.reload` 후 같은 셀 값을 다시 읽어 비교한다.

체크리스트 — 전 항목 Yes 여야 통과:

- [ ] 앞서기: Google Sheets에는 없는 수식 추적(선택한 셀이 참조하는 셀과 그 셀을 참조하는 셀을 격자 위에 서로 다른 색의 화살표·테두리로 동시에 표시, 2단계 이상 연쇄 포함)이 있고, CDP 실입력으로 수식 셀을 선택한 상태의 캡처와 `Runtime.evaluate` 로 읽은 표시 대상 셀 목록이 실제 참조 관계와 일치하는 것으로 확인되는가
- [ ] 기본기: 주제만 들은 사용자가 설명 없이 기대할 동작(타이핑으로 바로 입력·Enter/Tab/화살표 이동·더블클릭 또는 F2 편집·Esc 취소 / `=SUM(A1:A3)`·사칙연산·셀 참조 수식과 참조 셀 수정 시 재계산 / Ctrl+C·Ctrl+V 로 범위 복사, 외부 TSV 붙여넣기 / Ctrl+Z·Ctrl+Y 실행 취소·다시 실행 / 새로고침 뒤 데이터 유지 — 하한)이 실제로 써 봐서 전부 되고, 콜드 패스의 기본기 누락이 0건인가
- [ ] 순환 참조(`A1=B1`, `B1=A1`)·0 나누기·없는 함수·잘못된 참조가 각각 셀에 구분되는 오류값(`#CIRC!`·`#DIV/0!`·`#NAME?`·`#REF!` 등)으로 표시되고, 그동안 콘솔 예외가 0건이며 다른 셀 편집이 계속 되는가
- [ ] 1,000행 × 26열 격자에서 참조 체인 100단계(`A2=A1+1` … `A101=A100+1`)의 A1 을 바꿨을 때 A101 반영까지 `performance.now` 로 잰 시간이 100ms 이하이고, 끝 행(1000행)까지 스크롤해도 DOM 셀 요소 수가 1,000개 이하(가상 스크롤)인가
- [ ] 텍스트 색 3쌍(셀 본문/셀 배경, 머리글 텍스트/머리글 배경, 오류값/셀 배경)의 대비비가 모두 4.5:1 이상이고, 390 폭 iframe 에서 수식 바와 A1 셀이 가로 스크롤 없이 보이는가

판정문 `verdicts/round-N.md` 형식:

- 항목별 **pass/fail 과 근거**(측정값·라인 번호·종료 코드).
- **수용된 제약**: 과제 전제상 원리적으로 해결 불가능한 지적은 실패가 아니라 여기에 적는다. 실패로 세면 정체 감지가 잘못 발동한다.
- 남은 격차가 **요구사항 자체에서 강제된 것인지** 한 문단.
- 점수는 보조 신호다. 항목별 판정과 근거가 1차 결론이다.

## 종료 조건

체크리스트 전 항목 Yes (점수 없음) · 최대 2라운드.
미달이면 지적된 항목만 다시 만들어 재검증한다. 2라운드까지 못 닿으면 멈추고 남은 항목과 이유를 보고한다.

검증자의 **판정**은 받아들이되 **처방**은 체크리스트 전체와 대조한다 — 한 항목을 고치며 다른 항목을 깨는 교환은 손해다.
같은 지적이 2라운드 연속 반복되면 접근이 틀린 것이다. 멈추고 보고한다 (수용된 제약은 세지 않는다).

## 완료 후

마지막 판정문과 최종 커밋을 남기고 멈춘다. 미달로 끝나도 결과물을 지우지 말고 남은 항목과 이유를 판정문에 적는다.
