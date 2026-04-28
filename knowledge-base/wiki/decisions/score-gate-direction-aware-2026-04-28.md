# Pre-Registration LOCK: SCORE_GATE Direction-Aware Misalignment

- **Date**: 2026-04-28
- **Rule**: R1 (Slow & Strict — 新エッジ主張に準ずる構造変更、Pre-reg LOCK 必須)
- **Status**: LOCKED until 2026-05-12 (14 days)
- **Author**: Claude (quant-analyst mode)
- **Trigger**: P0調査 — `session_time_bias` (ELITE_LIVE) 本番全期間 NEVER_EVER 真因特定

## 1. 問題定義 (実測)

### 観察事実

本番 `https://fx-ai-trader.onrender.com/api/demo/trades?limit=2000` (12日 / 2,004件) と `/api/demo/logs?limit=10000` (30件) で:

| 戦略 | tier | 12日 LIVE | 12日 Shadow | direction内訳 | SCORE_GATE log |
|------|------|-----------|-------------|---------------|----------------|
| session_time_bias | ELITE_LIVE | **0** | **0** | (signal出力 SELL EUR_USD/GBP_USD 多数) | 9件 全block |
| trendline_sweep | ELITE_LIVE | 3 | 0 | **BUY × 3** | 0件 |
| gbp_deep_pullback | ELITE_LIVE | 1 | 0 | **BUY × 1** | 0件 |
| vix_carry_unwind | UNIVERSAL_SENTINEL | 1 | 4 | SELL (score=-3.56でも通過) | bypass |

本番LIVE 44件: **BUY=30 / SELL=14**。SELL 14件は全て scalp pipeline (compute_signal経由) または UNIVERSAL_SENTINEL のいずれか。**daytrade pipeline + ELITE_LIVE + SELL = 7日間 0件**。

### 根本原因 (コード読解)

**[app.py:2544](app.py:2544) (compute_daytrade_signal)**:
```python
_dte_score = _dt_best.score * 0.5 if _dt_best.signal == "BUY" else -(_dt_best.score * 0.5)
```

**[app.py:2552-2554](app.py:2552)**:
```python
if _dt_best.signal == "BUY":
    score += _dt_best.score * 0.5
else:  # SELL
    score -= _dt_best.score * 0.5  # 符号反転
```

→ daytrade pipeline で `sig["score"]` の **符号 = 方向情報** (BUY=正, SELL=負)。

**[modules/demo_trader.py:2862-2873](modules/demo_trader.py:2862) (旧 SCORE_GATE)**:
```python
if _entry_score < 0 and not _sentinel_score_bypass:
    _block(f"score_gate({_entry_score:.2f}<0)")
```

→ SCORE_GATE は方向に関係なく `score<0` で block。SENTINEL系は bypass、**ELITE_LIVE は bypass対象外**。

### 設計矛盾の性質

[modules/demo_trader.py:2849-2853](modules/demo_trader.py:2849) の SCORE_GATE 設計コメント:
> IC=0.089: scoreは勝敗予測で唯一の有効特徴量
> score<=0: WR=22% EV=-1.79pip / score>0: WR=34% EV=-0.98pip
> score<0 のみブロック（戦略自身が「入るな」と言っている）

この前提は「scoreは方向中立な信頼度指標」だが、daytrade pipelineの実装は「score符号=方向」。**両者の意味付けが衝突**しており、ELITE_LIVE SELL 戦略が構造的に block されていた。

これはバグではなく、二つのレイヤーの設計合意失敗 (semantic misalignment)。

## 2. 修正内容

### Code change

**Before** ([modules/demo_trader.py:2862-2879](modules/demo_trader.py:2862)):
```python
if _entry_score < 0 and not _sentinel_score_bypass:
    _block(f"score_gate({_entry_score:.2f}<0)")
    return
```

**After**:
```python
_score_misaligned = (
    (signal == "BUY" and _entry_score < 0)
    or (signal == "SELL" and _entry_score > 0)
)
if _score_misaligned and not _sentinel_score_bypass:
    _block(f"score_gate(misalign:{signal},{_entry_score:.2f})")
    return
```

### Semantics

- BUY signal × score>0 = **aligned** (戦略意図と combined direction 一致 → 通過)
- SELL signal × score<0 = **aligned** (同上 → 通過)
- BUY signal × score<0 = **misaligned** (戦略BUY なのに combined SELL方向 → 戦略が「入るな」と言っている → block)
- SELL signal × score>0 = **misaligned** (同上 → block)

旧 SCORE_GATE の本来意図 (`戦略自身が「入るな」と言っている`) を**direction-aware で正しく実装**。score=0 はそのまま通過 (未実装戦略のデフォルト保護)。

