---
strategy: mtf_counter_trend_scalp
tier: Tier 4 (SCALP_SENTINEL)
source_tier: scalp_sentinel
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

M15 で明確なトレンド存在を確認し、そのトレンド方向の M5 BB%B 過熱 + RSI divergence を待って、M1 engulfing/pin と Stoch 反転で短命 exhaustion swing を逆張りで取る counter-trend scalp。`strategies/scalp/mtf_counter_trend_scalp.py:1`, `strategies/scalp/mtf_counter_trend_scalp.py:6`, `strategies/scalp/mtf_counter_trend_scalp.py:7`, `strategies/scalp/mtf_counter_trend_scalp.py:8`, `strategies/scalp/mtf_counter_trend_scalp.py:108`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | MR thesis に対し、SELL は `m15_adx >= 25 AND m15_ema9 > m15_ema21 AND m5_bbpb >= 0.92 AND m5_div_bear AND (bearish_engulfing OR bearish_pin) AND stoch_k < stoch_d AND entry < open_price`。BUY は `m15_adx >= 25 AND m15_ema9 < m15_ema21 AND m5_bbpb <= 0.08 AND m5_div_bull AND (bullish_engulfing OR bullish_pin) AND stoch_k > stoch_d AND entry > open_price`。過熱・divergence・反転 candle・oscillator cross が thesis を直接捕捉しており、momentum chase にはなっていない。`strategies/scalp/mtf_counter_trend_scalp.py:31`, `strategies/scalp/mtf_counter_trend_scalp.py:32`, `strategies/scalp/mtf_counter_trend_scalp.py:33`, `strategies/scalp/mtf_counter_trend_scalp.py:133`, `strategies/scalp/mtf_counter_trend_scalp.py:149`, `strategies/scalp/mtf_counter_trend_scalp.py:150`, `strategies/scalp/mtf_counter_trend_scalp.py:152`, `strategies/scalp/mtf_counter_trend_scalp.py:155`, `strategies/scalp/mtf_counter_trend_scalp.py:157`, `strategies/scalp/mtf_counter_trend_scalp.py:159`, `strategies/scalp/mtf_counter_trend_scalp.py:178`, `strategies/scalp/mtf_counter_trend_scalp.py:179`, `strategies/scalp/mtf_counter_trend_scalp.py:181`, `strategies/scalp/mtf_counter_trend_scalp.py:183`, `strategies/scalp/mtf_counter_trend_scalp.py:185`, `strategies/scalp/mtf_counter_trend_scalp.py:187` |
| 3 (timing window) | LOOKAHEAD | 明示的な未来 index 参照はないが、M1 engulfing/pin は `df.iloc[-1]` の current bar を使い、同じ evaluate 内で `ctx.entry` と `ctx.open_price` の足色、Stoch cross を判定して Candidate を返す。strategy 内に bar-close 確定フラグ、signal bar timestamp、または `(symbol, signal, bar_time)` dedup がなく、未確定 1m 足で signal が点滅し同一 bar 多重 entry になるリスクがある。さらに M15/M5 は `ctx.htf["m15"]` / `ctx.htf["m5"]` を前提にするが、欠落時は即 no-trade で、過去 preflight でも m15/m5 unsupplied が silent 化原因として記録されている。`strategies/scalp/mtf_counter_trend_scalp.py:58`, `strategies/scalp/mtf_counter_trend_scalp.py:59`, `strategies/scalp/mtf_counter_trend_scalp.py:79`, `strategies/scalp/mtf_counter_trend_scalp.py:93`, `strategies/scalp/mtf_counter_trend_scalp.py:122`, `strategies/scalp/mtf_counter_trend_scalp.py:123`, `strategies/scalp/mtf_counter_trend_scalp.py:124`, `strategies/scalp/mtf_counter_trend_scalp.py:125`, `strategies/scalp/mtf_counter_trend_scalp.py:155`, `strategies/scalp/mtf_counter_trend_scalp.py:157`, `strategies/scalp/mtf_counter_trend_scalp.py:159`, `strategies/scalp/mtf_counter_trend_scalp.py:183`, `strategies/scalp/mtf_counter_trend_scalp.py:185`, `strategies/scalp/mtf_counter_trend_scalp.py:187`, `strategies/scalp/mtf_counter_trend_scalp.py:232` |
| 4 (filter coherence) | STRENGTHENS | Pair gate は USD_JPY/EUR_USD の liquid majors に限定し、hour friction gate は scalp cost を抑えるため STRENGTHENS。M15 ADX/EMA は MR 方向に MA alignment を要求するのではなく「反転を狙うための trend exhaustion tail」を定義しており、MA filter on MR strategy の BREAKS 例とは異なる。M5 BB%B + RSI divergence、M1 engulfing/pin + Stoch、M5 RSI extreme bonus、peak liquidity bonus、1m ADX>35 reject はいずれも exhaustion/reversion thesis を強化する。`strategies/scalp/mtf_counter_trend_scalp.py:28`, `strategies/scalp/mtf_counter_trend_scalp.py:29`, `strategies/scalp/mtf_counter_trend_scalp.py:31`, `strategies/scalp/mtf_counter_trend_scalp.py:32`, `strategies/scalp/mtf_counter_trend_scalp.py:33`, `strategies/scalp/mtf_counter_trend_scalp.py:113`, `strategies/scalp/mtf_counter_trend_scalp.py:117`, `strategies/scalp/mtf_counter_trend_scalp.py:118`, `strategies/scalp/mtf_counter_trend_scalp.py:133`, `strategies/scalp/mtf_counter_trend_scalp.py:149`, `strategies/scalp/mtf_counter_trend_scalp.py:152`, `strategies/scalp/mtf_counter_trend_scalp.py:155`, `strategies/scalp/mtf_counter_trend_scalp.py:157`, `strategies/scalp/mtf_counter_trend_scalp.py:178`, `strategies/scalp/mtf_counter_trend_scalp.py:181`, `strategies/scalp/mtf_counter_trend_scalp.py:183`, `strategies/scalp/mtf_counter_trend_scalp.py:185`, `strategies/scalp/mtf_counter_trend_scalp.py:211`, `strategies/scalp/mtf_counter_trend_scalp.py:212`, `strategies/scalp/mtf_counter_trend_scalp.py:216`, `strategies/scalp/mtf_counter_trend_scalp.py:223` |
| 5 (stop/TP geometry) | ALIGNED | SL は M5 exhaustion wick の外側 + 1pip buffer、かつ SL distance > 12pip は exhaustion 失敗として reject。TP は USD_JPY 6pip / EUR_USD 5pip の固定小幅と `1.2R` floor のうち利益幅が大きい方を採用するため、短命 exhaustion swing を狙う scalp MR と整合する。明示 mean target はないが、full mean reversion ではなく 5-8pip exhaustion swing thesis なので geometry は壊していない。`strategies/scalp/mtf_counter_trend_scalp.py:34`, `strategies/scalp/mtf_counter_trend_scalp.py:35`, `strategies/scalp/mtf_counter_trend_scalp.py:38`, `strategies/scalp/mtf_counter_trend_scalp.py:39`, `strategies/scalp/mtf_counter_trend_scalp.py:40`, `strategies/scalp/mtf_counter_trend_scalp.py:41`, `strategies/scalp/mtf_counter_trend_scalp.py:162`, `strategies/scalp/mtf_counter_trend_scalp.py:166`, `strategies/scalp/mtf_counter_trend_scalp.py:167`, `strategies/scalp/mtf_counter_trend_scalp.py:169`, `strategies/scalp/mtf_counter_trend_scalp.py:170`, `strategies/scalp/mtf_counter_trend_scalp.py:171`, `strategies/scalp/mtf_counter_trend_scalp.py:172`, `strategies/scalp/mtf_counter_trend_scalp.py:190`, `strategies/scalp/mtf_counter_trend_scalp.py:194`, `strategies/scalp/mtf_counter_trend_scalp.py:195`, `strategies/scalp/mtf_counter_trend_scalp.py:197`, `strategies/scalp/mtf_counter_trend_scalp.py:198`, `strategies/scalp/mtf_counter_trend_scalp.py:199`, `strategies/scalp/mtf_counter_trend_scalp.py:200` |
| 6 (pair-regime fit) | FIT / FORCED | Input は `ALL` だが、実装は `_ALLOWED_PAIRS = {"USD_JPY", "EUR_USD"}` のみ。USD_JPY/EUR_USD は dedicated fixed TP を持つため code-level fit はあるが、その他 pairs は audit scope 上の ALL に含まれるだけで実装上は no-trade。pair table below. |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master は SCALP_SENTINEL 所属のみで、prompt-supplied 365d BT EV は `—`。local `demo_trades.db` では `demo_trades` / `evaluated_candidates` / `oanda_audit` の exact `mtf_counter_trend_scalp` 行が 0 件。既存分析には標準 BT の MTF scalp が m15/m5 unsupplied で N=0 になる既知問題と、`mtf_counter_trend_scalp` 修正適用後 BT が未実施である記録がある。Wilson lower / PF / WF folds>=3 / Bonferroni-adjusted p / Kelly fraction は decision-grade source から揃わないため、`feedback_partial_quant_trap.md` 基準では統計判断不可。 |

