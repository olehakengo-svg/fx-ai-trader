# Cell-level Bonferroni Audit 2026-04-27

**Source**: Production demo_trades (`/api/demo/trades?status=CLOSED&limit=20000`), 30d window, XAU除外
**Total trades**: 3,075 (live + shadow, post-cutoff 2026-04-08)
**Audit framework**: `tools/cell_edge_audit.py --mode v3` (entry_type × session × pair × direction × mode)
**Min N per cell**: 15 → **49 qualified cells**
**Multi-test correction**: Bonferroni z=3.29 (k=52 strategies)

## Promotion Gate (適用基準)

```
🟢 STRICT  : Wilson_BF (k=52) lower > breakeven_wr (0.294)
            AND ev_after_friction > 0  (raw EV - 2.0pip rough)
            AND ev_raw > 0
            AND wins >= 2
🟡 WATCH   : Wilson 95% lower > 0.294 AND BH-FDR p < 0.05 AND avg_net > 0
⚪ NO_EDGE : 上記いずれも非通過
```

## 結果 — STRICT 候補 1件 / WATCH 0件 / NO_EDGE 48件

### 🟢 STRICT — `bb_rsi_reversion × EUR_USD × BUY × Scalp × Overlap`

| 項目 | 値 |
|---|---|
| N (live + shadow) | 19 |
| wins | 14 |
| WR | 73.7% |
| Wilson 95% lower | 51.2% |
| **Wilson_BF (k=52)** | **37.2%** > 29.4% ✓ |
| Wilson_BF (k=624, 3-tuple) | 22.7% < 29.4% (FAIL strict) |
| EV (raw, pip) | +2.10 |
| EV (-2.0pip friction) | +0.10 |
| Profit Factor | 2.86 |
| Binomial p (Bonferroni) | 1.0000 |
| Binomial p (BH-FDR) | 0.0707 |

**現在の tier**: `scalp_sentinel` (shadow tracking 中、OANDA 配信なし)

### クオンツ評価

**Pros**:
- Wilson_BF (k=52) > breakeven は厳密な統計的優位性の指標
- EV > 0 (raw + friction 控除後)
- PF 2.86 は強い
- セッション (Overlap = London/NY) が明確で時間帯の絞り込みが効いている

**Cons**:
- N=19 < gate minimum N=20 (1サンプル不足)
- Binomial p_bonf = 1.0 → 「ランダムから有意差」の強い証拠は不足
- BH-FDR p=0.0707 → α=0.10 でも boundary
- Wilson_BF (k=624 = 全 strategy×pair×direction tuple) では gate FAIL

**判定**: **WATCH 棚** (Pre-reg LOCK 候補)。N=30 まで shadow 蓄積を待ち、Wilson_BF が k=624 でも維持されるか + binomial が α=0.05 を切るかを再評価する。

## Pre-reg LOCK (起案)

```yaml
strategy: bb_rsi_reversion
pair: EUR_USD
direction: BUY
mode: Scalp
session: Overlap (London/NY 12-16 UTC)
audit_date: 2026-04-27
trigger_to_promote:
  - shadow_n >= 30 in (pair, direction, mode, session) cell
  - Wilson_BF (k=624) lower > 0.294
  - p_bonferroni < 0.05 (両側 binomial)
  - WF halves verdict in {stable, borderline} (collapse は失格)
  - avg_net (post-friction) > 0
action_if_pass:
  - tier_master.json `pair_promoted` に [bb_rsi_reversion, EUR_USD] 追加
  - direction=BUY の暫定ガードを bb_rsi_reversion strategy module に挿入
  - lot=0.01 で 30 trades or 14日 mini-pilot
  - 失敗時: scalp_sentinel に戻す
trigger_to_disqualify:
  - shadow N>=30 で Wilson_BF (k=52) <= 0.294
  - WF verdict = collapse
  - 4週間経過しても N<30
```

## 全 49 cells の verdict

NO_EDGE 48件はすべて以下の理由で gate FAIL:
- 大半: avg_net (after 2pip friction) < 0 → コスト負け
- 一部: WR > 50% でも Wilson_BF 下限 < 29.4% → 統計的に十分でない

詳細データは `/tmp/audit_v3/cell_edge_audit_2026-04-27_v3_30d_inclshadow.json` (リポジトリ外、再生成可能)。

再生成コマンド:
```bash
curl -s "https://fx-ai-trader.onrender.com/api/demo/trades?status=CLOSED&limit=20000" -o /tmp/trades_fresh.json
# /tmp/prod_trades_audit.db を再構築 (上記 commit メッセージ参照)
python3 tools/cell_edge_audit.py --db /tmp/prod_trades_audit.db --mode v3 \
  --include-shadow --window 30d --min-n 15 --out-dir /tmp/audit_v3
```

## 次のアクション

1. **bb_rsi_reversion EUR_USD/BUY/Overlap の Pre-reg LOCK** を `wiki/decisions/pre-reg-bbrsi-eurusd-2026-04-27.md` で確定
2. 週次で v3 audit を再実行し N=19→30 への蓄積を追跡
3. 4週間後 (2026-05-25 目安) に再評価 → mini-pilot 起動可否決定
4. 他 48 cells は「審査済み NO_EDGE」として記録、月次再 audit で誤検出を最小化

## Aggregate Fallacy 解消の効果

CLAUDE.md「Aggregate Fallacy」原則:
> aggregate (全 cell) が負けでも cell-level で edge があれば prefer

今回の発見: bb_rsi_reversion 全体は **PAIR_DEMOTED (EUR_JPY/EUR_USD/GBP_USD/USD_JPY 全敗)** だが、
**EUR_USD × BUY × Overlap という単一 cell では Wilson_BF 通過**。

これは典型的な aggregate fallacy 事例。同戦略の他 cells (USD_JPY 全方向) は明確に -EV だが、
特定セッション × 特定pair × 特定方向だけで edge を持つ可能性を示唆。

`tier_master.json` の pair_demoted は cell 軸を持たないため、
Phase 5 (direction × session 軸の正式導入) で構造的に解消することが望ましい。

## クオンツ判断の動機 (CLAUDE.md「動機の記録」)

- ✅ データ駆動: 49 cells の Bonferroni-corrected Wilson lower bound で唯一通過
- ✅ 既存 KB との整合性: bb_rsi_reversion 全体は pair_demoted (KB と整合) — cell では別エッジ
- ✅ Pre-reg LOCK 必須: live 投入前に明示的 trigger 条件を文書化
- ❌ 感情的: 「+EV だから昇格」は禁止 — Wilson_BF が n=30 で再通過するかが必要条件
