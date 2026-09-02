---
title: in-memory dedup ゲートはプロセス境界を越えず、boot 時 backfill は write-time ギャップを残す
date: 2026-09-02
type: lesson
severity: MEDIUM
related: [[lesson-shadow-emit-dedup-2026-04-30]], [[lesson-per-bar-dedup-tf-aware-2026-05-03]], [[hourblock-recal-and-ema200-verdict-2026-09-02]]
---

# dedup 系バグ 5 例目 — 「プロセス境界」と「boot 時 backfill の write-time ギャップ」(2026-09-02)

## 何が起きたか

ema200_trend_reversal×USD_JPY の forensics ([[hourblock-recal-and-ema200-verdict-2026-09-02]] Study 2) で、90d shadow 72 行中に同方向 <120s の近接重複 22 ペア (最短 0.4s) を発見。`_maybe_reserve_signal_emit` の 60s(→TF-aware) dedup を明確に突破していた。

診断の決め手は `/api/admin/dedup_status` の **counter 矛盾**: 単一インスタンス (エンドポイント 12/12 同一応答で確認) が boot (04:27) 以降 shadow_emit 行を 2 件書いたのに `shadow_called=1`。gate は 1 回しか呼ばれていない = **2 件目は gate を通らずに書かれた**。call-site は 1 箇所 (`demo_trader.py:4538`) のみで `dedup_already_reserved=True` を渡す経路は存在しない → **その 2 件目を書いたプロセスは今は存在しない別プロセス**、と帰結する以外にない。

## 根本原因 (2 層)

1. **in-memory ゲートはプロセス境界を越えられない**: `_recent_signal_emits` / `_order_bar_signal_emits` はインスタンス属性 (プロセスローカル)。デプロイ重複 (zero-downtime で旧コンテナ drain 中に新コンテナが同一 Render Disk SQLite に書く)、コンテナ置換、一時的な第 2 インスタンスが並走すると、各プロセスが独立した dedup 辞書を持ち、同一キーを互いに知らずに INSERT する。[[lesson-shadow-emit-dedup-2026-04-30]] の「restart で in-memory state 消失」の**並走版**。

2. **boot 時 backfill が write-time ギャップを残す**: `_backfill_dedup_violation` はプロセス境界越えの重複を retroactive に `dedup_violation=1` へ flag するが、**起動時にしか走らない**。あるプロセスの boot backfill 後にそのプロセス自身の寿命内で生じた (あるいは並走プロセスが書いた) 重複は、**次の再起動まで flag されない**。

## 影響 (定量、他戦略含む)

90d shadow 全体で intra-window 重複 **1,434 行**。うち **1,431 (99.8%) は既に backfill が dv=1 済み**、未 flag は **3 行 (0.04%)** のみ。つまり:

- **集計 (aggregate) quant-eval への水増しは軽微** — backfill が retroactive にほぼ全て回収している。
- **危険なのは point-in-time 分析**: 重複作成〜次回起動の窓で走った分析は水増し N を見る。実例 = 2026-07-31 の ema200 quant-eval N=79 PASS (Bonferroni p=2.6e-6) は、その時点で未 flag だった重複込み。後の起動が flag して N は縮小した。**churn 抑制 (PR #199/#201) で起動が稀になったほど、未 flag 窓は長くなる**ため放置できない。

## 修正 (rule:R3、本 PR)

`demo_db.open_trade` に **write-time の DB 参照 dedup flag** を追加。shadow 行の INSERT 時、同一 (entry_type, instrument, direction) の **dedup_violation=0** な shadow 行が TF 窓内に既存なら、新行を `dedup_violation=1` で書く。

- **プロセス境界を越える**: in-memory でなく共有 DB (コミット済み行) を参照するため、どのプロセスが書いても効く。
- **write-time で即時**: 次回起動を待たず、point-in-time 分析が常に除外できる。
- **挙動不変・データ非破壊**: 行は必ず INSERT される (トレード挙動不変、live 送信 `oanda_trade_id != ''` は対象外)。flag のみ変える = quant-eval / R2 audit が既に除外している列。
- backfill の「非重複行のみ last_seen を進める」意味論と一致 (dv=0 anchor)。boot backfill は歴史分の回収として存続 (相補的)。

**considered-but-rejected**: INSERT を skip して重複を完全防止する案 → データ損失 + 挙動変更のリスク。害は「測定の N 水増し」のみ (live 送信に重複なし) なので、**既存の flag 方式 (backfill と同じ) を踏襲**して害だけ無効化する方が正しいスコープ。

同 PR で **audit units:0 の自己記述化** も実施 (`_open_shadow_emit_trade` の `_add_oanda_audit` block_reason を `shadow_tracking(shadow_emit_no_lot)` へ)。この行の units=0 は「ロット未割当のトラッキングマーカー」であって「サイズ 0 の発注」ではない — 読み手はこの units をサイズとして使ってはならない。`shadow_tracking` prefix 維持で startswith 依存の guard/tool は互換。

## 一般化された教訓

> **In-memory な dedup / cooldown / cache state はプロセス境界 (restart だけでなく並走・重複デプロイ) を越えられない。プロセスをまたいで守るべき不変条件は、共有永続層 (DB) を write-time で参照して判定せよ。** そして **retroactive な cleanup (boot backfill 等) は「いつ走るか」がそのまま盲点になる** — 起動時のみの回収は「作成〜次回起動」を無防備に残し、皮肉にも churn 抑制で盲点が広がる。read-time でなく write-time に寄せると盲点が消える。

## 関連 commit / doc

- 2026-04-30 [[lesson-shadow-emit-dedup-2026-04-30]] — bypass 経路が gate を共有していなかった (1〜2 例目) + restart で in-memory 消失 (hydration + boot backfill 導入)
- 2026-05-03 [[lesson-per-bar-dedup-tf-aware-2026-05-03]] — 固定 60s が 15m/5m bar を取りこぼした (3 例目) + TF-aware 窓
- 2026-08-09 `project_dt_ctx_hour_utc_live_freeze` — 発火数ベース過去判断の再検討 (4 例目周辺)
- 2026-09-02 本 lesson — プロセス境界 + boot backfill の write-time ギャップ (5 例目)。forensics: [[hourblock-recal-and-ema200-verdict-2026-09-02]] Study 2
