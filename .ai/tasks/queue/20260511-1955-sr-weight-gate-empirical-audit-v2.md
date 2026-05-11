---
id: 20260511-1955-sr-weight-gate-empirical-audit-v2
title: "[SR-Redesign] Weight-Gate Empirical Audit v2 — touch_count × HTF × magnitude で 5 NULL 戦略の reborn 可能性を実測"
owner: codex
status: queued
priority: P1
created_at: 2026-05-11T19:55:00+0900
roadmap_gate: "SR-weight Phase 2 BT で 5/6 戦略が NULL になった原因を実装監査で確定 (誰も touch_count を gate に使っていない)。Phase 3 (Live shadow 再開) 前に weight gate を入れた redesign が edge を産むかを実測検証する。"
rule: pre-reg
related:
  - modules/sr_detector.py
  - modules/indicators.py
  - strategies/daytrade/sr_anti_hunt_bounce.py
  - strategies/daytrade/sr_break_retest.py
  - strategies/daytrade/sr_fib_confluence.py
  - strategies/daytrade/sr_liquidity_grab.py
  - strategies/scalp/sr_channel_reversal.py
  - data/cache/massive/USD_JPY_15m.parquet
  - data/cache/massive/EUR_USD_15m.parquet
  - data/cache/massive/GBP_USD_15m.parquet
  - data/cache/massive/EUR_JPY_15m.parquet
  - data/cache/massive/GBP_JPY_15m.parquet
---

# 0. 背景 (司令塔監査 2026-05-11)

## 0.1 SR-weight Phase 2 結果 (確定)
- BT 365d MASSIVE 4942 events
- **`sr_anti_hunt_bounce` のみ BH FDR survivor** (trend p=0.0034, N=594)
- 残り 5 戦略 (`sr_break_retest` / `sr_fib_confluence` / `sr_liquidity_grab` / `sr_channel_reversal` / 旧 `dual_sr_bounce`) は NULL

## 0.2 実装監査 (司令塔 2026-05-11)
**結論: 5 NULL 戦略の誰も touch_count を gate に使っていない。**

| 戦略 | level 取得 | 致命的 line |
|---|---|---|
| `sr_anti_hunt_bounce` ⭐survivor | `ctx.sr_levels` | sr_anti_hunt_bounce.py:80-87 (proximity 最小のみ。`sr_weighted_levels` は sr_meta tracking 用のみ) |
| `sr_break_retest` | **独自 Fractal** | sr_break_retest.py:61 `MIN_CLUSTERS = 1  # 単一フラクタルも有効SR` ← smoking gun |
| `sr_fib_confluence` | layer3 Fib/OB reasons | sr_fib_confluence.py:46-47 (文字列マッチのみ) |
| `sr_liquidity_grab` | `ctx.sr_levels` | sr_liquidity_grab.py:51-59 (proximity 最小のみ) |
| `sr_channel_reversal` | `ctx.sr_levels` + channel | sr_channel_reversal.py:64-65 (proximity のみ) |

→ `sr_detector.py` (modules/sr_detector.py:120 `detect_sr_levels`, :77 `score_obviousness`) は touch_count / round / age を加重した obviousness score を提供しているが、戦略側で gate に使っているところは皆無。これが NULL の主因仮説。

## 0.3 OANDA 公式 (https://www.oanda.jp/lab-education/technical_analysis/dow-theory/fx_horizon/) ギャップ
- 🔴 **HTF (D1/W1) level 不在** — 自TF 15m のみで detect。週足・日足の水平線が最も意識される (記事原文) のに注入無し
- 🔴 **「水平線は帯」概念欠如** — HTF level は atr_d1 × K の広い band で扱うべき
- 🔴 **Multi-source weight 合成不在** — 自TF touch + HTF touch + round + magnitude の独立 source を合成
- 🟠 **Touch independence 不足** — bar 単位 raw count はコンソリで過大評価
- 🟠 **Rejection magnitude 未計測** — 跳ね返し wick size の ATR 比

# 1. 目的

過去 365d MASSIVE データで 5 SR 戦略 (survivor 含む) について、weight gate (touch_count + HTF + magnitude) を入れた場合の bucket 別 EV/WR/Wilson_lo を実測し、**reborn verdict** を出す。

**reborn verdict**:
- `REBORN_HEAVY`: composite weight 上位 quintile かつ HTF source あり bucket で Wilson_lo>0.50 & EV>0 (Bonferroni m=5 補正後)
- `PARTIAL`: heavy bucket の一部のみ edge
- `DEAD`: heavy bucket でも edge 無し → 思想再検討

# 2. データ & 期間

**データソース (絶対遵守 — Yahoo 禁止)**:
- `data/cache/massive/{USD_JPY,EUR_USD,GBP_USD,EUR_JPY,GBP_JPY}_15m.parquet` (own TF)
- `data/cache/massive/{USD_JPY,EUR_USD,GBP_USD,EUR_JPY,GBP_JPY}_1h.parquet` (D1/W1 resample 用)
- 期間: 直近 365d (parquet 末尾から)

