# Decision 5 パッチ: ScalperEngine / HourlyEngine の post-return SL mutation 廃止

> 作成日: 2026-04-30
> 対象: Sub 4 #1 (Sev1) — engine 後段の SL floor 上書きで戦略の RR が壊れる
> ステータス: **提案のみ**。適用は user 承認後

## 問題

### 場所
- `strategies/scalp/__init__.py:91-105` (ATR×1.0 floor)
- `strategies/hourly/__init__.py:39-53` (ATR×1.5 floor)

### 現象
各戦略の `evaluate()` が完成済みの `Candidate` (entry/sl/tp/rr) を返した直後に、
engine が `result.sl` を ATR×1.0 (or 1.5) で上書きする。
**`tp` と `rr` は再計算されない** ため:
- 戦略が設計した RR=2.0 が、SL 拡大後は実質 RR=1.5 などに
- BT は engine を経由しないため、live と BT で異なる SL/RR で動く
- 統計母集団が汚染、Bonferroni 補正の意味がなくなる

### 既知の影響
- `mtf_regime_trend_cascade_scalp` の 5pip floor + RR floor が live で保存されない
- `ema_trend_scalp` 等の SL=ATR×1.0 ベース戦略は影響を受けないが、
  ATR×0.5 系戦略 (squeeze, micro_scalp) は SL が常に拡大される
- BT-Live 乖離の体系的原因の一つ

## 修正方針 (2 パターン)

### Pattern A (recommended): 戦略契約に floor を委譲
engine は SL を一切いじらない。各戦略が自分で `_min_sl_dist` を尊重して `evaluate()` を返す。

#### 変更箇所 1: strategies/base.py
```diff
+# 共通ヘルパー: SL floor を含む Candidate 構築
+def make_candidate_with_floor(name, signal, entry, sl, tp, score, confidence, ctx,
+                               min_sl_atr_mult=1.0, **kwargs):
+    """SL floor を尊重して Candidate を作る。RR を再計算する。"""
+    if ctx.atr > 0:
+        min_sl_dist = ctx.atr * min_sl_atr_mult
+        if signal == "BUY" and (entry - sl) < min_sl_dist:
+            sl = entry - min_sl_dist
+        elif signal == "SELL" and (sl - entry) < min_sl_dist:
+            sl = entry + min_sl_dist
+    # RR を再計算
+    sl_dist = abs(entry - sl)
+    tp_dist = abs(tp - entry)
+    rr = tp_dist / sl_dist if sl_dist > 0 else 0
+    return Candidate(
+        name=name, signal=signal, entry=entry, sl=sl, tp=tp,
+        score=score, confidence=confidence, rr=rr, **kwargs
+    )
```

#### 変更箇所 2: strategies/scalp/__init__.py
```diff
 def evaluate_all(self, ctx: SignalContext) -> list[Candidate]:
     if ctx.atr <= 0:
         logger.debug("[ScalperEngine] ATR<=0 → skip all strategies")
         return []
     candidates = []
     _rejected = []
-    # SL最低距離フロア: ATR(14)×1.0（ノイズレベル以下のSL防止）
-    _min_sl_dist = ctx.atr * 1.0
+    # SL floor は各戦略の責任 (2026-04-30 P0 fix Sub 4 #1: RR 再計算)
     for strategy in self.strategies:
         if not strategy.enabled:
             continue
         try:
             result = strategy.evaluate(ctx)
             if result is not None:
-                # SLフロア適用
-                if _min_sl_dist > 0:
-                    if result.signal == "BUY" and (ctx.entry - result.sl) < _min_sl_dist:
-                        result.sl = ctx.entry - _min_sl_dist
-                    elif result.signal == "SELL" and (result.sl - ctx.entry) < _min_sl_dist:
-                        result.sl = ctx.entry + _min_sl_dist
                 candidates.append(result)
                 logger.debug(f"[{strategy.name}] ✅ {result.signal} score={result.score:.2f} conf={result.confidence}")
             else:
                 _rejected.append(strategy.name)
```

#### 変更箇所 3: 各戦略 (38 ファイル) を 1 戦略ずつ移行
- `make_candidate_with_floor()` 経由で Candidate を返すよう書き換え
- 一気にやらず、まず scalp/ema_trend_scalp.py / scalp/bb_rsi.py / scalp/squeeze.py の 3 戦略を pilot
- 残り 35 戦略は段階的に移行

