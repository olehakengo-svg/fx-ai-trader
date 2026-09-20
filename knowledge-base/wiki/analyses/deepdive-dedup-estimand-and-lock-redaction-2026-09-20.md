# weekly deepdive の 2 欠陥 — dedup 除外率の estimand 誤り と pre-reg LOCK セルの毎週再計算

**日付**: 2026-09-20 / **rule**: R3 (構造バグ + estimand 訂正、365d BT 不要)
**きっかけ**: 2026-09-20 weekly deepdive 実行結果 (`knowledge-base/raw/cell_deepdive/2026-09-20/_summary.md`)
**データ**: Render PROD `/api/demo/trades?limit=100000` スナップショット (18,057 行、2026-09-20T15:51Z 取得)。
ローカル `demo_trades.db` は STALE のため不使用。
**成果物**: `tools/cell_deepdive_audit.py` (新規、in-repo 化) / `tests/test_cell_deepdive_lock_redaction.py` (45 pins)

---

## 0. 要旨

weekly deepdive は 10 週連続 (2026-07-02 〜 2026-09-20) で **repo に存在しないツール**
(`tools/cell_deepdive_audit.py`) を ad-hoc スクリプトとして毎週打ち直して実行されていた。
テストが無いまま 2 つの欠陥が生き延びていた:

| # | 欠陥 | 性質 | 危険の向き |
|---|---|---|---|
| A | pre-reg LOCK 下のセルの outcome 統計 (WR/EV/PF/Wilson/p) を毎週再計算・公表 | **P-10 違反** (中間再計算禁止) | 偽陽性 — optional stopping で type-I error が膨らむ |
| B | `dedup_violation` 除外率を「N 枯渇の真因」と提示 | **estimand の category error** | 誤った処方 (「dedup を直す」) へ誘導 |

いずれも「レポートの文言」ではなく**ハーネスの構造**の問題なので、修正は
ツールの in-repo 化 + 機械的 pin で行った。

---

## 1. 欠陥 B — dedup 除外率は N 蓄積速度を測っていない

### 1.1 2026-09-20 run の主張

> 🔴 **N 枯渇の真因は発火数でなく dedup 除外率** …
> `mqe_gbpusd_fix` は raw 88 本発火していながら 93% が dedup_violation で消え clean N=6。
> 「発火していないから N が貯まらない」のではなく「**発火が擬似反復なので統計に使えない**」構図
> … **dedup 除外率が高い 2 戦略は、shadow をいくら回しても有効 N が線形に貯まらない**

### 1.2 機構 (`modules/demo_db.py`)

フラグ付けは write-time (L1114-1145) と boot backfill (L701-766) の 2 経路だが、
**どちらも「直前の *採用された* 行 (`dedup_violation=0`) から TF 窓以内の行だけを flag」**
する (`advance last kept row only on non-dup`)。したがって:

- 各窓の **先頭 1 本は必ず残る**
- flag されるのは「既に記録済みイベントの重複コピー」のみ

→ **dedup 除外は独立観測を 1 件も取り除かない。** unique N の蓄積速度は除外率と無関係。
`dedup_excluded / raw` を分母 raw で提示すると「効率が悪い」ように見えるだけで、
これは **N 枯渇の指標ではない**。

### 1.3 実測による確認 (PROD、全対象戦略 tf=15m → 窓 900s)

**flag された行が、直前の採用行からどれだけ離れているか** (2026-06-09 以降 = TF-aware backfill 修正後):

| strategy | n_flag | p50 | p90 | > 0.5×窓 |
|---|---:|---:|---:|---:|
| sr_anti_hunt_bounce | 109 | 20 s | 50 s | 2 |
| vdr_jpy | 13 | 25 s | 35 s | 0 |
| rsk_gbpjpy_reversion | 16 | 14 s | 40 s | 0 |

中央値 14〜25 秒 = **同一 15m バー内の tick 再発火**。独立イベントではない。

**採用された行どうしの間隔** (over-flagging = 本物の抑圧 が起きていないかの反証側):

| strategy | n_gaps | p10 | p50 | 窓 (900s) 未満の件数 |
|---|---:|---:|---:|---:|
| sr_anti_hunt_bounce | 179 | 1,800 s | 37,795 s | **0** |
| vdr_jpy | 16 | 136,871 s | 669,999 s | **0** |
| vsg_jpy_reversal | 34 | 51,623 s | 431,984 s | **0** |
| rsk_gbpjpy_reversion | 33 | 914 s | 18,850 s | **0** |

採用行の最小間隔 (rsk の p10 = 914 s) すら窓 900 s を下回らない。
tf は全戦略 15m で窓と整合 (over-flagging を起こす tf 誤指定は無い)。
⇒ **ゲートは過剰抑制もしていない。**

### 1.4 93.2% の正体 — 凍結した過去のアーティファクト

除外を **dedup ゲート導入 (commit `6a45bb2`, 2026-04-30T02:42Z)** の前後で割ると:

| strategy | raw | 全体 | pre-fix raw | pre-fix 率 | post-fix raw | **post-fix 率** |
|---|---:|---:|---:|---:|---:|---:|
| mqe_gbpusd_fix | 88 | 93.2% | 86 | 95.3% | **2** | **0.0%** |
| rsk_gbpjpy_reversion | 152 | 68.4% | 0 | — | 152 | 68.4% |
| sr_anti_hunt_bounce | 462 | 42.2% | 24 | 87.5% | 438 | 39.7% |
| vsg_jpy_reversal | 84 | 33.3% | 12 | 75.0% | 72 | 26.4% |
| vdr_jpy | 44 | 36.4% | 0 | — | 44 | 36.4% |

**`mqe_gbpusd_fix` の 88 行中 86 行が 2026-04 の pre-fix バースト。** post-fix は raw 2 行・除外 0。
月次では `2026-04:87 / 2026-08:1` — **2026-05 以降の 4.7 ヶ月で発火はわずか 2 本**。

⇒ 2026-09-20 run の断定は**逆**である。mqe の clean N=6 の原因は
**発火の枯渇そのもの** (unique 90d = 1 本 = 0.08 本/週、最終 unique 発火 2026-08-28T15:31)。
引用されていた「outcome は WIN 42 / LOSS 46 と拮抗」も、その 88 行の大半が
4 月のバースト由来なので現状の記述として使えない。

`rsk_gbpjpy_reversion` の 68.4% は post-fix でも高いが、月次では
`2026-04:76/69 → 05:23/18 → 06:7/3 → 07:20/6 → 08:17/6 → 09:9/2` と **90% → 22% へ減衰済み**。
いずれにせよ §1.2-1.3 より unique N の蓄積速度には効かない。

