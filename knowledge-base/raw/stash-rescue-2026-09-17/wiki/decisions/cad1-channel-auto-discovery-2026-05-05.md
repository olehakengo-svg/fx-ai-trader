---
title: CAD-1 — Channel Auto-Discovery Pipeline (短期エッジ自動発掘 → Auto-Shadow)
date: 2026-05-05
status: PROPOSED → READY_FOR_PHASE0
owner: claude-司令塔
implementer: codex
trigger: 短期間のみ出現する水平チャネル型エッジを人手カタログから自動発掘 + Shadow へ自動投入
related:
  - knowledge-base/wiki/lessons/feedback_shadow_first_quant_architecture.md
  - knowledge-base/wiki/lessons/feedback_ma_filter_breaks_mr.md
  - knowledge-base/wiki/lessons/feedback_hmm_gate_same_trap.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_bt_must_use_massive.md
  - knowledge-base/wiki/lessons/feedback_codex_schema_hallucination.md
  - knowledge-base/wiki/lessons/feedback_codex_mock_test_trap.md
roadmap_gate: meta-discipline / auto-discovery layer (REDESIGN_QUEUE と並走)
rule: R1 (Slow & Strict — new strategy framework, 365d BT + Bonferroni + Pre-reg LOCK)
---

# 1. Why this pipeline exists

W4-EDA で 76 戦略を監査、91% が「思想は正、設計が誤」(REDESIGN_QUEUE 40 戦略) と判明。既知戦略の再設計と並行して、**未知のチャネル型エッジ**を自動発掘し Shadow へ投入する層が欠けている。

短期エッジの代表例:
- セッション固定型 — Tokyo/London/NY 時間帯で形成される水平チャネル (数時間〜1 日)
- 複数日固定型 — 数日〜数十日にわたって上限/下限が固定されるレンジ相場
- 週次型 — 1〜3 ヶ月続くマクロ consolidation (FOMC 待ち等)

これらは寿命が短く、**カタログ化したころには枯れている**。発掘 → 即 Shadow 投入 → 死亡検知 → retire を全自動化する。

# 2. Scope of v1 (POC = Phase 0)

**Phase 0 は L2 (multi-day, 1H) lane × USDJPY 単独 12 ヶ月 retro replay のみ**。Phase 1 で 3 lane × 6 pair に拡張、Phase 2 で production hardening。

## 2.1 ユーザー確定要件 (2026-05-05)

- 寿命 lane を 3 種 (L1 intraday session / L2 multi-day / L3 weekly) 全部対応
- 自動化深度は **Auto-Shadow promote のみ**。Live は既存 H1 Gate / 司令塔承認を経由 (本決定範囲外)
- 発掘対象は **水平チャネル** (固定上限/下限間の mean reversion)
- トリガーは Render worker による継続稼働

## 2.2 アーキテクチャ核心

**戦略の動的コード生成は採用しない**。代わりに **1 個のパラメトリック戦略** `auto_channel_mr.py` が `channel_candidates` テーブルから N 個のチャネルを同時ホストする。

```
[Render cron 15min/1h/6h] → channel_scanner.py
    → range-bound test (Hurst < 0.45 + Donchian width stability + touch count + width)
    → retro BT sanity → BH-FDR (q=0.10) → channel_candidates (status='shadow_active')
        ↓
auto_channel_mr.py (StrategyBase) — 全 lane / 全 pair を 1 戦略で
    → demo_db.append_trade(is_shadow=True)
        ↓
channel_lifecycle.py (5min worker) — break / decay / stale 検知 → status='retired_*'
        ↓
週次 channel_promotion_review.py — Shadow N≥30 を司令塔キューへ
```

# 3. Lane 定義

| Lane | TF | Window | 寿命 | 検出周期 | min_range_atr |
|------|----|--------|------|----------|--------------|
| L1 (Intraday) | 5m / 15m | Tokyo (UTC 0-7) / London (7-13) / NY (13-21) | 数時間〜1 日 | 15min | 3 |
| L2 (Multi-day) | 1H / 4H | rolling 3-30 日 | 数日〜1 ヶ月 | 1 hour | 4 |
| L3 (Weekly) | 4H / 1D | rolling 30-90 日 | 1〜3 ヶ月 | 6 hour | 5 |

# 4. 検出アルゴリズム (4 段すべて pass で候補)

1. **Range-bound test (Hurst exponent)**: H < 0.45 (mean-reverting). `modules/stats_utils.py` に `hurst_exponent()` を追加。
2. **Donchian width stability**: rolling 20 bar の `(don_high - don_low) / ATR` の標準偏差が 0.5×ATR 未満。`modules/indicators.py` の既存 `don_high20/48` を再利用。
3. **Touch count**: 上限/下限それぞれに ±0.2×ATR で接触したバーが N≥3 回ずつ。
4. **Range width**: `(upper - lower) ≥ k × ATR` (k は lane 別)。

# 5. Sanity Gate (BH-FDR)

per-scan で発見した全 candidate に対し、**formation window 終了の次の bar から** retro replay (look-ahead 0):

- 境界接触 → 反対境界到達 (TP) または逆突破 (SL) を simulate
- N, WR, PF, Wilson_lo (95%), Kelly_half を計算
- **個別ゲート**: N ≥ 6, WR ≥ 60%, PF ≥ 1.5, Wilson_lo ≥ 0.45
- **Family ゲート**: 通過候補に対し p-value (binomial vs WR=0.45) を計算 → BH-FDR (q=0.10) 適用 (`research/edge_discovery/v1b_forensics.py:60-73` の `benjamini_hochberg` 再利用)

