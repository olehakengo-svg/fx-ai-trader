# MASSIVE ベンダー欠損 2 区間の OANDA backfill — 2026-07-29 (rule:R3 データ配管修理)

## TL;DR

MASSIVE (Polygon 互換) の FX aggregates は **2019-09-14〜2019-10-05 (23日)** と **2020-10-13〜2020-11-14 (34日)** にベンダー側のデータ穴を持つ (ペア依存の重症度)。ローカル `data/cache/massive/` はベンダーを正確にミラーしており、**MASSIVE 再取得では埋まらない** (API 直接プローブでローカルと欠損日リストが完全一致)。`tools/massive_gap_backfill.py` (新規) で **OANDA v20 mid candles (UTC alignment) から欠損バーのみを 45 ファイル / +61,709 行 補完**した。live/tier/Kelly への影響なし。

- 発見経緯: holiday カレンダー観測前検証 ([[holiday-calendar-verification-2026-07-29]]、branch `claude/hopeful-kapitsa-417e40` で起票) 中に USD_JPY の窓内 0 行を実測
- 執行: 本 doc + `tools/massive_gap_backfill.py` (PR 同コミット)。データ実体は gitignore のためローカル/本番それぞれで実行

## 1. 欠損の全容 (横断スキャン実測、backfill 前)

窓内期待行数に対する充足率。**穴はソース側でペア×窓ごとに異なる**:

| ペア | 2019 窓 (09-14..10-05) | 2020 窓 (10-13..11-14) |
|---|---|---|
| USD_JPY | **0% (全欠)** | **0% (全欠)** |
| USD_CAD, USD_CHF | ~48% (09-25 以降欠) | **0% (全欠)** |
| NZD_USD, NZD_JPY | ~48% (09-25 以降欠) | ~37% (10-25 以降欠) |
| EUR_USD, GBP_USD, EUR_GBP, EUR_JPY, GBP_JPY, EUR_AUD | ~100% (完備) | ~37% (10-25 以降欠) |
| AUD_USD, AUD_JPY | ~100% | ~100% (日曜バー数本のみ欠) |

対象 = 当該窓をスパンする全 TF (5m/15m/1h/4h/1d) の長期履歴ファイル (`*_2014_2026` / `*_12y_*` / plain 1d/5m)。2021 年以降開始のファイルは窓外。

## 2. 根本原因 — ベンダー側の穴 (プローブ証拠)

MASSIVE API 直接照会 (`/v2/aggs/ticker/C:USDJPY/range/1/day/2019-09-10/2019-10-10`) が **2019-09-13 の次を 2019-10-06 に飛ばして返す** (status OK、エラーなし)。部分欠損ペア (USD_CHF 2019 窓 / EUR_USD 2020 窓) はベンダー返却の日付リストとローカル parquet の日付リストが**完全一致** = ローカルキャッシュは取得ミスではなくソースの忠実なミラー。

**refresh 経路が埋めない理由** (3 重):
1. `tools/bt_data_cache.py` の差分更新は「最終バー timestamp → 現在」のみを fetch して concat ([bt_data_cache.py:127-137](../../../tools/bt_data_cache.py)) — **履歴中間の穴は構造的に更新対象外**
2. TF_CONFIG の全量取得上限は 180〜730 日 — 2019/2020 に届かない
3. 届いたとしてもベンダーに無いので何度取得しても埋まらない

専用 cron は存在せず、BT ツールが `BTDataCache.get()` を呼んだ時のオンデマンド差分更新 (これは今回の欠損とは無関係で正常動作)。

## 3. 修理 — `tools/massive_gap_backfill.py`

- **ソース**: OANDA v20 `/v3/instruments/{pair}/candles` mid、`dailyAlignment=0&alignmentTimezone=UTC` — H4 バーは 0/4/8/12/16/20 UTC、D は 00:00 UTC で **MASSIVE の UTC alignment と完全一致** (プローブ検証済)。complete=true のみ採用
- **era-local pattern guard**: 追加バーは対象ファイル自身の窓前後 ±90 日に実在する (weekday, hour, minute) の組に限定 — 当時の session 慣行 (日曜 21:00 UTC オープン等) を保存。peer ファイル行数は完備基準に**使わない** (5m×2020 窓は全ファイルが同じ穴 = peer max 自体が欠損値、の罠を dry-run で検出済み)
- **不変量 (assert)**: 既存行はバイト不変 / 追加は窓内のみ / index 重複ゼロ
- **provenance**: 全書換ファイルに `.bak-pre-gapfill-2026-07-29` バックアップ + `.audit.json` に `backfill` レコード (source / 窓別追加行数 / 理由)
- **冪等**: 再実行は added=0 (dry-run で確認済)

### 結果 (2026-07-29 ローカル実行)

45 ファイル / +61,709 行。ペア別: USD_JPY 27,303 / GBP_JPY 8,638 / GBP_USD 6,363 / EUR_USD 6,238 / USD_CAD 4,851 / USD_CHF 4,078 / NZD_USD 2,941 / 他 <1,000。窓内 0 行ファイルは **19 → 0**。