### 1.5 正しい指標 = unique 蓄積速度

| strategy | unique 365d | 90d | 30d | **unique/週 (90d)** | 最終 unique 発火 |
|---|---:|---:|---:|---:|---|
| sr_anti_hunt_bounce | 267 | 170 | 27 | **13.22** | 2026-09-18T00:00 |
| rsk_gbpjpy_reversion | 48 | 33 | 10 | 2.57 | 2026-09-15T21:31 |
| vsg_jpy_reversal | 56 | 32 | 13 | 2.49 | 2026-09-18T03:07 |
| vdr_jpy | 28 | 19 | 3 | 1.48 | 2026-09-18T14:52 |
| mqe_gbpusd_fix | 6 | 1 | 1 | **0.08** | 2026-08-28T15:31 |
| sr_liquidity_grab | 2 | 2 | 0 | 0.16 | 2026-08-07T13:19 |
| cpd_divergence | 0 | 0 | 0 | 0.00 | — |

`tools/cell_deepdive_audit.py` はこの表 (`unique_accrual`) と era 分割
(`dedup_era_breakdown`) を出力し、除外率単独の提示をやめる。

### 1.6 この欠陥の位置づけ

ロードマップ v2.3 のボトルネック定義 (「摩擦調整 EV が正のセルの不在」) は**不変**。
本件は「N が貯まらない理由」の帰属を訂正しただけで、エッジ供給の結論は動かさない。
ただし **M3 (clean live N≥30 セル 3 本) のスループット議論に誤った修理対象を持ち込む**
ところだった — 直すべきは dedup ではなく発火頻度 (= シグナル供給) である。

---

## 2. 欠陥 A — pre-reg LOCK セルの outcome を毎週再計算していた

### 2.1 事実

2026-09-20 run が公表していたセル:

| 公表箇所 | セル | LOCK |
|---|---|---|
| PAIR_PROMOTED Candidates (4 週連続) | `sr_anti_hunt_bounce × EUR_JPY × Tokyo × BUY` N=33 | `sr-anti-hunt-eurjpy-buy-forward-confirm` の sub-cell |
| v2 eligible 表 | `sr_anti_hunt_bounce × EUR_JPY × BUY` N=74 | **同 LOCK の本体セル** |
| v2 eligible 表 | `sr_anti_hunt_bounce × USD_JPY × BUY` N=28 | `ws3-t11-anti-hunt-usdjpy-recheck` |

pre-reg ([[sr-anti-hunt-eurjpy-r1-verdict-2026-08-05]] §Forward 確認 pre-reg) は
**「fresh N≥40 到達時に 1 回限り」判定 / 「それまで本セル×outcome の中間再計算禁止 (P-10 型)」**
と明記している。weekly run はその outcome 統計を毎週計算し markdown に印刷していた。

run 自身がこの衝突を散文で認識していた —
> 中間再計算の禁止 (P-10 型) … **weekly deepdive が毎週再計算しており、ツール自体が LOCK と構造的に衝突**

にもかかわらず数値は印刷され続けた。**「知っているのに構造が止めない」= 検知器ではなく作文**。

### 2.2 なぜ危険か

LOCK の目的は optional stopping の封じ込めである。毎週 outcome を見られる状態は、
`N≥40` の到達を待つ間に「都合のよい週に判定する」余地を作る。
判定は 1 回限りという前提で α が設計されているので、覗きが常態化している時点で
**その α は成立しない**。危険の向きは偽陽性 (昇格すべきでないセルを昇格させる)。

### 2.2b 露出は今週分ではない — 少なくとも 5 週が repo history に残っている

`knowledge-base/raw/cell_deepdive/*/\_summary.md` を grep すると、LOCK セルの統計は
**2026-08-23 / 08-30 / 09-06 / 09-13 / 09-20 の 5 回**の weekly レポートに印刷され、
すべて既に main にコミット済みである (LOCK 発効は 2026-08-05)。

⇒ **「1 回限り判定」という LOCK の前提は、本 PR 以前にすでに実質的に崩れていた。**
本 PR の redaction は**追加の露出を止める**が、既に起きた露出は取り消せない。

これは計数基準 (§4) とは別の、より上位の問いを生む:
**5 週以上 outcome が可視だった状態で到達する N=40 の判定に、凍結時の α はまだ使えるのか。**
選択肢は概ね (a) そのまま判定し「optional stopping 露出あり」を verdict に明記して
結論の強度を下げる (b) LOCK を失効扱いにし、redaction 済みハーネス下で fresh な
OOS 窓を切り直す (= N 蓄積やり直し、時間コスト大) (c) 判定は行うが昇格の必要条件を
引き上げる。**いずれも R1 = user 決裁** (registry `sr-anti-hunt-eurjpy-lock-validity-disposition`)。

⚠️ **引用規律**: 本セルの今後の verdict を引用するときは、この露出を必ず併記すること。
露出を伏せた「Bonferroni 通過」型の引用は禁止。

### 2.3 修正

`tools/cell_deepdive_audit.py` に **redaction 層**を実装:

- `prereg-trigger-registry.json` の `active` かつ `*_count_decision` 型エントリから
  LOCK セル `(entry_type, instrument, direction)` を読む (`instrument`/`direction` は
  `None` = ワイルドカード)
- 一致するセル**およびその refinement (sub-cell)** の
  `wr / wilson_lo / ev_net / pf / p_raw / p_bonf / kelly / wf_stable / promoted / wins`
  を出力から除去し、**`n` のみ残す** (トリガが数えるのは N なので運用は止まらない)
- redacted セルは `candidates` に入りえない — 4 週連続で「LOCK 違反 sub-cell だから昇格しない」
  と手書きで弁明していた作業が構造的に不要になる
- `*_count_info` 型 (頻度監視、outcome ゲート無し) は対象外

実測: 2026-09-20 スナップショットに対し **3 セルを redact** (上表と一致)、
`candidates` は 1 → **0** になった。meta 計数 (raw 834 / dedup 427 / non-WL 22 / clean 385 /
m_v2 7 / m_v3 1) は ad-hoc 版と完全一致 = 移植は忠実。

### 2.3b レビュー指摘による硬化 (Codex P1×2 / P2×1、PR #273)

初版の redaction は **「計算してから出力で隠す」** 実装だった。connector レビューが
これを含む 3 件を指摘し、いずれも妥当だったので修正した。

