# R2 shadow demote 執行 2026-08-10 — batch 2 (保留 2 セル resolve + N 到達 1 セル) (rule:R2)

> **rule:R2 (Fast & Reactive — Shadow 降格)**。live 転送・tier・Kelly・env は不変更。変更 = `modules/shadow_demote_registry.py` の per-cell 追加 (emission 停止) + test pin 同期のみ。
> 起点: [[r2-shadow-demote-2026-08-05]] §3 で凍結した**次 cycle 規則**の履行 + `raw/audits/shadow-promote-r2-alert-2026-08-0{6..9},2026-08-10-*.md` (17 alert 系列)。
> 4原則整合: 原則3 (Shadow は UTC 固定で削らない) は維持 — 止めるのは持続負 EV セルのみで、同戦略の健全セル・他ペアの蓄積は継続。

## 1. 適用した規則 (08-05 で事前凍結、本 batch では一切変更していない)

08-05 doc §3 の凍結文言:

> **次 cycle 規則 (凍結)**: 2026-08-06 02:20 UTC 以降の alert で当該セルが CRITICAL を維持していれば (= 初回 CRITICAL 19:28 から 24h+ 持続)、追加バッチで registry へ執行。EV が正へ復帰していれば保留解除。

加えて 08-05 §1 の執行規則 (24h+ 離れた複数 alert での持続 CRITICAL / N 到達型は EV が全 alert で ≤ −1.0)。**判定に使ったのは alert gate の N・EV・持続性だけ** — 事後に新しい閾値やセグメントを持ち込んでいない。

## 2. 執行 3 セル

| セル | 種別 | N | EV | WR | Wilson_lo | PF | 持続 |
|---|---|---|---:|---:|---:|---:|---|
| xs_momentum × GBP_USD | 保留 resolve | 57 | −0.847 | 64.9% | 51.9% | 0.74 | 08-06 02:23 → 08-10 01:38 の **17 alert 全て CRITICAL** |
| xs_momentum × USD_JPY | 保留 resolve | 70 | −1.060 | 60.0% | 48.3% | 0.82 | 同上 17 alert 全て CRITICAL |
| engulfing_bb × GBP_USD | N 到達型 | 32 | −0.891 | 31.2% | 18.0% | 0.69 | 08-05 14:03 CRITICAL 化 → 08-10 まで 5 日連続。それ以前も 08-03 から WARN で EV −0.79〜−1.37 |

**保留 2 セルの軌跡 (08-05 doc §3 の懸念 = 符号 flip ノイズ かの決着)**:

| alert (UTC) | xs_momentum×GBP_USD EV | xs_momentum×USD_JPY EV |
|---|---:|---:|
| 08-04 14:05 | +1.26 | +0.36 |
| 08-04 19:28 | −0.27 | −0.09 |
| 08-05 02:20 | −0.31 | −0.09 |
| 08-06 02:23 | −0.696 (N=54) | −0.471 (N=58) |
| 08-06 14:02 | −0.696 | −0.121 (N=56) |
| 08-07 12:57 | −0.592 (N=51) | −0.262 (N=65) |
| 08-07 18:52 | −0.861 (N=56) | −0.700 (N=69) |
| 08-08 01:22 → 08-10 01:38 | −0.847 (N=57) | −1.060 (N=70) |

→ **符号は一度も正へ戻らず、EV は単調に悪化** (GBP_USD −0.27→−0.85 / USD_JPY −0.09→−1.06)。保留解除条件 (EV 正復帰) は成立せず、執行条件が成立。

**値の凍結 (08-08 01:22 以降ずっと同値) は weekend であって feed 断ではない** — 2026-08-08 は土曜、08-09 は日曜。判定に効いている「独立な新規観測を伴う持続」は 08-06 02:23 → 08-08 01:22 の **約 47h** 区間で確保されている (この間 N は 54→57 / 58→70 と増加)。同 alert 系列で 08-05 執行済みセルの N は減衰しており (vol_momentum_scalp×GBP_USD 53→46 等)、pipeline も demote 実効も生きている。

## 3. 統計的性格の分離 (誤読防止)

- **xs_momentum 2 セルは「高 WR × 負 EV」型** (WR 60-65%、Wilson_lo 48-52% はどちらも GBP_USD BEV_WR 37.9% / USD_JPY 34.4% を上回る)。**WR は勝っているのに EV が負** = v2.3 が中核 KPI に据えた payoff 非対称 ([[payoff-asymmetry-diagnosis-2026-07-07]] payoff 0.274) の署名であり、勝率の問題ではない。R2 は shadow 蓄積の出血を止めるだけで、この型のセルの「エントリーは効いているかもしれない」可能性を否定していない — 再評価は R1 (365d BT + Bonferroni + pre-reg) でのみ可。
- **engulfing_bb × GBP_USD は素直な劣化型** (WR 31.2%、Wilson_lo 18.0% ≪ BEV_WR 37.9%)。上側 CI 48.6% でも BEV に届かない。
- ⚠️ **`close_reason="SL_HIT"` 起点の解釈は本判定に一切使っていない** — MEMORY `project_sl_hit_label_collision_2026_08_07` のとおり SL_HIT は BE/トレール利確 exit を含み (実測 N=3308 の 54.2% が WIN)、本 registry 内の 2026-06-12 コメント (fib_reversal 「SL_HIT 56.2%」) は引用前に再検討が必要な旧記述である。本 batch の根拠は `pnl_pips` 由来の N/EV/WR/PF のみ。

