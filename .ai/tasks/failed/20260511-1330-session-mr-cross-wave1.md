---
id: 20260511-1330-session-mr-cross-wave1
title: "[W6-MR-Cross Wave 1] Session-boundary cross-pair Mean Reversion 戦略族 — BT feasibility"
owner: codex
status: queued
priority: P1
created_at: 2026-05-11T13:30:00+0900
roadmap_gate: "Gate 1 (Aggregate Kelly > 0) — uncorrelated edge を新カテゴリで投入し Live overall edge NEGATIVE を補完"
rule: R1
related:
  - knowledge-base/wiki/syntheses/roadmap-v2.1.md
  - data/cache/massive/
  - modules/demo_trader.py
  - modules/strategies/ (signal function 追加先)
  - knowledge-base/raw/bt-results/
external_evidence:
  - "Night Hunter Pro (Mishchenko): 2020/10〜 verified live, EURCHF/EURGBP, アジア時間低ボラ MR, 固定 SL, NO Martingale"
  - "Evening Scalper Pro (Mishchenko): 2021/1〜 verified live, 8クロス, GMT 19-23 MR window"
  - "SFE Night Scalper: 4年+ live, NY 終わり〜アジア序盤 MR, Myfxbook 公開"
  - "Waka Waka EA: 2018〜 7年+ live, EURNZD/AUDNZD/AUDCAD クラスのクロス・マイナー"
  - "外部調査レポート: 長寿 EA の最大派閥は『時間帯特化 cross-pair MR』、indicator-based MR (我々の BB-RSI MR) は短寿傾向"
---

# 0. 背景

## 0.1 司令塔監査 2026-05-11 13:00 の認識
- fx-ai-trader Live overall edge は **NEGATIVE** (raw Kelly ~ -0.23, DD 47.22%, ruin 3.8%)
- W4-EDA (2026-05-05) で 76 戦略中 **91% が「思想は正だが設計が誤」**、`THESIS_INVALID=0`
- 既存 MR は indicator-based (`bb_rsi_reversion`, `engulfing_bb`, `dt_sr_channel_reversal` 等) で **時間帯×クロス・マイナーの構造的 MR** カテゴリが portfolio に不在

## 0.2 外部 winning EA 調査 (2026-05-11) の結論
- 検証済み 4-7年級長寿 EA の最大派閥は「NY晩〜アジア時間の cross-pair Mean Reversion」族 (Night Hunter Pro / Evening Scalper Pro / SFE Night Scalper / Waka Waka EA)
- 構造的エッジの源泉: **アジア時間 (GMT 19-02) の低ボラ・レンジ志向 × クロス・マイナーの reversion 傾向**
- indicator-based MR と異なり、時間帯境界 + pair-class が edge の core
- **我々のシステムに完全に不在のカテゴリ**

## 0.3 データ事前監査 (Codex 着手前に司令塔確認済)
`data/cache/massive/` を 2026-05-11 13:30 時点で確認:
- ✅ `EUR_GBP_5m.parquet` 利用可能
- ❌ `EUR_NZD_5m.parquet` 不在 (1h/15m も不在)
- ❌ `AUD_NZD_5m.parquet` 不在
- ❌ `AUD_CAD_5m.parquet` 不在
- ❌ `NZD_CAD_5m.parquet` 不在

→ MASSIVE 経由データ取得が Wave 1 の前提条件。**Yahoo データは絶対に使わない** (feedback: `bt-must-use-massive`)

---

# 1. 仮説 (Hypothesis)

**H1 (Primary)**: NY晩 (GMT 19:00-23:00) または Tokyo Open 帯 (GMT 22:00-02:00) に発生する cross-minor の volatility-normalized レンジ逸脱は、365日 M5 BT で Wilson lower > 0.50 / PF >= 1.15 / post-friction EV > 0.10pip の安定 MR エッジを示す。

**H2 (Secondary)**: 同じパラメータでも window × pair の組み合わせで edge が大きく異なる (Wave 1 の主目的はこの heterogeneity を測ること)。