| # | 指摘 | なぜ妥当か | 修正 |
|---|---|---|---|
| P1 | **LOCK 判定を統計計算の前に行え** | pre-reg が禁じているのは「**再計算**」であって印字ではない。dict を作ってから削るのでは、禁止された計算自体は走っている | `eval_cells` で LOCK を**先に**判定し、該当セルは `cell_stats` / `wf_stable` / Bonferroni を**一切呼ばず** `n` だけの record を作る |
| P1 | **registry 読み込み失敗時は fail-closed に** | 旧実装は `except` で `[]` を返しており、registry が欠損/破損すると**全 LOCK が黙って無効化**され、まさに抑止対象の統計を公表していた | `LockRegistryUnavailable` を送出して監査を中断 |
| P2 | **365d 窓を実際に適用せよ** | 入力は戦略と XAU でしか絞られておらず、`run_date` との比較が無いまま「365d 監査」を名乗っていた。PROD が 1 年を超えたら/過去日付で再実行したら、stale 行や run 後の行が N・多重度・候補を変えるのにレポートは 365d と主張し続ける | `[run_date−365d, run_date+1d)` で `entry_time` を実際に filter し、適用窓を `window`/`filters` に出力 |

🔵 **P1 修正の副産物として、自分では見つけていなかった leak が 1 件出た** —
「LOCK セルの統計を一切計算しない」を spy で pin したところ、**戦略レベル集計**
(`target_strategies`) が落ちた。初版は「strict な super-set は別 estimand だから対象外」
と文書化していたが、**それが成り立つのは他ペアに行が存在するときだけ**で、
ある戦略の行が全て LOCK セルに属する場合その「集計」は **LOCK セルそのもの**になる。
**leak 条件がデータ依存** = 静かに壊れる型。⇒ 集計前に LOCK 行を除外し
(`locked_rows_excluded` を併記)、集計を**無条件に**別 estimand にした。

実測への影響: meta 計数は不変 (現データは全て 365d 窓内のため filter は no-op) で
**移植の忠実性の主張は維持**。`sr_anti_hunt_bounce` の戦略集計は
LOCK 行 112 を除外して clean_N 247 → **135** になった。

### 2.3c レビュー第2波 (Codex P2×2) — 「N の estimand」が本 PR 自身にもあった

| 指摘 | なぜ妥当か | 修正 |
|---|---|---|
| **LOCK の N は LOCK 自身の母集団で数えよ** | count-only record が `n=74` (セルの 365d Live+Shadow 行数) を **判定閾値 N=40 の隣**に出していた。LOCK の母集団は「`since`=2026-08-05 以降の CLOSED shadow 行、`dedup_violation=0`」で実数は **36**。⇒ **既に gate を通過したかのように読める** — 本 PR が糾弾している「隣に置いた estimand と一致しない計数」そのものを自分でやっていた | registry の母集団述語 (`since` / `closed_only` / `dedup_violation` / `mode` / shadow-vs-live) を `load_locked_cells` に保持し `lock_population_count` で適用。出力は **`n_lock_population`** (gate 関連) / **`n_decide`** (閾値) / **`n_rows_in_window`** (別物と明示) に分離し、曖昧な `n` は廃止 |
| **365d と言うなら 365 日にせよ** | 第1波の修正 `[run_date−365d, run_date+1d)` は両端を含んで **366 日**だった | `window_days − 1` を引き、inclusive 窓が厳密に `window_days` 日になるよう修正 (pin で日数を算術検査) |

✅ **独立クロスバリデーション**: `lock_population_count` の出力は
`tools/prereg_trigger_watch.py` の表示と一致した — EUR_JPY LOCK **36/40**、
ws3-t11 **22/30**。別実装の読み手が同じ数を出すことで実装の正しさを確認。

🔴 **本 PR だけで「隣に置いた閾値と estimand が合わない計数」が 3 例出た**
(35 vs 36 の読み手不一致 §4 / dedup 除外率の分母 §1 / 本項の `n=74` vs 36)。
**同じ病が、それを指摘している当の PR にも出る**。

### 2.3d レビュー第3波 (Codex P1 + P2) — fail-open の「対称な反対側」

| 指摘 | なぜ妥当か | 修正 |
|---|---|---|
| **構造的に不正な registry も拒否せよ** | 第1波の fail-closed は **読めない場合**しか塞いでいなかった。`{"triggers": "oops"}` / `[42]` は **JSON として妥当**なので通過し、要素が dict でないため全て skip → `[]` → **全 LOCK が消える**。読めない場合と同じ fail-open クラスの別形状 | root / `triggers` が list であること、要素が全て object であることを検証し、違反は `LockRegistryUnavailable` |
| **prefix LOCK を尊重せよ** | registry には `match: "prefix"` (multi-variant family 用) が実在し `tools/prereg_trigger_watch.py` が `count_matching(prefix=...)` で使っている。**完全一致だけでは `kalman_d7_variant_a` 等が LOCK を素通りし、凍結 family の outcome を公表しうる** | `match` を保持し `_entry_type_matches` で前方一致を実装。`lock_for_cell` と `lock_population_count` の**両方**に適用 (片側だけでは計数が壊れる) |

🔴 **これは [[feedback_check_the_symmetric_side_2026_09_19]] の 3 度目の実例**。
第1波で「registry が読めない」を塞いだとき、**「読めるが壊れている」**を塞いでいなかった。
*片側だけの fail-closed は「再発できない」という主張を偽にする* — 自分で書いた教訓を、
その教訓を引用している PR の中で踏んだ。

✅ **prefix 指摘の検証**: 指摘を額面で受けず registry を実査した
(`match` を持つ 5 エントリ、値は全て `"prefix"`、うち active な `*_count_decision` は
`t9-kalman-d7-live-n10-ev-check` / `ps-carveout-regate-post-172` /
`project-falsification-f2-wg-live-conversion`) — **指摘は事実**だった。

### 2.3e レビュー第4波 (Codex P1 + P2×2) — 正本 (`prereg_trigger_watch`) との契約ズレ

3 件とも **registry と正本ハーネスを実査して事実確認**した上で修正:

| 指摘 | 実査結果 | 修正 |
|---|---|---|
| **marker 定義の LOCK を落とすな** | `hourblock-class-exempt-r2-rollback` は **active / `live_count_decision` / `entry_type` が空 / `reasons_marker: "[HOURBLOCK_CLASS_EXEMPT]"`** で実在し、`prereg_trigger_watch` は `fetch_live_count(reasons_marker=...)` で対応済み。本ツールは `entry_type` が空だと `continue` していたので **active な decision LOCK を丸ごと無視**していた | marker LOCK は「セル」でなく**行集合**を定義するので、`clean` を組む**前**に該当行を除去 (`marker_locked_rows_excluded` を出力)。`lock_population_count` も marker で数える |
| **live LOCK の計数から重複行を除け** | `count_live_matching` は `dedup_violation == 1` を**無条件で**除外する。本ツールは registry が明示した時だけ除外していたため、重複 live 行が `n_lock_population` を正本より大きくし **n_decide 到達に見せうる** | `kind == "live"` は無条件除外。shadow 側は正本どおり `count_basis == "unique"` **または** `dedup_violation == 0` の時に除外 |
| **`active` 省略時は active 扱い** | 正本 `load_registry` は `t.get("active", True)`。本ツールは `e.get("active")` で **省略 = 非 active** と解釈しており fail-open (現 registry に省略エントリは 0 件なので実害は未発生、潜在) | `e.get("active", True)` に合わせた |

