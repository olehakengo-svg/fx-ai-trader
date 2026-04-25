---
date: 2026-04-25
scope: read-only (no code change) — KB unresolved の "Portfolio concentration diagnosis"
target: vwap_mean_reversion (post-cutoff Live + Shadow cell-level scan)
window: 2026-04-08 → 2026-04-24 (post-cutoff, 17 days)
data_source: Render `/api/demo/trades` (paginated 4 pages, total 3,296 records)
---

# Portfolio Concentration Diagnosis — vwap_mean_reversion (2026-04-25)

## 0. TL;DR

- **集中度の現状**: vwap_mr Live closed N=10 / Live total closed N=266 = **3.8%**
  → KB unresolved の "~80% 占有" は古い記述、`elite-freeing-patch` Patch C
  (OANDA TRIP) 適用後に既に解消済
- **Live aggregate**: N=10, **EV=-4.77p**, WR=40% — Patch C 維持を強く支持
- **Shadow cell-level (N=35)**: 14 cells に分解、**生存 cell 候補 2** (GBP_JPY BUY,
  EUR_USD SELL) が指向的に +EV、しかし **どの cell も Bonferroni significance
  未達** (cell-level α=0.0036, N≤7)
- **Live × Shadow 整合性**: 損 cells (EUR_JPY 両方向, GBP_USD SELL) は両系列で
  一致、winner cells (GBP_JPY BUY) も両系列で正符号 (Live N=2, Shadow N=5)
- **行動**: Patch C 維持、Shadow N≥20/cell まで蓄積、再判定は **pre-registration
  必須** ([[lesson-preregistration-gate-mechanism-mismatch]] 適用)

## 1. データ取得方法

```bash
curl 'https://fx-ai-trader.onrender.com/api/demo/trades?limit=1000&offset={0..3000}'
```

- Combined N: 3,296 records
- Post-cutoff (created_at ≥ 2026-04-08): N=2,780
- Closed (excluding `WEEKEND_CLOSE`): N=2,776
- vwap_mr closed: N=45 (Live 10 + Shadow 35)

`pnl_pips` は string で返るため float 変換必須。`is_shadow` も string ('0'/'1')。
`WEEKEND_CLOSE` レコードは TP/SL 到達でなく週末強制クローズなので EV 計算から除外。

## 2. 集中度の更新 — KB unresolved 記述は古い

| 指標 | KB unresolved (古い) | 実測 (2026-04-25) |
|------|----------------------|-------------------|
| vwap_mr の Live N 占有率 | "~80%" | **3.8%** (10/266) |
| Total Live N (post-cutoff) | (記載なし) | 266 |

→ Patch C (`VWAP_MR_OANDA_TRIP=1`) の effect が出て、新規 OANDA 送信は止まり、
**既存ポジションのクローズが Live N に残るのみ**。占有率は急速に低下中。

ELITE 3 戦略の Live N も `elite-freeing-patch` (c195d16) で MTF/Q4 gate 免除が
効き始めて分母が増加、相対的に vwap_mr 比率はさらに下がる。

## 3. cell-level 分解 (vwap_mr post-cutoff, N=45)

`pair × direction × mode(live/shadow)` で 14 cells に分解。

### 3.1 Live (N=10) — Patch C 適用前のポジションが残存クローズ

| pair | side | N | wins | WR | EV(p) | avg_win | avg_loss |
|------|------|--:|----:|----:|------:|--------:|---------:|
| GBP_JPY | BUY | 2 | 1 | 50.0% | **+12.05** | +44.20 | -20.10 |
| EUR_JPY | BUY | 3 | 2 | 66.7% | -6.33 | +1.80 | -22.60 |
| GBP_USD | SELL | 3 | 1 | 33.3% | -6.73 | +1.20 | -10.70 |
| EUR_JPY | SELL | 1 | 0 | 0% | -10.10 | — | -10.10 |
| GBP_USD | BUY | 1 | 0 | 0% | -22.50 | — | -22.50 |

**Live aggregate**: N=10, sum_pnl=**-47.70p**, EV=-4.77p, WR=40%

**観察**:
- EUR_JPY BUY は WR=66.7% と高く見えるが avg_win=+1.80p / avg_loss=-22.60p →
  **小利大損型の典型** ([[friction-analysis]] のペア別 friction 適用後でも EV 大幅マイナス)
- GBP_JPY BUY は **唯一の +EV cell** だが N=2 で statistical significance なし

### 3.2 Shadow (N=35) — 真の cell-level 生存者判定の本体

