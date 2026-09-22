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
  rt_per_month = ceil(target_usd / (volume_usd / rt_count))    telemetry (09-22: 520000/(520000/26) = 26)
                 ceil = worker の stop rule (毎 RT 前に volume>=target を見て止まる、届かなければ丸ごと 1 RT) と一致。
                 round だと 8,000u (520000/16000 = 32.5) で 32 と 1 RT 過小 (PR #285 review P2、2 巡目)
                 フォールバック 26 (telemetry 不能時、basis="default")
                 = 0 (enabled:false = STATUS_VOLUME_KEEPER_ENABLE=0 の payload、または target_usd==0 明示。basis="disabled"/"target_zero")
                 keeper 計画 0 ∧ edge unavailable の行は burn 0 → sentinel に折り畳まず fit を primary に (method="fit_fallback")
  JPY_PER_RT   = 80 × units / 10,000   (¥80 = 0.8p RT spread × ¥100/pip @10,000u、wiki/index.md L149 tx 709548〜709596)
                 units = volume_usd / rt_count / 2   telemetry (get_status は units を出さないが出来高/RT が運ぶ)
                 フォールバック 10,000u (telemetry 不能時、basis="default")
  → 26 × 80 / 30.44 = 68.3 JPY/日  (= ¥2,080/月 の日割り)。SVK_UNITS=20k なら 13 RT × ¥160、5k なら 52 × ¥40 — 総額不変

burn_edge = −edge_jpy / span
  window_start = max(min(asof − 30d, 当月1日 − 1d), 直前月 burst 終了日(14日) + 1d)
  start_row    = window_start 以降で最も古い CSV 行、span = asof − start_row.date  (span < 14d は unavailable)
  edge_jpy     = (NAV_now − NAV_start) + keeper_rt_in_window × JPY_PER_RT
  keeper_rt_in_window = 当月 rt_count (telemetry)   — start_row が当月 1 日より前なら当月 RT は全て窓内
                        = 0                          — CSV が当月内から始まり当月 rt_count == 0 (回収 RT も rt_count に乗る)
                        それ以外 (当月 RT の前後分割が telemetry で確定できない) → unavailable
                        ※ last_rt_at ≤ start_row.date では分割しない — _recover_stale_trades は rt_count を増やしても
                          last_rt_at を更新しない (status_volume_keeper.py L321-322)。PR #285 review P2、3 巡目
  前提: telemetry.month == asof の月。違えば (UTC 月替わり 00:00 cron、keeper loop の _roll_counters 前)
        rt_count は前月分なので unavailable:keeper_month_mismatch — 同日 06:00 run が当月 telemetry で上書き
```

設計原則:
- **keeper 分は推定しない** — telemetry と broker 実測コストから決定論的に出す。月初 burst が窓のどこにあっても値は同じ。
- **edge 分の窓は直前月の burst を跨がない** — 跨ぐと窓内 keeper 支出が telemetry で確定できず、均等分布などのモデルを持ち込むことになる。窓開始を burst 終了日 (定数 `KEEPER_BURST_END_DAY=14`、2026-09 実測 last_rt 09-14) の翌日へ切り上げる。窓は 14〜31 日。
- **keeper 単価は設定 units で線形スケール** — `SVK_UNITS` は 20k まで変えられる (`modules/status_volume_keeper.py` L70)。単価を ¥80 固定にすると 20k で keeper burn が半減 (13 RT × ¥80 = ¥1,040/月) し設定変更で F4 トリガが動く。units は telemetry の出来高/RT から導く (PR #285 review P2、1 巡目)。
- **前月 telemetry を当月支出として差し引かない** — `month` 不一致 (または欠落) は edge unavailable。差し引くと前月 26 RT × ¥80 = ¥2,080 が edge 残差に乗り、keeper burn を丸ごと打ち消して committed row の burn が keeper のみ相当 → 0 近傍に落ちる (PR #285 review P2、1 巡目)。
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
| `tools/nav_floor_projection.py` | `decomposed_burn_per_day` / `keeper_rt_per_month` / `keeper_units` / `keeper_jpy_per_rt` / `keeper_month_mismatch` / `edge_burn_per_day` 追加、`build_row` で primary=decomposed、CSV 列 5 本追加 (既存 6 列は位置・意味とも不変)。`fetch_status` で keeper telemetry も取得。API 取得失敗は従来どおり exit 1 + 行を書かない |
| `.github/workflows/daily-report.yml` | nav_floor step に `id: nav-floor`、Notify で `steps.nav-floor.outcome != success` を Discord に露出 (09-22 03:13Z HTTP 全断で 1 行欠落した際、`continue-on-error: true` で cron は緑だった)。continue-on-error 自体は daily report commit を巻き添えにしないため維持 |
| `tests/test_nav_floor_projection_f4.py` | 上記性質 8 本を pin (安定性 / counterfactual / keeper 決定論 / edge 残差 / 31 日・位相カット境界 / exit 1 / workflow 露出 / registry / 再現値) + review P2 ×2 の既知 NG 入力 pin (20k/5k units で総額不変・¥80 固定なら半減 / 前月 month で edge unavailable・month を無視すると edge<0 で keeper を打ち消す) |
| `prereg-trigger-registry.json` | F4 message に方法変更 + 発火日シフト追記 (condition 不変)、F3 message に D11 両基準併記 1 文、新規 deadline_info 4 件 (integrated-decision-packet-d1-d12 10-08 / e1-frozen-export-tool 10-06 / storm-guard-modify-sl 10-20 / sprint-0922-midpoint-check 10-06) |

## 5. 残る限界 (caveat)

- `KEEPER_JPY_PER_RT=80` は 09-04 時点の @10,000u broker tx 実測 (units で線形スケール済み)。spread が変われば ¥70〜¥90 で動く (RT あたり ±¥10 = burn ±8.5/日)。keeper の RT 単位 pl_jpy は `/var/data/status_volume_keeper.json` にあり API 非公開 — telemetry に `realized_pl_jpy` を出せば実測化できる (別 R3)。
- `KEEPER_BURST_END_DAY=14` は 2026-09 の実測。keeper が behind_pace で月後半に RT を持ち越す月は窓が burst を跨ぎ、edge 残差が keeper 分を含んで過大になる (保守側 = 早く発火)。telemetry に前月 last_rt を残せば定数を消せる。
- edge の estimand は **broker NAV Δ** (定義 A 側)。demo `pnl_pips` (定義 B 側) ではない。F3 の D11 と同じ母集団軸の論点であり、ここでは A を採る (floor は NAV/残高で判定されるため)。
- floor の estimand: OANDA 条件は「残高 ≥¥250k」、本 CSV は NAV。建玉ゼロの間は一致。
- month 一致チェックは keeper loop の poll (300s) が月替わりを跨いでから有効になる。00:00 cron の行は edge unavailable (keeper のみ) で書かれ、06:00 run で上書きされる。ただし 1 日が土日の月は 00:00/06:00 とも走らず、翌営業日の初回 run で当月 telemetry が読める (冪等上書きに依存しない)。

## 6. レビュー消化記録 (PR #285)

| 巡 | 指摘 | 判定 | 対応 |
|---|---|---|---|
| 1 | P2: keeper 単価 ¥80 が 10k 固定で `SVK_UNITS` 変更に追従しない (20k で ¥1,040/月 に半減) | 実欠陥 | `keeper_units` / `keeper_jpy_per_rt` (出来高/RT ÷ 2 → 線形スケール)、edge 差し引きも同単価 |
| 1 | P2: 月替わり直後に前月 `rt_count` を当月支出として差し引き keeper burn を打ち消す | 実欠陥 | `keeper_month_mismatch` で `month` ≠ asof 月 (または欠落) は edge unavailable (fail-closed)。RT 数 (比) は前月 telemetry でも有効なので keeper 分は落とさない |
| 4 | P2: `enabled:false` (keeper 停止) の payload でも default 26 RT × ¥80 = ¥68.3/日 を burn に乗せ、走らない keeper で F4 が早く発火する | 実欠陥 | `keeper_disabled` → 計画 RT 0 (basis disabled)、`target_usd==0` 明示も 0。停止中は counters/month が無いので edge は `unavailable:keeper_disabled` (窓途中の停止で窓内 RT が残り得る)。両成分未測定の行は burn 0 = sentinel 99999 (「減っていない」) に折り畳まず fit を primary に `method=fit_fallback` で露出 |
| 3 | P2: CSV が若い窓で「last_rt_at ≤ 窓開始 ∧ 当月完了 → keeper_rt_in_window=0」は、回収 RT (`_recover_stale_trades`、last_rt_at 非更新) の損失を edge に転嫁し days_to_floor を短くする | 実欠陥 | 分岐を削除。当月 rt_count == 0 のみ 0 と確定、他は `unavailable:keeper_split_unknown` (fail-closed)。09-22 時点の実経路 (CSV 09-07 開始、10-01 以降は窓開始 < 当月 1 日) では値は動かない |
| 2 | P2: `round(target/per_rt)` は worker の stop rule (ceil) と不一致 — 8,000u で 32 vs 実行 33、keeper burn 過小 + young-window 分岐で「当月完了」を誤判定 | 実欠陥 | `math.ceil` に変更 (割り切れる 10k/20k は不変)。stop rule の直接シミュレーションで pin |
