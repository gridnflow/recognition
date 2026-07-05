"""프레임 위 HUD 렌더링 — 한글은 Pillow(AppleSDGothicNeo), 컴퓨터 손은 컬러 이모지."""

from dataclasses import dataclass
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from game import COMPUTER, Hand, PLAYER

KR_FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
EMOJI_FONT = "/System/Library/Fonts/Apple Color Emoji.ttc"
EMOJI_SIZE = 160  # Apple Color Emoji는 고정 비트맵 크기만 지원

EMOJI = {Hand.MUK: "✊", Hand.JJI: "✌️", Hand.PPA: "🖐"}

WHITE = (255, 255, 255)
YELLOW = (255, 220, 60)
RED = (255, 90, 80)
GREEN = (120, 230, 140)
DARK = (20, 20, 20)


@dataclass
class HudState:
    score_player: int = 0
    score_computer: int = 0
    attacker: str | None = None
    center_text: str = ""
    center_color: tuple = YELLOW
    message: str = ""
    message_color: tuple = WHITE
    computer_hand: Hand | None = None
    show_computer_panel: bool = False
    player_hand: Hand | None = None
    hint: str = ""


@lru_cache(maxsize=16)
def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(KR_FONT, size)


@lru_cache(maxsize=1)
def _emoji_font() -> ImageFont.FreeTypeFont | None:
    try:
        return ImageFont.truetype(EMOJI_FONT, EMOJI_SIZE)
    except Exception:
        return None


def _text(draw: ImageDraw.ImageDraw, xy, s, size, fill, anchor="mm", stroke=3):
    draw.text(
        xy, s, font=_font(size), fill=fill, anchor=anchor,
        stroke_width=stroke, stroke_fill=DARK,
    )


def _draw_computer_hand(img: Image.Image, draw: ImageDraw.ImageDraw, hud: HudState):
    """우상단 패널: 컴퓨터가 낸 손 (이모지, 폰트 실패 시 글자)."""
    w = img.width
    panel_cx = w - 130
    _text(draw, (panel_cx, 40), "컴퓨터", 28, WHITE)
    if hud.computer_hand is None:
        _text(draw, (panel_cx, 140), "?", 90, YELLOW)
        return
    ef = _emoji_font()
    if ef is not None:
        try:
            draw.text(
                (panel_cx - EMOJI_SIZE // 2, 60), EMOJI[hud.computer_hand],
                font=ef, embedded_color=True,
            )
        except Exception:
            ef = None
    if ef is None:
        _text(draw, (panel_cx, 140), hud.computer_hand.value, 90, YELLOW)
    _text(draw, (panel_cx, 240), hud.computer_hand.value, 34, YELLOW)


def render(frame_bgr: np.ndarray, hud: HudState) -> np.ndarray:
    h, w = frame_bgr.shape[:2]
    img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img)

    # 스코어 (좌상단)
    _text(draw, (20, 24), f"나 {hud.score_player} : {hud.score_computer} 컴퓨터",
          30, WHITE, anchor="lm")

    # 공격권 배너 (상단 중앙)
    if hud.attacker is not None:
        who = "나" if hud.attacker == PLAYER else "컴퓨터"
        color = GREEN if hud.attacker == PLAYER else RED
        _text(draw, (w // 2, 30), f"공격: {who}", 34, color)

    _draw_computer_hand(img, draw, hud)

    # 중앙 카운트다운 / 안내
    if hud.center_text:
        _text(draw, (w // 2, h // 2 - 40), hud.center_text, 110,
              hud.center_color, stroke=6)

    # 판정 메시지 (중앙 아래)
    if hud.message:
        _text(draw, (w // 2, h // 2 + 70), hud.message, 48,
              hud.message_color, stroke=4)

    # 내가 낸 손 (좌하단)
    if hud.player_hand is not None:
        _text(draw, (20, h - 70), f"나: {hud.player_hand.value}", 40,
              GREEN, anchor="lm")

    # 힌트 (하단)
    if hud.hint:
        _text(draw, (w // 2, h - 26), hud.hint, 24, (200, 200, 200), stroke=2)

    return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
