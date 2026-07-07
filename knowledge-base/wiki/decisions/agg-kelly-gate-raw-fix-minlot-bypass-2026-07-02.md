# Aggregate Kelly Gate raw-fix + 1000u 固定契約 min-lot bypass (2026-07-02)

**Date**: 2026-07-02
**Rule**: R3 (構造バグ — 死にゲート) + R2 (interplay 設計, user 決裁)
**Decision**: (a) `kelly_criterion` に非クリップ `full_kelly_raw` 追加 + `_get_aggregate_kelly` raw 化, (b) 1000u 固定契約 3 戦略の min-lot bypass (二重ガード)
**User 決裁**: 2026-07-02 — (a)(b) とも推奨案を承認。単独 fix 禁止指示に従い同一 pre-reg で決裁
**Tier/lot 変更**: なし

## バグ (P1, eligible vs effective の再発事例)

v9.0 SHIELD「Aggregate Kelly Gate」(demo_trader.py `_tick_entry` 内) は
`_get_aggregate_kelly() < 0` で非 sentinel の OANDA 転送をブロックする設計。
しかし `_get_aggregate_kelly` は `stats_utils.kelly_criterion()["full_kelly"]` を
返しており、そこで **`max(0, full_kelly)` にクリップ済み** → 戻り値は負になり得ず、
**gate は導入以来一度も発火できなかった** (構造的死にゲート)。

- 発見: [[zero-fire-diagnosis-carrydip-vix-2026-07-02]] §2.4 (commit ba2f6b68 — 旧記載 5b205ce7 は rebase 前の同一内容 commit)
- 2026-07-02 時点の本番 aggregate edge=**-0.3617**, WR=48.2% (`/api/risk/dashboard`)
  — 設計意図どおりなら発火すべき状態で素通しだった
- 既存 edge-cell SHIELD bypass テスト群は `_get_aggregate_kelly → -0.25` をモック
  しており、「負を返せる」設計期待がテストに先行して存在していた
- 教訓 [[lesson-asymmetric-agility-2026-04-25]] / eligible vs effective:
  gate の判定は「クリップ後のロットサイジング用値 (effective sizing)」ではなく
  「エッジの生の符号 (raw)」で行うべきだった

## Fix (a): raw Kelly (rule:R3)

- `stats_utils.kelly_criterion` の戻り dict に **`full_kelly_raw`** (非クリップ) を追加。
  degenerate path (wr<=0 / avg_loss=0) にも 0.0 で追加。
- `full_kelly` / `half_kelly` は従来どおり max(0,·) クリップ維持 —
  既存 10+ 消費者 (lot sizing / BT tools / learning engine) は非破壊。
- `_get_aggregate_kelly` は `full_kelly_raw` を返す (負値可)。
- もう一つの呼び出し元 `_get_agg_kelly_lot_boost` は `kelly <= 0 → 1.0` 判定のため
  raw 化しても挙動不変 (負値でも no boost)。

## Fix (b): 1000u 固定契約 min-lot bypass (rule:R2, user 決裁)

gate は sentinel (1000u validation lot) を既に免除している。同一リスク水準の
「1000u 固定契約 (pre-reg LOCK)」戦略は `_is_pair_boosted=True` により
`_is_sentinel=False` となるため、単純修正すると aggregate edge<0 の間
**pilot が silent death** する (診断 §2.4 interplay 警告)。

**bypass 設計 — allowlist (eligible) AND 実効 units (effective) の二重ガード**:

```
_AGG_KELLY_GATE_MINLOT_BYPASS_TYPES = {
    vix_carry_unwind,               # Overlap pilot 1000u 固定 (2026-06-15 決裁)
    usdjpy_carry_dip_accumulator,   # MIN lot 1000u 契約 (2026-06-12)
    sweep_reversion_eurgbp_late,    # MIN lot 1000u 契約 (2026-06-12)
}
bypass = entry_type ∈ TYPES AND not XAU AND 0 < |units| <= 1000
```

- **hull_donchian_fade は意図的に対象外** — 5000u 契約 (5x リスク) のため gate 対象のまま
- 将来 lot が 5000u 等へ昇格したら bypass は**自動失効** (effective guard) —
  allowlist 更新忘れで大 lot が素通りする構造を遮断
- carry_dip / sweep_reversion は現在 Live N<10 の sentinel 保護下だが、N≥10 到達で
  `_is_sentinel=False` になった瞬間に vix と同じ罠を踏むため予防的に含める
  (FLAT bypass の既存コメントが同パターンを警告済み)
- bypass 発火時は `[SHIELD] Aggregate Kelly gate BYPASS (min-lot pre-reg contract ...)`
  を log — 観測可能性確保 (診断 P-V4 と同趣旨)

## 本番への即時影響 (デプロイ日から)

- aggregate raw Kelly < 0 (現在 edge=-0.3617) のため **gate が初めて実発火**する:
  promoted 非 sentinel / 非 edge-cell / 非 1000u契約 の OANDA 転送は
  aggregate raw Kelly が 0 以上へ回復するまでブロック
  (trendline_sweep ELITE_LIVE, hull_donchian_fade 5000u 等が対象)
- これは v9.0 SHIELD の**設計意図どおりの挙動** — DD=80.03% defensive mode とも整合
- sentinel 1000u 転送 / edge-cell force-live / 1000u契約 3 戦略は継続 → データ蓄積は維持
- 解除は自動: クリーンデータで aggregate raw Kelly >= 0 になれば gate は開く (60s cache)
- audit: block 時 `block_reason=agg_kelly=<raw>.3f<0` — 発火状況は `/api/oanda/audit` で追跡可能

## BT 検証について (hook 警告への回答)

本件は戦略パラメータ/エッジの変更ではなく **Rule 3 構造バグ修正** (BT スキップ、
数学/コード導出の文書化で代替 — 本ページと診断 §2.4)。bypass 側 (Rule 2) は
既存 pre-reg 契約の 1000u 検証 lot の維持であり「Sentinel lot での最小リスク化は例外」
条件に該当。tier/lot/パラメータの変更はゼロ。

## テスト (TDD RED→GREEN)

`tests/test_agg_kelly_gate_raw_and_minlot_bypass.py` — 10 cases:

- `kelly_criterion` raw field (負エッジで負値 / 正エッジで clipped と一致 / degenerate)
- `_get_aggregate_kelly` 負けブックで負値 (RED 時: クリップで 0 を返しバグ再現)
- bypass 述語 (契約 3 戦略 @1000u 許可 / units>1000 で失効 / hull・非契約・XAU 拒否)
- E2E: 実 DB 負けブック → promoted fill が shadow 化 + `[SHIELD]` log
  (RED 時: **live 素通し** = P1 バグの E2E 再現)
- E2E: vix Overlap pilot 1000u が gate 発火中も live 維持 + BYPASS log
  (RED 時: shadow 化 = silent death の再現)

## 関連

- [[zero-fire-diagnosis-carrydip-vix-2026-07-02]] §2.4 / §2.5 P-V2 (発見元)
- [[vix-overlap-pilot-prereg-2026-05-13]] / [[vix-carry-grail-removal-overlap-1000u-2026-06-15]]
- [[hull-donchian-fade-live-2026-06-12]] (5000u 契約 — bypass 対象外の根拠)
- [[lesson-asymmetric-agility-2026-04-25]] / eligible vs effective 教訓
- [[vix-carry-unwind]] (strategy card)
