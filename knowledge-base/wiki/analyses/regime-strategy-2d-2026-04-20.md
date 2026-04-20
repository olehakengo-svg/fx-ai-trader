# Regime × Strategy 2D Kelly Asymmetry Analysis (2026-04-20)

## TL;DR

| 判定 | 結論 |
|---|---|
| **調査範囲** | 43戦略 (STRATEGY_FAMILY 登録分 + 本番観測分) × 7 regime × 2 direction |
| **データ** | 本番 `/api/demo/trades` LIVE+SHADOW N=786 (closed, post-Fidelity-Cutoff 2026-04-16, XAU除外) |
| **サンプル期間** | 2026-04-16 → 2026-04-20 (≈4.6日, 週末含む) |
| **Gate通過候補** | **0 件** — 厳格 gate (N≥50/cell × ΔWR≥10pp × Bonferroni) を通過する追加戦略は存在しない |
| **新規 REGIME_ADAPTIVE 実装** | **なし (保留)** |
| **判断プロトコル #1 違反リスク** | 4日データでの対策実装は `lesson-reactive-changes` 違反 — **実装せず、観察継続** |

---

## 1. 動機

v9.3 Phase E ([[mtf-regime-validation-2026-04-17]] §E) で `REGIME_ADAPTIVE_FAMILY` が
**2戦略** (`bb_rsi_reversion`, `fib_reversal`) のみ実装済。LIVE ΔWR +2.4pp → +9.3pp (4×) の効果を
確認。**残り41戦略未調査**。

仮説: 他の戦略にも regime × direction 非対称性を示すものがあれば、単一 family 分類が
捉えきれないアルファ源。Phase E 同等 (ΔWR ≥10pp, Bonferroni 有意) を持つ戦略を抽出する。

---

## 2. データ取得

| 項目 | 値 |
|---|---|
| ソース | `https://fx-ai-trader.onrender.com/api/demo/trades?limit=5000&include_shadow=1` |
| 取得時刻 | 2026-04-20 T14:46 UTC |
| 全取引 | 2162 |
| Cutoff 後 (entry_time ≥ 2026-04-16) | 796 |
| XAU除外後 | 796 (XAU は Cutoff 以降 0 件) |
| 約定済 (pnl_pips not null) | 786 |
| Regime ラベル済 | 786 (下記 §3 の retrospective 補完後) |

### 2.1 `mtf_regime` 本番カラム空欄問題

本番 DB の `mtf_regime` カラムは **2026-04-20 以降のみ populated** (N=193)。
`modules/demo_trader.py::_get_mtf_regime` キャッシュ統合が shadow_monitor 起動後の
トレードにしか適用されていない。

**対応**: `research/edge_discovery/mtf_regime_engine.label_mtf()` を使い、
OANDA D1/H4/H1 candles から retrospective にラベル付与 (`/tmp/fx-regime-2d-analysis/run_analysis.py`).
Phase B で validated な同一 pipeline を使用 → 未来参照ゼロ, as-of backward.

### 2.2 Regime 分布 (Cutoff 後)

```
regime             N
range_tight        456
range_wide         167
trend_up_strong    122
trend_up_weak       41
trend_down_weak      0
trend_down_strong    0
uncertain            0
```

**構造的観測**: 週末 + 4日営業日の期間に `trend_down_*` と `uncertain` が **完全ゼロ**。
市場構造が one-sided (range dominant + mild bull) だったため、regime coverage が
全くそろわない。

---

## 3. 手法

### 3.1 2D matrix

各 `(strategy, regime, direction)` cell で:
- `N`: 観測取引数
- `wins`: `pnl_pips > 0` の件数
- `WR = wins / N`
- `mean_pnl`: 平均 PnL (pips)

出力: `/tmp/fx-regime-2d-analysis/matrix_all.csv` (103 cells).

### 3.2 Asymmetry metrics

