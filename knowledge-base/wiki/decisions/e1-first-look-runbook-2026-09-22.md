# E1 first look 手順書 — 2026-10-08 cutoff → 凍結 export → 判定器 → 2026-10-15 verdict (rule:R3、手続きのみ)

**Status**: 手順書 (2026-09-22 起案、[[path-to-win-reassessment-2026-09-22]] §3 Rank 2)。**本稿は手続きの固定であり、pre-reg の定義・grid・期日・分岐には一切触れない** — SSOT は [[e1-positioning-contrarian-prereg-2026-07-16]] (🔒 LOCKED 2026-07-17)。本稿と pre-reg が矛盾したら pre-reg が勝つ。
**執行者**: Claude (autopilot、record-only)。verdict の解釈・PASS 時の実装承認・DEFERRED は user。
**凍結 look 規律**: 本稿の作成にあたり E1 snapshots の skew/ratio/avg 価格・IC・EV・PnL は一切閲覧・計算していない (§6-2)。本番への接触は `table=health_log` limit=5 の dry-run 1 回のみ (2026-09-22、`id 1..5`、値なし)。

---

## §0 なぜ tool が要るのか (とその限界)

- pre-reg §2.5-6 は「verdict 用データは cutoff 直後に **1 回だけ** export → parquet + sha256 を `raw/bt-results/` に保存。以後の分析は artifact のみ参照 (本番 DB 再クエリ禁止)」を要求する。これは**手続き要件**であり、tool が無くても手作業で満たせる — **tool 不在 ≠ verdict 無効** (無効化は §6 違反時のみ)。
- tool `tools/e1_positioning_frozen_export.py` はこの規約の**機械担保**: (i) 凍結 marker (`.sha256`) があれば `--force` なしで再実行拒否 = 「2 回目の export」を構造的に止める、(ii) stdout に値を出さない = export 作業そのものが peeking にならない、(iii) 判定器 `tools/e1_positioning_prereg_eval.py --artifact` の入力契約 (JSON dict `{"snapshots","health","synthetic":false}`) をそのまま書く、(iv) M15 parquet の cutoff スライスを判定器 `clip_bars_to_cutoff` と同一規約 (open + 900s ≤ cutoff) で作り sha256 を raw 側に残す。
- pin: `tests/test_e1_positioning_frozen_export.py` (20 tests、全てオフライン fake API) — 合成 roundtrip (書く→判定器 `load_artifact` で読む→sha256 一致) / 1 回だけガード / cutoff 前拒否 / 値非表示 (stdout に `\d+\.\d+` が出ない、合成 sentinel 値が出ない) / ページング dedup / 定数が判定器・ingest と同値。

## §1 タイムライン (固定、データ非依存)

| 日付 (UTC) | 何をするか | 出所 |
|---|---|---|
| **〜2026-10-06** | 準備確認 (§2)。tool/判定器の test green、`--self-check` pass、`--dry-run-health` 1 回、`data/cache/massive` の 13 pair 15m が cutoff まで届く状態にする段取り | 本稿 |
| **2026-10-08T06:33:31Z** | **cutoff #1** (t0 + 12 週)。この瞬間以降に生まれた行は first look に入らない | pre-reg §7 (脚注 13) |
| 2026-10-08 (cutoff 後) 〜 10-09 | §3 凍結 export (1 回だけ) + M15 スライス + sha256 記録 → PR | pre-reg §2.5-6 |
| 2026-10-09 〜 10-14 | §4 品質 gate spot check (§2.5-5) → §5 判定器 `--verdict-run` 実行 (実データ初適用) | pre-reg §2.5 / §6-2 |
| **2026-10-15** | §6 verdict を pre-reg §8 へ追記 + 分岐執行 (§7) | pre-reg §7 registry `e1-prereg-verdict-deadline` |
| 2026-10-18 | scan#6 で (a-1) probe の R1 起案可否を裁定 (§8 一行定義) | [[supply-space-feasibility-2026-09-17]] §1.3 |

postpone (§2.5-3 family gate 不成立) が出た場合のみ cutoff / verdict / 評価窓終端が **4 週スライド** (burn-in・窓開始は不変、1 回限り)。→ 10-08 → 11-05 / 10-15 → 11-12。第 2 回目不達は DEFERRED。

## §2 準備 (〜10-06、本番の値に触れない)

