# chat vs lite 채점 — 업무용 캘린더 UI (단일 HTML)

채점자: 제3 에이전트, 두 결과물 생성에 관여하지 않음. (lite 쪽 builder-verdict-round-1.md 는 읽지 않았다.)

- chat = `bench/chat-vs-lite/chat-out/calendar.html`
- lite = `bench/chat-vs-lite/lite-out/index.html`
- 기준: `lite-prompt.md` 의 "## 검증" 절 커맨드와 "체크리스트 — 전 항목" 5개. 두 파일에 같은 절차를 적용했다.
- 작업 위치: 스크래치 `grade/{chat,lite}/index.html`(원본 사본). 모든 주입은 사본의 `verify/` 아래에서만 했다. Chrome 154.0.8037.57 `--headless=new`, Python 3.12.3.

## 사용한 커맨드

1. `run.sh <dir>` — `lite-prompt.md` "## 검증" 블록을 그대로 옮겼다(경로만 `<dir>` 기준으로 바꿈).
   - 캡처 2장: `--window-size=1440,987` → `week-1440.png`, `--window-size=390,931` → `narrow-390.png`.
   - 폭 프로브: `probe-width.html` 을 `--dump-dom` 으로 떠서 `{sw, iw}` 를 읽는다.
   - 키보드 프로브: `probe-kbd.html` 에 `c` → 제목 입력 → `Enter` 를 주입하고 `{inDom, inLS, focused}` 를 읽는다.
2. `contrast.py` — 프롬프트의 `lum/ratio` 함수를 그대로 쓰고 PAIRS 만 각 파일 CSS 에서 읽은 값으로 채웠다. `color-mix(in srgb, c 16%, white)` 는 sRGB 선형 혼합으로 계산했다. 칩 변형이 여럿이면 전부 계산하고 최솟값으로 판정했다.
3. 보조 측정(두 파일에 똑같이 적용). 절차 자체의 결함 3가지 때문에 추가했다.
   - (a) 이 Chrome 에서는 `--window-size=1440,987` 이 뷰포트 1440x**987** 로 찍힌다(PNG 1440x987). 그래서 `--window-size=1440,900` 으로 `week-1440x900.png` 를 따로 떴다.
   - (b) `--dump-dom` 모드는 창 최소폭 때문에 390 을 줘도 `iw=500` 이 된다. 그래서 `iframe390.sh` 로 390x844 iframe 안에서 잰 `{sw, iw}` 를 postMessage 로 받았다.
   - (c) 원 키보드 프로브의 `inDom` 은 주입한 `<script>` 자신의 텍스트('PROBE-회의')에도 걸려 **항상 true** 가 된다. 그래서 `kbd2.sh` 로 `body *:not(script)` 만 검사하는 보정 프로브를 돌렸다.
4. 참고용(점수 제외, "다른 방식" 메모 근거): chat 사본에 대해서만 돌렸다.
   - `w`/`d` 키를 주입해 `alt-week-1440.png`, `alt-day-390.png` 를 떴다.
   - `n` → 제목 입력 → `form.requestSubmit()` 프로브를 돌렸다. `requestSubmit()` 은 실제 Enter 키의 암묵적 제출과 같은 동작이다.

## 원시 결과

| 측정 | chat | lite |
|---|---|---|
| 폭 프로브 (절차 원본, dump-dom) | `{sw:500, iw:500}` | `{sw:500, iw:500}` |
| 폭 프로브 (보조 b, 390 iframe) | `{sw:390, iw:390}` | `{sw:390, iw:390}` |
| 키보드 프로브 (절차 원본) | `{inDom:true, inLS:false, focused:BODY}` | `{inDom:true, inLS:true, focused:INPUT}` |
| 키보드 프로브 (보정 c, script 제외) | `{inDom:false, inLS:false, focused:BODY}` | `{inDom:true, inLS:true, focused:INPUT}` |
| 대비 — 칩 텍스트/칩 배경 (최솟값) | **2.15** (종일 칩 `#fff`/`#f59e0b`). 주간 칩 `#111`/틴트는 15.28–16.65, 월뷰 시각 `#6b7280`/`#fff` 는 4.83 | **10.06** (`#592804`/`#fde6cf`). 겹침 빗금 줄무늬 위 최악값도 8.6 |
| 대비 — 시간 라벨/격자 배경 | 4.83 (`#6b7280`/`#ffffff`) | 8.67 (`#4f4a3f`/`#fffdf8`). 보조 시간대 `.alt` 는 5.7 |
| 대비 — 충돌 배지 텍스트/배지 배경 | 해당 요소 없음 (`badge`·`conflict` grep 0건) | 6.57 (`#ffffff`/`#b42318`) |

## 판정표

