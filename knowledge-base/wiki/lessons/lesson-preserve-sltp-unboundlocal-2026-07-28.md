# Lesson: _1H_PRESERVE_SLTP 型の UnboundLocalError — 3.5ヶ月の chronic silent live-kill (2026-07-28, rule:R3)

## Symptom
- **2026-04-10 〜 2026-07-28 の 3.5ヶ月間**、`_1H_PRESERVE_SLTP` に属する全 entry_type の live 送信が死んでいた:
  - `weekend_gap_fade` / `hull_donchian_fade` / `sweep_reversion_eurgbp_late` / `keltner_squeeze_breakout` / `donchian_momentum_breakout` / `price_shock_rev_*` (Tier-1 5種)
- 初回イベント 2026-07-26 の weekend_gap_fade USD_JPY (−22.8p shadow) が **latch 済み・row 挿入済みなのに OANDA 未送信** — forensic でバグ確定
- Live 発火ゼロなのにエラーが表面化しない ⇒ **flat book の一因**（正 EV セルが構造的に発火不能）

## Root Cause
`modules/demo_trader.py` `_tick_entry` 内:

```python
if entry_type not in _1H_PRESERVE_SLTP:   # ← SR/ATR 再計算ブロック
    ...
    _is_xau_inst = "XAU" in instrument.upper() if instrument else False  # ← ここで代入
...
if _is_sentinel:
    _adjusted_units = 1 if _is_xau_inst else 1000   # ← 無条件参照 (旧 L6558)
if _is_xau_inst:                                    # ← 無条件参照 (旧 L6561)
```

- preserve 型（戦略 SL/TP 完全保存契約）は `if entry_type not in _1H_PRESERVE_SLTP:` ブロックを**設計通りスキップ**する
- しかし `_is_xau_inst` の代入がそのブロック内にあったため、preserve 型は**未代入のまま**下流の無条件参照（Sentinel 単位数 / 1000u 丸め / FLAT bypass 判定）に到達 → `UnboundLocalError`
- クラッシュ位置は **DB row 挿入 (`open_trade`) と weekend latch 永続化の後・OANDA bridge 送信の前** — 例外は `_tick_entry` 呼び出し元でキャッチされ、tick は次周期へ

## なぜ 3.5ヶ月見えなかったか（教訓の核心）
1. **row 挿入後のクラッシュは「無タグ shadow」を作る** — row は存在する (is_shadow 値も一見正常) が bridge 送信だけが欠落。集計上は「shadow が蓄積している」ように見え、live-kill が指標に出ない
2. **純関数テストだけでは送信経路を保証できない** — 各戦略のシグナル関数 / build_sig / detect の unit test は全部 green だった。バグは共有経路 `_tick_entry` のスコープにあり、**新 entry_type は `_tick_entry` を送信判定直前まで通す統合テストが必須**
3. **error handler がメッセージのみ** — `[WEEKEND_GAP] tick error` は `{err}` だけで traceback なし。UnboundLocalError の行番号が一度もログに出なかった（本修正で traceback 出力追加）
4. **preserve 集合は追加され続けた** — 2026-04-10 (KSB/DMB) 時点で潜伏したバグに、その後 5 戦略以上が「契約保存」目的で合流し、被害が静かに拡大した

## Fix (rule:R3 構造バグ — スコープ修正のみ、ロジック変更なし)
1. `_is_xau_inst = "XAU" in instrument.upper() if instrument else False` を `_is_jpy_or_xau` 等の**無条件初期化群へ移動**（同一式・同一値、全経路で参照より前に実行）
2. **regression pin**: `tests/test_preserve_types_tick_entry.py`
   - `_1H_PRESERVE_SLTP` を `_tick_entry` ソースから ast 抽出して全 entry_type をパラメタライズ（新 preserve 型は自動でテスト対象化、config 未追加なら KeyError で落ちる設計）
   - 合成 sig で実 `_tick_entry` を通し、row 挿入（= 旧クラッシュ地点より上流、間に early return なし）+ 正常 return を assert
   - 修正前に UnboundLocalError 再現を確認 → 修正で green (TDD)
3. 観測性 (P1): `_weekend_gap_tick` no-qualify 時の週末ごと 1 行 gap ログ (07-26 EUR_USD +19.9p near-miss が無音だった欠陥) + wg tick error handler に `traceback.format_exc()`

## Why rule:R3
- 算数/構造バグ: 同一式のスコープ位置のみが誤り。戦略ロジック・凍結契約 (pre-reg SL/TP/lot) は一切不変
- BT 不要 — 変更は「クラッシュ経路の除去」であり EV/WR に触れない。preserve 型の凍結統計 (weekend_gap_fade OOS PASS 等) はそのまま有効


## デプロイ影響 (再武装範囲の申告 — 2026-07-28 main セッション裁定)

本修正のデプロイで live 送信が自動復活しうるのは以下だった:
| 対象 | tier | 措置 |
|---|---|---|
| weekend_gap_fade ×3 (EUR_USD/USD_JPY/AUD_USD) | _PAIR_PROMOTED (user 承認 2026-07-25 option b) | **live 復活 = 意図どおり** |
| price_shock_rev ×5 (EUR_GBP/EUR_AUD/USD_CAD/NZD_JPY/AUD_JPY) | _PAIR_PROMOTED (2026-05-18 R1) | **`_PRESERVE_REARM_LIVE_PIN` で shadow 固定** — 昇格以来 live fill N=0 (本バグで送信死)、再武装は user 決裁待ち |
| donchian_momentum_breakout ×NZD_JPY/NZD_USD | _PAIR_PROMOTED (2026-05-27 R1-EXCEPTION) | 同上 pin |
| hull_donchian_fade / sweep_reversion_eurgbp_late | live enable **false (code pin)** | 不変 (本修正で再武装しない、/api/demo/live-enable-flags で実測確認済み) |
| keltner_squeeze_breakout ほか | Phase0 shadow tier | 不変 |

pin の解除は user 決裁 + frozenset 削除 PR のみ (KV 不可)。price_shock の判断材料 = 昇格根拠 (12.3y BH-FDR m=3744, Wilson_lo≥0.58) + 2026-07-24 exit-free 監査 (全席 p=0.0001 / headroom 6.5-35x、ただし EUR_AUD/USD_CAD/AUD_JPY は pre-2021 OOS が 0 と分離不能 + grid ev_pip artifact 過大)。

## 再発防止ルール
- **新 entry_type（特に `_1H_PRESERVE_SLTP` 追加時）は `tests/test_preserve_types_tick_entry.py` の `TYPE_CONFIG` に送信経路 config を追加すること**（membership pin `test_preserve_set_matches_frozen_membership` が drift を強制検知）
- 共有経路の条件ブロック内で変数を代入し、ブロック外で参照する構造は禁止（初期化は無条件スコープで）
- silent except / メッセージのみの error handler は禁止 — traceback を必ず出す

## 関連
- forensic: 2026-07-28 セッション (weekend_gap_fade 初回イベント 07-26 調査)
- 戦略カード: [[weekend-gap-fade]] (07-26 イベント記録)
- 類似教訓: [[lesson-tool-verification-gap]], `project_watchdog_decrement_rearm_bug` (KV disable は pin にならない、不可逆化は code で)
