# Trigger Watch 評価空白 (2026-09-06〜09-10) 影響監査

- 監査日: 2026-09-10 (rule:R3)
- 監査主体: fix/trigger-watch-crash-20260910 (本 PR)
- 対象: `tools/prereg_trigger_watch.py` の全面クラッシュ (KeyError) による日次評価空白
- 関連: [[pr-review-gate-2026-09-08]] (インシデント記録) / PR #236 (修復) / PR #226 (混入)

## 1. 検証結果: 修復は PR #236 で完了済み (重複修理は不要)

反証レビューの主張「registry エントリ `roster-e2-silent-promoted-cells` の `requirements`
欠落で build_report() が KeyError 全面クラッシュ — 全 active トリガの日次評価が 09-06 から死亡」
は**過去形としては正しく、現在形としては修復済み**。origin/main (1edd2ce2) で実測:

| 検査項目 | 実測結果 |
|---|---|
| (a) クラッシュするか | **しない** — `python3 tools/prereg_trigger_watch.py` exit 0 |
| (b) 全 active トリガが評価されるか | **される** — registry 60 エントリ中 active 40、全 40 の id がレポートに出力 (欠落 0) |
| (c) EVAL_ERROR 箱に落ちるエントリ | **0 件** |

PR #236 (188e62ad、2026-09-10 17:22 JST マージ) が導入済みの防御:

- `roster-e2-silent-promoted-cells` を `conditional_info` 型へ修復 (reachability 付き、watching に出力される)
- `evaluate_trigger()` 隔離ラッパ — 壊れたエントリは自分だけ EVAL_ERROR を名乗り、残りは評価継続 (`tools/prereg_trigger_watch.py` L719-734)
- EVAL_ERROR は DATA_UNAVAILABLE と別箱 + exit 2 で呼び出し側にも故障を名乗る
- `lint_schema()` — 型別必須フィールド (REQUIRED_FIELDS_BY_TYPE、全 11 型網羅) + reject-by-default 3 層 (top-level / nested spec / コレクション要素)
- `scripts/check.py` 第 9 チェック = registry lint (検査不能は ERROR)
- `quant_gate_status.run_prereg_trigger_watch()` の returncode 検査 (exit 2 で stdout を捨てない + 故障 banner 前方固定)
- counterfactual テスト: `tests/test_prereg_trigger_watch.py::test_lint_schema_catches_the_exact_2026_09_08_defect` (欠落 fixture で lint 検出)、`test_one_broken_entry_does_not_blind_the_other_entries` (fault injection で隔離確認)、`test_required_fields_cover_every_machine_evaluable_type` (型網羅 pin)

数値の訂正: レビュー主張の「全 33 active トリガ」は当時の実数と不一致 — インシデント記録
([[pr-review-gate-2026-09-08]]) は 51 エントリと記録、現 registry は 60 エントリ / active 40。

### 本 PR で追加した残欠陥修理 (同型検査)

`quant_gate_status.run_quant_readiness()` に同型欠陥が残っていた:
`r.stdout or r.stderr` は returncode を見ないため、(a) 非ゼロ exit + 部分 stdout で
stderr の traceback を**黙って捨て**、途中まで印字された本文が健全な Readiness に見える、
(b) stdout 空で素の traceback が本文として流れる。run_prereg_trigger_watch と同じ
fail-loud 化 (banner + stderr 末尾 6 行 + 部分本文保持) + counterfactual テスト 3 本を追加。

## 2. 評価空白の窓

| 時点 | 事象 |
|---|---|
| 2026-09-06 12:11 UTC | PR #226 (29cad718) が壊れたエントリを main へ着地 |
| 2026-09-07〜09-10 00:20 UTC | Tier-A cron (`fx-ai-tier-a-gate-status`, `quant_gate_status.py --to-discord --strong`) **4 run が影響** — watch 節は traceback (全エントリ未監視) |
| 2026-09-08 | 発見 (未読 finding の遡及読解、[[pr-review-gate-2026-09-08]]) |
| 2026-09-10 08:22 UTC | PR #236 マージ = 修復。**本日 00:20 UTC の cron 実行より後**のため、修復後の初回 cron 配信は 2026-09-11 00:20 UTC |

