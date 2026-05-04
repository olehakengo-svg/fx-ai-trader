---
strategy: tokyo_range_breakout
tier: Tier 2 (Shadow)
source_tier: phase0_shadow
pairs: ALL
audited_at: 2026-05-04
auditor: codex
---

## Axis 1: 思想 articulation

Tokyo session の range を基準に、London open 7-9 UTC で Tokyo high を上抜けた最初の BUY breakout は、流動性流入により数時間の upside continuation が発生するという session breakout / momentum thesis。コードは Tokyo range、London entry window、fresh upside breakout、4h hold、BUY-only trend type を明示している。`strategies/daytrade/tokyo_range_breakout.py:12`, `strategies/daytrade/tokyo_range_breakout.py:13`, `strategies/daytrade/tokyo_range_breakout.py:14`, `strategies/daytrade/tokyo_range_breakout.py:15`, `strategies/daytrade/tokyo_range_breakout.py:35`, `strategies/daytrade/tokyo_range_breakout.py:36`, `strategies/daytrade/tokyo_range_breakout.py:37`, `strategies/daytrade/tokyo_range_breakout.py:38`, `strategies/daytrade/tokyo_range_breakout.py:39`, `strategies/daytrade/tokyo_range_breakout.py:40`, `strategies/daytrade/tokyo_range_breakout.py:41`, `strategies/daytrade/tokyo_range_breakout.py:56`

## Axes 2-7: 8軸診断

| Axis | Verdict | Evidence |
|------|---------|----------|
| 2 (trigger 整合) | PASS | Momentum / breakout thesis に対して、entry trigger は `BUY: ctx.entry > Tokyo_high ∧ London window(7 <= hour < 9) ∧ earlier London closes <= Tokyo_high ∧ London lows >= Tokyo_low ∧ bullish body_ratio >= 0.30`。これは MR の oversold trigger ではなく、range high の上抜けと陽線実体で continuation を捕捉しているため整合する。`strategies/daytrade/tokyo_range_breakout.py:89`, `strategies/daytrade/tokyo_range_breakout.py:90`, `strategies/daytrade/tokyo_range_breakout.py:129`, `strategies/daytrade/tokyo_range_breakout.py:130`, `strategies/daytrade/tokyo_range_breakout.py:138`, `strategies/daytrade/tokyo_range_breakout.py:139`, `strategies/daytrade/tokyo_range_breakout.py:142`, `strategies/daytrade/tokyo_range_breakout.py:149`, `strategies/daytrade/tokyo_range_breakout.py:150`, `strategies/daytrade/tokyo_range_breakout.py:151`, `strategies/daytrade/tokyo_range_breakout.py:152`, `strategies/daytrade/tokyo_range_breakout.py:155`, `strategies/daytrade/tokyo_range_breakout.py:156`, `strategies/daytrade/tokyo_range_breakout.py:157`, `strategies/daytrade/tokyo_range_breakout.py:166`, `strategies/daytrade/tokyo_range_breakout.py:172`, `strategies/daytrade/tokyo_range_breakout.py:173`, `strategies/daytrade/tokyo_range_breakout.py:175` |
| 3 (timing window) | LOOKAHEAD | コメント上は current bar close breakout だが、strategy 内では bar-close 契約や per-bar dedup state が明示されていない。`ctx.entry` と `ctx.df.iloc[-1]` の current bar High/Low/Open を使って同じ評価タイミングで signal を返すため、実行層が形成中 bar を渡す場合は intrabar high/low/body を見た即時 entry になる。同一 bar 再評価に対する `(pair, date, bar)` dedup もなく、fresh breakout 抑制は過去 London bars のみに依存する。`strategies/daytrade/tokyo_range_breakout.py:100`, `strategies/daytrade/tokyo_range_breakout.py:138`, `strategies/daytrade/tokyo_range_breakout.py:139`, `strategies/daytrade/tokyo_range_breakout.py:149`, `strategies/daytrade/tokyo_range_breakout.py:150`, `strategies/daytrade/tokyo_range_breakout.py:151`, `strategies/daytrade/tokyo_range_breakout.py:152`, `strategies/daytrade/tokyo_range_breakout.py:167`, `strategies/daytrade/tokyo_range_breakout.py:169`, `strategies/daytrade/tokyo_range_breakout.py:170`, `strategies/daytrade/tokyo_range_breakout.py:236` |
| 4 (filter coherence) | BREAKS | Pair filter、15m filter、London 7-9 UTC、minimum Tokyo bars、BOTH breakout exclusion、HTF bear hard block、bullish body filter は breakout continuation を概ね強化する。一方で thesis は Tokyo range の相対的な狭さと London 流動性遷移を根拠にしているのに、実装は `MIN_RANGE_PIP=15` で narrow-range day を除外し、さらに `Tokyo range >= 25pip` に score bonus を与える。これは MA filter on MR strategy -> BREAKS や HMM regime gate same-trap -> BREAKS と同型ではないが、edge が依存する compression 条件を逆向きに扱う filter incoherence である。`strategies/daytrade/tokyo_range_breakout.py:13`, `strategies/daytrade/tokyo_range_breakout.py:64`, `strategies/daytrade/tokyo_range_breakout.py:65`, `strategies/daytrade/tokyo_range_breakout.py:66`, `strategies/daytrade/tokyo_range_breakout.py:76`, `strategies/daytrade/tokyo_range_breakout.py:77`, `strategies/daytrade/tokyo_range_breakout.py:80`, `strategies/daytrade/tokyo_range_breakout.py:82`, `strategies/daytrade/tokyo_range_breakout.py:85`, `strategies/daytrade/tokyo_range_breakout.py:89`, `strategies/daytrade/tokyo_range_breakout.py:111`, `strategies/daytrade/tokyo_range_breakout.py:135`, `strategies/daytrade/tokyo_range_breakout.py:155`, `strategies/daytrade/tokyo_range_breakout.py:163`, `strategies/daytrade/tokyo_range_breakout.py:166`, `strategies/daytrade/tokyo_range_breakout.py:215`, `strategies/daytrade/tokyo_range_breakout.py:216`, `strategies/daytrade/tokyo_range_breakout.py:217` |
| 5 (stop/TP geometry) | MISALIGNED | 実装 R:R は `TP=+20pip`, `SL=-15pip`, `RR=1.33`。固定 asymmetry は悪くないが、breakout thesis の推奨 geometry は continuation を取りに行く trailing / BE / time-stop であり、`MAX_HOLD_BARS=16` は class attr にあるだけで `Candidate` へ渡らず、return は fixed `sl` / `tp` のみ。したがって breakout の右尾を伸ばす構造としては未整合。`strategies/daytrade/tokyo_range_breakout.py:68`, `strategies/daytrade/tokyo_range_breakout.py:69`, `strategies/daytrade/tokyo_range_breakout.py:70`, `strategies/daytrade/tokyo_range_breakout.py:71`, `strategies/daytrade/tokyo_range_breakout.py:73`, `strategies/daytrade/tokyo_range_breakout.py:74`, `strategies/daytrade/tokyo_range_breakout.py:181`, `strategies/daytrade/tokyo_range_breakout.py:182`, `strategies/daytrade/tokyo_range_breakout.py:183`, `strategies/daytrade/tokyo_range_breakout.py:184`, `strategies/daytrade/tokyo_range_breakout.py:190`, `strategies/daytrade/tokyo_range_breakout.py:191`, `strategies/daytrade/tokyo_range_breakout.py:236`, `strategies/daytrade/tokyo_range_breakout.py:237` |
| 6 (pair-regime fit) | FORCED | 下の Pair-Regime Table 参照。input は ALL だが、実装は `_ENABLED_PAIRS = {"USDJPY"}` のため exact live/shadow behavior は USDJPY only。他 pair は WFA 補助証拠があっても、現コードでは配信対象外であり ALL cell としては forced。 |
| 7 (empirical evidence) | INSUFFICIENT_EVIDENCE | tier-master 入力の 365d BT EV は `—`。local `demo_trades.db` では `entry_type LIKE '%tokyo_range%'` が 0 件で、production sqlite は chart pattern table のみ。既存 WFA artifact には N/WR/t-stat と 1 split IS/OOS があるが、`feedback_partial_quant_trap.md` 基準の PF、WF folds>=3、Bonferroni-adjusted p、Kelly fraction が揃わないため decision-grade evidence は不足。数値は下表。 |

