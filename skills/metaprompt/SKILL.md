---
name: metaprompt
description: "주제 한 줄 → 다른 세션에서 실행할 프롬프트 파일. 작업 성격을 플래그 없이 라우팅한다 — 생성 불필요(한 문장 diff·질문·한 세션 크기)는 파일 없이 돌려보내고, 정밀(버그·마이그레이션·수치 목표)은 먼저 실패하는 회귀 테스트와 종료 코드로, 창의(UI·도구·새 방법)는 실명 기준점을 넘는 앞서기 항목으로 만든다. 역할별 모델·effort 와 agent teams·Workflow·루프 스위치를 이유와 함께 박는다. 티어(lite/standard/max)로 토큰과 품질을 맞바꾼다."
when_to_use: "트리거: 메타프롬프트, metaprompt, 프롬프트 만들어줘, 실행용 프롬프트, 루프 프롬프트, 원샷 프롬프트. 쓰지 않음: 한 문장으로 설명되는 수정, 한 세션이 혼자 끝낼 단일 파일 작업, 단순 질의응답, 코드 리뷰, 탐색 — 이런 주제가 와도 스킬이 판정 한 줄로 채팅에 돌려보낸다."
argument-hint: "<주제> | --check   [--route-only] [--route creative|precise] [--tier lite|standard|max] [--profile product|research|system] [--mode greenfield|worktree] [--yes] [--from <이전 프롬프트>] [--benchmark <기준점>] [--rounds N] [--out <경로>]"
allowed-tools: ["Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/*)", "Read", "Write", "Edit", "Agent", "AskUserQuestion", "WebSearch", "WebFetch"]
effort: medium
---

# metaprompt

주제 한 줄 → **다른 세션에서 실행할 프롬프트 파일 하나**, 또는 "만들 필요 없음" 한 줄. 만든 프롬프트를 실행하지 않는다.
설계 판단이 갈리면 **토큰 대비 품질**로 정한다. 작업 크기와 무관하게 같은 절차를 태우는 것이 이 스킬의 실패다.

입력: `$ARGUMENTS`

## 환경 (로드 시 자동 수집)

```!
python3 ${CLAUDE_SKILL_DIR}/scripts/detect_env.py --skill-dir ${CLAUDE_SKILL_DIR}
```

위 JSON 의 `skill_dir` 을 아래에서 `<skill_dir>` 로 쓴다. JSON 이 아니면 그 커맨드를 직접 실행한다. `--mode` 가 오면 `mode` 를 덮어쓴다.
**`--check` 만 왔으면**: JSON 을 보여주고 `python3 <skill_dir>/scripts/check_prompt.py --self-test` 의 마지막 줄과 `skill_version` 을 한 줄로 보고하고 끝낸다.

## 0. 경로 판정 — 다른 파일을 읽기 전에

위에서부터 처음 걸리는 경로. **크기가 신호보다 먼저다** — skip 에 걸리면 creative·precise 신호가 있어도 skip 이다. 두 경로 신호가 팽팽하면 **가벼운 쪽**(skip < precise < creative)으로 닫는다. `--route` 가 오면 판정 대신 그것.

1. **skip — 만들지 않는다.** 산출물이 답변이다(질문·설명·비교 조사·코드 리뷰·탐색·"어떻게") / 바꿀 위치와 내용이 주제에 이미 있어 **diff 를 한 문장으로 쓸 수 있다**(오타·문구·색·설정값 하나·이름 변경·버전 하나·원인이 적힌 한 줄 수정) / **한 세션이 혼자 끝낼 크기다** — 그린필드이고 산출물이 파일 1~2개(단일 HTML·스크립트·모듈 하나)이며 출시·공개·"○○보다 나은" 신호가 없다. 새 화면이든 명세형이든 같다: 실측 3주제에서 lite 는 채팅 한 번과 같거나, 나아도 채팅에 개선 요청을 한 번 더 한 것과 같은 수준·비용이었다.
2. **precise — 정답이 정해져 있다.** 원인 불명이거나 여러 곳에 걸친 버그 · 마이그레이션·업그레이드 · 동작 불변 리팩터링 · 수치 목표(지연·처리량·용량·정확도) · 보고된 수치 재현 · 기존 방법끼리 어느 쪽이 나은지 측정 · 테스트·CI 정비. 완료를 커맨드가 판정할 수 있다.
3. **creative — 새로 설계하고 비교로 품질이 갈린다.** 화면·앱·게임·도구·API·문서 사이트를 새로 만들거나 다시 디자인 · "○○보다 나은 / ○○ 같은" · 새 방법 제안.