## 3. 期待効果 (事前予測)

### 復旧すべき発火パス
- session_time_bias × USD_JPY × Tokyo (BUY) — 過去本番では HTF block で別経路で止まっていた可能性
- session_time_bias × EUR_USD × London (SELL) — **本修正で復旧期待 (1分間隔のsignal出力実績あり)**
- session_time_bias × GBP_USD × London (SELL) — 同上
- trendline_sweep × {EURUSD, EURGBP, XAUUSD} (SELL_ONLY_PAIRS) — 復旧期待
- gbp_deep_pullback × GBP_USD × SELL — 復旧期待

### 副次効果
- 本来 misalignment で正しく block されていた戦略-signal 組合せはそのまま block 維持
- Sentinel系は引き続き bypass で観測継続

## 4. KPI Pre-registration (rule:R1 LOCK)

### Primary KPI (Continuation条件)

期間: 2026-04-28 ~ 2026-05-12 (14日 / 2週間)

ELITE_LIVE 3戦略の **direction別** で以下を測定:

| KPI | 閾値 | Bonferroni補正 |
|-----|------|----------------|
| Live N | ≥ 15 | 6 strata (3戦略×BUY/SELL) |
| WR | ≥ 40% | Wilson lower bound (95% CI) > 30% |
| PF | ≥ 0.8 | bootstrap CI |
| EV (pips) | ≥ -0.5 | 90% CI lower > -1.5 |
| 連敗 | < 6 | 即停止条件 (rule:R2) |

### 即停止条件 (rule:R2 trigger)

以下のいずれかに該当した時点で**即 SCORE_GATE 旧仕様 (score<0 一律block) に revert**:

1. ELITE_LIVE × SELL 単独で N≥10 かつ WR<30%
2. ELITE_LIVE 全体で N≥15 かつ PF<0.6
3. 同一戦略×ペアで6連敗
4. 月利目標 (¥454,816) に対し、本修正起因の Live累計損失 > -¥10,000 (約 2.2% drawdown contribution)

### Re-evaluation 2026-05-12

判定:
- **Continue**: 全Primary KPI通過 → 修正定着、コメント L2849-2861 を更新して semantic 統一
- **Revert**: 1つでも失格 → SCORE_GATE 旧仕様に戻し、根本問題は app.py の符号反転を見直す別Phaseへ

## 5. リスク評価 (CLAUDE.md Live/Shadow 区別チェック)

| 観点 | 評価 |
|------|------|
| Live / Shadow | 本修正は Live 発火条件の緩和 → **Live実弾コスト発生** |
| Kelly前段 | 既存 ELITE_LIVE は 365日 BT STRONG 確認済 (`_ELITE_LIVE` コメント参照) → Kelly Half到達前のクリーンデータ蓄積として正当 |
| Bonferroni | 6 strata で multiple testing 補正 |
| N希釈 | 戦略×direction で独立集計 |
| KB絶対視リスク | 旧 SCORE_GATE 設計コメントを上書きせず、新仕様の根拠を明記して中道 |

CLAUDE.md「Live クリーンデータ蓄積最優先 (Shadow抑制ではない)」原則と整合。

## 6. ロールバック手順

revert 時は以下を逆実行:
1. `git revert <commit-hash>` で modules/demo_trader.py を元に戻す
2. CHANGELOG.md / 本ファイルに revert 記録追記
3. wiki/lessons/ に lesson-score-gate-direction-aware-rollback-{date}.md を作成
4. 翌セッションで根本fix (app.py の符号反転廃止 or signal別score field 分離) を計画

## 7. 関連ファイル

| ファイル | 変更 |
|---------|------|
| modules/demo_trader.py:2862-2880 | SCORE_GATE direction-aware化 |
| app.py:2544, 2552-2554 | (参考) 符号反転の発生源、本Phase未変更 |
| raw/audits/low_firing_root_cause_2026-04-28.md | 調査レポート、本修正参照 |
| CHANGELOG.md | エントリ追加 |
| knowledge-base/wiki/strategies/session_time_bias.md | (要更新) Live発火復旧の予告 |

## 8. 監視ダッシュボード (推奨)

- 本番 `/api/demo/logs?limit=10000` で `[SCORE_GATE] Blocked: misalign` を観測
- `/api/demo/trades` で entry_type=session_time_bias, trendline_sweep, gbp_deep_pullback の direction別カウント (Live/Shadow)
- 既存の `cell_deepdive_audit.py` weekly cron で WR/EV 自動集計
- Sentryに `[SCORE_GATE] Sentinel bypass: misaligned` を warning として送出 (新ログ形式)
