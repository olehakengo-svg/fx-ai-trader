# Phase 2a / 2a.1 Deploy Status Audit (2026-04-23)

**Session**: MTF gate 中立化 deploy 確認スレッド
**Trigger**: 本セッションでユーザーが「デプロイは完了しているのか確認進めてもらっていい？」と指示
**Scope**: コード側の配線状況確認 (read-only). 新たな統計判定は行っていない.

## Executive summary

| 項目 | 状態 |
|---|---|
| **Phase 2a** (signal enhancer conf_adj 中立化) | ✅ **完了** (3 commits on origin/main) |
| **Phase 2a.1** (MTF aligned gate 中立化) | ⚠ **未配線** (registry 定義はあるが runtime 呼び出しなし) |
| **運用影響** | MTF gate は依然として `conflict → SHADOW 降格` を実行中 |

**重要訂正**: 本セッション初動で「MTF gate を 1-line 中立化して即 deploy」を提案したが、
これは `[[lesson-premature-neutralization-2026-04-23]]` の同じ失敗パターン.
並行セッションが既に Bonferroni 不通過を確認し `[[pre-registration-phase2-cell-level-2026-04-23]]`
と Phase 1 holdout (2026-05-07) で binding criteria を固定済み. **追加 code 変更は holdout 待ち**.

## Phase 2a 配線確認 (完了済)

| Commit | 対象 | 配線状況 |
|---|---|---|
| `b37ee8b` | VWAP zone/slope conf_adj 中立化 | `modules/massive_signals.py` — Phase 2a コード反映済 |
| `2a6d1da` | HVN/LVN + institutional flow 中立化 | `modules/massive_signals.py` — 同上 |
| `91f34ac` | app.py VWAP deviation bonus 中立化 | `app.py` (compute_signal ⑬) — 同上 |

3 commit とも `origin/main` 反映済、Render auto-deploy で本番稼働中.

## Phase 2a.1 配線確認 (未完)

### Registry 定義 (モジュール内)

`modules/strategy_category.py:105-113`:
```python
_POLICY: Dict[str, Dict[Category, float]] = {
    "vwap_zone":           {"TF": 1.0, "MR": -1.0, "BR": 0.5, "OTHER": 0.0},
    "vwap_slope":          {"TF": 1.0, "MR": -1.0, "BR": 0.5, "OTHER": 0.0},
    "institutional_flow":  {"TF": 0.0, "MR": 0.0,  "BR": 0.0, "OTHER": 0.0},
    "mtf_alignment":       {"TF": 0.0, "MR": 0.0,  "BR": 0.0, "OTHER": 0.0},  # ← 定義あり
    "volume_profile_hvn":  {"TF": 0.0, "MR": 0.0,  "BR": 0.0, "OTHER": 0.0},
    "volume_profile_lvn":  {"TF": 0.0, "MR": 1.0,  "BR": 0.0, "OTHER": 0.0},
}
```

### 配線検査 (grep 結果)

```
$ grep -rn "apply_policy" --include="*.py"
modules/strategy_category.py:116:def apply_policy(enhancer: str, ...):  # 定義のみ
```

`apply_policy()` は **どこからも呼ばれていない**. registry は宣言だけで runtime 未配線.

### MTF gate 実際の挙動 (`modules/demo_trader.py:3434-3449`)

```python
# Group A (mtf_gated): conflict なら LIVE→SHADOW 降格
if _gate_group == "mtf_gated":
    if _mtf_alignment == "conflict":
        if not _is_shadow:
            _is_shadow = True                 # ← 依然として稼働中
            _mtf_gate_action = "downgraded"
```

commit `2a6d1da` の body でも明言: 「MTF gate (demo_trader.py:3400-3450) は
aligned (WR 10%) を LIVE 残留、conflict (WR 20.2%) を SHADOW 降格している逆選別の疑い。
**A/B 実験中のため gate 自体は未変更、observation-only**」.

## 本セッションの判断訂正

### 初動提案 (誤り)

「MTF gate を `_is_shadow` 改変停止で即中立化」 — `demo_trader.py:3436` 1箇所変更提案.

### 訂正後の判断 (クオンツ的に正)

