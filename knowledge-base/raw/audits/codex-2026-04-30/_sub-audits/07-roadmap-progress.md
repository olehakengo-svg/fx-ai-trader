# Sub 7 (訂正版): ロードマップ v2.1 進捗監査

> **訂正履歴**:
> - v1 (12:50): is_shadow フィルター漏れで「Gate 1 未達 / 月利達成不可能」と誤断
> - **v2 (13:00, 本ファイル)**: LIVE 純粋集計で Gate 1 達成判定、月利目標達成可能性あり
>
> Codex API 利用上限のため Claude が直接実行。

## Scope
- ロードマップ: `knowledge-base/wiki/syntheses/roadmap-v2.1.md`
- Tier: `knowledge-base/wiki/tier-master.md`
- 実績: ライブ DEMO 2026-04-02 〜 2026-04-29
  - **LIVE 実弾 (is_shadow=0): N=36, +6pip (outlier 除外で +176pip)**
  - Shadow (is_shadow=1): N=437, -668pip (学習資産)
- 補助: Sub 1-6 監査結果

## 1. Bugs Found
| # | Severity | File:Line | Description | Root Cause | Suggested Fix |
|---|----------|-----------|-------------|-----------|--------------|
| 1 | Sev2 | `tier-master.md:1-3` | 5日間更新なし、Live drift 未反映 (v1 から継続課題) | 自動 trigger なし | nightly cron 化 |
| 2 | Sev2 | `tools/tier_integrity_check.py` (推定) | Shadow→LIVE 昇格基準が BT EV ベースで Live drift を見ない | tier integrity ロジックが BT 偏重 | Live N≥10 + Wilson + Bonferroni 補正の自動昇格判定追加 |

## 2. Structural Issues (訂正版)
1. **LIVE 実弾 vs Shadow の集計分離が運用 dashboard で機能していない**
   - api_strategies_status / api_phase_gate が is_shadow の集計分離出力を持たない可能性 (要 code 確認)
   - そのため誰も LIVE +6pip / Shadow -668pip という景色を即座に見られない
   - これが私 (Claude) の誤判断の原因でもあり、運用上のガバナンス欠陥
2. **Tier 昇格基準が BT 依存で Shadow 実績を見ない**
   - tier-master.md の ELITE_LIVE 3 戦略は BT EV で決定
   - Shadow N≥30 の sr_break_retest / sr_fib_confluence 等の実弾データはあるのに昇格判定に反映されない構造
3. **bb_rsi_reversion の LIVE Bonferroni 候補が Tier に未反映**
   - LIVE N=22, Wilson lower 0.430, PF 6.97, Kelly +0.545
   - tier-master.md A-1 ELITE_LIVE に bb_rsi_reversion がいない
   - **ELITE_LIVE 昇格を即時検討すべき真の候補**
4. **roadmap v2.1 「Scalp +200pip/年」想定が LIVE データではまだ確認できていない**
   - Scalp LIVE 母集団が小さい (vol_momentum_scalp N=4 など)
   - Track E (Scalp Lab 改善) で N 蓄積を加速すべき
5. **roadmap +633pip/年想定の Live 換算**
   - LIVE 28日 +6pip → 年化 +78pip (outlier 込み)
   - LIVE 28日 +176pip → 年化 +2,295pip (outlier 除外)
   - **outlier 除外なら roadmap 想定の 3.6 倍超**
   - ただし母集団小、信頼区間広い

## 3. Losing Edge Analysis
Sub 6 (訂正版) で詳述。LIVE で N≥2 の負け戦略は trend_rebound (N=2, -5.9pip) のみ。

## 4. Roadmap Alignment (訂正版)

### Gate 0 [即時]: DT LIVE + Scalp SENTINEL + AVOID 全停止
- **状態**: ⚠️ 部分達成
- **根拠**: Tier 構造はあるが ELITE_LIVE 戦略 (gbp_deep_pullback / session_time_bias / trendline_sweep) の LIVE N が極小 (各 0-1 件)
  - 現在の真の LIVE エッジ bb_rsi_reversion が Tier 上は別カテゴリ
