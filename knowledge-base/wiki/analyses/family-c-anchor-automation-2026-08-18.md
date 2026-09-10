# family C アンカー自動化パケット (2026-08-18)

**user 承認**: 2026-08-18「ここまでデータ揃ってるなら自動化させて」。
**SSOT**: MEMORY `user_manual_edge_usdjpy_carry_2026_08_12` 追記 1〜7 / [[intervention-history-anatomy-2026-08-18]] family C 節。
**性格**: 純データ基盤 + defensive monitoring (rule:R3)。live/tier/lot 変更ゼロ。シグナル計算ゼロ。

## 1. rate-anchor-daily — family C 材料の日次蓄積

- **目的**: user「水平線理論」最終形 = 金利観測フェアバリュー帯からの乖離リバージョン (family C、pre-reg 前) の**材料**を毎日蓄積し、09-18 スキャンの A/B/C 統合裁定と将来の pre-reg explore を可能にする
- **ツール**: `tools/rate_anchor_ingest.py` (e20_rates_ingest の配管様式を踏襲 — allowlist / wareki パーサ再利用 / manifest)。**凍結 e20 パネル (`knowledge-base/raw/bt-results/e20/`) には触れない** — 出力は新設 `data/external/rate_anchor/` (git 追跡、README 同梱)
- **ソース (全 keyless)**: MoF `jgbcm_all.csv` (JGB 全 15 テナー歴史、Shift-JIS+和暦、月次ラグ) + MoF 英語版 `jgbcme.csv` (当月分、日次更新 — ラグを補完) / FRED `fredgraph.csv` DGS1/2/5/10 / ZN=F 日足 (`data/cache/yield/ZN_F_1h.parquet` の UTC-day 集計)
- **蓄積規約**: 全 CSV union-merge (重複日 fresh 採用 = ベンダー訂正反映)、行数単調非減少・既存日付欠落なし・左端保持を assert (lesson-rolling-window-cache-overwrite-2026-08-14)。manifest はタイムスタンプなしの決定的生成 (データ不変なら diff ゼロ)
- **実行**: `.github/workflows/rate-anchor-daily.yml` 平日 21:15 UTC (`--refresh-zn` で ZN 1h cache も日次延伸 — 週次 zn-cache-refresh は backstop 残置、merge 冪等)。**repo へのデータ commit 経路は GH Actions のみ** (Render cron は書込不可)
- **規律境界**: **材料収集のみ。フェアバリュー帯・乖離・シグナルの計算は本パイプラインでは構造的に行わない** (family C は pre-reg 前 — signal×outcome 接触の予防)。USD_JPY 価格との join も行わない
- **シード実測 (2026-08-18)**: jgb_yields 3,328 行 (2013-01-04→2026-08-17、前日鮮度確認) / us_treasury_yields 3,554 行 (→08-14、FRED ラグは union-merge で自己修復) / zn_f_daily 756 行 (→08-18)。値の突合: JGB 10y 08-17 = 2.919、DGS10 08-14 = 4.68 (ソース原本一致)

## 2. intervention-watch — E-A 検知器の defensive alert 化

- **rule**: [[mof-intervention-forward-prereg-2026-07-24]] §2.2/§5.2 凍結 `(X,Y)=(2.0, 0.25%)` **as-is (再校正禁止)**。E-A は 2026-08 verdict で forward 的中 p=0.0143 = real-time 検知の実証済み
- **ツール**: `tools/mof_intervention_watch.py` — 前 UTC 営業日 1 回評価 → `knowledge-base/raw/intervention_watch/YYYY-MM.jsonl` 追記 (JSONL が dedup 状態) → candidate=1 なら Discord 通知
- **実行**: `.github/workflows/intervention-watch.yml` 00:20 UTC 火-土 (前 UTC 営業日 = 月-金) + 04:50 catch-up (dedup で no-op)
- **スコープ境界 (絶対)**:
  1. **監視 + 通知 + KB 記録のみ** — live gating (発火後 48h 新規ロング禁止等) の自動執行は**実装しない**。それは #4 §5.5 Variant B の別 pre-reg + user 最終承認事項 (E-C FAIL により SELL 執行系は stage-2 進行不可)。test pin `test_no_gating_or_order_path_imported` が order 系 import を構造遮断
  2. **candidate ≠ 介入ラベル** — 公式ラベルは MoF 開示のみ。alert 文面にも明記
  3. **grade 分離** — 本 alert は yfinance 1h → UTC-day 集計 (`grade` フィールドで永続記録)。verdict-grade 測定 (mof-next-episode-reverdict、11-14) は凍結どおり Massive 15m mid — **alert 記録を candidate list S に流用禁止** (ベンダー系統が違う)。yfinance 日足の UTC ずれ lesson は intraday 集計には非該当だが、日足は使わない
- **スモーク実測 (2026-08-18)**: 08-17 評価 = 静穏日 candidate=false (co_ret +0.06%、ratio 0.97、n_bars 24)、dedup 再実行 no-op 確認

## 3. registry トリガ 3 点 (到達経路明記 — ZN 教訓)

| id | type | 期日/条件 | 到達経路 |
|---|---|---|---|
| `mof-monthly-total-2026-08-29-check` | deadline_info | 08-28 (公表 ~08-29 前後) | Tier-A cron が TRIGGERED 表示 → Claude が MoF 月次公表を確認 → **当日 user 報告** (7月「介入をくらった」説の答え合わせ。総額>0 でも日次帰属は Q3 開示まで不明、価格推定ラベリング禁止) |
| `statement-ladder-foundation-readiness` | conditional_info | 発言ラダー基盤の main 着地 | 並行セッション task_a3b5b005 が構築中 (08-18 時点 branch 未 push = 現状は構造的に未到達と自覚した上での watching)。着地→resolve + edge-dev へ family A 起草可通知 |
| `edge-supply-scan-monthly` (増補) | deadline_info | 09-18 | 第4次スキャンに A/B/C 統合裁定を追加。C 材料 = rate-anchor-daily / B 入力 = intervention-watch / A 基盤 = 上記トリガ |

## 4. 次アクション

- edge-dev レーン (friendly-cohen 系) へ family A/B/C pre-reg 起草開始可を通知 (本パケット main 着地後)
- family C pre-reg 起草時の必須事項 (SSOT 追記 7): ppp #14 corpse との**明示差分節** (anchor が価格由来でない / 日次リプライス / USD_JPY 単独)、負の prior (slow-MR 死型 4 例) の正直な記載、「介入 dip」を価格シグネチャで識別しない (explore は 2014-2021 窓 + 介入と呼ばない dip 定義)
