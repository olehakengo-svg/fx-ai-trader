---
title: 勝ち側 exit の regime break — shadow の avg_win 縮小は劣化ではなく計測の是正
date: 2026-09-14
rule: R3
status: 機構帰属は確定 (2026-10-01 estimand 修正後も再現) / ⚠️ 「市場機会は劣化していない」(敵対的検証②) は 2026-10-01 撤回 — exit 非依存の固定ホライズン対照では市場側の変化は未識別 (点推定は振幅縮小、重なり窓ブロック CI は 0 を含む)、「三重確認」は二重 (機構帰属 + step function) に格下げ (末尾「2026-10-01 review backlog 消化」節)
supersedes_claim: "cell deepdive 2026-09-13 §『本当の構造的問題 — R:R 反転』の解釈"
related:
  - knowledge-base/wiki/lessons/lesson-shadow-sl-rollback-bug-2026-06-03.md
  - knowledge-base/wiki/analyses/mfe-be-lock-design-2026-06-03.md
  - knowledge-base/wiki/analyses/payoff-asymmetry-diagnosis-2026-07-07.md
  - knowledge-base/raw/cell_deepdive/2026-09-13/_summary.md
---

# 勝ち側 exit の regime break (2026-06-03T07:58Z)

## 問い

2026-09-13 の cell deepdive が `sr_anti_hunt_bounce` の R:R 反転 (2026-05 の 2.30 →
以降 0.27 / 0.25 / 0.71 / 0.04) を検出し、主因が負け拡大ではなく **avg_win の 1/5 への
縮小** (19.03p → 3.5〜5.9p) であることを特定、次アクションとして
「exit_reason 別実測での分解」を最優先に指定した。本ページはその実行結果。

- ツール: `tools/win_side_exit_decomposition.py` (本 PR で新規、副作用なし)
- データ: Render PROD `/api/demo/trades?limit=100000` (HTTP 200, 17,602 件, 2026-09-14 取得)
- estimand: XAU 除外 / `dedup_violation=1` 除外 / `outcome ∈ {WIN, LOSS}`。
  `avg_win` = `outcome=WIN` 行の `pnl_pips` 平均。
  ⚠️ `close_reason="SL_HIT"` は BE/トレール利確を含む混成ラベル
  (MEMORY `project_sl_hit_label_collision`) のため、分解は**全て outcome で分割**した。

## 答え — avg_win 縮小は市場でも戦略でもなく、**shadow の exit 機構が 1 日で入れ替わった**

`sr_anti_hunt_bounce` の WIN 行を close_reason × outcome で割ると、期間の前後で
**終端機構がほぼ完全に入れ替わっている**:

| 期間 | 終端機構 (WIN 行) | avg_win | WIN 行 median 保有時間 |
|---|---|---|---|
| < 2026-06-03 | `MAX_HOLD_TIME` 70.6% / `WEEKEND_CLOSE` 29.4% / `SL_HIT` **0%** | 19.42p ⚠️ | **8.00h** |
| ≥ 2026-06-03 | `SL_HIT` **100%** | 3.96p | **0.54〜1.28h** |

> ⚠️ 2026-10-01 訂正: 上表の pre 行は live 1 行 (EUR_JPY BUY +25.7p `MAX_HOLD_TIME`、
> `oanda_trade_id` 有り) を含んでいた。shadow 限定 + clean cohort では pre = `MAX_HOLD_TIME`
> 68.8% / `WEEKEND_CLOSE` 31.2% / avg_win **19.03p** (N_win=16)、post = `SL_HIT` 100% /
> avg_win **4.02p** (N_win=121)。結論 (終端機構の入れ替わり) は不変。

`SL_HIT` かつ `outcome=WIN` = **BE/トレールが利益側で刈った**の意 (ラベル衝突の定義より)。
つまり「勝ちトレードが 8 時間走って終値で終わる」体制から
「勝ちトレードが 30〜80 分で BE/トレールに刈られる」体制へ切り替わった。

