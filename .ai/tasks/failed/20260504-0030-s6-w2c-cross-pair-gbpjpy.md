---
id: 20260504-0030-s6-w2c-cross-pair-gbpjpy
title: S6 W2c cross-pair — GBP_JPY M5 12.3y detector+BT, regime axis included (no LIVE)
owner: codex
status: queued
priority: P1
created_at: 2026-05-04T00:30:00+0900
roadmap_gate: 新戦略族 S6 Wave 2c (cross-pair 検証、PARK 判断の confirmability、LIVE 露出なし)
rule: R1
prerequisite_decision:
  - 2026-05-04 W2b commit 57c8fe8 — USD_JPY M5 で全 24 verdict REJECT/INSUFFICIENT (S6 PARKED)
  - 2026-05-04 W2a regime axis 再評価 — triple_bottom × BULL D1 N=88 EV+0.66 PF1.18 (sub-100 borderline)
  - feedback_codex_schema_hallucination — DDL 直接記載
  - feedback_codex_mock_test_trap — 実 parquet E2E 必須
  - feedback_partial_quant_trap — N/WR/EV だけで判定禁止
  - feedback_label_empirical_audit — 実測クエリ、コード演繹禁止
---

## 0. 目的

USD_JPY M5 で 4 wave (W1P0/W2/W2a/W2b) 検証して edge 不在を確認した S6 ATR 12-pattern hypothesis を、**もう 1 つの主要 pair (GBP_JPY M5) で完全独立検証**する。同 hypothesis が GBP_JPY でも null なら hypothesis family を高い確度で棄却 (PARK 確定)。万一 GBP_JPY で edge を見せれば cross-market signal として強力 (Wave 4 LIVE candidate 検討)。

LIVE / Shadow 露出ゼロ、新規 OANDA 接続なし。

## 1. 検証範囲 (LOCK)

| pair | TF | Years | Bars | 役割 |
|---|---|---|---:|---|
| **GBP_JPY** | **M5** | **2014-2026 (12.3y)** | **925,109** | **★ primary cross-pair (USD_JPY と同期間・同 TF)** |
| EUR_USD | M5 | 2025-10〜2026-04 (0.5y) | 37,034 | 補助診断 (低 statistical power、肯定/否定なら有用) |

GBP_JPY は USD_JPY と同 12.3y データ → 同等の statistical power を確保できる **唯一**の cross-pair。

## 2. 仮説

- **H1 (主 / null hypothesis)**: GBP_JPY M5 でも全 12 patterns × isolated mode で edge なし (USD_JPY W2 と同じ pattern) → **S6 family hypothesis 完全棄却**確定
- **H2 (cross-pair edge possibility)**: 1 つでも GBP_JPY × isolated PROMOTE 圏なら、ATR 12-pattern hypothesis に market-specific edge があり得る → Wave 4 LIVE candidate 検討
- **H3 (regime axis cross-pair)**: GBP_JPY の triple_bottom × BULL D1 が USD_JPY と同様 borderline (PF 1.1〜1.2, N<100) なら統計ノイズ仮説支持 → PARK 確定
- **H4 (cross-pair regime divergence)**: GBP_JPY で USD_JPY と異なる regime cell に edge があれば pair-specific regime sensitivity の証拠 (W2c+ 拡張)

## 3. Phase 構成 (LOCK)

### Phase 3.1: Detector run on GBP_JPY M5
W1P0 と同 schema/閾値で `chart_pattern_signals` テーブルに `pair='GBP_JPY', timeframe='M5'` 行を追加。USD_JPY 行 (22,094) は read-only 不変。

### Phase 3.2: BT run on GBP_JPY M5 (isolated mode のみ、3 mode 不要)
W2 と同 engine で `chart_pattern_bt_trades` に `pair='GBP_JPY', bt_run_id='isolated'` 行追加。フィルタ条件 (signal_ts+1 bar entry, spread, max_hold) は USD_JPY と同じだが **GBP_JPY スプレッドは 1.5p ではなく実測ベース**:
- demo_trades.db で `instrument='GBP_JPY' AND spread_at_entry > 0` の avg を集計
- なければ literature default `2.5 pip` (USD_JPY の 1.5p より広い、GBP cross の特徴)

### Phase 3.3: Verdict (W2 と同 logic) + regime axis
- 12 pattern × isolated → 12 verdicts (W2 と同基準: N≥100, Wilson_lo>BEV, PF≥1.3, Bonferroni p<0.0042)
- 12 pattern × 2 regime → 24 secondary verdicts (W2a regime axis と同)
- Bonferroni m: **primary verdict は m=24 (12 pattern × 2 pair USD_JPY+GBP_JPY)**, regime axis は m=48
- α/m primary = 0.05/24 = 0.00208

### Phase 3.4 (補助): EUR_USD M5 簡易チェック
EUR_USD 0.5y データで detector run、N が極端に薄い場合 INSUFFICIENT 全件想定。Bonferroni 適用なし、参考値として doc 末尾に併記のみ。

## 4. SQLite DDL (LOCK)