1. **regime_asymmetry_wr** — 戦略ごと, direction を marginalize した
   `max(WR_regime) − min(WR_regime)`, 各 regime N≥20 要件.
2. **max_direction_swing** — 戦略ごと, regime A と B の
   `(WR_BUY − WR_SELL)` の符号付き差を比較し, 最大と最小の差. Phase E で
   bb_rsi_reversion の "uptrend は TF, downtrend は MR" を検出した指標.

### 3.3 Gate 条件 (Phase E 基準を流用)

1. **N ≥ 50 per (strategy, regime, direction) cell** — 厳格要件
2. **ΔWR ≥ 10pp between regimes (同方向)** — 効果サイズ
3. **Bonferroni α = 0.05 / K** — 多重検定補正
4. **IS/OOS 符号一致** — 時期依存バイアス排除 (今回は単期間なので不適用)
5. **既存 REGIME_ADAPTIVE_FAMILY 非該当** — 差分のみ評価

---

## 4. 結果

### 4.1 Strategy totals (Cutoff 後 N, 上位)

```
ema_trend_scalp             193
bb_rsi_reversion            110
stoch_trend_pullback         65
fib_reversal                 57
bb_squeeze_breakout          55
sr_channel_reversal          42
sr_fib_confluence            41
engulfing_bb                 39
vol_surge_detector           30
macdh_reversal               23
trend_rebound                20
(以下 N<20 のため cell 評価対象外)
```

総戦略数 (Cutoff 後観測): 25. うち N≥20 の戦略: 11. うち N≥50 の戦略: 5.

### 4.2 Asymmetry ranking (N≥20 per cell 緩和基準)

| strategy | n_total | n_qual_cells | regime_asymm_wr | max_dir_swing | in_adaptive | base_family |
|---|---|---|---|---|---|---|
| ema_trend_scalp | 176 | 5 | 0.107 | **0.108** | No | TF |
| bb_rsi_reversion | 78 | 2 | 0.000 | 0.000 | **Yes** | MR |
| bb_squeeze_breakout | 24 | 1 | 0.000 | 0.000 | No | BO |
| stoch_trend_pullback | 50 | 2 | 0.000 | 0.000 | No | TF |

緩和基準 (N≥20) でも **全 4 戦略のうち direction-swing を測定可能なのは 1 戦略のみ** (残り 3 戦略は BUY/SELL cell が同 regime で揃わず比較不能).

### 4.3 Strict gate (N≥50 per cell)

| strategy | n_qual_cells | max_dir_swing | 判定 |
|---|---|---|---|
| ema_trend_scalp | 1 | 0.0 | **単一 cell のみ qualified → regime 間比較不能** |

**Gate 通過: 0 件**

### 4.4 Bonferroni 有意性検定 (Fisher exact, 同方向 regime 間比較)

緩和基準 N≥20 での有効テスト数 K=4:
- α_Bonferroni = 0.05 / 4 = 0.0125
- 最小 p 値: 0.277 (ema_trend_scalp SELL range_wide vs trend_up_strong, ΔWR=15.7pp)

**Bonferroni 有意な cell: 0**. 生 p 値でも 0.05 を下回るものなし.

---

## 5. 個別戦略 diagnostics (top 5 by N)

### 5.1 ema_trend_scalp (N=193, TF base)

```
regime           direction  n   WR      mean_pnl
range_tight      BUY        46  0.239   -1.67
range_tight      SELL       54  0.259   -0.11
range_wide       BUY        17  0.118   -3.66
range_wide       SELL       21  0.143   -2.55
trend_up_strong  BUY        35  0.171   -1.85
trend_up_strong  SELL       20  0.300   -0.62
```

観測: `trend_up_strong` で **SELL WR 30% > BUY 17% (13pp gap)**. TF 戦略なのに強いトレンドで逆張りが勝つ = Phase E で既述の "strong trend = exhaustion" MR signal.