通過したものだけ `status='shadow_active'` で登録。

# 6. 死亡検知

`channel_lifecycle.py` worker (5 分毎):

- **Hard break**: 直近 close が `upper + 0.5×ATR` 超 / `lower - 0.5×ATR` 下 → `retired_break`
- **Slow death**: shadow N≥10 で rolling Wilson_lo < 0.40 → `retired_decay`
- **Stale**: lane 別 max_lifetime 超過 (L1=2 日 / L2=45 日 / L3=120 日) → `retired_stale`

retire は `algo_change_log` に記録。

# 7. DB スキーマ (Codex 実装時に直接埋め込み — schema ハルシネーション対策)

```sql
CREATE TABLE channel_candidates (
  channel_id      TEXT PRIMARY KEY,           -- "L2_USDJPY_1H_20260505T0700"
  pair            TEXT NOT NULL,
  tf              TEXT NOT NULL,
  lane            TEXT NOT NULL,              -- 'L1' / 'L2' / 'L3'
  lower           REAL NOT NULL,
  upper           REAL NOT NULL,
  atr_at_formation REAL NOT NULL,
  formed_at       TEXT NOT NULL,              -- ISO8601 UTC
  hurst           REAL NOT NULL,
  retro_n         INTEGER NOT NULL,
  retro_wr        REAL NOT NULL,
  retro_pf        REAL NOT NULL,
  retro_wilson_lo REAL NOT NULL,
  fdr_p_adj       REAL NOT NULL,
  status          TEXT NOT NULL,              -- 'shadow_active' | 'retired_break' | 'retired_decay' | 'retired_stale'
  retired_at      TEXT,
  shadow_n        INTEGER DEFAULT 0,
  shadow_wr       REAL,
  shadow_wilson_lo REAL
);
CREATE INDEX idx_channel_active ON channel_candidates(status, pair, tf);
```

# 8. Phase 構成

**Phase 0 (sanity prototype)** — 本決定で承認する範囲:
- L2 lane × USDJPY 単独 × 12 ヶ月 retro replay
- **Stage 0 ACCEPT 基準**: discovered channels の retro Wilson_lo 中央値 ≥ 0.50, FDR 適用後の生存率 ≥ 30%
- 不通過なら検出アルゴリズム見直しへ戻る

**Phase 1 (3 lane × 6 pair 拡張)** — Phase 0 ACCEPT 後、別決定文書で承認:
- L1 / L3 を追加実装、`auto_channel_mr.py` を全 pair で有効化
- Render cron 3 本 + lifecycle worker をデプロイ
- Pre-reg LOCK doc を git commit してから Shadow 30 日観測

**Phase 2 (production hardening)** — Phase 1 N≥30 蓄積後、別決定:
- 週次 promotion_review で Bonferroni-corrected promotion candidate を司令塔キューへ
- ELITE_LIVE 経路は既存 H1 Gate に委譲

# 9. 棄却条件

- Phase 0 で BH-FDR 通過率 < 10% → false positive 過多、検出アルゴリズム再設計
- Phase 1 Shadow 30 日で aggregate WR < 50% → CAD-1 全体棄却
- 既存 H1 Gate (lessons: `feedback_hmm_gate_same_trap.md`) と同じく、shadow → live で edge が消える pattern が観測されたら lane 構造を再考

# 10. 既知の罠 (memory に基づく事前回避)

1. **チャネル発掘の自己充足バイアス**: formation window 終了の **次の bar から** retro BT を始める (look-ahead 0)。
2. **MA トレンドフィルタ追加禁止** (`feedback_ma_filter_breaks_mr.md`): channel mean reversion に trend filter を入れない。Lane 分離で regime 適合を担保。
3. **HMM gate 同様の罠** (`feedback_hmm_gate_same_trap.md`): Phase 0 では regime gate を入れずフラット評価。
4. **Codex schema ハルシネーション対策** (`feedback_codex_schema_hallucination.md`): §7 の DDL を Codex タスク仕様に直接埋め込む。
5. **Codex mock-only 罠** (`feedback_codex_mock_test_trap.md`): scanner の Codex タスク仕様で massive parquet 実 fetch を必須化、mock 禁止。
6. **BT は MASSIVE 必須** (`feedback_bt_must_use_massive.md`): `tools/bt_data_cache.py` 経由で `data/cache/massive/USD_JPY_1h.parquet` を読む。
7. **Live/Shadow 分離必須** (`feedback_live_shadow_separation.md`): Phase 1 観測時は `is_shadow=1` のみ抽出。

# 11. 月利目標への寄与経路

直接的な edge ではなく、**Shadow tier に良質候補を継続供給する layer** として寄与:

- REDESIGN_QUEUE (40 戦略) の手作業再設計と並走、auto-discovery が高速 churn で候補 N を稼ぐ
- Live promotion は既存 H1 Gate を経由するので Phase 0/1 では月利には直接寄与しない
- Phase 2 で Bonferroni 通過候補が Live tier 入りすれば月利寄与開始
- 想定 timeline: Phase 0 (1 週間) → Phase 1 (2 週間 + Shadow 30 日) → Phase 2 promotion (Phase 1 完了 +30 日)

# 12. 実装着手

Phase 0 は Codex タスク `20260505-1100-cad1-phase0-l2-usdjpy-bt.md` を `.ai/tasks/queue/` に投入して開始する。