**Null (帰無)**: 5 ペア × 2 window = 10 cell で Bonferroni m=10 (α=0.005) 後に Wilson lower > 0.50 を満たす cell が 0 個。

何が正しければロードマップが前進するか:
- H1 が >=2 cells で立てば Wave 2 (Shadow 投入) へ。Gate 1 への uncorrelated edge 候補となる
- 0 cells で立てば W4 redesign queue 側に資源を戻し、本族は academic only (Tier 3) で記録

---

# 2. 対象データ・分離

| 種別 | 用途 |
|---|---|
| **BT (MASSIVE 365日 M5)** | Wave 1 の唯一の評価対象。他データソース禁止 |
| Shadow / Live / OANDA | **Wave 1 では一切使わない** (Wave 2 以降の話) |

### データ分離の徹底
- BT結果は `knowledge-base/raw/bt-results/session-mr-cross-wave1-2026-05-11.json` に隔離
- Live `is_shadow=0` テーブルとの混入は **絶対禁止** (feedback: `live-shadow-separation`)
- 既存 Tier 1 LIVE 戦略 (`session_time_bias` 等) との logic 重複を確認、被ったら distinct rule で分離

---

# 3. 仕様

## 3.1 Phase A: MASSIVE データ ingestion (前提条件)

対象ペア・TF:

| Pair | TF | 期間 |
|---|---|---|
| EUR_NZD | 5m, 1h | 直近 365日 + 30日 warmup (合計 395日) |
| AUD_NZD | 5m, 1h | 同上 |
| AUD_CAD | 5m, 1h | 同上 |
| NZD_CAD | 5m, 1h | 同上 |
| EUR_GBP | (既存利用) | — |

実装:
- `tools/fetch_massive_data.py --pair EUR_NZD --tf 5m --days 395 --out data/cache/massive/EUR_NZD_5m.parquet` 等 (既存 fetcher のフラグに合わせる。なければ最小実装を追加)
- fetch 完了後 audit json (`{pair}_{tf}.audit.json`) を生成 (rows, start, end, gap_count, completeness%)
- **Rule 1 data quality gate**: completeness >= 95% (W3-4 の GBPJPY M5 4.09% blocker と同じ failure mode を回避)。下回ったペアは **その cell を Wave 1 から除外** し、レポートに記録

## 3.2 Phase B: 戦略実装 (signal function)

新規 signal 関数: `modules/strategies/session_mr_cross.py::signal_session_mr_cross(df, params)`

パラメトリック設計 (10 cell すべて同一実装、cell 差は params のみ):

```python
params = {
  "pair": "EUR_NZD",            # 5 ペア
  "window": "NY_LATE" | "TOKYO_OPEN",  # 2 window
  "lookback_bars": 20,           # M5 で 100 分
  "fade_quantile": 0.10,         # 直近 lookback の low/high 10%-90% を境界とする
  "atr_period": 14,
  "sl_atr_mult": 1.5,
  "tp_atr_mult": 0.5,            # アジア MR の典型 R:R 0.33 (WR で稼ぐ前提)
  "max_hold_bars": 24,           # 2時間。window 終端以前に強制 close
  "entry_cost_pips": 0.6         # 既存 friction model 経由
}
```

Window 定義 (UTC):
- `NY_LATE`: 19:00 <= UTC < 23:00 (4h)
- `TOKYO_OPEN`: 22:00 <= UTC < 02:00 翌日 (4h)

シグナルロジック (擬似コード):
```
bar_close = df.iloc[i]
if not in_window(bar_close.ts, params.window): return None

low_q  = quantile(low [i-lookback:i], fade_quantile)
high_q = quantile(high[i-lookback:i], 1 - fade_quantile)
atr    = ATR(df, atr_period).iloc[i]

if bar_close.close < low_q:   side = "BUY"
elif bar_close.close > high_q: side = "SELL"
else: return None

sl = bar_close.close - side_sign * sl_atr_mult * atr
tp = bar_close.close + side_sign * tp_atr_mult * atr
exit_deadline = bar_close.ts + max_hold_bars * 5min  # window 跨いでも保有上限
return Signal(side, entry=next_bar_open, sl, tp, deadline)
```