| pair | side | N | wins | WR | EV(p) | avg_win | avg_loss | **判定** |
|------|------|--:|----:|----:|------:|--------:|---------:|----------|
| **GBP_JPY** | **BUY** | **5** | **3** | **60.0%** | **+10.32** | +23.97 | -10.15 | ★ 候補 |
| **EUR_USD** | **SELL** | **7** | **2** | **28.6%** | **+3.41** | +21.30 | -3.74 | ★ 候補 |
| GBP_USD | SELL | 8 | 3 | 37.5% | -1.50 | +14.23 | -10.94 | △ 中立 |
| USD_JPY | BUY | 3 | 0 | 0% | -0.80 | — | -0.80 | △ 中立 (low magnitude) |
| EUR_JPY | BUY | 4 | 0 | 0% | -7.45 | — | -7.45 | ✗ 損 |
| EUR_JPY | SELL | 4 | 0 | 0% | -15.20 | — | -15.20 | ✗ 損 (最悪) |
| EUR_USD | BUY | 2 | 0 | 0% | -4.55 | — | -4.55 | ✗ 損 (small N) |
| GBP_JPY | SELL | 1 | 0 | 0% | -14.90 | — | -14.90 | ✗ 損 (single) |
| GBP_USD | BUY | 1 | 0 | 0% | -2.20 | — | -2.20 | ✗ 損 (single) |

### 3.3 cell-level Bonferroni 検定

- 観測 cells M=14
- α_family = 0.05 → α_cell = 0.05/14 = **3.57e-3**
- 各 +EV cell の null = "cell EV ≤ 0" を Welch t (single sample vs 0)
  もしくは Wilson WR > BEV_pair で検定:

| cell | N | EV | WR | BEV (per pair) | Wilson WR_lo (95%) | p (informal) | Bonferroni |
|------|--:|---:|---:|---------------:|-------------------:|-------------:|:---------:|
| GBP_JPY BUY shadow | 5 | +10.32 | 60% | ~38% | 18% | ~0.16 | ❌ NO |
| EUR_USD SELL shadow | 7 | +3.41 | 28.6% | 39.7% | 5% | ~0.7 | ❌ NO |

→ **cell-level でどの cell も Bonferroni significance 到達せず**。N が決定的に
不足 (N≤7、必要 N≥20-30 cell)。

## 4. Live × Shadow 整合性 — 信号の robustness

| pair-side | Live EV (N) | Shadow EV (N) | 同符号? |
|-----------|-------------|---------------|--------|
| **GBP_JPY BUY** | **+12.05 (2)** | **+10.32 (5)** | ✅ 両系列 +、winner 候補 |
| EUR_JPY BUY | -6.33 (3) | -7.45 (4) | ✅ 両系列 −、loser 確定的 |
| GBP_USD SELL | -6.73 (3) | -1.50 (8) | ✅ 両系列 −、loser |
| EUR_JPY SELL | -10.10 (1) | -15.20 (4) | ✅ 両系列 −、loser 最悪 |
| GBP_USD BUY | -22.50 (1) | -2.20 (1) | ✅ 両系列 −、N 不足 |
| **EUR_USD SELL** | (Live 0) | **+3.41 (7)** | ⚠️ Live 未検証 |

**観察**:
- Loser cells は Live × Shadow 両系列で頑健に同符号 (誤判定リスク低)
- Winner 候補 GBP_JPY BUY も両系列で +、ただし N=7 (=2+5) で確証なし
- EUR_USD SELL は Live 件数ゼロ → patch C 適用後の OANDA 送信停止が効いており
  Live 検証パスは絶たれている → Shadow N で判断するしかない

## 5. 判定 — Patch C 維持 + 段階的解除条件

### 5.1 維持判断の根拠
1. **Live aggregate EV=-4.77p (N=10)** — Patch C 緊急トリップは結果的に妥当
2. **Loser cells が両系列で確定的** — 全面解除は明確に有害
3. **Winner 候補 N が不足** — 解除しても OANDA 送信は loser cells も含む

### 5.2 段階的解除のための pre-registration テンプレ

`lesson-preregistration-gate-mechanism-mismatch` 遵守: data look 前にゲート LOCK。

```
Hypothesis: 
  vwap_mr の Shadow EV は (pair × side) cell-level で異質、
  loser cells を block しつつ winner cells のみ Live 復帰させれば
  aggregate EV > 0 を達成できる

Mechanism: 
  cell selection filter (=block list)。WR を上げる機構ではなく、
  既存 EV 分布の loser tail を切り落とすことで mean を上げる →
  WR 軸でなく **mean EV / EV CI lower bound** を binding gate に使う

Binding criteria (LOCKED before next data look):
  cell SURVIVOR = 以下を ALL pass:
    - Shadow N ≥ 20 (per cell)
    - mean EV ≥ +1.0p
    - mean EV の 95% CI lower bound ≥ 0
    - Bonferroni: Welch t (vs 0) p < 0.05/M
    - Live × Shadow 同符号 (Live N≥3 のとき)

Anti-criteria (損切りを優先):
  cell BLOCKED = 以下のどれか:
    - Shadow N ≥ 20 かつ mean EV ≤ -1.0p
    - Live × Shadow 両方 N≥3 で両 mean EV < 0

§7 Anti-pattern guard: 結果を見てゲート緩和は禁止
```

