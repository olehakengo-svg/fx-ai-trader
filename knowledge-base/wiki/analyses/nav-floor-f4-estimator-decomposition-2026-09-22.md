---
title: F4 資金時計 burn 推定器の分解 (fit → decomposed) — 2026-09-22
type: analysis
rule: R3
status: implemented
related:
  - "[[process-meta-audit-2026-09-07]]"
  - "[[path-to-win-decision-memo-2026-09-20]]"
  - "[[prereg-trigger-registry]]"
---

# F4 資金時計 burn 推定器の分解 (fit → decomposed)

**Rule 3 (構造欠陥、code derivation)** — 検知器の estimand 是正。registry F4 の condition (`days_to_floor <= 90`) は不変。

## 1. 欠陥 (何が壊れていたか)

`tools/nav_floor_projection.py` (旧 L106–120) は CSV 行数 ≥7 で `method=fit` (直近 60 行の (日付, NAV) 線形回帰) を `days_to_floor` に書いていた。keeper (`modules/status_volume_keeper.py`) は月次出来高 target を**月初に集中して**支出する (2026-09: 26 RT、last_rt 09-14T01:01Z、`/api/demo/status.status_volume_keeper` 09-22 実測) ため、窓が 1 周期 (≈30 暦日) 未満の間、fit の slope は月内位相で単調に縮む。

実測 (`data/monitoring/nav_floor_projection.csv` 09-16〜09-21 行、NAV は 09-14 以降 275,517 で不変): 6 日で burn 推定値が半分近くに、`days_to_floor` は 180 → 334 に動いた。値の数値転記は禁止 (引用禁止値: fit 現況値)。同じ入力で推定器が振動するなら、F4 の発火日は推定器の位相で 1 ヶ月動く = 「発火しても不発火でも設計どおりと言えない」 (再評価 2026-09-22 §1 計測行 (iii))。

窓延長では直らない: 60 行 ≈ 10 週は既に 2 周期超で、振動の原因は「窓未充填 11 行 + 月内位相」 (再評価 §3 Rank 3)。`ground_capital_clock.md` L92 が示した正しい estimand = 「keeper 確定分 (target × cost/RT、決定論) + edge 実現 PnL の 30d 実測」に分解する。

## 2. 新推定器 `decomposed` (code derivation)

```
burn_decomposed = burn_keeper + burn_edge                       [JPY/日]

burn_keeper = rt_per_month × JPY_PER_RT / 30.44
  rt_per_month = round(target_usd / (volume_usd / rt_count))   telemetry (09-22: 520000/(520000/26) = 26)
                 フォールバック 26 (telemetry 不能時、basis="default")
  JPY_PER_RT   = 80  (0.8p RT spread × ¥100/pip @10,000u、wiki/index.md L149 tx 709548〜709596)
  → 26 × 80 / 30.44 = 68.3 JPY/日  (= ¥2,080/月 の日割り)

burn_edge = −edge_jpy / span
  window_start = max(min(asof − 30d, 当月1日 − 1d), 直前月 burst 終了日(14日) + 1d)
  start_row    = window_start 以降で最も古い CSV 行、span = asof − start_row.date  (span < 14d は unavailable)
  edge_jpy     = (NAV_now − NAV_start) + keeper_rt_in_window × JPY_PER_RT
  keeper_rt_in_window = 当月 rt_count (telemetry)   — start_row が当月 1 日より前なら当月 RT は全て窓内
                        = 0                          — CSV が当月内から始まり last_rt_at ≤ start_row.date ∧ 当月完了
                        それ以外 (当月 RT の前後分割が telemetry で確定できない) → unavailable
```

設計原則:
- **keeper 分は推定しない** — telemetry と broker 実測コストから決定論的に出す。月初 burst が窓のどこにあっても値は同じ。
- **edge 分の窓は直前月の burst を跨がない** — 跨ぐと窓内 keeper 支出が telemetry で確定できず、均等分布などのモデルを持ち込むことになる。窓開始を burst 終了日 (定数 `KEEPER_BURST_END_DAY=14`、2026-09 実測 last_rt 09-14) の翌日へ切り上げる。窓は 14〜31 日。
- **測れない = 0 に折り畳まない** — `edge_basis` 列に `unavailable:<理由>` を書く (monitoring-blind 教訓)。09-22 時点では CSV が 09-07 開始で窓が若く、edge は unavailable (= keeper のみ)。CSV が 30 日充填される 10-07 以降に `nav_delta:` へ移る。
- fit は消さず参考列 `burn_fit_per_day_jpy` / `days_to_floor_fit` に併記 (推定器間の乖離が毎日見える)。

