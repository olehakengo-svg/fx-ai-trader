---
title: per-bar dedup gate が TF 非対応で 15m / 5m バー再発火を素通しさせていた構造バグ
date: 2026-05-03
type: lesson
severity: HIGH
rule: R3
related: [[lesson-shadow-emit-dedup-2026-04-30]], [[lesson-shadow-always-emit-cleanup-2026-04-28]], [[lesson-bt-live-divergence]]
---

# Per-Bar Dedup Gate が TF 非対応だった (2026-05-03)

## 一行サマリ

`_maybe_reserve_signal_emit` の dedup window が **60s ハードコード** だったため、15m / 5m バー戦略は同一バー内の 2 件目以降を素通しさせていた。28 戦略×ペア combo / 318 件未フラグ violation / 推定 -1,000+ pip の累積 PnL ドラッグ（うち Live 約定は 4 件、残りは Shadow phantom emission による統計汚染）。

## 何が起きたか

[[lesson-shadow-emit-dedup-2026-04-30]] で「shadow_emit 経路が dedup をバイパスしていた」バグは修正済みだったが、**dedup gate そのものの window が 60s 固定**だった。

実害:

- 1m バー戦略 → 60s 窓で正しく機能
- 5m バー戦略 → 60s 〜 300s の間で同一バー再発火が発生
- 15m バー戦略 → 60s 〜 900s の間で同一バー再発火が発生 (**14 分間 gate 無効**)

## どう発見したか

2026-05-03 の per-bar dedup audit (`tools/per_bar_dedup_audit.py`) を本番 API (`/api/demo/trades?limit=2000`) に対し走らせ、TF 認識した bar window で違反検出した結果:

| combo | TF | 違反数 | うち未フラグ | PnL |
|---|---|---|---|---|
| rsk_gbpjpy_reversion/GBP_JPY | 15m | 81 | 42 | -539p |
| **sr_anti_hunt_bounce/USD_JPY** | 15m | 21 | 21 | **-357p** |
| **sr_fib_confluence/EUR_JPY** | 15m | 11 | 11 | **-173p** |
| **sr_fib_confluence/USD_JPY** | 15m | 8 | 8 | **-117p** |
| **ema_trend_scalp/USD_JPY** | 5m | 23 | 23 | **-61p** |
| **htf_false_breakout/EUR_JPY** | 15m | 3 | 3 | **-62p** |
| ... 他 22 combo | | 281 | 210 | (略) |
| **合計** | | **428** | **318** | **約 -1,000p** |

OANDA fill された違反は 4 件のみ → **直接 PnL 損失は限定的だが、Shadow phantom emission による統計汚染が深刻**。Live N/WR/EV を膨らませて promote 判定を誤らせる。

## 根本原因

[modules/demo_trader.py:3349](../../../modules/demo_trader.py#L3349) (旧 3331) の primary 経路、および [modules/demo_trader.py:2791](../../../modules/demo_trader.py#L2791) の shadow_emit 経路、両方とも `_maybe_reserve_signal_emit(...)` を **window_sec デフォルト 60** で呼んでいた。

戦略の `tf` フィールドは signal 辞書に存在し、`_tick_entry` の引数にも渡っていたが、dedup gate にその情報が伝播していなかった。

## 修正

`rule:R3 (構造バグ即修正)` を適用:

1. [demo_trader.py:2834](../../../modules/demo_trader.py#L2834) — `_tf_to_window_sec(tf)` static helper を追加 (1m/5m/15m/30m/1h/4h を秒に変換、未知/None は 60s フォールバック)
2. [demo_trader.py:2791](../../../modules/demo_trader.py#L2791) — shadow_emit 呼び出しを `window_sec=_tf_to_window_sec(tf)` 経由に
3. [demo_trader.py:3349](../../../modules/demo_trader.py#L3349) — primary 呼び出しを同様に修正、ブロックメッセージに dynamic window 値を埋め込み

検証: `tests/test_shadow_stats.py` / `tests/test_oanda_audit_join_invariant.py` 計 12 テスト pass。

## 適用ルール

- **Rule 3 (Immediate)** — 365日 BT スキップ可。code derivation を本ファイルに記録、Rule 2 監視に格下げ
- **同コミットに本 lesson ページを含む** (CLAUDE.md WRITE rule)

## 検証方法（fix 後）

```bash
# Production API 経由
python3 tools/per_bar_dedup_audit.py --prod --limit 2000

# 期待: deploy 後の新規 trade では unflagged_violations = 0
# 既存 violation は履歴データなので残るが、新規発生はゼロになる
```

## 関連

- [[lesson-shadow-emit-dedup-2026-04-30]] — 本バグの「shadow 経路バイパス」修正版。window 値そのものが間違っていた点は当時見落とし
- [[lesson-asymmetric-agility-2026-04-25]] — Rule 1/2/3 の使い分け
- [[lesson-bt-live-divergence]] — Live PnL / N が信頼できない構造的要因の一つ
