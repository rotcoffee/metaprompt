<!-- metaprompt route=creative tier=lite domain=product mode=greenfield baseline="Google Calendar 웹 주간 뷰" generated=2026-09-30
     regenerate: /metaprompt "업무용 캘린더 UI, 단일 HTML 파일" --route creative --tier lite --profile product --mode greenfield --from ./prompt.md --out ./prompt.md -->

# 목표

업무용 캘린더 UI 를 `index.html` 한 파일로 만들어줘. **Google Calendar 웹 주간 뷰** 를 넘어서는 수준이어야 한다.
제약: HTML·CSS·JS 를 한 파일에 인라인, 외부 CDN·폰트·빌드 도구 없음(node 없음). 데이터는 시드 JSON + `localStorage`. 검증은 `google-chrome` 헤드리스와 `python3` 표준 라이브러리만으로 한다.

"동작하는 수준"이 아니라 "Google Calendar 웹 주간 뷰와 나란히 놓아도 밀리지 않고, 겹치는 회의를 요일 헤더에서 바로 보여 주는 점에서는 앞서는 수준"이 목표다.
실패의 정의: FullCalendar 기본 `timeGridWeek` 템플릿(회색 격자 + 파란 일정 칩)과 구분되지 않으면 실패다.

## 기준점 상세

- Google Calendar 웹은 일/주/월/연/일정 목록 뷰를 두고, 키보드 단축키 `d`·`w`·`m`(뷰 전환), `t`(오늘), `j`/`k`(이전/다음), `c`(새 일정)를 제공한다.
- Google Calendar 주간 뷰는 현재 시각을 빨간 가로선으로 표시하고, 빈 칸을 드래그하면 기본 15분 단위로 새 일정 범위를 잡는다 (15분 단위는 출처 미확인).
- Google Calendar 는 겹치는 일정을 같은 열 안에서 폭을 나눠 나란히 그리지만, 겹침 자체를 경고·집계하지는 않는다 (출처 미확인).
- Notion Calendar(구 Cron)는 `Cmd/Ctrl+K` 명령 메뉴와 키보드 우선 조작, 여러 시간대 열을 나란히 표시하는 기능을 내세운다.
- Google Calendar 는 보조 시간대를 1개까지만 격자 옆에 표시한다 (출처 미확인).

## 실행 예산 (route: creative · tier: lite)

- 메인 세션 effort **medium** — `claude --effort medium` 로 시작한다 (도중에는 `/effort medium`). xhigh·max 는 이득을 실측하지 않았으면 쓰지 않는다.
- 라운드 상한 **2**. 팬아웃 없음 — 빌더는 메인 세션 하나다. 혼자 끝낼 수 있는 일을 위임하지 마라.
- 역할 — effort 는 에이전트 정의 frontmatter 로만 지정된다 (Agent 호출에는 effort 가 없다). 세션 **시작 전에** `python3 <metaprompt>/scripts/agents.py <이 파일>` 이 아래 표로 `.claude/agents/mp-*.md` 를 만든다. 정의가 로드되지 않았으면 호출에 model 만 지정하고, effort 가 세션값을 상속했다고 판정문에 적는다.

  | 역할 | 정의 | model | effort | 맡는 일 |
  |---|---|---|---|---|
  | 메인 세션 (오케스트레이터·빌더) | — | 세션 모델 | medium | `index.html` 전체 구현, 라운드 진행, 커밋 |
  | 검증자 | mp-verifier | opus | high | 매 라운드 새 컨텍스트로 렌더·주입 스크립트 증거를 얻어 체크리스트 판정 |

- 기능 스위치:
  - agent teams **OFF** — lite 이고 산출물이 한 파일이라 조율할 독립 흐름이 없다.
  - Workflow **OFF** — 증거 실행이 캡처 2장 + 스크립트 2개로 5개 미만이다.
  - 루프 **내부 라운드 (/goal·/loop OFF)** — 판정이 검증자의 렌더 판독이라 `/goal` 의 Haiku 평가자가 대신할 수 없고, 외부 대기도 없다.
