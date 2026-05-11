# Session MR Cross Wave 1 Look-ahead Audit

- generated_at: 2026-05-11T10:54:05.015470+00:00
- same_bar_both_hit_total: 261/6875 (3.80%)
- conclusion: Current Wave 1 exit simulation resolves same-bar TP/SL conflicts SL-first. The shared trade_sim helper also uses SL-first ordering. Therefore any WR overshoot in this runner is not explained by TP-first same-bar ordering; friction and bid/ask treatment are the primary audited drivers.

## Current Wave 1 Runner Ordering

- path: /data/repo/fx-ai-trader/scripts/run_session_mr_cross_wave1_bt.py

```python
93: def _simulate_exit(data: pd.DataFrame, entry_i: int, sig, pair: str) -> dict:
94:     sign = 1 if sig.side == "BUY" else -1
95:     max_i = min(len(data) - 1, entry_i + int(DEFAULT_PARAMS["max_hold_bars"]))
96:     exit_price = float(data.iloc[max_i]["Close"])
97:     exit_ts = data.index[max_i]
98:     reason = "DEADLINE"
99: 
100:     for j in range(entry_i, max_i + 1):
101:         row = data.iloc[j]
102:         ts = data.index[j]
103:         high = float(row["High"])
104:         low = float(row["Low"])
105:         if sig.side == "BUY":
106:             if low <= sig.sl:
107:                 exit_price = float(sig.sl)
108:                 exit_ts = ts
109:                 reason = "SL"
110:                 break
111:             if high >= sig.tp:
112:                 exit_price = float(sig.tp)
113:                 exit_ts = ts
114:                 reason = "TP"
115:                 break
116:         else:
117:             if high >= sig.sl:
118:                 exit_price = float(sig.sl)
119:                 exit_ts = ts
120:                 reason = "SL"
121:                 break
122:             if low <= sig.tp:
123:                 exit_price = float(sig.tp)
124:                 exit_ts = ts
125:                 reason = "TP"
126:                 break
127: 
128:     raw_pips = (exit_price - float(sig.entry)) * sign * _pip_mult(pair)
129:     net_pips = raw_pips - float(sig.friction_pips)
130:     return {
131:         "pair": pair,
132:         "window": None,
133:         "side": sig.side,
134:         "signal_ts": sig.signal_ts.isoformat(),
135:         "entry_ts": sig.entry_ts.isoformat(),
136:         "exit_ts": exit_ts.isoformat(),
137:         "entry": float(sig.entry),
138:         "exit": exit_price,
139:         "sl": float(sig.sl),
140:         "tp": float(sig.tp),
141:         "exit_reason": reason,
142:         "raw_pips": raw_pips,
143:         "friction_pips": float(sig.friction_pips),
144:         "friction_source": sig.friction_source,
145:         "net_pips": net_pips,
146:     }
```

## Shared trade_sim Ordering

- path: /data/repo/fx-ai-trader/tools/lib/trade_sim.py

