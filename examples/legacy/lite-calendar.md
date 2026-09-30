<!-- 스모크 테스트 산출물 (2026-09-28, --yes 자동 경로). 스킬이 로드하지 않는다. 형식·품질 참고용. -->
<!-- metaprompt tier=lite domain=product mode=greenfield baseline="Google Calendar 웹" generated=2026-09-28
     regenerate: /metaprompt "업무용 캘린더 UI, 단일 HTML 파일" --tier lite --profile product --mode greenfield --from prompts/metaprompt-lite-calendar.md --out prompts/metaprompt-lite-calendar.md -->

# 목표

`calendar.html` 파일 하나로 동작하는 업무용 캘린더 UI 를 만들어줘. **Google Calendar 웹** 수준이어야 한다.
빌드 단계 없음(이 환경에 node 없음) · 외부 CDN·웹폰트·네트워크 요청 0 · `file://` 로 열어도 동작 · 샘플 일정 2주치를 파일 안에 내장 · `?now=YYYY-MM-DDTHH:mm` 쿼리로 시계를 고정할 수 있어야 한다 (검증 재현용) · 390px 폭에서 가로 스크롤 없음.

"동작하는 수준"이 아니라 "Google Calendar 웹과 나란히 놓고 비교해도 밀리지 않는 수준"이 목표다.
날짜 표 위에 색 칩만 얹은 것, 즉 "폰트만 다른 기본 캘린더" 면 실패다 (출처 미확인).

## 기준점 상세

- 뷰는 Day / Week / Month / Year / Schedule / 4 days 여섯 가지이고 우측 상단 드롭다운으로 전환한다 — 출처: https://support.google.com/calendar/answer/6110849
- 키보드 단축키: `c` 일정 생성 · `/` 검색 · `t` 오늘로 이동 · `d` 일간 뷰 · `a` 일정 목록 뷰 · `?` 로 단축키 목록 표시 — 출처: https://support.google.com/calendar/answer/37034. `w` 주간 · `m` 월간 · `j`/`k` 다음·이전 기간 (출처 미확인)
- 밀도 설정 "Responsive to your screen" 이 있다 — 출처: https://support.google.com/calendar/thread/429461132. 대안 "Compact" 옵션이 있고, 주간 뷰의 시간당 행 높이는 약 48px, 초기 스크롤 위치는 아침 업무 시작 근처라 08:00~18:00 업무 시간대가 한 화면에 들어온다 (출처 미확인)
- 오늘 열에는 빨간 수평선 + 왼쪽 끝 점으로 현재 시각을 표시하고, 오늘 날짜 헤더는 파란 채움 원으로 강조한다 (출처 미확인)
- 같은 시간대에 겹치는 일정은 위아래로 쌓지 않고 같은 열 안에서 좌우로 분할 배치한다. n 개 겹치면 폭을 n 등분하고, 늦게 시작하는 일정이 살짝 겹쳐 올라온다 (출처 미확인)
- 상단에 종일 일정 행이 따로 있고 좌측에 시간 거터가 있으며, 지난 일정은 불투명도를 낮춰 흐리게 표시한다 (출처 미확인). 사용자가 좋다고 말하는 이유: "빠르고, 키보드로 다 되고, 캘린더별 색으로 회사·개인 일정이 한눈에 갈린다" (출처 미확인)

