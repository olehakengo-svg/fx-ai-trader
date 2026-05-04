---
strategy: vdr_jpy
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

Daily session VWAP から ATR 正規化で大きく乖離した JPY pair は、institutional benchmark pressure により VWAP 方向へ短期平均回帰する、という MR thesis。対象は USDJPY/EURJPY/GBPJPY に限定され、方向は deviation の逆符号。`strategies/daytrade/vdr_jpy.py:2`, `strategies/daytrade/vdr_jpy.py:4`, `strategies/daytrade/vdr_jpy.py:5`, `strategies/daytrade/vdr_jpy.py:6`, `strategies/daytrade/vdr_jpy.py:16`, `strategies/daytrade/vdr_jpy.py:17`, `strategies/daytrade/vdr_jpy.py:18`, `strategies/daytrade/vdr_jpy.py:39`, `strategies/daytrade/vdr_jpy.py:41`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Trigger は `dev_atr = (entry - vwap) / atr`、`abs(dev_atr) >= 1.5`、`dev_atr > 0 -> SELL` / `dev_atr < 0 -> BUY`。VWAP 乖離 MR thesis に必要な extension proxy と逆張り方向が直接実装されている。ただし raw vdr audit の best は USD_JPY `sigma=2.0 fw=2` で、現コードの全 pair 共通 `DEV_SIGMA_THRESHOLD = 1.5` は USDJPY には緩い可能性がある。`strategies/daytrade/vdr_jpy.py:43`, `strategies/daytrade/vdr_jpy.py:57`, `strategies/daytrade/vdr_jpy.py:58`, `strategies/daytrade/vdr_jpy.py:62`, `strategies/daytrade/vdr_jpy.py:63`, `strategies/daytrade/vdr_jpy.py:64`, `strategies/daytrade/vdr_jpy.py:66`, `strategies/daytrade/vdr_jpy.py:70`, `strategies/daytrade/vdr_jpy.py:71`, `strategies/daytrade/vdr_jpy.py:77`, `strategies/daytrade/vdr_jpy.py:78` |
| 3 (timing window) | LATE | Signal は `ctx.entry` と latest VWAP / latest session HLCV を使う bar-close 型で、コード単体に future bar 参照はない。一方、反転確認として BUY は `Close >= Open`、SELL は `Close <= Open` を要求するため、乖離発生足ではなく反転足の close 待ちになる。さらに `MAX_HOLD_BARS = 4` は reason 文字列に出るだけで Candidate に保持されず、この file 内に bar dedup / time exit enforcement は無い。look-ahead ではないが、signal→execution は遅延しやすい。`strategies/daytrade/vdr_jpy.py:48`, `strategies/daytrade/vdr_jpy.py:63`, `strategies/daytrade/vdr_jpy.py:64`, `strategies/daytrade/vdr_jpy.py:96`, `strategies/daytrade/vdr_jpy.py:97`, `strategies/daytrade/vdr_jpy.py:98`, `strategies/daytrade/vdr_jpy.py:99`, `strategies/daytrade/vdr_jpy.py:100`, `strategies/daytrade/vdr_jpy.py:112`, `strategies/daytrade/vdr_jpy.py:115`, `strategies/daytrade/vdr_jpy.py:116`, `strategies/daytrade/vdr_jpy.py:123`, `strategies/daytrade/vdr_jpy.py:125`, `strategies/daytrade/vdr_jpy.py:140`, `strategies/daytrade/vdr_jpy.py:141`, `strategies/daytrade/vdr_jpy.py:142`, `strategies/daytrade/vdr_jpy.py:145` |
| 4 (filter coherence) | STRENGTHENS | Symbol filter は USDJPY/EURJPY/GBPJPY のみを通し、コード内 thesis の JPY pair 限定と一致するため STRENGTHENS。`df` length / valid VWAP / positive ATR / positive `sl_dist` は NEUTRAL。candle confirmation は VWAP 方向への初動を要求するため STRENGTHENS だが、Axis 3 の遅延コストを伴う。RNR の TP shift は execution micro-adjustment で thesis には概ね NEUTRAL。MA filter on MR strategy (`feedback_ma_filter_breaks_mr.md`) や HMM regime gate same trap (`feedback_hmm_gate_same_trap.md`) と同型の trend/regime hard block は無い。`strategies/daytrade/vdr_jpy.py:41`, `strategies/daytrade/vdr_jpy.py:51`, `strategies/daytrade/vdr_jpy.py:52`, `strategies/daytrade/vdr_jpy.py:53`, `strategies/daytrade/vdr_jpy.py:54`, `strategies/daytrade/vdr_jpy.py:59`, `strategies/daytrade/vdr_jpy.py:60`, `strategies/daytrade/vdr_jpy.py:62`, `strategies/daytrade/vdr_jpy.py:85`, `strategies/daytrade/vdr_jpy.py:86`, `strategies/daytrade/vdr_jpy.py:88`, `strategies/daytrade/vdr_jpy.py:90`, `strategies/daytrade/vdr_jpy.py:96`, `strategies/daytrade/vdr_jpy.py:97`, `strategies/daytrade/vdr_jpy.py:99` |
| 5 (stop/TP geometry) | ALIGNED | Geometry は `SL = 1.0 ATR`、TP は VWAP distance と `1.5R` fallback の大きい方、`MIN_RR = 1.2`。entry threshold が `1.5 ATR` なので、通常は target が VWAP 近辺/以遠になり、MR thesis の mean target と整合する。stop は entry からさらに 1ATR 外側で、threshold 1.5ATR entry なら VWAP から約 2.5ATR 側まで noise を許容する。懸念は stop/TP ではなく、`MAX_HOLD_BARS` がこの file 内で exit rule として実装されていない点。`strategies/daytrade/vdr_jpy.py:19`, `strategies/daytrade/vdr_jpy.py:43`, `strategies/daytrade/vdr_jpy.py:44`, `strategies/daytrade/vdr_jpy.py:45`, `strategies/daytrade/vdr_jpy.py:46`, `strategies/daytrade/vdr_jpy.py:48`, `strategies/daytrade/vdr_jpy.py:72`, `strategies/daytrade/vdr_jpy.py:73`, `strategies/daytrade/vdr_jpy.py:74`, `strategies/daytrade/vdr_jpy.py:75`, `strategies/daytrade/vdr_jpy.py:76`, `strategies/daytrade/vdr_jpy.py:79`, `strategies/daytrade/vdr_jpy.py:80`, `strategies/daytrade/vdr_jpy.py:81`, `strategies/daytrade/vdr_jpy.py:82`, `strategies/daytrade/vdr_jpy.py:83`, `strategies/daytrade/vdr_jpy.py:88`, `strategies/daytrade/vdr_jpy.py:89`, `strategies/daytrade/vdr_jpy.py:92`, `strategies/daytrade/vdr_jpy.py:93` |
| 6 (pair-regime fit) | FIT | `pairs: ALL` dispatch でも code は JPY majors のみを trade するため、non-JPY への forced deployment は無い。per-pair: `USDJPY=FIT` ただし raw best は stricter `sigma=2.0`; `EURJPY=FIT`; `GBPJPY=FIT`; `EURUSD/GBPUSD/other=not traded by code, not forced`。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | raw vdr audit には 365d event grid と best trade simulation があり、best `USD_JPY sigma=2.0 fw=2` は `N=11`, `WR=63.64%`, `Wilson lo=35.38%`, `PF=3.624`, `Kelly=0.3949`。しかし tier-master の 365d BT EV は `—`、demo audit DB には `vdr_jpy` candidate/trade が 0 件、WF folds は `[]`、Bonferroni-adjusted p は `6.58594` で有意ではない。`feedback_partial_quant_trap.md` 準拠では N/WR/EV と単発 PF/Kelly だけでは decision-grade ではない。下表参照。 |

