---
strategy: mqe_gbpusd_fix
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

Month-end last 2 business days の London 4pm fix window では、GBPUSD に institutional rebalancing pressure が発生し、直前 4 bar の方向へ伸びた move が 6 bar 程度で反転する、という event-driven reversal thesis。コード上も GBPUSD 限定、月末営業日 window、prior 4-bar move の逆方向へ fade する設計として明示されている。`strategies/daytrade/mqe_gbpusd_fix.py:2`, `strategies/daytrade/mqe_gbpusd_fix.py:4`, `strategies/daytrade/mqe_gbpusd_fix.py:5`, `strategies/daytrade/mqe_gbpusd_fix.py:6`, `strategies/daytrade/mqe_gbpusd_fix.py:14`, `strategies/daytrade/mqe_gbpusd_fix.py:15`, `strategies/daytrade/mqe_gbpusd_fix.py:16`, `strategies/daytrade/mqe_gbpusd_fix.py:17`, `strategies/daytrade/mqe_gbpusd_fix.py:56`, `strategies/daytrade/mqe_gbpusd_fix.py:88`, `strategies/daytrade/mqe_gbpusd_fix.py:94`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Reversal thesis に対し、trigger は `sym in {"GBPUSD"}`、`15 <= ts.hour < 16`、`last 2 business days`、`prior_move = ctx.entry - Close[-5]`、`signal = SELL if prior_move > 0 else BUY`。数式としては `direction = -sign(entry - close[t-4])` で、直前 move の fade を直接捕捉している。`strategies/daytrade/mqe_gbpusd_fix.py:56`, `strategies/daytrade/mqe_gbpusd_fix.py:69`, `strategies/daytrade/mqe_gbpusd_fix.py:70`, `strategies/daytrade/mqe_gbpusd_fix.py:82`, `strategies/daytrade/mqe_gbpusd_fix.py:83`, `strategies/daytrade/mqe_gbpusd_fix.py:85`, `strategies/daytrade/mqe_gbpusd_fix.py:89`, `strategies/daytrade/mqe_gbpusd_fix.py:90`, `strategies/daytrade/mqe_gbpusd_fix.py:94` |
| 3 (timing window) | OK | Trigger は current/future close を参照せず、`ctx.entry` と 4 bar 前 close の差で方向を決めるため、コード内に明示的な look-ahead は見えない。月末判定も timestamp の date だけを使う。ただし docstring は `15:30-16:00 UTC` と書く一方、実装は `15:00-16:00 UTC` 全体で発火し、strategy 内に per-bar/day dedup はないため、同じ fix window 内で複数 candidate が出るリスクは実行層依存。`strategies/daytrade/mqe_gbpusd_fix.py:5`, `strategies/daytrade/mqe_gbpusd_fix.py:16`, `strategies/daytrade/mqe_gbpusd_fix.py:33`, `strategies/daytrade/mqe_gbpusd_fix.py:46`, `strategies/daytrade/mqe_gbpusd_fix.py:58`, `strategies/daytrade/mqe_gbpusd_fix.py:59`, `strategies/daytrade/mqe_gbpusd_fix.py:78`, `strategies/daytrade/mqe_gbpusd_fix.py:82`, `strategies/daytrade/mqe_gbpusd_fix.py:83`, `strategies/daytrade/mqe_gbpusd_fix.py:89`, `strategies/daytrade/mqe_gbpusd_fix.py:90` |
| 4 (filter coherence) | STRENGTHENS | GBPUSD 限定は、コード内 historical note が Bonferroni-significant cell を GBPUSD reversal に限定しているため thesis を強化する。月末 last 2 business days と London fix hour も event edge の発生条件そのものなので STRENGTHENS。MA filter on MR や HMM regime gate same trap の先行例に該当する generic trend/regime hard gate はなく、ゼロ move 除外と最低 RR gate は中立的な guard。`strategies/daytrade/mqe_gbpusd_fix.py:8`, `strategies/daytrade/mqe_gbpusd_fix.py:9`, `strategies/daytrade/mqe_gbpusd_fix.py:10`, `strategies/daytrade/mqe_gbpusd_fix.py:11`, `strategies/daytrade/mqe_gbpusd_fix.py:56`, `strategies/daytrade/mqe_gbpusd_fix.py:60`, `strategies/daytrade/mqe_gbpusd_fix.py:70`, `strategies/daytrade/mqe_gbpusd_fix.py:85`, `strategies/daytrade/mqe_gbpusd_fix.py:91`, `strategies/daytrade/mqe_gbpusd_fix.py:111` |
| 5 (stop/TP geometry) | MISALIGNED | Code comment は `Hold <= 6 bars (90 min)` とし、audit note も fw=6 を最良としているが、return される candidate は `signal/confidence/sl/tp/reasons/entry_type/score` のみで、`MAX_HOLD_BARS` は reason 文字列にしか出ない。Bracket は `SL=1.0 ATR`, `TP=1.5 ATR`, `MIN_RR=1.4` で、TP は round-number shift 後にさらに近くなる。Event MR なら「6 bar の fix reversal を時間で取り切る」設計が自然だが、現行は time stop 不在の ATR bracket で、thesis の測定 horizon と exit geometry がずれている。`strategies/daytrade/mqe_gbpusd_fix.py:12`, `strategies/daytrade/mqe_gbpusd_fix.py:18`, `strategies/daytrade/mqe_gbpusd_fix.py:19`, `strategies/daytrade/mqe_gbpusd_fix.py:62`, `strategies/daytrade/mqe_gbpusd_fix.py:63`, `strategies/daytrade/mqe_gbpusd_fix.py:64`, `strategies/daytrade/mqe_gbpusd_fix.py:65`, `strategies/daytrade/mqe_gbpusd_fix.py:96`, `strategies/daytrade/mqe_gbpusd_fix.py:98`, `strategies/daytrade/mqe_gbpusd_fix.py:99`, `strategies/daytrade/mqe_gbpusd_fix.py:101`, `strategies/daytrade/mqe_gbpusd_fix.py:102`, `strategies/daytrade/mqe_gbpusd_fix.py:104`, `strategies/daytrade/mqe_gbpusd_fix.py:110`, `strategies/daytrade/mqe_gbpusd_fix.py:111`, `strategies/daytrade/mqe_gbpusd_fix.py:118`, `strategies/daytrade/mqe_gbpusd_fix.py:121`, `strategies/daytrade/mqe_gbpusd_fix.py:122`, `strategies/daytrade/mqe_gbpusd_fix.py:123`, `strategies/daytrade/mqe_gbpusd_fix.py:124`, `strategies/daytrade/mqe_gbpusd_fix.py:125`, `strategies/daytrade/mqe_gbpusd_fix.py:126`, `strategies/daytrade/mqe_gbpusd_fix.py:127`, `strategies/daytrade/mqe_gbpusd_fix.py:128` |
| 6 (pair-regime fit) | FIT | 下の Pair-Regime Table 参照。Input pair は `ALL` だが、コードは GBPUSD 以外を hard block するため、実質 cell は GBPUSD only。GBPUSD fw=4/6/8 reversal だけが Bonferroni significant として `raw/mqe_audit/mqe_audit_20260427_1305.json` に残っており、ALL broad scope の forced 適用ではない。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | 730d `mqe_audit` には GBPUSD reversal fw=6 の N=96, WR=69.79%, Wilson lower=59.99%, p_bonf=0.00158, avg_pip=+5.88, Sharpe=6.03 がある。一方、tier-master の phase0_shadow 365d BT EV は `—` で、PF / WF folds>=3 / Kelly fraction は tier-master と audit DB から確認できない。`feedback_partial_quant_trap.md` 基準では N/WR/EV だけでは不可であり、PF/WF/Kelly 欠落により promotion-grade evidence は不足。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| GBPUSD | FIT | Strategy は `_ALLOWED_SYMBOLS = {"GBPUSD"}` で GBPUSD のみ発火する。730d `mqe_audit` では GBP_USD reversal fw=6 が N=96, WR=69.79%, Wilson lower=59.99%, p_bonf=0.00158 と Bonferroni 通過。`strategies/daytrade/mqe_gbpusd_fix.py:56`, `strategies/daytrade/mqe_gbpusd_fix.py:69`, `strategies/daytrade/mqe_gbpusd_fix.py:70` |
| EURUSD | FORCED / BLOCKED | Input は ALL だがコードで non-GBPUSD は `return None`。同監査では EUR_USD reversal fw=6 は WR=60.42%, p_bonf=0.62292 で Bonferroni 不通過。`strategies/daytrade/mqe_gbpusd_fix.py:56`, `strategies/daytrade/mqe_gbpusd_fix.py:70`, `strategies/daytrade/mqe_gbpusd_fix.py:71` |
| USDJPY | FORCED / BLOCKED | Input は ALL だがコードで non-GBPUSD は `return None`。同監査では USD_JPY reversal fw=6 は WR=63.54%, p_bonf=0.12415 で Bonferroni 不通過。`strategies/daytrade/mqe_gbpusd_fix.py:56`, `strategies/daytrade/mqe_gbpusd_fix.py:70`, `strategies/daytrade/mqe_gbpusd_fix.py:71` |
| Other pairs | FORCED / BLOCKED | 実装上は GBPUSD 以外に発火しないため、ALL 指定でも tradeable scope ではない。`strategies/daytrade/mqe_gbpusd_fix.py:56`, `strategies/daytrade/mqe_gbpusd_fix.py:70`, `strategies/daytrade/mqe_gbpusd_fix.py:71` |

