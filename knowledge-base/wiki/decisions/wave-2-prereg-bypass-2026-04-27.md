# Wave 2 Pre-reg Bypass Decision (2026-04-27)

## Status
**rule:R1-bypass** — CLAUDE.md の Rule 1 (新フィルタ → 365日BT + Bonferroni + Pre-reg LOCK) を**ユーザー判断で意図的にバイパス**して導入。本ドキュメントが事後 audit trail。

## Context
ユーザーから配布された FX/EA 学術論文13本パッケージ (`~/Downloads/files.zip`) を分析し、現システムに足りない要素として9カテゴリ・11項目の改善案を提示。
ユーザーは Wave 2 として **A2 (SL clamp)** + **A3 (cost throttle)** + **A4 (vol-scaled confidence)** の3項目を承認、Rule 1 をバイパスしての即実装を選択(オプション4)。

承認時のplanファイル: [users-jg-n-012-downloads-files-zip-cozy-finch.md](../../../../.claude/plans/users-jg-n-012-downloads-files-zip-cozy-finch.md)

## Changes

### A2 — SL/TP制約レンジ
- **出典**: B3_Constraint_Heuristics (10年データ・3通貨ML、SL∈[3,50]pip)
- **修正**: [app.py:807-826](../../../app.py) `calc_sl_tp_v3()` に SL pip clamp を追加
  - 下限 3pip: 全TF適用
  - 上限 50pip: 短期TF (1m/5m/15m/30m/1h) のみ
  - clamp 発動時は `min_rr+0.3` で TP を再計算
- **N1 検証 (2026-04-27)**: 既存 N=373 のうち
  - SL <3pip: N=36 (全 Shadow scalp_eur, min=3.0 で実質既に floor を満たす)
  - SL >50pip: N=0 (clamp 非発火)
  - **結論: 現データ上は実質 no-op、将来コードパスへの guardrail として機能**

### A3 — Cost-aware Frequency Throttle
- **出典**: C3_Ishikawa Online DRL (cost 0.01%→0.05% で WR 59.5%→49.2%, Sharpe 2.04→0.68)
- **修正**:
  - [friction_model_v2.py:163-205](../../../modules/friction_model_v2.py) に `cost_throttle_factor()` 追加
  - [app.py:3879-3905](../../../app.py) daytrade path R2-A 直後で適用
- **threshold=1.55 (empirical adjustment)**:
  - 当初案 1.5 で N1 検証時に **Tokyo Scalp (ratio=1.52, N=44 WR=61.4% EV=+5.89pip)** が誤発火 → 利益セルを破壊するリスク
  - **threshold を 1.55 に引き上げ** Tokyo Scalp(1.52)を保護、Sydney DT(1.60) / Asia_early DT(1.55) / Sydney Scalp(1.68) のみ throttle 維持
  - 現 demo_trades.db には Sydney/Asia_early データなし → 発火実例ゼロ (将来データ次第)

### A4 — Vol-scaled Confidence
- **出典**: C2_Zhang DRL (vol-targeting reward, 60日窓)
- **修正**:
  - [app.py:7487-7497](../../../app.py) `detect_market_regime()` に `vol_scale = clip(1.5/atr_ratio, 0.5, 1.5)` 追加
  - HIGH_VOL閾値 **1.8 → 2.5** に引き上げ (extreme時のみbinary mute維持)
  - [app.py:3907-3920](../../../app.py) daytrade path で confidence × vol_scale
- **N1 検証**: demo_trades.db の `regime` カラムが空のため atr_ratio遡及不可。Live observation で検証予定。
- **applied scope**: daytrade path のみ。swing/scalp は未適用 (R2-A と同じ scope)。

## Rule 1 Bypass の根拠と検証計画

### バイパスの判断
- ユーザー明示の判断 (option 4 選択)
- A2/A4 の効果は数学的(下限/連続化) で empirical 検証なしでも妥当
- A3 のみ重要な閾値判断あり → N1 で empirical adjustment 実施済 (1.5→1.55)

### Live observation 検証計画
1. **発動頻度モニタ**: `reasons` フィールドに `A2 / A3 cost throttle / A4 vol_scale` を記録、daily で発火率を集計
2. **発動率の警報閾値**:
   - A2 SL clamp: 全トレードの 5% 超で発動 → 過剰、再 calibration
   - A3 cost throttle: Sydney/Asia_early で 100% / 他で 0% を期待
   - A4 vol_scale: 平均 0.9〜1.1 を期待 (極端なら閾値見直し)
3. **2週間後の遡及検証**: N=400+ で A2/A3/A4 適用 cell の WR/EV vs baseline cell を Wilson CI 比較
4. **問題があれば即 revert**: 各変更は独立コミットでロールバック可能

## Tests

- 既存 `pytest tests/` 全 **407 passed** (regression なし)
- A3 unit test: 6/6 cases pass (threshold=1.55 で Tokyo Scalp 保護を確認)
- A2 算術検証: 0.45pip→3pip, 75pip→50pip clamp 正常、4h は upper clamp スルー、JPY/non-JPY pip 変換正常

## Failure Mode (lesson 化条件)

以下のいずれかが満たされた場合、本決定は**失敗**として `wiki/lessons/` 行きとする:
- A3 throttle が profitable cell (WR>50% N≥20) を継続的に抑制
- A4 vol_scale で HIGH_VOL 1.8〜2.5帯のトレードが atr_ratio<1.8 帯より EV低下
- A2 SL clamp で 1m/5m scalp の WR/EV が悪化 (N1で安全と判断したが逆転リスク)
- いずれも 2026-05-11 までに見直し決定

## References

- [Plan file (approved)](/Users/jg-n-012/.claude/plans/users-jg-n-012-downloads-files-zip-cozy-finch.md)
- [B3_Constraint_Heuristics PDF](/Users/jg-n-012/Downloads/files_unpacked/B3_Constraint_Heuristics.pdf)
- [C2_Zhang_DRL_Trading PDF](/Users/jg-n-012/Downloads/files_unpacked/C2_Zhang_DRL_Trading.pdf)
- [C3_Ishikawa_Online_DRL PDF](/Users/jg-n-012/Downloads/files_unpacked/C3_Ishikawa_Online_DRL.pdf)
- [edge-reset-direction-2026-04-26.md](edge-reset-direction-2026-04-26.md) (Phase 1 Edge Reset 決定)
- [CLAUDE.md Rule 1/2/3](../../../CLAUDE.md)

## Next Actions
1. **N3 commit**: A2/A3/A4 を独立3コミットに分割 (個別 revert 可能性確保)
2. **Wave 3 N5**: features table 永続化を着手 (B1 features ストア = A1/B2/B3 の前提)
3. **2週間後 (2026-05-11)**: 遡及検証で本ドキュメントの failure mode に該当しないか確認
