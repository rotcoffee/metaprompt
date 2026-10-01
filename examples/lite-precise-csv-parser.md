<!-- metaprompt route=precise tier=lite domain=system mode=greenfield baseline="RFC 4180 §2 + CPython 3.12.3 csv.reader (excel dialect)" generated=2026-09-30
     regenerate: /metaprompt "파이썬 표준 csv 모듈 없이 RFC 4180 준수 CSV 파서 구현 — 표준 csv 모듈과 출력 동일" --route precise --tier lite --profile system --mode greenfield --from prompts/metaprompt-csv-parser.md --out prompts/metaprompt-csv-parser.md -->

# 목표

표준 `csv`·`_csv` 모듈을 import 하지 않는 순수 파이썬 CSV 파서 `csvparse.py` 를 만들어줘. 기준은 **RFC 4180 §2 + CPython 3.12.3 `csv.reader` (기본 excel dialect)** 이고, 완료는 의견이 아니라 종료 코드가 판정한다.
환경: Linux x86_64, python3 3.12.3, 표준 라이브러리만 (pytest 없음 → `unittest`). 새 디렉터리에서 `git init` 된 상태로 시작한다. 범위는 **읽기(reader)만**, dialect 는 기본 excel 하나 — writer·Sniffer·DictReader·다른 dialect 는 범위 밖.

완료 = `python3 -m unittest tests.test_rfc4180 -v` 와 `python3 tests/fuzz_equiv.py --n 1000 --seed 0 && python3 -m unittest discover -s tests` 가 exit 0, 그리고 먼저 쓴 회귀 테스트가 고쳐지지 않은 채로 통과.
실패의 정의: 테스트를 고쳐 통과시킨 것 · 구현이 어떤 경로로든 `csv`/`_csv` 를 쓰는 것(import·`importlib`·`__import__`·subprocess 포함) · 픽스처 입력을 하드코딩해 맞춘 것 · 예외를 삼켜 빈 결과를 돌려주는 것.

## 기준점 상세

- 공개 API: `csvparse.parse(text: str) -> list[list[str]]` 는 `list(csv.reader(io.StringIO(text, newline='')))` 와 같아야 하고, `csvparse.reader(lines)` 는 임의의 문자열 이터러블에 대해 `csv.reader(lines)` 와 같은 행을 같은 순서로 내야 한다. csv 가 `csv.Error` 를 내는 입력에서는 `csvparse.Error` 를 낸다.
- RFC 4180 §2 조항 1·2: 레코드는 CRLF 로 구분하고, 마지막 레코드의 줄바꿈은 있어도 없어도 된다. 조항 4: 필드는 쉼표로 구분하고 공백도 필드의 일부다. 조항 5·6: 필드는 큰따옴표로 감쌀 수 있고, 줄바꿈·큰따옴표·쉼표가 든 필드는 감싸야 한다. 조항 7: 따옴표 안의 `"` 는 `""` 로 이스케이프한다.
- CPython 3.12.3 실측값 (이 세션에서 확인): `'a,b\r\nc,d'`→`[['a','b'],['c','d']]` · `'x\ry\nz'`→`[['x'],['y'],['z']]` (`\r`·`\n`·`\r\n` 모두 줄 끝) · `'\r\n\r\nx\n'`→`[[],[],['x']]` (빈 줄은 빈 리스트) · `'a,\n'`→`[['a','']]`.
- RFC 보다 관대한 CPython 동작 (strict=False, 실측): `'a"b,c\n'`→`[['a"b','c']]` (따옴표로 안 감싼 필드 속 `"` 는 리터럴) · `'"ab"c,d\n'`→`[['abc','d']]` (닫는 따옴표 뒤 문자는 이어 붙임) · `' "a",b\n'`→`[[' "a"','b']]` (skipinitialspace=False) · `'"unterminated\n'`→`[['unterminated\n']]` (EOF 에서 열린 따옴표는 오류 없이 닫힘). **RFC 와 CPython 이 다르면 CPython 이 정답이다** — 주제가 "출력 동일" 이다.
- `csv.field_size_limit()` 기본값 131072 를 넘는 필드에서 CPython 은 `csv.Error` 를 낸다 (출처 미확인 — 라운드 0 에서 실측해 판정문에 적는다).

## 실행 예산 (route: precise · tier: lite)