미학 상충 메모: 기준점의 일정 칩은 채도 높은 배경 + 흰 글자다 (예: Peacock #039BE5 위 흰 글자 ≈ 3.0:1, 출처 미확인). 이 방식은 아래 체크리스트 4번(칩 텍스트 4.5:1)을 못 넘는다. 그래서 칩은 **연한 틴트 배경 + 같은 색상의 진한 글자** 방식으로 고정한다. 배경 채도를 올려 기준점을 흉내내다 4번을 깨지 마라.

## 실행 예산 (tier: lite)

- 라운드 상한 **2**. 팬아웃 없음 — 빌더 하나, 검증자 하나.
- 서브에이전트 보고는 **30줄 이내**로 받아라. 코드·로그·스크린샷 전체를 부모 컨텍스트로 올리지 마라.
  상세는 파일에 두고 경로와 결론만 보고한다. 컨텍스트가 길어질수록 뒤 라운드의 판단이 흐려진다.
- 검증자 판정문은 `verdicts/round-N.md` 에 저장한다. 다음 라운드 작업 지시는 **실패 항목만** 추려서 넘긴다.
  통과 항목의 근거는 다시 읽지 않는다.
- 라운드마다 커밋한다 (`round N: <한 줄 요약>`). 커밋이 없으면 중간 상태 복원도, 개선 전후 비교도 못 한다.
- 검증 증거 범위: 캡처 2장 (주간 뷰 라이트 1440x987 · 좁은 폭 390x931, 둘 다 `?now=2026-09-30T14:30`) + 텍스트 색 3쌍 대비 계산 + 측정 스크립트 주입 1회 (`--dump-dom`)

## 사전조건 (검증 도구)

라운드 0 에서 아래를 확인한다. 없으면 사용자 공간 설치는 직접 하고, 시스템 수준이면 **멈추고 사용자에게 설치를 요청**한다. 도구 없이 상상으로 채점하지 마라.

| 도구 | 확인 | 없을 때 |
|---|---|---|
| 헤드리스 브라우저 (google-chrome, 생성 시 확인됨) | `google-chrome --version` | `pip install playwright && python3 -m playwright install chromium` 또는 firefox 헤드리스 |
| python3 (대비 계산) | `python3 --version` | 시스템 수준 — 멈추고 요청 |

## 순차로 진행할 것 (쪼개지 마)

아래 전부를 빌더 하나가 순서대로 처리한다. 병렬화하지 마라 — 이 티어는 이음매를 다시 붙일 예산이 없다.
캘린더 코어(시간→픽셀 좌표계 · 주간 그리드 · 겹침 배치 · 현재 시각 선 · 뷰 전환 · 키보드 핸들러 · 390px 축소)는 한 에이전트가 처음부터 끝까지 맡아.
이유: 전부 하나의 상태 `{view, selectedDate, events[]}` 와 하나의 그리드 좌표계(시간당 행 높이 · 열 폭 · 거터 폭)에 같이 쓰기를 한다. 겹침 배치가 정한 칩 좌표 위에 현재 시각 선이 얹히고, 뷰 전환이 그 좌표계를 통째로 바꾼다.
여기를 병렬로 쪼개면 부분별로는 그럴싸해 보여도 이음매에서 버그가 난다.

빌더의 작업 순서 (팔레트·타이포를 먼저 정하고 코어를 짠다):

1. 디자인 토큰을 CSS 변수로 먼저 고정 — 배경/본문 텍스트/보조 텍스트/선 색, 캘린더 색 4종(각각 틴트 배경 + 진한 글자 쌍), 시간당 행 높이(48px 권장), 거터 폭, 글자 크기(칩 제목 12px 이상). 이 값들이 이후 모든 계산의 입력이다.
2. 데이터 모델과 샘플 데이터 — `?now=` 기준일 앞뒤 2주, 캘린더 4종(회의·개인·마감·휴가), 종일 일정 2개, **기준일 14:00–15:00 에 겹치는 일정 2개**, 30분짜리 일정 3개 이상, 지난 일정 포함. `?now=` 가 없으면 실제 시각.
3. 시간→픽셀 좌표계 함수 하나 (`minutesToY`, `yToMinutes`). 이후 그리드·칩·현재 시각 선이 전부 이 함수만 쓴다.
4. 주간 뷰 — 좌측 시간 거터, 상단 요일 헤더(오늘은 채움 원 강조), 종일 행, 24시간 그리드. 초기 스크롤은 08:00 이 상단에 오게 해서 18:00 까지 1440x900 뷰포트 안에 들어오게 한다. 지난 일정은 흐리되 대비 3:1 이상 유지.
5. 겹침 배치 — 같은 열에서 시간이 겹치는 일정을 좌우 분할. 2개면 각각 열 폭의 50% 이상, n 개면 n 등분. 위아래 스택 금지.
6. 현재 시각 선 — `?now=` 의 날짜 열에만, 빨간 수평선 + 좌측 점. 위치는 3번 함수로 계산.
7. 뷰 전환 — 일간(d) · 주간(w) · 월간(m). 전환 후에도 `selectedDate` 가 표시 범위 안에 남아야 한다. 이전/다음 기간(j/k 또는 버튼), 오늘(t).
8. 키보드 — `t d w m c ?` 와 `j/k`. `c` 는 생성 폼(제목·날짜·시작·종료·캘린더 색)을 열고 저장하면 메모리의 `events[]` 에 추가되어 즉시 그려진다. `?` 는 단축키 목록 오버레이.
9. 390px 폭 — 주간 뷰 대신 일간 뷰로 떨어지고 가로 스크롤이 없어야 한다. 거터·칩이 겹치지 않게.
10. 검증 훅 (필수, 이게 없으면 검증자가 측정을 못 한다): `window.__cal = {view, selectedDate: 'YYYY-MM-DD', visibleRange: ['YYYY-MM-DD','YYYY-MM-DD']}` 를 항상 최신으로 유지 · 시간 그리드의 각 시간 행에 `data-hour="0..23"` · 현재 시각 선에 `data-now-line` · 생성 폼 루트에 `data-create-form`.

## 검증

만드는 에이전트와 **별개의** 검증 에이전트를 둬. 자기가 만든 걸 자기가 채점하지 마.
검증자는 아주 가혹한 비평가여야 하고, 기본 태도는 거부다.

**검증자는 다음 방법으로 직접 증거를 확보한 뒤 판정해라. 추정하지 마라.**

검증자는 결과물을 **실제로 렌더링해서 픽셀을 보고** 판정해라. CSS를 읽고 화면을 재구성하지 마라.

    mkdir -p verdicts
    google-chrome --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
      --virtual-time-budget=5000 --window-size=1440,987 \
      --screenshot=verdicts/round-N-week.png "file://$PWD/calendar.html?now=2026-09-30T14:30"
    google-chrome --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
      --virtual-time-budget=5000 --window-size=390,931 \
      --screenshot=verdicts/round-N-narrow.png "file://$PWD/calendar.html?now=2026-09-30T14:30"

- `--window-size` 높이에서 약 87px 뺀 값이 실제 뷰포트다 (1440x987 → 1440x900, 390x931 → 390x844). 모르면 캡처 하단 여백을 레이아웃 버그로 오인한다.
- 캡처 세트 (lite): 2장 — 주간 뷰 라이트 1440x987, 좁은 폭 390x931. 대비는 텍스트 색 3쌍만 계산한다.
- 다른 상태(키 입력 후 뷰)와 좌표 측정값은 **원본 사본** `verdicts/probe.html` 의 `</body>` 앞에 스크립트를 주입해 만든 뒤 `--dump-dom` 으로 읽는다. 원본 `calendar.html` 은 수정하지 마라.

      cp calendar.html verdicts/probe.html
      # verdicts/probe.html 의 </body> 앞에 아래를 삽입한다
      <script>
        const m = {};
        const line = document.querySelector('[data-now-line]');
        const h14 = document.querySelector('[data-hour="14"]');
        m.nowLineCount = document.querySelectorAll('[data-now-line]').length;
        m.lineY = line ? line.getBoundingClientRect().top + window.scrollY : null;
        m.h14Top = h14 ? h14.getBoundingClientRect().top + window.scrollY : null;
        m.h14H = h14 ? h14.getBoundingClientRect().height : null;
        m.scrollWidth = document.documentElement.scrollWidth;
        m.before = JSON.parse(JSON.stringify(window.__cal));
        m.after = {};
        for (const k of ['d','w','m']) {
          document.dispatchEvent(new KeyboardEvent('keydown', {key: k, bubbles: true}));
          m.after[k] = JSON.parse(JSON.stringify(window.__cal));
        }
        document.dispatchEvent(new KeyboardEvent('keydown', {key: 'c', bubbles: true}));
        m.createFormOpen = !!document.querySelector('[data-create-form]');
        document.dispatchEvent(new KeyboardEvent('keydown', {key: 't', bubbles: true}));
        m.afterT = JSON.parse(JSON.stringify(window.__cal));
        const pre = document.createElement('pre'); pre.id = '__m'; pre.textContent = JSON.stringify(m);
        document.body.appendChild(pre);
      </script>
      google-chrome --headless=new --disable-gpu --no-sandbox --virtual-time-budget=5000 \
        --dump-dom "file://$PWD/verdicts/probe.html?now=2026-09-30T14:30" | grep -o '<pre id="__m">[^<]*'

  항목 3 의 기대 y 는 `h14Top + h14H * 0.5` 다 (14:30). 항목 5 의 `visibleRange` 포함 여부는 `after.m` 값으로 본다. 390px 의 가로 스크롤은 같은 주입을 `--window-size=390,931` 로 돌려 `scrollWidth <= 390` 인지 본다.
- 대비비·광도 같은 수치는 추정하지 말고 스크립트로 계산해서 값을 보고해라. `calendar.html` 의 CSS 변수에서 실제 hex 값을 읽어 아래에 넣는다.

      python3 - <<'PY'
      def lum(h):
          r, g, b = [int(h[i:i+2], 16) / 255 for i in (1, 3, 5)]
          f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
          return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
      def ratio(a, b):
          la, lb = sorted([lum(a), lum(b)], reverse=True)
          return (la + 0.05) / (lb + 0.05)
      pairs = [("본문/배경", "#000000", "#ffffff"), ("보조·거터/배경", "#000000", "#ffffff"), ("칩 글자/칩 배경", "#000000", "#ffffff")]  # 실제 값으로 교체
      for name, fg, bg in pairs:
          print(name, fg, bg, round(ratio(fg, bg), 2))
      PY

- 렌더링 도구가 없으면 그 사실을 판정문에 명시하고 진행해라. 조용히 건너뛰지 마라.
- 목표 절의 제약(단일 파일 · 네트워크 요청 0 · `?now=` 동작 · 390px 가로 스크롤 없음)을 어겼으면 체크리스트를 채점하기 전에 그 사실만 적고 fail 로 돌려보낸다. `grep -nE 'https?://|<link|<script src' calendar.html` 로 외부 참조를 확인해라.

체크리스트 — 전 항목 Yes여야 통과:

- [ ] 1. 1440x900 주간 뷰 캡처에서 `data-hour="8"` 행 상단과 `data-hour="18"` 행 상단이 모두 뷰포트 안에 보이고(세로 스크롤 없이), 30분짜리 샘플 일정 칩 안의 제목이 12px 이상 글자로 잘림 없이 1줄 읽히는가
- [ ] 2. 기준일 14:00–15:00 에 겹치는 샘플 일정 2개가 같은 열에서 좌우로 나란히 놓이고(각 칩 폭이 열 폭의 40% 이상, 위아래 스택이면 No) 두 칩 모두 제목 첫 단어가 캡처에서 읽히는가
- [ ] 3. 측정값에서 `nowLineCount == 1` 이고 `lineY` 가 `h14Top + h14H * 0.5` 에서 ±4px 안이며, 캡처에서 그 선이 기준일 열에만 그려져 있는가
- [ ] 4. 라이트 모드 텍스트 색 3쌍 — 본문/배경 · 보조 텍스트(시간 거터)/배경 · 일정 칩 글자/칩 배경 — 의 대비가 python3 계산으로 전부 4.5:1 이상인가
- [ ] 5. 주입한 `d → w → m` 각각에서 `window.__cal.view` 가 `day / week / month` 로 바뀌고 `m` 이후 `selectedDate` 가 `visibleRange` 안에 있으며, `c` 로 `[data-create-form]` 이 열리고 `t` 로 `selectedDate` 가 `?now=` 날짜로 돌아오는가

검증자는 아래 형식으로 `verdicts/round-N.md` 에 남겨라.

- 항목별 **pass/fail 과 근거**(측정값·라인 번호·재현된 수치). 근거 없는 pass 는 무효다.
- **수용된 제약**: 이 과제의 전제상 원리적으로 해결 불가능한 지적은 실패가 아니라 여기에 적어라.
  실패로 집계하면 정체 감지 규칙이 잘못 발동한다.
- 남은 격차가 **요구사항 자체에서 강제된 것인지** 한 문단으로 답해라.
- 점수는 보조 신호다. 항목별 판정과 근거 수치가 1차 결론이다.

## 종료 조건

체크리스트 전 항목 Yes (점수 없음) · 최대 2라운드.
미달이면 지적된 항목만 다시 만들어서 재검증해.
2라운드까지 통과 못 하면 멈추고, 남은 미달 항목과 그 이유를 보고해.

검증자의 **판정**은 받아들이되 **처방**은 체크리스트 전체와 대조해라. 한 항목을 고치려다 다른
항목을 깨는 제안이 나올 수 있다. 통과 조건은 전 항목 Yes이므로 그런 교환은 손해다.

같은 지적이 2라운드 연속 반복되면 접근 방식이 틀린 것이다. 멈추고 보고해.
(수용된 제약으로 분류된 항목은 이 카운트에서 제외한다.)

## 완료 후

마지막 판정문 `verdicts/round-N.md` 와 최종 커밋을 남기고 멈춘다.
미달로 끝나도 결과물을 지우지 마라. 남은 미달 항목과 이유를 판정문에 적는다.
