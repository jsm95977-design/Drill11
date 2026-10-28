# PRD: 자동 무적런(AutoRun) 상태 추가

## 1. 개요

### 1.1 배경
현재 소년(Boy)은 `transitions` 라이브러리 기반 상태 머신으로 **Idle / Sleep / Run** 세 가지 상태를 가진다.
여기에 키 조작 없이 화면을 좌우로 자동 왕복하는 **자동 무적런(AutoRun)** 상태를 추가한다.

### 1.2 목표
- Idle 상태에서 `A` 키로 AutoRun 상태에 진입한다.
- AutoRun 상태에서는 키 조작 없이 소년이 스스로 좌우로 이동한다.
- AutoRun 상태의 소년은 Run보다 **빠르고**, **크게** 그려진다.
- 일정 시간이 지나거나 방향키를 누르면 AutoRun이 끝난다.

### 1.3 범위 밖
- "무적"은 상태 이름일 뿐이다. 현재 게임에는 충돌/피격 요소가 없으므로 실제 무적 판정은 구현하지 않는다.
- 기존 Idle / Sleep / Run의 동작은 바꾸지 않는다.

---

## 2. 현재 상태 (As-Is)

| 상태 | 설명 |
|---|---|
| Idle | 제자리 대기 애니메이션. 5초 경과 시 Sleep |
| Sleep | 90도 회전한 누운 모습 |
| Run | 방향키 방향으로 `5` 속도 이동, `clamp(25, x, 775)` |

```
idle  --time_out-->   sleep
sleep --space_down--> idle
idle  --arrow_down--> run
sleep --arrow_down--> run
run   --arrow_up-->   idle
```

---

## 3. 기능 요구사항 (To-Be)

### FR-1. AutoRun 진입
- **Idle** 상태에서 `A` 키를 누르면(`SDL_KEYDOWN`, `SDLK_a`) AutoRun 상태로 바뀐다.
- Sleep, Run, AutoRun 상태에서 `A` 키는 무시한다. (`ignore_invalid_triggers=True` 사용)
- 시작 이동 방향은 진입 시점의 `face_dir`(소년이 바라보던 방향)을 따른다.

### FR-2. 자동 좌우 이동
- AutoRun 상태에서는 키 입력 없이 매 프레임 현재 방향으로 이동한다.
- 이동 속도는 Run(`5`)보다 빠르다. **기본값: `15` (Run의 3배)**
- 이동 애니메이션은 Run과 같은 스프라이트 줄을 쓴다. (오른쪽: y=100, 왼쪽: y=0)

### FR-3. 화면 끝 자동 방향전환
- 소년이 화면 오른쪽 끝에 닿으면 왼쪽으로, 왼쪽 끝에 닿으면 오른쪽으로 방향을 바꾼다.
- 경계는 확대된 크기를 반영해 소년이 화면 밖으로 나가지 않게 한다.
  - 확대 크기가 `150`이면 경계는 `x ∈ [75, 725]` (화면 폭 800 기준)
- 방향을 바꾸면 `face_dir`도 같이 바뀌어, 그려지는 방향과 이동 방향이 항상 같다.

### FR-4. 크기 확대
- AutoRun 상태의 소년은 원본(100×100)보다 크게 그린다. **기본값: 1.5배 (150×150)**
- 커져도 발이 땅에서 뜨거나 묻히지 않도록 그리는 y 좌표를 보정한다.
  - 원본 발 위치: `y - 50 = 40` → 확대 시 중심 y = `40 + 75 = 115`
- 다른 상태로 나가면 원래 크기로 그린다. (실제 `x, y` 값은 바꾸지 않고 그릴 때만 보정한다.)

### FR-5. 시간 초과 시 Idle로 복귀
- AutoRun에 들어온 지 **5초가 지나면** 자동으로 Idle로 돌아간다.
- 타이머는 AutoRun에 들어올 때마다 새로 시작한다.
- Idle로 돌아가면 Idle의 5초 Sleep 타이머도 새로 시작한다. (기존 `Idle.enter` 동작)

### FR-6. 방향키 입력 시 Run으로 전환
- AutoRun 중에 왼쪽/오른쪽 방향키를 누르면 AutoRun을 취소하고 **Run**으로 바꾼다.
- Run에서는 **누른 방향**으로 이동한다. (기존 `boy.dir` 계산 방식을 그대로 사용)
- AutoRun 중에 방향키를 떼는 이벤트(`arrow_up`)는 무시한다.
- AutoRun 중의 `SPACE` 키는 무시한다.

---

## 4. 상태 전이 (To-Be)

```
                 time_out(5초)
        ┌──────────────────────────► sleep
        │                              │
        │        space_down            │
      idle ◄───────────────────────────┘
      │  ▲ ▲
 a_down│  │ │ arrow_up
       │  │ └──────────────── run ◄──── arrow_down (idle, sleep)
       ▼  │ auto_time_out      ▲
    autorun ───────────────────┘
              arrow_down
```

| 트리거 | 출발 | 도착 | 조건 |
|---|---|---|---|
| `time_out` | idle | sleep | Idle 5초 경과 (기존) |
| `space_down` | sleep | idle | SPACE 누름 (기존) |
| `arrow_down` | idle, sleep | run | 방향키 누름 (기존) |
| `arrow_up` | run | idle | 방향키 모두 뗌 (기존) |
| **`a_down`** | **idle** | **autorun** | **A 키 누름 (신규)** |
| **`auto_time_out`** | **autorun** | **idle** | **AutoRun 5초 경과 (신규)** |
| **`arrow_down`** | **autorun** | **run** | **방향키 누름 (신규)** |