**重要 — カーブフィッティング防止**:
- パラメータは上記値で **固定**。Wave 1 で grid search 禁止
- ATR/lookback/fade_quantile を tune したくなったら Wave 2 以降の話

## 3.3 Phase C: BT 実行

- データソース: Phase A で確保した MASSIVE M5 parquet (1h は ATR/quantile 補助用に optional)
- 期間: 直近 365 日 (warmup 30 日除く)
- 摩擦: 既存 friction model (`modules/friction.py`) を使う。spread + slippage を **必ず控除**
- `backtest_mode=True` で本番 signal 関数経由 (CLAUDE.md 規律)

10 cell 並列:

| Cell | Pair | Window |
|---|---|---|
| C1 | EUR_NZD | NY_LATE |
| C2 | EUR_NZD | TOKYO_OPEN |
| C3 | AUD_NZD | NY_LATE |
| C4 | AUD_NZD | TOKYO_OPEN |
| C5 | AUD_CAD | NY_LATE |
| C6 | AUD_CAD | TOKYO_OPEN |
| C7 | NZD_CAD | NY_LATE |
| C8 | NZD_CAD | TOKYO_OPEN |
| C9 | EUR_GBP | NY_LATE |
| C10 | EUR_GBP | TOKYO_OPEN |

## 3.4 Phase D: 統計評価

各 cell について算出:
- N (取引数)
- WR (win rate)
- EV (pip/trade, post-friction)
- PF (profit factor)
- Wilson 95% lower (WR の片側 LCB)
- Bonferroni 調整 p (m=10, two-sided)
- Walk-forward (4-fold, 各 fold で EV と WR の符号一致確認)

集計レポート: `knowledge-base/raw/bt-results/session-mr-cross-wave1-2026-05-11.md` (人読み) + `.json` (機械可読)

---

# 4. ACCEPT / NEEDS_MORE_EVIDENCE / REJECT 境界

各 cell の判定 (Bonferroni α=0.005):

## ACCEPT (Wave 2 shadow 投入候補)
**すべて満たす**:
- N >= 30
- Wilson lower (WR) > 0.50
- post-friction EV > 0.10 pip/trade
- PF >= 1.15
- WF 4-fold で EV 符号一致 fold >= 3

## NEEDS_MORE_EVIDENCE (Wave 1 を 730 日へ延長 or データ補強)
- N >= 30
- PF >= 1.10
- Wilson lower (WR) >= 0.45 (border)
- EV >= 0 (post-friction)

## REJECT
上記いずれも満たさない、または `N < 30` で WF fold で符号反転が 2 以上。

## Wave 1 全体 verdict

| Wave 1 verdict | 条件 |
|---|---|
| **Wave 2 GO** | ACCEPT cell >= 2 (Bonferroni 後)、互いに independent (window or pair が異なる) |
| **Wave 1 延長 (NEEDS_MORE_EVIDENCE)** | ACCEPT 1 cell + NEEDS_MORE 1 cell 以上 |
| **REJECT (Wave 1 で打ち切り)** | 上記いずれも非該当 |

REJECT 時の処理: 本族を W4 redesign queue に投入せず、`knowledge-base/wiki/lessons/lesson-session-mr-cross-rejection-2026-05-11.md` にて null result を記録し academic only Tier 3 にカテゴライズ。

---

# 5. 月利100%ロードマップへの寄与

**進める Gate**: Gate 1 (Aggregate Kelly > 0) 突破経路。

| シナリオ | 寄与 |
|---|---|
| Wave 2 GO | 既存 Tier 1 LIVE と低相関の新エッジ (時間帯+pair-class) を shadow 投入 → Gate 1 突破の独立寄与 |
| Wave 1 延長 | 寄与は遅延するが、棄却ではなく続行価値あり |
| REJECT | Gate 1 への直接寄与なし。ただし「indicator-based MR ではなく構造特性ベース MR の null result」という設計知見を獲得し、W4 redesign の方向性決定に寄与 |

