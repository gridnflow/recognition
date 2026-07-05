"""game.py 상태머신 단위 테스트. `python test_game.py` 또는 pytest로 실행."""

from game import BEATS, COMPUTER, Game, Hand, Outcome, Phase, PLAYER, rps_winner


def test_rps_winner():
    assert rps_winner(Hand.MUK, Hand.MUK) is None
    assert rps_winner(Hand.MUK, Hand.JJI) == 0   # 바위 > 가위
    assert rps_winner(Hand.JJI, Hand.PPA) == 0   # 가위 > 보
    assert rps_winner(Hand.PPA, Hand.MUK) == 0   # 보 > 바위
    assert rps_winner(Hand.JJI, Hand.MUK) == 1
    assert rps_winner(Hand.PPA, Hand.JJI) == 1
    assert rps_winner(Hand.MUK, Hand.PPA) == 1


def test_rps_draw_retries():
    g = Game()
    for h in Hand:
        res = g.play(h, h)
        assert res.outcome == Outcome.DRAW_RETRY
        assert g.phase == Phase.RPS
        assert g.attacker is None


def test_rps_sets_attacker():
    g = Game()
    res = g.play(Hand.MUK, Hand.JJI)  # 플레이어 승
    assert res.outcome == Outcome.ATTACKER_SET
    assert g.attacker == PLAYER
    assert g.phase == Phase.MJP

    g = Game()
    res = g.play(Hand.JJI, Hand.MUK)  # 컴퓨터 승
    assert res.outcome == Outcome.ATTACKER_SET
    assert g.attacker == COMPUTER


def test_same_hand_wins_for_attacker():
    for attacker_wins_rps, expected_winner in [
        ((Hand.MUK, Hand.JJI), PLAYER),
        ((Hand.JJI, Hand.MUK), COMPUTER),
    ]:
        for h in Hand:
            g = Game()
            g.play(*attacker_wins_rps)
            res = g.play(h, h)
            assert res.outcome == Outcome.GAME_OVER
            assert g.phase == Phase.OVER
            assert g.winner == expected_winner
            assert res.winner == expected_winner


def test_attacker_moves_to_exchange_winner():
    g = Game()
    g.play(Hand.MUK, Hand.JJI)  # 플레이어가 공격권
    assert g.attacker == PLAYER

    res = g.play(Hand.PPA, Hand.JJI)  # 컴퓨터(찌)가 이김 → 공격권 이동
    assert res.outcome == Outcome.ATTACKER_CHANGE
    assert g.attacker == COMPUTER
    assert g.phase == Phase.MJP
    assert g.winner is None

    res = g.play(Hand.MUK, Hand.PPA)  # 컴퓨터(빠)가 또 이김 → 공격권 유지
    assert res.outcome == Outcome.ATTACKER_KEEP
    assert g.attacker == COMPUTER

    res = g.play(Hand.PPA, Hand.PPA)  # 같은 손 → 공격자(컴퓨터) 승
    assert res.outcome == Outcome.GAME_OVER
    assert g.winner == COMPUTER


def test_full_game_never_ends_without_same_hand():
    # 서로 다른 손만 내면 몇 라운드가 지나도 게임이 끝나지 않아야 한다
    g = Game()
    g.play(Hand.MUK, Hand.JJI)
    pairs = [(a, b) for a in Hand for b in Hand if a != b]
    for a, b in pairs * 3:
        res = g.play(a, b)
        assert res.outcome in (Outcome.ATTACKER_CHANGE, Outcome.ATTACKER_KEEP)
        assert g.phase == Phase.MJP
        # 공격권은 항상 그 판의 승자에게
        w = rps_winner(a, b)
        assert g.attacker == (PLAYER if w == 0 else COMPUTER)


def test_play_after_over_raises():
    g = Game()
    g.play(Hand.MUK, Hand.JJI)
    g.play(Hand.MUK, Hand.MUK)
    try:
        g.play(Hand.MUK, Hand.JJI)
        assert False, "should have raised"
    except RuntimeError:
        pass


def test_beats_table_is_cycle():
    assert set(BEATS) == set(Hand)
    assert set(BEATS.values()) == set(Hand)
    for k, v in BEATS.items():
        assert k != v


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
