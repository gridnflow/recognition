"""묵찌빠 웹캠 게임 진입점: 카메라 루프 + 라운드 타이밍 + 키 입력.

실행: .venv/bin/python main.py   (Q/ESC 종료, R 새 게임, SPACE 시작)
"""

import random
import sys
import time

import cv2

from game import COMPUTER, Game, Hand, Outcome, Phase, PLAYER
from gesture import GestureBuffer, HandReader, draw_landmarks
from sound import Speaker
from ui import GREEN, HudState, RED, WHITE, YELLOW, render

BEAT = 0.55          # 구호 한 박자 길이 (초)
CAPTURE_SECS = 0.7   # 마지막 구호("보!"/"빠!") 직후 손 판독 윈도우
REVEAL_SECS = 2.2    # 판정 표시 시간
RETRY_SECS = 1.4     # 손 인식 실패 안내 시간

START, COUNTDOWN, CAPTURE, REVEAL, RETRY, OVER = range(6)


class App:
    def __init__(self, speaker: Speaker):
        self.speaker = speaker
        self.buffer = GestureBuffer()
        self.score_player = 0
        self.score_computer = 0
        self.state = START
        self.game = Game()
        self.words: list[str] = []
        self.t0 = 0.0
        self.until = 0.0
        self.message = ""
        self.message_color = WHITE
        self.computer_hand: Hand | None = None
        self.captured_hand: Hand | None = None

    # ── 라운드 진행 ──────────────────────────────────────────────

    def new_game(self):
        self.game = Game()
        self.start_round(announce=True)

    def start_round(self, announce: bool = False):
        rps = self.game.phase == Phase.RPS
        self.words = ["가위", "바위", "보"] if rps else ["묵", "찌", "빠"]
        self.t0 = time.monotonic()
        self.state = COUNTDOWN
        self.message = ""
        self.computer_hand = None
        self.captured_hand = None
        self.buffer.reset()
        call = ", ".join(self.words) + "!"
        self.speaker.say(("시작! " + call) if announce else call, rate=170)

    def _finish_capture(self, now: float):
        player = self.buffer.result(min_samples=3)
        if player is None:
            self.state = RETRY
            self.until = now + RETRY_SECS
            self.message = "손을 못 봤어요! 다시!"
            self.message_color = YELLOW
            self.speaker.say("다시!")
            return
        self.captured_hand = player
        self.computer_hand = random.choice(list(Hand))
        res = self.game.play(player, self.computer_hand)
        self._apply_result(res, now)

    def _apply_result(self, res, now: float):
        o = res.outcome
        if o == Outcome.DRAW_RETRY:
            self.message, self.message_color = "비겼다! 한 번 더!", YELLOW
            self.speaker.say("비겼다!")
        elif o == Outcome.ATTACKER_SET:
            if res.attacker == PLAYER:
                self.message, self.message_color = "공격권 획득! 묵찌빠!", GREEN
                self.speaker.say("공격권 획득!")
            else:
                self.message, self.message_color = "컴퓨터가 공격! 묵찌빠!", RED
                self.speaker.say("컴퓨터 공격!")
        elif o == Outcome.ATTACKER_CHANGE:
            if res.attacker == PLAYER:
                self.message, self.message_color = "공격권을 뺏어왔다!", GREEN
                self.speaker.say("공격 교체!")
            else:
                self.message, self.message_color = "공격권을 뺏겼다!", RED
                self.speaker.say("공격 교체!")
        elif o == Outcome.ATTACKER_KEEP:
            if res.attacker == PLAYER:
                self.message, self.message_color = "계속 공격!", GREEN
            else:
                self.message, self.message_color = "컴퓨터가 계속 공격!", RED
            self.speaker.say("공격 유지!")
        else:  # GAME_OVER
            if res.winner == PLAYER:
                self.score_player += 1
                self.message, self.message_color = "묵찌빠! 승리!!", GREEN
                self.speaker.say("묵찌빠! 이겼습니다!")
            else:
                self.score_computer += 1
                self.message, self.message_color = "졌다...", RED
                self.speaker.say("아쉽네요, 졌습니다.")
            self.state = OVER
            return
        self.state = REVEAL
        self.until = now + REVEAL_SECS

    # ── 프레임마다 호출 ──────────────────────────────────────────

    def tick(self, now: float, live_gesture: Hand | None) -> HudState:
        hud = HudState(
            score_player=self.score_player,
            score_computer=self.score_computer,
            attacker=self.game.attacker if self.game.phase != Phase.RPS else None,
            hint="Q: 종료  R: 새 게임",
        )

        if self.state == START:
            hud.center_text = "묵찌빠!"
            hud.message, hud.message_color = "SPACE를 눌러 시작", WHITE
            hud.hint = "웹캠에 손이 보이게 해주세요  ·  Q: 종료"
        elif self.state == COUNTDOWN:
            idx = min(int((now - self.t0) / BEAT), 2)
            hud.center_text = self.words[idx] + "!"
            if now >= self.t0 + 2 * BEAT:
                self.state = CAPTURE
                self.until = now + CAPTURE_SECS
        elif self.state == CAPTURE:
            hud.center_text = self.words[2] + "!"
            self.buffer.add(live_gesture)
            if now >= self.until:
                self._finish_capture(now)
        elif self.state == RETRY:
            hud.message, hud.message_color = self.message, self.message_color
            if now >= self.until:
                self.start_round()
        elif self.state == REVEAL:
            hud.message, hud.message_color = self.message, self.message_color
            hud.computer_hand = self.computer_hand
            if now >= self.until:
                self.start_round()
        elif self.state == OVER:
            hud.center_text = "승리!" if self.message_color == GREEN else "패배"
            hud.center_color = self.message_color
            hud.message, hud.message_color = self.message, self.message_color
            hud.computer_hand = self.computer_hand
            hud.hint = "R: 새 게임  Q: 종료"

        # 손 표시: 판정 중엔 캡처된 손, 평소엔 실시간 인식 결과
        hud.player_hand = (
            self.captured_hand if self.state in (REVEAL, OVER) else live_gesture
        )
        return hud

    def on_key(self, key: int):
        if key == ord(" ") and self.state == START:
            self.new_game()
        elif key in (ord("r"), ord("R")):
            self.new_game()


def main() -> int:
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    if not cap.isOpened():
        print("카메라를 열 수 없습니다.")
        print("macOS 카메라 권한: 시스템 설정 > 개인정보 보호 및 보안 > 카메라에서 터미널을 허용하세요.")
        return 1

    reader = HandReader()
    speaker = Speaker()
    app = App(speaker)

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("카메라 프레임을 읽지 못했습니다.")
                return 1
            frame = cv2.flip(frame, 1)  # 거울 모드
            now = time.monotonic()

            gesture, landmarks = reader.read(frame, int(now * 1000))
            if landmarks is not None:
                draw_landmarks(frame, landmarks)

            hud = app.tick(now, gesture)
            cv2.imshow("Muk-Jji-Ppa", render(frame, hud))

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):  # 27 = ESC
                return 0
            if key != 255:
                app.on_key(key)
    finally:
        speaker.stop()
        reader.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    sys.exit(main())