W1/W2 の既存 schema を再利用、append のみ:

```sql
-- 既存表: chart_pattern_signals (W1P0)
-- 既存表: chart_pattern_bt_trades (W2)
-- 既存表: chart_pattern_bt_verdicts (W2)
-- 全て append、UNIQUE 制約で pair × timeframe 区別

-- 新規: cross-pair verdict 比較用
CREATE TABLE IF NOT EXISTS chart_pattern_w2c_cross_pair_verdicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id INTEGER NOT NULL,
    pattern_name TEXT NOT NULL,
    pair TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    axis TEXT NOT NULL CHECK (axis IN ('isolated','regime_BULL','regime_BEAR')),
    n INTEGER NOT NULL,
    wr REAL NOT NULL,
    ev_pips REAL NOT NULL,
    pf REAL,
    wilson_lo_95 REAL NOT NULL,
    bev_wr REAL NOT NULL,
    bonferroni_p REAL NOT NULL,
    bonferroni_alpha REAL NOT NULL,
    bonferroni_m INTEGER NOT NULL,
    kelly REAL NOT NULL,
    max_dd_pips REAL NOT NULL,
    spread_pips_used REAL NOT NULL,
    spread_source TEXT NOT NULL,         -- 'demo_trades_empirical' / 'literature_default'
    verdict TEXT NOT NULL CHECK (verdict IN ('PROMOTE','SHADOW','REJECT','INSUFFICIENT')),
    cross_pair_consistency TEXT,         -- 'CONFIRMS_USDJPY' / 'CONTRADICTS_USDJPY' / 'N_INSUFFICIENT'
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(pattern_id, pair, timeframe, axis)
);
```

DB path: `data/chart_patterns.db` (append、既存 5 表 read-only)

## 5. 受入条件 (LOCK)

- [ ] `chart_pattern_signals` 既存 22,094 USD_JPY 行 不変
- [ ] GBP_JPY M5 signals が新規追加 (期待 N ≈ 22k 前後、parquet サイズ比例)
- [ ] `chart_pattern_bt_trades` 既存 42,483 行 不変、GBP_JPY isolated 行追加
- [ ] `chart_pattern_w2c_cross_pair_verdicts` に 36 行 (12 pattern × {isolated, regime_BULL, regime_BEAR})
- [ ] `pytest tests/test_s6_w2c_cross_pair.py -q` 全 pass (≥ 15 tests)
  - 必須: GBP_JPY parquet 読み込み + signal 生成 (既存 detector engine 再利用)
  - 必須: GBP_JPY spread 集計 (demo_trades 実測 or default 2.5p)
  - 必須: pair × pattern × axis verdict logic test
  - 必須: cross_pair_consistency 計算 test (USD_JPY verdict との比較)
- [ ] `wiki/decisions/s6-w2c-cross-pair-2026-05-04.md` に:
  - GBP_JPY 12 pattern isolated verdict 表
  - regime axis 12×2 verdict 表
  - USD_JPY (W2/W2a) との cross-pair 比較 (CONFIRMS / CONTRADICTS / N_INSUFFICIENT)
  - EUR_USD 補助診断
  - H1〜H4 verdict
  - 最終判断: S6 PARK 確定 / Wave 2d 拡張提案 / Wave 4 LIVE candidate
- [ ] `wiki/strategies/s6-chart-pattern.md` Wave Plan / Status 更新
- [ ] `app.py` / `modules/` / `strategies/` 編集 0 件
- [ ] `chart_pattern_signals` USD_JPY 行 / `chart_pattern_bt_trades` USD_JPY 行 不変

## 6. Scope

Codex MAY change:

- `tools/s6_w2c_cross_pair.py` (new) — GBP_JPY 検出+BT+verdict driver
- `tests/test_s6_w2c_cross_pair.py` (new)
- `knowledge-base/wiki/strategies/s6-chart-pattern.md` (UPDATE)
- `knowledge-base/wiki/decisions/s6-w2c-cross-pair-2026-05-04.md` (new)
- `data/chart_patterns.db` (append GBP_JPY signals, trades + new verdicts table)
- `.ai/runs/<run-dir>/final.md`

Codex MAY NOT change:

- `tools/s6_chart_pattern_detector.py` / `tools/s6_chart_pattern_bt.py` (W1P0/W2 engines、再利用 import のみ)
- USD_JPY 行 (signals/trades/verdicts/w2a_diagnosis/w2b_*)
- `data/cache/massive/*.parquet` (read-only)
- `app.py` / `modules/` / `strategies/`
- `.env`, OANDA secrets
- `wiki/index.md`, `wiki/tier-master.json`
- 既存未コミット変更

## 7. Required Reading