**判定**: これは既存の `strategy_aware_alignment()` が既に処理済:
```python
# mtf_regime_engine alignment rule:
# TF + trend_up_strong + non-JPY → conflict
```
つまり TF BUY は conflict 判定済で gate 後 downgrade 対象. REGIME_ADAPTIVE_FAMILY 追加の必要なし.

### 5.2 bb_rsi_reversion (N=110, REGIME_ADAPTIVE 登録済)

```
regime           direction  n   WR      mean_pnl
range_tight      BUY        31  0.290   -0.75
range_tight      SELL       47  0.234   -2.41
range_wide       BUY         4  0.000   -3.50
range_wide       SELL        7  0.286   -1.97
trend_up_strong  BUY         6  0.833   +4.33
trend_up_strong  SELL       15  0.067   -2.93
```

観測: `trend_up_strong × BUY WR 83% (N=6) vs SELL 6.7% (N=15)` — **76.7pp gap**. Phase E IS データ (tu BUY 55% / SELL 50%) より遥かに強い TF シグナル. しかし N が小さすぎる (BUY N=6).

**判定**: 既存 REGIME_ADAPTIVE 設定 (`trend_up_strong` → TF) と整合. **符号 OOS 一致**. 現状設定で既にアルファを捉えている. 変更不要.

### 5.3 fib_reversal (N=57, REGIME_ADAPTIVE 登録済)

```
regime           direction  n   WR      mean_pnl
range_tight      BUY        19  0.421   -0.03
range_tight      SELL       14  0.071   -3.93
range_wide       BUY         6  0.000   -4.07
range_wide       SELL        6  0.500   +2.08
trend_up_strong  BUY         8  0.125   -2.36
trend_up_strong  SELL        4  0.250   +0.28
```

観測: tu_strong で SELL > BUY (MR-like). 既存 `fib_reversal × trend_up_*` → MR と整合. **符号 OOS 一致**.

### 5.4 stoch_trend_pullback (N=65, TF base)

```
regime           direction  n   WR
range_tight      BUY        24  0.333
range_tight      SELL       26  0.154
range_wide       BUY         6  0.167
range_wide       SELL        7  0.286
trend_up_strong  BUY         1  1.000
trend_up_strong  SELL        1  1.000
```

range_tight で **BUY 33% > SELL 15% (18pp gap)**. ただし N=24/26 小. `trend_up_*` は N=2. **regime-adaptive 候補としては情報不足**.

### 5.5 fib_reversal / sr_channel_reversal / engulfing_bb / vol_surge_detector / macdh_reversal

いずれも N<50/cell. 観測上いくつか大きな direction gap (engulfing_bb × tu_strong BUY 67% vs SELL 0% など) があるが **cell N≤3** で Fisher exact が意味をなさない.

---

## 6. Gate 通過候補: なし

### 6.1 Gate 通過候補リスト

**該当なし**. 以下の複合要因が原因:

1. **Fidelity Cutoff (2026-04-16) ≤ 現在 (2026-04-20) = 4.6 暦日** — `lesson-reactive-changes` の
   "1日データ禁止" に抵触するほど短い.
2. **Regime coverage 欠損** — `trend_down_*`, `uncertain` が 0 件. 方向非対称性を測る
   前提 (両向きの trend regime) が満たされない.
3. **cell N 不足** — 43戦略中, N≥50 cell を 1 つ以上持つのは `ema_trend_scalp` のみ
   (かつ regime 内単一 cell). Bonferroni K=4 で α=0.0125 を下回る p 値ゼロ.

### 6.2 実装した REGIME_ADAPTIVE 新規登録

**なし**.

### 6.3 保留した候補と理由