## 4. 形態を per-cell に据え置く理由 と 既知の残存リスク (開示)

08-05 と同じく **セル単位 registry (code)** で執行する。戦略単位 env var 除去は不採用 (健全セルの巻き添え / KV・env トグルは pin にならない — watchdog DECREMENT 再武装バグの教訓)。

ただし本 batch により:

- **engulfing_bb** は現在 emission のある全セル (EUR_USD / GBP_USD / USD_JPY / USD_CHF) が demote 済み
- **xs_momentum** も同様に全セル (EUR_USD / GBP_USD / USD_JPY) が demote 済み

となり、**de facto の戦略停止**になる。それでも `SHADOW_RETIRED_STRATEGIES` (= 将来の新ペアも含めて恒久ブロック) には**入れない**: あの集合は edge-factor audit (N≥450 + メカニズム判定) を根拠に置く枠であり、本 batch の根拠は alert gate の機械規則にすぎないため、同じ強度の主張はできない。

→ **残存リスク (既知・受容)**: 新モードが新ペアを追加すると当該戦略の emission が再開する (ema_trend_scalp × USD_CHF で実際に起きた漏れと同型)。監視は R2 alert 系列がそのまま担う (新ペアが N≥10 で負に振れれば WARN として再浮上する)。回帰テスト `test_engulfing_bb_and_xs_momentum_stay_cell_level_not_retired` にこの意図を pin した。

**非対象 (巻き添え確認済み)**: `xs_momentum_rsi × USD_JPY` は **別 entry_type** で `_PAIR_PROMOTED` の live セル。registry key は (entry_type, instrument) なので本 demote の影響を受けない (実測確認: `is_shadow_demoted("xs_momentum_rsi","USD_JPY") == False`)。`_is_live_tier_exempt` 経路も無関係 — 執行 3 セルはいずれも `_ELITE_LIVE` (空集合) にも `_PAIR_PROMOTED` にも属さない (xs_momentum×GBP_USD/EUR_USD は 2026-05-29 に `_PAIR_DEMOTED` 済み [[xs-momentum-pair-demote-2026-05-29]])。

## 5. ECG forward (#22) との相互作用 — 開示

- **xs_momentum × GBP_USD は [[equity-curve-shadow-gating-explore-prereg-2026-08-03]] §2 の primary 4 セルの 1 つ**。本 demote の deploy 時点で shadow emission が停止し、同セルの forward 系列は**打ち切り**となる (v2 pre-reg §2 の事前宣言どおり: 打ち切り理由 = R2 demote、日付 = 本 PR の deploy 日。forward N≥150 未達なら UNDERPOWERED として開示、**m = 4 cells × 3 K = 12 は事前固定のまま縮めない**)。
- これで primary 4 セル中 **2 セルが打ち切り** (vol_momentum_scalp×GBP_USD = 08-05、xs_momentum×GBP_USD = 本件)。**残り 2 セル (session_time_bias × GBP_USD / EUR_USD) は SHADOW_PROMOTE 対象外で本件の影響なし**、蓄積継続。first look 2026-11-06 時点で verdict に参加できるのは実質この 2 セルになる見込み — これは pre-reg が事前に想定した劣化経路であり、m を縮めない以上 power 低下として素直に開示される。
- **本判定は alert gate + 持続性の機械規則のみで行い、ECG の測定 power は判定に一切使っていない** (使えば demote が実験に endogenous 化し、交絡遮断が壊れる)。**P-10 型凍結を遵守 — gate×outcome のジョイント計算は本 batch で一切行っていない。**
- 副次: 本コミットは `shadow_demote_registry.py` に触れるため、ECG の epoch 層化 permutation (v2 §4) の **epoch 境界として自動的に取り込まれる** (deploy 由来の水準シフトを null 側に保存する設計どおり)。

## 6. 実効と検証

- 経路: `modules/demo_trader.py` の `is_shadow_demoted(entry_type, instrument)` gate (行 4313 / 4766) → 該当セルの shadow emit を skip + `[R2_SHADOW_DEMOTE]` ログ。
- test: `tests/test_shadow_demote_registry.py` — expected set 更新 (26→29 セル)、保留 assert を `test_r2_batch_2026_08_10_deferred_cells_resolved_to_demote` へ反転、leak-check を現役セル (dt_sr_channel_reversal×USD_JPY / three_bar_reversal×USD_JPY) に差し替え、§4 の per-cell 据え置き意図を pin。
- E7 / E1 / E12 / MoF / ECG の LOCK 対象データに非接触 (本件は emission 構成変更であり、統計計算ゼロ)。

## 7. 関連

- [[r2-shadow-demote-2026-08-05]] (batch 1、本件の次 cycle 規則の出典)
- [[shadow-promote-r2-alert 系列]] `raw/audits/shadow-promote-r2-alert-2026-08-0{3..9}-*.md` / `-2026-08-10-0138.md` (一次証拠)
- [[equity-curve-shadow-gating-explore-prereg-2026-08-03]] §2 (セル途中退場の事前宣言)
- [[payoff-asymmetry-diagnosis-2026-07-07]] (高WR×負EV 型の解釈)
- [[xs-momentum-pair-demote-2026-05-29]] (live tier 側の先行 demote)
- MEMORY `project_r2_shadow_demote_batch_2026_08_05` / `project_sl_hit_label_collision_2026_08_07` / `project_ecg_22_forward_lock_race_2026_08_03`