```bash
# 1. pin green (worktree 内、stale bytecode 事故防止で -B)
PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest tests/test_e1_prereg_eval.py tests/test_e1_positioning_frozen_export.py -q
# 2. 判定器の canary suite (合成のみ)
python3 -B tools/e1_positioning_prereg_eval.py --self-check
# 3. 本番 API 疎通 (許可範囲 §6-2: health_log の運用フィールドのみ、書込みなし)
python3 -B tools/e1_positioning_frozen_export.py --dry-run-health --limit 5
# 4. ingest 健全性は status API の運用フィールドのみ (verified 13 キー / stale)
#    → registry `e1-positioning-ingest-freshness` が毎日機械評価している
```

- **禁止**: `/api/positioning/export` を snapshots table で叩くこと (limit=1 でも生 skew 1 行の閲覧 = §6-2 許可リスト外)。tool には snapshots の試走モードを**意図的に実装していない**。
- **M15 parquet**: 判定器は `{PAIR}_15m.parquet` × 13 (primary 6 + confirmatory 7) の完備を `--verdict-run` で強制する (`tools/e1_positioning_prereg_eval.py` main、欠落 = exit 2)。`data/cache/massive/` のフル期間版は 2026-09-22 時点で末尾 2026-09-18T20:45Z (`EUR_GBP_15m.parquet` 実測) — cutoff まで届かせる更新は **cutoff 到達後** に `python3 tools/bt_data_cache.py refresh 15m` (差分更新) で行い、スライスはその後。価格データは E1 の凍結対象 (signal×return) ではないので更新自体は peeking にならない。
- **既知 debit (verdict に併記する材料、値ではなく欠測)**: Render Disk 満杯 2026-08-23→08-26 (71.3h、market-time ≈54.6h ≈ 評価窓の 5.7%) と Myfxbook 認証停止 2026-09-10 (≈5.78h) — registry `e1-positioning-ingest-freshness` message。coverage gate (≥90%) の判定は判定器の quality_gates が機械的に出す。2026-09-22 の本番 blackout の coverage 影響は未計算 ([[path-to-win-reassessment-2026-09-22]] §9)。

## §3 凍結 export (cutoff 到達後、1 回だけ)

```bash
# (a) フル期間 parquet を cutoff まで差分更新 (価格のみ、E1 値には触れない)
python3 tools/bt_data_cache.py refresh 15m
# (b) 凍結 (snapshots 13 instrument outlook + health_log、M15 スライス込み)
python3 -B tools/e1_positioning_frozen_export.py --look 1 --slice-ohlcv
# (c) 直後に roundtrip 突合 (§2.5-5(b))
python3 -B tools/e1_positioning_frozen_export.py --verify knowledge-base/raw/bt-results/e1-first-look-freeze-2026-10-08.sha256
```

成果物 (tool `default_paths`):

| パス | 中身 | git |
|---|---|---|
| `knowledge-base/raw/bt-results/e1-first-look-freeze-2026-10-08.sha256` | sha256sum 互換 (`<hex>  <repo 相対 path>`)。**= 凍結 marker** | commit |
| `knowledge-base/raw/bt-results/e1-first-look-freeze-2026-10-08.manifest.json` | 件数 / instrument 別 first・last snapshot_time (秒精度) / health_log 行数・id 範囲・key 数 / cutoff / api_base / frozen_at / ohlcv スライスの rows・sha256 / `force_history` | commit |
| `knowledge-base/raw/bt-results/e1-first-look-freeze-2026-10-08/e1_prereg_frozen_export_look1.json` | 判定器入力 artifact (`synthetic: false`) | サイズ次第。数十 MB なら commit せず sha256 のみ raw に残し、ファイルは隔離 worktree 内に保持 |
| `data/cache/e1_frozen_look1_2026-10-08/{PAIR}_15m.parquet` × 13 | cutoff スライス済み M15 | gitignored (`data/cache/`)。sha256 は上記 `.sha256` に同居 |

