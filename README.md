[![make.fun · btc-race-24h-20261123-0511](https://make.fun/badge/btc-race-24h-20261123-0511.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)
[![rank](https://make.fun/badge/btc-race-24h-20261123-0511/gunturprast/cbbtc-race-bot-20261123/rank.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)
[![reward](https://make.fun/badge/btc-race-24h-20261123-0511/gunturprast/cbbtc-race-bot-20261123/reward.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)

# btc-race-24h — impulse-and-hold cbBTC bot

A Python bot (standard library only) for the make.fun
`btc-race-24h-20261123-0511` competition: it trades cbBTC against USDC,
one one-minute bar at a time, over the `agent-fun/bars-replay/v1`
protocol, starting from 1,000 USDC of paper money.

## Strategy

On this pool a full-size round trip costs about 40 bps once the 4 bps
fee, 2 bps modelled slippage and constant-product price impact on both
sides are paid, so the bot trades rarely and only on moves that dwarf
the cost:

- **Entry (while flat):** buy with 97% of the cash when the close has
  risen more than 35 bps over the last 60 bars — a genuine impulse — or
  more than 80 bps over the last 240 bars, which catches a slow grind
  that never prints a sharp hour.
- **Hold (while long):** do nothing. One position at a time, no
  rebalancing, no averaging.
- **Exits (whole position):** the close falls below a trailing stop
  under the highest close since entry — 250 bps while the trade is
  young, tightened to 200 bps once the position has run +200 bps — or
  150 bps below the entry reference close (hard stop), or 240 bars pass
  without the position ever trading +30 bps above its entry reference —
  the impulse failed, so the bot stops paying carry for it and waits
  for the next one.

Every order carries a 250 bps `max_slippage_bps` cap from the latest
close. All decisions are integer arithmetic on the raw price units, so
the bot is deterministic: two runs over the same bars answer byte for
byte the same.

## Layout

- `main.py` — the bot; it speaks the protocol through the SDK shim.
- `vendor/makefun_bars.py` — a byte-for-byte copy of the kit's Python
  SDK (`sdk/makefun_bars.py`), vendored because the grader runs
  `python3 -P -s`, which leaves the script's directory off `sys.path`;
  `main.py` adds `vendor/` itself.
- `.makefun/owner.json` — the repository claim file naming the payout
  wallet linked to the entrant's account.
