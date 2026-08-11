# ECG forward primary セルの emission census + estimand switch 開示 (2026-08-11)

> **rule:R3 (読むだけ)**。使用量は **counts / timestamps のみ** — [[equity-curve-shadow-gating-explore-prereg-2026-08-03]] (以下 v2) の P-10 ban (「蓄積センサス件数のみ可」) に整合。gate×outcome ジョイント量は一切未計算。**本文書は LOCKED 設計への変更を一切含まない** — first look (2026-11-06) 執行者への事実開示のみ。

## 1. Census (forward 窓 [2026-08-04, ) の 7 日目、entry_time 基準・shadow・dedup_violation≠1)

| primary セル | fwd N | 状態 |
|---|---|---|
| session_time_bias × GBP_USD | **2** (最終 exit 08-07 12:30Z) | emission 継続中だが崩壊レート (§2) |
| session_time_bias × EUR_USD | **2** (最終 exit 08-07 11:48Z) | 同上 |
| vol_momentum_scalp × GBP_USD | 0 | **打ち切り済み** — R2 demote batch 1、2026-08-05T05:51:58Z deploy ([[r2-shadow-demote-2026-08-05]]) |
| xs_momentum × GBP_USD | 11 | **打ち切り済み** — R2 demote batch 2、2026-08-10T02:28:50Z deploy ([[r2-shadow-demote-2026-08-10]]) |

- book 全体の shadow 蓄積は健全: 日次 73-123 行 (08-04〜08-11、週末除く) — 崩壊は session_time_bias 固有。
- 参考: 歴史レートは ~3 行/日/セル (328 trades / 3.5mo、GBP_USD) → 現在 ~0.3/日。

## 2. 原因: DT ctx.hour_utc 凍結 (PR #168) と session_time_bias の関係

[[dt-ctx-hour-utc-live-freeze-2026-08-09]] (123 日潜伏、live で hour≡12 / is_friday≡False、2026-08-09T01:47Z 修復 deploy) の session_time_bias への帰結:

- LONDON 窓 = **UTC 07:30–14:00 (450–840 分)** (`strategies/daytrade/session_time_bias.py` LONDON_ENTRY_START/END)。凍結 hour≡12 → total_min は常に 720–779 = **常時窓内**。
- つまり EUR_USD / GBP_USD セルのセッションゲートは **live/shadow で 123 日間事実上無効 (常時開放)** だった。v2 が warm-up に使う全履歴 (~328 trades/セル) と、forward 窓の最初の 5 営業日 (fwd N=4) は「セッションゲート無し + SELL バイアス + 他フィルタのみ」という **別 estimand** で生成されている。
- **2026-08-09T01:47Z 以降は真の estimand** (実時刻ゲート、窓 = 1 日の 27%)。修復後の観測はまだ ~1.5 営業日で真レートは未確定 (今週の London セッション数日で判明)。
- 補足: 07-30〜08-03 の先行スローダウンは凍結修復より前で、常時開放ゲート下では他フィルタ (ADX≤35 / body ratio 等) の市況依存が唯一の変動源 — バグではなく regime 由来と整合。追加調査は不要と判断 (発火ゼロではなく低下であり、修復後レートの観測が同じ問いに答える)。

## 3. ⚠️ v2 epoch 層化規則の盲点 (開示 — 設計変更ではない)

v2 §4 の epoch 境界の凍結定義は「`modules/demo_trader.py` / `modules/demo_db.py` / `modules/shadow_demote_registry.py` / `strategies/` に触れた first-parent merge commit」。**PR #168 の修正は `app.py` のみ**であり、この定義に該当しない = **08-09 の estimand switch は epoch 境界として層化されない**。

- 帰結: session_time_bias セルが仮に N≥150 に達して検定対象になった場合、08-09 前後の水準シフトは null 側に保存されず「持続性」として拾われうる (v2 の敵対的検証が殺した K1 型のリスクが、凍結ファイルリストの盲点経由で一部残存)。
- **凍結規則の変更は禁止** (v2 の no-design-change 拘束)。first look 執行者は verdict の解釈節で本開示を引用し、session_time_bias セルの結果 (もしあれば) に 08-09 境界の感度注記を付すこと — 検定自体は凍結どおり実行する。

## 4. 軌道予測と分岐 (すべて v2 の事前宣言内)

- 参加条件 = forward N≥150/セル (cutoff 2026-11-01)。必要レート ≈ 1.7/日。実測 ~0.3/日 (修復前) / 修復後は窓 27% 化でさらに低下見込み → **session_time_bias ×2 も未達がほぼ確実**。
- vol_momentum_scalp×GBP_USD (fwd 0) / xs_momentum×GBP_USD (fwd ~11 で凍結) は打ち切り済み。
- → **primary 4 セル全て N<150 = v2 §5 の UNDERPOWERED 分岐** (verdict を出さず second look cutoff 2027-01-31、1 回のみ)。現行レートでは second look も 25 週 × ~2/週 ≈ 50 ≪ 150 で未達公算 — その場合は正直クローズが v2 の帰結。**中間の設計変更・セル差替・窓延長は禁止のまま** (何もしないことが正しい)。
- m=12 は事前固定で縮めない (power 劣化として開示、[[project-r2-shadow-demote-batch-2026-08-05]] と整合)。

## 5. 機械監視 (本コミットで registry 追加)

- `ecg-stb-postfix-fire-info` (shadow_count_info): session_time_bias の修復後発火数を prereg_trigger_watch で観測。~0/週が続く場合は (a) ECG all-UNDERPOWERED の早期確定材料、(b) session_time_bias 自体の「真窓では発火しない」構造 (= 歴史実績が全て常時開放 artifact だった) の確定 → 戦略自体の R2 レビュー材料。
- 次の census (counts のみ) は 2026-08-15 前後 (London 4-5 セッション後) が目安。

## 6. 関連

- [[equity-curve-shadow-gating-explore-prereg-2026-08-03]] (SSOT、変更なし) / [[dt-ctx-hour-utc-live-freeze-2026-08-09]] / [[r2-shadow-demote-2026-08-05]] / [[r2-shadow-demote-2026-08-10]] / [[ec-gating-race-cross-audit-2026-08-03]]
- MEMORY: `project_ecg_22_forward_lock_race_2026_08_03` / `project_r2_shadow_demote_batch_2026_08_05` / `project_dt_ctx_hour_utc_live_freeze_2026_08_09`