---

# 6. 検証コマンド (Codex が実行)

```bash
# 1. データ ingestion 完了確認
ls -la data/cache/massive/EUR_NZD_5m.parquet data/cache/massive/AUD_NZD_5m.parquet \
       data/cache/massive/AUD_CAD_5m.parquet data/cache/massive/NZD_CAD_5m.parquet
cat data/cache/massive/{EUR_NZD,AUD_NZD,AUD_CAD,NZD_CAD}_5m.audit.json

# 2. signal 関数の unit test
python3 -m pytest tests/test_session_mr_cross.py -x -q

# 3. 既存テスト regression
python3 -m pytest tests/ -x -q

# 4. BT 実行
python3 scripts/run_session_mr_cross_wave1_bt.py \
  --pairs EUR_NZD AUD_NZD AUD_CAD NZD_CAD EUR_GBP \
  --windows NY_LATE TOKYO_OPEN \
  --days 365 \
  --out knowledge-base/raw/bt-results/session-mr-cross-wave1-2026-05-11

# 5. 統計レポートの sanity
python3 tools/sanity_check_bt_report.py \
  knowledge-base/raw/bt-results/session-mr-cross-wave1-2026-05-11.json
```

---

# 7. 受け入れ条件 (Codex 完了報告に必須)

Codex が `status: completed` で返す前に以下を **すべて満たすこと**:

1. `data/cache/massive/{EUR_NZD,AUD_NZD,AUD_CAD,NZD_CAD}_5m.parquet` が存在、completeness >= 95%
2. `modules/strategies/session_mr_cross.py` が新規追加、signal 関数とそのテストが green
3. `tests/test_session_mr_cross.py` が >= 6 ケース (boundary / signal / SL/TP / window フィルタ / no-signal / friction)
4. `knowledge-base/raw/bt-results/session-mr-cross-wave1-2026-05-11.{md,json}` が生成
5. 各 cell について N/WR/EV/PF/Wilson/Bonf-p/WF 4-fold が記載
6. Wave 1 全体 verdict (Wave 2 GO / 延長 / REJECT) が明示
7. 既存 `python3 -m pytest tests/ -x -q` が green
8. `python3 scripts/check.py` が green
9. Codex は **commit するが push しない**。司令塔 (Claude) のレビューを待つ

未達なら `status: changes_requested` でレポートし司令塔に返却。

---

# 8. 禁止事項

- **本番 OANDA 口座 / API キーへのアクセス禁止** (Wave 1 は BT のみ)
- **`.env` / `data/oanda.db` (Live) への書き込み禁止**
- **`modules/demo_trader.py` の既存戦略ロジック変更禁止** (signal 関数は新規追加のみ、register は Wave 2 以降)
- **Yahoo データの使用禁止** (feedback: `bt-must-use-massive`)
- **既存未コミット変更を上書きしない** (`git status` で確認、conflict は abort)
- **Live `is_shadow=0` テーブルへのクエリ禁止** (Wave 1 は BT のみ)
- **既存 ELITE_LIVE / Tier 1 戦略の demote / promote 禁止** (R1 task はこの task に閉じる)
- **XAU データの利用禁止** (feedback: `exclude-xau`)
- **Bonferroni / Wilson の事後緩和禁止** (cell 数 m=10 で fix、event 中の m 削減は curve fitting)

---

# 9. 完了後の司令塔アクション (参考)

Wave 1 verdict 受領後、司令塔が判断:
- **Wave 2 GO**: Shadow 投入 spec を別 task で起草 (Tier promotion gate / lot / monitoring)
- **延長**: 730日 BT or データ補強 task を起草
- **REJECT**: lesson markdown を作成、tier-master と W4-EDA カタログを更新

---

**司令塔承認**: 2026-05-11 13:30 JST (Claude as Quant)
**Codex 着手承認待ち**: queued


## Error (2026-05-11T07:38:49Z)

```
orphaned: container restarted while task was running
```


## Error (2026-05-11T07:58:18Z)

```
orphaned: container restarted while task was running
```
