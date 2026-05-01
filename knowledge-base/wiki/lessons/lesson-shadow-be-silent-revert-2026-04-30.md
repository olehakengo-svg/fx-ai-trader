# Lesson: Shadow trade BE/Trailing が silently revert していた構造バグ

**Date**: 2026-04-30
**Rule**: R3 (構造バグ — 数学/code derivation)
**Detected by**: `tools/mfe_sl_giveback_forensic.py` (新規監査スクリプト)
**Patch**: [modules/demo_trader.py:1758-1770](../../../modules/demo_trader.py)

## 観察された症状

直近30日の demo_trades.db (XAU除外) で:
- **Shadow SL_HIT 213件** のうち **22件 (10%)** が高MFE (mfe_r ≥ 0.8) を記録した後 SL 着地
- 22件 **すべて** が pnl_r ≤ -1.0R (G1 タグ = BE-Skip 着地)
- BE 発火閾値 (ATR×0.8) 到達後そのまま SL になるトレードが **100%** を占めた

確率的にこれが偶然な分布である可能性は極めて低く (Wilson 95% LB > 0)、
構造バグを示唆する強いシグナルだった。

## 根本原因

`modules/demo_trader.py:1758-1760` の旧コード:
```python
if sl != _original_sl:
    if not self._oanda.modify_sl_sync(trade_id, sl, instrument=_inst):
        sl = _original_sl  # OANDA失敗時はSLを元に戻す
```

`OandaBridge.modify_sl_sync` は `_trade_map` に登録のないトレード ID で
即 `False` を返す ([modules/oanda_bridge.py:558-560](../../../modules/oanda_bridge.py)):
```python
oanda_id = self._trade_map.get(demo_trade_id)
if not oanda_id:
    return False
```

Shadow トレードは OANDA に発注されないので `_trade_map` に存在せず、
**毎 tick で `modify_sl_sync` が False → `sl = _original_sl` が実行** されていた。

さらに `sl = trade["sl"]` ([modules/demo_trader.py:1639](../../../modules/demo_trader.py))
が毎 tick DB から読み直すため、ローカルの BE 更新は次 tick で消える。
よって Shadow トレードの BE/Tier2 trail は **完全に無効化** されていた。

## なぜ Live トレードでは見えなかったか

Live トレードは OANDA broker が SL を保持するため、ローカルの sl 変数の有無に
関わらず broker 側 SL がトリガーされる。よってローカル `_original_sl` への
revert は実害なし。Live SL_HIT N=11 のうち高MFE→SL は1件のみで、シグナルが
弱く検出が難しかった。

## 修正

**[shadow gate + DB 永続化](../../../modules/demo_trader.py)** を追加 (rule:R3):

```python
if sl != _original_sl:
    _is_shadow_t = bool(trade.get("is_shadow", 0))
    if _is_shadow_t:
        try:
            self._db.update_sl_tp(trade_id, sl, tp)
        except Exception:
            sl = _original_sl
    elif not self._oanda.modify_sl_sync(trade_id, sl, instrument=_inst):
        sl = _original_sl  # Live: OANDA 同期失敗時のみ revert
```

**Shadow**: DB に直接永続化 → 次 tick で BE 状態が維持される。
**Live**: 従来通り OANDA mirror。OANDA 失敗時のみ revert。

## なぜ 365日 BT を passe したか (Rule 3 妥当性)

- 数学的・構造的バグ (silent revert ループ) であり、365日 BT で「観測される
  give-back 率」の値だけ見ても**根本原因の修正案にならない**。
- 修正は既存の Live 経路の挙動を変えない (shadow-only gate)。
- 修正後の効果は Rule 2 監視で N=10〜30 蓄積後に確認可能 — Bonferroni 補正後
  の高MFE→SL 率の有意減少を観測すれば妥当。

## 関連 forensic / KB

- 監査スクリプト: [tools/mfe_sl_giveback_forensic.py](../../../tools/mfe_sl_giveback_forensic.py)
- レポート: [raw/audits/mfe_sl_giveback_20260430T110849Z.md](../../../raw/audits/)
- 解析: [knowledge-base/wiki/analyses/mfe-sl-giveback-2026-04-30.md](../analyses/mfe-sl-giveback-2026-04-30.md)

## 次のアクション (本 Lesson のスコープ外)

1. **`_entry_atr` 永続化** (R3-b): プロセス再起動で in-memory ATR が失われる問題は別タスク。
2. **GBP_USD MAX_HOLD/TIME_DECAY での give back** (R2): TP×0.85→0.70 の cell-specific
   QH スカラー化を検討 (forensic レポートの「ペア × 退出理由」セクション参照)。
3. **Site 4-7 の modify_sl_sync 呼び出し** (Profit Extender 系): Shadow には
   そもそも適用されない feature paths のため Site 1 修正のみで十分だが、
   将来の Shadow expansion 時に同種バグが再発しないよう監視リスト入り。
