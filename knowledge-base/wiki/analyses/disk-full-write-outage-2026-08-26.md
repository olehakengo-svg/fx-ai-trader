# Render Disk 満杯による全 DB 書込み停止 — 継続中の事故と恒久対策 (2026-08-26)

- **rule**: R3 (構造バグ / 算数破綻 — 365 日 BT スキップ)
- **status**: 対策 main 着地、本番復旧確認は deploy 後
- 関連: [[deploy-churn-trading-gap-2026-08-21]] / [[hull-fire-rate-funnel-2026-08-24]] / MEMORY `project_render_disk_full_write_outage_2026_08_25`

---

## 1. 一行要約

**2026-08-21T18:46Z 以降、本番の全 SQLite 書込みが失敗し続けている。「08-25 に解消」という既存記録は誤りで、本セッション (08-26T03:18Z) の実測でも `database or disk is full (consecutive=85)` が継続していた。** クリーン N 蓄積 = M1 の唯一のボトルネックが、5 日間完全にゼロだった。

## 2. 事実 (全て実測、推定ではない)

| 観測 | 値 | 取得元 |
|---|---|---|
| trades の最終行 | `entry_time = 2026-08-21T18:46:24Z` | `/api/demo/trades?limit=500` の max |
| evaluated_candidates 直近 1/2/3 日 | **0 / 0 / 0 件** | `/api/demo/evaluated-candidates?days=N` |
| 同 直近 7 日 | 12,738 件 (全て 08-19〜08-21 の残骸) | 同上 |
| 本番ログ (08-26T03:16-03:18Z) | `database or disk is full`、`consecutive=85` | Render app log |
| 失敗している書込み経路 | positioning outlook / health / `log_candidates` / `_tick_entry` | 同上 |
| disk | `/var/data`, **1 GB**, `dsk-d7757ama2pns73dea1f0` | Render service 定義 |

`/api/demo/status` は `main_loop_alive=true`、`tick_counts` も `block_counts` も増加し続けている。**これらは全てプロセス内メモリのカウンタで、DB を経由しない。** 結果としてダッシュボードは「静かな相場」と区別がつかない。前回の発見が手作業だったのはこのためで、今回も発見は偶然ではなく能動的な突き合わせによる。

## 3. なぜ 5 日止まったのか — 3 つの構造欠陥 + 1 つの死んだ検知器

### D1. `backup_database` が「コピー先行 → ローテーション後行」だった

満杯時、`source_conn.backup(dest_conn)` が例外を投げ、**空きを作る唯一の処理であるローテーションに制御が到達しない**。失敗するほど回復不能になる自己増悪ループ。4 日連続 FAILED + バックアップ不在という前回の記録と完全に整合する。

→ **修正**: ローテーションを先頭へ移動し、その後に free-space pre-flight を挟む。容量不足時はコピーを試みず `status="skipped_low_disk"` を返す (半端なファイルを残さない)。**counterfactual 検証済み** — `test_backup_rotates_before_copying` は旧実装で FAIL、新実装で PASS。

⚠️ ローテーション対象の census から「今日の書き先」を除外している。含めると `keep_last` の枠を 1 つ食い、実効保持数が黙って 1 減る。

### D2. 空き容量を測る計装がどこにも無かった

`shutil.disk_usage` も `statvfs` も、リポジトリ全体で参照ゼロだった。エンドポイントも、ログ行も、アラートも無い。

→ **修正**: `modules/disk_guard.py` (測定) + `GET /api/admin/disk_status` (読み出し) + `scripts/anomaly_watcher.py` の 15 分毎ポーリング (warn 75% / critical 90%)。**閾値は API 応答に同梱して返す** ので、判定基準は本番コードと単一ソース。

### D3. `evaluated_candidates` に retention が無かった

2026-04-28 の作成以来、無制限に増加。08-24 の実測で **517,378 行 / 54 戦略 / 2026-04-28〜08-21** ([[changelog]] 08-24 項)。皮肉なことに `query_candidate_meta` の docstring 自身が 「no retention job exists as of 2026-08-24」と書いていた — 認識されていたが実装されなかった。

