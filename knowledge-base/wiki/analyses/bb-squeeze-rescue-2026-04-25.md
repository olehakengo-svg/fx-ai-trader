# Pre-Registration: bb_squeeze_breakout 救済 BT (Cell-Filter + Time-Floor) (2026-04-25)

## 1. 背景と動機

R&D 全件解剖 ([[rd-target-rescue-anatomy-2026-04-25]]) で、N≥100 級の Shadow 負EV
戦略 7つを Approach A (RR再構築) / B (Time Decay) / C (極限フィルター) で評価.

**bb_squeeze_breakout は唯一の "二重正当化" 救済候補**:

| 指標 | 値 |
|---|---|
| Baseline N=113 | EV=-0.26p, PF=0.89 |
| **AvgWin / AvgLoss** | **+9.79 / -2.97 (W:L=3.30)** |
| Break-even WR | **23.3%** (実測 17.7%, 5.6pt 不足) |
| Approach A (RR救済) | NO (med MFE 1.0p / 必要 RR 4.65) |
| **Approach B (Time Floor)** | **YES — hold≥20m で EV+5.04, hold≥40m で EV+11.00** |
| **Approach C (Cell)** | **YES — USD_JPY×London×TREND_BEAR N=9 EV+1.58 Wlo=18.9% PF=1.97** |

仮説: **「BB squeeze の本来の意味 (圧縮→ブレイクの初動)」を捉えるには
保持時間が必要。早期 (hold<10m) は false-break ノイズで損切り**。
Cell (London×TREND_BEAR) は「Asia 後の London 突破」と
「上位足下降中のレンジ離脱」が重なる物理的に意味ある特異点.

緊急トリップではなく **R&D 検証** — 本戦略は既に Shadow なので Live リスクはゼロ.

## 2. 仮説 (Pre-Registered)

### H0 (帰無)
Cell-Filter / Time-Floor / 両方適用 のいずれも 365日 BT で EV ≤ 0.

### H1 (代替)
3 改造のいずれかが EV>+1.0p (摩擦+slippage マージン) を達成.

### H1 詳細期待値 (Live 観測ベース推定, BT検証対象)

| 改造 | 期待 N | 期待 WR | 期待 EV | 根拠 |
|---|---|---|---|---|
| C: Cell only (USD_JPY×London×TREND_BEAR) | 365日換算 ~25 | 44.4% | +1.58p | Live 9件観測 |
| B: Time Floor only (hold≥20m) | ~30 | 42.1% | +5.04p | Live bin 観測 |
| C+B: 両方適用 | ~10 | ~50% | +6〜+10p | 重複領域期待 |
| Baseline (no change) | ~365 | 17.7% | -0.26p | 現状 |

## 3. データセット

- ペア: 全 6 ペア (USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY, EUR_GBP) — XAU除外
- 期間: 365 日 (2025-04-26 〜 2026-04-25)
- 戦略: `bb_squeeze_breakout` のみ
- 摩擦モデル: v2 (spread, slippage, wick noise, cascade CD)
- Time-Floor 実装: hold < threshold で TIME_DECAY_EXIT 発火を抑制

## 4. 検定軸 (4 cells, Bonferroni 補正)

| Cell | Filter | Time Floor | 期待 RR |
|---|---|---|---|
| **A0 baseline** | none (現状) | none | as-is |
| **A1 Cell only** | USD_JPY × London × TREND_BEAR | none | as-is |
| **A2 Time only** | none | hold ≥ 20min | as-is |
| **A3 Cell+Time** | USD_JPY × London × TREND_BEAR | hold ≥ 20min | as-is |

副次 (Bonferroni対象外, secondary):

| Cell | Filter | Time Floor |
|---|---|---|
| A4 | USD_JPY × London (TREND_BEAR制約緩) | hold ≥ 20min |
| A5 | USD_JPY 全session × TREND_BEAR | hold ≥ 20min |

## 5. SURVIVOR Gate (Pre-Registered, Bonferroni α=0.05/4=0.0125)

Cell 通過条件 (AND):
1. **EV > +1.0p** (摩擦+slippage マージン)
2. **PF > 1.30**
3. **N ≥ 30** (Wilson_lo 安定要件)
4. **Wilson_lo (WR) > BE 必要値** (= (1-WR)/WR で逆算した必要 WR)
5. **WF 同符号** (90日×4期間で全 EV>0)
6. **Welch t vs A0 baseline で p < 0.0125**

## 6. CANDIDATE / REJECT 判定

- **SURVIVOR**: 6 条件全通過 → Live 昇格 pre-reg を別途起案
- **CANDIDATE**: 4-5 条件通過 → Holdout (2026-05-25) で再判定
- **REJECT**: ≤3 条件 → bb_squeeze_breakout を `_FORCE_DEMOTED` に格上げ

## 7. 副次仮説 (Bonferroni対象外)

H2: **squeeze→expansion transition** の検出強化  
   → BB width pct が前 N bar で <30% から >60% に拡大した瞬間のみエントリー

H3: **MTF squeeze 必須化**  
   → mtf_vol_state=squeeze の時のみ発火 (今回の Grail Sentinel と整合)

## 8. 実装注記 (本番コード変更なし)

- BT harness: `scripts/bb_squeeze_rescue_bt.py` (新規, R&D環境のみ)
- 既存 `app.py` の `compute_scalp_signal()` を `backtest_mode=True` で流用
- Time-Floor: BT 内で hold_min 推定値 (next-bar timestamp - entry_timestamp) で gate
- Output: `raw/bt-results/bb-squeeze-rescue-{date}.json`

## 9. 凍結ルール

- 本 pre-reg LOCK 後、**コード変更禁止**まで BT 完走.
- BT 結果が出るまで bb_squeeze_breakout の Shadow 状態維持.
- SURVIVOR 判定 → Cell+Time の組合せを `_GRAIL_CANDIDATES` に追加する deploy pre-reg.
- REJECT 判定 → bb_squeeze_breakout を `_FORCE_DEMOTED`.

## 10. タイムライン

| 日付 | アクション |
|---|---|
| 2026-04-25 | 本 pre-reg LOCK + harness 設計 |
| 2026-04-26〜2026-04-29 | 365日 BT 実行 (4 main cells + 2 secondary) |
| 2026-04-30 | SURVIVOR/CANDIDATE/REJECT 判定 |
| 2026-05-07 | Phase 1 holdout 期限と並走 |

## 11. メモリ整合性

- [部分的クオンツの罠]: PF/Wilson_lo/RR/Break-even WR/W:L/WF 全て本 pre-reg に含む ✅
- [ラベル実測主義]: TP-rate/EV は 365日 BT 実測判定 ✅
- [成功するまでやる]: REJECT 判定の場合、別セッションで H2/H3 副次仮説深掘り ✅
- [XAU除外]: data 段階で除外 ✅

## 参照
- [[rd-target-rescue-anatomy-2026-04-25]] (本 pre-reg の根拠データ)
- [[tp-hit-deep-mining-grail-2026-04-25]] (squeeze系 grail と整合)
- [[bb-squeeze-breakout]] (戦略 KB)
