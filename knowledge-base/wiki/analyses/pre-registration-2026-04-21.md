# Pre-Registration: bb_squeeze_breakout / vol_surge_detector × USD_JPY LIVE Promotion

**登録日**: 2026-04-21 (LIVE データ到来**前**に登録 — post-hoc bias 排除のため)
**評価期日**: 2026-05-05 (14 日後、N 蓄積状況により延長可)
**最終期日**: 2026-06-02 (42 日後、強制判定)

---

## 目的

2026-04-21 commits (`db12a07`, `6c5a516`) で 2戦略×USD_JPY が LIVE tier に昇格。
**LIVE データが観測される前に** 評価基準を事前宣言することで:

1. Post-hoc rationalization を防ぐ ([[lesson-shadow-contamination]] / Phase 3 教訓の制度化)
2. Confirmation bias を排除
3. 「感情的再開」「感情的継続」両方向の判断誤りを防ぐ

本文書は **binding** — 本文書の基準を満たさない観察結果を基に promotion/demotion 判断を変更する場合は、必ずここへ追記 (理由と共に).

---

## 1. Strategy-Specific Hypotheses

### H1: bb_squeeze_breakout × USD_JPY

**Primary hypothesis**: USD_JPY 5m scalp で PF > 1.1 かつ WR > BEV (34.4%) を LIVE で維持できる.

**Null hypothesis**: LIVE EV = 0 (friction-only、エッジなし).

**Pre-BT estimates** (commit `9918057`):
- 365d BT: N=43, WR=74.4%, EV=+0.354 pip, PF=1.818
- Wilson 95% CI for WR: [59.8%, 85.1%]
- WF 3バケット全正 (+0.09, +1.03, +0.45)

### H2: vol_surge_detector × USD_JPY

**Primary hypothesis**: USD_JPY 5m scalp で PF > 1.1 かつ WR > BEV を LIVE で維持できる.

**Null hypothesis**: LIVE EV = 0.

**Pre-BT estimates** (commit `6c5a516`):
- 365d BT: N=50, WR=68.0%, EV=+0.242 pip, PF=1.811
- Wilson 95% CI: [54.2%, 79.2%]
- WF 3バケット全正 (+0.28, +0.86, +0.14)

---

## 2. Observation Protocol

### Data window
- **Start**: 初回 LIVE trade の約定時刻 (Render auto-deploy 後)
- **End**: 下記 decision rule のいずれかが発火した時点

### Included trades
- `is_shadow == 0` **のみ** (LIVE 実弾のみ)
- `instrument == "USD_JPY"` **のみ**
- `entry_type` が対象戦略と一致
- `outcome IN ("WIN", "LOSS")` (OPEN 除外)

### Excluded trades
- Shadow trades (Phase 3 誤診防止)
- 他ペア (EUR_USD/GBP_USD は PAIR_DEMOTED 継続中)
- エラー/キャンセル/close_reason 異常 (gate_leak 等)

---

## 3. Decision Rules (pre-specified)

### 3.1 bb_squeeze_breakout × USD_JPY

| 到達 N | 条件 | Action |
|---|---|---|
| N=10 | Wilson 95% CI 下限 < 20% | **即時 PAIR_DEMOTE** (BT 乖離が致命的) |
| N=15 | WR < 40% かつ sum_pnl < -5 pip | **即時 PAIR_DEMOTE** |
| N=20 | PF < 0.9 | **即時 PAIR_DEMOTE** |
| N=30 | PF ≥ 1.3 かつ Wilson 下限 > BEV (34.4%) | **継続、現 lot 維持** |
| N=30 | PF ≥ 1.5 かつ Sharpe > 0.25 | **lot 1.3x へ昇格** (Kelly Half 近似) |
| N=30 | 上記いずれも満たさない | **SCALP_SENTINEL へ格下げ** (sentinel lot 継続観察) |

**Binding な最低観察期間**: 14日 or N=10 の大きい方。早期 demotion は N=10 + Wilson 下限 < 20% の時のみ発火.

### 3.2 vol_surge_detector × USD_JPY

