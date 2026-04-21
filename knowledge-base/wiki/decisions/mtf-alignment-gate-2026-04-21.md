# MTF Alignment Gate — 実装判断 (2026-04-21)

## TL;DR
**判断: 実装保留**
- BT: +49.6R 改善を確認 (sr_fib_confluence × 3ペア 365d)
- 本番 Shadow: +253.6p 改善を確認 (N=106)
- 本番 LIVE: +56.4p 改善 (ACTIVE戦略, N=410) — 統計的に弱い
- **理由**: 工数対効果が現時点では不十分。Live N 蓄積待ちが妥当

## 背景
「全戦略をレジーム判定付きで 365d DT / 120d Scalp BT を実施し勝てるロジックを探す」
というユーザ依頼に対し、regime_combo_bt_search.py で 4 family (TF/MR/BO/SE) × 3 pair ×
2 mode の組合せ BT を実行 (N=6,698 trades)。

### BT 結果サマリ
- **Bonferroni 有意 cells**: 0 (K=37, α=0.00135) — 多重検定厳密基準では新エッジなし
- **IS/OOS 整合 + 方向性強**: sr_fib_confluence × 3pair が最強候補
  - OOS ΔEV +0.39〜+0.61, ΔWR +14〜+21pp
- **family alignment 効果**:
  - TF DT: +0.238 EV / +9.9pp WR
  - MR DT: +0.199 EV / +5.0pp WR

## Tier 1 候補: sr_fib_confluence × 3 ペア の詳細検証

### BT (/tmp/regime_combo_bt/bt_trades.csv, 365d)
```
Pair     N   aligned_EV  conflict_EV  ΔEV     ΔWR
USD_JPY  150 +0.025      -0.411       +0.436  +15.9pp
EUR_USD  232 +0.074      -0.348       +0.423  +13.6pp
GBP_USD  248 +0.034      -0.328       +0.361  +13.6pp
```
- IS→OOS で効果拡大 (+0.196 → +0.526)
- 月次 9/11 (82%) で ΔEV>0
- Gate適用 BT 予測: 総PnL -27.1R → +22.5R (**+49.6R改善, +182.8%**)

### 本番 Shadow データ (labeled_trades.csv, N=106)
```
alignment    N    WR      mean_pips
aligned      66   30.3%   -2.52p
conflict     35   14.3%   -7.25p
neutral       5    0.0%   -10.62p
→ ΔWR=+16.0pp, Δmean=+4.73p
```
- Gate適用で shadow PnL -472.8p → -219.2p (**+253.6p改善, 53% 損失削減**)
- **ただし** strategy自体は依然として損失。Gate は損失軽減策だが黒字転換しない。
- BT 予測 +49.6R vs shadow 実測 +253.6p ≒ 規模感は整合するが Live EV は依然負

### 本番 LIVE データ — ACTIVE 戦略のみ (N=410, 中 Gate 適用可能な ACTIVE 戦略 は 3)
```
strategy                 live_N  base_PnL  gated_PnL  改善   除外件数
vol_momentum_scalp        18     +4.5p     +21.9p    +17.4p  6  (33%)
vol_surge_detector        45     -5.9p     +1.5p     +7.4p   33 (73%!)
mtf_reversal_confluence   10     +4.9p     +7.9p     +3.0p   1  (10%)
─ Total LIVE ──────────── 410    -173.8p   -117.4p   +56.4p
```

## 判断理由

### 実装しない根拠
1. **sr_fib_confluence は FORCE_DEMOTED (OANDA停止中)**
   - Gate で shadow +253p 改善してもOANDA送信されないため月利貢献ゼロ
   - Gate適用後も Live では負 EV 継続（-2.52p/trade）→ 再活性化は正当化できない

2. **ACTIVE 戦略への Gate 適用は N 不足で判断不能**
   - Live N≥5 で alignment 可変な ACTIVE 戦略はわずか 3つ
   - vol_surge_detector は 73% 除外で実質機能停止
   - 残り 2 戦略 (vol_momentum_scalp, mtf_reversal_confluence) は N=10-18 で有意性検定不能

3. **新 MTF module + 信号パス改修のコストが回収不能**
   - 必要な変更:
     - `modules/mtf_regime_cache.py` 新規（キャッシュ付き D1/H4 ラベラー, ~200行）
     - `modules/demo_trader.py` 信号生成前の regime 計算注入
     - 全 ACTIVE 戦略の signal 関数修正（sr_fib 1 つでは不十分）
     - BT の `_compute_bt_htf_bias` path への MTF 注入
   - 推定工数: 4-6 時間 + BT 検証 + 監査
   - 期待 Live 改善: +56.4p (全ペア, 過去 20日) — 月利寄与 < 1%

4. **CLAUDE.md の判断プロトコル違反になる**
   - 「Live N≥30 で判断」原則 — ACTIVE 戦略の Gate 適用 N=10-45 は未満
   - 「バグ修正 vs パラメータ変更」 — 構造変更は BT 検証後原則

### 保留後のフォローアップ計画
1. **Shadow N 蓄積待ち** — ACTIVE 戦略（trendline_sweep, gbp_deep_pullback, xs_momentum 等）の shadow N が 50 超えたら alignment 効果を再評価
2. **ELITE_LIVE 戦略で LIVE N≥30 達成時の自動検証**
   - `regime_accuracy_scan.py` を週次実行し alignment 効果を追跡
   - ΔEV>+0.1 かつ Live N≥30 の組合せが出現したら実装を再検討
3. **sr_fib_confluence 再活性化は別課題**
   - BT/Live 乖離 -36pp WR の構造的原因は未解明
   - Gate では完全解決しないため、まず BT/Live 乖離の根本原因特定が先

## 保存した分析成果物
- `/tmp/regime_combo_bt/` — 365d BT × regime combo 結果 (N=6,698)
  - `bt_trades.csv` (1MB), `bonferroni_cells.csv`, `is_oos.csv`, `gate_patterns.csv`
- `/tmp/regime_accuracy_scan/labeled_trades.csv` — 本番トレードの MTF regime ラベル (N=2,266)
- `/tmp/sr_fib_validate.py` — sr_fib × 3 pair BT 深堀り検証
- `/tmp/sr_fib_live_validate.py` — sr_fib 本番 shadow 検証
- `/tmp/active_gate_validate.py` — ACTIVE 戦略 Gate 効果検証

## 関連
- [[roadmap-v2.1]] — 月利100%ロードマップ
- `wiki/analyses/mtf-regime-validation-2026-04-17.md` — MTF engine 基礎検証
- `wiki/analyses/bt-live-divergence.md` — BT/Live 乖離の6つの構造的バイアス
- [[2026-04-21-session]] — 本セッションログ

## 結論
**現時点では MTF alignment gate の実装を保留する。**

Gate 効果（ΔEV +0.36〜+0.44, ΔWR +13〜+21pp）は BT + Shadow で確認されているが、
ACTIVE 戦略の LIVE N 不足で月利改善が保証できず、実装コストが回収できない。

ACTIVE 戦略の Live N が増えた時点で再評価し、Live ΔEV>+0.1 かつ N≥30 の組合せが
複数出現してから実装する。