✅ **3 度目の独立クロスバリデーション**: marker LOCK の `n_lock_population` = **2**
が `prereg_trigger_watch` の `hourblock-class-exempt-r2-rollback: live N=2/10` と一致。
EUR_JPY **36/40** / ws3-t11 **22/30** と合わせ、3 本とも正本と一致した。

🔴 **本 PR の欠陥の主系統は「正本との契約ズレ」だった** — registry のフィールド
(`match` / `reasons_marker` / `count_basis` / `active` 既定 / live の暗黙 dedup) を
**正本ハーネスがどう解釈しているか**を読まずに自前解釈したのが原因。
**同じ registry を読む 2 つ目の実装を書くときは、フィールド一覧ではなく
正本の読み取りコードを仕様として読む。**

### 2.3f レビュー第5波 (Codex P1 + P2×2) — 「検査不能を異常なしに畳まない」

| 指摘 | 実査結果 | 修正 |
|---|---|---|
| **`triggers` の欠落/空を拒否せよ** | 正本 `load_registry_raw` は **root 非 dict / `triggers` キー欠落 (綴り違い候補を提示) / 非 list / 空** の 4 つを全て `RuntimeError` にする。本ツールは `.get("triggers", [])` のままで、`{"trigers": []}` も `{"triggers": []}` も**空台帳に畳んで全 LOCK を消して**いた | 正本の契約を 1:1 で移植 (綴り違いヒント込み)。🔴 **第3波で自分が書いた pin「空 registry は正当」は誤りだったので撤回** — 正本契約に反し、かつ fail-open そのものを pin していた |
| **marker 除外にも LOCK の述語を適用せよ** | marker 除外が reasons 文字列一致のみで、`kind`/`since`/instrument/direction を見ていなかった。hourblock LOCK は **live 限定・2026-09-02 以降**だが marker は後段ゲートが shadow 化する前に付くので、**LOCK 外の shadow 行や `since` 前の行まで監査から削除**していた | `row_in_lock_population()` を**単一の真実**として抽出し、LOCK の N と marker 除外の**両方**がこれを使う |
| **`trades` を欠く API 応答を拒否せよ** | `payload.get("trades", [])` がエラーオブジェクトを**空データセット**に畳み、`--no-write` なしだと「0 行・候補なし」の**もっともらしい週次レポートで上書き**していた | `trades` キーと list 性を検証し `SystemExit` (実測: エラーオブジェクトで exit 1) |

🔴 **over-exclusion は leak の鏡像**。marker 除外の穴は P-10 的には「安全側」だが、
**実在する観測を黙ってレポートから消す**という別の嘘を作っていた。
片側 (漏れ) だけを見ていると、もう片側 (過剰削除) を見落とす。

🔴 **fail-open クラスはこれで 3 度目** (読めない → 構造不正 → キー欠落/空)。
**「検査不能を『異常なし』に畳まない」は 1 つの不変条件であって、
入力形状ごとに個別対応する類のものではない** — 正本はこれを 1 箇所で表明していた。

### 2.3g レビュー第6波 (Codex P1×2) — 計数自体が outcome の関数だった

| 指摘 | 実態 | 修正 |
|---|---|---|
| **LOCK 行は outcome を読む前に分岐せよ** | LOCK セルの行も先に **WIN/LOSS フィルタ**を通っていたため、**出力される計数そのものが `outcome` の関数**だった (BREAKEVEN 行 1 本で計数もセルの出現可否も変わる)。**これは本分析 §4 が指摘している 35 vs 36 そのもの — それを直すためのツールの中で再現していた** | raw 行の段階で LOCK セルを分岐し、`outcome`/`pnl_pips` を**一度も読まず**に count-only record を作る。計数は outcome 非依存 (`n_unique_rows_in_window` = dedup 除外 ∧ 窓内) に改名 |
| **selector 無しの active decision を拒否せよ** | `{"type":"shadow_count_decision","entry_typo":"foo"}` は構造検査を通り**黙って捨てられる**。本コマンドは正本 linter を呼ばないので、綴り違い/削除された selector が **LOCK を消したまま監査は当該母集団を公表し続ける** | active な `*_count_decision` が `entry_type` も `reasons_marker` も持たなければ `LockRegistryUnavailable` |

🔴 **実測で裏が取れた**: 修正後 `sr_anti_hunt_bounce × EUR_JPY × BUY` の計数は
**74 → 75** に変わった。**増えた 1 本がまさに BREAKEVEN 行**で、§4 の「35 vs 36」の
差分と同一の行である。`× USD_JPY × BUY` も 28 → 35 (非 WIN/LOSS 7 本)。

⚠️ **「移植は忠実」の主張をここで更新する**: 第1波〜第5波までは meta 計数が ad-hoc 版と
完全一致していたが、本修正で **`clean_N` 385 → 273** (LOCK 行 215 を routing で除外)、
LOCK セルの計数も上記のとおり変わる。**これは意図した訂正であり、
「ad-hoc 版と同一」はもはや成立しない** — 同一なのは
**非 LOCK セルの統計** (`sr_anti_hunt_bounce` 集計 clean_N 135 / WR 0.519 /
EV −4.27 / PF 0.37 は不変) と `m_v2` = 7 / `m_v3` = 1 / `candidates` = 0。

多重度について: LOCK セルは候補になりえないので `m` から外す選択もありうるが、
**外すと `m` が縮んで他セルの `p_bonf` が通りやすくなる** (危険な向き)。
多重度補正では保守側を取り、**LOCK セルも `m` に数え続ける**。

### 2.3h レビュー第7波 (Codex P1×1) — meta 診断値にも outcome が漏れていた

第6波で cell の計数は outcome 非依存にしたが、**`meta.non_winloss_excluded` は
依然 `target_all` (LOCK 行込み) で `outcome` を読んで**いた。LOCK セルだけの監査で
1 行を WIN→BREAKEVEN にすると、count-only record は不変なのに**メタデータが 0→1 に動く**
= 凍結母集団の outcome 由来の性質を公表していた。
⇒ `open_raw` (LOCK/marker 行を除いた後) から計算するよう変更。
`dedup_violation_excluded` は outcome 非依存なので全行対象のまま。

