# R2 shadow demote 執行 2026-08-05 — 持続 CRITICAL 10 セル (rule:R2)

> **rule:R2 (Fast & Reactive — Shadow 降格)**。live 転送・tier・Kelly・env は不変更。変更 = `modules/shadow_demote_registry.py` の per-cell 追加 (emission 停止) + test pin 同期のみ。
> 起点: `raw/audits/shadow-promote-r2-alert-2026-08-05-0220.md` (CRITICAAL 12) + 08-03/08-04 系列との突合検証。
> 4原則整合: SHADOW_ALWAYS 型 bypass への R2 demotion gate 併設義務 (lesson: 無条件 emit は EV<0 で自動的にデータ汚染源化) の履行。Shadow 全体の蓄積は継続 — 止めるのは持続負 EV セルのみ。

## 1. 判定規則 (このバッチで適用した機械規則)

- **執行**: alert gate (30d、N≥30 ∧ EV<0 = CRITICAL) を **24h 以上離れた複数 alert で持続**して満たすセル。N 到達型 (WARN→CRITICAL が N 閾値横断のみで、EV が全 alert で ≤ −1.0) も持続と見なす。
- **保留**: 直近 alert のみで CRITICAL 化し、かつ直前まで EV 正だった符号 flip 型 (rolling 窓の出入りノイズと区別不能)。**次 cycle 判定** = 以後の alert で 24h+ 持続 CRITICAL なら追加バッチで執行。
- **形態**: セル単位 registry (code)。戦略単位 env var 除去は不採用 — (a) 非 CRITICAL の同戦略他セル (健全蓄積中) を巻き添え停止する、(b) KV/env トグルは pin にならない (watchdog DECREMENT 再武装バグの教訓 — 不可逆化は code で)。

## 2. 執行 10 セル (検証値: 08-03 02:36 alert → 08-05 02:20 alert)

| セル | N | EV | PF | 備考 |
|---|---|---|---|---|
| dt_sr_channel_reversal × AUD_JPY | 35→34 | −3.20→−3.36 | 0.36→0.35 | 持続 |
| engulfing_bb × EUR_USD | 71→78 | −2.07→−1.82 | 0.21→0.17 | 持続。ECG v1 検証で retired 済み系列とは別 (現役 emission) |
| london_breakout × GBP_USD | 41→53 | −2.27→−2.18 | 0.30→0.28 | 持続 |
| ma_regime_switch × USD_JPY | 45→53 | −0.85→−0.90 | 0.65→0.68 | 持続 |
| sr_break_retest × EUR_JPY | 43→37 | −3.07→−3.49 | 0.40→0.39 | 持続 |
| sr_break_retest × GBP_JPY | 27→31 | −7.02→−7.36 | 0.16→0.20 | N 到達型 (08-04 14:05 に N=30 到達、EV は全 alert −6.3〜−7.4) |
| sr_break_retest × GBP_USD | 39→37 | −1.45→−1.57 | 0.58→0.56 | 持続 |
| vol_momentum_scalp × GBP_USD | 60→53 | −0.79→−1.93 | 0.76→0.43 | 持続・悪化中。**ECG 相互作用 §4** |
| vol_momentum_scalp × USD_JPY | 75→74 | −1.67→−1.42 | 0.46→0.54 | 持続 |
| xs_momentum × EUR_USD | 45→39 | −1.60→−1.74 | 0.50→0.49 | 持続 |

## 3. 保留 2 セル (次 cycle 判定)

| セル | 軌跡 | 理由 |
|---|---|---|
| xs_momentum × GBP_USD | +1.26 (08-04 14:05) → **−0.27 (19:28)** → −0.31 (08-05 02:20)、PF 0.91 | 5 時間で符号 flip (数トレードの窓出入り)。CRITICAL 2 回だが間隔 ~7h < 24h |
| xs_momentum × USD_JPY | +0.36 (14:05) → −0.09 (19:28/02:20)、PF 0.98 | break-even knife-edge。同上 |

**次 cycle 規則 (凍結)**: 2026-08-06 02:20 UTC 以降の alert で当該セルが CRITICAL を維持していれば (= 初回 CRITICAL 19:28 から 24h+ 持続)、追加バッチで registry へ執行。EV が正へ復帰していれば保留解除。

## 4. ECG forward (#22) との相互作用 — 開示

- **vol_momentum_scalp × GBP_USD は [[equity-curve-shadow-gating-explore-prereg-2026-08-03]] の primary 4 セルの 1 つ**。本 demote の deploy 時点で shadow emission が停止し、同セルの forward 系列は打ち切りとなる (v2 pre-reg §2 の事前宣言どおり: 打ち切り理由 = R2 demote、日付 = 本 PR の deploy 日。forward N≥150 未達なら UNDERPOWERED として開示)。
- **本判定は alert gate + 持続性の機械規則のみで行い、ECG の測定 power は判定に一切使っていない** (使えば demote が実験に endogenous 化し、ECG の交絡遮断が壊れる)。xs_momentum × GBP_USD (同じく primary) の保留も同一規則の帰結であって ECG 保護ではない。
- 副次: 本コミットは `shadow_demote_registry.py` に触れるため、ECG の epoch 層化 permutation (v2 §4) の **epoch 境界として自動的に取り込まれる** (deploy 由来の水準シフトを null 側に保存する設計どおり)。
- session_time_bias ×2 (primary #1/#2) は SHADOW_PROMOTE 対象外で本件の影響なし。

## 5. 実効と検証

- 経路: `modules/demo_trader.py` の `is_shadow_demoted(entry_type, instrument)` gate (行 4301/4754) → 該当セルの shadow emit を skip + `[R2_SHADOW_DEMOTE]` ログ。
- test: `tests/test_shadow_demote_registry.py` の pin set 更新 + 保留 2 セル・健全同戦略セル (vol_momentum_scalp×EUR_USD 等) の非停止 assert 追加。
- E7/E1/E12/MoF/ECG の LOCK 対象データに非接触 (本件は emission 構成変更であり、統計計算ゼロ)。

## 6. 関連

- [[shadow-promote-r2-alert 系列]] `raw/audits/shadow-promote-r2-alert-2026-08-0{3,4,5}-*.md` (一次証拠)
- [[ec-gating-race-cross-audit-2026-08-03]] §「SSOT v2 と demote 執行形態」/ MEMORY `project_ecg_22_forward_lock_race_2026_08_03`
- 前例: 2026-07-02 USD_CHF hourly バッチ (同 registry、rule:R2)