- 메인 세션 effort **medium** · model **opus** — `claude --model opus --effort medium` 로 시작한다 (도중에는 `/effort medium`). 세션 모델이 다르면 시작하지 말고 알린다. xhigh·max 는 이득을 실측하지 않았으면 쓰지 않는다.
- 라운드 상한 **2**. 팬아웃 없음 — 빌더는 메인 세션 하나다. 혼자 끝낼 수 있는 일을 위임하지 마라.
- 역할 — effort 는 에이전트 정의 frontmatter 로만 지정된다 (Agent 호출에는 effort 가 없다). 세션 **시작 전에** `python3 <metaprompt>/scripts/agents.py <이 파일>` 이 아래 표로 `.claude/agents/mp-*.md` 를 만든다. 정의가 로드되지 않았으면 호출에 model 만 지정하고, effort 가 세션값을 상속했다고 판정문에 적는다.

  | 역할 | 정의 | model | effort | 맡는 일 |
  |---|---|---|---|---|
  | 메인 세션 (오케스트레이터·빌더) | — | opus | medium | 테스트 작성·잠금, 파서 구현, 라운드 커밋 |
  | 검증자 | mp-verifier | opus | high | 마지막 라운드 1회, 새 컨텍스트로 정확성만 |

- 기능 스위치:
  - agent teams **OFF** — 단일 파일 상태기계라 독립 흐름이 없고, lite 이며 경쟁 가설 디버깅도 아니다.
  - Workflow **OFF** — 독립 증거 실행이 5개 미만(유닛 테스트·퍼즈 둘)이고 `-p` 에서도 돌아야 한다.
  - 루프 **/goal ON** — 완료가 종료 코드라 새 컨텍스트 평가자가 판정할 수 있고 `-p` 에서도 돈다. 외부 대기 없음이라 `/loop` 는 OFF.
  - 세션 시작 전 이 파일을 작업 디렉터리에 `PROMPT.md` 로 복사한다 (`cp <이 파일> PROMPT.md`).
  - `/goal` 줄 (첫 입력): `/goal PROMPT.md 를 읽고 따른다. 완료: python3 -m unittest tests.test_rfc4180 -v 와 python3 tests/fuzz_equiv.py --n 1000 --seed 0 && python3 -m unittest discover -s tests 가 exit 0 으로 출력되고 git diff <red SHA>..HEAD -- tests/ 가 비어 있음. 또는 2 라운드 후 멈추고 보고`
- 턴 종료 규약: 텍스트만 있는 턴 종료는 완료가 아니다. 종료 조건 미달이고 라운드 상한 전이면 남은 체크리스트 항목을 다시 적고 이어 간다. 사람 입력 없는 자동 재개는 연속 2회까지 — 그 뒤엔 멈추고 남은 항목을 보고한다.
- 서브에이전트 보고는 **30줄 이내**. 코드·로그·스크린샷 전체를 부모 컨텍스트로 올리지 말고 파일 경로와 결론만.
- 판정문은 `verdicts/round-N.md`. 다음 라운드에는 **실패 항목만** 넘기고, 통과 항목의 근거는 다시 읽지 않는다.
- 라운드마다 커밋한다 (`round N: <한 줄 요약>`).
- 검증 증거 범위: lite — 등가성 1천 건(시드 고정 퍼즈) + 고정 사례 유닛 테스트 + 10만 행 스트리밍 1회. 반복 측정·장애 주입·지속 부하·롤백은 성능 목표가 없는 과제라 생략.

## 사전조건 (검증 도구)

라운드 0 에서 확인한다. 사용자 공간 설치(pip·바이너리)는 직접 하고, 시스템 수준(드라이버·apt·docker)이면 **멈추고 사용자에게 요청**한다. 도구 없이 상상으로 채점하지 마라.

| 도구 | 확인 | 없을 때 |
|---|---|---|
| python3 3.12.x (오라클 csv 버전 고정) | `python3 -c "import sys;print(sys.version)"` | 3.12 가 아니면 멈추고 보고 — 오라클 동작이 버전마다 다를 수 있다 |
| unittest (표준) | `python3 -m unittest --help >/dev/null && echo ok` | 없을 수 없음. pytest 는 쓰지 않는다 |
| git | `git --version` | `sudo apt install git` 은 사용자에게 요청 |
| uv (선택) | `uv --version` | 필요 없음 — 외부 패키지를 쓰지 않는다 |
| hyperfine (system 도메인 기본 도구) | `command -v hyperfine` | 이 과제는 성능 목표가 없어 쓰지 않는다. 설치하지 않는다 |