実測: `non_winloss_excluded` **22 → 13** (LOCK 行由来の 9 が除かれた)。

🔑 **この波で不変条件を「性質」として pin し直した** — 個別フィールドを列挙するのではなく
**「LOCK 行の outcome を反転させてもレポート JSON 全体が 1 バイトも変わらない」**を
直接 assert する。本 PR が主張している性質そのもので、フィールドが増えても自動で守られる
(lesson: *pin は構文でなく性質で書く* [[lesson_validity_check_pins_proxy_2026_09_02]])。

### 2.3i レビュー第8波 (Codex P1 + P2) — 多重度族の分割 (統計的欠陥)

| 指摘 | 実態 | 修正 |
|---|---|---|
| **v2 と v3 を 1 つの多重度族で補正せよ** | `m_v2` と `m_v3` を別々に当てて結果を `candidates` に merge していたため、**単独の v3 sub-cell が多重度ペナルティをほぼ受けずに通る** (`m_v3=1` ⇒ `p_bonf = p_raw`)。レビューの数値例: N=20/15勝 は Wilson_lo 0.531・`p_raw≈0.025` で **promote されるが、v2 7 セルを含む族なら `p_bonf≈0.203` で FAIL**。🔴 **これが Tokyo sub-cell が 4 週連続「候補」に出ていた機構**であり、**2026-09-20 レポートは本文で「探索族を v2∪v3 (m=8) で取れば p_bonf=0.0720 → FAIL」と正しく書きながら、ハーネスは分割のままだった** | `m_family = m_v2 + m_v3` を単一の族として両グリッドに適用 (実測 **m_family = 8** = レポート本文と一致)。`m_family_v2_union_v3` を meta に出力 |
| **accrual の窓を名乗った長さに揃えよ** | `x >= as_of − d 日` は両端を含んで **d+1 日**を数えていた (d=90 で 2026-06-22〜09-20 = 91 日)。**signal 枯渇の診断に使う accrual rate を過大に出す** | `d − 1` を引いて inclusive で厳密に d 日に (`window_bounds` と同じ規約) |

**実測の変化** (本 doc §1.5 の表・changelog・週次レポートの引用値も同コミットで訂正):
`sr_anti_hunt_bounce` 90d 173→**170** / 13.46→**13.22 本/週**、
`vdr_jpy` 90d 20→**19** / 1.56→**1.48**。
**`mqe_gbpusd_fix` の 0.08 本/週 は不変** — §1.4 の結論 (真因は発火枯渇) に影響なし。
訂正は行アンカー完全一致 + 出現回数の事前表明 + `--word-diff` 全数照合で実施
([[feedback_scoped_edits_no_global_replace_2026_09_18]])。

🔴 **本 PR で最も statistically 重い指摘**。他の指摘が「漏れ/fail-open」だったのに対し、
これは **promote 判定そのものを甘くする**欠陥で、危険の向きは偽陽性。
しかも **レポート本文は正しい族を書いていた** — 「文章では正しく、コードでは違う」の
3 例目 (§2.1 の LOCK 衝突認識、§2.3e の正本契約、本項)。

### 2.3j レビュー第9波 (Codex P2) — 正本の方が pre-reg から外れていた例

指摘: 「shadow LOCK の `n_lock_population` が canonical watcher と食い違いうる」。
**実査したところ指摘は事実だが、ズレているのは本ツールではなく正本の方だった**:

- pre-reg 原文 ([[sr-anti-hunt-eurjpy-r1-verdict-2026-08-05]]) の母集団 =
  「`dedup_violation=0` の **shadow rows のみ**」
- MEMORY `feedback_live_vs_shadow_strict_separation` = live は `oanda_trade_id != ''`
- しかし正本 `count_matching` は instrument/direction/closed/dedup は適用するが
  **`oanda_trade_id` で絞らない** ⇒ live fill 済みの行も「shadow 件数」に入る

現データでは**両者とも 36 で一致**しており潜在 (本セルにまだ live fill が無い)。
だが本セルが live fill を取り始めた瞬間に顕在化し、
**watcher が先に発火したのに監査は未達と表示する** (またはその逆) 事故になる。

**どちらも採らなかった。** LOCK トリガの計数規則を一方的に変えることは、
本 PR が §4 で「user 決裁」に回したのと同じ種類の行為だからである。
代わりに **両方を出力して差異を可視化**する:
`n_lock_population` (pre-reg 忠実) / `n_lock_population_watcher` (watcher 互換) /
`watcher_divergence` フラグ + `watcher_divergent_locks` 一覧。
決裁点 `sr-anti-hunt-eurjpy-count-basis-declaration` に**第 2 の論点として追記**し、
BREAKEVEN の扱いと **1 回で決める**よう明記した (別々に決めると 2 つの読み手が
別の理由でずれ続ける)。

🔑 **レビュー指摘を「直す」ことと「正しい側に寄せる」ことは別。**
第4波で得た「正本の読み取りコードを仕様として読め」は、
**正本が常に正しいという意味ではない** — 正本と凍結文書が食い違ったら、
勝手にどちらかへ寄せず**両方出して決裁に上げる**。

### 2.3k レビュー第10波 (Codex P2×2) — 厳格 shadow の定義と as-of 上界

| 指摘 | 実査結果 | 修正 |
|---|---|---|
| **厳格 shadow は `is_shadow` も要る** | `rnb-support-bounce-shadow-forward` の LOCK 文が**逐語で**「**厳格 shadow = is_shadow=1 ∧ oanda_trade_id 空**」と定義している。本ツールは OANDA id しか見ておらず、**flag-drift 行 (id 空 ∧ is_shadow=0) を shadow として数えて**いた。**PROD に該当行が実際に 47 本存在**するので潜在的でなく現実の危険 | faithful 側は `is_shadow` も要求。`watcher_compat` は正本の広い挙動を意図的に維持 (§2.3j の二本立てと整合) |
| **LOCK の計数に監査の as-of 上界を** | `lock_population_count` が payload 全体を数えており、**過去日付の `--run-date` を現在のスナップショットに対して再実行すると run 後の行まで数え**、historical report が「もう n_decide に達していた」と示唆しうる | `as_of_exclusive` を追加し監査の排他的上界を適用。`since` は LOCK 自身の下界として独立に維持 |

実測: PROD の LOCK 計数は **36/36・22/22・marker 2 のまま不変** (現時点で
LOCK セルに flag-drift 行も run 後の行も無いため) — 修正は**将来の事故を塞ぐもの**で、
今回の数値解釈には影響しない。