- 턴 종료 규약: 텍스트만 있는 턴 종료는 완료가 아니다. 종료 조건 미달이고 라운드 상한 전이면 남은 체크리스트 항목을 다시 적고 이어 간다. 사람 입력 없는 자동 재개는 연속 2회까지 — 그 뒤엔 멈추고 남은 항목을 보고한다.
- 서브에이전트 보고는 **30줄 이내**. 코드·로그·스크린샷 전체를 부모 컨텍스트로 올리지 말고 파일 경로와 결론만.
- 판정문은 `verdicts/round-N.md`. 다음 라운드에는 **실패 항목만** 넘기고, 통과 항목의 근거는 다시 읽지 않는다.
- 라운드마다 커밋한다 (`round N: <한 줄 요약>`).
- 검증 증거 범위: 캡처 2장(1440x900 주간 뷰 기본 · 390 폭 좁은 화면) + 텍스트 색 3쌍 대비 계산 + 키보드 생성 주입 스크립트 1개.

## 사전조건 (검증 도구)

라운드 0 에서 확인한다. 사용자 공간 설치(pip·바이너리)는 직접 하고, 시스템 수준(드라이버·apt·docker)이면 **멈추고 사용자에게 요청**한다. 도구 없이 상상으로 채점하지 마라.

| 도구 | 확인 | 없을 때 |
|---|---|---|
| google-chrome (헤드리스 캡처·DOM 덤프) | `google-chrome --version` | 사용자에게 설치 요청 (apt — 직접 하지 않는다). 대체: `uv run --with playwright python -m playwright install chromium` |
| python3 (대비비 계산·로컬 서버) | `python3 --version` | 사용자에게 요청 |
| git (라운드 커밋) | `git --version` | 사용자에게 요청 |

## 순차로 진행할 것 (쪼개지 마)

아래 전부를 메인 세션이 순서대로 처리한다. 이 티어는 이음매를 다시 붙일 예산이 없다.
작업 순서: ① 컬러 토큰(CSS 변수)·타이포·스페이싱 → ② 시드 데이터(이번 주 일정 15개 이상, 겹치는 쌍 2개 이상 포함) → ③ 시간 격자 좌표계와 일정 배치(겹침 열 분할 포함) → ④ 요일 헤더 충돌 배지 → ⑤ 뷰 전환·키보드 단축키·생성 폼 → ⑥ `localStorage` 저장 → ⑦ 좁은 폭 레이아웃.
시간 격자 좌표계·일정 배치·충돌 계산·생성/저장 경로는 한 에이전트가 처음부터 끝까지 맡아.
이유: 모두 같은 일정 배열과 "분 → 픽셀" 좌표 변환에 같이 쓴다. 쪼개면 부분별로는 그럴싸해도 이음매에서 버그가 난다.

## 검증

만드는 에이전트와 **별개의** 검증을 둔다. 자기가 만든 걸 자기가 채점하지 마.
`mp-verifier` 를 매 라운드 새 컨텍스트로 띄운다. 판정은 아래 커맨드로 얻은 증거만.
보고 범위는 **아래 체크리스트 항목과 정확성 결함으로 한정**한다 — 새 컨텍스트 리뷰어는 결과가 멀쩡해도 뭔가를 보고하는 경향이 있다. 취향 지적은 판정에 넣지 않는다. 근거 없는 pass 는 무효다.

**직접 증거를 확보한 뒤 판정해라. 추정하지 마라.**

검증자는 결과물을 **실제로 렌더링해서 픽셀을 보고** 판정해라. CSS 를 읽고 화면을 상상하지 마라. 원본 `index.html` 은 수정하지 말고, 상태를 바꿀 때는 `verify/` 아래 **사본**에 스크립트를 주입한다.

