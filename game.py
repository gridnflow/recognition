"""묵찌빠 규칙 상태머신. I/O 없는 순수 로직 — test_game.py로 검증."""

from dataclasses import dataclass
from enum import Enum


class Hand(Enum):
    MUK = "묵"  # 주먹 (바위)
    JJI = "찌"  # 가위
    PPA = "빠"  # 보


# key가 value를 이긴다
BEATS = {Hand.MUK: Hand.JJI, Hand.JJI: Hand.PPA, Hand.PPA: Hand.MUK}

PLAYER = "player"
COMPUTER = "computer"


class Phase(Enum):
    RPS = "rps"  # 가위바위보로 공격권 결정
    MJP = "mjp"  # 묵찌빠 본게임
    OVER = "over"


def rps_winner(a: Hand, b: Hand) -> int | None:
    """a가 이기면 0, b가 이기면 1, 비기면 None."""
    if a == b:
        return None
    return 0 if BEATS[a] == b else 1


class Outcome(Enum):
    DRAW_RETRY = "draw_retry"          # 가위바위보 무승부 → 재시도
    ATTACKER_SET = "attacker_set"      # 가위바위보 승자가 공격권 획득
    ATTACKER_CHANGE = "attacker_change"  # 묵찌빠에서 공격권 이동
    ATTACKER_KEEP = "attacker_keep"    # 공격자가 이겨서 공격권 유지
    GAME_OVER = "game_over"            # 같은 손 → 공격자 최종 승리


@dataclass
class RoundResult:
    phase_played: Phase
    player_hand: Hand
    computer_hand: Hand
    outcome: Outcome
    attacker: str | None  # 라운드 이후의 공격자
    winner: str | None    # 게임이 끝났을 때만


class Game:
    def __init__(self):
        self.phase = Phase.RPS
        self.attacker: str | None = None
        self.winner: str | None = None
        self.round_no = 0

    def play(self, player: Hand, computer: Hand) -> RoundResult:
        if self.phase == Phase.OVER:
            raise RuntimeError("game is over; start a new Game")
        self.round_no += 1

        if self.phase == Phase.RPS:
            w = rps_winner(player, computer)
            if w is None:
                outcome = Outcome.DRAW_RETRY
            else:
                self.attacker = PLAYER if w == 0 else COMPUTER
                self.phase = Phase.MJP
                outcome = Outcome.ATTACKER_SET
        else:  # Phase.MJP
            if player == computer:
                self.phase = Phase.OVER
                self.winner = self.attacker
                outcome = Outcome.GAME_OVER
            else:
                w = rps_winner(player, computer)
                new_attacker = PLAYER if w == 0 else COMPUTER
                outcome = (
                    Outcome.ATTACKER_KEEP
                    if new_attacker == self.attacker
                    else Outcome.ATTACKER_CHANGE
                )
                self.attacker = new_attacker

        return RoundResult(
            phase_played=Phase.RPS if outcome in (Outcome.DRAW_RETRY, Outcome.ATTACKER_SET) else Phase.MJP,
            player_hand=player,
            computer_hand=computer,
            outcome=outcome,
            attacker=self.attacker,
            winner=self.winner,
        )
