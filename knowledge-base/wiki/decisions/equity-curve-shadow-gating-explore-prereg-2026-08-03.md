# Pre-registration — equity_curve_shadow_gating explore (台帳 #22, wave-6 EA-b) — 2026-08-03

> **rule:R3 (counterfactual 診断)**。live/shadow 一切不変更。live gate 化は本 explore と独立の R1 手続き + user 最終承認。
> **状態: 🔒 LOCKED (凍結コミット後に測定、コミット hash は台帳へ追記)**
> **由来**: [[ea-landscape-sweep-2026-07-31]] §4.2 (31-agent EA 調査の敵対的検証 GO、score 55)。
> **関連**: [[hypothesis-catalog-2026-07-24]] #22 / 4原則#3 LIVE 側 winning-location ドクトリン

## 1. 仮説と estimand

- **H1**: セル (mode×entry_type×instrument) の shadow closed P&L に短期 regime 持続性があり、「直近 K トレード合計 pips > 0」条件下の平均 pips が、条件不成立下の平均を上回る。
- **H0**: 系列独立 (uplift = 0)。
- **estimand**: `contrast(c,K) = mean(pnl | state>0) − mean(pnl | state≤0)`。シグナル族ではなく露出配分層 — 市場データ・LOCKED データ (E1/E7/E12/MoF) に一切触れない。
- **事前確率は mixed〜negative** (戦略リターンの系列相関は通常≈0)。本 explore は低 prior・低コスト枠 — 正直な power 開示は §6。

## 2. データ (凍結)

- **ソース**: 本番スナップショット `knowledge-base/raw/snapshots/render-demo-trades-20260803.db` (2026-08-03 取得、15,009 行、`tools/render_trades_snapshot.py` 正規経路)。**sha256 = `b6253dcc430b606ca2688001621e881411e0836d3df45cae364ed2e7d85bde0d`** (ファイル実体は 25MB/gitignored のためローカル保持 — ハーネスが照合し、不一致なら実行拒否)。
- **行フィルタ**: `status='CLOSED'` AND `(oanda_trade_id IS NULL OR oanda_trade_id='')` (= shadow、live 行は摩擦混入のため除外) AND `COALESCE(dedup_violation,0)=0`。
- **窓**: 全スパン 2026-04-02〜2026-08-02 (entry_time UTC)。スパン 4 ヶ月 = explore/OOS 時分割は不能 → **本検証は explore 単窓。OOS は forward のみ** (§8)。
- **dedup 追加規則**: 同一セル・同方向・entry_time 差 60 秒以内の行は最初の 1 行のみ採用 (engine 再構築 dedup 死の残滓対策)。
- **対象セル (N≥200 floor、件数センサスのみで確定 — outcome 非接触)**: 以下 10 セルで凍結。

| # | cell (mode / entry_type / instrument) | N | 状態 |
|---|---|---|---|
| 1 | daytrade_gbpusd / session_time_bias / GBP_USD | 330 | active |
| 2 | scalp / ema_trend_scalp / USD_JPY | 282 | retired 05-07 |
| 3 | daytrade_eur / session_time_bias / EUR_USD | 276 | active |
| 4 | scalp_5m_gbp / vol_momentum_scalp / GBP_USD | 242 | active |
| 5 | scalp_5m / ema_trend_scalp / USD_JPY | 237 | retired 05-08 |
| 6 | scalp_eur / ema_trend_scalp / EUR_USD | 216 | retired 05-07 |
| 7 | scalp_5m_gbp / ema_trend_scalp / GBP_USD | 212 | retired 05-08 |
| 8 | daytrade_gbpusd / xs_momentum / GBP_USD | 201 | active |
| 9 | scalp / bb_rsi_reversion / USD_JPY | 200 | retired 05-07 |
| 10 | scalp_5m_gbp / sr_channel_reversal / GBP_USD | 200 | retired 06-16 |

retired セル (shadow 引退/置換で系列が窓中で終了) も履歴として有効 — estimand は系列内持続性であり継続性を要求しない。ただし **live gate R1 提案の根拠にできるのは active セルの PASS + forward 検証のみ** (§8)。

## 3. Gate 定義 (凍結)

- **K ∈ {5, 10, 20}** の 3 点のみ。閾値 = 0 固定 (rolling sum > 0)。**グリッド最適化禁止**。
- **因果的 state**: トレード t の state = 「`exit_time < entry_time(t)` を満たす同セル closed trades のうち exit_time 降順 K 件」の pnl_pips 合計。**t 自身と、t の entry 時点で未決済のトレードは含まない** (lookahead ゼロ)。K 件未満の初期トレードは評価対象外。
- pnl は記録された `pnl_pips` (gross)。contrast は定数摩擦に不変。経済ゲート (§5) のみ net 換算 (per-pair RT: USD_JPY 2.14 / EUR_USD 2.00 / GBP_USD 4.53 / EUR_JPY 2.50)。

