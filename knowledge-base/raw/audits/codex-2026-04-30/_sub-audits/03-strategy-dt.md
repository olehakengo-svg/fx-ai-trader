# Sub 3: 戦略ライブラリ — Daytrade

## Scope
`strategies/base.py`, `strategies/context.py`, `strategies/__init__.py`, `strategies/daytrade/*.py` を監査。比較のため `strategies/scalp/sr_channel_reversal.py`, `strategies/scalp/bb_rsi.py`, `strategies/scalp/squeeze.py`, `strategies/hourly/keltner_squeeze_breakout.py` も参照したが、指摘の主対象は Daytrade 側。

## 1. Bugs Found
| # | Severity | File:Line | Description | Root Cause | Suggested Fix |
|---|----------|-----------|-------------|-----------|--------------|
| 1 | Sev2 | `strategies/daytrade/sr_break_retest.py:175-177,190-239` | `sr_break_retest` が fractal highs と lows を同一クラスタに混ぜ、同じ `sr_level` を BUY/SELL 両方向に使う。支持線/抵抗線の役割情報が消えており、最大損失源のロジックとして不適切。 | `_all_levels = _frac_highs + _frac_lows` で方向情報を捨てている。 | 高値クラスタと安値クラスタを分離し、BUY は resistance break→retest、SELL は support break→retest に限定。 |
| 2 | Sev2 | `strategies/daytrade/sr_fib_confluence.py:24-30,35-48,66-68` | `sr_fib_confluence` は価格水準を計算せず、`layer3` の理由文字列に `"Fib"`/`"OB"` が含まれるだけで発火する。さらに `entry_type` が `"ob_retest"` に化ける。 | シグナル生成が価格ロジックではなく理由テキスト依存。`Candidate.entry_type` も `self.name` 非固定。 | 価格ベースで SR/Fib/OB を再計算するか撤退。少なくとも `entry_type=self.name` を強制。 |
| 3 | Sev2 | `strategies/context.py:115-152,180-205` | `SignalContext` が現在行の `Close/High/Low` をそのまま `entry` や各戦略参照用 `df.iloc[-1]` に渡すが、「確定足のみ」の契約がコード上で保証されていない。多くの戦略が現在足の実体・ヒゲ・高安で判定しており、未確定足なら BT-Live 乖離を起こす。 | `from_df()` が bar finality を表現せず、戦略側も `df.iloc[-1]` を確認バーとして多用。 | `bar_confirmed` を契約に追加するか、戦略評価を常に `[-2]` 確定足基準に統一。 |
| 4 | Sev3 | `strategies/daytrade/london_session_breakout.py:56-60`, `strategies/daytrade/__init__.py:75-77` | `london_session_breakout` は `enabled=True` でエンジンに登録されているが、実装冒頭で常時 `return None`。ライブラリ契約上は「有効戦略」だが実体は死コード。 | 無効化を `enabled=False` ではなく早期 return で隠している。 | `enabled=False` に落とすか、エンジン登録を外す。 |
| 5 | Sev3 | `strategies/daytrade/__init__.py:71-120`, `strategies/daytrade/hmm_regime_filter.py:9-12,86-133` | `HmmRegimeFilter` は Candidate を返さない副作用専用オーバーレイなのに、通常戦略と同じ `evaluate_all()` 契約に混在している。 | 戦略ライブラリが「シグナル生成」と「状態更新」を同じインタフェースで兼用。 | オーバーレイは別パイプラインへ分離。 |

## 2. Structural Issues
1. `dt_sr_channel_reversal` は独立戦略というより `sr_channel_reversal` の劣化コピー。`dt_sr_channel.py:28-39,43-75` と `strategies/scalp/sr_channel_reversal.py:35-48,50-102` は同じ SR/parallel-channel 反発ロジックだが、DT版は `stoch` 確認を削り、近接閾値を `0.3ATR→0.4ATR` に緩め、HTF hard block を足しただけで、ノイズを増やしている。`06b` の `dt_sr_channel_reversal` は `N=17, PF=0.284` と既に負け。

2. `sr_fib_confluence` は `dt_fib_reversal` と機能重複し、さらに独自性が弱い。`dt_fib_reversal.py:23-49,61-73` は実際に Fib 水準へ近接を測るのに対し、`sr_fib_confluence.py:24-39` は他レイヤーの理由文を再利用しているだけ。これは「独立戦略」ではなくラベル再包装。

3. 命名整合が崩れている。`alpha_intraday_seasonality.py` の `name` は `intraday_seasonality` (`alpha_intraday_seasonality.py:38-45`)、`alpha_wick_imbalance.py` は `wick_imbalance_reversion` (`alpha_wick_imbalance.py:49-57`)、`alpha_atr_regime_break.py` は `atr_regime_break` (`alpha_atr_regime_break.py:48-55`) で、`alpha_*` というカテゴリ情報が `entry_type` に残らない。`tokyo_range_breakout.py` もファイル名に対し `name="tokyo_range_breakout_up"` (`tokyo_range_breakout.py:52-56`)。集計・Tier・実績照合で混乱源になる。

