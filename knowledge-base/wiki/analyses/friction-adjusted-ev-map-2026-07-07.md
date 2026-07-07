# 摩擦調整 EV マップ — 稼働 entry_type × pair × dir (WS-Diag T4, 2026-07-07)

**Status**: 確定 (read-only 集計、estimand 確定済み)。rule:R3 (診断/マップ、live 変更なし)。
**目的**: roadmap v2.3 ボトルネック「正の摩擦調整 EV セルの不在」を全 entry_type 網羅で定量化 (M6 母集団確定)。
**データ**: Render 本番 snapshot `render-trades-20260707b.db` (demo_trades 12,372 行、max entry 2026-07-07T04:24)。
**関連**: [[roadmap-v2.3-payoff-friction-repair]] WS-Diag T4 / [[payoff-asymmetry-diagnosis-2026-07-07]] / [[friction-analysis]] / [[exit-repair-tp-sl-prereg-2026-07-07]] / MEMORY `project_be_trail_inflates_python_bt_wr` / `project_engine_reconstruction_live_dedup_dead`
**再現**: `tools/t4_friction_ev_map.py` / 生データ `raw/bt-results/t4_friction_ev_map.json`

## 1. TL;DR

稼働 39 entry_type (post-cutoff shadow, deduped N≥30) を **gross EV − per-pair 理論 RT friction** で網羅評価。

- **正の摩擦調整 EV = 1/39 entry_type、3/89 セル (N≥30) のみ。** shadow は BE/Trail 水増し込み (楽観側) にもかかわらずこの少なさ。
- **唯一の net+ entry_type = vix_carry_unwind (shadow net +1.86p) は live で負** (live net −1.22p〜−1.90p)。shadow-live gap = BE/Trail 水増しそのもの。→ **shadow net+ は live viability を意味しない。**
- 結論: **現行シグナル母集団に「live で信頼できる正の摩擦調整 EV セル」は存在しない** (楽観 shadow ですら不在)。v2.3 ボトルネック定義を定量的に裏付け、exit-repair (WS-Diag T2) か signal 張り替え (WS3) の構造是正が不可避であることを確認。

## 2. Estimand の確定 (shadow dedup キー — 未照合問題の解消)

engine 毎tick再構築で per-bar dedup が live デッド ([[project_engine_reconstruction_live_dedup_dead]]) のため、shadow には同一バー再 emit が混入し raw カウントを inflate する。T8 forensic #3 の estimand (order 層 dedup key) と揃えるため、**dedup key = `(entry_type, instrument, direction, bar_ts)`** (bar_ts = entry_time を row の tf バーで floor) で dedup した母集団を評価対象とする。

| 窓 | shadow raw | deduped (estimand) | drop | 備考 |
|---|---|---|---|---|
| all post-cutoff (≥2026-04-16) | 10,648 | 8,667 | 1,981 (18.6%) | 本マップの母集団 |
| 診断窓 (06-07〜07-08) | 3,332 | 2,686 | 646 (19.4%) | draft の「3,281 vs 2,466」に対応する slice — 再emit inflation ~19% で符合 |
| draft 窓 (06-06〜07-07) | 3,313 | 2,669 | 644 (19.4%) | |

**「raw 3,281 vs 2,466 未照合」= 診断窓 shadow の再emit inflation (~19%)** と確定。`dedup_violation=1` フラグ (engine 側、全体 2,395) は estimand-key 重複 (1,981) と部分的にしか一致せず (フラグは runaway のみ捕捉、通常の poll 再emit を取りこぼす) — **estimand は bar_ts dedup を正とする**。

## 3. entry_type レベル 摩擦調整 EV (deduped shadow, N≥30, net EV 降順・抜粋)

friction = per-pair 理論 RT ([[friction-analysis]]: USD_JPY 2.14 / EUR_USD 2.00 / GBP_USD 4.53 / EUR_JPY 2.50 / 他 3.0)。net EV = gross − friction。

| entry_type | N | WR% | gross EV | **net EV** | sum gross | 判定 |
|---|---|---|---|---|---|---|
| vix_carry_unwind | 58 | 41.4 | +4.00 | **+1.86** | +232 | 唯一 net+ (但し live 負、§4) |
| orb_trap | 39 | 46.2 | +2.06 | −0.94 | +80 | gross+ / net− |
| vol_spike_mr | 42 | 57.1 | +1.06 | −1.08 | +44 | |
| dt_bb_rsi_mr | 124 | 45.2 | +0.93 | −2.29 | +116 | T10 KILL 済 |
| bb_squeeze_breakout | 105 | 20.0 | +0.29 | −2.20 | +30 | PAIR_PROMOTED |
| … (残り 34 type すべて net−) | | | | −2.8〜−8.3 | | |
| trendline_sweep | 114 | 48.2 | −3.29 | −6.51 | −375 | ELITE_LIVE だが shadow net 深赤 |
| sr_fib_confluence | 411 | 28.7 | −3.00 | −6.10 | −1232 | |
| session_time_bias | 543 | 37.0 | −2.14 | −5.50 | −1161 | |

**net-positive entry_types: 1/39 (N≥30)。** gross-positive でも friction 控除で 4/39 → 1/39 に落ちる (摩擦の水準効果、payoff 診断 §5 と整合)。

## 4. cell レベル (entry_type × pair × dir) net EV>0 (N≥30) — 全 3 セル

