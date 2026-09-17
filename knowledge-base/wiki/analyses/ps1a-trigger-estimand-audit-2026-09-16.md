# P-S1(a) 執行トリガの estimand 監査 — 発火した verdict は gross/net 不一致の産物 (2026-09-16、rule:R3)

**Status**: 🔴 確定 / 自動執行を停止 (verdict を `USER_REDECISION_ESTIMAND` へ) / live 不触 → **✅ 決裁済み (2026-09-17): (a) Option C = retire 採択** ([[ps1a-option-c-retire-2026-09-17]])
**対象**: `sweep_reversion_eurgbp_late` — T8 DEFER の Option B 執行トリガ
**契機**: 2026-09-14T21:16Z の 10 本目到達で `tools/ps1a_execution_check.py` が
**`OPTION_B_EXECUTE`** を返した (unique N=10 ∧ spaced EV=+2.92p>0)
**前提資料**: [[sweep-zero-fire-forensic-2026-09-14]] (forensic #2) §6 / [[sweep-reversion-ps1a-decision-packet-DRAFT]] §1.1 §6-2 §8

---

## 0. 結論 (3 行)

1. 発火した `OPTION_B_EXECUTE` は **estimand 不一致の産物**。凍結閾値 (+6.22 p/t) は
   研究 grid の **net-of-spread**、判定器が読んでいた shadow EV は **gross-of-spread**。
2. 同一 10 本を凍結閾値と同じ estimand に揃えると **spaced net EV = −3.33 p/t**
   (符号反転)。負性は **摩擦 convention の選び方に依存しない** (4 通り中 3 通りで負、
   唯一正になるのは「spread=1.5p」という **10/10 で反証済みの仮定**のみ)。
3. **自動執行が armed だった** — scheduled task `ps1a-sweep-trigger-executor` は
   毎日 19:37 JST に判定し `OPTION_B_EXECUTE` なら runbook §3 (PR → `--admin`
   merge → deploy) まで自走する委任 (2026-08-05)。本監査の修正で判定器が
   `USER_REDECISION_ESTIMAND` を返すため、同 task の既定分岐
   (「OPTION_B_EXECUTE 以外は live 不触で報告のみ」) により停止する。

## 1. 何が違う量だったのか (コード由来の事実)

| 層 | 量 | 出所 |
|---|---|---|
| 凍結閾値 +6.22 p/t | **net** = `Δprice/psize − SPREAD_PIP[EUR_GBP]` (=**1.5p**、往復1回控除) | `tools/research_sweep_reversion_grid_12y.py` L33/L156-158 |
| 判定器が読む shadow EV | **gross** = `(exit_price − entry_price) × pip_mult`、摩擦控除なし | `modules/demo_db.py:1223` |
| shadow の約定価格 | **mid** — `entry_price == signal_price` が実測 **10/10 で差 0.00 pip** | 本番 API 実測 (§2) |
| `spread_at_entry/_at_exit` | 実 OANDA `ask−bid` を各時点で記録。**診断表示専用**で pnl には入らない | `demo_trader.py:1478-1487 / 3558-3562`、使用箇所は friction ratio と close_analysis のみ |

⇒ 「spaced EV>0」という凍結条件の**閾値は net 側で校正されている**のに、
**評価は gross 側で行われていた**。差額は EUR_GBP LATE ロールオーバーの実勢 spread で、
これは 1.5p ではなく **5.4〜16.6p** (§2)。

## 2. 実測 (本番 API `/api/demo/trades` mode=daytrade_eurgbp、since 2026-07-03、全ページ)

18 行 = unique 10 (`dedup_violation!=1`) + 重複 8。全行 `is_shadow=1` /
`oanda_trade_id` 空 = **live 露出はゼロ** (止血対象ではない)。

| 基準 | N | EV gross | WR gross | **EV net (研究 parity)** | WR net | s_entry 平均 |
|---|---|---|---|---|---|---|
| row | 18 | +2.61 | 77.8% | −3.43 | 22.2% | 7.67p |
| unique | 10 | +3.37 | 80.0% | **−2.48** | 30.0% | 7.60p |
| spaced | 8 | +2.92 | 75.0% | **−3.33** | 25.0% | 8.06p |

### 2-1. 摩擦 convention 4 通り (spaced N=8) — 負性は convention 非依存

| convention | 控除 | EV | Σ | 勝ち行 | t |
|---|---|---|---|---|---|
| 研究の**仮定** (反証済) | 1.5p 固定 | **+1.43** | +11.4 | 5/8 | +1.01 |
| 研究 **parity** (primary) | `(s_e+s_x)/2` | **−3.33** | −26.7 | 2/8 | −1.95 |
| forensic #2 §6 | `s_e` | **−5.14** | −41.1 | 2/8 | −3.42 |
| house RT ([[friction-analysis]]) | `s_e+s_x` | **−9.59** | −76.7 | 0/8 | −4.00 |

- 研究 parity を primary とする理由: 研究は mid 価格差から往復 spread を **1 回**
  控除する。live でその 1 回分に対応するのは buy=ask / sell=bid の片側ずつ
  = `(s_e+s_x)/2`。**最も甘い実測ベースの convention**であり、それでも負。
- bootstrap (20k resample, N=8): **P(net EV>0) = 0.0224** / unique N=10 では 0.0512。
  N=8-10 なので「負であることの有意性」は主張しない。主張は**逆**方向 —
  **正であるという読みが、測定されている実コストを落とした結果である**こと。

### 2-2. spread 前提は平均でなく **全観測**で反証されている

| 前提 | 出所 | 充足行 |
|---|---|---|
| 実勢 1.5-3p | pre-reg 反証チェック #2 | **0 / 10** |
| 3.5p でも +4.22p (耐性) | 同 #2 | **0 / 10** |

entry spread min/med/max = **5.4 / 6.6 / 16.6p**。最小値すら前提上限の 1.5 倍超。
「平均が超えた」ではなく「**一度も前提内に入っていない**」。

## 3. cap 再決裁 (forensic #2 §8-1) の選択肢は空だった

forensic #2 は「cap を breakeven 7.72p 未満 (例 5.0-6.0p) に締めるか Option C」を
user 決裁に出した。**実測でその menu を埋めると、締める側に解が無い。**

| live cap | 生存行 (spaced) | EV gross | **EV net** |
|---|---|---|---|
| 1.5p (研究前提) | **0** | — | — |
| 3.5p (耐性前提) | **0** | — | — |
| 5.0p | **0** | — | — |
| 6.0p | 1 | +0.10 | −5.45 |
| 7.0p | 4 | −0.18 | −5.36 |
| 7.72p (breakeven) | 6 | +2.60 | −2.35 |
| 8.0 / 10.0p (現 AMENDMENT) | 7 | +2.59 | −2.86 |
| 無制限 | 8 | +2.92 | −3.33 |

**どの cap でも net は負**。かつ breakeven 未満に締めると **母集団が消える** (N=0) —
「cap を締めて正 EV 部分集合を残す」経路は存在しない。cap は選べる変数ではなく、
**この cell が live で成立しないことの言い換え**になっている。

## 4. もう一つの独立な水増し (参考、本判定には使っていない)

gross 側の勝ちは `close_reason="SL_HIT"` かつ pnl 正の行が **5/10** —
BE/トレール利確のラベル衝突 (MEMORY `project_sl_hit_label_collision_2026_08_07`)。
BE/Trail は WR を +20pp 水増しする既知経路 (`project_be_trail_inflates_python_bt_wr`
/ T3 診断) であり、**gross EV 自体も上振れ側**にある。
ただし本監査の結論は §2 の摩擦だけで確定するので、この分は加算していない。

## 5. あわせて見つかった量の乖離 (packet §114 の再確認)

- 研究 gross ≈ **+7.72p** (= +6.22 + 仮定 1.5) に対し、shadow 実測 gross は
  **+2.92p** (spaced) — 摩擦を入れる前に既に **研究エッジの 38%** しか出ていない。
- つまり不成立の原因は 2 つ独立にある: (i) **エッジの再現不足** (7.72 → 2.92)
  (ii) **摩擦の前提違反** (1.5 → 6.26 実測 cost)。**どちらか一方だけでも不足**で、
  両方が同方向に効いている。packet §114 の「shadow EV は entry 方向の符号確認まで。
  検証済み +6.22 p/t の再現確認ではない」という留保が、ここで定量的に確定した。

## 6. 判定と執行 (本セッション)

### やったこと (R3 — 計測が名乗る量を測っていない構造バグ)
- `tools/ps1a_execution_check.py`: gross と net を併記し、**gross>0 ∧ net≤0 の間は
  `USER_REDECISION_ESTIMAND`** を返す (自動執行を止める)。spread 記録の被覆が
  1.0 未満の基準も同 verdict (「spread 欠測 = 摩擦ゼロ」と黙読しない fail-loud)。
- 回帰 pin 6 本追加 (`tests/test_ps1a_execution_check.py`、fixture に実測 spread 投入)。
  中核は `test_gross_positive_but_net_negative_blocks_option_b` と
  `test_live_population_2026_09_16_is_estimand_split` (2026-09-14 の実状態を固定)。

### やらなかったこと (と理由)
- **Option B (live 昇格) を執行しない** — §2-§3 のとおり負 EV 帯への送信になる。
- **Option C (retire) も自動執行しない** — 凍結文言は「spaced EV≤0 → Option C」で
  あり、net で読めば retire 側に落ちる。しかし**どの量で読むかの変更それ自体**が
  凍結文言の修正であり、packet §6-2 は符号が割れたときは **user 再決裁**と規定する。
  自分の再解釈を根拠に retire まで自走すると、pre-reg の意味が失われる。
  なお live 露出ゼロ (§2) なので Rule 2 の緊急性 (出血停止) は無い。
- **score_gate の shadow rescue も実装しない** — forensic #2 §7 の判断を維持。
  分母を機械的に回復させると、負 EV 帯の行が spaced EV を動かす。

## 7. user 決裁事項 (forensic #2 §8 を本監査で差し替え)

1. **~~cap 10.0p を breakeven 未満に締める~~ → 選択肢として消滅** (§3)。
   残る実質的な選択は **(a) Option C = retire** か **(b) 研究前提を満たす
   執行形態の再設計** (指値・LATE 窓外への移動等 = 新規 pre-reg、Rule 1) の二択。
   **本監査の推奨は (a)**: 摩擦前提が全観測で反証され、cap による救済集合が空で、
   かつ研究エッジ自体も 38% しか再現していない (§5)。
2. **score_gate の扱い** (forensic #2 §8-2 から継続) — (a) を採る場合は
   分母回復が不要になるため、この決裁は自動的に不要化する。

**放置した場合の既定結末**: 判定器は毎日 `USER_REDECISION_ESTIMAND` を返し続け、
2026-10-28 に unique N<5 なら `RETIRE_R2_DEADLINE`。ただし N は既に 10 に到達して
いるため N<5 には戻らない ⇒ **期日による自動終結は起きない**。決裁なしでは
本 cell は「毎日 user 再決裁と表示されるだけ」の状態で滞留する。

> **✅ 決裁 (2026-09-17)**: user「推奨で進めて」により **(a) Option C = retire を採択**。
> 執行記録: [[ps1a-option-c-retire-2026-09-17]] (registry resolved 化 / 判定器
> `OPTION_C_RETIRED_USER` 恒久化 / scheduled task 無効化 / shadow rescue 残置)。
> §7-2 score_gate 決裁は規定どおり不要化。本監査はクローズ。

## 8. 参照
- forensic #2: [[sweep-zero-fire-forensic-2026-09-14]] (§6 の breakeven 7.72p 導出)
- パケット: [[sweep-reversion-ps1a-decision-packet-DRAFT]] §1.1 / §6-2 / §8 / §114
- 手順書: [[sweep-reversion-ps1a-execution-runbook-2026-07-31]]
- 摩擦 convention: [[friction-analysis]]
- 同型の教訓: MEMORY `project_ps_capture_estimand_disjoint_2026_09_09`
  (「BT 由来 EV を live 期待値に使うな」) / `feedback_audit_past_verdicts_2026_08_05`