## Axis 8: failure mode 診断

`vdr_jpy` は Tier 2 (Shadow) / phase0_shadow。Axis 2 の VWAP deviation trigger、Axis 4 の JPY pair gate、Axis 5 の VWAP target geometry は thesis と概ね整合している。破綻候補は Axis 3 と Axis 7。コード上は反転 candle close 待ちで entry が遅れやすく、`MAX_HOLD_BARS = 4` が Candidate contract に載っていないため、raw audit の forward-bar edge を live execution に固定できていない。

再設計案は trigger/timing の一系統修正。まず pair-specific parameter を導入し、USDJPY は raw best に合わせて `DEV_SIGMA_THRESHOLD=2.0` と `forward_bars=2` 相当の time exit、EURJPY/GBPJPY は `DEV_SIGMA_THRESHOLD=1.5` を維持する variant を pre-register する。次に candle confirmation を hard gate から score penalty/bonus へ落とし、乖離成立 bar close で entry できる variant と、反転確認 bar close variant を分けて既存 audit DB に PF/WF/Kelly 付きで再検証する。

## Verdict

`THESIS_VALID_INSUFFICIENT_EVIDENCE`

## Redesign Recommendation

`A`

思想と主要 trigger は残す。`dev_atr = (entry - vwap) / atr` と `signal = -sign(dev_atr)` は VWAP deviation reversion を直接表しており、MA/HMM 型 filter が thesis を壊している形跡もない。

優先修正は timing と pair-specific trigger。コードレベルでは `_ALLOWED_SYMBOLS` は維持しつつ、`DEV_SIGMA_THRESHOLD` を単一 float から `{USDJPY: 2.0, EURJPY: 1.5, GBPJPY: 1.5}` の mapping に変える。`MAX_HOLD_BARS` は reason 文字列だけでなく exit/routing 側に渡る contract が必要で、少なくとも `fw=2` と `fw=4` の variant を分ける。candle confirmation は `return None` ではなく score adjustment に変更する candidate を作ると、Axis 3 の late-entry リスクを検証できる。新規 BT はこの監査の out-of-scope なので、PF / WF folds / Bonferroni p / Kelly を埋める redesign BT が次の必要 evidence。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | 11 | `raw/vdr_audit/vdr_audit_20260427_1147.json` best `USD_JPY sigma=2.0 fw=2`; deployed `phase0_shadow` tier-master 365d BT EV は `—` |
| Win rate | 63.64% event WR; 54.55% trade simulation WR | `raw/vdr_audit/vdr_audit_20260427_1147.json` best / `trade_sim` |
| Wilson lo (95%) | 35.38% | `raw/vdr_audit/vdr_audit_20260427_1147.json` best |
| PF | 3.624 | `raw/vdr_audit/vdr_audit_20260427_1147.json` `trade_sim` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: `quarterly.wrs = []`, fold count 0 | `raw/vdr_audit/vdr_audit_20260427_1147.json`; tier-master / audit DB search |
| Bonferroni-adj p | 6.58594 | `raw/vdr_audit/vdr_audit_20260427_1147.json` best; not significant |
| Kelly fraction | 0.3949 | `raw/vdr_audit/vdr_audit_20260427_1147.json` `trade_sim`; unstable because N=11 and WF folds absent |
