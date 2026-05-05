# FX Nexus Step 1 — Claude Quant Review Verdict

- Decision date: 2026-05-05
- Reviewed task: `.ai/tasks/done/20260504T1753-fx-nexus-step1-shadow.md`
- Reviewed branch: `feature/fx-nexus-step1-shadow-audit` @ `3443cf2`
- Reviewer: Claude (司令塔)
- Codex run: 519s, exit=0

## Verdict: **NEEDS_MORE_EVIDENCE**

実装は ACCEPT 相当（TDD 通過、pytest 933 passed + 1 xfailed、scope 外変更も後方互換確認）。
ただし 3 仮説すべて pre-reg ACCEPT 帯に到達せず、Wave 5 α reversion 戦略 spec 起票の条件不成立。

## 仮説別判定（pre-reg LOCK 基準照合）

### H1 V_ti: NEEDS_MORE
- Wilson lower=0.5010（基準 ≥0.51 で ACCEPT、0.49-0.51 NM）→ NM 帯の境界値
- 他指標（condition number 1.41 / corr 0.978 / N=29968）は ACCEPT 帯
- 結論: **境界値で NM**。次回 12 ヶ月で再観測

### H2 α residual: NEEDS_MORE（部分的有意発見あり）
- Bonferroni 補正後 p<0.01 のペア: **GBP_USD (p=0.0014)**, **EUR_JPY (p=0.0005)** = **2/5**
- pre-reg 基準: 5/5 ACCEPT → **NEEDS_MORE**
- 重要な robustness 確認:
  - α vs spread 相関 = 0.0024 → α は spread の影 ではない（真の残差シグナル）
  - α autocorr lag1 = 0.2567 → MR 性質確認
  - LIVE entry KW p=1.0000 → 既存戦略は α を全く活用していない
- **未活用エッジが 2 ペアに存在する可能性**を示唆するが、post-hoc selection 罠回避のため 5/5 基準を堅持
- 次セッションで Wave 5 spec 起票は **不可**。次の 12 ヶ月 OOS 再観測で 2 ペアの再現性を確認すべき

### H3 τ_exec jitter: 実質 REJECT（テスト不成立）
- SRM N=0, asia_range_fade_v1 N=0（15m parquet cache 全滅）
- 「PF drop=0.0000」は実験不成立を示す N=0 由来。lookahead 検出機能の検証として **無効**
- Codex verdict は NEEDS_MORE だが、厳密には REJECT 相当（再走必須）

## scope 外変更の精査

| ファイル | 変更内容 | 判定 |
|---|---|---|
| `app.py` (+25/-4) | `run_daytrade_backtest` に `exec_lag_jitter` 引数追加（default 0.0） | ACCEPT — spec §4.3 を実体化、後方互換 |
| `modules/demo_trader.py` (+33/-4) | `SHADOW_AUDIT_REASONS` 等 4 symbol 追加 + `_resolve_shadow_audit_block_reason(True, "shadow_tracking")` 経由化 | ACCEPT — pre-commit blocker 解消、`is_shadow=True` 時の戻り値は `"shadow_tracking"` で従来挙動と意味論的同等 |

LIVE 経路への意味論的影響なし。pytest 933 passed + 1 xfailed で regression 0 を確認。

## データ分離・安全性

- ✓ feature branch のみ、main 未マージ
- ✓ Render 本番未デプロイ
- ✓ `basket_strength()` シグネチャ無変更
- ✓ shadow / LIVE 分離保持
- ✓ XAU 除外
- ⚠ PR は GitHub PAT 権限不足で未作成（手動作成必要）

## ロードマップ寄与

- Gate 0/1/2 への直接前進 **なし**（本タスクは critical path 外の P2）
- H2 で GBP_USD/EUR_JPY に未開発 α エッジの可能性を発見、ただし pre-reg 基準不成立で Wave 5 起票不可
- Tier 1 Edge Audit が DESIGN_BROKEN ≥ 3 で HALT 中（commit `0f91904`）→ こちらが Gate 1 unblock の主経路

## 後続アクション

1. **H3 再走 blocker**: 15m parquet cache 整備（USDJPY=X / EURUSD=X 等）— 別 P3 タスクで先行整備推奨
2. **H1/H2 再観測**: 2026-11-04 (6 ヶ月後) に同 audit を自動再走（cron 化）
3. **GBP_USD / EUR_JPY α 有意の post-hoc 罠回避**: 5/5 基準を変更しない。OOS 期間で 2 ペアが維持されたら Wave 5 検討
4. **Wave 5 α reversion 戦略 spec 起票**: 本タスク結果では条件不成立、見送り