### 機構帰属 — commit `ab7a4931` (2026-06-03 16:58 JST = **07:58 UTC**)

`fix(exit): persist shadow SL changes directly to DB [rule:R3]`。
それ以前、shadow trade の SL 変更は `OandaBridge.modify_sl_sync` が
`oanda_trade_id` 不在で `False` を返すため毎 iteration ロールバックされており、
**BE-lock / SMC BE+0.1 / ATR×0.8 BE / ATR×1.5 trail / v6.4 TP extender の全てが
shadow 上で dead code** だった ([[lesson-shadow-sl-rollback-bug-2026-06-03]])。
この fix で shadow が初めて本番の BE/trail スタックを実際に受けるようになった。

## 敵対的検証 (3 点 — ⚠️ ② は 2026-10-01 撤回、末尾節の固定ホライズン対照で置換)

**① 遷移の鋭さ** — 全戦略 shadow の WIN 行に占める `SL_HIT` 比率 (日次):

| 05-28 | 05-29 | 06-01 | 06-02 | **06-03** | 06-04 | 06-05 | 06-08 |
|---|---|---|---|---|---|---|---|
| 0.0% (N=31) | 0.0% (N=31) | 0.0% (N=19) | 0.0% (N=22) | **76.7% (N=73)** | 85.3% | 88.3% | 89.3% |

1 日で 0% → 77% の step function。市場レジームでも戦略変更でもこの形は作れない。