> 시간 초과 트리거는 Idle의 `time_out`과 섞이지 않도록 `auto_time_out`이라는 별도 이름을 쓴다.

---

## 5. 구현 설계

### 5.1 `boy.py`
- import에 `SDLK_a` 추가
- `AutoRun` 클래스 추가 (기존 상태 클래스와 같은 구조: `enter / exit / do / draw`)
  - `enter`: `frame = 0`, 이동 방향을 `face_dir`로 정함, `auto_run_start_time = get_time()`
  - `do`: 프레임 증가, 이동, 경계에서 방향전환, 5초가 지나면 `auto_time_out()` 호출
  - `draw`: `clip_draw(..., x, y + 25, 150, 150)`로 확대해서 그림
- `Boy.__init__`
  - `self.AUTO_RUN = AutoRun(self)`, `states` 딕셔너리에 `'autorun'` 등록
  - `State('autorun', ...)` 추가
  - 전이 3개 추가 (4장 표의 신규 항목)
- `Boy.handle_event`
  - `SDL_KEYDOWN` + `SDLK_a` → `self.a_down()`

### 5.2 상수
| 이름 | 값 | 설명 |
|---|---|---|
| AutoRun 속도 | 15 | Run 속도(5)의 3배 |
| 확대 크기 | 150 | 원본 100의 1.5배 |
| 지속 시간 | 5초 | 지나면 Idle로 복귀 |

### 5.3 `main.py`
- 바꿀 것 없음. (이벤트는 이미 `boy.handle_event`로 넘어간다.)

---

## 6. 수용 기준 (테스트 시나리오)

| # | 시나리오 | 기대 결과 |
|---|---|---|
| T1 | Idle에서 A 키 | AutoRun 진입, 소년이 커지고 빠르게 이동 |
| T2 | Sleep / Run에서 A 키 | 아무 변화 없음 |
| T3 | AutoRun 중 키 입력 없음 | 계속 좌우로 이동 |
| T4 | AutoRun 중 화면 오른쪽 끝 도달 | 왼쪽으로 방향전환, 화면 밖으로 나가지 않음 |
| T5 | AutoRun 중 화면 왼쪽 끝 도달 | 오른쪽으로 방향전환, 화면 밖으로 나가지 않음 |
| T6 | AutoRun 진입 후 5초 경과 | Idle로 복귀, 원래 크기로 그려짐 |
| T7 | T6 이후 5초 더 대기 | Sleep으로 전환 (기존 동작 유지) |
| T8 | AutoRun 중 → 방향키 누름 | Run 전환, 누른 방향으로 기본 속도·원래 크기로 이동 |
| T9 | T8 이후 방향키 뗌 | Idle로 복귀 |
| T10 | AutoRun 중 SPACE | 무시 |
| T11 | 오른쪽을 보던 Idle에서 A / 왼쪽을 보던 Idle에서 A | 바라보던 방향으로 AutoRun 시작 |
| T12 | AutoRun 중 땅과 발 위치 | 커진 상태에서도 발이 잔디 위에 자연스럽게 닿음 |

---

## 7. 작업 계획 (커밋 단위)

작업을 잘게 나누고, 단계마다 한글 메시지로 커밋한다.

| 단계 | 작업 | 커밋 메시지 (예시) |
|---|---|---|
| 0 | 지금까지 한 Idle/Sleep/Run 코드를 기준점으로 커밋 | `Idle/Sleep/Run 상태 머신 기본 구현 추가` |
| 1 | PRD 문서 추가 | `자동 무적런 PRD 문서 추가` |
| 2 | `AutoRun` 클래스 골격(빈 enter/exit/do/draw) 추가 및 상태 등록 | `AutoRun 상태 클래스 골격 추가 및 상태 머신에 등록` |
| 3 | A 키 이벤트 처리 및 `idle → autorun` 전이 추가 | `Idle 상태에서 A 키로 AutoRun 진입 전이 추가` |
| 4 | AutoRun 그리기 (Run 스프라이트 사용, 원래 크기) | `AutoRun 상태 달리기 애니메이션 그리기 구현` |
| 5 | 자동 이동 및 빠른 속도 적용 | `AutoRun 상태 자동 이동 및 속도 증가 구현` |
| 6 | 화면 끝 자동 방향전환 | `AutoRun 상태 화면 끝 도달 시 자동 방향전환 구현` |
| 7 | 1.5배 확대 그리기 + 발 위치 보정 + 경계값 보정 | `AutoRun 상태 소년 크기 확대 및 위치 보정` |
| 8 | 5초 경과 시 Idle 복귀 (`auto_time_out`) | `AutoRun 5초 경과 시 Idle 복귀 전이 추가` |
| 9 | 방향키 입력 시 Run 전환 (`autorun → run`) | `AutoRun 중 방향키 입력 시 Run 전환 전이 추가` |
| 10 | 수용 기준 T1~T12 점검 후 필요한 수정 | `AutoRun 동작 점검 및 수정` (필요할 때만) |

각 단계가 끝날 때마다 게임을 실행해 그 단계의 동작을 확인하고 나서 커밋한다.