## 순차로 진행할 것 (쪼개지 마)

1. **빨강 먼저** — `tests/` 에 명세를 검사하는 회귀 테스트를 쓰고, 고치기 전에 `python3 -m unittest tests.test_rfc4180 -v` 가 exit ≠ 0 임을 확인해 `round 0: red` 로 커밋한다. 그 SHA 를 판정문에 적는다.
   - 먼저 `csvparse.py` 스텁을 둔다: `class Error(Exception)`, `parse`·`reader` 는 `raise NotImplementedError`. ImportError 로 빨개지는 것은 빨강으로 치지 않는다 — 단언 실패로 빨개야 한다.
   - `tests/test_rfc4180.py`: 기준점 상세의 사례 전부를 `self.assertEqual(csvparse.parse(s), list(csv.reader(io.StringIO(s, newline=''))))` 모양으로 (기대값은 **오라클이 계산**한다, 손으로 쓰지 않는다). 조항 1·2·4·5·6·7 각각 최소 1건, 관대 동작 4건, 빈 입력 `''`, BOM 없는 유니코드 필드, `reader()` 에 줄 리스트를 넘겨 여러 줄에 걸친 따옴표 필드, 오류 입력에서 `csvparse.Error` 발생. 그리고 `csvparse.py` 를 `ast` 로 파싱해 `csv`/`_csv` import·`__import__`·`importlib`·`subprocess` 이름이 없음을 단언하는 테스트.
   - `tests/fuzz_equiv.py`: 알파벳 `a b , " \r \n 공백 é` 에서 길이 0~40 무작위 문자열 `--n` 개를 `--seed` 로 생성, `parse` 결과(또는 예외 발생 여부)를 오라클과 비교, 첫 불일치 입력을 `repr` 로 출력하고 exit 1. 전부 일치면 `OK n=<n>` 을 출력하고 exit 0. 추가로 10만 행 입력을 `reader()` 에 제너레이터로 넘겨 행 수·첫/끝 행이 오라클과 같은지 확인.
2. 이후 `tests/` 는 수정하지 않는다 — `git diff <red SHA>..HEAD -- tests/` 가 비어야 한다. 테스트가 틀렸다고 판단되면 멈추고 보고한다.
3. 원인 지점을 고친다 → `python3 -m unittest tests.test_rfc4180 -v` exit 0 → `python3 tests/fuzz_equiv.py --n 1000 --seed 0 && python3 -m unittest discover -s tests` exit 0.
   - 구현은 문자 단위 상태기계로 한다 (CPython `_csv.c` 의 상태: START_RECORD · START_FIELD · IN_FIELD · IN_QUOTED_FIELD · QUOTE_IN_QUOTED_FIELD · EAT_CRNL 을 참고해도 되지만 `_csv` 를 호출하지는 않는다).
   - 불일치가 나면 추측으로 분기를 추가하지 말고, 퍼즈가 출력한 최소 입력을 오라클에 넣어 동작을 실측한 뒤 상태 전이를 고친다.

외부 리서치는 하지 않는다 — 기준점은 base commit 과 명세다.
아래 전부를 메인 세션이 순서대로 처리한다. 이 티어는 이음매를 다시 붙일 예산이 없다.
파서 상태기계(`csvparse.py`)는 한 에이전트가 처음부터 끝까지 맡아.
이유: 모든 분기가 같은 상태 변수와 같은 필드 버퍼에 쓴다. 쪼개면 부분별로는 그럴싸해도 이음매에서 버그가 난다.

## 검증

만드는 에이전트와 **별개의** 검증을 둔다. 자기가 만든 걸 자기가 채점하지 마.
1차 판정은 먼저 잠긴 테스트의 종료 코드다 — 만든 쪽이 테스트를 바꿀 수 없다. `/goal` 평가자가 턴마다 출력을 읽고, 마지막 라운드에 `mp-verifier` 가 한 번 새 컨텍스트로 정확성만 본다: 테스트가 명세를 실제로 검사하는가, diff 가 증상만 가리는가.
보고 범위는 **아래 체크리스트 항목과 정확성 결함으로 한정**한다 — 새 컨텍스트 리뷰어는 결과가 멀쩡해도 뭔가를 보고하는 경향이 있다. 취향 지적은 판정에 넣지 않는다. 근거 없는 pass 는 무효다.

**직접 증거를 확보한 뒤 판정해라. 추정하지 마라.**