**resampling 仕様**:
- D1 = 1h を `df.resample('1D').agg({'Open':'first','High':'max','Low':'min','Close':'last'})`
- W1 = 1h を `df.resample('1W').agg(...)` (週末は欠損許容)

# 3. 仕様

## 3.1 weight gate ライブラリ (新規 `tools/sr_weight_gate_audit_v2.py`)

```python
# モジュール構造 (新規ファイル)
# tools/sr_weight_gate_audit_v2.py
#   - load_data(symbol, tf) -> pd.DataFrame  # massive parquet 読込
#   - resample_htf(df_1h, freq) -> pd.DataFrame  # D1/W1 生成
#   - detect_sr_levels_with_weight(df, htf_df_d1, htf_df_w1, tolerance_pip, min_touches) -> list[dict]
#     各 level に composite_weight / own_touch / d1_touch / w1_touch /
#     round_score / magnitude_score / distinct_touch_events を付与
#   - run_strategy_bt(strategy_name, df, levels) -> pd.DataFrame  # signal/pnl 記録
#   - bucket_stats(signals, weight_col, quintiles=5) -> pd.DataFrame
#   - main(): 5 戦略 × 5 majors を全走、報告書出力
```

## 3.2 composite weight 定義 (Wave 1 primary、固定)

```python
def composite_weight(level_meta: dict) -> float:
    """
    level_meta keys:
      own_touch: int  # 自TF 15m での distinct touch events
      d1_touch: int   # D1 での distinct touch events
      w1_touch: int   # W1 での distinct touch events
      round_score: float in [0,1]  # is_near_round() の連続化
      magnitude_score: float in [0,1]  # median rejection wick / ATR (clip 0-1)
    """
    return (
        1.0 * level_meta["own_touch"] +
        3.0 * level_meta["d1_touch"] +
        5.0 * level_meta["w1_touch"] +
        2.0 * level_meta["round_score"] +
        1.5 * level_meta["magnitude_score"]
    )
```

**Wave 1 primary threshold**: `composite_weight >= 5.0` を heavy 扱い (post-hoc selection 罠回避のため固定。exploratory として 3.0/4.0/6.0/8.0 を別ラベルで併走可)。

## 3.3 distinct touch events (touch independence)

```python
def count_distinct_touches(df, level, tolerance, min_gap_bars=5):
    """連続して触れている bar を 1 event に統合。

    Algorithm:
      1. df 各 bar について |close - level| <= tolerance または
         (low <= level <= high) を 'touched' とマーク
      2. 連続 touched 群を 1 event とする
      3. event 間の bar 数が min_gap_bars 未満なら統合
    Returns: int (distinct event count)
    """
```

## 3.4 rejection magnitude

```python
def median_rejection_size(df, level, tolerance, atr_series):
    """各 touch event での max wick excursion / ATR の中央値。

    Returns: float (clip to [0, 2.0])
    """
```

## 3.5 HTF level 検出

own TF detection と同じ `detect_sr_levels()` を D1 / W1 candle で走らせる:
- D1: `min_touches=2`, `tolerance_pip = atr_d1 * 0.3 / pip_size`
- W1: `min_touches=2`, `tolerance_pip = atr_w1 * 0.3 / pip_size`

own TF level と HTF level を **price-match** (`abs(own.price - htf.price) <= atr_d1 * 0.5`) して、own level の `d1_touch` / `w1_touch` に投影。

## 3.6 strategy BT 実行 (重要 — シグナル収集が主目的)

各戦略の **既存 evaluate() を変更しない** で BT mode 実行。各シグナルについて以下を記録:
- 既存 sr_meta (level price, distance_atr)
- 新規拡張メタ: own_touch / d1_touch / w1_touch / round_score / magnitude_score / composite_weight / distinct_touch
- exit pnl_pip / win (15m bar の 12 本以内 SL/TP hit or time-out)

**注意**: 戦略の現行ロジックを変更しない (Wave 1 は audit only)。weight gate は **post-hoc bucket 分析** で疑似的に効果検証する。

## 3.7 統計プロトコル (pre-registered)

- Primary hypothesis (各戦略 H0): `composite_weight >= 5.0` bucket で EV<=0
- Test: bucket EV と全体 EV の差を bootstrap (10000 resamples) で 95% CI 算出
- Family-wise correction: Bonferroni m=5 (5 戦略の同時 H0)、α=0.01
- Wilson_lo for WR: 95% lower bound、Bonferroni m=5 補正後 α=0.01
- 単一年 (例 2024) WR>=90% に集中している場合は flag
- post-hoc bucket selection 罠回避: primary threshold は `composite_weight >= 5.0` のみで pre-reg、他 quintile / 3.0/4.0/6.0/8.0 は exploratory ラベル