**検証**: (a) 全ファイル再スキャンで両窓とも期待行数到達 (b) ギャップ境界の価格連続性 = クロスソース jump 0.003〜0.07% (2019-09-14 境界の 0.54% は通常の週末ギャップ)、1d と 5m の境界値が一致 (c) 既存行バイト不変 assert 通過。

⚠️ **Volume/n_transactions の意味**: backfill 行の volume は OANDA tick count であり MASSIVE の volume とスケールが異なる。窓内で volume 系特徴量を使う分析は `.audit.json` の backfill 窓を確認すること。OHLC は mid で、境界一致から実用上同質。

## 4. 凍結物・過去 explore への影響評価

| 対象 | 影響 | 措置 |
|---|---|---|
| **E15/E7 pre-reg data ledger** (plain `{pair}_15m.parquet` 13 本を rows_at_ledger_last で凍結、phase-1 verdict 08-28) | backfill すると `load_and_verify_bars` の台帳再現が壊れる | **plain 15m は backfill 恒久除外** (ツールに `_EXCLUDE_RE` で code pin)。初回 run で誤って 6 本触れたが `.bak` から**バイト同一復元済み** (net 変更ゼロ)。なお plain 15m は各種 explore の短い `--days` フル取得上書き (WS3 round-2 prep 等) で**それ以前から 11/13 ペア台帳再現不能**だった → **同日修理済み**: phase-0 実行 worktree (`e15-oos-20260722`) に verdict data_ledger sha256 と一致する原本 13 本が現存 → `tools/e15_e7_data_refreeze.py --restore-from` で **byte-exact 復元** + 凍結コピー (`data/cache/massive/e15_e7_frozen/` + sha256 manifest `raw/bt-results/e15_e7_frozen_manifest_2026-07-29.json`)。判定器 `load_and_verify_bars` で 13/13 GREEN 実証。**MASSIVE 歴史バー集合は不安定** (fresh 再取得で AUD_USD が台帳比 −25 行の drift) — 凍結コピーが必須の理由。phase-1 実行前は `--verify-only` pre-flight、clobber 再発時は `--restore-from-frozen`。詳細: runbook `e15_phase0_execution_status.md` 2026-07-29 節 |
| **gotobi 較正 explore** (`USD_JPY_5m_2014_2026` 使用、family クローズ 2026-07-28) | 探索窓内の 2 窓に五十日イベントが存在するが当時データ 0 行 | robustness 評価済み・**verdict 不変** (発見側 branch で注記済)。データは backfill 済みになったため将来の再走は当該日を含む — ただし family クローズと再試行禁止スコープは不変。[報告書](../../../reports/gotobi-calibration-explore-2026-07-28.md) に data note 追記 |
| **holiday family** (凍結前、縮約版が背景キュー) | 凍結**前**に是正完了 = 幸運なタイミング | pre-reg 凍結時は backfill 済みデータで LOCK し、data ledger に `.audit.json` の backfill レコードを含めること |
| **W3 wick 12y** (`tools/bt/data_prep_manifest.json` が USD_JPY/GBP_JPY 5m_2014_2026 を sha256 pin、完了済) | sha256 変化 | `.bak-pre-gapfill-2026-07-29` の sha256 == manifest 値を**検証済み** — 完了済み監査の provenance は .bak が保持 |
| **JPY 台帳 12y audit** (`*_12y_audit`、PR #124 完了) | 2020 窓に +1〜573 行 | 決裁済み記録は不変。再走時は backfill 済みデータになる (改善方向) |
| **HIP-1 holdout lock** (2025-11-04..2026-05-04) | なし — backfill 窓は 2019/2020 でロック窓外 | — |
| **MoF intervention forward pre-reg** ([[mof-intervention-forward-prereg-2026-07-24]]、`USD_JPY_15m_2014_2026.parquet` 使用) | 探索窓側の 2019/2020 に行が増えた (verdict は将来の MoF 開示ラベル待ち) | **verdict 完全性は不変** — 同 pre-reg の「バックフィルは実施しない」宣言は **2026 窓 (2026-05-07 の穴) スコープ** (二度目の接触・ソース選択自由度の封鎖が目的) であり、本 backfill は 2019/2020 窓のみで 2026-05-07 は**未接触のまま** (母集団 M=21 / k_eff 規約は凍結どおり)。探索は 07-24 に旧データで完了済み・凍結済みで再走しない (2026-07-29 事後評価) |
| **BTDataCache 消費者** (365d 以下の BT) | なし — get() は ≤365d スライスで 2019/2020 行は不可視 | — |

## 5. 恒久運用

- 新規に 12y 級の MASSIVE fetch を行ったら、本ツールを一度走らせて 2 窓を補完する (audit.json に記録が残る)
- plain `{pair}_15m.parquet` の除外は E7 family クローズまで維持 (code pin 済み)
- MASSIVE の他の歴史窓に同種の穴が見つかった場合は `WINDOWS` に追記して再実行 (冪等)

## Related

- [[holiday-calendar-verification-2026-07-29]] (発見元、別 branch)
- [[e15-e7-event-modality-prereg-2026-07-18]] §3.1 (data ledger 凍結)
- [[gotobi-calibration-explore-prereg-2026-07-28]]
- `tools/massive_gap_backfill.py` / `tools/bt_data_cache.py` / `tools/fetch_massive_data.py`