### Pair-Regime Table

| Pair | Fit | Evidence |
|------|-----|----------|
| USDJPY | FIT | 現コード唯一の有効 pair。コードコメントは USD_JPY UP breakout を STABLE_EDGE とし、実装も USDJPY のみ許可する。`strategies/daytrade/tokyo_range_breakout.py:18`, `strategies/daytrade/tokyo_range_breakout.py:19`, `strategies/daytrade/tokyo_range_breakout.py:20`, `strategies/daytrade/tokyo_range_breakout.py:24`, `strategies/daytrade/tokyo_range_breakout.py:25`, `strategies/daytrade/tokyo_range_breakout.py:76`, `strategies/daytrade/tokyo_range_breakout.py:77` |
| EURUSD | FORCED / DISABLED | 既存 WFA の UP OOS は alive だが stable 判定ではない。現コードは `_ENABLED_PAIRS` に含めないため ALL cell としては配信不能。 |
| GBPUSD | FORCED / DISABLED | 既存 WFA の UP は stable だが、現コードは `_ENABLED_PAIRS` に含めない。pair-specific 実装・friction・spread gate が未設計。 |
| EURJPY | FORCED / DISABLED | 既存 WFA の UP は stable だが、現コードは `_ENABLED_PAIRS` に含めない。JPY cross と USDJPY の session/funding/friction 差を吸収する pair-specific gate がない。 |
| GBPJPY | FORCED / DISABLED | 既存 WFA の UP は stable だが、現コードは `_ENABLED_PAIRS` に含めない。ボラティリティが大きく fixed 20/15pip geometry の転用は危険。 |
| Other ALL pairs | FORCED | コード・tier-master・audit DB に pair-specific evidence なし。 |