같이 있으면: 산출물의 중심이 **새 설계**면 creative, 있는 것을 **목표치·명세에 맞추는** 것이면 precise.
도메인(증거 방법): 화면·UI·앱·게임 → `product` / 논문·재현·실험·지표·가설 → `research` / 지연·처리량·인프라·안정성·비용 → `system`. 없으면 precise 는 `system`, creative 는 `product`.
티어: "초안·내부용·일단·빠르게"·신호 없음 → `lite` / "공개·팀·배포·사용자에게" → `standard` / "출시·경쟁 제품 옆·논문·SOTA" → `max`. `--tier`·`--profile` 이 오면 그것.

**출력 규칙** — 여기서 끝나는 두 경우는 파일을 읽지도 만들지도 않는다.

- `--route-only`: 한 줄만 쓰고 끝낸다. `route=<skip|precise|creative> tier=<t> domain=<d> mode=<m> — <근거 한 줄>`
- skip (플래그 무관): 두 줄만 쓰고 끝낸다. `route=skip — <근거>. 프롬프트 파일을 만들지 않았다.` / `채팅으로 바로: "<그대로 붙여 쓸 한 문장 지시>"`
  크기로 skip 이면 지시는 주제 그대로 쓰고 (덧붙여도 결과가 같았다 — 실측) 셋째 줄을 더한다: `더 올리려면: 결과를 본 뒤 "지금 버전을 유지하고 개선버전도 만들어줘" 한 번 — 무인으로 돌리려면 /metaprompt <주제> --route <creative|precise> --tier lite (둘 다 비용·시간 약 2.5배, 실측에서 같은 수준)`

## 파일 지도 — 필요한 때 하나씩

| 파일 | 언제 |
|---|---|
| `references/contract.md` | 판정 직후 항상 — 티어 수치 · 역할→모델·effort · 기능 스위치의 **유일한 출처** |
| `references/creative.md` · `precise.md` | 판정된 경로 **하나** |
| `references/product.md` · `research.md` · `system.md` | 판정된 도메인 **하나** (증거 방법) |
| `references/worktree.md` | mode 가 worktree 일 때만 |
| `references/tools.md` | 도메인 필수 도구가 환경에 **빠졌을 때만** |
| `references/template.md` | 조립 직전 |

## 1. 체크포인트 — 횟수는 contract 의 Q

`--yes` 면 전부 건너뛰고 판정을 한 줄로 통보한다. 아니면 **AskUserQuestion 한 번**에 최대 3문항, 추천을 첫 옵션에 `(Recommended)` 로.

- 판정: `<route> · <tier> (Recommended)` 와 인접 조합 2~3개. 설명에 contract 의 M·K 와 역할 수를 적는다 — 사용자는 여기서 비용을 고른다.
- 경로 문항: creative·lite → 기준점 후보 2개(모델 지식) / precise → 테스트 커맨드를 못 찾았으면 그것, 찾았으면 "이미 실패한 접근·제약" / worktree×product → 기존 디자인 시스템을 따를지.
- standard+ 만: "이후 추천값으로 자동" 여부.

standard+ 의 두 번째 체크포인트는 3단계 초안 뒤 한 번 — 기준점 선택(creative) + 체크리스트 승인. 이 밖에서 묻지 않는다.
도구 점검은 별도다: 도메인 레퍼런스의 **필수 도구**가 환경 JSON 에 없을 때만 `tools.md` 를 읽고 한 번 묻는다 (`--yes` 면 묻지 않고 사전조건 절에 넣는다).

## 2. 사실 수집 — 이 컨텍스트에서 검색하지 않는다

- creative: 경로 레퍼런스 1절. 에이전트 수는 contract 의 R. 서브에이전트 타입 `metaprompt:researcher` (없으면 `general-purpose` + `model: "sonnet"`, effort 는 세션값 상속). 여러 개면 한 메시지에서 동시에.
- precise: 외부 리서치 없음. 기준점은 base commit·명세다. 사실은 환경 JSON · 저장소 · 명세에서.
- worktree 이고 standard+: `metaprompt:scout` 1개를 같은 메시지에서 (없으면 `Explore` + `model: "sonnet"`). 반환 형식은 `worktree.md`.