→ **修正**: `prune_candidates` (keep_days=90、env `C1_RETENTION_DAYS` で可変) を起動時と日次レビューで実行。

⚠️ **正直に書く**: SQLite の `DELETE` はページを再利用可能にするだけで**ファイルは縮まない**。これは*将来の増加を止める*対策であって、*既に消費された容量を取り戻す*対策ではない。`VACUUM` なら回収できるが、実行にはほぼ DB 1 個分の空きが要る — 満杯時に最も無い資源なので、意図的に実行しない。**したがって今回の即時解放に prune は寄与しない**。即時解放は §4 のバックアップ削除が担う。保持 90 日は「観測された最長読み出し窓 30 日 × 3 倍マージン」から導出し、定常サイズを 2026-08 時点付近に固定する (無制限増加を止めるのが目的で、縮小が目的ではない)。

### D4 (最悪). 唯一の検知器が 126 日間 no-op だった

`check_live_n_stagnation` は `status["last_trade_time"]` を読んでいた。**この key は `/api/demo/status` にも app.py のどこにも存在しない** (全数 grep で生成箇所ゼロ)。docstring は自ら「status API に last_trade_time があると仮定。無ければ skip」と書いており、**その仮定は一度も検証されなかった**。2026-04-22 の作成以来 126 日、常に `[]` を返していた。

「24 時間トレードが増えなければ警告する」— まさにこの事故のための検知器が、この事故の間ずっと沈黙していた。

→ **修正**: 時刻は `/api/demo/trades` の実データ (`entry_time`、本番応答で実在を確認済) から取る。そして**時刻が 1 件も読めない場合を `stagnation_check_broken` として異常報告する** — 黙って skip する旧挙動こそが欠陥だったため。

## 4. 復旧手段 (書込みが 1 件も通らない状態からの脱出)

満杯時は「書ける処理」が全滅しているので、**書込み成功を前提としない解放手段**が要る。唯一それを満たすのが `os.remove` によるバックアップ削除。

`disk_guard.emergency_reclaim()` は起動時 (DemoDB 生成より前) と `POST /api/admin/disk_reclaim` から走る:

1. 古いバックアップ削除 — 書込み不要。**readable なコピーを recent なコピーより優先**する (満杯で中断されたコピーは mtime が最新になるので、素朴な「最新を残す」は壊れたファイルだけを残す)
2. `wal_checkpoint(TRUNCATE)` — main DB の伸長を伴いうるので、1 の後にのみ試行
3. 前後の実測差分を `freed_bytes` として報告 (推定値ではない)

平常時は **no-op** (critical 未満かつバックアップ余地ありなら何も消さない)。

## 5. 教訓

> **「書込み停止」は「異常」ではなく「凍結」として観測される。** メモリ内カウンタで駆動されるダッシュボードは、永続化層が全滅していても正常に見え続ける。生存監視は必ず**永続化層に到達した最新レコードの時刻**で行う — プロセスの生存フラグでも、tick カウンタでもなく。

> **計装の field 契約は「仮定」ではなく「検証対象」。** docstring に「〜と仮定。無ければ skip」と書いた時点で、それは検知器ではなく飾りになる。読めなかったことは、異常が無かったことではない。**測れないなら測れないと鳴らせ。**

> **回復処理は、壊れている資源に依存してはならない。** 満杯からの回復手順が「まず書き込む」で始まるなら、それは回復手順ではない。

ZN 教訓 (計装契約バグ) の **5 例目**、「読まれない計装は劣化を検知できない」([[hull-fire-rate-funnel-2026-08-24]]) の直系。今回は *読まれてはいた* が、**読んでいた値が常に存在しなかった**という一段深い形。

## 6. 残件 (user 決裁)

- **disk 1 GB は本件の背景条件**。回収後の実使用率が高止まりするなら増設 (sizeGB 引き上げ) が必要だが、**課金が発生するので user 決裁事項**。deploy 後の `/api/admin/disk_status` 実測を待って判断する。
