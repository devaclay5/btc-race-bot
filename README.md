# btc-race-bot

[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/devaclay5/btc-race-bot/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/devaclay5/btc-race-bot/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)

A Python trading bot for make.fun's "Race a BTC trading bot live for 24 hours" bounty. It trades Coinbase Wrapped BTC (cbBTC) against USDC, minute by minute, on a replay of on-chain Orca Whirlpool prices, starting with 1,000 USDC of paper money.

## Strategy

Ride multi-hour uptrends, sit in cash otherwise:

- **Entry** — all three must hold on a bar's close: the close breaks above the highest close of the last 105 bars; the 12-bar EMA sits above the 48-bar EMA; and the Kaufman efficiency ratio over the last 30 bars is at least 0.35 (the move is directional, not chop).
- **Exit** — either: the close falls below the lowest close of the last 60 bars, or the close falls 120 bps below the highest close since entry (trailing stop).
- **Sizing** — full size on entry (all cash), whole position on exit. Long only, at most one position.

A full-size round trip costs about 36 bps in fees, slippage and price impact at the pool depths this window shows, so the bot only trades on moves far larger than that. On the published dev window it trades twice (2 round trips) and ends with a net PnL of about +6.3 USDC, maximum drawdown about 1.2%.

## Run it

```sh
python3 -P -s main.py
```

The bot speaks agent-fun/bars-replay/v1: newline-delimited JSON on stdin and stdout (hello, one batch per minute bar, done; one reply per batch echoing its sequence number). Standard library only; `vendor/makefun_bars.py` is the kit's Python SDK shim, copied byte for byte.

---

<sub>Entered on [make.fun](https://make.fun/?ref=zg4y7cmj&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444) · AI agents build software for cash rewards</sub>
