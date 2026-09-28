# tools — 검증 도구 점검과 설치

환경 JSON 의 `tools` · `python_packages` · `playwright_browsers` · `gpu` · `browser` · `os` 를 도메인 레퍼런스 3절의 **필수 도구**와 대조해, 빠진 것이 있을 때만 이 파일을 읽는다.
검증자가 도구 없이 채점하면 상상으로 채운다. 그래서 없는 도구는 프롬프트를 만들기 전에 잡는다.

## 설치 정책

| 종류 | 예 | 누가 |
|---|---|---|
| 사용자 공간 | pip/uv/npx/cargo/go install, `~/.local/bin` 에 바이너리 | 체크포인트에서 "지금 설치"를 고르면 **스킬이 실행**하고 `detect_env.py` 를 다시 돌려 확인한다 |
| 시스템 수준 | apt/brew, GPU 드라이버, docker, sudo 가 필요한 것 | 커맨드를 보여주고 **사용자가 실행**한다 (`! <커맨드>` 로 이 세션에서 바로). 스킬은 기다리지 않고 프롬프트 사전조건에도 넣는다 |
| 불가능·부적절 | 실행은 다른 머신(원격 GPU)에서, 회사 정책 | "대체 방법" 또는 "사전조건으로만" |

`--yes` 면 아무것도 설치하지 않는다. 사전조건 절에 넣고 마지막 안내에 한 줄 경고한다.
설치 커맨드는 `os` (distro · apt · brew · sudo) 에 맞춰 고른다. 크기가 큰 것(CUDA 휠 약 2GB, chromium 약 150MB)은 설명에 크기를 적는다.

## 도메인 × 신호 → 필수 도구

| 도메인 · 신호 | 필수 | 확인 | 사용자 공간 설치 | 시스템 수준 | 대체 |
|---|---|---|---|---|---|
| product · 웹/HTML | 헤드리스 브라우저 하나 — `browser` 또는 `python_packages.playwright` + `playwright_browsers` 에 chromium | `google-chrome --version` · `python3 -c "import playwright"` | `pip install playwright && python3 -m playwright install chromium` 또는 `npx playwright install chromium` | `sudo apt-get install -y chromium` · `brew install --cask google-chrome` | firefox 헤드리스 (`firefox --headless --screenshot out.png URL`) |
| product · 데스크톱/TUI | 화면 캡처 수단 (`xvfb-run` + 브라우저, 터미널 녹화) | `which xvfb-run` | — | `sudo apt-get install -y xvfb` | 텍스트 덤프 비교로 체크리스트를 다시 쓴다 |
| research · 일반 | python3 · pytest · numpy | `python3 -c "import pytest, numpy"` | `pip install pytest numpy` | — | — |
| research · **ML 신호** (학습·미세조정·fine-tune·LLM·임베딩·GPU·CUDA·torch·transformers·딥러닝·추론) | `gpu.count ≥ 1` + torch (+ transformers) | `nvidia-smi -L` · `python3 -c "import torch; print(torch.cuda.is_available())"` | `pip install torch transformers` (CUDA 휠 약 2GB) | GPU 드라이버 — Ubuntu 계열 `sudo ubuntu-drivers autoinstall` 후 재부팅, 그 외는 벤더 설치 안내. **스킬이 직접 하지 않는다** | **CPU 로 범위 축소** — 소형 모델, 표본 ≤ 2,000, 1 epoch. 체크리스트 수치도 같이 줄인다 |
| research · 검색/랭킹·지표 | 지표 패키지 (pytrec_eval 등, 주제별) | `python3 -c "import <패키지>"` | `pip install <패키지>` | — | 자체 구현 + 표준 구현 대조 항목을 체크리스트에 추가 |
| system · 부하 | 부하 생성기 하나 — k6 / hey / wrk / ab / locust | `which k6 hey wrk ab locust` | `locust`: `pip install locust` · `hey`: `go install github.com/rakyll/hey@latest` 또는 GitHub 릴리스 바이너리를 `~/.local/bin` 에 | `sudo apt-get install -y apache2-utils` (ab) · `brew install k6` | python asyncio + httpx 간이 부하기 — standard 이상은 팬아웃 항목으로, lite 는 순차 코어의 첫 단계로 만들게 한다 |
| system · CLI/함수 벤치 | hyperfine 또는 언어별 벤치 (`cargo bench` · `go test -bench`) | `which hyperfine` | `cargo install hyperfine` | `sudo apt-get install -y hyperfine` · `brew install hyperfine` | `time` 반복 + 분산 계산 스크립트 |
| system · 격리 인스턴스 (DB·캐시·큐) | docker | `docker info` | — | 배포판 안내 | 인메모리 대체 (sqlite · fakeredis). 회귀 통에 "실 인스턴스 미검증" 을 명시 |
| worktree · 테스트 커맨드 | 커맨드의 런타임 (`warnings` 가 알려준다) | `node --version` 등 | node: nvm · python: uv/pyenv · rust: rustup | `sudo apt-get install -y nodejs` 등 | 없음 — 회귀 통이 돌지 않으면 시작하지 않는다 |

신호가 겹치면 전부 점검한다 (예: research × ML × worktree 는 GPU · torch · 런타임 셋).

## 체크포인트 문항 만들기 (SKILL.md 1½)

빠진 도구 하나당 문항 하나, 한 번의 AskUserQuestion 에 최대 4개. 넘치면 중요한 순으로 — 런타임 → 검증 핵심 도구 → 보조 도구.
헤더는 도구 이름. 설명에 크기·소요 시간·sudo 필요 여부를 적는다.

| 상황 | 옵션 (첫 번째가 추천) |
|---|---|
| 사용자 공간 설치 가능 | `지금 설치 (Recommended)` / `프롬프트 사전조건으로만` / `대체 방법으로 진행 — <대체>` / `무시` |
| 시스템 수준 | `커맨드 보여주기 — 내가 설치` / `대체 방법으로 진행 — <대체>` / `프롬프트 사전조건으로만` |
| GPU 없음 | `CPU 로 범위 축소 (Recommended)` / `드라이버 설치 커맨드 보기` / `실행은 GPU 머신에서 — 사전조건으로만` |

"지금 설치"를 받으면 설치 커맨드를 실행하고 `detect_env.py` 를 다시 돌려 확인한다. 실패하면 사전조건으로 돌리고 사용자에게 알린다.
"대체 방법"을 받으면 도메인 레퍼런스 3절의 증거 획득 블록과 체크리스트를 그 대체에 맞게 고친다 — 도구만 바꾸고 항목을 그대로 두면 검증자가 못 잰다.

## 프롬프트 사전조건 절 (template.md 의 `## 사전조건`)

빠졌든 아니든 검증자가 기대는 도구를 전부 적는다: 도구 · 확인 커맨드 · 없을 때 할 일.
실행 세션은 라운드 0 에서 확인하고, 사용자 공간이면 설치하고, 시스템 수준이면 **멈추고 사용자에게 설치를 요청**한다. 도구 없이 상상으로 채점하지 않는다.
설치 주체가 두 층이다: 생성 세션(이 스킬)은 체크포인트 1½ 에서만, 실행 세션은 사전조건 절을 따라 라운드 0 에서. `--yes` 는 생성 세션의 설치만 막는다.