### Pair-Regime Table

| Pair / scope | Verdict | Evidence |
|--------------|---------|----------|
| USD_JPY | FIT | 実装で許可され、固定 TP は 6pip。JPY major の trend exhaustion scalp として code-level thesis に適合する。`strategies/scalp/mtf_counter_trend_scalp.py:28`, `strategies/scalp/mtf_counter_trend_scalp.py:40`, `strategies/scalp/mtf_counter_trend_scalp.py:113` |
| EUR_USD | FIT / empirically unproven | 実装で許可され、固定 TP は 5pip。liquid major への限定としては thesis と衝突しないが、現行 artifact では pair-specific Wilson/PF/Kelly が不足している。`strategies/scalp/mtf_counter_trend_scalp.py:28`, `strategies/scalp/mtf_counter_trend_scalp.py:41`, `strategies/scalp/mtf_counter_trend_scalp.py:113` |
| Other pairs in ALL | FORCED / NO-TRADE | Audit input は ALL だが、実装では許可ペア以外を即 return するため強制適用すると no-trade になる。`strategies/scalp/mtf_counter_trend_scalp.py:28`, `strategies/scalp/mtf_counter_trend_scalp.py:113`, `strategies/scalp/mtf_counter_trend_scalp.py:114` |

## Axis 8: failure mode 診断

