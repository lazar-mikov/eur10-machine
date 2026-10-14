import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategies import buy_dip, donchian, momentum, sma_cross  # noqa: E402
from bot import apply_target  # noqa: E402


def test_sma_cross_follows_trend():
    assert sma_cross(list(range(1, 301))) == 1
    assert sma_cross(list(range(300, 0, -1))) == 0
    assert sma_cross([1.0] * 100) == 0  # not enough bars


def test_momentum():
    assert momentum([1.0] * 30 + [2.0]) == 1
    assert momentum([2.0] * 30 + [1.0]) == 0
    assert momentum([1.0] * 10) == 0


def test_donchian_enters_on_breakout_and_exits_on_breakdown():
    flat = [10.0] * 25
    assert donchian(flat + [11.0]) == 1
    assert donchian(flat + [11.0, 9.0]) == 0


def test_buy_dip_holds_five_bars_after_a_crash():
    base = [100.0] * 10
    crash = base + [85.0]
    assert buy_dip(crash) == 1
    assert buy_dip(crash + [85.0] * 4) == 1
    assert buy_dip(crash + [85.0] * 5) == 0


def test_round_trip_costs_two_fees():
    acc = {"cash": 10.0, "units": 0.0, "pos": 0, "trades": 0}
    assert apply_target(acc, 1, 100.0, 0.0025) == "buy"
    assert apply_target(acc, 1, 100.0, 0.0025) is None
    assert apply_target(acc, 0, 100.0, 0.0025) == "sell"
    assert abs(acc["cash"] - 10.0 * 0.9975 * 0.9975) < 1e-9
    assert acc["trades"] == 2
