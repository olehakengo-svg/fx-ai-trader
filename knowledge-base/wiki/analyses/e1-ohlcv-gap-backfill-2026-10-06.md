# E1 first look — M15 OHLCV の vendor 欠落 (MASSIVE) と OANDA mid 補填 (2026-10-06、rule:R3 data-pipeline repair、record-only)

**Status**: 執行済み (2026-10-06 autopilot)。E1 の値 (skew / IC / EV / PnL) には一切触れていない — 本稿の数字は **bar 件数・時刻・sha256 のみ** (手順書 [[e1-first-look-runbook-2026-09-22]] §6-2 の運用)。
**出所**: 手順書 §2-3b「10-06 に `--preflight-only` で gaps / extra を先に確認する」の実行結果。registry `e1-first-look-freeze-due` (10-08)。
**関連**: [[e1-positioning-contrarian-prereg-2026-07-16]] §2.1 (ソース = MASSIVE M15 mid) / §2.3 (OHLCV join 契約) / `tools/massive_gap_backfill.py` (2026-07-29、2019/2020 vendor 窓の OANDA 補填 = 先例) / MEMORY `project_massive_vendor_gap_backfill_2026_07_29`。

---

## §1 発見: 評価窓内に vendor 由来の内部欠落が 8/13 pair (合計 1,125 本)

13 pair を `bt_data_cache.py refresh 15m` (13 pair 明示) で 2026-10-06T02:15/02:30Z まで更新した後、`--preflight-only` (cutoff 2026-10-08T06:33:31Z、t0 2026-07-16T06:33:31Z) の結果:

| pair | 窓内 rows / slots | 欠落 (gaps) | runs | 最長 run | 初出 | 窓内 extra |
|---|---|---|---|---|---|---|
| USD_JPY | 5,547 / 5,552 | 4 | 4 | 1 | 2026-09-06 21:45Z (日曜) | 0 |
| EUR_USD | 5,551 / 5,552 | 0 | — | — | — | 0 |
| GBP_USD | 5,547 / 5,552 | 4 | 4 | 1 | 2026-07-19 21:45Z (日曜) | 0 |
| **EUR_JPY** (primary) | 4,998 / 5,552 | **553** | 27 | **53** | 2026-07-28 00:00Z | 0 |
| **GBP_JPY** (primary) | 5,358 / 5,552 | **194** | 14 | 48 | 2026-07-16 06:30Z | 0 |
| AUD_JPY | 5,551 / 5,552 | 0 | — | — | — | 0 |
| AUD_USD | 5,315 / 5,552 | **237** | 11 | 48 | 2026-07-16 06:30Z | 0 |
| NZD_USD | 5,551 / 5,552 | 0 | — | — | — | 0 |
| USD_CAD | 5,552 / 5,553 | 0 | — | — | — | 0 |
| USD_CHF | 5,545 / 5,553 | 7 | 7 | 1 | 2026-08-02 21:45Z (日曜) | 0 |
| NZD_JPY | 5,552 / 5,553 | 0 | — | — | — | 0 |
| EUR_AUD | 5,456 / 5,553 | 96 | 4 | 44 | 2026-07-17 00:00Z | 0 |
| EUR_GBP | 5,522 / 5,553 | 30 | 2 | 19 | 2026-09-28 00:00Z | 0 |

(窓 = [t0, 末尾完結 bar 2026-10-06T02:15/02:30Z] の市場時間 15m スロット。`slots − rows` が欠落と 1 本ずれる pair があるのは t0 06:33:31 を含む 06:30 スロットを slots が数え rows (≥ t0 の完結 bar) が数えないため。)

形状は 2 種類:
- **平日 00:00Z 起点のアジア時間帯の連続欠落** (最長 53 本 ≈ 13h、EUR_JPY で 2026-08-21 00:00–13:00Z など) — クロス通貨 (EUR_JPY / GBP_JPY / AUD_USD / EUR_AUD / EUR_GBP) に集中。USD_JPY / EUR_USD / GBP_USD には無い。
- **日曜 21:45Z の 1 本欠落** (USD_JPY / GBP_USD / USD_CHF / GBP_JPY) — vendor の週初セッション規約 (判定器 `is_market_open` は NY Sun 17:00 = 夏時間 21:00Z open を市場時間に数える)。