## Axis 8: failure mode 診断

Tier 2 (Shadow) / phase0_shadow で、tier-master 365d BT EV が `—` のため昇格判断は不足だが、設計破綻は主に Axis 5、補助的に Axis 3 にある。Axis 2 は thesis を直接捕捉し、Axis 4 も generic MA/HMM filter で edge tail を潰す形ではない。破綻は「fw=6 の event reversal として検証された edge」を、実装では time stop なしの ATR bracket と 15:00-16:00 全時間発火に落としている点。

再設計案は、trigger 中核は維持しつつ、entry/timing と exit を audit 設計に合わせること。具体的には window を code comment と audit note に合わせて `15:30 <= ts.time < 16:00` に狭め、同一 `(symbol, month_end_date, fix_window)` の 1 trade/day dedup を追加する。Exit は `MAX_HOLD_BARS=6` を実行層に渡せる設計へ変更し、TP/SL 到達がなくても 6 bar で time close する。ATR bracket は保護 stop として残すなら、TP は固定 1.5ATR ではなく、fw=6 の observed move distribution または time-close を主 exit にする。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`A`

思想と trigger は有効候補。GBPUSD 月末 London fix fade はコード内 thesis と既存 `mqe_audit` の Bonferroni 通過が一致しており、棄却対象ではない。再設計の中心は trigger 条件を作り直すことではなく、検証された horizon と live 実装の exit/timing を一致させること。

