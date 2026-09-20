# weekly deepdive の 2 欠陥 — dedup 除外率の estimand 誤り と pre-reg LOCK セルの毎週再計算

**日付**: 2026-09-20 / **rule**: R3 (構造バグ + estimand 訂正、365d BT 不要)
**きっかけ**: 2026-09-20 weekly deepdive 実行結果 (`knowledge-base/raw/cell_deepdive/2026-09-20/_summary.md`)
**データ**: Render PROD `/api/demo/trades?limit=100000` スナップショット (18,057 行、2026-09-20T15:51Z 取得)。
ローカル `demo_trades.db` は STALE のため不使用。
**成果物**: `tools/cell_deepdive_audit.py` (新規、in-repo 化) / `tests/test_cell_deepdive_lock_redaction.py` (18 pins)

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
| sr_anti_hunt_bounce | 267 | 173 | 30 | **13.46** | 2026-09-18T00:00 |
| rsk_gbpjpy_reversion | 48 | 33 | 10 | 2.57 | 2026-09-15T21:31 |
| vsg_jpy_reversal | 56 | 32 | 13 | 2.49 | 2026-09-18T03:07 |
| vdr_jpy | 28 | 20 | 3 | 1.56 | 2026-09-18T14:52 |
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