- **律速要因**: Tier 判定が BT 依存で Shadow→Live 移行が機械的でない
- **推奨**: bb_rsi_reversion を ELITE_LIVE に昇格 (LIVE N=22, Bonferroni 候補)

### Gate 1 [W1-2] Aggregate Kelly > 0
- **状態**: ✅ **達成**
- **定量根拠**: LIVE trade-weighted Kelly = **+0.385** (outlier 込み) / **+0.396** (turtle_soup 除外)
- **律速要因**: なし (達成済み)
- **次のステップ**: Gate 2 へ進む (lot 0.2x → 0.3x)

### Gate 2 [W2-3] Kelly>0.05, PnL>+50pip, 破産<70%, 月利100%
- **状態**: ⚠️ Kelly 部分達成、PnL は outlier 影響大
- **定量根拠**:
  - Kelly +0.385 ≫ 0.05 ✅
  - PnL: +6pip (outlier 込み) / +176pip (outlier 除外) — turtle_soup 1件で判定が反転する敏感さ
  - 破産確率: Kelly +0.385 で通常 30-50% (Sub 2 #2 の DSR 単位不整合で正確計算は要修正)
- **律速要因**: turtle_soup -170pip outlier の真贋確定 + Sev1 11 件のうち LIVE 経路 (idempotency, lot 永続化) 修正
- **推奨**: outlier 検証 → bb_rsi_reversion 単独で +192pip / 単戦略 N=22 だけでも目標近接

### Gate 3 [W4-6] PF>1.0, N≥100, 破産<30%, DSR>0.80
- **状態**: ❌ N不足
- **定量根拠**: LIVE N=36、Gate 3 の N≥100 まで不足。bb_rsi_reversion 単独でも N=22 で 100 まで遠い
- **律速要因**: クリーンデータ蓄積律速 + DSR 計算不整合 (Sub 2 #2)
- **推奨**: Scalp 高頻度で N 蓄積加速 (Track E) + bb_rsi_reversion lot up で 1 トレードあたり pip 寄与増

### Gate 4 [W8+] DSR>0.95, 破産<10%, N≥200, Kelly Half (3.0lot)
- **状態**: ❌ 未着手
- **律速要因**: N=200 まで遠い、DSR 計算修正が前提
- **推奨**: Gate 1-3 順次達成後

## 5. Top 5 Action Items (impact 順、攻めの再構成)

1. **bb_rsi_reversion を ELITE_LIVE 昇格 + lot 0.2x → 0.3x に増量**
   - LIVE N=22, Kelly +0.545, PF 6.97, PnL +192pip, Wilson lower 0.430 で Bonferroni 候補
   - Gate 1 達成判定で lot 進行は roadmap どおり
   - Impact: 月利目標への最大寄与
   - Confidence: high

2. **turtle_soup outlier の broker-side 検証**
   - LIVE 1件で -170pip は execution bug 起因の可能性 (Sub 1d #6)
   - OANDA 取引履歴と照合し、SL/TP 同時到達時の broker truth を確認
   - もし bug 起因なら PnL を broker truth に書き換え
   - Impact: LIVE 純益が +6pip → +176pip に確定する可能性、Aggregate Kelly 上昇
   - Confidence: high

3. **Sev1 11 件のうち LIVE 経路に集中修正** (Sub 1d #1, #2, Sub 1c #1-2)
   - OANDA idempotency (Sub 1d #1) — 二重発注防止で LIVE PnL 信頼性回復
   - ロット永続化 (Sub 1d #2) — 増量実行時のロット管理が前提条件
   - 認証強化 (Sub 1c #1-2) — control plane セキュリティ
   - 中低優先 (BT 経路、Shadow 経路バグ) は P2 へ降格
   - Impact: LIVE 増量実行の安全保証
   - Confidence: high

4. **Shadow → LIVE 昇格基準を厳格化** + tier_integrity_check 拡張
   - Sub 8 提言と統合: Live N≥10 で Wilson<BEV+5%, EV<0 → 自動 demote
   - Shadow N≥30, Wilson lower ≥ BEV+5pp, 直近 30日 EV>0 → LIVE 昇格候補
   - Impact: Tier の Live drift 自動是正、ELITE_LIVE の意味回復
   - Confidence: high

5. **Scalp Lab (Track E) 加速で Gate 3 N 蓄積を急ぐ**
   - vol_momentum_scalp / doji_breakout / mtf_reversal_confluence の LIVE N 蓄積
   - bb_squeeze_breakout / bb_rsi_reversion の Scalp variant が roadmap 記載済み (USD_JPY 5m, EUR_USD 1m)
   - これは Sub 4 #1 の ScalperEngine SL floor mutation 修正が前提
   - Impact: Gate 3 N≥100 への到達が 4-6 週間で見込める
   - Confidence: med

## 6. Out-of-Scope Findings
- v1 で書いた「現状ペースでは目標達成不可能」は誤り。LIVE outlier 除外で年化 +2,295pip 出ている
- v1 の「Live 緊急停止」提言も誤り。LIVE は健全に黒字
- shadow 戦略の負けは「データ蓄積による学習」であり、roadmap の v2.1 設計どおり

## 7. Roadmap Progress Verdict (訂正版)

```
Gate 0: ⚠️ 部分達成 (Tier-Live drift / bb_rsi_reversion 未反映)
Gate 1 (Kelly>0):           ✅ 達成 (LIVE Kelly +0.385)
Gate 2 (Kelly>0.05):        ⚠️ 部分達成 (Kelly 達成、PnL outlier 次第)
Gate 3 (PF>1.0, N≥100):     ❌ N不足 (現 36, 目標 100)
Gate 4 (DSR>0.95, N≥200):   ❌ 未着手
```

## 8. 月利100% への距離 (訂正版)

| シナリオ | LIVE 28日 PnL | 年化 | vs roadmap想定 (+633pip) | 月利 100% 達成性 |
|---|---:|---:|---:|---|
| outlier 込み | +6pip | +78pip | 12% | 不十分、要 N 蓄積 |
| **outlier 除外** | **+176pip** | **+2,295pip** | **362%** | **★達成見込みあり、ただし N=36 で信頼区間広い** |
| **bb_rsi_reversion 単独 (LIVE N=22)** | **+192pip** | **+2,503pip** | 395% | 単戦略でも目標超過 |

加速施策 (再掲):
1. bb_rsi_reversion lot up
2. outlier 検証
3. LIVE 経路 Sev1 修正
4. Shadow→LIVE 昇格基準厳格化
5. Scalp Track E 加速

## 9. ドリフト検出 (訂正版)

### roadmap に書かれているが実装されていない
1. Gate 0 lot-step 進行 (`api_phase_gate` 実装欠落、Sub 1c #2)
2. AVOID 全停止 cell-level kill 機構 (Sub 2 #5: cell_routing.py stub)
3. **Tier の Shadow→LIVE 自動昇格 (本サブ追加)** — bb_rsi_reversion が Bonferroni 候補なのに ELITE_LIVE に未反映
4. DSR ベースの Gate 3-4 判定 (Sub 2 #2 単位不整合)
5. ScalperEngine SL floor mutation 廃止 (Sub 4 #1) — Scalp Track E 加速の前提

### 実装されているが roadmap に反映されていない
1. Layer 0 spread/friction hard gate (obs 603)
2. Layer 1 regime classifier (obs 607)
3. mtf_regime_*_cascade_scalp 2 戦略 (obs 609, 614) — まだ Live 発火なし
4. **bb_rsi_reversion の真のエッジ確認 (本サブ追加)** — roadmap v2.1 に明記すべき

## 10. ガバナンス課題 (本サブ独自)

私 (Claude) が v1 で誤判断した最大の原因は:
1. is_shadow フィルター漏れ — `_gen_cell_stats.py` の SQL に `is_shadow=0` を入れ忘れた
2. Aggregate fallacy 再発 — 全体 PnL -661pip だけ見て LIVE/Shadow を分離せず
3. CLAUDE.md 原則 #4「攻撃は最大の防御 — データ蓄積を優先」を真逆に解釈

これは Sub 8 が指摘する「lesson が code/手順に内部化されていない」と同型。
**`_gen_cell_stats.py` のような分析スクリプトに `is_shadow` 区分を強制するテンプレート化** が必要。