1. **N=30 (TF aligned) は Bonferroni 不通過**. `[[quant-validation-label-audit-2026-04-23]]` で
   TF aligned vs conflict: Fisher p=3.56e-01、MR aligned vs conflict: p=1.23e-02 →
   **両方 α=1e-3 (M=50) 不通過**.
2. 並行セッションが既に `[[pre-registration-phase2-cell-level-2026-04-23]]` で
   **action locked: holdout 2026-05-07 まで code 変更禁止**.
3. 私の「即 1-line patch」提案は `[[lesson-premature-neutralization-2026-04-23]]` の
   再発. `feedback_partial_quant_trap` (Wilson + Bonferroni + Fisher + WF) を
   **逆校正判定にも完全適用**する必要.
4. → **Phase 2a.1 deploy は Phase 1 holdout (2026-05-07) 通過まで保留**が正しい.

## Portfolio concentration observations (次セッション引き継ぎ)

本セッションで並行確認したが action には未到達な項目:

| 観察 | 詳細 | 次アクション候補 |
|---|---|---|
| `vwap_mean_reversion` が Live N の ~80% | Simpson 的に集約 EV を歪める | cell-level scan で生存者判定 (pre-registration で carried) |
| ELITE_LIVE 3 戦略 post-cutoff fire=0 | `gbp_deep_pullback` 365d fire=0、`session_time_bias` / `trendline_sweep` post-cutoff fire=0 | entry gate bottleneck 調査 (read-only) |
| `trendline_sweep` shadow fire rate 10/18d = 0.56/day | BT 207/365 = 0.57/day と整合、regression ではない | 判断: 問題なし |
| Aggregate Kelly f* = -7.81% (N=10) | concentration で歪み、aggregate 計算は無意味 | **per-strategy Kelly** 設計に移行 |

## Lesson adherence 自己チェック

本セッションで以下を遵守:
- ✅ ユーザー challenge (「クオンツとしては？」「統計的に厳格に」) を diagnostic 信号として受容
- ✅ 統計閾値 (Wilson CI + Bonferroni) を再計算し N=30 不十分と認定
- ✅ 並行セッションの pre-registration を尊重、独自 code 変更を提案せず
- ❌ 初動で「即 patch deploy」と言ってしまった (lesson-premature-neutralization 再発リスク) →
     本 doc で明示的に訂正記録

## Next-session checklist

新セッション開始時に確認すべき項目:

1. **Scenario A 確定後の戦略判断**: `[[cell-level-scan-2026-04-23]]` で **GO 0 / CANDIDATE 0**
   (240 cells 全て regime mismatch). Phase 1 holdout (2026-05-07) 通過待ち、または
   Phase 3 stopping rule / 新戦略設計 (Phase 4) への移行判断
2. **Phase 1 holdout window の状態**: Apr 24–May 7 の期間で `[[pre-registration-label-holdout-2026-05-07]]`
   の binding criteria を満たすか (code 変更は holdout 後)
3. **ELITE_LIVE 0-fire 調査 (read-only)**: `gbp_deep_pullback`, `session_time_bias`,
   `trendline_sweep` の entry gate bottleneck を grep + code read で特定. Kelly Half
   gate が意味を持つための分母情報. Scenario A との関係検証
4. **Portfolio concentration 診断**: `vwap_mean_reversion × EUR_USD × BUY` 等の cell を
   cell-level scan 結果で追跡、observational only
5. **本 doc と並行セッション成果を統合**: 本セッションの deploy status 確認 +
   並行セッションの Bonferroni 検定 + Scenario A 確定 = Phase 2a.1 全体像

## References

- [[quant-validation-label-audit-2026-04-23]] — Bonferroni + Fisher + WF (並行セッション成果)
- [[phase0-data-integrity-2026-04-23]] — shadow data 健全性 ✓
- [[pre-registration-phase2-cell-level-2026-04-23]] — cell-level scan 計画
- [[pre-registration-label-holdout-2026-05-07]] — holdout 窓
- [[mtf-gate-category-audit-2026-04-23]] — TF/MR/OTHER category 別分解
- [[lesson-premature-neutralization-2026-04-23]] — 本セッション初動の失敗パターン
- [[lesson-why-missed-inversion-meta-2026-04-23]] — 実装監査と運用監査の分離
- Commit 履歴: `b37ee8b`, `2a6d1da`, `91f34ac` (Phase 2a)、`9787dd8` (registry)
