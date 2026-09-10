# Pre-registration — equity_curve_shadow_gating **forward** (台帳 #22, wave-6 EA-b) — 2026-08-03

> **rule:R3 (counterfactual 診断)**。live/shadow 一切不変更。live gate 化は R1 手続き + user 最終承認。
> **状態: 🔒 LOCKED (v2 forward、2026-08-03)** — first look **2026-11-06** (backstop 2027-01-31、registry `ecg-forward-first-look`)。**first look まで gate×outcome のジョイント計算は全面禁止 (P-10 型)**。
> **由来**: [[ea-landscape-sweep-2026-07-31]] §4.2 (31-agent EA 調査の敵対的検証 GO、score 55)。
> **v1→v2 転換 (同日)**: 遡及 explore 案 (v1) は敵対的検証 3 レンズで **KILL 2 件** — §10 参照。遡及窓 (04-08〜08-02) では (a) 窓中の一度きりの構造ブレークが family PASS をほぼ確定させ (合成データ実証: 1.0σ step で偽陽性 100%、robustness 3 種全素通し)、(b) 週層化で偽陽性を殺すと真の持続性への検出力も消える (0.51→0.02) = **このデータ密度で「K トレード持続性」と「週スケールドリフト」は識別不能**、(c) retired 6 セルの系列終端は outcome-conditioned truncation。→ **プロジェクト前例 (#4 MoF / #10 E12) に従い forward pre-reg に転換**。遡及窓は**未測定のまま保存** (burn なし)。

## 1. 仮説と estimand (v2 で正直化)

- **H1**: セルの shadow closed P&L 系列で、「直近 K トレード合計 pips > 0」条件下の forward トレード期待値が条件不成立下を上回る。
- **estimand の源泉について**: 改善の源泉は「短期持続性」と「緩慢な市場レジームドリフト」の**合成でよい** — 本 gate は実運用でどちらも収穫するため、両者の分離は要求しない (v1 の誤り)。**除外すべきはエンジン変更由来の人工的非定常のみ** — forward では deploy イベントが git 履歴から機械的に定義できるため epoch 層化で除外可能 (§4)。
- 市場データ・LOCKED データ (E1/E7/E12/MoF) に一切触れない。事前確率 mixed〜negative の低 prior・低コスト枠。

## 2. データ (凍結)

- **forward 測定窓**: 本番 shadow closed trades、**entry_time ≥ 2026-08-04T00:00:00Z**、first look 時に cutoff = 2026-11-01T00:00:00Z (13 週)。取得は `tools/render_trades_snapshot.py` 正規経路 (first look 時に新規スナップショット + sha256 記録)。
- **state warm-up**: gate state の計算には 2026-08-04 以前の履歴 closed trades を使用してよい (初日から K priors を確保)。**outcome 側は forward 行のみ**。
- **行フィルタ (凍結)**: `status='CLOSED'` AND `(oanda_trade_id IS NULL OR oanda_trade_id='')` AND `COALESCE(is_shadow,1)=1` (FLAG_DRIFT 除外) AND `COALESCE(dedup_violation,0)=0` AND 保有 ≥5 秒 (canonical seed-exclusion) AND `pnl_pips IS NOT NULL AND exit_time IS NOT NULL` (実測 0 件だが明文化)。**外れ値トリミングは行わない**。`exit_time < entry_time` の行は実行エラー (ハーネスが raise)。
- **dedup (凍結)**: 同セル・同方向で「直前に**採用**した行」との entry_time 差 60 秒**未満**は破棄 (チェーンでなくアンカー式)。SQL は `ORDER BY entry_time ASC, trade_id ASC` でタイ決定的。
- **対象セル (primary family、凍結)**: active 4 セル — daytrade_gbpusd/session_time_bias/GBP_USD、daytrade_eur/session_time_bias/EUR_USD、scalp_5m_gbp/vol_momentum_scalp/GBP_USD、daytrade_gbpusd/xs_momentum/GBP_USD。**verdict 参加は forward N≥150 のセルのみ** (未達セルは UNDERPOWERED として開示、m は事前固定のまま縮めない)。retired セル (v1 の 6 セル) は本測定から**完全除外** — 系列終端の outcome-conditioned truncation と banned 家系 (bb_rsi T10 等) の再訴訟リスクのため。**本測定は banned families の entry/filter 再生ではない** — gate はシグナル生成に一切触れない純配分層であり、対象セルはすべて現役 shadow-emitting セルのみ。
- **セル途中退場の扱い (事前宣言)**: forward 窓中に R2 demote / shadow 引退が発生したセルは、その時点で系列打ち切り。打ち切り理由と日付を verdict に開示。N≥150 未達なら UNDERPOWERED。
- **live 送信穴の扱い (事前宣言)**: live 転送成功した signal は shadow 行にならず系列に穴を開ける (v1 敵対的検証 MUST-FIX-1)。forward 窓中の各セル live 行数を verdict で開示し、live 行が当該セル forward 総行数の 20% を超えた場合は当該セルを COMPOSITION-CONFOUNDED として claim 不可 (記述のみ) とする。

## 3. Gate 定義 (凍結)

- **K ∈ {5, 10, 20}** の 3 点のみ、閾値 = 0 固定。グリッド最適化禁止。
- **因果的 state**: トレード t の state = 「`exit_time < entry_time(t)` (厳密不等号) を満たす同セル closed trades のうち exit_time 降順 K 件」の pnl_pips 合計。t 自身・t の entry 時点で未決済の trade は不含 (lookahead ゼロ — v1 検証で合成データ実証済み)。
- **exit_time の意味論**: exit_time は per-mode background thread の close 検知時刻 (poll ベース)。本番 gate 化した場合も同じ検知時刻を読むため explore と本番の情報集合は一致する。state の実時間スパンは daytrade セル ~3 trades/day で K=5 ≈ 1.7 日 / K=20 ≈ 7 日 — gate は「数日前までの成績」を見る層であることを開示。
- pnl は記録された `pnl_pips` (gross)。contrast は定数摩擦に不変、経済ゲート (§5) のみ net 換算 (USD_JPY 2.14 / EUR_USD 2.00 / GBP_USD 4.53 / EUR_JPY 2.50)。

## 4. 統計 (凍結)

- **primary**: `contrast(c,K) = mean(pnl | state>0) − mean(pnl | state≤0)` の**片側検定 (>0)**。**primary p は unique-spaced 系列上で計算** (entry が前採用行の exit より前の行を除いた系列 — 同時保有の機械的相関による anti-conservative を除去、v1 検証 M1)。フル系列 contrast は記述統計として併記。
- **null**: within-cell **epoch 層化 permutation** — トレードの時刻骨格を固定し、pnl 値を epoch 層内でのみ 10,000 回シャッフル。**epoch 境界の機械的定義 (凍結)**: origin/main の first-parent merge commits のうち、`modules/demo_trader.py`、`modules/demo_db.py`、`modules/shadow_demote_registry.py`、`strategies/` のいずれかに触れたものの commit 日 (UTC date)。eligible outcome <10 の stratum は**後続** stratum に併合 (決定的)。この定義により deploy 由来の水準シフトは null 側に保存され、偽陽性化しない。
- **多重性**: Bonferroni **m = 4 cells × 3 K = 12**、α = 0.05/12 ≈ 0.00417。
- **退化 permutation** (全 on / 全 off) は**保守側にカウント** (ge+=1)。p の床 = 1/(n_perm+1)。
- **robustness gates (PASS セルに必須、全て符号維持)**:
  - (i) フル系列 (overlap 込み) でも contrast > 0
  - (ii) LOYO-week (outcome 側のみ除外、informative fold = eligible ≥1 のみ分母): contrast > 0 が (informative 週数 − 3) 以上
  - (iii) coverage = gate_on 率 ∈ [0.25, 0.75]
  - (iv) split-half (eligible 時系列前半/後半、outcome 側分割) 両方で contrast > 0
  - (v) 上位 2 |pnl| 除外で contrast > 0 (heavy-tail 支配の排除)
- **knife-edge**: p < 5α の (cell,K) は n_perm=100,000 (per-cell 決定的 seed = sha256(cell+K) 派生、規約は §9) で再計算し最終とする (MC 誤差対策、v1 検証 N3)。
- **seed**: 20260803 + sha256(cell/K) 派生 (per-cell 決定的、§9 のハーネスに実装)。

## 5. Verdict 規則 (凍結)

- **統計 PASS** ⟺ ≥1 (cell,K): p < α AND contrast > 0 AND robustness (i)-(v) 全通過。
- **経済 PASS (live-R1 経路の資格)** ⟺ 統計 PASS セルで `mean(pnl_net | gate_on) > 0` **かつ当該セルに live 経路が実在する** (xs_momentum×GBP_USD は 05-29 から _PAIR_DEMOTED = live 経路なし — PASS しても gate 適用先は shadow→live 昇格 R1 とセットでのみ)。
- **FAIL クローズ** ⟺ 統計 PASS ゼロ。**同型再試行禁止 = 自戦略 closed P&L の rolling-K 合計閾値ゲート (shadow 書内 counterfactual) 全変種**。再入場 = forward データがさらに 2 倍蓄積した時点で新 pre-reg + 敵対的検証を条件に 1 回のみ。
- **UNDERPOWERED** ⟺ 全セル N<150 — verdict を出さず second look を 2027-01-31 cutoff で 1 回のみ。

## 6. Power の正直な開示 (v1 検証 M5 反映)

α=0.00417 (z≈2.64)、forward 13 週で projected N≈170-260/セル、coverage 50-50 として検出可能効果 ≈ **0.37σ @ 50% power / 0.47σ @ 80% power**。unique-spaced 化 (daytrade セルで −20%) と coverage 偏りでさらに悪化し得る。**PASS は「強い条件付き期待値差の存在」のみを主張でき、FAIL は小効果を棄却しない**。低 prior・低コスト枠として受容済み。

## 7. 交絡の扱い (v2 で全面改稿)

- **artifact 非定常 (エンジン変更)**: §4 の epoch 層化で null 側に保存 — v1 の主要 KILL への構造的対処。
- **市場レジームドリフト**: 本 estimand では**正当なシグナル** (gate が実運用で収穫する) — 層化しない。「持続性そのもの」との分離は主張しない (§1)。
- **BE-lock A/B (06-03〜)**: forward 窓では全期間適用中で breakpoint なし — 交絡でなく系列の恒常的性質。
- **同時保有相関**: primary を unique-spaced 化して対処 (§4)。「遮断」ではなく「主要部の除去」。
- **live 送信穴 / セル退場 / FLAG_DRIFT**: §2 で事前宣言済み。
- **既存 R2 損失停止 / watchdog との差分**: 既存は片側 (損失時停止)・ad hoc。本仮説は対称・事前登録・counterfactual。live gate 化時の二重ゲート設計は R1 パケット (本測定の範囲外)。
- **自己フィードバック (gate 化後)**: gate_on → live 送信 → shadow 系列に穴 → state 計算対象が痩せる — **live gate 化する場合は state 系列を live+shadow 合成で定義し直す必要がある** (R1 パケットで設計、explore の外挿限界として明記)。

## 8. First look の執行手順 (凍結)

1. 2026-11-06 以降に新規スナップショット取得 (`render_trades_snapshot.py`) + sha256 記録
2. `tools/equity_curve_gating_explore.py` を n_perm=10,000 (固定、CLI で下回る指定は拒否) で単一実行
3. verdict を本ドキュメント §11 に追記 + 台帳 #22 更新 + raw JSON/report 保存
4. **前倒し実行は peeking として禁止**。first look までの gate×outcome ジョイント計算全面禁止 (P-10 型)。蓄積センサス (件数のみ) は可
5. PASS 時: live gate R1 パケット起案は forward 再現 (second forward 90d) 後のみ — 「PASS → 即 R1」は不可

## 9. 実装

`tools/equity_curve_gating_explore.py` (LOCK コミット同梱、forward 設定済み)。読み取り専用、seed 20260803 + sha256(cell/K) 派生、epoch 境界は §4 の凍結規則で first look 時に `git log` から機械導出。出力 `knowledge-base/raw/bt-results/ecg_forward-<date>.json` + `reports/ecg-forward-<date>.md`。

## 10. 敵対的検証ログ (2026-08-03、LOCK 前実施 — v1 遡及案への 3 レンズ)

**verdict: v1 LOCK 不可 (KILL 3 件) → v2 forward 転換で解決。**

- **統計レンズ (KILL K1 + M1-M7)**: 全シャッフル permutation の H0 は i.i.d. — 窓中の一度きりの水準シフトで偽陽性が family PASS を確定させることを合成データで実証 (0.5σ step → 26%、1.0σ → 100%、robustness 全素通し)。週層化は真の持続性の検出力も殺す (0.51→0.02) = **遡及窓では estimand が識別不能**。M 群: primary の unique-spaced 化 / LOYO informative-fold / 退化 perm 保守化 / knife-edge 規約 / power 50%↔80% 明記 / md report + n_perm 強制 / フィルタ明文化 — **全て v2 に反映**。
- **交絡レンズ (KILL-1/2 + MUST-FIX 1-5)**: 対象 10 セル中 6 セルは decay を理由に R2 停止されたセル自身で、系列終端が outcome-conditioned truncation — 既知の decay を新エッジ様式でロンダリングする構造。窓開始 04-02 は Fidelity Cutoff (04-08) 前の SLTP バグ汚染期を含み、セル 9 は cutoff 修正で floor 割れ。BE-lock A/B (06-03)・live 送信穴・seed-exclusion 欠落・家系ファイアウォール不在 — **retired 6 セル完全除外 + forward 化 + §2/§7 の事前宣言群で全て解決**。
- **データ衛生レンズ (MUST-FIX 1-4 + NOTE 7)**: lookahead 構造 (厳密不等号・自己除外) は合成データ実証で健全。FLAG_DRIFT 22 行 (is_shadow=0 × oanda 空) がセル 9 に混入 → `COALESCE(is_shadow,1)=1` フィルタ追加で解決 (セル 9 は v2 で除外済み)。exit<entry ガード / タイムスタンプ形式 assert / ORDER BY タイ決定化 / dedup 文言確定 — **全て v2 ハーネスに反映**。スナップショット可用性指摘 (gitignore) は forward 化により「first look 時に新規取得 + sha256 記録」で置換。
- **v1 の遡及窓 (2026-04-08〜08-02) は未測定のまま保存** — 将来 epoch 層化での遡及診断 (非 claim) に使う場合も新 pre-reg 必須。

## 11. Verdict (first look 2026-11-06 以降に追記)

<!-- 未測定 — P-10 型凍結中 -->