## Axis 8: failure mode 診断

Tier 2 (Shadow) だが、tier-master の 365d BT EV が `—`、production/demo audit DB では exact entry の蓄積が 0、さらに low-firing audit では USDJPY BUY-only の稀イベントとして NEVER_EVER 側に分類されているため under-evidenced / under-firing cell として failure mode を診断する。破綻軸は Axis 3、Axis 4、Axis 5。Axis 2 の core trigger は thesis と整合するが、bar-close/dedup 契約が strategy 内に閉じておらず、range compression thesis に対して narrow-range 除外と wide-range bonus が逆向きで、exit も breakout continuation 用の trailing geometry ではない。

再設計案は、core trigger を残しつつ、filter と timing と exit を分離して v2 化すること。Trigger は `last_closed_close > tokyo_high + buffer` の bar-close only に寄せ、`buffer = max(spread, 0.05-0.10ATR)` を加える。`(symbol, trade_date, direction)` または `(symbol, trade_date, london_session)` の dedup key を実行層か strategy state に置き、同一 breakout bar / 同一日 2nd entry を禁止する。

Range filter は `MIN_RANGE_PIP` の下限だけでなく compression percentile を使う。少なくとも `Tokyo range <= pair-specific p60/p70` のような上限を設け、`Tokyo range >= 25pip` score bonus は削除または「適度な range」帯への置換を検証する。Stop/TP は fixed 20/15pip 単独をやめ、初期SLを breakout invalidation level に置き、1R 到達後 BE、以後 ATR trailing または London follow window の time stop を採用する。採用前の必要 BT は、pair別 365d 以上、WF folds>=3、Wilson lower、PF、Bonferroni-adjusted p、Kelly fraction を同一 artifact に出す内容で、本監査では実行しない。

## Verdict

`THESIS_VALID_DESIGN_BROKEN`

## Redesign Recommendation

`B`

思想はコードから明確で、core trigger も breakout thesis を捕捉しているため `THESIS_INVALID` ではない。ただし修正点は一箇所ではなく、timing の bar-close / dedup、filter の range compression 再定義、stop/TP の trailing 化、ALL cell と USDJPY-only 実装の整合を同時に扱う必要がある。

コードレベルの想定は、`ctx.entry > _tokyo_high` をそのまま使うのではなく、確定済み signal bar の close が `tokyo_high + buffer` を超えたときだけ signal を作る形にする。`_london_bars.iloc[:-1]` だけに頼る fresh 判定ではなく、strategy/execution side に session-level dedup を持たせる。Range filter は `_tokyo_range_pip < MIN_RANGE_PIP` と `>=25pip bonus` の組み合わせを廃止し、pair-specific percentile で compression と過大 range の両方を制御する。

Exit は `TP_PIP=20`, `SL_PIP=15` の固定幅から、`initial_sl = min(breakout bar low, tokyo_high - buffer)` 相当の invalidation stop と、1R 到達後 BE、ATR trailing、または UTC 13:00 time stop へ変更する。USDJPY 以外を ALL に戻すなら、GBPUSD/EURJPY/GBPJPY は別 cell として PF/Kelly/WF を出してから有効化する。

## Empirical Evidence Table

| Metric | Value | Source |
|--------|-------|--------|
| N (trades) | exact audit DB/demo trades: 0; supplementary existing WFA UP total: 505 across USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY | local `demo_trades.db` query; `knowledge-base/raw/bt-results/tokyo-range-breakout-wfa-2026-04-23.json` |
| Win rate | exact audit DB: INSUFFICIENT_EVIDENCE; supplementary existing WFA UP aggregate: 67.52% (341/505), USD_JPY UP: 72.45% (71/98) | local `demo_trades.db` query; `knowledge-base/raw/bt-results/tokyo-range-breakout-wfa-2026-04-23.json` |
| Wilson lo (95%) | supplementary WFA UP aggregate: 63.32%; USD_JPY UP: 62.88%; not official tier-master/audit DB metric | computed from existing WFA N/WR in `knowledge-base/raw/bt-results/tokyo-range-breakout-wfa-2026-04-23.json` |
| PF | INSUFFICIENT_EVIDENCE: tier-master 365d BT EV is `—`; existing WFA artifact lacks gross win/loss or PF | prompt tier-master input; `knowledge-base/raw/bt-results/tokyo-range-breakout-wfa-2026-04-23.json` |
| WF folds (3+) | INSUFFICIENT_EVIDENCE: existing WFA is one IS/OOS split, not folds>=3 | `knowledge-base/raw/bt-results/tokyo-range-breakout-wfa-2026-04-23.json` |
| Bonferroni-adj p | INSUFFICIENT_EVIDENCE: no multiple-test adjusted p in tier-master or local audit DB | prompt tier-master input; local audit DB search |
| Kelly fraction | INSUFFICIENT_EVIDENCE: PF/payoff distribution absent; code comment mentions Kelly sizing but no audit DB Kelly metric | `strategies/daytrade/tokyo_range_breakout.py:27`; prompt tier-master input; local audit DB search |
