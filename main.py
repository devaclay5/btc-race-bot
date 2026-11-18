"""Breakout-trend bot for the BTC 24h race (agent-fun/bars-replay/v1).

Strategy: ride multi-hour uptrends, sit in cash otherwise.
  Entry (all three must hold on a bar's close):
    - the close breaks above the highest close of the last 105 bars (a genuine
      multi-hour breakout, not 1-minute noise);
    - the fast EMA (12 bars) sits above the slow EMA (48 bars): the medium trend
      is up;
    - the Kaufman efficiency ratio over the last 30 bars is at least 0.35:
      the move is directional, not chop.
  Exit (either):
    - the close falls below the lowest close of the last 60 bars (the uptrend
      broke down);
    - the close falls 120 bps below the highest close since the entry
      (trailing stop, a safety net for a fast drop).
  Full size on entry (all cash), whole position on exit. Long only, at most
  one position. A full-size round trip costs about 36 bps at the pool depths
  this window shows, so the bot only trades on moves far larger than that:
  on the dev window it trades twice.

Deterministic: every decision is a pure function of the bars seen so far.
No wall clock, no environment, no randomness. Prices are integers at the
protocol's scales; the EMAs and the efficiency ratio are the only floats,
and float arithmetic is deterministic for identical inputs.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars  # noqa: E402

SYMBOL = "CBBTC"

# Strategy parameters (tuned on the dev window; see the README for the numbers).
BREAKOUT_BARS = 105   # entry: close above the highest close of the last N bars
EXIT_BARS = 60        # exit: close below the lowest close of the last N bars
EMA_FAST = 12         # entry filter: fast EMA above slow EMA
EMA_SLOW = 48
ER_BARS = 30          # efficiency-ratio window
ER_MIN = 0.35         # entry filter: efficiency ratio at least this
TRAIL_BPS = 120       # exit: close TRAIL_BPS below the peak close since entry

BUY_SLIPPAGE_BPS = 200   # a buy filling >2% above the last close is a chase: reject
SELL_SLIPPAGE_BPS = 500  # exits must go through even in a fast drop


class Strategy:
    """The strategy's own state: the closes it has seen and the trend it reads."""

    def __init__(self):
        self.closes = []        # every CBBTC close so far, price-scale integers
        self.ema_fast = None    # EMA of the closes, span EMA_FAST
        self.ema_slow = None    # EMA of the closes, span EMA_SLOW
        self.peak = None        # highest close since the position opened

    def note_close(self, close):
        """Fold one new close in (EMAs update; the peak tracks only while holding)."""
        self.closes.append(close)
        kf = 2.0 / (EMA_FAST + 1)
        ks = 2.0 / (EMA_SLOW + 1)
        self.ema_fast = float(close) if self.ema_fast is None else close * kf + self.ema_fast * (1.0 - kf)
        self.ema_slow = float(close) if self.ema_slow is None else close * ks + self.ema_slow * (1.0 - ks)
        if self.peak is not None and close > self.peak:
            self.peak = close

    def efficiency_ratio(self):
        """Kaufman efficiency ratio over the last ER_BARS bars: net move / total path."""
        n = len(self.closes)
        net = abs(self.closes[-1] - self.closes[n - ER_BARS - 1])
        total = 0
        for j in range(n - ER_BARS, n):
            total += abs(self.closes[j] - self.closes[j - 1])
        return net / total if total > 0 else 0.0

    def ready(self):
        """True once the longest lookback (the breakout window) is full."""
        return len(self.closes) > BREAKOUT_BARS

    def entry_signal(self):
        """All three entry conditions on the latest close."""
        closes = self.closes
        high = max(closes[-BREAKOUT_BARS - 1:-1])
        return (
            closes[-1] > high
            and self.ema_fast > self.ema_slow
            and self.efficiency_ratio() >= ER_MIN
        )

    def exit_signal(self):
        """Either exit condition on the latest close."""
        closes = self.closes
        low = min(closes[-EXIT_BARS - 1:-1])
        if closes[-1] < low:
            return True
        if self.peak is not None and closes[-1] * 10000 < self.peak * (10000 - TRAIL_BPS):
            return True
        return False


STRATEGY = Strategy()


def on_batch(state, batch):
    """Decide this batch's orders: at most one buy or one sell, full size."""
    bar = None
    for b in batch["bars"]:
        if b["symbol"] == SYMBOL:
            bar = b
            break
    if bar is None:
        return []  # CBBTC absent this minute: no new information, no orders
    STRATEGY.note_close(int(bar["c"]))
    if not STRATEGY.ready():
        return []  # history still building: the breakout window is not full
    holding = state.positions.get(SYMBOL)
    if holding is None or holding.qty <= 0:
        STRATEGY.peak = None
        if STRATEGY.entry_signal():
            # Never send a buy the market would reject for size: the harness
            # refuses any buy below the minimum notional (1 USDC here), so
            # stay out when the cash left is smaller than that.
            min_notional = int(state.hello["fees"]["min_notional_quote_units"])
            if state.cash < min_notional:
                return []
            return [{
                "side": "buy",
                "symbol": SYMBOL,
                "notional_quote_units": state.cash,
                "max_slippage_bps": BUY_SLIPPAGE_BPS,
            }]
        return []
    if STRATEGY.peak is None:
        STRATEGY.peak = STRATEGY.closes[-1]
    if STRATEGY.exit_signal():
        return [{
            "side": "sell",
            "symbol": SYMBOL,
            "qty": holding.qty,
            "max_slippage_bps": SELL_SLIPPAGE_BPS,
        }]
    return []


makefun_bars.run(on_batch)
