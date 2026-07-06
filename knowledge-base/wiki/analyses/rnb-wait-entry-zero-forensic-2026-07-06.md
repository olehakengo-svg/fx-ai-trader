# Forensic: rnb_usdjpy WAIT entry=0 による _price_history 恒常汚染 (rule:R3)

**日付**: 2026-07-06 / **分類**: 構造バグ (Rule 3 — 365日BT不要、code derivation で確定)
**関連**: [[zero-fire-diagnosis-carrydip-vix-2026-07-02]] §2.6 / PR #38 (PRICE_HISTORY_GUARD)

## TL;DR

`[PRICE_HISTORY_GUARD] drop contaminated tick: USD_JPY price=0 mode=rnb_usdjpy` の連発 (~2,880件/日) は
**外部データソース障害ではない**。`compute_rnb_signal` の WAIT dict が `entry: 0` を返す設計 (2026-04-05
db5e3e4c 実装初日から) が唯一の発生源。

## 証拠チェーン (origin/main 基準)

1. app.py:4298-4302 — `_WAIT = {"signal": "WAIT", "entry": 0, ...}`。全 WAIT 経路 (~10箇所) で実 Close による上書きなしに return
2. modules/demo_trader.py:3491 — `_tick` は WAIT でも `_tick_entry` を呼ぶ
3. modules/demo_trader.py:3754 — `current_price = sig.get("entry", 0)` → RNB WAIT では 0
4. modules/demo_trader.py:3761-3776 — bid/ask 取得と realtime フォールバックは `if signal in ("BUY","SELL")` 内。**WAIT は救済経路なし**
5. RNB は BUY-only 5条件 AND + UTC 7-20 フィルタ → 実運用ほぼ常時 WAIT → 毎 tick 発火
6. 周期 10-30 秒 = `interval_sec: 30` × MainLoop/RequestTick の 2 系統位相ずれ

## なぜ rnb_usdjpy だけか

daytrade / scalp / hourly の各 signal 関数は WAIT でも実 Close を entry に入れて返す。
**WAIT で entry=0 のまま返すのは compute_rnb_signal のみ** (compute_1h_zone_signal の entry=0 は dispatch されない)。

## 影響範囲 (KB 訂正事項)

- `_price_history` は instrument キーで全モード共有 (spike gate demo_trader.py:4959 / velocity gate 4991)
- **2026-04-05〜07-04 (ガード導入前) の間、USD_JPY の spike/velocity gate は 30秒周期の (t, 0) 汚染下で動作**
- [[zero-fire-diagnosis-carrydip-vix-2026-07-02]] §2.6 の「fetch 全滅時の 0/None」は副次源。**支配的な 0 の発生源は RNB WAIT tick**
  (07-02 vix Overlap 14/14 shadow 事故と整合: 60秒窓に 30秒周期の 0 がほぼ常在 → range=価格そのもの)

## 修正 (本 PR)

- app.py `compute_rnb_signal`: len ガード直後に `_WAIT["entry"] = float(df.iloc[-1]["Close"])` 1行 —
  以降の全 WAIT 経路が実価格を持つ。len 不足の早期 return のみ entry=0 残置 (_tick が len<50 で先に return、かつガードが防御)
- 回帰: tests/test_rnb_wait_entry_price.py (3 cases)
- 期待効果: PRICE_HISTORY_GUARD 発火 ~2,880件/日 → ほぼ 0。**残発火 = 真の fetch 障害シグナル**として観測性が回復

## 同梱: QUALBAR logger.info 不可視バグ (T7 E2E 検証不能の根本原因)

- strategies/hourly/usdjpy_carry_dip_accumulator.py の QUALBAR log が `logger.info` 使用
- 本番 (gunicorn) は logging handler 未設定 → INFO は破棄 (app.py:2628-2632 の 07-02 コメントが同じ落とし穴を明記済み)
- **T7 の「7d 0-fire → filter 診断」pre-reg は logger.info のままでは恒久的に実行不可能だった** → print(flush=True) 化
- 教訓候補: 本番可観測性の SSOT は print()。logging モジュール経由テレメトリは全て本番不可視