| 到達 N | 条件 | Action |
|---|---|---|
| N=10 | Wilson 95% CI 下限 < 20% | **即時 PAIR_DEMOTE 再設定** |
| N=15 | WR < 40% かつ sum_pnl < -5 pip | **即時 PAIR_DEMOTE 再設定** |
| N=20 | PF < 0.9 | **即時 PAIR_DEMOTE 再設定** |
| N=30 | PF ≥ 1.3 かつ Wilson 下限 > BEV | **PAIR_PROMOTED 昇格** (sentinel → full lot) |
| N=30 | 上記満たさず PF ≥ 1.0 | **SCALP_SENTINEL 継続** (再観察) |

---

## 4. Multiple Testing Correction

**問題**: 2026-04-21 の promotion 判断で 6 pair × 2 strategy = 12 セルを検定.

**Bonferroni correction**: α_family = 0.05 → α_cell = 0.05/12 = **0.00417**

**影響再計算** (Wilson CI を 99.58% で再計算):
- bb_squeeze USD_JPY 99.58% CI ≈ [53%, 88%] — 下限 > 34.4% ✓ **robust**
- vol_surge USD_JPY 99.58% CI ≈ [47%, 84%] — 下限 > 34.4% ✓ **robust**

結論: Bonferroni 補正後も両決定は有意. **promotion 維持**.

---

## 5. Kelly Criterion for Lot Sizing

### bb_squeeze × USD_JPY (BT-derived, PAIR_PROMOTED 適用済み 1.0x)
- p = 0.744, q = 0.256
- W (avg win) = 50.03/32 = 1.563 pip
- L (avg loss) = 27.52/11 = 2.502 pip
- **Kelly full** = (p·W - q·L) / (W·L) = 0.522 / 3.910 = **0.134 (13.4%)**
- **Kelly Half** = 6.7%

現在 lot 1.0x (base) は Kelly Half に相当. N=30 到達で PF ≥ 1.5 なら 1.3x 昇格可.

### vol_surge × USD_JPY (BT-derived, SCALP_SENTINEL 適用)
- p = 0.68, q = 0.32
- W = 46.3/34 = 1.362 pip
- L = 25.6/16 = 1.600 pip
- **Kelly full** = (0.68·1.362 - 0.32·1.600) / (1.362·1.600) = 0.414 / 2.179 = **0.190 (19.0%)**
- **Kelly Half** = 9.5%

SCALP_SENTINEL は sentinel 最小ロット → Kelly Half より保守的. N=30 到達で PAIR_PROMOTED 昇格時、base (1.0x) 適用でも Kelly Half に近い.

---

## 6. Sensitivity Analyses (pre-specified)

LIVE データ評価時に**必ず**実行する追加分析:

1. **Regime breakdown**: range_tight / range_wide / trend_* 別の EV
   - 依存性が極端 (例: range_tight でのみ正 EV) なら regime-conditional promotion を検討
2. **Time-of-day**: Tokyo/London/NY セッション別の WR/EV
3. **Spread-conditional**: spread < median vs spread > median の EV 比較
4. **Consecutive loss streak**: 5連敗以上が出現したら追加監査

---

## 7. Amendment Policy

本文書は **binding**. 変更は以下のみ許容:

1. **誤字・計算ミス訂正**: 即時可 (理由を末尾に追記)
2. **観察期間延長**: N が想定より少ない場合のみ (N < 10 at day 14 等). user 承認要
3. **早期停止以外の decision rule 変更**: **不可** (観察データ到来後は特に不可)

緊急停止 (戦略が明らかに暴走): user 判断で override 可. 本文書に事後記録.

---

## 8. Audit Trail

本文書は **LIVE データ観測前** に作成 (2026-04-21). 
commits `db12a07` / `6c5a516` のデプロイ前 pre-registration.

関連:
- [[bb-squeeze-breakout]] — 365d BT + 深部分析
- [[vol-surge-detector]] — 365d BT + 深部分析
- [[negative-strategy-stop-conditions-2026-04-21]] — negative 戦略側の対称文書
- [[lesson-shadow-contamination]] — Phase 3 教訓
- [[2026-04-21-session]] — 経緯

---

## 9. Sign-off

- [x] 2026-04-21 作成、LIVE データ到来**前**にコミット
- [ ] 2026-05-05 中間評価 (予定)
- [ ] 2026-06-02 最終評価 (予定)
- [ ] Amendment log (none yet)