> ⚠️ **② は 2026-10-01 に撤回** (PR #253 Codex P1 4002255778)。下表の 2 指標はどちらも
> exit 機構に依存する — `mafe_favorable_pips` は WIN だけでなく **全行が exit 時点で
> censored**、LOSS 保有時間は SL/BE/trail の変化そのもので動く。よって「exit 機構に
> 依存しない指標」という前提が偽で、市場側の悪化を棄却する根拠にならない。
> 置換となる exit 非依存の対照 (entry 後の固定ホライズン excursion) は末尾節を参照。
> 以下は撤回済みの原文として残す。

**② 対照群 (MFE の censoring を疑う)** — 「相場が走らなくなった」説の検定。
capture (realized/MFE) は 0.815 → 0.55 へ落ち avg_MFE も 23.34 → 6p へ落ちるが、
**MFE は exit 時点までしか観測されない**ため exit を早めれば機械的に縮む。
exit 機構に依存しない指標で見ると:

| 指標 | 2026-05 | 2026-06 | 2026-07 | 2026-08 |
|---|---|---|---|---|
| 全 clean 行の **median** MFE | 2.00p | 3.10p | 3.70p | **5.70p** |
| LOSS 行 median 保有時間 | 2.01h | 0.96h | 2.73h | 4.00h |

median MFE は**むしろ上昇**している。5 月の平均 MFE 9.87 に対し中央値 2.00 という
裾の重さが、少数の大走り (05-25/05-26 の EUR_JPY 群) に由来していたことを示す。
→ ~~**市場側の順行余地は劣化していない。走らせるのをやめただけ。**~~
(⚠️ 撤回 2026-10-01: 根拠の 2 指標が exit 機構依存で無効。exit 非依存の固定ホライズン
対照では市場側の変化は未識別 (点推定は振幅縮小、重なり窓ブロック CI は 0 を含む) —
「走らせるのをやめた」が主因である点は維持、「市場側は劣化していない」は主張できない)

**③ shift-share は本件では非同定** — close_reason 軸の分解は
`mix -0.00p / within -15.46p (100%)` と出るが、これは share_A(SL_HIT)=0% /
share_B(SL_HIT)=100% と**群が前後で素に交わらない**ため、欠側の平均を補完した
数字にすぎない。「100% が群内劣化」と読んではならない。正しい記述は
**「機構そのものが入れ替わった (mix/within に分解できない型の変化)」**。

## 全戦略への波及 — shadow の payoff 統計は境界で estimand が変わる

fix は shadow 全体に効くため、影響は 1 戦略に留まらない
(全戦略 / XAU 除外 / dedup 除外):

| stream | 期間 | N | WR | avg_win | avg_loss | R:R | EV | WIN 行の SL_HIT 率 |
|---|---|---|---|---|---|---|---|---|
| **SHADOW** | pre-fix | 5,377 | 26.3% | 11.72 | 6.16 | **1.90** | −1.45 | 0.3% |
| **SHADOW** | post-fix | 7,200 | **51.5%** | 4.35 | 7.94 | **0.55** | −1.61 | **88.3%** |
| LIVE (`oanda_trade_id!=''`) | pre-fix | 744 | 41.9% | 4.76 | 4.72 | 1.01 | −0.74 | 1.9% |
| LIVE | post-fix | 133 | 51.1% | 5.00 | 12.05 | 0.42 | −3.33 | 14.7% |

読み方は 3 点:

1. **WR +25.2pp / R:R −71% は BE/trail の署名**。MEMORY `project_be_trail_inflates_python_bt_wr`
   が Python BT で ablation 実証した +20pp の水増しが、**本番 shadow で +25.2pp として
   再現**した。同メモリの適用範囲を「Python BT」から「2026-06-03 以降の本番 shadow」へ拡張する。
2. **EV はほぼ動いていない** (−1.45 → −1.61)。WR だけ見れば大改善、R:R だけ見れば崩壊、
   EV は一貫して負。MEMORY `feedback_partial_quant_trap` の教科書例。
3. **fix は shadow の live 忠実度を上げた**。pre-fix の shadow R:R 1.90 に対し
   同期間 live は 1.01 (乖離 1.9×)。post-fix は shadow 0.55 / live 0.42 で接近。
   すなわち **pre-fix shadow の方が異常値**であり、post-fix は是正後の姿。

## deepdive 2026-09-13 の解釈訂正

> 「2026-05 の 2.30 を最後に R:R が反転したまま戻っていない … 利確側 (TP / early exit) の
> 変化を疑うべき」

方向は正しかった (利確側) が、**「戻っていない」= 劣化が継続中**という含意は誤り。
2026-06-03 に計測体制が一度だけ切り替わり、以後は新体制で安定している。
**劣化ではなく水準の付け替え**であり、「戻る」ことは fix を戻さない限り起きない。

## 決定への影響 — 週次 PAIR_PROMOTED 候補の汚染

9 週連続で出ている唯一の候補 `sr_anti_hunt_bounce × EUR_JPY × Tokyo × BUY`:

| 母集団 | N | WR | Wilson_lo | avg_win | R:R | EV | 総pips |
|---|---|---|---|---|---|---|---|
| 全体 (週次レポート掲載値) | 32 | 71.9% | 0.546 | 12.90 | 1.68 | **+7.11** | +227.6 |
| pre-fix (< 06-03) | 14 | 64.3% | 0.388 | 24.83 | 2.53 | +12.46 | **+174.4** |
| post-fix (≥ 06-03) | 18 | 77.8% | 0.548 | 5.24 | **1.04** | **+2.96** | +53.2 |

**掲載 EV +7.11 の実質は、消滅した計測体制由来の 14 行が総 pips の 77% を担った結果**。
現行体制だけで見ると EV は 4.2 分の 1 (+2.96)、R:R は 1.04 (ほぼ等倍)、N は 18 で
deepdive の候補化閾値 `MIN_N=20` にも届かない。

前週レポートの「post-May 単独で Wilson_lo 0.567 を維持 ✅」という安心材料も、
(a) cut が **5 月末**であって **fix 日 (06-03)** ではない、
(b) 通した gate が WR ベースであり、その WR こそ BE/trail が水増しする量である、
の 2 点で本件の反証になっていない。

⚠️ **pre-reg LOCK には触れていない。** forward 枠 (`entry_time ≥ 2026-08-05`,
fresh N=32/40) は全数が post-fix であり汚染されていない。本節は週次レポートが毎週
再掲する**記述統計の訂正**であって、pre-reg の中間再計算 (P-10) ではない。

## 恒久ルール (運用へ)

**shadow の payoff 系統計 (`avg_win` / `avg_loss` / `R:R` / `WR` / 保有時間) を
2026-06-03T07:58Z をまたいで集計してはならない。** 境界前後は別 estimand。
必要なら fix 日で分割して両方を出す。
(2026-10-01 改訂: 境界は 1 点ではなく遷移窓 [07:58:28Z, 09:00:00Z)。clean pre =
`exit_time < 07:58:28Z`、clean post = `entry_time ≥ 09:00:00Z`、窓に掛かる建玉は除外。
対象は shadow stream (`oanda_trade_id` 無し ∧ `is_shadow=1`) に限定する。)
定数は `tools/win_side_exit_decomposition.py::SHADOW_EXIT_REGIME_BREAK`
(+ `SHADOW_EXIT_REGIME_TRANSITION_END`) を SSOT とし、
`tests/test_win_side_exit_decomposition.py` で pin 済み。

## 残件

- `sr_anti_hunt_bounce` の EV は post-fix 体制でも負 (戦略累計 −1.89p / PF 0.63)。
  本ページは **avg_win 縮小の原因**を確定させたが、**負 EV そのもの**は未解決。
  次の問いは「BE/trail を受けた上で正 EV になる構成が存在するか」であり、これは
  [[roadmap-v2.3-payoff-friction-repair]] T2 で grid 9 構成が BH-FDR 不通過 (p=1.0)
  となった論点と同型。安易な再試行は禁止 (R1 手続き必須)。
- `cpd_divergence` 通算 0 発火 (9 週連続) は本件と独立。経路断の確認は別件。

## 2026-10-01 review backlog 消化 — estimand 修正後の再計算

registry `review-backlog-253-257-digest` の PR #253 群 (Codex connector 未消化 5 件) を
消化した (rule:R3)。データ = Render PROD `/api/demo/trades?limit=100000`
(HTTP 200, 18,829 件, 2026-10-01 取得)。実行:
`python3 tools/win_side_exit_decomposition.py prod_trades.json --strategy ALL --stream shadow --bars-dir data/cache/massive`

### 指摘と処置

| # | 指摘 | 処置 |
|---|---|---|
| (a) P1 4002219365 | live/shadow 混在 | `load_clean(stream=)` 新設、既定 `shadow` = `oanda_trade_id` 無し ∧ `is_shadow=1`。live = `oanda_trade_id != ''` (is_shadow=0 単独では判定しない)。is_shadow=0 ∧ id 無し の 47 行は ambiguous でどちらにも入れない |
| (b) P2 4002219368 | 境界跨ぎ建玉を entry_time で pre へ | `split_cohorts`: clean pre = `exit_time < START` / clean post = `entry_time ≥ END` / それ以外は除外し件数・WR・SL_HIT 率を別報告 |
| (c) P2 4002219370 | 偶数コホートの中央値 | `statistics.median`。LOSS 行の保有時間表も併設 |
| (d) P2 4002255783 | cutoff が commit 分 | 遷移窓化。START = commit object 時刻 **07:58:28Z** (旧 "07:58" は 07:58:00–27 を誤って post へ)。END = Render deploy 完了時刻は記録なし (Render workspace 未選択 / KB・lesson にも時刻なし) のため挙動で導出: shadow 初の「WIN ∧ SL_HIT」(BE/trail 利益刈りの署名、06-02 まで日次 0%) が exit **08:01:26Z**、以後連続 → 遅くともこの時刻に稼働。保守的に **09:00:00Z** まで除外 |
| (e) P1 4002255778 | 三点確認 ② は exit 依存 | ② 撤回 (上記本文)。exit 非依存の対照 = [entry, entry + 60 分 / 240 分] を MASSIVE 1m 足でクリップした窓の最大有利/不利幅を計算する `fixed_horizon_excursion` を新設 (PR #310 Codex 2〜5 巡目で窓・母集団・CI を是正、下記)。exit_time / close_reason / mafe_* を一切参照しない |

各修正に既知 NG 入力で落ちる pin を併設し、修正を 1 つずつ戻す counterfactual 8 種で
全て対応 pin が落ちることを確認 (`python3 -B`)。

### 旧 vs 新 — 全戦略 shadow (XAU 除外 / dedup 除外)

| 項目 | 旧 (09-14, entry_time < "07:58") | 新 (shadow / clean cohort / 窓 [07:58:28, 09:00)) |
|---|---|---|
| pre N | 5,377 | 5,369 |
| post N | 7,200 (09-14 時点) | 8,259 (10-01 時点) / 除外 16 |
| WR | 26.3% → 51.5% | **26.2% → 51.1%** |
| avg_win | 11.72 → 4.35 | **11.74 → 4.49** |
| avg_loss | 6.16 → 7.94 | **6.16 → 8.01** |
| R:R | 1.90 → 0.55 | **1.91 → 0.56** |
| EV | −1.45 → −1.61 | **−1.47 → −1.63** |
| WIN 行の SL_HIT 率 | 0.3% → 88.3% | **0.1% → 88.4%** |

感度 (遷移窓 END): 08:01:26Z (除外 9) / 09:00Z (除外 16) / 06-04T00:00Z (除外 128)
のいずれでも WR 51.1% / R:R 0.56 / EV −1.63〜−1.64 で不変。旧方式
(entry_time 文字列 split) も同水準 → **全戦略 shadow の regime break の数値は (a)(b)(d)
修正後もほぼそのまま再現**。旧 09-14 表の SHADOW 行は実質 shadow 限定だったため
(a) の影響は sr_anti_hunt_bounce 個別表と下記 PAIR_PROMOTED 表に限られる。

live stream (`oanda_trade_id != ''`、untreated 側): pre N=744 WR 41.9% / R:R 1.01 /
EV −0.74 → post N=137 WR 50.4% / R:R 0.41 / EV −3.57。live は ab7a4931 の処置を
受けていないのに R:R が同方向に落ちている — ただし live の post は N=137 で、live
転送セル構成が 06 月以降大きく入れ替わっている (roster attrition) ため、これを
「市場悪化」の証拠とも「無関係」の証拠とも読まない (未識別)。

### sr_anti_hunt_bounce (shadow 限定)

| 群 | N | WR | avg_win | avg_loss | R:R | EV | WIN 行 SL_HIT 率 | WIN median 保有 |
|---|---|---|---|---|---|---|---|---|
| clean pre | 54 | 29.6% | 19.03 | 9.84 | 1.93 | −1.28 | 0% | 8.00h (05 月) |
| clean post | 199 | 60.8% | 4.02 | 11.54 | 0.35 | −2.08 | 100% | 0.40〜1.25h |

境界跨ぎ 0 行。close_reason 軸 shift-share は引き続き非同定 (群が素に交わらない)。

PAIR_PROMOTED 候補 (`× EUR_JPY × Tokyo(UTC 0–6) × BUY`, entry < 2026-09-14):
掲載値 N=32 は live 2 行を含んでいた。**shadow 限定の pre (clean、全行が LOCK since
2026-08-05 より前) は N=12 / EV +12.96 / 総 pips +155.5** (旧 N=14 / EV +12.46 / +174.4)。
post 側 (shadow 限定 N=18、境界跨ぎ 0) は本節では**数値を出さない** — 下記 P-10 注記。

> 🔴 **P-10 開示 (2026-10-01)**: この sub-cell は LOCK `sr-anti-hunt-eurjpy-buy-forward-confirm`
> (EUR_JPY × BUY、since 2026-08-05、fresh N≥40 で 1 回限り判定、中間再計算禁止) の
> refinement であり、post 群 (06-03〜09-14) は forward 枠の行を含む。上の「決定への影響」表
> (09-14 作成) の post 行・全体行は**既に forward 行を含む outcome 統計を公表していた**
> (2026-09-20 changelog が記録した 5 週の systematic exposure と同型)。本 PR の再計算でも
> Claude は post 群の outcome を観測した (shadow 限定の post は 09-14 掲載値と同一行集合 =
> 新情報なし。ただし Tokyo 定義を UTC 0–7 / 0–8 に広げた変種で forward 行を含む集計を
> 追加で 1 回ずつ観測)。⇒ registry `sr-anti-hunt-eurjpy-lock-validity-disposition` の
> 露出記録に追加すべき事項として親セッションへ回付。本ページでは post 側・全体の
> outcome 数値を新たに記載しない。

### (e) 三点確認の結論 — exit 非依存の固定ホライズン excursion

全戦略 shadow。**母集団は outcome を問わない全 entry** (BREAKEVEN / 未決済を含む、
N=14,627)、**entry 時刻だけで分割** (pre = entry < 07:58:28Z / post = entry ≥ 09:00Z) —
WIN/LOSS 限定や exit_time による分割は、BE/trail が ±0.5p 決済 (= BREAKEVEN) を生む以上
exit 機構による選別になる (PR #310 Codex P1 4151271131)。excursion は 0 で clamp
(P1 4151271136)。**窓は [entry, entry + H] を 1m 足でクリップ** (P1 4151347679: 旧
「entry 以後の最初の 15m バーから H 本」は非整列 entry で先頭最大 15 分を欠き末尾に最大
15 分を足していた。1m 足なら名目窓とのずれは先頭・末尾とも ≤1 分)。1m 足は
`data/cache/massive` の 1m キャッシュが 2026-04-15 前後で切れるため、MASSIVE から
2026-03-27〜10-01 を 13 pair 分取得して使用 (リポジトリには置かない)。窓の内部に
5 分超の欠落 / 先頭・末尾に 4 分超の欠落があれば除外 (P2 4151253825)。
**共通被覆** (P1 4151253820: キャッシュ終端・始端の差で片群だけ pair が落ちる型を防ぐ) は
1m では 13 pair 全てが全期間を覆うので除外 0 行。窓の有効率 pre 94〜96% / post 95〜97%:

| horizon | 群 | N | median 有利幅 | median 不利幅 | 有利/不利 比 | instrument×entry_type を揃えた mean 有利幅 | 同 不利幅 |
|---|---|---|---|---|---|---|---|
| 60 分 | pre | 5,705 | 6.60 | 7.70 | 0.857 | 9.24 | 10.15 |
| 60 分 | post | 8,347 | 6.10 | 7.30 | 0.836 | 8.63 | 9.17 |
| 240 分 | pre | 5,570 | 12.80 | 14.00 | 0.914 | 18.32 | 20.02 |
| 240 分 | post | 8,247 | 12.10 | 13.20 | 0.917 | 16.91 | 16.66 |

- median 有利幅 post−pre: 60 分 **−0.50p** / 240 分 **−0.70p**。
  **重なり窓ブロック bootstrap 95% CI: 60 分 [−1.00, +0.24] / 240 分 [−2.00, +1.40]**
  (窓 [entry, entry+H] が START を越える pre 行 (60 分 14 行 / 240 分 30 行) は落とし、
  群を跨いだ窓の重なりを無くしてある — Codex P2 4152047567)
  (ブロック = excursion 窓 [entry, entry+H] が連鎖的に重なる観測の塊、数 pre 131 / post 310 (60 分)・
  21 / 20 (240 分)。UTC 日ブロック ([−1.10, +0.20] / [−2.00, +0.80]) は日付を跨いで重なる
  240 分窓を別ブロックに分けていた — Codex P2 4152000632)
  (日数 pre 44 / post 85)。同時刻に複数 pair・戦略が発火すると excursion 窓が重なって
  強く従属するため、行単位 i.i.d. bootstrap は CI を不当に狭くする (P1 4151311925)。
  instrument×entry_type を揃えた mean (共通 156 cell、pre 行の 64%) では有利幅
  −7% (60 分) / −8% (240 分)、不利幅 −10% / −17%。
- 改訂履歴 (同じ問いへの推定値の推移、いずれも本 PR 内で是正): 初版 (WIN/LOSS 限定・
  被覆非対称・clamp なし・i.i.d. CI・15m 非整列窓) は「有利幅 −19%・有意」→ 2〜3 巡目
  修正後 15m 窓で median −0.60p / −1.10p (日ブロック CI [−1.20, +0.00] / [−2.50, +0.40])
  → 1m クリップ窓 (本表) で −0.50p / −0.70p。**どの段でもブロック bootstrap CI は 0 を含む / 境界上**。
- 読み:
  1. **「市場側の順行余地は劣化していない」は根拠ごと撤回**。旧根拠 (mafe / LOSS 保有時間)
     は exit 機構依存で無効。exit 非依存の対照では点推定で有利幅が 7〜8% 縮小 (不利幅も
     同程度以上に縮小、有利/不利 比 0.857→0.836 / 0.914→0.917 でほぼ不変 = 方向性ではなく
     振幅の形) だが、**重なり窓ブロック bootstrap の CI は 0 を含む** —
     「縮んだ」とも「縮んでいない」とも統計的には言えない。⇒ **市場側の変化は未識別**。
  2. ~~大きさの比較: 点推定の有利幅縮小 −7〜−8% は avg_win の −62% (11.74→4.49) を説明できる
     規模ではない。~~ (⚠️ 2026-10-01 撤回、PR #310 Codex P1 4152175652: 対照コホートは約定した
     建玉であり、建玉上限 / 決済後 cooldown のゲート (`modules/demo_trader.py` の open-position
     limit / post-exit cooldown) を経由するため、BE/trail で早く決済されると枠が空いて post 期に
     別の entry が入る = **対照自体が exit regime で選別されている**。よって本表は完全な exit 非依存
     対照ではなく、点推定の大きさで市場寄与を上限評価することはできない。完全な対照はゲート前の
     候補シグナル (C1 candidate テーブル等) から組む必要があり未実施)。
     **avg_win 縮小の主因が exit 機構の入れ替わりである点は維持** (根拠は機構論のみ:
     WIN 行の SL_HIT 率 0.1%→88.4% の step function は市場では作れない)。
     ただし exit 機構と市場振幅の寄与の定量配分は**未識別** (excursion と realized avg_win の
     写像は非線形で、この表から引き算はできない)。
- sr_anti_hunt_bounce 単独 (全 entry N=273、1m で 5 pair 全て被覆。strategy 集計 =
  LOCK セルの strict super-set で、outcome でなく価格 excursion): 60 分 median 有利幅
  +0.95p (重なり窓ブロック [−1.80, +2.50]) / 240 分 −2.30p ([−6.39, +1.80])、ブロック数 pre 27〜43 /
  post 62〜63。**検出力不足で未識別** (どちら向きの主張にも使わない)。

### 結論の改訂

- **維持**: shadow の payoff 統計は 2026-06-03 の遷移窓で estimand が断絶する。
  WR 26→51% / R:R 1.9→0.56 は BE/trail が shadow で有効化された署名であり、
  劣化ではなく計測の是正 (EV は −1.47→−1.63 でほぼ不変)。数値は estimand 修正後も再現。
- **撤回**: 「市場機会は悪化していない (三点確認)」。正しくは「exit 非依存を意図した対照
  (約定建玉の固定ホライズン excursion — ただし建玉ゲート経由で exit regime に選別されうる) で
  有利幅・不利幅とも点推定 7〜17% 縮小 (振幅の形) だが重なり窓ブロック CI は 0 を含み、
  **市場側の変化は未識別**。avg_win −62% の主因が exit 機構である点は機構論 (SL_HIT step function) で維持、
  寄与の配分は未識別 (点推定の大きさによる上限評価も撤回)」。完全な exit 非依存対照 = ゲート前候補シグナル基準は未実施。
- **訂正**: sr_anti_hunt_bounce pre avg_win 19.42→19.03p (live 1 行除外)、
  PAIR_PROMOTED pre 14→12 行 (live 2 行除外)。