#### リスク
- 38 戦略書き換えは大規模変更、deploy 時の regressions 懸念
- 段階移行中は engine 側 floor を完全削除できない (一部戦略は floor 未対応)

### Pattern B (短期): engine 側で RR を再計算する
SL を上書きしたら **同時に TP も比例調整して RR を保つ**。

#### 変更箇所 (scalp/__init__.py)
```diff
 def evaluate_all(self, ctx: SignalContext) -> list[Candidate]:
     ...
     for strategy in self.strategies:
         ...
         try:
             result = strategy.evaluate(ctx)
             if result is not None:
-                # SLフロア適用
-                if _min_sl_dist > 0:
-                    if result.signal == "BUY" and (ctx.entry - result.sl) < _min_sl_dist:
-                        result.sl = ctx.entry - _min_sl_dist
-                    elif result.signal == "SELL" and (result.sl - ctx.entry) < _min_sl_dist:
-                        result.sl = ctx.entry + _min_sl_dist
+                # SL floor を尊重しつつ RR を保つ (2026-04-30 P0 fix Sub 4 #1)
+                if _min_sl_dist > 0:
+                    orig_sl_dist = abs(ctx.entry - result.sl)
+                    if result.signal == "BUY" and (ctx.entry - result.sl) < _min_sl_dist:
+                        # SL を拡大、TP も比例拡大
+                        new_sl = ctx.entry - _min_sl_dist
+                        rr = result.rr if result.rr > 0 else (abs(result.tp - ctx.entry) / orig_sl_dist if orig_sl_dist > 0 else 1.5)
+                        result.sl = new_sl
+                        result.tp = ctx.entry + rr * _min_sl_dist
+                    elif result.signal == "SELL" and (result.sl - ctx.entry) < _min_sl_dist:
+                        new_sl = ctx.entry + _min_sl_dist
+                        rr = result.rr if result.rr > 0 else (abs(result.tp - ctx.entry) / orig_sl_dist if orig_sl_dist > 0 else 1.5)
+                        result.sl = new_sl
+                        result.tp = ctx.entry - rr * _min_sl_dist
+                    # rejected if rr<0 (戦略の signal と TP/SL が矛盾)
+                    if (result.signal == "BUY" and result.tp <= ctx.entry) or \
+                       (result.signal == "SELL" and result.tp >= ctx.entry):
+                        _rejected.append(f"{strategy.name}(rr_invariant_violated)")
+                        continue
                 candidates.append(result)
```

同じ変更を `strategies/hourly/__init__.py` にも適用 (ATR×1.5)。

#### リスク
- 既存 BT との結果差分が出る (BT 側は engine を経由しないため、もともと差分あり)
- TP の拡大で勝率が下がる可能性 (TP 到達条件が遠くなる)
- ただし RR 不変は **戦略の数学的整合性回復** であり、優先される

#### 検証
1. shadow mode で 7 日走らせ、entry/sl/tp/rr の整合性ログ確認
2. BT を engine 経由で再実行 (engine 側で動く BT runner を新設)
3. live と BT で SL/TP が一致することを確認

## 推奨

**Pattern B を先に短期適用**、その後 Pattern A への段階移行を計画する。
- Pattern B は 30 行で完結、影響範囲が engine 2 ファイルのみ
- Pattern A は 38 戦略書き換えで規模大、別 epic として管理

## 関連 lesson 候補

このバグは「engine による silent mutation」というアンチパターン。
新規 lesson として記録すべき:
- `lesson-engine-silent-mutation-2026-04-30.md`
- 教訓: 「戦略の数学的契約 (entry/sl/tp/rr) を後段で書き換えるな。書き換えるなら必ず再計算」

CI/lint チェック化 (Sub 8 governance Top 3 #1):
```python
# pytest fixture: 各戦略の Candidate.rr が evaluate_all 後も保たれることを assert
def test_engine_preserves_rr():
    for strat in scalp_engine.strategies:
        ctx = make_dummy_context()
        result = strat.evaluate(ctx)
        if result is None:
            continue
        original_rr = result.rr
        candidates = scalp_engine.evaluate_all(ctx)
        for c in candidates:
            if c.entry_type == strat.name:
                assert abs(c.rr - original_rr) < 0.01, f"{strat.name}: RR changed {original_rr} → {c.rr}"
```