🔑 **「47 本実在した」が効いた**。指摘を仮説として受け取らず PROD を数えたことで、
これが理論上の穴ではなく**いつ踏んでもおかしくない穴**だと確定できた。

### 2.3l レビュー第11波 (Codex P2×2) — 過剰 redaction と過少報告

| 指摘 | 実態 | 修正 |
|---|---|---|
| **redaction を本物の outcome LOCK に限定せよ** | 全 `*_count_decision` を redact していたが、そのうち **3 件は件数監視のみで凍結 outcome look を持たない** (`rnb-shadow-lane-health-checkpoint-1/2` は「count のみで outcome は見ない = P-10 非抵触」と自称、`project-falsification-f2-wg-live-conversion` は N≥1 の転換監視)。⇒ **正当な監査結果と昇格候補まで握り潰す** = leak の鏡像 | registry に **`outcome_lock` フラグ**を新設し該当 3 件に `false` を明示。**既定は `True` (redact)** — 過少 redaction は静かに漏れ、過剰 redaction は少なくとも目に見えるため保守側に倒す。`prereg_trigger_watch` の key allowlist にも登録 (未登録キーは lint が reject-by-default で弾く) |
| **min_n 未満の LOCK セルも報告せよ** | 在庫が `min_n=20` 以上の群に限られており、**自分の閾値が min_n 未満の LOCK** (kalman `n_decide=10`) は 10 行揃っても **`redacted_cell_count=0` / `n_lock_population` 無し** = 宣言した look に到達しているのに何も表示されない | 在庫は**全ての非空 LOCK 群**から作る。`min_n` は**多重度の資格**にのみ使う (実測: redacted 3 → **15** セル) |

🔴 **文面から推測する実装は実際に誤分類した** — 「count のみ」「P-10 非抵触」で
grep したところ **`rnb-support-bounce-shadow-forward` (本物の outcome LOCK) を
件数のみと誤判定**した (その文言は同エントリが*併設する checkpoint* の説明だった)。
⇒ **分類は文面推測でなく明示フラグで表明する**。

✅ registry lint が新キーを正しく弾いた (`未知のキー 'outcome_lock'`) — allowlist の
reject-by-default が設計どおり機能。allowlist へ意図を書いて登録した。

### 2.3m レビュー第12波 (Codex P2) — 新フラグに型検査が無かった

第11波で足した `outcome_lock` を `META_FIELDS` にだけ登録したため、registry lint は
`"false"` / `0` / `null` を**素通り**させていた。`load_locked_cells` の opt-out 判定は
`is False` なので、これらは**件数のみのモニタを黙って outcome lock 扱いに戻し**、
正当な監査結果と昇格候補を握り潰す。⇒ `BOOL_FIELDS` へ追加し authoring 時に落とす。

実測で 3 形状 (`"false"` / `0` / `null`) すべてが lint に弾かれることを確認、
真の bool と**キー未記載**は通る (未記載 = redact が既定 = 安全側)。

🔑 **ガードを足したら、そのガード自身の入力も検査する。** `closed_only: "false"` が
`bool()` で true になる穴は既に registry lint が塞いでいた ([[prereg_trigger_watch]]
BOOL_FIELDS の由来) のに、**同じ穴を新フラグで作り直した**。
既存の防御が「なぜその形で存在するか」を読めば、新フィールドに同じ検査が要ることは
追加時点で分かる。

### 2.3n レビュー第13波 (Codex P2) — まだ始まっていない LOCK が過去を消していた

LOCK の `since` より前で終わる窓を再実行しても、セル一致だけで routing していたため
**まだ発効していない LOCK が過去の監査結果を redact** していた。
実測: `--run-date 2026-07-01` で **14 セルが redact され全て `n_lock_population: 0`** —
2026-08-05 開始の LOCK が 7 月の統計と候補を消していた。
⇒ `since >= 窓の上界` の LOCK は routing 前に除外し、**除外した LOCK を
`locks_not_yet_started` に列挙**して省略を可視化する。

検証: 修正後 `--run-date 2026-07-01` は **redact 0 / clean_N 173** (7 LOCK すべてを
not-yet-started として列挙)、`--run-date 2026-09-20` は **redact 15 / clean_N 273 で不変**。

🔑 **over-redaction は本 PR で 3 度出た** (件数モニタ §2.3l / min_n 未満 §2.3l /
未発効 LOCK)。**leak を塞ぐガードは、塞ぎすぎる方向にも同じ数だけ穴を開ける** —
「redact する条件」を足すたびに「redact してはいけない条件」を対で確認する。

### 2.3o レビュー第14波 (Codex P2×2) — routing が母集団でなくセルで切っていた

| 指摘 | 実態 | 修正 |
|---|---|---|
| **LOCK 母集団の行だけを routing せよ** | routing が `(entry_type, instrument, direction)` だけを見ていたため、**LOCK の `kind`/`since`/`mode`/`closed_only`/dedup を満たさない同一セル行まで一緒に退避**していた。⚠️ **指摘は本 PR が公開した出力そのものを証拠にしている** — 「in-window unique **75** 行を退避して LOCK 母集団は **36**」= 39 行が LOCK の対象外なのに監査から消えていた | routing に `row_in_lock_population` を適用。母集団外の同一セル行は **unlocked complement** として評価を続け、`lock_complement_only` + `lock_complement_cells` で「セル全体ではない部分ビュー」と明示 |
| **完全なスナップショットを要求せよ** | `/api/demo/trades` は **default limit=50** (app.py)。help のとおり素朴に curl すると**もっともらしいが激しく truncate された監査**になり、`--no-write` 無しでは週次サマリを誤った N・多重度・候補で上書きする。`count` は len(trades) と同値なので自己検知できない | 50 行ちょうど (= default の署名) / `--min-rows` (既定 1000) 未満 / `count != len(trades)` を **fail-loud** に。help も `?limit=100000` 付きに訂正 |

**実測の変化**: `locked_rows_routed_out` **215 → 58**、`clean_N` **273 → 335**、
`sr_anti_hunt_bounce × EUR_JPY × BUY` の redacted 記録は **uniq 75 → 36 で
`n_lock_population` と一致** (指摘の数値がそのまま解消)。複合ビューは 3 セル。

🔑 **「LOCK が覆う範囲」と「LOCK セルの全行」は別物**。cell identity で切ると
**LOCK が一度も対象にしていない行 (live / `since` 前) まで巻き込む** —
over-redaction の 4 度目。母集団述語を 1 箇所 (`row_in_lock_population`) に
集約しておいたおかげで、routing 側に 1 行足すだけで整合した。

