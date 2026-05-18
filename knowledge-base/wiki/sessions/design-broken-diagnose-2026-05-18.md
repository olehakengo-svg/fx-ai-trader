# DESIGN_BROKEN Diagnose Session (2026-05-18)

## Scope

Pre-registered diagnosis for:

- `dt_sr_channel_reversal`
- `wick_imbalance_reversion`

Out of scope honored: no `modules/demo_trader.py` or `strategies/` implementation changes, no MASSIVE BT execution, no PRIME integration.

## Source and Method

- Code source: `strategies/daytrade/dt_sr_channel.py`, `strategies/daytrade/alpha_wick_imbalance.py`, `app.py`, `modules/demo_trader.py`.
- Data source: Render `/api/demo/trades?limit=10000`, fetched 2026-05-18.
- Clean slice: `is_shadow=1`, `status=CLOSED`, `outcome in (WIN, LOSS)`, `dedup_violation=0`, non-XAU.
- MAFE/MFE basis: **entry_price**, not `signal_price`.

## Phase 1: Code Reading

### dt_sr_channel_reversal

- TP/SL: legacy production path uses **TP=2.0 ATR7 / SL=1.0 ATR7** for both directions. Observed DB geometry after execution/min-distance: avg SL **10.8p**, avg TP **21.9p**, median RR **1.73**, median BE_WR **36.6%**.
- Direction filter: both BUY and SELL. BUY = support/channel-lower proximity + `RSI<45` + MACD-H improvement. SELL = resistance/channel-upper proximity + `RSI>55` + MACD-H deterioration. HTF agreement blocks counter-HTF direction.
- Session: strategy itself is 24h; execution mode may have `active_hours_utc`, but FX daytrade modes for these pairs do not hard-block sessions. Signal scoring only boosts overlap / haircuts off-session.
- Entry timing: legacy uses current/latest bar `df.iloc[-1]` via `ctx.entry`. V2 closed-bar/next-bar path exists behind `DT_SR_CHANNEL_REDESIGN_V2=1`.
- Exit: SL/TP, `SIGNAL_REVERSE`, `MAX_HOLD_TIME` 8h, `TIME_DECAY_EXIT`, `WEEKEND_CLOSE`.

### wick_imbalance_reversion

- TP/SL: **SL=1.5 ATR**, TP=`min(2.5, 1.2 + abs(WIR)*2.0) ATR`. Observed DB geometry: avg SL **13.5p**, avg TP **26.6p**, median RR **1.71**, median BE_WR **36.9%**.
- Direction filter: code supports BUY and SELL, but clean shadow sample is **BUY-only (70/70)**.
- Session: no hard strategy session filter.
- Entry timing: legacy uses latest bar; V2 uses closed confirmation bar and next-bar execution when env is enabled. Current shadow evidence contains mixed runtime path markers.
- Exit: SL/TP, `SIGNAL_REVERSE`, `MAX_HOLD_TIME`, `TIME_DECAY_EXIT`, `MANUAL_CLOSE`, `WEEKEND_CLOSE`.

## Phase 2: Shadow Dissection

### dt_sr_channel_reversal

| Axis | Evidence | State |
|---|---|:---:|
| N / WR | **N=106 WR=33.0%** | 🟠 |
| TP vs SL | **TP_HIT N=18 avg adj=+13.1p / SL_HIT N=42 avg adj=-14.3p** | 🔴 |
| Direction | BUY **N=65 EV=-4.74p**, SELL **N=41 EV=-3.54p** | 🔴 |
| MAFE/MFE | avg MAFE **6.7p**, avg MFE **6.5p** vs avg TP **21.9p** | 🔴 |
| Spread drag | raw EV **-0.93p** -> adj EV **-4.28p**, drag **-3.35p/trade** | 🔴 |
| Best pocket | ADXQ2 **N=10 WR=60.0% EV=+2.32p WF=2/3** | 🟠 |
| WF | **0/3** | 🔴 |

Close reason breakdown:

| close_reason | N | WR | avg raw P/L | avg spread-adj P/L |
|---|---:|---:|---:|---:|
| SL_HIT | 42 | 0.0% | -10.6p | -14.3p |
| SIGNAL_REVERSE | 41 | 31.7% | -1.9p | -4.6p |
| TP_HIT | 18 | 100.0% | +16.4p | +13.1p |
| MAX_HOLD_TIME | 3 | 100.0% | +42.1p | +35.4p |
| TIME_DECAY_EXIT | 1 | 0.0% | -11.8p | -16.4p |
| WEEKEND_CLOSE | 1 | 100.0% | +13.2p | +6.3p |

### wick_imbalance_reversion

| Axis | Evidence | State |
|---|---|:---:|
| N / WR | **N=70 WR=38.6%** | 🟢 |
| TP vs SL | **TP_HIT N=23 avg adj=+17.0p / SL_HIT N=24 avg adj=-19.6p** | 🔴 |
| Direction | BUY **N=70 EV=-2.88p**, SELL **N=0** | 🟠 |
| MAFE/MFE | avg MAFE **8.2p**, avg MFE **10.0p** vs avg TP **26.6p** | 🔴 |
| Spread drag | raw EV **-0.12p** -> adj EV **-2.88p**, drag **-2.76p/trade** | 🔴 |
| Pair asymmetry | GBP_USD **N=17 EV=+5.95p**, GBP_JPY **N=18 EV=-10.40p** | 🟠 |
| Session asymmetry | Tokyo **N=27 EV=+0.55p**, overlap **N=10 WR=0% EV=-11.70p** | 🟠 |
| WF | **1/3** | 🔴 |

Close reason breakdown:

| close_reason | N | WR | avg raw P/L | avg spread-adj P/L |
|---|---:|---:|---:|---:|
| SL_HIT | 24 | 0.0% | -15.6p | -19.6p |
| TP_HIT | 23 | 100.0% | +18.5p | +17.0p |
| SIGNAL_REVERSE | 13 | 23.1% | -3.6p | -6.1p |
| TIME_DECAY_EXIT | 9 | 0.0% | -2.0p | -5.5p |
| MANUAL_CLOSE | 1 | 100.0% | +6.4p | +5.5p |

## Phase 3: Redesign Drafts

### dt_sr_channel_reversal

1. **Closed-bar boundary reversion + ADXQ2 gate**: use existing V2 closed-bar/next-bar semantics, gate to ADXQ2. BT m=72.
2. **Overlap-only friction gate**: restrict to overlap and spread-cost/TP <= 15%. BT m=36.
3. **Early invalidation**: exit failed bounce if no 0.3R MFE within 4 bars or close crosses touched boundary. BT m=36.

### wick_imbalance_reversion

1. **Pair-scope friction filter**: focus on `GBP_USD`, `USD_JPY`, optional small-N `EUR_GBP`; exclude JPY crosses until redesigned. BT m=36.
2. **Overlap hard block**: no overlap entries for this MR wick thesis. BT m=24.
3. **Weaker WIR, stronger confirmation**: threshold 0.45-0.55, confirmation body >=0.25 ATR, optional next-bar non-reversal. BT m=36.

## Phase 4: Output

- Formal proposal: `research/design_broken_redesign_proposal.md`
- This session note: `knowledge-base/wiki/sessions/design-broken-diagnose-2026-05-18.md`
- Decision doc updated: `knowledge-base/wiki/decisions/prime-gate-promotion-path-bug-2026-05-18.md`

## Recommended Next Steps

- First BT: `wick_imbalance_reversion` pair/session filter. It has the clearest positive observed slice: majors/no-JPY-cross **N=42 WR=52.4% EV=+2.80p PF=1.66**.
- Second BT: `dt_sr_channel_reversal` closed-bar + ADXQ2. It is the only positive DT pocket, but current N=10 is too small.
- Third BT: `dt_sr_channel_reversal` early invalidation if the closed-bar/ADXQ2 result still suffers full-SL loss clustering.
