# DD 台帳の broker 決済パス欠落 — 構造バグの特定と修復 (2026-08-06)

**性格**: Rule 3 (構造バグ / 算数破綻)。365日BT スキップ、code derivation + 本番実測の恒等式で証明。
**live パラメータ変更**: なし (DD tier 不変 — §5 参照)。
**起点**: `wiki/index.md` の 2026-08-05 注記「本日 +29.0p の win を DD ledger が登録していない = `attribution` は更新済なのに `dd_status`/`jpy_ledger` が 08-04 と byte-identical、要確認」

---

## 1. 結論

**`_sync_oanda_closures()` (broker 側 SL/TP 約定の同期クローズ経路) が Equity 台帳を一切更新していなかった。**

台帳更新 (`_eq_current` / `_eq_current_jpy` / `_eq_peak*` / `dd_lot_mult`) は内部決済パスに**インラインで**書かれており、sync 経路からは構造的に到達不能だった。よって `close_reason='OANDA_SL_TP'` の決済は DD 台帳に一度も計上されていない。

DD 台帳は defensive lot multiplier の **SSOT** (Track C D-b、2026-07-28) であるため、これは表示バグではなく**サイジングの入力が実 book と乖離していた**問題である。

---

## 2. 恒等式による証明 (本番実測、2026-08-06)

台帳 anchor (`eq_jpy_ledger_v1`、D-a 実測で再基準化) 以降の eligible 決済は 4 件:

| exit_time | instrument | entry_type | pnl | close_reason | 経路 |
|---|---|---|---|---|---|
| 2026-07-29T16:44 | AUD_JPY | price_shock_rev_aud_jpy_h1_long | +0.6p | horizon | 内部 |
| 2026-07-30T13:49 | USD_JPY | vix_carry_unwind | −30.1p | SL_HIT | 内部 |
| 2026-07-31T20:57 | AUD_JPY | price_shock_rev_aud_jpy_h1_long | −123.2p | horizon | 内部 |
| 2026-08-05T06:33 | USD_JPY | usdjpy_carry_dip_accumulator | **+29.0p** | **OANDA_SL_TP** | **broker** |

- 内部経路 3 件の合計 = **−152.7p** → USD_JPY/AUD_JPY 1000 units = ¥10/pip で **−1,527.00 JPY**
- KV 実測 delta = `eq_current_jpy` 324,945.58 − anchor 326,472.58 = **−1,527.00 JPY**

**完全一致。** broker 経路の +29.0p (¥290) の寄与は**ちょうどゼロ** — 当該経路が一度も計上していないことの算術的証拠 (誤差でも丸めでもない)。

---

## 3. 欠落母集団の規模と符号 (これが重要)

母集団 = `oanda_trade_id != ''` ∧ `is_shadow=0` ∧ 非 XAU ∧ CLOSED (本番 `/api/demo/trades`)。

| 母集団 | n | sum | mean | 備考 |
|---|---|---|---|---|
| 台帳**計上済** (内部経路) | 37 | **−319.3p** | −8.63 | 台帳が見ている世界 |
| 台帳**欠落** (`OANDA_SL_TP`) | **21** | **+28.0p** | **+1.33** | **WR 85.7%** |
| 実 book 合計 | 58 | −291.3p | −5.02 | 真値 |

**欠落は全決済の 36.2% を占め、かつ正 EV 側に偏っている。**

### メカニズム (なぜランダムでないか)
欠落は無作為標本ではない。**broker の TP 約定は sync 経由でしか観測されない**のに対し、**損失は demo 側の SL 判定 (`_check_sltp_realtime`) が先に発火して内部経路でクローズされる**。つまり「勝ち side が sync に、負け side が内部に」系統的に振り分けられる。この非対称は構造的・持続的であり、小標本の揺らぎではない。

**帰結**: 台帳は実 book より**構造的に悪い DD** を報告し、防御 multiplier を過剰に絞っていた。原則 4「攻撃は最大の防御」に反する方向のバイアス。

---

## 4. 修復