- `CLAUDE.md` (Rule 1 適用、cross-pair 検証は新戦略 promotion 候補)
- `wiki/decisions/s6-w2-bt-2026-05-03.md` (USD_JPY W2 全 REJECT)
- `wiki/decisions/s6-w2a-diagnosis-2026-05-03.md` (regime axis triple_bottom×BULL borderline)
- `wiki/decisions/s6-w2b-pre-reg-bt-2026-05-04.md` (USD_JPY W2b 全 REJECT/INSUFFICIENT)
- `tools/s6_chart_pattern_detector.py` (W1P0 engine 再利用)
- `tools/s6_chart_pattern_bt.py` (W2 engine 再利用)
- `tools/s6_w2a_diagnosis.py` (regime axis 計算方法)
- `wiki/lessons/index.md` の `feedback_partial_quant_trap`, `feedback_label_empirical_audit`, `feedback_codex_schema_hallucination`

## 8. Verification Commands

```bash
# 0. Frozen tables 確認 (USD_JPY 行 不変前提)
sqlite3 data/chart_patterns.db "SELECT pair, COUNT(*) FROM chart_pattern_signals GROUP BY pair;"
sqlite3 data/chart_patterns.db "SELECT pair, COUNT(*) FROM chart_pattern_bt_trades GROUP BY pair;"

# 1. GBP_JPY parquet 確認
python3 -c "import pandas as pd; df=pd.read_parquet('data/cache/massive/GBP_JPY_5m.parquet'); print(df.shape, df.index.min(), df.index.max())"
# 期待: (925109, 6+) 2014-01-02 to 2026-04-30

# 2. Self-test
python3 tools/s6_w2c_cross_pair.py --self-test

# 3. Unit tests
python3 -m pytest -q tests/test_s6_w2c_cross_pair.py

# 4. Production run
python3 tools/s6_w2c_cross_pair.py --pair GBP_JPY --tf M5

# 5. Cross-pair verdict 集計
sqlite3 data/chart_patterns.db "SELECT pattern_name, axis, n, ROUND(wr,3), ROUND(ev_pips,2), ROUND(pf,2), ROUND(wilson_lo_95,3), ROUND(bonferroni_p,5), verdict, cross_pair_consistency FROM chart_pattern_w2c_cross_pair_verdicts WHERE pair='GBP_JPY' ORDER BY pattern_id, axis;"

# 6. Frozen USD_JPY 不変確認
sqlite3 data/chart_patterns.db "SELECT COUNT(*) FROM chart_pattern_signals WHERE pair='USD_JPY';"
# 期待: 22094

# 7. EUR_USD 補助
python3 tools/s6_w2c_cross_pair.py --pair EUR_USD --tf M5 --aux-only
```

## 9. Codex Instructions

**Rule 1 (Slow & Strict)** タスク。USD_JPY との cross-pair 検証で hypothesis family 全体の判定。

**絶対遵守**:
- §1 GBP_JPY が primary、EUR_USD は補助 (low N で参考値のみ)
- §3.2 BT engine は USD_JPY W2 と完全同 logic、spread のみ pair 別 (GBP_JPY 実測 or default 2.5p)
- §3.3 Bonferroni m 適切に: primary axis m=24 (12 pattern × 2 pair) で α/m=0.00208
- §4 DDL を BT スクリプト冒頭にコメント直接埋め込み (`feedback_codex_schema_hallucination` 回避)
- §5 verdict logic を厳格適用 (`feedback_partial_quant_trap` 回避: N/WR/EV だけで PROMOTE 出さない)
- look-ahead bias 禁止
- USD_JPY signals/trades/verdicts/w2a/w2b の行を絶対書き換えない
- D1 regime 計算は USD_JPY W2a と同方式 (D1 EMA200 alignment)

**禁止事項**:
- `app.py` / `modules/` / `strategies/` の編集
- `tools/s6_chart_pattern_detector.py` / `tools/s6_chart_pattern_bt.py` の改変 (再利用 import のみ)
- 既存 5 表の更新/DROP/再生成
- LIVE / Shadow / OANDA bridge への接続
- `wiki/index.md` / `wiki/tier-master.json` の更新
- Bonferroni m を不当に小さく取って有意化する操作

**判定基準**:
- 全 GBP_JPY isolated REJECT + regime borderline → **S6 PARK 完全確定** (USD_JPY と整合)
- 1+ GBP_JPY cell PROMOTE → **cross-market edge 発見**、Wave 2d/W3 sweep へ進める根拠
- 1+ cell SHADOW → cross-market borderline、Shadow データ蓄積で N 補完候補

`feedback_success_until_achieved` 通り、verdict 不確定で closure 短絡禁止。N が薄ければ Wave 2d (TF 拡張、M15/H1) 提案を含める。

PR 作成は本タスクで実行しない。proposal doc + 実装 + test のみ。Claude review 後、別 task で commit/deploy。

最終レポートには status, files changed, GBP_JPY 12 pattern isolated verdict 表, regime axis 24 verdict 表, USD_JPY との比較表 (CONFIRMS/CONTRADICTS/N_INSUFFICIENT), EUR_USD 補助結果, H1〜H4 verdict, 最終判断 (PARK 確定 / Wave 2d 提案 / Wave 4 LIVE candidate), residual risks, 次タスクを含む。


## Error (2026-05-04T05:24:22Z)

```
orphaned: container restarted while task was running
```
