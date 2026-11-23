"""Impulse-and-hold cbBTC bot for agent-fun/bars-replay/v1.

Strategy, in one paragraph: a full-size round trip on this pool costs
roughly 40 bps (4 bps fee + 2 bps slippage + constant-product impact on
each side), so the bot only trades moves that dwarf the cost. While flat
it waits for a genuine impulse -- the close up more than 35 bps over the
last 60 bars, or more than 80 bps over the last 240 bars for a slow
grind -- and then buys with 97% of its cash. While long it simply holds:
it sells only when the close falls under a trailing stop below the
highest close since entry -- 250 bps while the trade is young, tightened
to 200 bps once the position has run +200 bps, because a leg that has
travelled that far and then gives 200 bps back is over -- or 150 bps
under its entry reference (hard stop), or when 240 bars pass without
the position ever reaching +30 bps over the entry reference (the
impulse failed, so stop paying for it). Everything
is integer arithmetic on the raw price units, so two runs over the same
bars give byte-identical replies.

Run by the grader as ``python3 -P -s /bot/main.py``: -P keeps this
file's directory off sys.path, so the vendored SDK is added by hand.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import makefun_bars

SYMBOL = "CBBTC"

# Entry: how strong a rise, in bps over the lookback, counts as an impulse.
FAST_WINDOW = 60
FAST_BPS = 35
SLOW_WINDOW = 240
SLOW_BPS = 80
# Stake: share of the cash on hand spent on an entry (kept under 100% so
# the position stays inside the weight cap as the fill price moves).
STAKE_NUM = 97
STAKE_DEN = 100
# Exits, in bps against closes observed while the position is open.
TRAIL_BPS = 250
ARM_BPS = 200  # peak gain over the entry reference that arms the tighter trail
TRAIL_LATE_BPS = 200
HARD_BPS = 150
PROGRESS_BARS = 240
PROGRESS_BPS = 30
# Slippage cap on every order, measured from the latest close: wide
# enough that a normal one-minute move never rejects a fill, tight
# enough to refuse a fill through a genuine gap.
MAX_SLIPPAGE_BPS = 250

BPS = 10_000


class ImpulseHold:
    """The strategy's memory: the closes seen, and the open trade's marks."""

    def __init__(self):
        self.closes = []  # raw price units, one per batch that carried the symbol
        self.entry_ref = None  # latest close when the position was first seen
        self.peak = None  # highest close since then
        self.held = 0  # bars the position has been seen open

    def _risen(self, window, bps):
        """True when the latest close is more than ``bps`` over its close ``window`` bars ago."""
        if len(self.closes) <= window:
            return False
        now = self.closes[-1]
        then = self.closes[-1 - window]
        return now * BPS > then * (BPS + bps)

    def decide(self, state):
        """The orders for this batch: at most one, or none."""
        bar = state.latest.get(SYMBOL)
        if bar is None:
            return None
        close = int(bar["c"])
        self.closes.append(close)
        held = state.positions.get(SYMBOL)

        if held is not None:
            if self.entry_ref is None:
                self.entry_ref = close
                self.peak = close
                self.held = 0
            self.held += 1
            if close > self.peak:
                self.peak = close
            trail = TRAIL_BPS
            if self.peak * BPS >= self.entry_ref * (BPS + ARM_BPS):
                trail = TRAIL_LATE_BPS
            if close * BPS < self.peak * (BPS - trail):
                return [self._sell(held.qty)]
            if close * BPS < self.entry_ref * (BPS - HARD_BPS):
                return [self._sell(held.qty)]
            if self.held >= PROGRESS_BARS and self.peak * BPS < self.entry_ref * (BPS + PROGRESS_BPS):
                return [self._sell(held.qty)]
            return None

        # Flat: forget the last trade's marks and watch for an impulse.
        self.entry_ref = None
        self.peak = None
        self.held = 0
        if state.warming_up:
            return None
        if self._risen(FAST_WINDOW, FAST_BPS) or self._risen(SLOW_WINDOW, SLOW_BPS):
            return [self._buy(state)]
        return None

    def _buy(self, state):
        stake = state.cash * STAKE_NUM // STAKE_DEN
        room = state.weight_room(SYMBOL)
        if room < stake:
            stake = room
        return {
            "side": "buy",
            "symbol": SYMBOL,
            "notional_quote_units": stake,
            "max_slippage_bps": MAX_SLIPPAGE_BPS,
        }

    def _sell(self, qty):
        return {
            "side": "sell",
            "symbol": SYMBOL,
            "qty": qty,
            "max_slippage_bps": MAX_SLIPPAGE_BPS,
        }


_BOT = ImpulseHold()


def on_batch(state, batch):
    return _BOT.decide(state)


if __name__ == "__main__":
    makefun_bars.run(on_batch)