```bash
mkdir -p verify verdicts
P="$(pwd)"

  # 캡처 1 — 기본 주간 뷰 (--window-size 1440x987 → 실제 뷰포트 1440x900)
google-chrome --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
  --virtual-time-budget=5000 --window-size=1440,987 \
  --screenshot="$P/verify/week-1440.png" "file://$P/index.html"

  # 캡처 2 — 좁은 폭 (390x844 뷰포트)
google-chrome --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
  --virtual-time-budget=5000 --window-size=390,931 \
  --screenshot="$P/verify/narrow-390.png" "file://$P/index.html"

  # 가로 넘침 수치 — 사본에 측정 스크립트 주입 후 DOM 덤프
python3 - <<'EOF'
src = open("index.html", encoding="utf-8").read()
probe = """<script>addEventListener('load',()=>setTimeout(()=>{
document.body.setAttribute('data-probe', JSON.stringify({sw:document.documentElement.scrollWidth, iw:innerWidth}));},500));</script>"""
open("verify/probe-width.html","w",encoding="utf-8").write(src.replace("</body>", probe+"</body>"))
EOF
google-chrome --headless=new --disable-gpu --no-sandbox --virtual-time-budget=5000 \
  --window-size=390,931 --dump-dom "file://$P/verify/probe-width.html" | grep -o 'data-probe="[^"]*"'

  # 키보드만으로 생성 + 저장 — 사본에 keydown 주입, 결과를 DOM 에 기록
python3 - <<'EOF'
src = open("index.html", encoding="utf-8").read()
probe = """<script>addEventListener('load',()=>setTimeout(async()=>{
const k=(key,t=document.activeElement||document.body)=>t.dispatchEvent(new KeyboardEvent('keydown',{key,bubbles:true}));
k('c'); await new Promise(r=>setTimeout(r,300));
const el=document.activeElement; el.value='PROBE-회의'; el.dispatchEvent(new Event('input',{bubbles:true}));
k('Enter',el); await new Promise(r=>setTimeout(r,300));
const inDom=[...document.querySelectorAll('*')].some(n=>n.children.length===0&&n.textContent.includes('PROBE-회의'));
const inLS=Object.keys(localStorage).some(x=>localStorage.getItem(x).includes('PROBE-회의'));
document.body.setAttribute('data-probe', JSON.stringify({inDom,inLS,focused:el.tagName}));},500));</script>"""
open("verify/probe-kbd.html","w",encoding="utf-8").write(src.replace("</body>", probe+"</body>"))
EOF
google-chrome --headless=new --disable-gpu --no-sandbox --virtual-time-budget=8000 \
  --window-size=1440,987 --dump-dom "file://$P/verify/probe-kbd.html" | grep -o 'data-probe="[^"]*"'
```

대비비는 `index.html` 의 CSS 변수에서 실제 색을 읽어 계산하고 값을 판정문에 적는다 (3쌍: 일정 칩 텍스트/칩 배경 · 시간 라벨/격자 배경 · 충돌 배지 텍스트/배지 배경):

```bash
python3 - <<'EOF'
def lum(h):
    h=h.lstrip('#'); c=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    c=[x/12.92 if x<=0.03928 else ((x+0.055)/1.055)**2.4 for x in c]
    return 0.2126*c[0]+0.7152*c[1]+0.0722*c[2]
def ratio(a,b):
    la,lb=sorted([lum(a),lum(b)],reverse=True); return (la+0.05)/(lb+0.05)
PAIRS=[("#FG1","#BG1"),("#FG2","#BG2"),("#FG3","#BG3")]  # index.html 에서 읽은 실제 값으로 바꿔 넣는다
for f,b in PAIRS: print(f,b,round(ratio(f,b),2))
EOF
```

렌더 도구가 없으면 판정문에 명시하고 해당 항목은 fail 로 둔다.

체크리스트 — 전 항목 Yes 여야 통과:

- [ ] 앞서기: Google Calendar 웹 주간 뷰에는 없는 **요일 헤더의 충돌 개수 배지(겹치는 일정 쌍 수)와 겹친 일정의 구분 표시**가 있고, `verify/week-1440.png` 에서 시드의 겹침 2쌍 이상이 배지 숫자와 일치하게 보이는 것으로 확인되는가
- [ ] `verify/week-1440.png`(뷰포트 1440x900)에서 5개 평일 열과 09:00–18:00 이 세로 스크롤 없이 한 화면에 들어오고, 30분 이상 일정의 제목이 한 줄 이상 잘림 없이 읽히는가
- [ ] 키보드 생성 주입 결과가 `inDom:true` 이고 `inLS:true` 인가 (`c` → 제목 입력 → `Enter`, 마우스 없이)
- [ ] 텍스트 색 3쌍의 대비비가 전부 4.5:1 이상인가 (위 스크립트 출력값)
- [ ] 390 폭에서 `sw <= iw` (가로 넘침 없음)이고, `verify/narrow-390.png` 에서 일/3일 뷰로 바뀌어 일정 제목이 읽히는가

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
