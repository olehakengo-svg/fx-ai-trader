# ロードマップ v2.1: DT幹 + Scalp枝 統合ポートフォリオ

**作成日**: 2026-04-14
**旧版**: roadmap-v2.md (A+B+C三位一体) → v2.1で「DT専業」から「DT+Scalp統合」に修正
**根拠**: 全戦略×全ペア×全TF包括BTスキャン (365日DT, 60日Scalp)

---

## コンセプト: 「DTで稼ぎ、Scalpで加速し、データで判断する」

```
DT (15m):  年間+433pip → ポートフォリオの「幹」（安定α）
Scalp (1m/5m): 年間+200pip推定 → 「枝」（加速+分散+N蓄積）
合計: +633pip/年推定
```

---

## 二軸構造: ゲート軸（直列）× 実装軸（並行）

### ゲート軸

```
Gate 0 [即時]: DT LIVE + Scalp SENTINEL + AVOID全停止
Gate 1 [Week 1-2]: Aggregate Kelly > 0 → DD 0.2x → 0.3x
  ★ Scalp高頻度でN蓄積加速 → 1週間で到達の可能性
Gate 2 [Week 2-3]: Kelly>0.05, PnL>+50pip, 破産<70% → 0.3x → 0.5x → ★月利100%
Gate 3 [Week 4-6]: PF>1.0, N≥100, 破産<30%, DSR>0.80 → 1.0x
Gate 4 [Week 8+]: DSR>0.95, 破産<10%, N≥200 → Kelly Half (3.0lot)
```

### 実装軸（全並行、v2から継続）

```
Track A: VWAPファクター + キャッシュTTL ✅完了
Track B: MCゲート + Kelly動的 + Gate API ✅完了
Track C: HMM 2状態モデル（ログ並走） ✅完了
Track D: BT自動パイプライン ✅完了
Track E [新]: Scalp Lab改善 (SR 1bar化 + SL幅テスト → 追加正EV発掘)
```

---

## DT幹: Tier 1 LIVE（即時）

| 戦略 | ペア | BT EV | BT N | BT PF | BT PnL |
|---|---|---|---|---|---|
| session_time_bias | USD_JPY | +0.580 | 157 | 2.46 | +91p |
| session_time_bias | EUR_USD | +0.215 | 566 | 1.34 | +122p |
| session_time_bias | GBP_USD | +0.113 | 516 | 1.16 | +58p |
| trendline_sweep | GBP_USD | +0.599 | 134 | 1.68 | +80p |
| gbp_deep_pullback | GBP_USD | +1.064 | 77 | 2.00 | +82p |

合計PnL: **+433pip/年**

## DT SENTINEL（Live N蓄積待ち）

| 戦略 | ペア | BT EV | 昇格条件 |
|---|---|---|---|
| orb_trap | USD_JPY | +0.866 | Live N≥15, WR≥60% |
| htf_false_breakout | JPY/GBP/EUR | +0.35~0.66 | Live N≥15 |
| turtle_soup | GBP_USD | +0.386 | Live N≥15 |
| doji_breakout | GBP_USD | +0.724 | Live N≥15 |
| post_news_vol | GBP/EUR | +0.82~1.76 | Live N≥15 |
| xs_momentum | JPY/EUR | +0.22~0.27 | Live N≥20 |

---

## Scalp枝: ペア×TF最適組合せ（SENTINEL開始）

**原則: 同じ戦略でもペアとTFでエッジが異なる。BTデータが最適TFを決める。**

| 戦略 | ペア | TF | BT EV | BT N | BT WR | 根拠 |
|---|---|---|---|---|---|---|
| bb_squeeze_breakout | USD_JPY | **5m** | **+1.030** | 11 | 90.9% | 全Scalp最強。5mで摩擦克服 |
| engulfing_bb | USD_JPY | **5m** | **+0.677** | 17 | 88.2% | WR=88%, 5m限定 |
| fib_reversal | EUR_USD | **1m** | +0.426 | 40 | 72.5% | 1mでのみ正EV (5m=0.001) |
| bb_squeeze_breakout | EUR_USD | **1m** | +0.473 | 19 | 73.7% | 1m限定 |
| sr_channel_reversal | EUR_USD | **5m** | +0.231 | 17 | 70.6% | 5mの方がEV高い |

### Scalp停止対象

- **GBP_USD Scalp全停止** — 摩擦/ATR=48.7%、構造的に不可能
- **bb_rsi_reversion Scalp全停止** — 全ペア全TFで負EV
- **vol_momentum_scalp全停止** — 1m負EV, 5m負EV (Live WR=80%はN=10の幸運)

---

## lot配分ルール

| モード | lot比率 | 根拠 |
|---|---|---|
| DT Tier 1 LIVE | **3** | αの幹。安定収益源 |
| Scalp SENTINEL | **0.1** (0.01lot) | Live検証フェーズ。BT乖離を実測 |
| Scalp LIVE昇格後 | **1** | DTの1/3。高頻度なので小lotでも十分なPnL |

## リスク管理ルール

| ルール | 根拠 |
|---|---|
| DT lot : Scalp lot = 3:1 | DTが幹、Scalpは枝 |
| Scalp 1日損失-2%で**OANDA転送のみ**停止（デモは蓄積継続） | 高頻度のため累積損失が速い。ただしデモデータは常に蓄積 |
| Scalp BT乖離>20ppで即SENTINEL降格 | 摩擦モデル誤差検出 |
| ペア×TF組合せはデータ固定 | カーブフィッティング防止 |
| aggregate Kelly < 0: OANDA全停止 | 実装済み（自動ゲート） |
| MC破産確率 > 70%: OANDA全停止 | 実装済み（自動ゲート） |

---

## Scalp改善ロードマップ（Track E）

| Step | 内容 | 期待効果 |
|---|---|---|
| E1 [完了] | London/NYフィルター分析 | JPY London: -42pip→-1pip |
| E2 [次] | SR recheck 3bar→1bar | BT/Live乖離 -5pp |
| E3 [次] | SL幅テスト (×0.75→×1.0/×1.2) | 即死率削減 → WR +5-10pp |
| E4 | 修正後全Scalp再スキャン | 追加正EV戦略発掘 |
| E5 | Scalp専用摩擦モデル | BT信頼性3倍向上 |

---

## DT+Scalp統合の優位性

| 指標 | DT専業 | DT+Scalp統合 |
|---|---|---|
| 年間PnL推定 | +433pip | **+633pip (+46%)** |
| 月間トレード数 | ~100 | **~400** |
| Kelly正転まで | 2-3週 | **1-2週** |
| ポートフォリオ分散 | ペア分散のみ | **ペア+TF+戦略分散** |
| DT-Scalp相関 | — | **低相関（異なるエッジ源）** |
| Gate 1到達 | Week 2 | **Week 1（前倒し）** |

---

## BT根拠データ（本セッション実施）

- DT 365日 5ペア: `knowledge-base/raw/bt-results/comprehensive-bt-scan-2026-04-14.md`
- Scalp 1m 60日: `knowledge-base/raw/bt-results/shadow-bt-reeval-2026-04-14.md`
- Scalp Lab: `data/cache/scalp_lab_results.json`
- Scalp 5m 60日: `data/cache/bt_scan_scalp_results.json`

## Related
- [[roadmap-v2]] — 旧版（DT専業前提）
- [[roadmap-to-100pct]] — 初版（v1、WARNING付き）
- [[friction-analysis]] — ペア別摩擦
- [[bt-live-divergence]] — 6つの構造的楽観バイアス