| # | 항목 | chat | lite |
|---|---|---|---|
| 1 | 요일 헤더 충돌 개수 배지 + 겹친 일정 구분 표시. 시드 겹침 2쌍 이상이 배지 숫자와 일치 | **fail**. `chat-week-1440.png` 의 기본 화면은 **월 보기**이고 요일 헤더에 배지가 없다. 겹침을 경고하거나 세는 요소가 코드에 없다(grep 0건). | **pass**. `lite-week-1440.png` 의 헤더 배지는 월 1 · 화 없음 · 수 2 · 목 없음 · 금 1, 합계 4. 사이드바 "겹치는 일정 4쌍" 목록(9/28 1건, 9/30 2건, 10/2 1건)과 맞는다. 겹친 칩에는 빨간 테두리, 빗금, `!` 표시가 있다. |
| 2 | 1440x900 에서 평일 5열과 09:00–18:00 이 스크롤 없이 한 화면에 들어오고, 30분 이상 일정 제목이 잘림 없이 읽힘 | **fail**. 기본 캡처(`chat-week-1440.png`)가 월 보기라 시간 격자가 없다. | **pass**. `lite-week-1440x900.png` 에 월–금 5열이 보이고, 09:00 은 y≈129, 18:00 은 y≈786 으로 900 안에 들어간다. 30분 이상 제목은 모두 온전히 보인다('아키텍처 리뷰' 는 2줄로 줄바꿈되지만 잘리지 않음). 줄임표는 메타(시간·장소) 줄에만 있다. |
| 3 | 키보드만으로 생성 (`c` → 제목 → `Enter`) 결과 `inDom:true` 이고 `inLS:true` | **fail**. 원 프로브 `inLS:false`, `focused:BODY`. 보정 프로브는 `inDom:false`. `c` 키는 바인딩되어 있지 않다. | **pass**. 원 프로브와 보정 프로브 모두 `{inDom:true, inLS:true, focused:INPUT}`. |
| 4 | 텍스트 색 3쌍 대비비 전부 4.5:1 이상 | **fail**. 칩 최솟값 2.15(종일 칩; `chat-week-1440.png` 의 '부산 출장'). 충돌 배지 쌍이 없다. 시간 라벨은 4.83 으로 통과. | **pass**. 10.06 / 8.67 / 6.57. |
| 5 | 390 폭에서 `sw <= iw` 이고, `narrow-390.png` 에서 일/3일 뷰로 바뀌어 일정 제목이 읽힘 | **fail**. `sw <= iw` 는 성립(500/500, iframe 390/390). 그러나 `chat-narrow-390.png` 는 월 보기 그대로이고 칩에 시각('09:30' 등)만 보이며 제목은 보이지 않는다. | **pass**. `sw <= iw` 성립(500/500, iframe 390/390). `lite-narrow-390.png` 가 **일** 보기로 자동 전환되고 '채용 인터뷰', '제품 리뷰', '보안 점검' 등 제목이 읽힌다. 헤더에 '겹침 2' 칩도 보인다. |

## chat 이 같은 목적을 다른 방식으로 달성했는지 (점수 제외)

1. **부분 달성.** `w` 로 들어간 주간 보기(`chat-alt-week-1440.png`)는 겹친 일정을 열로 나눠 나란히 그린다(9/30 분기 보고서 · 코드 리뷰 · 점심 미팅). 기준점인 Google Calendar 와 같은 방식이다. 겹침을 경고하거나 세는 기능은 없어서 기준점을 "앞서는" 목적은 달성하지 못했다.
2. **부분 달성.** 기본 화면을 월 보기(개요 우선)로 정한 것이 다른 선택이다. `w` 주간 보기에는 7일 열과 09:00–18:00 이 한 화면에 들어온다(48px/시간). 다만 '분기 보고…' 처럼 좁아진 열에서 제목이 줄임표로 잘린다.
3. **달성(다른 키).** 생성 키가 `c` 가 아니라 `n` 이다. `n` 을 누르면 제목 INPUT 에 포커스가 가고, 네이티브 폼 제출(Enter)로 저장된다. `n` + `requestSubmit()` 프로브 결과는 `{inDom:true, inLS:true, focused:INPUT}` 이다. 원 프로브의 합성 `keydown Enter` 는 암묵적 폼 제출을 일으키지 않으므로, JS 로 Enter 를 처리하는 설계에만 맞는 측정이다.
4. **부분 달성.** 주간 칩(15.28 이상)과 월뷰 시간 일정 텍스트(14.68)는 기준을 크게 넘는다. 하지만 종일 칩은 흰 글자에 채도 높은 카테고리 색을 써서 2.15–4.83 이고, 6색 중 5색이 4.5 미만이다. 충돌 배지는 없다.
5. **부분 달성.** 390 에서 가로 넘침은 없다. `d` 를 눌러 수동으로 일 보기에 들어가면(`chat-alt-day-390.png`) '코드 리뷰', '점심 미팅' 제목이 읽힌다. 그러나 폭에 따른 자동 전환은 없다. 헤더 제목은 글자 단위로 줄바꿈되고, 월/주/일 세그먼트 버튼이 잘려 보인다.

## 캡처 (bench/chat-vs-lite/grade-shots/)

- chat
  - `chat-week-1440.png`: 기본, 1440x987
  - `chat-narrow-390.png`
  - `chat-alt-week-1440.png`: 참고, `w` 주입
  - `chat-alt-day-390.png`: 참고, `d` 주입
- lite
  - `lite-week-1440.png`: 기본, 1440x987
  - `lite-week-1440x900.png`: 보조 a
  - `lite-narrow-390.png`

모두 170KB 이하.

SCORE chat=0/5 lite=5/5