### 5.3 タイムライン予想
- **GBP_JPY BUY shadow N=20 到達**: 現 N=5 + 1.7d で 5 件ペース → ~50 日後 (2026-06-15 頃)
- **EUR_USD SELL shadow N=20 到達**: 現 N=7 + 2.4d で 7 件ペース → ~37 日後 (2026-06-01 頃)
- **早期 cell judgement** が可能になるのは概ね **6 月初旬以降**

## 6. 推奨アクション

### 6.1 今セッション (read-only)
- [x] 本 analysis doc 作成
- [x] KB unresolved の "Portfolio concentration" 記述を更新 (Patch C で解決済)
- [x] cell-level 生存者の暫定リストを KB に固定
- [x] pre-registration テンプレート提示 (実装は次データ look 直前)

### 6.2 実施しないもの
- ❌ **code 変更 (cell selection filter 実装)**: KB unresolved 明記の "code 変更禁止"
  + N 不足 + pre-reg 未 LOCK で実装すれば post-hoc fitting
- ❌ **Patch C 解除**: Live EV=-4.77p で正当化されたガード。N≥20 cell で +EV
  確認まで維持
- ❌ **vwap_mr V2 logic (sublimation filters) の評価**: 別 pre-reg が必要

### 6.3 次セッション以降
- [ ] Shadow N 蓄積監視 (週次)
- [ ] GBP_JPY BUY が N≥20 到達したら **5.2 のテンプレで pre-reg LOCK** → cell-level 検定
- [ ] EUR_USD SELL も同様
- [ ] "cell selection filter" の code 設計は pre-reg PASS 後

## 7. KB unresolved 更新

更新前:
> [ ] **Portfolio concentration diagnosis** — `vwap_mean_reversion` が Live N の ~80% 占有、負 EV. cell-level scan 経由で生存者判定 (code 変更禁止)

更新後 (推奨):
> [x] **Portfolio concentration diagnosis 完了** — Patch C 適用後 vwap_mr 占有率は 3.8% (10/266) に低下、全面危機は解消. Shadow N=35 cell-level 分解で winner 候補 2 (GBP_JPY BUY +10.32, EUR_USD SELL +3.41) / loser 確定 4 cells. 但し全 cell で N≤7 → Bonferroni 未達, 5.2 テンプレで pre-reg LOCK 待ち. 詳細: [[portfolio-concentration-vwap-mr-2026-04-25]]

## 8. メタ監査

- ✅ read-only scope 遵守 (code 変更ゼロ)
- ✅ XAU 除外 (vwap_mr は XAU 取引対象外)
- ✅ Live × Shadow 別集計 ([[lesson-shadow-contamination]] 遵守)
- ✅ pnl_pips の string→float 変換確認、WEEKEND_CLOSE 除外
- ✅ data look 前に pre-reg をテンプレ化 (将来的 LOCK 対象)
- ⚠️ 単一週末 (4 日 fresh + 13 日 paginated) のみで判断 → Live × Shadow データが
  全期間 post-cutoff に揃っていることを確認した上での判定。日次 EV の cycle 性は
  未調査 (週次 EV による cell-level breakdown は将来課題)
- ⚠️ Friction model の per-pair 値 ([[friction-analysis]]) は本分析の avg_loss
  数値と整合的 (e.g., GBP_USD friction=4.53p で typical loss が -10p 域)

## 9. References

- [[elite-freeing-patch-2026-04-24]] — Patch C (vwap_mr OANDA 緊急トリップ)
- [[vwap-mean-reversion]] — 戦略 KB
- [[friction-analysis]] — per-pair friction (Loss magnitude の妥当性 sanity)
- [[lesson-preregistration-gate-mechanism-mismatch]] — pre-reg 設計ルール
- [[bt-live-divergence]] — 楽観バイアス参照軸
- [[cell-level-scan-2026-04-23]] — 過去の Phase 2 cell-level scan template

---

**Status**: Portfolio concentration diagnosis closed (read-only)
**Next milestone**: Shadow N≥20 per cell 到達 (~5-7 週間後) → pre-reg LOCK → cell-level 検定