**ファイル全体の `extra_off_grid_or_closed_bars` (13/13 で FAIL、1,456〜26,159 本/pair) は全て t0 以前 (2014〜2021 年) の閉場 bar** で、窓内 extra は 13/13 で **0** (`plan_pair.extra_in_window`)。スライスには入らないので凍結時は `--ohlcv-drop-extra-bars` を併記して preflight を通す (artifact は不変)。

## §2 fetch artifact ではなく vendor 本体の穴 (直接 probe)

欠落 run の区間を MASSIVE aggregates API に **1m / 15m / 1h** で直接問い合わせ (`modules.data._fetch_chunk`、本番と同じ経路):

| 区間 | 対照 | 結果 |
|---|---|---|
| EUR_JPY 2026-08-20T20:00–08-21T16:00Z (run 53 本を含む) | USD_JPY 同区間 | 15m: EUR_JPY **111 本** / USD_JPY 180 本。1m: 1,654 / 2,700。1h: 28 / 45 |
| GBP_JPY 2026-09-17T20:00–09-18T16:00Z (run 48 本を含む) | — | 15m 102 本、1m 1,517 本 (run 内 0) |
| EUR_JPY / GBP_JPY / AUD_USD / EUR_GBP の先頭 12 run | — | run 内 **0/N 本** (全 run) |

⇒ 同じ区間の bar が全 granularity で無い = **vendor 本体の欠落** (ページング・timeout・delta 境界の取りこぼしではない)。`refresh` の差分取得 (`last_ts` 以降) ではこの穴は二度と埋まらない。

## §3 なぜ受容しないか

判定器 `tools/e1_positioning_prereg_eval.py` は forward return / ATR の horizon を **配列位置** (`h_bars` 番目の bar) で進める (手順書 (xv))。53 本の穴の直前にある signal の h=4 (1h) forward return は実時間 14h 後の価格で計算される。EUR_JPY は窓の **10.0%** (553/5,552)、GBP_JPY 3.5%、AUD_USD 4.3% の bar が欠け、primary 2 pair が含まれる。`--ohlcv-max-gap-bars 553` で受容すると first look の推定量が静かに変わる — これは手順書が preflight を「fail-loud」にした理由そのもの。

pre-reg [[e1-positioning-contrarian-prereg-2026-07-16]] §2.1 の「ソース = MASSIVE 12y OHLCV M15 mid (本番 signal 関数と同一ソース)」は**価格列の素性**の宣言であり、OHLCV の欠落処置は pre-reg に無い (§2.5-2 の stale gap は positioning snapshots の LOCF に関する規則)。手順書 §3 は「欠落を受容するなら閾値を明示して verdict に併記」と書くだけで、補填は想定していなかった。

## §4 決定: 共有 cache を改変せず、窓内の欠落 bar だけを OANDA v20 mid で埋めた**複製**を凍結のスライス元にする

選択肢:
- (a) `--ohlcv-max-gap-bars N` で受容 — 上記の歪み。否。
- (b) **OANDA v20 mid M15 (price=M, dailyAlignment=0, alignmentTimezone=UTC, complete のみ) で欠落スロットだけ補填** — 2026-07-29 の `tools/massive_gap_backfill.py` (2019/2020 の vendor 窓を同方式で補填、provenance 付き) の先例に従う。採用。
- (c) MASSIVE の別 granularity から再構成 — §2 のとおり 1m/1h も無いので不可。