## 3. 再現 (シミュレーション、09-22 時点、幅で引用)

仮定: keeper burst = 毎月 1〜9 日 3 RT/日 (26 RT)、writer 毎日成功、09-22 NAV ¥275,516.83 (heartbeat)。`tests/test_nav_floor_projection_f4.py::_simulate_first_fire` で pin。

| 経路 | fit 読み手 (旧、再評価 §1) | decomposed 読み手 (新) | floor 到達 |
|---|---|---|---|
| keeper のみ (edge 0) | 2027-01-08 | **2027-01-05** (burn 68.3/日) | 2027-04-05 |
| keeper + drift 13.7/日 (audit 82/日 相当) | 2026-12-04〜07 | **2026-12-04** (burn 82.0/日) | 2027-03-04 |

読み方: 発火日は keeper のみなら F2 (12-31) → E1 2nd look (01-06) の**後**、drift 込みなら F2 の**前**。「F4 は 12-03 に発火」を確定事実として書かない (引用禁止)。欠行パターンで数日動く。

安定性 (実 CSV 09-15〜09-21 入力、`test_decomposed_stable_within_10pct_on_real_0915_0921_but_fit_is_not`): decomposed は 7 日とも同値 (±0%)、fit は同じ入力で max/min > 1.5。

## 4. 変更点

| ファイル | 変更 |
|---|---|
| `tools/nav_floor_projection.py` | `decomposed_burn_per_day` / `keeper_rt_per_month` / `edge_burn_per_day` 追加、`build_row` で primary=decomposed、CSV 列 5 本追加 (既存 6 列は位置・意味とも不変)。`fetch_status` で keeper telemetry も取得。API 取得失敗は従来どおり exit 1 + 行を書かない |
| `.github/workflows/daily-report.yml` | nav_floor step に `id: nav-floor`、Notify で `steps.nav-floor.outcome != success` を Discord に露出 (09-22 03:13Z HTTP 全断で 1 行欠落した際、`continue-on-error: true` で cron は緑だった)。continue-on-error 自体は daily report commit を巻き添えにしないため維持 |
| `tests/test_nav_floor_projection_f4.py` | 上記性質 8 本を pin (安定性 / counterfactual / keeper 決定論 / edge 残差 / 31 日・位相カット境界 / exit 1 / workflow 露出 / registry / 再現値) |
| `prereg-trigger-registry.json` | F4 message に方法変更 + 発火日シフト追記 (condition 不変)、F3 message に D11 両基準併記 1 文、新規 deadline_info 4 件 (integrated-decision-packet-d1-d12 10-08 / e1-frozen-export-tool 10-06 / storm-guard-modify-sl 10-20 / sprint-0922-midpoint-check 10-06) |

## 5. 残る限界 (caveat)

- `KEEPER_JPY_PER_RT=80` は 09-04 時点の broker tx 実測。spread が変われば ¥70〜¥90 で動く (RT あたり ±¥10 = burn ±8.5/日)。keeper の RT 単位 pl_jpy は `/var/data/status_volume_keeper.json` にあり API 非公開 — telemetry に `realized_pl_jpy` を出せば実測化できる (別 R3)。
- `KEEPER_BURST_END_DAY=14` は 2026-09 の実測。keeper が behind_pace で月後半に RT を持ち越す月は窓が burst を跨ぎ、edge 残差が keeper 分を含んで過大になる (保守側 = 早く発火)。telemetry に前月 last_rt を残せば定数を消せる。
- edge の estimand は **broker NAV Δ** (定義 A 側)。demo `pnl_pips` (定義 B 側) ではない。F3 の D11 と同じ母集団軸の論点であり、ここでは A を採る (floor は NAV/残高で判定されるため)。
- floor の estimand: OANDA 条件は「残高 ≥¥250k」、本 CSV は NAV。建玉ゼロの間は一致。
