# 묵찌빠 웹캠 게임 (Muk-Jji-Ppa)

웹캠 손 제스처로 컴퓨터와 묵찌빠를 하는 macOS용 Python 게임.
개선 작업을 시작하기 전에 **ROADMAP.md**를 먼저 읽을 것 — 우선순위별 개선 항목과 구현 힌트가 정리되어 있다.

## 실행 / 테스트

```bash
.venv/bin/python main.py        # 게임 실행 (SPACE 시작, R 새 게임, Q/ESC/창닫기 종료)
.venv/bin/python test_game.py   # 규칙 상태머신 단위 테스트 (pytest 불필요)
```

## 아키텍처 (데이터 흐름)

```
카메라 프레임(BGR, 거울 반전)
  → gesture.HandReader.read()        # MediaPipe HandLandmarker (VIDEO 모드)
  → gesture.classify()               # 랜드마크 → 묵/찌/빠 (규칙 기반, 애매하면 None)
  → gesture.GestureBuffer            # 캡처 윈도우 동안 다수결
  → game.Game.play()                 # 순수 로직 상태머신 (I/O 없음)
  → main.App.tick()                  # 라운드 타이밍/상태 전환, HudState 생성
  → ui.render()                      # Pillow로 한글/이모지 HUD 합성
```

- `game.py`는 **순수 로직만** 유지할 것 (I/O·시간·랜덤 금지). 규칙 변경 시 `test_game.py`에 테스트 먼저 추가.
- `main.py`의 타이밍 상수(`BEAT`, `CAPTURE_SECS`, `REVEAL_SECS`)가 게임 체감을 좌우한다.
- 게임 규칙: 가위바위보로 공격권 결정 → 묵찌빠 단계에서 **같은 손이면 공격자 승리**(수비가 따라 내면 짐), 다르면 그 판의 승자가 공격권 획득.

## 환경 함정 (반드시 숙지)

- **Python 3.14 venv** (`.venv/`). 이 환경의 mediapipe 0.10.35에는 **legacy `mp.solutions` API가 없다** — `mediapipe.tasks.python.vision.HandLandmarker`(Tasks API)만 사용 가능. 랜드마크 드로잉 유틸도 없어서 `gesture.draw_landmarks()`를 직접 구현해 둠.
- 모델 파일 `models/hand_landmarker.task`(7.5MB)는 리포에 커밋되어 있음. VIDEO 모드는 **단조 증가 타임스탬프**를 요구 — `HandReader`가 내부에서 보정한다.
- `cv2.putText`는 한글 렌더링 불가 → 모든 텍스트는 `ui.py`에서 Pillow + AppleSDGothicNeo로 그린다.
- Apple Color Emoji 폰트는 **고정 비트맵 크기만 지원** (`ui.EMOJI_SIZE = 160`). 임의 크기로 로드하면 실패한다.
- 음성은 macOS `say -v Yuna` (이 머신에 설치 확인됨). `sound.Speaker`가 논블로킹으로 실행.
- 첫 실행 시 터미널에 **카메라 TCC 권한** 프롬프트가 뜸. 권한 없으면 `cap.isOpened()` 실패 경로로 안내 출력.

## 검증 절차 (변경 후 필수)

1. `.venv/bin/python test_game.py` — 규칙 로직.
2. 헤드리스 스모크: 카메라 없이 `App.tick()`을 가짜 시간/제스처로 구동해 상태 전환 확인, `ui.render()`에 합성 프레임을 넣어 결과 PNG를 눈으로 확인 (기존 세션에서 쓴 패턴 — 검은 720p 프레임 + HudState 조합).
3. 실플레이: `main.py` 실행해 한 게임 완주 (가위바위보 → 묵찌빠 → 승패 선언).

## 커밋 규칙

- 커밋 메시지는 영어로. Co-Authored-By 줄 금지.
- 원격: https://github.com/gridnflow/recognition (public, `main` 브랜치)