## 3. 초안

경로 레퍼런스 2~3절과 도메인 레퍼런스 2절로 만든다: 체크리스트(contract 의 C) · 회귀 통(worktree) · 종료 문장 · 팬아웃(K 이하)/순차와 그 **이유** · 역할 표(contract 에서 이 경로·티어가 쓰는 행만) · 스위치 셋의 값과 이유(contract 의 조건을 이 주제에 적용).
**동시 만족 점검**: 항목끼리, 항목과 기준점의 미학, 항목과 회귀 통이 상충하는가. 상충이면 항목을 고친다 (체크포인트가 있으면 보여 주고 고르게 한다).
"좋은가"로 끝나는 항목은 다시 쓴다. 공유 상태(같은 파일·좌표계·분할·측정 기준선)에 쓰는 작업은 팬아웃하지 않는다 — 애매하면 순차.

## 4. 조립 · 점검 · 저장

`template.md` 의 규칙대로 채운다. 증거 획득 블록에는 실제 커맨드를 넣는다 — 비우면 검증자가 상상으로 채점한다. 사전조건 절에는 있는 도구까지 전부 적는다.
저장: `--out` 또는 `./prompts/metaprompt-<슬러그>.md` (`--from` 과 같은 경로인데 티어가 바뀌면 `-<티어>` 접미사). 저장 후:

```bash
python3 <skill_dir>/scripts/check_prompt.py <저장 경로>
```

FAIL 은 고쳐서 다시 검사한다 (최대 2회). 남으면 항목과 이유를 알린다. 조용히 끝내지 않는다.

마지막 메시지는 한 화면. 판정된 모드·스위치에 맞는 줄만 남긴다:

```
저장: <경로>
route <r> · tier <t> · domain <d> · mode <m> · 기준점 <b> · 라운드 <M> · 팬아웃 <K>
실행:
  greenfield → mkdir -p <디렉터리> && cd <디렉터리> && git init
  worktree   → git worktree add ../<repo>-metaprompt-<슬러그> -b metaprompt/<슬러그> && cd ../<repo>-metaprompt-<슬러그>
  python3 <skill_dir>/scripts/agents.py <저장 경로>     # 역할 정의 — 반드시 세션 시작 전에
  claude --model <메인 model> --effort <메인 effort>     # teams ON 이면 앞에 CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
  첫 입력 → 내부 라운드: 파일 내용 붙여넣기 / /goal ON: 프롬프트의 `/goal` 줄 / /loop ON: /loop 다음 줄에 붙여넣기 / Workflow ON: 첫 줄에 ultracode
worktree 완료 후 (사람이 판정문을 읽고): git merge --no-ff metaprompt/<슬러그>
```

## 규칙

1. **기준점 없이 뱉지 않는다.** creative 는 실명·수치 사실 3개 이상, precise 는 base commit·명세 조항·재현 절차 3개 이상. 확인 못 한 것은 `(출처 미확인)`.
2. **creative 는 앞서기 항목 + 기본기 항목**, **precise 는 빨강 먼저·테스트 잠금·종료 코드**. 이것이 없으면 평범한 프롬프트다.
3. **생성자와 채점자를 분리한다.** creative 는 새 컨텍스트 검증자, precise 는 먼저 잠긴 테스트의 종료 코드 + `/goal` 평가자. 검증자의 보고 범위는 체크리스트·정확성·기본기 누락(creative)으로 한정한다.
4. **모든 역할에 model 과 effort.** 값은 contract 에서만 가져오고 모델 ID 를 박지 않는다 (별칭 해석은 제공자마다 다르다).
5. **스위치 셋은 값과 이유를 한 줄씩.** 켤 이유가 contract 조건을 전부 채우지 않으면 OFF.
6. **티어가 깎는 것은 깊이다.** 기준점 · 채점자 분리 · Yes/No 체크리스트 · 정체 감지 · 수용된 제약은 lite 에서도 빼지 않는다.
7. **레퍼런스를 미리 읽지 않고, 체크포인트 밖에서 묻지 않고, 시스템 수준 설치(sudo·드라이버)를 직접 하지 않는다.**