# 4. 出力

## 4.1 報告書 `reports/sr_weight_gate_audit_v2_<date>.md`

```markdown
# SR Weight Gate Empirical Audit v2

## Summary
| Strategy | N total | N heavy | WR all | WR heavy | EV all | EV heavy | Wilson_lo (heavy, Bonf) | Verdict |
|---|---|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce | ... | ... | ... | ... | ... | ... | ... | REBORN_HEAVY / PARTIAL / DEAD |
| sr_break_retest | ... | ... | ... | ... | ... | ... | ... | ... |
| sr_fib_confluence | ... | ... | ... | ... | ... | ... | ... | ... |
| sr_liquidity_grab | ... | ... | ... | ... | ... | ... | ... | ... |
| sr_channel_reversal | ... | ... | ... | ... | ... | ... | ... | ... |

## Per-Strategy Details
### sr_anti_hunt_bounce
- composite_weight quintile bucket 統計表 (Q1 lightest → Q5 heaviest)
- HTF source 別 (none / D1 only / W1 only / D1+W1)
- own_touch bucket 別 (1, 2, 3, 4-5, 6+)
- magnitude quartile 別
- 単一年集中チェック
- **Redesign 仕様案** (gate threshold / family clarification / removed conditions)
...

## Statistical Discipline
- Pre-registered primary threshold: composite_weight >= 5.0
- Exploratory thresholds: [3.0, 4.0, 6.0, 8.0]  # 別表に分離
- Bonferroni m=5, α=0.01
- Bootstrap CI: 10000 resamples
```

## 4.2 raw データ `raw/audits/sr_weight_gate_v2_<date>.parquet`

per-signal レコード (col: timestamp, symbol, strategy, signal, entry, sl, tp, own_touch, d1_touch, w1_touch, round_score, magnitude_score, composite_weight, distinct_touch, pnl_pip, win, exit_reason, year)

## 4.3 (オプション) 戦略別 redesign spec drafts `docs/sr_redesign_drafts/{strategy}_v1.md`

Verdict が REBORN_HEAVY / PARTIAL なら、weight gate を実装する **redesign 草案** を 1 ファイル / 戦略で出力 (どこの条件式に gate を入れるかの行レベル diff 含む)。

# 5. テスト要件 (Codex mock-only テスト罠回避)

**unit tests** (mock 可):
- `count_distinct_touches`: 既知パターン (3 連続 bar 1 event, gap 6 bar で 2 event)
- `composite_weight`: 既知 input → 期待値
- `median_rejection_size`: 単純 wick で median 一致

**integration tests** (mock 禁止、実 parquet 必須):
- USD_JPY 15m parquet で `detect_sr_levels_with_weight` が ≥1 level 返す
- 5 戦略全部について BT が完走しシグナル 1+ 件返す
- `composite_weight >= 5.0` の signal が 全 N の 1-30% に収まる (sanity range)
- 報告書 markdown が生成される

# 6. 不変条件 (絶対遵守)

- ✋ **戦略の evaluate() コードを変更しない** (Wave 1 は audit only)
- ✋ **新規ファイル限定**: `tools/sr_weight_gate_audit_v2.py` のみ追加。既存ファイル編集は無し
- ✋ Yahoo データ禁止、`data/cache/massive/*.parquet` のみ
- ✋ post-hoc threshold selection 禁止 — primary は `composite_weight >= 5.0` で pre-reg
- ✋ stash leak 禁止 — final.md は `git log/diff/stash list` で必ず実 verify、変更が main に着地していることを確認

# 7. 完了条件

1. `tools/sr_weight_gate_audit_v2.py` 実装、`python3 tools/sr_weight_gate_audit_v2.py --all` で完走
2. unit tests + integration tests 全 PASS
3. `reports/sr_weight_gate_audit_v2_<date>.md` 生成 (上記スキーマ準拠)
4. `raw/audits/sr_weight_gate_v2_<date>.parquet` 生成
5. PR タイトル: `feat(sr-redesign): empirical weight-gate audit v2 — 5 NULL strategy reborn verdict`
6. PR description に Summary 表を貼る (Verdict 列含む)
7. final.md に **`git log --oneline -5` の出力をコピペ**、**`git stash list` が空**、**`git status` clean** を実 verify した証跡を記載

# 8. 後続タスクとの接続 (本タスク完了後)

Verdict 別 next action:
- REBORN_HEAVY ≥ 2 戦略 → 個別 redesign 実装タスクを順次投入 (司令塔が判断)
- ALL DEAD → 思想再検討タスク (例: rejection magnitude が主軸ではないか / TP geometry の問題か)
- 一部 REBORN_HEAVY → 段階的に redesign + 残りは catalog §B-2 (academic only) 検討