(b) の約束 (`tools/e1_ohlcv_gap_backfill.py`、pin `tests/test_e1_ohlcv_gap_backfill.py` 9 本):
1. **共有 `data/cache/massive/` は改変しない**。補填済み複製を `data/cache/e1_ohlcv/` に書き、凍結 export は `--ohlcv-src data/cache/e1_ohlcv` で読む。E15/E7 の凍結台帳 (`.bak-pre-refreeze-2026-07-29` + sha256) や他 consumer に触れない (なお共有 cache 自体は 09-22 / 10-06 の refresh で既に 07-29 時点の sha から動いている — 凍結 bytes は .bak が保持)。
2. 追加するのは **[t0, min(last_complete, expected_last)] の市場時間 15m スロットのうち src に無い bar のみ**。既存行は値・順序・dtype とも不改変 (書込み前 assert + 読み戻し検査)。OANDA が返した欠落外の bar は捨てる。
3. 埋め残し (OANDA にも無い bar) は `unfilled_bars` として残し、黙って受容しない (凍結時に `--ohlcv-max-gap-bars` で明示)。
4. 出力は件数・時刻・sha256 のみ。audit JSON (`raw/bt-results/e1-ohlcv-gap-backfill-<slug>-<date>.json`) に価格値は入らない (pin: `\d+\.\d+` 不在)。
5. OANDA の volume は tick 数で MASSIVE の volume と意味が異なる — 判定器は mid OHLC のみ使う (pre-reg §2.3)。verdict に併記。

**estimand 上の開示 (verdict §8 に転記する)**: first look の価格列は「MASSIVE M15 mid + 窓内欠落 1,125 本 (13 pair 合計、下表) を OANDA mid で補填」。補填 bar の割合は EUR_JPY 10.0% / AUD_USD 4.3% / GBP_JPY 3.5% / EUR_AUD 1.7% / EUR_GBP 0.5% / USD_CHF・USD_JPY・GBP_USD ≤0.13%、残り 5 pair は 0。MASSIVE と OANDA mid の価格差は pip 級で、欠落による horizon の実時間伸長 (最長 13h) より 2 桁小さい — ただしこれは定性で、first look の値を見てから補填方式を変えることは §6-2 違反 (補填方式は本稿で cutoff 前に固定)。

## §5 執行記録 (2026-10-06、counts only)

- refresh: 13 pair 明示で実行 → **5 pair (USD_CAD / USD_CHF / NZD_JPY / EUR_AUD / EUR_GBP) が DNS 解決失敗 / timeout で delta failed、`refresh` は exit 0 のまま既存 bar を保持** → 再実行で 13/13 到達 (末尾 2026-10-06T02:15/02:30Z)。⚠️ `bt_data_cache.py refresh` は部分失敗を終了コードに出さない — 必ず `--preflight-only` で 13/13 の末尾を確認する (手順書 §3 (a) の注記に追加)。
- 補填 (`tools/e1_ohlcv_gap_backfill.py --src <共有 cache> --dst data/cache/e1_ohlcv`、02:50:09Z): **gap 1,125 / filled 1,125 / unfilled 0** (全 70 run で OANDA が完結 bar を返した)。pair 別: EUR_JPY 553 / AUD_USD 237 / GBP_JPY 194 / EUR_AUD 96 / EUR_GBP 30 / USD_CHF 7 / USD_JPY 4 / GBP_USD 4、gaps 0 の 5 pair は byte copy (sha256 一致)。
- audit: `raw/bt-results/e1-ohlcv-gap-backfill-first-look-2026-10-06.json` (sha256 先頭 `d7576507c2b33792`、pair 別 src/dst sha256・run 一覧・件数)。
- 補填後 preflight (`--ohlcv-src data/cache/e1_ohlcv --ohlcv-drop-extra-bars`): **13/13 で残る理由は `stale_tail` のみ** (lag 207–208 本 = cutoff 未到達、10-08 06:33Z 以降の refresh で 0 になる)。gaps 0 / dup 0。

## §6 凍結日 (10-08) の手順変更 (手順書 §3 に反映)