⚠️ つまり本監査 (09-10 の手動全評価) が**修復後最初の読み手**であり、下記 TRIGGERED は
明日の cron まで Discord には届かない。

## 3. 空白期間に埋もれていた TRIGGERED — 全評価 1 回の実測 (2026-09-10)

TRIGGERED は **2 件** (active 40 中、残り 38 は watching/info)。

### 3.1 e1-positioning-ingest-freshness — 🔴 新規・進行中 (空白が実害を持った唯一の例)

- 実測: verified:{PAIR}:outlook **全 13 キーが stale 7.9h超 (増加中) > 閾値 2h**
- 本番一次確認 (`/api/positioning/status` 直叩き): 最終 snapshot **2026-09-10T06:58:44Z**、
  `consecutive_failures=11`、stale_seconds ~28,300
- 影響: E1 は唯一の主力供給ライン (first look 2026-10-15)。Render Disk 満杯 71.3h 停止
  (2026-08-23〜26) が coverage 予算を既に 5.7% 消費しており、**残 budget は ~41h**。
  本停止が継続すると first look の coverage gate 90% を割るリスクがある
- 空白との関係: 停止開始 (06:58 UTC) は修復マージ (08:22 UTC) より前 = 検知経路が
  死んでいる間に始まった。本日 00:20 UTC cron も故障版のため、**本監査がなければ
  最短でも 09-11 00:20 UTC まで誰にも見えなかった** (その時点で stale ~17.4h)
- 処置: 原因調査・復旧を別タスクとして起票済み (本 PR のスコープ外 — 監視器の修理と
  ingest の修理は別の故障)

### 3.2 t5-jpy-cap-restore-price — 既知・空白起因ではない

- 実測: D1 close=154.038 < 159.50 — T5 復帰第 1 要件成立 (2026-08-10 から継続的に成立)
- 第 2 要件 (介入観測の外部一次情報認定) は保留のまま、lot 1.0x 復帰は R1 = user 決裁事項
  ([[mof-monthly-total-verdict-2026-08-31]] §4)。空白期間中に状態変化なし

## 4. 見逃しスイープ (期日超過・N 到達)

- **deadline が空白窓 (09-06〜09-10) に落ちた active エントリ: 0 件**。
  最近傍は `ps-seat-supply-remeasure-30d` (deadline=2026-09-10 = 本日) — 評価器は
  `today > deadline` で発火するため判定日は 09-11。見逃しなし (N=7/15 → retire 判定へ)
- **N 到達 (n_decide 到達) が空白窓で起きた形跡: 0 件**。N は since 固定の単調増加であり、
  現時点で n_decide 以上のエントリが 1 つも無い (最接近: t8-sweep-defer-decision N=9/10、
  ps-carveout-regate-post-172 N=6/10) = 窓内でも未到達
- 窓内に resolve されたエントリ: `rnb-support-bounce-registration-decision`
  (2026-09-10、PR #238) — watch 経由ではなく独立の R1 手続きで前進しており、空白の影響なし

## 5. 結論

1. **修復済み** — PR #236 が本監査の想定修理 (conditional_info 型修復 / 隔離ラッパ /
   EVAL_ERROR 別箱 / registry lint / check.py 第 9 チェック / gate_status returncode 検査) を
   全て実装済み。counterfactual テストも網羅。重複修理はしない
2. 空白期間 (~3.8 日、cron 4 run) に**期日超過・N 到達の見逃しはゼロ**
3. ただし空白明けの全評価が **E1 positioning ingest の進行中停止 (7.9h+、全 13 ペア)** を
   検出 — これは空白がなければ最大 ~6h 早く見えた実害候補であり、E1 残 coverage budget
   ~41h に対する現在進行形の消費。復旧は別タスクで追跡
4. 残欠陥として `run_quant_readiness()` の stderr 黙殺経路を本 PR で fail-loud 化
