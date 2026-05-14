---
date: 2026-05-14
type: lesson
status: confirmed
rule: R3 (structural defect — multiple session/geometry combos fail 365d Deep BT)
---

# 1m USDJPY Scalp — 4 Strategy Variants All Fail 365d Deep BT

## 一行教訓
**1m × 24日 TV strategy tester で PF>1.5 に見えるエッジは 365d Deep BT で全滅。1m USDJPY は構造的に scalp +EV 困難。**

## 検証結果サマリ (TV Pine v5, USDJPY 1m, OANDA, 2025-05-14 → 2026-05-14)

| Variant | 設計 | N | WR% | PF | Net (raw) | Friction-Adj EV |
|---|---|---|---|---|---|---|
| macd_1m_scalp London | hist round-trip TP, SELL H1<50 | 673 | 39.67 | 1.535 | +0.64% | **-1.56%/yr ❌** |
| macd_1m_scalp Tokyo BUY | BUY-only, H1<70 | 453 | 39.51 | 1.307 | +0.26% | **negative ❌** |
| macd_1m_scalp NY | ATR-TP 1:2 dual | 1,276 | 36.52 | 1.150 | +0.22% | **negative ❌** |
| bmr_scalp_v1 (mean rev) | BB+RSI bounce, 4/2 pip | 923 | 21.99 | <1 | **-1.53%** | -1.53% ❌ |
| ets_scalp_v1 (trend) | SMA9/21 + RSI50 + MACD hist, 6/3 pip | 3,428 | 28.27 | 0.313 | **-5.76%** | -5.76% ❌ |

(Friction modeled: commission=0.012% RT + slippage=5 ticks ≈ 1.2 pip RT)

## 中核的失敗構造

### 1. **24d→365d で PF が 1.85→1.54 に劣化** (London variant)
- 短期 BT は出来高/ボラ環境が偏る (single regime)
- 365d は QE/QT/JPY介入/Fed/BOJ 複数政策レジームを跨ぐ
- 短期で +EV な edge は regime-dependent で 365d 平均でならされる

### 2. **1m USDJPY ATR ~2pip は friction 1.2pip RT と同等**
- Per-trade edge を friction 上に積み上げる余裕がほぼゼロ
- TP=6pip / SL=3pip の R:R=2 でも WR 54% 必要 (BE_WR 33% + friction margin)
- 実測 WR は 28-40% の範囲、全て BE_WR 未達

### 3. **mean-reversion (bmr) も trend (ets) も両方失敗**
- 1m は random walk に近く、両方向の structural edge が薄い
- MACD hist round-trip (London) も SMA cross pullback (ets) も
  signal-to-noise が friction を超えない

### 4. **N の多さは edge を保証しない**
- ets_scalp_v1 N=3,428 (9.4 trades/day) は scalp 仕様を満たすが
  PF 0.313 で構造的負け戦略 (frequency × small edge = ゼロ × inf)

## 関連 Lesson との接続

- **lesson-orb-trap-bt-divergence**: 短期 BT の WR/EV は 365d で必ず検証 (再確認、今回も該当)
- **lesson-cell-audit-bt-required-2026-04-27**: cell-level pre-filter で +EV を見せても全体 365d は別問題
- **lesson-xau-friction-distortion**: friction が ATR と同等の TF は構造的に scalp 不可 (XAU と同様の構造)
- **lesson-1m-scalp-not-the-problem**: 過去に 1m scalp 自体は問題ではないと判断したが、本検証で USDJPY 1m に限れば構造不可と再判定

## 含意 (次の方向性)

1. **1m USDJPY scalp は撤退**: roadmap-v2.1 「Scalp 枝 = 1m 戦略」前提を見直し
2. **5m 以上 + cross-pair** で edge 探索: tv-pine-edge-discovery-framework.md の path に戻る
3. **DT 15m が幹 (年+433pip)** は変わらず: ここに集中投資
4. **既存 macd 3 variants Pine ファイルは "Pine 内で短期 PF>1.5 だが 365d で friction 負け" の参考事例として残置**
   - 削除はしない (Pine BT 学習の証跡)
   - wiki/strategies/ に正式戦略カードは作らない

## 4 原則との照合

- **「攻める」**: 攻めた結果、4変種全て負け → 攻める方向を変える (1m → 5m+)
- **「カーブフィッティング禁止」**: 24d で見えたエッジは fitting だった
- **「クリーンデータ蓄積優先」**: -EV 戦略を Live shadow に流すのはデータ汚染、停止が正解

## Pine ファイル
- `bt-results/tv-overlays/macd_1m_scalp-{london,tokyoBuy,ny}.pine` — 短期 PF>1.5, 365d -EV (参考事例)
- ets_scalp_v1 / bmr_scalp_v1 は disk 未保存 (in-memory のみ、棄却)

## TV serial screenshots
- `/Users/jg-n-012/test/tradingview-mcp/screenshots/macd_1m_scalp_*_365d.png`
- `/Users/jg-n-012/test/tradingview-mcp/screenshots/ets_scalp_v1_initial.png`