## 4. 統計 (凍結)

- **primary**: contrast(c,K) の **片側検定 (uplift > 0)**。有意でも符号が負なら FAIL — **事後の反持続 (mean-reversion) 主張は禁止** (holiday レグ c 前例)。
- **null**: within-cell permutation — トレードの時刻骨格 (entry/exit) を固定し pnl 値のみを 10,000 回シャッフル → state/gate を再計算 → contrast の null 分布。p の床は 1/(n_perm+1)。
- **多重性**: Bonferroni **m = 10 cells × 3 K = 30**、α = 0.05/30 ≈ 0.00167。
- **robustness gates (PASS セルに必須、全て符号維持判定)**:
  - (i) unique-spaced 系列 (entry が前採用トレードの exit より前の行を落とす) で contrast > 0
  - (ii) LOYO-week: 週単位 leave-one-out 全再計算で contrast > 0 が (総週数 − 3) 以上
  - (iii) **coverage gate**: gate_on 率 ∈ [0.25, 0.75] (退化ゲート排除)

## 5. Verdict 規則 (凍結)

- **統計 PASS** ⟺ ≥1 (cell,K): p < α AND contrast > 0 AND robustness (i)(ii)(iii) 全通過。
- **経済 PASS (live-R1 経路の資格)** ⟺ 統計 PASS セルで `mean(pnl_net | gate_on) > 0`。統計 PASS のみで経済 FAIL の場合は「持続性は実在するが gated book が負」として記録 (live 提案不可)。
- **FAIL クローズ** ⟺ 統計 PASS ゼロ。**同型再試行禁止 = 自戦略 closed P&L の rolling-K 合計閾値ゲート (shadow 書内 counterfactual) 全変種**。再入場は §7 の時限条件のみ。
- knife-edge 検査: 最小 p が α の ±20% 圏内の場合、シード非依存の厳密化 (n_perm 10 万) を 1 回だけ実施し、その結果を最終とする。

## 6. Power の正直な開示

α=0.00167 (z≈2.94)、N=200/gate 50-50 分割で検出可能効果 ≈ **0.42σ (トレード pips SD の 4 割)** — 小さな持続性は検出不能。本 explore の PASS は「強い持続性の存在」のみを主張でき、FAIL は「強い持続性の不在」しか意味しない (小効果の棄却ではない)。これは低 prior・低コスト枠として設計時に受容済み。

## 7. 交絡遮断と限界 (凍結)

- **shadow-only 系列**のため watchdog/R2 の live 転送停止は系列を汚染しない (shadow emission は継続)。shadow 引退セルは系列が自然終了するのみ。
- **系統的交絡として残るもの (正直に)**: (a) 窓中のエンジン/フィルタ変更による regime 非定常 — estimand は「記録された emitted 系列」の持続性であり、gate 適用先も同一プロセスのため方向的バイアスにはならないが、PASS の外挿性を弱める。(b) BE/Trail による WR 歪み — 系列の一部だが production gate も同じ歪んだ系列を見るため整合。(c) 同時保有トレードの機械的相関 — robustness (i) で遮断。
- **既存 R2 損失停止 / watchdog stage 減衰との差分**: 既存は片側 (損失時に落とす)・ad hoc・非対称。本仮説は対称 (勝ち時だけ通す)・事前登録・counterfactual 測定。live gate 化する場合は既存 watchdog との二重ゲート相互作用を R1 パケットで設計する (本 explore の範囲外)。
- **再入場条件 (時限)**: FAIL 時、対象セル群の総 eligible shadow N が本測定の 2 倍 (≥ 4,600/セル群合計比) に到達した時点で、新 pre-reg + 敵対的検証を条件に 1 回だけ再試行可 (データ倍増は re-dress ではない)。

## 8. PASS 時の forward OOS (事前宣言)

統計+経済 PASS の場合: **forward second look = PASS セル (active のみ) の 2026-08-04 以降 90 日 shadow forward** を registry (`prereg-trigger-registry.json`) に登録してから結果を KB 反映する。forward で符号再現するまで live gate R1 は起案しない。retired セルのみ PASS の場合は「機構は実在したが適用先なし」でクローズ。

## 9. 実装

`tools/equity_curve_gating_explore.py` (LOCK コミット同梱)。スナップショット read-only、乱数 seed 固定 (=20260803)、出力 `knowledge-base/raw/bt-results/ecg_explore-2026-08-03.json` + `reports/ecg-explore-2026-08-03.md`。

## 10. 敵対的検証

LOCK 前に 3 レンズ (統計的妥当性 / lookahead・データ衛生 / 交絡・本番セマンティクス) の敵対的検証を実施し、指摘と解決を本節に追記してから凍結する。

<!-- 敵対的検証の結果をここに追記 -->