```
(a)  refresh 15m 13 pair (共有 cache)          ← 10-06 と同じ。部分失敗は exit 0 なので (a') で末尾を見る
(a″) tools/e1_ohlcv_gap_backfill.py --look 1   ← 10-06〜10-08 分に新しい穴があれば埋め、複製を作り直す (audit は 10-08 日付で別ファイル)
(a') --preflight-only --ohlcv-src data/cache/e1_ohlcv --ohlcv-drop-extra-bars   ← 13/13 OK (lag 0 / gaps 0) を確認
(b)  --look 1 --slice-ohlcv --ohlcv-src data/cache/e1_ohlcv --ohlcv-drop-extra-bars
```
- `data/cache/` は gitignored なので、**凍結は共有 cache を持つ checkout (`/Users/jg-n-012/test/fx-ai-trader`) から実行するか、`--src/--dst/--ohlcv-src` を絶対パスで渡す** (10-06 は worktree から絶対パス指定で実行し、worktree 内の cache を見た初回 preflight は 11/13 missing で REFUSED だった — 配線の確認として記録)。
- 補填後に `unfilled_bars > 0` が出たらその本数だけ `--ohlcv-max-gap-bars N` を明示し verdict に併記 (10-06 時点は 0)。
- **POSTPONE 時** (§2.5-3、11-05 再凍結): `--postponed` で cutoff 11-05 / 別 dst `data/cache/e1_ohlcv_postponed/` / 別 audit 名。10-08 の複製は不改変で残し、postponed 凍結は `--ohlcv-src data/cache/e1_ohlcv_postponed` を読む (Codex P2 4191149521)。
- **src が無い / index が壊れた pair** は複製側の古いファイルを削除して exit 2 (前回成功分が今回の入力から作られたふりをして preflight を通らないように、Codex P2 4191149514)。

## §7 引用規律

- 本稿の件数は **2026-10-06T02:50Z 時点の [t0, 2026-10-06T02:15/02:30Z] 窓**の値。cutoff 到達後の再実行で窓が伸び件数は変わる — 凍結時の値は 10-08 の audit JSON と manifest `ohlcv_coverage` を引く。
- 価格値・skew・return は本稿にも audit にも無い。first look の値は判定器 `--verdict-run` (10-09〜10-14) まで誰も見ていない。
- 「MASSIVE に欠落がある」は **2026-07〜10 のクロス通貨 M15/1m/1h** について確認した事実で、他の期間・pair への一般化は probe が必要 (2019/2020 窓は 07-29 に別途確認済み)。

## §8 凍結時の再実行 (2026-10-09、autopilot)

- cutoff 到達後 (10-09T04:25Z) に同 tool を `--look 1` で再実行 (src/dst 絶対パス、共有 cache は不改変): 窓 [t0, 2026-10-08T06:15Z] で **gap 1,131 / filled 1,131 / unfilled 0**。10-06 (1,125) からの差 +6 は 10-06→10-08 の末尾区間に新たに現れた vendor 欠落 (GBP_JPY 194→197、AUD_USD 237→240)、他 6 pair は不変 (EUR_JPY 553 / EUR_AUD 96 / EUR_GBP 30 / USD_CHF 7 / USD_JPY 4 / GBP_USD 4)。gaps 0 の 5 pair は byte copy。
- 補填後 preflight **13/13 OK** (lag 0 / gaps 0 / dup 0) → 凍結 export は複製を `--ohlcv-src` に読み、manifest `ohlcv_coverage` 13/13 `ok` (gap_bars 0)。`--ohlcv-max-gap-bars` は不使用 (unfilled 0)。
- audit: `raw/bt-results/e1-ohlcv-gap-backfill-first-look-2026-10-08.json` (値なし)。凍結の記録は [[e1-first-look-runbook-2026-09-22]] §9、registry `e1-first-look-freeze-due` resolution。verdict §8 に「MASSIVE 同一ソースからの逸脱 = 窓内 1,131 本の OANDA mid 補填」を転記する。

## §9 判定器 POSTPONE 後の扱い (2026-10-10、autopilot)

- first look #1 の判定器は品質 gate (coverage 88.6% < 90%、ingest 停止 2 件由来) で `POSTPONE` — **OHLCV 側 (本稿の補填) は無関係** (preflight 13/13 OK、parquet sha256 13/13 一致、`bars_clipped_beyond_cutoff` 空)。estimand 開示 (窓内 1,131 本 OANDA mid 補填) は pre-reg §8-1 に転記済み。
- postpone 後の再凍結 (cutoff 11-05T06:33:31Z) では **複製を別ディレクトリ `data/cache/e1_ohlcv_postponed/` に作る** (`--postponed`、audit `raw/bt-results/e1-ohlcv-gap-backfill-first-look-postponed-2026-11-05.json`)。10-08 複製 `data/cache/e1_ohlcv/` と凍結スライス `data/cache/e1_frozen_look1_2026-10-08/` は不改変。10-08〜11-05 に新たに生じる vendor 穴も同手順で埋める (filled / unfilled を audit に、値は書かない)。