검증자는 코드를 읽고 맞을 것이라고 판단하지 마라. **실행한 종료 코드와 출력만 근거로 인정한다.**

    RED=$(git log --format=%H --grep='^round 0: red' | tail -1)
    git stash -u 2>/dev/null; git checkout -q "$RED"
    python3 -m unittest tests.test_rfc4180 -v; echo "red exit=$?"        # ≠ 0 이어야 한다
    git checkout -q -; git stash pop 2>/dev/null
    python3 -m unittest tests.test_rfc4180 -v; echo "head exit=$?"       # 0 이어야 한다
    python3 tests/fuzz_equiv.py --n 1000 --seed 0; echo "fuzz exit=$?"   # 0
    python3 tests/fuzz_equiv.py --n 1000 --seed 1; echo "fuzz1 exit=$?"  # 잠긴 시드 밖에서도 일치하는가 (과적합 탐지)
    python3 -m unittest discover -s tests; echo "all exit=$?"
    git diff --stat "$RED"..HEAD -- tests/                               # 빈 출력이어야 한다
    grep -nE '(^|[^_a-z])(_?csv)\b|__import__|importlib|subprocess' csvparse.py; echo "grep exit=$? (1 이어야 한다)"

1. 등가성: 위 퍼즈 두 시드의 `OK n=1000` 출력을 판정문에 그대로 붙인다. 불일치면 출력된 입력 `repr` 을 붙인다.
2. 스트리밍: 10만 행 확인이 `fuzz_equiv.py` 출력에 있는지 본다.
3. 우회 탐지: `csvparse.py` 에서 `except` 절을 grep 해, 예외를 삼키고 빈 결과·오라클 호출로 대체하는 경로가 있으면 라인 번호와 함께 fail.

체크리스트 — 전 항목 Yes 여야 통과:

- [ ] 회귀 테스트가 red 커밋에서 exit ≠ 0, HEAD 에서 exit 0 인가 (`python3 -m unittest tests.test_rfc4180 -v`)
- [ ] red 이후 `tests/` 의 diff 가 0줄인가
- [ ] 시드 0 과 시드 1 퍼즈 각 1천 건에서 `parse` 결과(예외 여부 포함)가 CPython 3.12.3 `csv.reader` 와 전부 일치하고 10만 행 스트리밍이 일치하는가 (`fuzz exit=0`·`fuzz1 exit=0`)
- [ ] `csvparse.py` 에 `csv`/`_csv`/`__import__`/`importlib`/`subprocess` 가 한 번도 나오지 않는가 (`grep exit=1`)
- [ ] 예외를 삼키거나 입력 문자열을 하드코딩한 분기 없이, 상태 전이로 결과를 만드는가 (검증자가 `except`·문자열 리터럴 비교 라인 번호로 판정)

판정문 `verdicts/round-N.md` 형식:

- 항목별 **pass/fail 과 근거**(측정값·라인 번호·종료 코드).
- **수용된 제약**: 과제 전제상 원리적으로 해결 불가능한 지적은 실패가 아니라 여기에 적는다 (예: 오류 메시지 문자열은 CPython 과 달라도 된다 — 예외 **발생 여부**만 비교한다). 실패로 세면 정체 감지가 잘못 발동한다.
- 남은 격차가 **요구사항 자체에서 강제된 것인지** 한 문단.

## 종료 조건

`python3 -m unittest tests.test_rfc4180 -v` 와 `python3 tests/fuzz_equiv.py --n 1000 --seed 0 && python3 -m unittest discover -s tests` 의 종료 코드 0 · 잠금 diff 비어 있음 · 오라클 대비 불일치 회귀 0건 (퍼즈 두 시드 · 유닛 테스트 전부) · 체크리스트 전 항목 Yes · 최대 2라운드.
미달이면 지적된 항목만 다시 만들어 재검증한다. 2라운드까지 못 닿으면 멈추고 남은 항목과 이유를 보고한다.

검증자의 **판정**은 받아들이되 **처방**은 체크리스트 전체와 대조한다 — 한 항목을 고치며 다른 항목을 깨는 교환은 손해다.
같은 지적이 2라운드 연속 반복되면 접근이 틀린 것이다. 멈추고 보고한다 (수용된 제약은 세지 않는다).

## 완료 후

마지막 판정문과 최종 커밋을 남기고 멈춘다. 미달로 끝나도 결과물을 지우지 말고 남은 항목과 이유를 판정문에 적는다.