最小 diff の方向性は、`FIX_HOUR_START`/window check を 15:30-16:00 UTC 相当に修正し、strategy または dispatch 層で month-end fix window あたり 1 回だけ candidate を出す dedup key を持たせること。次に `MAX_HOLD_BARS` を reason 文字列ではなく exit policy に接続し、fw=6 の time close を必須化する。採用前には新規探索 BT ではなく既存 audit pipeline の再集計として、365d + WF folds>=3 で Wilson lower / PF / Bonferroni-adjusted p / Kelly fraction を同一 source から出す必要がある。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 96 for GBP_USD reversal fw=6; tier-master phase0_shadow 365d BT EV is `—` | `raw/mqe_audit/mqe_audit_20260427_1305.json`; `knowledge-base/wiki/tier-master.md` |
| Win rate | 69.79% for GBP_USD reversal fw=6 | `raw/mqe_audit/mqe_audit_20260427_1305.json` |
| Wilson lo (95%) | 59.99% for GBP_USD reversal fw=6 | `raw/mqe_audit/mqe_audit_20260427_1305.json` |
| PF | INSUFFICIENT_EVIDENCE: not present in tier-master or `mqe_audit`; no existing audit DB table found for this strategy with profit/loss decomposition | `knowledge-base/wiki/tier-master.md`; `raw/mqe_audit/mqe_audit_20260427_1305.json` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: no WF folds>=3 record found for `mqe_gbpusd_fix` in tier-master/audit artifacts | `knowledge-base/wiki/tier-master.md`; repository audit artifacts search |
| Bonferroni-adj p | 0.00158 for GBP_USD reversal fw=6; fw=4 and fw=8 also pass at 0.01709 | `raw/mqe_audit/mqe_audit_20260427_1305.json` |
| Kelly fraction | INSUFFICIENT_EVIDENCE: payoff distribution / PF is unavailable; WR and code-level nominal RR are insufficient for decision-grade Kelly under `feedback_partial_quant_trap.md` | `raw/mqe_audit/mqe_audit_20260427_1305.json`; `strategies/daytrade/mqe_gbpusd_fix.py:62`, `strategies/daytrade/mqe_gbpusd_fix.py:63`, `strategies/daytrade/mqe_gbpusd_fix.py:104`, `strategies/daytrade/mqe_gbpusd_fix.py:110` |
