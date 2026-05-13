# Regime-Gate Phase E 司令塔 verdict (2026-05-13)

## 経緯

[Tier A](regime-gate-tier-a-2026-05-12.md) → [Phase B2.5](regime-gate-phase-b25-2026-05-13.md) → **Phase E (Universal Tagging + Composite Cell Analysis)**。

ユーザー指示で 2 段階の design 改訂を経て確定:
- Phase E 初版 (司令塔単独): 17 variant entry_type を pre-register する static design — **棄却**
- Phase E v2 (ユーザー提案): 全 trade に dow_regime + v2_regime tag、composite cell で勝ち探索 — **採用後、partial validation**

| Phase | 内容 | Commit | Verdict |
|---|---|---|---|
| E1a | dow_regime universal tagging 実装 | `c05a86b3` | ✅ Production 影響なし、観測層完成 |
| E1b | Classifier consensus consultation (Codex + Claude sub-agent) | `c05a86b3` | ✅ 両 opinion 獲得、共通合意「17 を Live promote しない」 |
| E1c | ユーザー提案 composite classifier 採用 | (議論) | ✅ design 確定 |
| E1d | v2_regime universal tagging 実装 | `13755b54` | ✅ Production 影響なし、dow と並走で観測 |
| **E2** | **Composite cell retrospective analysis** | `13755b54` | ⚠️ **HOLD_GAP5_COMPOSITE** |

## Phase E2 主結論

### ❌ Universal composite gate は single classifier に劣る

| Model | Brier score | Log loss |
|---|--:|--:|
| **v2_only** | **0.24015** | **0.67332** ← 最良 |
| dow_only | 0.24033 | 0.67368 |
| composite (dow+v2) | 0.24040 | 0.67383 ← 最悪 |

→ Composite を **universal rule** として gate 適用する根拠なし。

### ✅ しかし strategy-specific composite cells に structural edge 存在