### 2.4 pin (同一コミット、`tests/test_cell_deepdive_lock_redaction.py`)

教訓「**検知器には『NG を返す既知の入力』を同じコミットで pin せよ**」
([[project_review_gate_vacuous_2026_09_11]]) に従い、redaction の assertion は
すべて**非 redaction の counter-pin と対**にした (全部 redact する実装・何も redact しない実装の
双方が落ちる):

0. **LOCK セルでは outcome ヘルパが 1 度も呼ばれない** (spy で `cell_stats`/`wf_stable`
   を差し替え) ∧ counter-pin: 非 LOCK セルでは呼ばれる
0b. **registry 欠損/破損 → `LockRegistryUnavailable` 送出** ∧ counter-pin: 正常 registry は読める
   ∧ `run_audit` まで伝播する
0c. **窓外 (2024 の stale / 2027 の post-run) 行は N・多重度に入らない** ∧ `run_date` 当日は入る
0c2. **LOCK の N は LOCK 母集団で数える** (`since` 前 / OPEN / live / dup 行を混ぜた
   KNOWN-NG 入力で `n_lock_population` が 12、`n_rows_in_window` はそれより大)
   ∧ 実 registry から母集団述語が読めている
0c2b. **構文は妥当だが構造が壊れた registry 5 形状で raise** ∧ counter-pin: 正常 registry と
   空 registry は通る
0c2c. **prefix LOCK が variant family を覆う** (`kalman_d7_variant_a` が redact され
   `n_lock_population` も prefix で数える) ∧ counter-pin: `exact` LOCK は variant を飲み込まない
   ∧ 実 registry の prefix フラグが保持されている
0c2d. **marker LOCK の行が outcome 計算に入らない** (marked 15 行が WR を 0.5 でなく
   0.2 に保つ) ∧ `since` は marker LOCK にも効く ∧ 実 registry から marker LOCK が読める
0c2e. **live LOCK の計数が重複行を無条件に除外** (dup 5 行を足しても 8 のまま)
0c2f. **`active` 省略 = active** ∧ counter-pin: `active: false` は無効のまま
0c2g. **`triggers` 欠落/綴り違い/空/list root で raise** ∧ 綴り違いヒントが near-miss キーを
   名指しする ∧ counter-pin: 実 registry は読める
0c2h. **marker 除外が LOCK の述語を守る** (live 限定 LOCK に対し shadow 行・`since` 前の行は
   **削除されない**、除外は 1 行のみ・セル N は 22 のまま)
0c2i. **LOCK セルの計数が outcome 非依存** (BREAKEVEN 6 本込みでも 40、outcome を全反転
   させても同値) ∧ counter-pin: 非 LOCK セルでは WIN/LOSS フィルタが残る (34)
0c2j. **selector 無しの active decision を拒否** ∧ counter-pin: inactive / `*_count_info` /
   正常エントリは通る
0c2k. 🔑 **LOCK 行の outcome を反転してもレポート JSON 全体が不変** (性質 pin)
   ∧ counter-pin: 非 LOCK 行では `non_winloss_excluded` が実際に 7 を返す (非空振り)
0c2l. **Bonferroni が v2∪v3 の単一族** (レビューの数値例を fixture 化: 15/20 の v3 sub-cell が
   `p_bonf > p_raw` を受け `promoted=False`、`candidates` は空) ∧ 全 tested セルの
   `p_bonf` が `p_raw × m_family` と一致
0c2m. **accrual 窓が名乗った長さちょうど** (30d/90d の境界日をまたぐ行で off-by-one を検出)
0c2n. **shadow LOCK の watcher 乖離が可視化される** (live fill 5 本を足すと
   pre-reg 忠実 22 / watcher 互換 27 / `watcher_divergence=True`、v2 と v3 の両方が
   flag される) ∧ counter-pin: live fill 無しなら一致し flag は空 ∧ live LOCK は
   構造上乖離しえない
0c2o. **厳格 shadow が `is_shadow` を要求** (flag-drift 4 本 + live 3 本を足しても faithful は
   9 のまま / watcher_compat は 16) ∧ counter-pin: drift 行は watcher_compat では数えられる
0c2p. **LOCK 計数が監査の as-of 上界に従う** (run 後 2 本を足しても 11 のまま、run 当日は含む)
   ∧ counter-pin: `since` は下界として独立に効く
0c2q. **件数監視 (`outcome_lock: false`) は redact されない** ∧ **キー未記載は redact が既定**
   ∧ 実 registry で count-only 3 件が除外され outcome LOCK 7 件が残る
0c2r. **min_n 未満の LOCK セルも在庫に出る** (kalman `n_decide=10` で 10 行 → 記録あり)
   ∧ counter-pin: 多重度は min_n のままなので 10 行群は族を膨らませない
0c2s. **`outcome_lock` は真の bool のみ** (`"false"` / `"true"` / `0` / `1` / `null` / `"no"`
   を lint が拒否) ∧ counter-pin: `True`/`False`/キー未記載は通る
0c2t. **未発効 LOCK は redact しない** (6 月の行を 07-01 窓で監査 → redact 0・統計生存・
   `locks_not_yet_started` に列挙) ∧ counter-pin: 窓が LOCK に届けば redaction 再開
0c2u. **routing が LOCK 母集団の行だけを退避** (母集団 21 / `since` 前 13 / live 9 の
   fixture で退避は 21、`n_unique_rows_in_window == n_lock_population`)
   ∧ complement 22 行は評価され `lock_complement_only` が立つ ∧ その WR に
   LOCK 行の outcome が混ざらない
0c2v. **truncate されたスナップショットを拒否** (50 行ちょうど / `--min-rows` 未満 /
   `count != len(trades)` の 3 形状) ∧ counter-pin: 完全なスナップショットは通る
0c3. **inclusive 窓が厳密に 365 日** (`window_bounds` の日数を算術検査、`window_days=1`
   なら 1 日)
0d. **戦略集計が LOCK セルそのものにならない** (全行 LOCK なら `clean_N=0`) ∧ counter-pin:
   非 LOCK ペアは集計される (LOCK の 40 WIN が混入すれば WR が 0.25 でなくなる)
1. LOCK セル (WR 90% の派手な fixture) → outcome 全欠落 ∧ `n` 生存
2. 非 LOCK セル (同じ fixture) → outcome 全生存
3. LOCK セルの session sub-cell → redact ∧ `candidates == []`
4. `direction=None` ワイルドカード LOCK → BUY/SELL 両方 redact
5. 別ペア / 逆方向 → redact されない
6. 実 registry ロード → `sr-anti-hunt-eurjpy-buy-forward-confirm` を含む ∧
   `*_fire-info` 系を含まない ∧ 解決済み `vix-sell-pilot-recheck` を含まない
