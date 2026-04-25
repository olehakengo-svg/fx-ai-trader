# Edge Reset — 方向転換決定 (2026-04-26)

**Date**: 2026-04-26
**Type**: 戦略方針転換 / Decision
**Trigger**: ユーザー発言「現時点勝ててない、エッジがない、MTFの判定が出来ない」
**Status**: 承認済 (auto mode 中、ユーザー 3 質問への明示同意で承認)
**Plan ID**: `/Users/jg-n-012/.claude/plans/luminous-fluttering-shannon.md`

## 1. 決定内容

「断定的ラベルの逆校正を発見・神経化する」 incremental アプローチを停止し、
**Edge 再構築 (Mechanism-driven 戦略再設計)** に方向転換する。

### 保持するもの

過去 6 commit の中立化変更は維持 (実害が確認されているため):
- `b37ee8b` VWAP conf_adj 中立化
- `6ae6962` calibration monitor + baseline KB
- `9787dd8` strategy_category registry + TF rootcause KB
- `2a6d1da` HVN/LVN + 機関フロー中立化
- `032cd6a` meta-lesson (why missed inversion)
- `91f34ac` app.py VWAP deviation conf bonus 中立化

### 停止するもの

- 未監査ラベル (BUY強化/SELL強化/HMM一致/ADX強/Stoch 等) の逐次監査作業
- 「ラベル has/no で WR 差を取って中立化」の作業フロー
- ※ 前セッション handoff (`Task 2: 未監査ラベル網羅`) は **Phase 2 thesis 棚卸しに統合**

## 2. 第三者診断の数値根拠

| 指標 | 値 | 解釈 |
|---|---|---|
| Live FX-only (post-2026-04-08) WR | 39.0% (N=259) | 戦略レベル負 EV |
| Kelly | -17.97% | 数学的に lot 上げ禁止 |
| PnL | -215 pip | 構造的赤 |
| TP-hit grid (N≥50) で BEV gap < 0 | 16/16 cells | 全 cell 理論期待値がコストで赤 |
| Scalp 摩擦 / DT 摩擦 | 5.4× | Scalp は事実上 edge 不可 |
| MTF η² | <0.005 | 単一 TF ADX は分散の 0.5% も説明しない |
| macdh_reversal median MFE | 0 pip | 予測力エントリー直後にゼロ |

これらは「ラベル品質」の問題ではなく、**戦略設計レベルの構造的問題**を示している。

## 3. 第三者診断: System vs Structural

| 区分 | 問題 | 重大度 |
|---|---|---|
| Structural | TAP-1/2/3 (中間帯AND/N-bar/直前candle) を含む戦略の根本欠陥 | 🔴 最高 |
| Structural | BT 楽観バイアス 6 因子 (entry price / spread / signal_reverse / HTF / fill / label) | 🔴 最高 |
| Structural | Scalp 摩擦 5.4× が cost model に未反映 | 🟠 高 |
| System | MTF gate の resample 生成 (M5→H4) で microstructure 喪失 | 🟠 高 |
| System | MTF gate の TF/MR 統一ロジック (Δ-7.5pp / Δ+10.8pp で逆転) | 🟠 高 |
| System | RR floor 引き上げが「数学的対症療法」(BEV を下げただけ) | 🟡 中 |
| Strategic | 「ラベル神経化」が edge 不在を覆い隠す KB narrative | 🔴 最高 |

**結論**: System 修正だけでは勝てない。Structural 再設計が必須。

## 4. Phase 0 即時実装 (本決定)

### 4.1 MTF alignment soft modulation を完全 disable

`app.py:1665-1681` (旧):
```python
if htf_agreement == "bull":
    if combined < 0: combined = 0.0
    else: combined = min(1.0, combined * 1.2)
elif htf_agreement == "bear":
    if combined > 0: combined = 0.0
    else: combined = max(-1.0, combined * 1.2)
else:
    combined *= 0.60
```

→ 全コメントアウト、`pass`。`htf_agreement` 変数は L2486+/L2077+ の HTF Hard Block で依然使われるので変数自体は保持。

### 4.2 _BT_SLIPPAGE 確認

既に 2026-04-21 の commit で friction-analysis.md 公称値に更新済 (USDJPY 0.5 / EURUSD 0.5 / GBPUSD 1.0)。Phase 0 では追加変更なし。

### 4.3 KB 文書化

- 本決定: `wiki/decisions/edge-reset-direction-2026-04-26.md`
- 教訓: `wiki/lessons/lesson-label-neutralization-was-symptom-treatment-2026-04-26.md`

## 5. Phase 1+ ロードマップ要約

| Phase | 期間 | 内容 |
|---|---|---|
| **Phase 0** (本決定) | 即時 | MTF soft mod disable + KB 文書化 |
| **Phase 1** | 1 週間 | OANDA native H4/D1 fetch + strategy_category.apply_policy() 統合 + EMA順列 category 分岐 |
| **Phase 2** | 1 週間 | 既存全戦略の mechanism thesis 棚卸し (前セッション Task 2 を統合) |
| **Phase 3** | 1-3 ヶ月 | TF/Range の高勝率エッジ研究 (mechanism thesis 必須) |

## 6. ユーザー意思決定の記録

- 方向転換受け入れ: **YES**
- EMA順列 (app.py:2745-2772): **Phase 1 で category 分岐** (前 reject の意図を反映)
- Phase 3 研究方向: **TF と Range の両カテゴリで高勝率エッジ探索 (mechanism thesis 必須)**

## 7. Anti-pattern 警告 (継続監視)

- ❌ 「BT で勝つ戦略を増やす」誘惑 — BT 楽観バイアスで edge を錯覚
- ❌ 「Kelly が負だから lot を上げて取り戻す」誘惑 — 数学的に破綻
- ❌ 「ラベル神経化を続けたほうが安全」誘惑 — symptom treatment で edge は生まれない

## References

- Plan: `/Users/jg-n-012/.claude/plans/luminous-fluttering-shannon.md`
- [[lesson-label-neutralization-was-symptom-treatment-2026-04-26]]
- [[lesson-why-missed-inversion-meta-2026-04-23]]
- [[tf-inverse-rootcause-2026-04-23]]
- [[bt-live-divergence]]
- [[friction-analysis]]
- Phase 5 lesson (cbbbc8b): 5m Pure Edge 6/9 DEAD は本決定と整合