1. **台帳更新を `_apply_equity_ledger_close(trade, pnl)` に集約** — 内部決済パスと `_sync_oanda_closures()` の**両方**が同一 helper を通る。台帳への直接加算箇所は helper 内 1 箇所のみ (+ backfill 1 箇所) に制限し、回帰テストで本数を pin。
2. **一度きりの backfill** `_backfill_broker_close_ledger_gap()` — 定数ではなく **DB から再導出**する。欠落母集団は「eligible ∧ `close_reason='OANDA_SL_TP'` ∧ `exit_time >= 2026-07-28`」で決定論的に確定できる (当該経路は一度も計上していないため「計上済みか」の状態を持つ必要がない)。KV フラグ `eq_ledger_broker_close_backfill_v1` で冪等化。
   - anchor **以前**の欠落は D-a 実測 (broker `oanda_trades.realized_pl` 由来) に既に吸収済みのため対象外。
3. 回帰テスト `tests/test_dd_ledger_broker_close.py` (12 件)。うち中核 2 件は修正前コードに対して実際に FAIL することを確認済み。

---

## 5. live への影響 — なぜ R3 で執行可能か

backfill 適用による DD 変化:

| | dd_jpy | dd_pct | tier | lot_mult |
|---|---|---|---|---|
| 補正前 | 34,342.89 | 9.56% | ≥8% | **0.20x** |
| 補正後 | 34,052.89 | 9.48% | ≥8% | **0.20x** |

`DD_LOT_TIERS` の 8% 境界を跨がないため **live lot は不変**。本変更は純粋な会計是正であり、防御水準の緩和ではない (R1 が要る lot↑ ではない)。回帰テストで tier 中立性も pin。

**ただし将来効果は非対称に効く**: 今後 broker TP 約定 (正 EV 側) が正しく計上されることで、DD 回復経路が実 book どおりに進む。従来は勝ちが台帳に載らず、8% → 0.40x 復帰が構造的に遠のいていた。

---

## 6. 目標への寄与

- **M1 (clean live 月次符号転換)** — 直接の PnL 改善ではないが、**サイジング入力の正しさ**を回復する。従来は実 book より悪い DD で lot を絞り続ける片道ラチェットが働いていた。
- **Kelly / lot 階段** — [[lot-ladder-template-2026-08]] の段階昇格は DD tier と資本計測に依存する。台帳が実 book を追わないままでは階段判定そのものが汚染される。
- **ボトルネック順位は不変** — 供給ライン (正 EV セルの不在) が依然として律速。本件はその手前の配管修復。

---

## 7. 教訓 (既存 lesson の再発)

> **同じ事実を表す複数列/複数経路は同じ helper を通す。「片方の経路だけ更新」は SSOT を静かに壊す。**

これは KB 既存教訓の 3 度目の再発である:
- 「同じ事実を表す複数列は同じ statement で更新する」(is_shadow / oanda_trade_id)
- Track C D-b 自身の「gate 側だけ直し dashboard 側に旧デフォルトが残った」片方欠落 ([[mc-ruin-dashboard-artifact-2026-08-05]])
- 本件: 決済経路が 2 本あるのに台帳更新が 1 本にしか無い

**構造的対策**: 「複数の入口を持つ状態更新」はインライン実装を禁止し、helper 1 箇所 + 呼び出し側 N 箇所の形に正規化する。本 PR では加算箇所の**本数**を AST/文字列カウントでテスト pin した (インライン再実装が入ると即 FAIL)。

**検知が遅れた理由**: 台帳の値は `attribution` (DB 由来、常に正しい) と別系統で、両者を突き合わせる監視が無かった。日次 KB 注記で「byte-identical」に気付いたのが初検知 = 人手依存。→ §8。

---

## 8. フォローアップ (本 PR 対象外)

- [ ] **台帳 vs DB の日次整合チェック** — `eq_current_jpy` の delta が「前回以降の eligible 決済の JPY 合計」と一致するかを日次で検算し、乖離を alert する。本件のような片方欠落を人手注記でなく機械で検知する。監視系 (`tools/prereg_trigger_watch.py` の隣) に置くのが自然。

---

## 参照
- 実装: `modules/demo_trader.py` (`_apply_equity_ledger_close` / `_backfill_broker_close_ledger_gap` / `_sync_oanda_closures`)
- テスト: `tests/test_dd_ledger_broker_close.py`
- 前提: [[track-c-capital-plumbing-decision-packet-2026-07-28]] (D-b: JPY 台帳 = SSOT)、[[mc-ruin-dashboard-artifact-2026-08-05]] (同型の片方欠落)