Bonferroni 通過 10 cells (effective m=46, α' = 0.00109):

| Strategy | Dow | V2 | N | WR | EV (pip) | PF | Wilson_lo |
|---|---|---|--:|--:|--:|--:|--:|
| streak_reversal | CHOP | **no_go** | 245 | 70.2% | +0.93 | 2.25 | 0.64 |
| session_time_bias | CHOP | **no_go** | 649 | 61.6% | +0.08 | 1.11 | 0.58 |
| streak_reversal | TRENDING | **no_go** | 98 | 76.5% | +1.31 | 3.54 | 0.67 |
| xs_momentum | TRENDING | **no_go** | 312 | 64.7% | +0.17 | 1.27 | 0.59 |
| streak_reversal | RANGING | **no_go** | 80 | 75.0% | +1.03 | 2.32 | 0.65 |
| sr_anti_hunt_bounce | CHOP | **no_go** | 43 | 83.7% | +4.44 | 5.62 | 0.70 |
| session_time_bias | TRENDING | **no_go** | 178 | 66.3% | +0.25 | 1.41 | 0.59 |
| trendline_sweep | CHOP | **no_go** | 78 | 71.8% | +0.64 | 1.79 | 0.61 |
| session_time_bias | RANGING | **no_go** | 200 | 63.5% | +0.13 | 1.18 | 0.57 |
| vix_carry_unwind | CHOP | **no_go** | 32 | 78.1% | +0.97 | 2.26 | 0.61 |

### 🔥 重大な気付き — 全 10 通過 cells が `v2_regime = no_go`

これは深い意味を持つ:

1. **v2 calibration の境界**: `modules/regime_classifier.py` v2 は **bb_rsi_reversion / ema_trend_scalp / dt_bb_rsi_mr 等の MR family** に対して `moderate_trend` を勝ち域と判定する best fit
2. **逆向き edge の発見**: streak_reversal / sr_anti_hunt_bounce / xs_momentum / session_time_bias / trendline_sweep / vix_carry_unwind は **v2 = no_go の "死域" で structurally 勝つ**
3. **Universal classifier の限界**: 単一 classifier (v2 binary or Dow 3-class) は **戦略 family ごとに最適 regime が異なる** 事実を捉えられない
4. **Strategy-specific cell ID 運用**: composite は universal gate でなく **(entry_type × dow × v2) cell ID として個別判定** するのが正解

### Memory 整合性確認

- ✅ `feedback_ma_filter_breaks_mr` (filter 一律適用は MR で edge 殺す): 本 verdict と整合、universal gate は誤り
- ✅ `feedback_partial_quant_trap` (PF/Wilson/Bonferroni 完備): m_eff=46 で適切に補正済
- ✅ `feedback_shadow_first_quant_architecture` (BT は sanity、Shadow が estimator): Phase E2 は **retrospective hypothesis-forming only**、Live 昇格根拠としない
- ✅ `feedback_label_empirical_audit` (コード演繹禁止、実測必須): 10 cells は実測 N≥30 + Bonferroni 通過

## Phase E 確定 framework

### Universal Tagging (実装済、継続運用)

- `demo_trades.dow_regime` TEXT — H1 ADX/ER/BBW 3-class (`TRENDING`/`RANGING`/`CHOP`/`NULL`)
- `demo_trades.v2_regime` TEXT — M15 binary (`moderate_trend`/`no_go`/`NULL`)
- signal 時点で classifier 呼出、best-effort fail-safe (失敗時 None、signal block しない)
- Live / Shadow / FLAG_DRIFT 全 cohort で同条件 tagging
- 時間帯軸は `entry_time` から自動計算可

### Live 昇格基準 (Pre-Reg, Rule 1)

任意の (entry_type × dow_regime × v2_regime) cell について:

| 条件 | 閾値 |
|---|---|
| Forward Shadow N | ≥ 30 |
| Wilson_lo | ≥ 0.55 |
| Bonferroni 通過 | α' = 0.05 / m_eff |
| BT/Shadow EV 整合 | 符号反転禁止 |
| Cohort time check | demote/promote 履歴で歴史データと混同しない (`feedback_cohort_time_check`) |
| LIVE/Shadow 分離 | is_shadow=1 のみで集計 (`feedback_live_shadow_separation`) |

### Non-Universal Gate 原則

- composite を **universal rule** として live runner に組込しない
- 個別 cell が pre-reg 通過した場合のみ、その特定 (entry_type × dow × v2) のみ Live 昇格
- 他 cell には影響しない (purely additive)

## 10 cells の Phase E3 候補化 (forward Shadow validation)

上記 10 cells は **retrospective Bonferroni 通過 hypothesis**。**Live 昇格判定の根拠としない**。
Forward 実 Shadow N で再 Bonferroni 通過後のみ candidate 化:

| Phase | 内容 | 期間目安 |
|---|---|---|
| E3 | Forward Shadow N≥30 per cell 蓄積待ち | ~4-8 週 |
| E4 | Forward N で再 Bonferroni 通過 cell 識別 | E3 完了後 |
| E5 | 通過 cell の Live 昇格 pre-reg | 個別判断 |

## 棄却した design

| 棄却 design | 理由 |
|---|---|
| Phase E 初版: 17 variant entry_type pre-register | composite Brier が単体に劣る、universal pre-register は post-hoc 罠 |
| Dow classifier 単独 universal gate | v2_only より prediction power 弱、`feedback_ma_filter_breaks_mr` 罠 |
| v2 classifier 単独 universal gate | 10 cells が v2=no_go で勝つ事実と矛盾、family 別最適 regime あり |
| Composite universal gate | 上記 3 軸全て universal は誤り |

## 司令塔の反省

Tier A 〜 Phase B2.5 で **誤った Tier A 数字**を信用、Phase B2.5 で **production-fair measurement** を回復、Phase E1 で **司令塔単独設計を pre-register variant 化** で複雑化させた。ユーザー指摘 ("regime tag を全戦略につける") で **observation-first design** に切替、Phase E2 で **strategy-specific cell の存在** を実測確認できた。**司令塔の単独判断より、ユーザーの quant 直感が複数回優れた** ことを記録。

## 参照

- [Tier A verdict](regime-gate-tier-a-2026-05-12.md)
- [Phase B2.5 verdict](regime-gate-phase-b25-2026-05-13.md)
- Composite analysis artifacts: `reports/composite_cell_analysis/`
- v2 tagging implementation: `modules/demo_db.py` / `modules/demo_trader.py` (commit `13755b54`)
- Classifier consensus: `reports/regime_classifier_consensus/` (commit `c05a86b3`)
- Memory: `feedback_ma_filter_breaks_mr`, `feedback_partial_quant_trap`, `feedback_shadow_first_quant_architecture`

## Verdict

**Phase E は Universal Observation Layer として完成 (commit `13755b54`)。Composite は strategy-specific cell ID として運用、universal gate にしない。10 Bonferroni cells は forward Shadow validation 待ち、Live 昇格は forward N≥30 通過後の個別判断のみ。**

次は **Phase F (Gap 1 cross-pair confluence)** を並走で着手 (Phase E は forward N 蓄積中で待機可)。