| cell | N | WR% | gross EV | net EV | Wilson_lo | live 対照 |
|---|---|---|---|---|---|---|
| vix_carry_unwind×USD_JPY×SELL | 58 | 41.4 | +4.00 | **+1.86** | 0.296 | **live net −1.22 (all) / −1.90 (30d)** ← 乖離 |
| ob_retest×USD_JPY×BUY | 31 | 58.1 | +3.14 | +0.99 | 0.408 | live N 不足・未検証 |
| dt_sr_channel_reversal×USD_JPY×BUY | 35 | 54.3 | +2.22 | +0.08 | 0.382 | marginal、live 未検証 |

**crux — shadow net+ は live に伝わらない**: 最良の net+ セル vix_carry_unwind×USD_JPY×SELL は shadow net +1.86p だが、同セルの **live** は N=20 で gross +0.92 / net **−1.22p** (all post-cutoff)、直近 30d では EV **−1.90p** ([[payoff-asymmetry-diagnosis-2026-07-07]] §7 の R2 demote 候補)。gap = BE/Trail 水増し (shadow paper exit が live 執行より capture 大) と同一機序。ob_retest / dt_sr_channel の 2 セルも N=31/35 と小さく live 未検証。→ **どの shadow net+ セルも live promote 根拠にならない** ([[project_be_trail_inflates_python_bt_wr]] を cell 単位で再確認)。

## 5. 結論とロードマップへの含意

1. **ボトルネック確定の裏付け**: 楽観 (BE/Trail 水増し) shadow ですら net+ が 1/39 type・3/89 cell、かつその唯一候補は live 負。現行シグナル母集団に「live で信頼できる正の摩擦調整 EV セル」は不在。
2. **exit-repair (WS-Diag T2) の必要性**: 勝ち側 capture を回復すれば shadow の gross+ (orb_trap / vol_spike_mr / dt_bb_rsi_mr 等の marginal 群) が net+ に転じうるか、が exit-repair grid BT ([[exit-repair-tp-sl-prereg-2026-07-07]]) の検証対象。FAIL なら §5-3 へ。
3. **signal 張り替え (WS3) の優先母集団**: 「高 gross WR × 深い net−」群 (trendline_sweep WR48/net−6.5、gbp_deep_pullback WR54/net−6.6、sr_anti_hunt_bounce) = エントリーは効くが decision/friction で殺される典型。exit-repair が全滅なら WS3 の第一候補。
4. **shadow EV を promote 根拠にしない規律の再確認**: 本マップは screen であり promote 判定ではない。net+ shadow セルも live/cell-conditional BT の三段防御を経ずに live 化しない ([[lesson: Cell-level 統計だけで Live promote するな]])。

## 6. Caveats

1. **shadow gross EV は BE/Trail 水増し込み (楽観)** — §4 の live 対照が示すとおり live では大きく劣化。net EV は上限側の推定。
2. friction は per-pair 理論 RT (旧レジーム計測、BEV 前提未更新)。実測フロア (1.30/t) 採用なら net は約 +0.7〜3.2p 改善方向だが、順位と「net+ 稀少」の結論は不変。
3. dedup は bar_ts floor による近似 (tf 列依存)。tf 欠損行は 15m 扱い。
4. N≥30 足切りで小 N セルは非掲載 (方向性示唆のみで有意性主張なし、Bonferroni 未補正)。
5. shadow に対称摩擦 (spread) は未負担のため、gross は真の「摩擦ゼロ」paper 値。net は理論 friction 一律控除であり、セル別の実 spread 差は無視。

## 7. Addendum (2026-07-07 引き継ぎセッション — 独立再集計との突合)

引き継ぎセッションが新規 snapshot (12,415 行、07-07T12:43Z fetch) で独立に同型マップを再導出し、以下 2 点を追補する (結論 §1/§5 は完全一致 — 診断窓セル粒度でも理論摩擦後 EV≥0 は vol_spike_mr×USD_JPY×BUY の +0.001 ただ 1 つ = break-even):

1. **estimand は bar_ts dedup 単独より `dedup_violation=0 ∪ bar_ts dedup` が強い**。診断窓 (06-07〜07-08) の実測: raw 3,371 のうち `dedup_violation=1` は 798 行で、これを除外した 2,573 行に bar_ts dedup を追加適用しても**追加除去ゼロ** — すなわち診断窓では bar_ts 重複 ⊆ flag 済み行であり、flag は bar_ts が取れない cross-bar runaway (~150 行) も捕捉している。§2 の bar_ts 単独 estimand (2,686) はこの ~150 行の既知汚染を母集団に残す。全 post-cutoff では逆に flag が poll 再emit を取りこぼす (§2 のとおり) ため、**以後の shadow 集計は両者の union 除外を標準とする**。
2. **実測摩擦列の初回集計** (PR #53 輸出後初、clean live 30d N=94): spread_at_entry 平均 1.16p / spread_at_exit 平均 1.47p / slippage_pips 平均 0.56p。exit spread > entry spread は server 側クローズの流動性劣化と整合。実測フロア 1.30/t ([[payoff-asymmetry-diagnosis-2026-07-07]] §5) は保守側で妥当 — [[exit-repair-tp-sl-prereg-2026-07-07]] §7 の感度分析はこの列で更新可能 (エンドポイント不変)。