| 戦略 | 観測方向性 | 保留理由 |
|---|---|---|
| `ema_trend_scalp` | tu_strong × SELL > BUY (13pp) | 既存 `strategy_aware_alignment` が処理済 (TF + tu_strong + non-JPY → conflict). N=55 (BUY+SELL) で Bonferroni 不合格. |
| `stoch_trend_pullback` | range_tight × BUY > SELL (18pp) | range regime に direction-adaptive は Phase E アーキテクチャ外. 機序仮説なし. N=50 でも p > 0.05. |
| `engulfing_bb`, `macdh_reversal`, `vol_surge_detector` | 各種 gap 観測 | cell N≤10 で統計的意味なし. lesson-orb-trap-bt-divergence の短期カーブフィットリスク. |

---

## 7. 判断プロトコル適用

CLAUDE.md §判断プロトコル:

| 問 | 回答 |
|---|---|
| 1. 根拠データ | 4日, 全サンプル N=786, 中央値 N/戦略 ≈ 10. **365日BT or Live N≥30 要件未充足 → 分析のみ** |
| 2. KB参照 | `mtf-regime-validation-2026-04-17.md` (Phase A-E), `lesson-reactive-changes.md`, `lesson-orb-trap-bt-divergence.md`, `strategy_family_map.py` |
| 3. 既存戦略との整合性 | 観測された全ての方向非対称性は既存 `strategy_aware_alignment` か `REGIME_ADAPTIVE_FAMILY` の既定規則と整合. 矛盾なし |
| 4. バグ修正 vs パラメータ変更 | パラメータ変更 (新戦略 family 追加) に該当 → **BT検証後** 必要. 365日 BT で retrospective family-map A/B 検証する pipeline は Phase B で実装済だが, 新規候補はまだ入口 (N足りず) |
| 5. 動機の記録 | データ駆動 (指令タスク) だが, データ自体が判断に必要な基準を満たしていない |

**判定**: **実装せず, 観察継続**. `lesson-reactive-changes` 教訓を遵守.

---

## 8. 並行して発見された運用課題

### 8.1 `mtf_regime` DB populated 率 = 24.5% (193/786)

本番 `mtf_regime` カラムが 2026-04-20 からのトレードにしか書かれていない. shadow_monitor 実装
([[mtf-regime-validation-2026-04-17]] §D) が Phase D A/B routing コミットに伴い enable されたが,
それ以前の backfill がない.

**推奨** (別 task):
- `scripts/backfill_mtf_regime.py` を作成し, 過去トレードを retrospective labeling で埋める
  (本分析で作成した pipeline を再利用).
- Fidelity Cutoff 以降の全トレードに `mtf_regime` / `mtf_d1_label` / `mtf_h4_label` / `mtf_vol_state`
  を注入. 次回の 2D 分析の N を即座に 4-5 倍化できる.

### 8.2 Regime 構造バイアス

Cutoff 後期間が trend_up + range に偏っているため, `trend_down_*` regime での
戦略挙動が全く観測できない. Phase E の fib_reversal `trend_down_*` → TF, bb_rsi_reversion
`trend_down_*` → MR の **OOS 検証すら当面不可能**.

**推奨**: backfill 完了後, Cutoff を遡って 3月 SVB-like bearish 局面を含む期間で再評価.

---

## 9. 次アクション

### 9.1 即時 (本タスクスコープ外, 別 task 推奨)

- [ ] `mtf_regime` backfill スクリプト実装 + 実行 (§8.1)
- [ ] backfill 後 2D matrix 再生成 (N ≈ 1500+ 見込み, cell N≥50 を複数戦略で達成可能性)
- [ ] 拡張 N で Phase E 候補 (bb_rsi/fib) の OOS 符号一致再確認

### 9.2 14日後

- [ ] shadow_monitor 本番蓄積 ≥ N=3000 cutoff でこの分析を再実行
- [ ] その時点で Gate 通過候補があれば REGIME_ADAPTIVE_FAMILY 追加検討 (Phase F?)

### 9.3 30日後

- [ ] Welch t-test (cell-level) で有意差検定
- [ ] IS/OOS 50:50 split で符号一致確認後に gate promotion