```python
62: def simulate_single_trade(
63:     df: pd.DataFrame,
64:     entry_idx: int,
65:     direction: str,
66:     atr_at_signal: float,
67:     sl_atr_mult: float = 1.0,
68:     tp_atr_mult: float = 1.5,
69:     max_hold_bars: int = 8,
70:     pair: str = "USD_JPY",
71:     apply_friction: bool = True,
72: ) -> Optional[dict]:
73:     """Simulate one trade with SL/TP exit logic.
74: 
75:     Args:
76:         df: OHLCV DataFrame with Open/High/Low/Close columns
77:         entry_idx: Index in df where SIGNAL was generated. Entry price = df[entry_idx+1].Open.
78:         direction: "BUY" or "SELL"
79:         atr_at_signal: ATR value at bar(entry_idx) — used for SL/TP distance
80:         sl_atr_mult: SL distance = sl_atr_mult × ATR
81:         tp_atr_mult: TP distance = tp_atr_mult × ATR
82:         max_hold_bars: Max bars to hold before timeout exit
83:         pair: Currency pair for friction calc
84:         apply_friction: Subtract friction from P&L
85: 
86:     Returns:
87:         dict {entry, exit, outcome, pnl_gross_pip, pnl_net_pip, hold_bars}
88:         or None if entry not feasible (e.g., end of data)
89:     """
90:     if entry_idx + 1 >= len(df):
91:         return None
92:     if not (np.isfinite(atr_at_signal) and atr_at_signal > 0):
93:         return None
94: 
95:     entry_bar = df.iloc[entry_idx + 1]
96:     entry_price = float(entry_bar["Open"])
97:     pip = pip_size(pair)
98: 
99:     if direction == "BUY":
100:         sl_price = entry_price - sl_atr_mult * atr_at_signal
101:         tp_price = entry_price + tp_atr_mult * atr_at_signal
102:     else:
103:         sl_price = entry_price + sl_atr_mult * atr_at_signal
104:         tp_price = entry_price - tp_atr_mult * atr_at_signal
105: 
106:     # Walk forward for SL/TP hit
107:     outcome = "TIMEOUT"
108:     exit_price = None
109:     exit_idx = None
110:     end_idx = min(entry_idx + 1 + max_hold_bars, len(df) - 1)
111:     for j in range(entry_idx + 1, end_idx + 1):
112:         bar = df.iloc[j]
113:         bh = float(bar["High"])
114:         bl = float(bar["Low"])
115:         if direction == "BUY":
116:             # Conservative: if both could hit in same bar, assume SL hit first
117:             if bl <= sl_price:
118:                 outcome, exit_price, exit_idx = "SL", sl_price, j
119:                 break
120:             if bh >= tp_price:
121:                 outcome, exit_price, exit_idx = "TP", tp_price, j
122:                 break
123:         else:
124:             if bh >= sl_price:
125:                 outcome, exit_price, exit_idx = "SL", sl_price, j
126:                 break
127:             if bl <= tp_price:
128:                 outcome, exit_price, exit_idx = "TP", tp_price, j
129:                 break
130: 
131:     if exit_price is None:
132:         # Timeout — exit at end_idx Close
133:         exit_price = float(df.iloc[end_idx]["Close"])
134:         exit_idx = end_idx
135: 
136:     if direction == "BUY":
137:         pnl_gross_pip = (exit_price - entry_price) / pip
138:     else:
139:         pnl_gross_pip = (entry_price - exit_price) / pip
140: 
141:     if apply_friction:
142:         # Determine session at entry bar
143:         ts = df.index[entry_idx + 1]
144:         sess = session_for_utc_hour(ts.hour) if hasattr(ts, "hour") else "default"
145:         friction = friction_pip_default(pair, session=sess)
146:         pnl_net_pip = pnl_gross_pip - friction
147:     else:
148:         friction = 0.0
149:         pnl_net_pip = pnl_gross_pip
150: 
151:     return {
152:         "entry_idx": entry_idx,
153:         "exit_idx": exit_idx,
154:         "entry_ts": df.index[entry_idx + 1],
155:         "exit_ts": df.index[exit_idx],
156:         "entry_price": entry_price,
157:         "exit_price": exit_price,
158:         "direction": direction,
159:         "outcome": outcome,
160:         "pnl_gross_pip": float(pnl_gross_pip),
161:         "pnl_net_pip": float(pnl_net_pip),
162:         "friction_pip": float(friction),
163:         "hold_bars": exit_idx - entry_idx,
164:     }
```

## Same-bar Conflict Diagnostic

| Cell | Pair | Window | Both-hit % | Both-hit N | SL-first EV | SL-first Verdict | TP-first EV | TP-first Verdict |
|---|---|---|---:|---:|---:|---|---:|---|
| C1 | EUR_NZD | NY_LATE | 3.61% | 25 | 0.8155 | ACCEPT | 2.1061 | ACCEPT |
| C2 | EUR_NZD | TOKYO_OPEN | 0.48% | 5 | 0.6661 | ACCEPT | 0.8221 | ACCEPT |
| C3 | AUD_NZD | NY_LATE | 11.45% | 56 | -0.9910 | REJECT | 2.7001 | ACCEPT |
| C4 | AUD_NZD | TOKYO_OPEN | 1.93% | 13 | 1.9921 | ACCEPT | 2.5067 | ACCEPT |
| C5 | AUD_CAD | NY_LATE | 2.02% | 14 | 0.3568 | ACCEPT | 0.7425 | ACCEPT |
| C6 | AUD_CAD | TOKYO_OPEN | 0.51% | 4 | 0.6823 | ACCEPT | 0.7522 | ACCEPT |
| C7 | NZD_CAD | NY_LATE | 4.53% | 32 | -3.3699 | REJECT | -2.4862 | REJECT |
| C8 | NZD_CAD | TOKYO_OPEN | 0.76% | 6 | -2.6345 | REJECT | -2.4748 | REJECT |
| C9 | EUR_GBP | NY_LATE | 16.91% | 91 | -1.3926 | REJECT | 0.0867 | NEEDS_MORE_EVIDENCE |
| C10 | EUR_GBP | TOKYO_OPEN | 3.18% | 15 | -0.3461 | REJECT | -0.0593 | REJECT |