7. dedup era 分割 (mqe 形状: 93.2% 全体 / 0.0% post-fix)
8. **算術 pin**: `DEDUP_GATE_FIX_TS` が `DemoDB._DEDUP_BACKFILL_CUTOFF` と一致
   (境界がずれると era 帰属が静かに壊れる)

---

## 3. 🔴 開示 — 本監査中に Claude が LOCK セルの outcome を 1 回観測した

§4 の計数不一致を追う過程で、Claude は
`sr_anti_hunt_bounce × EUR_JPY × BUY` の fresh (2026-08-05 以降) shadow 行の
`(status, outcome)` 分布を 1 回クエリし、**WIN/LOSS 内訳を観測した**。
これは P-10 (本セル×outcome の中間再計算禁止) に抵触する。

- **経緯**: 「fresh N = 35 か 36 か」の読み手間不一致 (§4) を切り分ける意図だったが、
  クエリが outcome ラベルを返した。counting の問いに outcome を返す経路を事前に
  潰していなかったのが原因。
- **緩和材料ではあるが免責ではない**: 同じ統計は weekly deepdive が少なくとも 5 週
  公表し続けており (§2.2b)、本観測は既存の系統的漏洩に 1 件追加したもの。
  **重大なのは本観測ではなく §2.2b の systematic exposure の方である** — 開示の主眼を
  取り違えないこと。
- **帰結**: §4 の計数基準の確定を Claude が単独で行うと、内訳を知った上での選択になり
  中立でない。よって **計数基準の確定は user 決裁**とし、registry に決定点を登録した
  (`sr-anti-hunt-eurjpy-count-basis-declaration`)。
- **再発防止**: 本 PR の redaction 層は**レポート出力**を塞ぐが、
  ad-hoc クエリは塞がない。`n` のみを返す計数ヘルパを使うこと (§5 残課題)。

---

## 4. 付随して発見: LOCK トリガの計数基準が読み手間で不一致 (未解決)

| 読み手 | 基準 | 2026-09-20 時点の N |
|---|---|---:|
| `tools/prereg_trigger_watch.py` (トリガ所有者) | registry `closed_only: true` — CLOSED 全件 | **36** |
| weekly deepdive | `outcome ∈ {WIN, LOSS}` | **35** |

差 1 行は `outcome = BREAKEVEN` の CLOSED 行。pre-reg 原文 (§Forward 確認 pre-reg) は
母集団を「`dedup_violation=0` の shadow rows、2026-08-05 以降の新規」としか書いておらず、
**BREAKEVEN の扱いを規定していない** (`closed_only` 自体 registry 側の補間)。

これが問題になるのは判定式の側:

- ① `EV>0 (片側 t)` — BREAKEVEN (pnl≈0) を含めて計算可能
- ② `Wilson_lo(95%) > 38.7%` — **WIN/LOSS の二値分母が必要** = BREAKEVEN は入れられない

⇒ 現行のままだと **トリガは N=40 で発火するのに、②が評価される実 N は ≤39** となり、
「宣言した N で判定した」という前提が崩れる (LOCK 自身の power 主張が不正確になる)。

**いま直すべき理由**: 計数基準の確定は、outcome を見る前に行えば無バイアスだが、
N=40 到達後に行うと結果を見てからのルール変更になる。残り 4-5 本 / ETA 約 3 週間
(2026-10 中旬、直近 4 週の実効 accrual 1.75 本/週) なので、猶予は小さい。

**取り扱い**: 凍結 pre-reg の判定規則の補完は R1 (= user 決裁)。かつ §3 の開示により
Claude の選択は中立でない。よって registry に **期日 2026-10-12 の決定点**を登録し、
autopilot は執行しない。選択肢は (a) BREAKEVEN を母集団から除外し N=40 を WIN/LOSS で数える
(b) BREAKEVEN を含めて数え ② は WIN/LOSS 部分集合で評価すると明記し power 低下を受容
(c) BREAKEVEN を LOSS 扱い。**どれも「優劣を outcome から判断してはならない」** — 決め方は
事前の統計的筋 (②の分母定義との整合) のみで行う。

---

## 5. 残課題

- [ ] **LOCK 妥当性の disposition** (registry `sr-anti-hunt-eurjpy-lock-validity-disposition`、
      期日 2026-10-12) — §2.2b の 5 週露出を受けて、凍結時の α のまま判定してよいか
- [ ] 計数基準の user 決裁 (registry `sr-anti-hunt-eurjpy-count-basis-declaration`、期日 2026-10-12)
- [ ] LOCK セル用の「`n` だけを返す」計数ヘルパを用意し、ad-hoc クエリ経路も塞ぐ (§3 再発防止)
- [ ] 他の読み手 (`tools/r2_cell_demotion_audit.py`, `tools/alpha_scan_block_recalibration.py`,
      `tools/cell_edge_audit.py`) が LOCK セルの outcome を出していないか横展開で grep
      — 「1 箇所直したら同型の兄弟を同じ PR で掃く」([[project_mof_ingest_defect_family_2026_09_17]])
      の未実施分。本 PR では deepdive 経路のみ塞いだ
- [ ] `mqe_gbpusd_fix` の発火枯渇 (4.7 ヶ月で 2 本) の原因調査 — §1.4 で真因が
      dedup でないと確定したので、次は signal 側

## 6. 教訓

- **除外率は分母の選択で意味が変わる。「raw の何%が捨てられたか」は効率の話であって、
  「独立観測が何本貯まるか」とは別の estimand。** 捨てられた行が独立イベントかどうかを
  機構から確認するまで、除外率を枯渇の原因に使ってはならない
- **レポートが自分で「構造的に衝突している」と書いているのに数値を出し続けるなら、
  それは検知ではなく作文。** 衝突を認識した回で構造を止めること
- **repo に無いツールはテストされない。10 週打ち直され続けた ad-hoc スクリプトは、
  「毎週動いている」ように見えて品質ゲートの外側にあった**

## Related
- [[sr-anti-hunt-eurjpy-r1-verdict-2026-08-05]] (LOCK 原本) / [[lesson-shadow-emit-dedup-2026-04-30]]
- [[lesson-per-bar-dedup-tf-aware-2026-05-03]] / [[roadmap-v2.3-payoff-friction-repair]] M3 行
- MEMORY: `project_review_gate_vacuous_2026_09_11` (検知器の NG 入力 pin) /
  `project_r2_audit_dedup_contamination_2026_06_08` / `feedback_audit_past_verdicts_2026_08_05`