---

## 10. 成果物

| ファイル | 内容 |
|---|---|
| `/tmp/fx-regime-2d-analysis/matrix_all.csv` | 103 (strategy, regime, direction) cells |
| `/tmp/fx-regime-2d-analysis/asymmetry.csv` | 緩和基準 N≥20 asymmetry ranking |
| `/tmp/fx-regime-2d-analysis/asymmetry_strict.csv` | 厳格基準 N≥50 asymmetry ranking |
| `/tmp/fx-regime-2d-analysis/summary.json` | 全体統計 |
| `/tmp/fx-regime-2d-analysis/run_analysis.py` | 再現 pipeline (retrospective labeling 含む) |

---

## 11. 結論

**43戦略のうち 41 戦略未調査のアルファソース仮説は, 現時点のデータでは検証不可**.

- 観測期間 4日 = 判断プロトコル #1 違反リスク領域.
- Regime coverage one-sided = 方向非対称性の片側しか見えない.
- cell N 過小 = Bonferroni を一つも通過しない.
- 観測された非対称性は全て既存 `strategy_aware_alignment` / `REGIME_ADAPTIVE_FAMILY` の
  既定規則で処理済 (符号 OOS 一致).

**実装: なし**. **観察継続**. backfill + 14日以上の N 蓄積後に再評価.

これは Phase E の正当性を追認する **null result (good null)**: 既存 2戦略の mapping が
現時点で意味のある差分を残しておらず, v9.3 Phase E マッピングが "まだ有効" であることを示唆.

---

## 12. Backfill 事前宣言 → Pivot 記録 (2026-04-21)

> **Status**: この §12 は 2026-04-21 に事前宣言として追記されたが, 同セッション内で前提が複数箇所破壊され, **当初タスク (REGIME_ADAPTIVE_FAMILY 拡張) は凍結** された. 下記は事前宣言の原文 + pivot 記録として保存 (透明性のため削除しない).
>
> **詳細**: [[lesson-backfill-task-pivot-2026-04-21]] / [[sessions/2026-04-21-session]] Phase 2

### Pivot summary (後追記, 2026-04-21)

1. **Instrument × Regime 完全交絡**: 全候補戦略で (regime, strategy) cell が単一 instrument にロック. 例: macdh × trend_down_strong = 48件全て EUR_USD.
2. **BT-Live 乖離の真因 = 市場 regime 遷移**: 4/16 境界で range_tight 14% → 58% (4x). 全 MR/TF 戦略 -12〜-20pp WR 崩壊.
3. **既存 REGIME_ADAPTIVE mapping は正しい** (P0 validation で全符号一致確認). 損失源は range_tight × MR (mapping override 対象外).
4. **真の優先**: range_tight 止血 + Gate leak 調査. 拡張は複数 regime 遷移観測後に再評価.

### 解凍経路: BT 摩擦モデル改善

現状データ (Live 18日) だけでは R1 期間短・R2 instrument 交絡・R3 市場遷移により拡張不可. 3-6ヶ月待ちを回避する唯一の fast path は **BT を信頼できる alternative source にする** こと = BT 摩擦モデル改善.

**最小修正 (Tier 1, 半日)**: mode×pair (DT/Scalp × 6pair = 12 cell) の摩擦係数テーブル化. 既存 BT runner の uniform 定数を pair/mode lookup に置換. 成功基準は bb_rsi/fib_reversal の BT-Live 乖離が -36pp → -15pp 以下.

Tier 1 成功時点で BT 2D scan が regime-confound-free な分析基盤になり, 本件 (REGIME_ADAPTIVE_FAMILY 拡張) を再評価できる. 詳細は [[sessions/2026-04-21-session]] §P0'.

---

### 事前宣言原文 (参考 / 下記)

