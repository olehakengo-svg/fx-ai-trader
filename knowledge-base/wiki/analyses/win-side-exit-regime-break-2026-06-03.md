---
title: 勝ち側 exit の regime break — shadow の avg_win 縮小は劣化ではなく計測の是正
date: 2026-09-14
rule: R3
status: 確定 (機構帰属 + 日次 step function + 対照群で三重確認)
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
| < 2026-06-03 | `MAX_HOLD_TIME` 70.6% / `WEEKEND_CLOSE` 29.4% / `SL_HIT` **0%** | 19.42p | **8.00h** |
| ≥ 2026-06-03 | `SL_HIT` **100%** | 3.96p | **0.54〜1.28h** |

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

## 敵対的検証 (3 点)

**① 遷移の鋭さ** — 全戦略 shadow の WIN 行に占める `SL_HIT` 比率 (日次):

| 05-28 | 05-29 | 06-01 | 06-02 | **06-03** | 06-04 | 06-05 | 06-08 |
|---|---|---|---|---|---|---|---|
| 0.0% (N=31) | 0.0% (N=31) | 0.0% (N=19) | 0.0% (N=22) | **76.7% (N=73)** | 85.3% | 88.3% | 89.3% |

1 日で 0% → 77% の step function。市場レジームでも戦略変更でもこの形は作れない。

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
→ **市場側の順行余地は劣化していない。走らせるのをやめただけ。**

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
定数は `tools/win_side_exit_decomposition.py::SHADOW_EXIT_REGIME_BREAK` を SSOT とし、
`tests/test_win_side_exit_decomposition.py` で pin 済み。

## 残件

- `sr_anti_hunt_bounce` の EV は post-fix 体制でも負 (戦略累計 −1.89p / PF 0.63)。
  本ページは **avg_win 縮小の原因**を確定させたが、**負 EV そのもの**は未解決。
  次の問いは「BE/trail を受けた上で正 EV になる構成が存在するか」であり、これは
  [[roadmap-v2.3-payoff-friction-repair]] T2 で grid 9 構成が BH-FDR 不通過 (p=1.0)
  となった論点と同型。安易な再試行は禁止 (R1 手続き必須)。
- `cpd_divergence` 通算 0 発火 (9 週連続) は本件と独立。経路断の確認は別件。
