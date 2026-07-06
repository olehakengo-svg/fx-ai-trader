# Fable5 監査 Phase A 修正バッチ — P0-1 / P0-2 / P1-1 (2026-07-03/04)

**Rule**: R2 (P0-1 = lot↓) + R3 (P0-2 / P1-1 = 診断済み構造バグ) — 365日BT 不要カテゴリ
**根拠**: [[fable5-system-audit-2026-07-02]] の CONFIRMED findings + 2026-07-03 の 22-agent 全件再照合 (origin/main 直読、FIXED 主張は敵対的クロスチェック済み)
**動機記録**: データ駆動 (監査で診断済みの構造欠陥×3)。感情的動機ではない。P0-1 は user 決裁 2026-07-03 を執行。

---

## P0-1: edge cell force-live に DD defensive multiplier を適用 (user 決裁)

### 問題
`_adjusted_units = _edge_cell_lot` の生値代入 (2箇所) により、edge cell
force-live 経路が DD defensive 0.2x を完全バイパスしていた。
`_resolve_units_with_multiplier` も edge cell は素通し設計、コメントは
「pre-reg LOCK: 固定 lot は乗算しない」で意図的の体裁だが、**DD defensive
時の挙動は未検証・未文書化** (全テストが `_dd_lot_mult=1.0` 固定)。
DD defensive 下でも stage3 セルは 10000u フル送信 — 最も資金が枯渇している
局面で最大ロットが飛ぶ構造。

### user 判断 (2026-07-03)
3択 (①DD mult + 1000u floor / ②バイパスを設計として明文化 / ③floor なし完全適用)
のうち **① DD mult 適用 + 1000u floor** を選択。

### 修正 (pre-reg LOCK 修正条項)
```python
_edge_cell_units = max(1000, int(_edge_cell_lot * float(self._dd_lot_mult or 1.0)))
```
- 口座防御 (DD 0.2x) が pre-reg 固定サイズの統計的純度に優先する
- min 1000u floor により、defensive 中もクリーン N 蓄積は継続 (Sentinel と同じ最小契約単位)
- 縮小時は `[EDGE_CELL] {cell} DD defensive sizing` ログ + lot_tag `(EDGE-Ex 🛡️DD20%)` で観測可能
- exposure_manager への登録も実効 units に統一 (過大 exposure block の副作用防止)
- 例: stage1 5000u→1000u / stage2 7500u→1500u / stage3 10000u→2000u (DD≥8% の 0.2x 時)

### 影響セル
現在 active な cell は E2 / E9 のみ (E1/E4/E8/E10 は code pin 済み)。
DD defensive 継続中は E2/E9 のマッチトレードが縮小サイズで送信される。
**per-cell Kelly/EV 評価は pips ベースのため縮小の影響なし** (lot は EV に非影響)。

### テスト
`tests/test_edge_cell_dd_defensive_units.py` — 5 ケース (stage1/3 × mult 0.2/1.0 + floor 発動) + ログ検証×2

---

## P0-2: `_sync_demo_to_oanda` 孤児クローズに openTime 年齢ガード

### 問題
5秒毎の孤児スイープが openTime を見ずに即クローズ。fire-and-forget fill →
DB write-back 完了前に再起動/デプロイが挟まると、正規 live ポジションを
再起動 ~5 秒で誤クローズしうる (テストカバレッジゼロだった)。

### 修正
- `_ORPHAN_MIN_AGE_SEC = 600` (Render deploy 所要 ~数分 を覆う余裕を持たせた 10 分)
- openTime (OANDA v20 ナノ秒 RFC3339) を秒精度で parse し、若い trade はスキップして次周期再判定
- **parse 不能 / openTime 欠落も fail-safe スキップ** (誤クローズ > 遅延クローズ)
- コスト: 真の孤児のクローズが最大 ~10 分遅延 (許容)

### テスト
`tests/test_sync_demo_to_oanda_age_guard.py` — 5 ケース (old close / young skip / garbage skip / mapped 除外 / 境界)

---

## P1-1: `_get_strategy_kelly` を clean 版へ委譲 (汚染除去)

### 問題
`_get_strategy_kelly` だけ FIDELITY_CUTOFF / XAU / is_shadow フィルタが無く、
実弾サイジング 2 経路 (dynamic Kelly boost / half-Kelly lot cap) + shadow
promotion 判定が all-time 汚染データで駆動されていた。
**実害の実測**: 本番 `/api/risk/dashboard` で T10 KILL 済み bb_rsi_reversion に
`full_kelly=0.2672 / half=0.1336 / WR=72.7%` が推奨され続けていた (2026-07-03、
pre-cutoff 遺産データ由来)。CLAUDE.md「All-time data を Kelly に使わない」に直接抵触。

### 修正
本体を `_get_strategy_kelly_clean(entry_type)` への委譲に置換 (SSOT 正規化)。
instrument 引数は呼び出し互換のため残置 (旧実装でもフィルタ未使用だった)。
効果: クリーン N<10 の戦略は boost/cap 不発 (None) — pre-cutoff 遺産だけで
Kelly 推奨を得る経路が閉じる。

### テスト
`tests/test_strategy_kelly_clean_delegation.py` — 4 ケース (汚染除外 / 委譲一致 / clean N<10 → None / entry_type スコープ)

---

## レビューで発見された新規事項 (本バッチのスコープ外、既存バグ)

- **P1-9 (新規)**: `_get_strategy_kelly_clean` は clip 済み `full_kelly` (`max(0,·)`) を返すため、
  `_shadow_promotion_decision` 側の `_kelly_block = (_kelly_f < 0)` 負値判定が**構造的に不発**。
  `_get_aggregate_kelly` で修正済み (60652ac1) の「死にゲート」と同型 — `full_kelly_raw` 化が必要。
  2026-07-04 の敵対的レビューで検出。Phase B に積む。

## 残る Phase A 項目
- P1-5: 表示 DD 分母は本番実測で 1000 ハードコード産物と確定済み (dd_pct=989.7/1000 丁度)。
  残り = Render env `OANDA_EQ_BASE_PIPS` 実値確認 (CLI token 失効中 → `render login` 後)。
  ※どちらでも DD≥8% → 0.2x は不変 (DD_LOT_TIERS 構造上、lot 挙動への影響なし)
- Phase B/C: [[fable5-system-audit-2026-07-02]] のロードマップ参照