**目的**: `mtf_regime` 未充当の 1969件 (entry_time < 2026-04-20) を
`mtf_regime_engine.label_mtf()` で retrospective 充当し, 2D 行列の N と regime 多様性を拡張する. 事後的な p-hacking を防ぐため, 基準を **実行前に** 固定.

### 12.1 事前検証 (Step 1-2) 結果
- **Live labeler 自己照合**: N=193 (2026-04-20) で offline vs live 100% 一致. As-of alignment (shift+backward merge) が look-ahead なく再現することを確認.
- **Base rate 推定** (全 2127 trades / 6 instruments, `/tmp/step2_regime_coverage.json`):
  - trend_down_strong: 213件 (**新規** — 現状 0)
  - trend_down_weak: **0件** — 18日間の相場で出現せず
  - range_tight/range_wide/trend_up_*: 既存の 5〜10x 拡張
  - uncertain: 147件

### 12.2 Gate 基準 (Phase E §3.3 を継承し, Backfill 実行前に固定)

| # | 基準 | 値 |
|---|------|-----|
| 1 | Cell 最小 N | **N ≥ 50** per (strategy, regime, direction) |
| 2 | 効果サイズ | **ΔWR ≥ 10pp** between regimes (同方向) |
| 3 | 多重検定補正 | **Bonferroni α = 0.05 / K** (K = 評価戦略数) |
| 4 | IS/OOS 符号一致 | 両期間で `(WR_regime_A − WR_regime_B)` 同符号 **かつ** 各側 p < 0.1 |
| 5 | 既存 REGIME_ADAPTIVE_FAMILY 非該当 | `bb_rsi_reversion`, `fib_reversal` は差分評価対象から除外 |

**IS/OOS 分割点** (backfill 完了後適用):
- **IS**: 2026-04-02 〜 2026-04-15 (pre-Fidelity Cutoff, N ≈ 1600, 低 fidelity 疑い)
- **OOS**: 2026-04-16 〜 2026-04-20 (post-Fidelity Cutoff, N ≈ 527, 高 fidelity)

### 12.3 事前除外項目

- **`trend_down_weak`**: N=0 のため評価不可. 本 backfill サイクルでは評価対象外 (明示的に pre-declared — 後から理由をこじつけることの禁止).
- **`uncertain`**: 既存方針どおり regime-adaptive 判定の外側. 差分評価しない.

### 12.4 事前優先候補 (2D 再スキャン後の検証対象)

base rate 推定に基づく, **cell N ≥ 30 を複数 regime で満たす既存 REGIME_ADAPTIVE_FAMILY 非該当戦略**:

| 優先度 | 戦略 | 観察済 cell N (推定) |
|--------|------|---------------------|
| **1** | `macdh_reversal` | trend_down_strong 48, trend_up_weak 40, range_tight 19 |
| 2 | `sr_fib_confluence` | trend_up_weak 37, trend_down_strong 25 (境界), range_wide 25 |
| 3 | `ema_trend_scalp` | range_wide 88, range_tight 108, trend_up_strong 55 (down 不在) |

**第一候補 macdh_reversal** が Gate 基準を通過しない場合, 本 backfill サイクルで新規 REGIME_ADAPTIVE_FAMILY 追加は行わない. これも事前宣言 — 候補を後から差し替えない.

### 12.5 実装フロー

1. `scripts/backfill_mtf_regime.py` を実装 (SQL UPDATE 出力モード — 本番 DB の write 経路は別途合意).
2. 本番 DB にバックフィル適用 (承認後).
3. 2D 再スキャン実行 → Gate 判定.
4. 通過すれば `research/edge_discovery/strategy_family_map.py` に候補追加 PR (同時に `tests/test_strategy_family_map.py`, `tools/tier_integrity_check.py`, `tools/strategies_drift_check.py` で検証).
5. 通過しなければ **何も変更しない** (good null の維持).

**宣言者**: Claude (quant mode), 2026-04-21, pre-backfill.