Tier 4 (SCALP_SENTINEL) なので failure mode 診断対象。破綻軸は Axis 3 が主で、Axis 7 が検証不足として残る。Axis 2 は MR exhaustion trigger と整合し、Axis 4 の filter は trend tail / cost / micro-reversal を強化し、Axis 5 の wick stop + 1.2R floor は短命 exhaustion swing と整合する。一方で、未確定 1m bar の engulfing/pin、足色、Stoch cross を同一 evaluate で読み、strategy 内に bar-close gate と dedup key がないため、BT/Shadow/Live で signal timing がズレるリスクがある。さらに `ctx.htf["m15"]` / `ctx.htf["m5"]` 欠落で no-trade になるデータ契約も過去に silent 化原因として観測されている。

再設計案は Timing/Data-contract 修正の 1 系統。M15/M5 は確定済み HTF feature だけを渡す契約にし、M1 engulfing/pin と Stoch/足色は直近確定 1m bar で評価、entry は次 bar execution に分離する。Candidate または routing 層に `entry_type + symbol + signal + signal_bar_time` の dedup key を持たせ、同一 signal bar の多重発火を止める。trigger/filter/stop は現行維持でよいが、修正後に 365d BT または少なくとも pre-registered 180d、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 source で再集計する必要がある。

## Verdict

`THESIS_VALID_TIMING_BROKEN`

## Redesign Recommendation

`A`

思想は明確で、trigger/filter/stop の設計は大きく崩れていない。修正対象は timing/data contract に集中させる。具体的には `ctx.df.iloc[-1]` を「確定済み 1m signal bar」として扱える context を用意し、未確定 bar なら return する。HTF 側も `m15` / `m5` が close 済み feature であることを上位層で保証し、欠落時は silent no-trade ではなく監査可能な reject reason を残す。

コードレベルの想定 diff は、entry 条件前に `if not ctx.is_closed: return None` 相当を追加し、`Candidate` または上位 routing に `signal_bar_time` を伝播させる方向。既存の `m5_bbpb` / `rsi_div_*` / engulfing-pin / Stoch / wick SL / 1.2R floor は維持する。統計 artifact がないため Shadow 復帰前に必要なのは新規探索ではなく、closed-bar 版の既存 thesis を USD_JPY/EUR_USD で同一手順再集計すること。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | INSUFFICIENT_EVIDENCE. tier-master 365d BT: `—`; local `demo_trades.db` exact rows: `demo_trades=0`, `evaluated_candidates=0`, `oanda_audit=0`; standard MTF scalp BT historically N=0 due m15/m5 unsupplied; repaired `mtf_counter_trend_scalp` BT is recorded as未実施. | `knowledge-base/wiki/tier-master.md`; local `demo_trades.db`; `audit/2026-04-30/silent-strategies-preflight.md`; `knowledge-base/wiki/analyses/mtf-regime-trend-cascade-null-finding-2026-04-30.md` |
| Win rate | INSUFFICIENT_EVIDENCE; no decision-grade trade set for this exact strategy/pair scope. | audit DB / tier-master |
| Wilson lo (95%) | INSUFFICIENT_EVIDENCE; N=0 or no stored exact trade set, so Wilson lower cannot support promotion or rejection. | audit DB / tier-master |
| PF | INSUFFICIENT_EVIDENCE; tier-master has SCALP_SENTINEL membership only and no PF for `mtf_counter_trend_scalp`. | `knowledge-base/wiki/tier-master.md`; `knowledge-base/wiki/tier-master.json` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE; no stored 3+ fold WF artifact for this exact strategy. | audit DB / tier-master |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE; no stored Bonferroni-adjusted p for this exact strategy. | audit DB / tier-master |
| Kelly fraction | INSUFFICIENT_EVIDENCE; local exact rows are 0 and tier-master does not store Kelly for this strategy. | local `demo_trades.db`; `knowledge-base/wiki/tier-master.md` |