- **tool の挙動 (pin 済み)**: marker が既存なら exit 3 で拒否 (API へ問い合わせもしない)。現在時刻 < cutoff なら exit 2 で拒否 (早期凍結が marker を占有するのを防ぐ)。0 行の instrument があれば exit 2 (`--allow-missing-instruments` で記録のみ続行 — ingest 障害を先に切り分ける)。stdout は件数・秒精度時刻・sha256・パスのみ。
- **snapshots の範囲**: t0 (2026-07-16T06:33:31Z) 以降 cutoff 以下の **全行** (burn-in 前も含む — §3.1 の trailing rolling rank は burn-in 前の履歴を窓として使う。評価窓 08-13〜 の切り出しは判定器の仕事)。book_type は `outlook` のみ (§2.1、OANDA 旧行は型で除外)。
- **health_log の範囲**: value ≤ cutoff の全行。本番の `positioning_health_log` は **2026-07-17T08:40:27Z から** (dry-run 実測 id 1) — それ以前の verified 証跡は artifact の行 snapshot_time を判定器が union する (§2.2、`load_artifact` docstring)。
- **再実行が本当に必要なとき** (例: export 中の 5xx で不完全): `--force` を付ける。manifest `force_history` に前回 sha256 と時刻が残る (fail-loud)。**理由を verdict §8 に併記する**。値を見た後の再 export は §6-2 違反。

## §4 品質 gate spot check (§2.5-5、結果は raw/ へ)

| 項目 | やり方 | 注意 |
|---|---|---|
| (a) content-hash 再計算 | 無作為 20 行の `buckets` を `modules.positioning_ingest.outlook_content_key` で再計算し、同 instrument の**隣接行と相異なる**こと (dedup 契約) を確認 | ⚠️ 本番 schema に hash 列は無い (`positioning_snapshots` DDL) — 「保存済み hash と一致」は検査不能。確認できるのは決定性と隣接非重複のみ。**この検査は値を読む** — verdict 期日の判定器実行と同日に、判定器の出力と同じ raw JSON に結果だけ書く (数値の目視・記録禁止) |
| (b) roundtrip 突合 | `--verify` (§3(c)) が OK | 凍結直後と判定器実行直前の 2 回 |
| (c) Myfxbook web UI 突合 | 3 ペア × 1 時点の pct (±0.5pp) | rate limit 100 req/24h 内。**cutoff 後の時点**で行う (凍結 artifact の値と突合するのは判定器実行日) |
| (d) unit tests green | §2 の pytest | 判定器 `tests/test_e1_prereg_eval.py` + export `tests/test_e1_positioning_frozen_export.py` |

## §5 判定器実行 (2026-10-09〜10-14、実データ初適用 = ここが P-10 解除点)

```bash
python3 -B tools/e1_positioning_prereg_eval.py \
    --artifact knowledge-base/raw/bt-results/e1-first-look-freeze-2026-10-08/e1_prereg_frozen_export_look1.json \
    --ohlcv-dir data/cache/e1_frozen_look1_2026-10-08 \
    --cutoff 2026-10-08T06:33:31Z --look 1 --verdict-run \
    --out knowledge-base/raw/bt-results/e1_prereg_look1_2026-10-15.json
```

- `--verdict-run` は (i) synthetic 宣言のない artifact の実行を許可、(ii) 13 pair parquet 完備を強制、(iii) stale cap 主モード (health verified 系列) を強制する。health 系列が欠けると fail-loud → `--fallback-mode` は §2.2 fallback 宣言の適用 (2 方向バイアスを estimand 制約として verdict に併記、閑散集中で DEFERRED 接続)。
- 出力 JSON の `inputs` に artifact sha256 と parquet 別 sha256 が入る → §3 の `.sha256` と一致することを verdict に記録。
- **seed は default 固定 (20261015)**。`--n-boot` default 10,000。変更禁止。
- 判定器が `POSTPONE` を返したら §1 の 4 週スライド (look 非消費)。`DEFERRED` は user 裁定。

## §6 verdict 追記 (2026-10-15)

pre-reg §8 placeholder に、判定器出力から**転記**する (解釈を足さない): 品質 gate 判定表 (stale cap モード・NA 分布・量子化粒度) / Gate 1 pooled IC 表 (6 combo、p_MBB / p_IM、BH q=0.05) / Gate 2 EV 表 (time-exit / first-touch / stress、trade N) / combo 排他分類 C1〜C5 + フラグ / ナイフエッジ 4 点 / confirmatory 符号表 / 実測 ρ̄ と N_eff / 全体 verdict と固定分岐。併記必須: 既知 debit (§2)、artifact sha256、`force_history` (空であること)、§2.5-5 spot check 結果。

**hot file (session log / index / changelog / registry) は orchestrator 経由** — 本稿の執行 PR は pre-reg §8 追記 + raw JSON + 本稿 §9 実行ログのみ。

## §7 分岐 (pre-reg §4.4 の転記 — 本稿で新しい分岐を作らない)