4. 静的時間ブロックが Daytrade に広範囲に残っており、`CLAUDE.md` の原則3「静的時間ブロック禁止」に反する。例: `session_time_bias.py:41-49,118-122`, `tokyo_range_breakout.py:58-63,89-90,111-113`, `xs_momentum.py:118-129`, `asia_range_fade_v1.py:51-52,71-73`, `liquidity_sweep.py:493-506`。戦略の生殺与奪が固定時刻依存になっている。

5. 過剰最適化臭の強いハード分岐が散見される。`pd_eurjpy_h20_bbpb3_sell.py:29,50,66` の `hour_utc == 20`、`xs_momentum.py:118-129` の `12<=hour<18`、`tokyo_range_breakout.py:69-70` の固定 `TP=20p/SL=15p` は、セル最適化の可能性が高い。

## 3. Losing Edge Analysis
| Strategy | Cell | N | WR | PF | Wilson Lower | Kelly | 負けの帰属 | 調整案 |
|---|---|---:|---:|---:|---:|---:|---|---|
| `sr_break_retest` | aggregate live | 22 | 27.3% | 0.158 | 0.1315 | -1.4497 | `sr_break_retest.py:175-177,190-239` の方向喪失SR、`MIN_CLUSTERS=1` (`:60`)、`BREAK_MARGIN_ATR=0.05` (`:66`)、`RETEST_ZONE_ATR=0.7` (`:69`) により weak level を広く取りすぎ。signal lag ではなく quality 崩壊。 | 高値/安値クラスタ分離、`MIN_CLUSTERS>=2`、`BREAK_MARGIN>=0.15ATR`、`RETEST_ZONE<=0.35ATR`、break bar に `DI` 一致必須。改善できなければ撤退候補最上位。 |
| `sr_channel_reversal` | aggregate live | 28 | 3.6% | 0.036 | 0.0063 | -0.9575 | 比較対象コード `strategies/scalp/sr_channel_reversal.py:50-102` と DT clone `dt_sr_channel.py:43-75` が同系統。水平線反発を trend/momentum 確認なしで逆張りしており regime mismatch。 | Daytrade 側は独立戦略として残さず、`liquidity_sweep` 型の wick-confirmed MR に統合。単純 bounce 戦略は撤退が妥当。 |
| `sr_fib_confluence` | aggregate live | 33 | 24.2% | 0.438 | 0.1283 | -0.3109 | `sr_fib_confluence.py:24-30` が「理由文字列に Fib/OB があるか」で発火し、`35-48` で方向は `ema_score` 任せ。独立戦略でなく duplicate strategy。 | 価格水準を自前計算できないなら撤退。残すなら `dt_fib_reversal` に吸収し、`entry_type` 汚染 (`:66-68`) を止める。 |
| `bb_squeeze_breakout` | aggregate live | 17 | 5.9% | 0.053 | 0.0105 | -1.0564 | 範囲外だが `strategies/scalp/squeeze.py:19-35,45-60` は「当該足で BB 幅拡大したか」と `%B` だけで発火し、事前圧縮の持続長も prior-range break も見ていない。false breakout の量産。 | スキャルプ版は撤退し、`strategies/hourly/keltner_squeeze_breakout.py:122-197` のように squeeze 持続本数、実体比率、MACD拡大、Keltner外 close を必須化。 |

## 4. Roadmap Alignment
- このスコープで Gate 進行を最も阻害しているのは `sr_break_retest` と `sr_fib_confluence` の負EV継続。特に `sr_break_retest` の `-414.6pip` は aggregate Kelly を直接破壊している。
- 律速要因は `Kelly` と `DD`。ここは「攻める/守る」以前に、負けエッジのロジック純度が低い。
- 加速施策は、`sr_*` 重複群の整理、未確定足契約の明文化、静的時間ブロック戦略の縮退。勝ち筋の拡張より先に、明確な負け筋を止血すべき段階。

## 5. Top 3 Action Items
1. `sr_break_retest` を即時再設計または停止 — Impact: 最大損失源の除去、Kelly改善が最も大きい — Confidence: high
2. `sr_fib_confluence` を `dt_fib_reversal` へ統合し、理由文字列依存を廃止 — Impact: 重複シグナルとラベル汚染を解消 — Confidence: high
3. `SignalContext` に確定足契約を追加し、現在足依存戦略を `[-2]` 基準へ寄せる — Impact: BT-Live 乖離と look-ahead 疑義を同時に低減 — Confidence: med

## 6. Out-of-Scope Findings
- `bb_squeeze_breakout` は Daytrade ではなく `strategies/scalp/squeeze.py` にあり、集計上の大負けはそちらのロジック起因。
- `london_session_breakout` は実質停止中だがライブラリ上は有効戦略として残っており、棚卸し不足の兆候。
- `alpha_*` 系はファイル名と `entry_type` が一致せず、カテゴリ別監査や live attribution を難しくしている。