| verdict | 直後の処置 | 期日 |
|---|---|---|
| **UNDERPOWERED** (C1=0 ∧ ∃C3、事前宣言 modal) | registry に `e1-prereg-second-look` 登録 (orchestrator)。**cutoff #2 = 2026-12-30T06:33:31Z、verdict 2027-01-06**。second look は `--look 2 --look2-combos <first look の C3 combo をカンマ区切り>` (BH m=\|C3\|、q=0.05)、標本 = burn-in 後〜cutoff #2 の**累積**、年末窓 2026-12-19〜2027-01-02 の新規 event は判定器が a priori 除外 (`YEAR_END_EXCL`)。凍結は `tools/e1_positioning_frozen_export.py --look 2 --slice-ohlcv` (marker は別ファイル `e1-second-look-freeze-2026-12-30.sha256`)。着地は PASS / REJECT-F / REJECT のみ、3 回目の look 禁止。併存 C4 の REJECT-F 処置 (decision memo) は second look verdict まで保留 | 12-30 / 2027-01-06 |
| **PASS** (∃C1) | 実装 pre-reg (pre-reg §0「D4 準拠」= shadow 起点の実装 pre-reg、Rule 1) を起案し **user 最終承認**。併存 C3 の second look は行わない (α 節約)。barrier / ペア選抜 / lot は実装 pre-reg 側の自由度。live N≥30 到達は 2027-05〜09 の見積り ([[path-to-win-reassessment-2026-09-22]] §3 Rank 2) — M2 分母は直ちには動かない。CONFOUNDED フラグ付き C1 は PASS-with-flag として user 裁定 + 実装 pre-reg に価格モメンタム増分検証条項 | 起案 10-22 目安 (user 期限は packet D1–D12 と合流、11-30) |
| **REJECT-F** (∃C4 のみ) | aggregate 版クローズ + 有償 bucket 級 (KB §8c オプション C) の decision memo 起案 (契約判断は user)。他の再判定経路なし | memo 10-22 目安 |
| **REJECT** (全 C2/C5) | E1 aggregate 版クローズ。供給ラインは KB §8c 残オプションの再決裁へ。F1 kill 条件 (2027-02-05、E1/ECG/E12 全て非 PASS) の 1 本目が確定 | 記録即日 |
| **DEFERRED** | 明示フラグ + user 裁定 (勝手に解釈しない) | — |

いずれでも**データ蓄積は止めない** (pre-reg §0「REJECT でもデータ収集の停止は別決裁」、4 原則 #3)。

## §8 UNDERPOWERED のとき 10-18 scan#6 で (a-1) probe を R1 起案するか — 一行定義

> **起案する ⇔ [E1 first look verdict ∈ {UNDERPOWERED, REJECT, REJECT-F}] ∧ [U1「継続」が有効 (U1=(b) 2026-09-17 決裁済み)] ∧ [対象は CME DataMine FX options 歴史の一回性 probe (数百 $ 上限) のみ — 月額サブスク型 ($2k 級) は U2 が ¥1M+ に解決していない限り自動 NO] ∧ [probe 購買は新 family の pre-reg 起案 (新敵対的検証必須) とセットでのみ]。PASS なら起案しない (供給圧は一時緩和、round4 凍結の再上程条件は片側充足のまま)。**

出所: [[supply-space-feasibility-2026-09-17]] §1.2 (a-1) 行 + §1.3。R1 起案は「購買 → データ QA → family 起案」の順で、単体購買は「読み手のいない write」の再生産として禁止。本稿は起案の可否条件を固定するだけで、起案の中身・採否は 10-18 scan#6 と user 決裁。

## §9 実行ログ (執行時に追記)

| 日時 (UTC) | 手順 | 結果 (件数・sha256・exit のみ。値は書かない) |
|---|---|---|
| 2026-09-22 | §2-3 dry-run health_log limit=5 | exit 0、`id 1..5`、first row 2026-07-17T08:40:27Z、keys = verified:{EUR_JPY,EUR_USD,GBP_JPY,GBP_USD,USD_JPY}:outlook、書込みなし |
| | | |

## 引用禁止 / 禁止事項 (本稿固有)

- 本稿・manifest・sha256 記録に skew / ratio / avg 価格 / IC / EV / PnL を書かない。「coverage 予測 94.3%」等の registry 既往値は**予測**であり実測は判定器 quality_gates のみ。
- 「tool が無いから verdict 無効」型の引用禁止 (§0)。「export を 2 回実行した」は §6-2 違反候補として lessons 化。
- second look で定義変更 / combo 拡大 / 3 回目 look をしない (pre-reg §6-3)。
