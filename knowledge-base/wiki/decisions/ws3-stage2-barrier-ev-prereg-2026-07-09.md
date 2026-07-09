# Pre-registration DRAFT: WS3 stage-2 — barrier/EV 設計 + TV Pine canon 再現 (rule:R1 stage-2)

**起案日**: 2026-07-09 (grid BT / TV 検証の実行前に設計固定 — カーブフィッティング禁止の遵守)
**Status**: 📝 **DRAFT — user 最終承認待ち**。承認で 🔒 LOCKED 化 + registry 監視エントリ追加。**LOCK 前の grid BT / barrier シミュレーション / TV 検証の実行は禁止** (結果を見た後の設計変更を構造的に排除するため)。承認後の本文書の変更はレビュー必須 PR のみ
**起点**: [[ws3-asymmetry-oos-prereg-2026-07-09]] §8 (stage-1 verdict: ✅ PASS 2/8、2026-07-09) / [[roadmap-v2.3-payoff-friction-repair]] WS3
**承認**: 本 DRAFT の LOCK 化に user 承認が必要 (stage-1 §8.3 の固定分岐)。さらに **stage-2 PASS でも live/shadow 実装は別途 user 最終承認** — 本 pre-reg は評価のみで live パラメータを一切変更しない
**タスク票**: `.ai/tasks/queue/20260709-1610-ws3-stage2-barrier-ev-prereg.md` (排他 claim 済み)

## 1. 仮説 (H1)

stage-1 で OOS 再現した方向性非対称 2 セル (london_fix_reversal×EUR_USD h24 / htf_false_breakout×AUD_JPY h24) は、**h24 アンカーの固定 TP/SL barrier + 24 bar timeout の下で、摩擦控除後も正 EV に変換できる**。

H0: 全 barrier 構成の摩擦調整 EV ≤ 0 (非対称は実在しても摩擦・先着順序 (sequencing) が EV 化を阻む)。

**stage-1 との estimand の違い (明示)**: stage-1 は forward MFE/MAE 比 (barrier 非依存・sequencing 無視)。stage-2 は first-touch barrier シミュレーションによる EV — MFE≥TP でも SL 先着なら負け。この変換が非自明であることが本検証の存在理由。

## 2. 対象セルと barrier grid (a priori 固定、m=18)

**対象は stage-1 PASS 2 セルのみ** (§8.3 拘束: trendline_sweep×EUR_USD 追加禁止 / london_fix_reversal×GBP_USD 負EV 前歴の EUR_USD への横展開禁止 / fail 6 セルの入れ替え禁止)。

**アンカー方針**: TP/SL は**探索標本 (2025-07-08〜2026-06-07) の h24 分位点**にアンカー (OOS 標本の分位点は使わない — OOS は stage-1 判定に使用済みで、かつ 2024-25 AUD_JPY はボラ水準が探索比 ~2 倍のため、保守側 = 探索標本水準を採用)。ホールドは **24 bars (15m×24 = 6h) 固定** — 探索診断 [[ws3-mfe-distribution-2026-07-08]] の減衰型分類 (h24 ピーク) に従う。BE/Trail は **OFF 固定** (MEMORY `project_be_trail_inflates_python_bt_wr`: +20pp 水増し源。ablated が全エンジン default 済み)。

| cell | TP grid (pips) | SL grid (pips) | アンカー根拠 (探索標本 h24) |
|---|---|---|---|
| london_fix_reversal×EUR_USD | {14, 18, 24} | {10, 14, 18} | MFE p50=14.35 / p75=18.68、MAE p50=9.5。OOS 参考: TP20 の WIN/LOSS 判別 0.65 vs 0.19 |
| htf_false_breakout×AUD_JPY | {20, 28, 36} | {16, 24, 30} | MFE p50=22.1 / p75=35.75、MAE p50=15.9。OOS 参考: WIN MAE p90=29.7 / LOSS MAE p50=32.5 の分離点 = SL 25-30p |

- 自由度は各セル TP×SL の 2 つのみ (3×3=9 構成/セル、計 **m=18**)。hold/BE/Trail/エントリー定義は固定 — grid をこれ以上拡張することは禁止
- 各セルのエントリー母集団は stage-1 と同一 (本番 signal 関数 baseline、V2 parity 3flag)。戦略ネイティブの exit (lfr: SL=ATR×1.0/TP=ATR×1.5/hold 4 bars、htf_fb: hold 8 bars) は**使わない** — 本検証は「exit を h24 幾何に張り替えたときの EV」を問う

## 3. 評価プロトコル

- **エンジン**: 新規 `tools/ws3_stage2_barrier_sim.py` (LOCK 後に実装)。ws3_mfe_scan 同様の per-entry forward scan 上で first-touch 判定: entry fill (ep) から 24 bars 内に TP/SL どちらが先に触れるか。**同一バー内 TP+SL 両ヒットは SL 優先** (保守側 tie-break — P1-2b で 4 エンジンに pin 済みの規約と同一)。24 bars 無接触は bar-24 close で決済
- **評価窓 (OOS-2)**: **2023-07-07〜2024-07-06** — 探索窓 (2025-07-08〜2026-06-07)・stage-1 OOS 窓 (2024-07-07〜2025-07-07)・診断窓のいずれとも重複ゼロの**第3窓**。stage-1 OOS 窓は「セル選択に使用済み」のため EV 判定に再使用しない (winner's curse 防止)。実装 = 隔離 worktree に末尾 2024-07-06 で切詰めた parquet (look-ahead 遮断、stage-1 と同方式)
- **データ制約 (a priori 宣言)**: EUR_USD 15m は 2014〜ローカルあり。AUD_JPY 15m の 2023-07〜2024-07 は Massive API から追加取得 (12y 履歴あり)。取得不能なら該当セルは取得可能な最長部分窓で評価し verdict に明記 (除外はしない)。**セル毎 N<30 の場合は窓を 2022-07-07 まで遡って延長** (この延長規則も今宣言する — 結果を見てから延長しない)
- **摩擦 (判定値、往復控除)**: EUR_USD = **2.00 p/t** ([[friction-analysis]] 理論値)。AUD_JPY は理論テーブル不在のため **3.125 p/t** (EUR_JPY 2.50 + 25% マージン) を判定値として今宣言。感度: 実測フロア 1.30 p/t と stress 4.0 p/t (AUD_JPY) / 3.0 p/t (EUR_USD) での符号を §8 に併記 (判定には不使用)
- **Walk-forward**: OOS-2 を 3-fold (約 4 ヶ月×3) に分割し、fold 毎の摩擦調整 EV 符号を記録

### 3b. TV Pine canon 再現ゲート (必須、stage-1 §8.3 (a))

Python BT エントリー母集団への系統疑義 (MEMORY `feedback_tv_edge_discovery_loop`: Live > TV > Python BT) に対する独立検証。**grid 判定 (§4) とは独立の barrier — 両方 PASS で初めて stage-2 PASS**:

1. **エントリー母集団の trade-level 突合** (aggregate 比較は不可 — N 乖離は aggregate で検出不能の教訓): `tools/tv_overlay_gen.py` で Python BT trade list を Pine overlay 化し、手書き strategy replica の発火と timestamp/方向を突合。**エントリー数一致 ±20% + 不一致エントリーの機構帰属説明** を要求
2. **非対称の TV feed 上での再現**: Pine `var array` accumulator で entry 後 h24 の MFE/MAE を集計し、**ratio ≥ 1.2** (stage-1 shrinkage 床と同値) が TV OANDA feed 上でも成立
3. **手続き衛生** (全て過去の失敗事例): "Update report" refresh 後の数字のみ採用 / on-chart instance の save 後 手動 Remove→再Add / `process_orders_on_close=true` semantics 統一 / 摩擦は `strategy.commission.percent` (per-side = RT/2) で TV 側に注入 / データ feed 差 (MASSIVE vs TV OANDA) による PF ~20% 乖離の前歴 (AUDJPY) があるため、**AUD_JPY セルは feed 差を機構帰属できない乖離が残る場合 FAIL 扱い**
4. TV 検証窓は TV Deep BT が許す最長の OOS-2 重複窓。重複が取れない場合は直近 365d で実施し「窓不一致」を verdict に明記

## 4. エンドポイント (固定)

- **Primary (構成毎)**: OOS-2 窓の摩擦調整 EV (p/t) = mean(per-trade pnl − friction判定値)。pnl = +TP (TP 先着) / −SL (SL 先着) / (close₂₄ − ep)×dir (timeout)
- **検定**: 日次ブロックブートストラップ (B=10,000、day resample、seed 固定) → p = P(EV ≤ 0) one-sided。**多重性 m=18 (両セル pooled)、BH-FDR q=0.10**
- **PASS 条件 (セル毎、全て充足)**:
  - (a) 当該セルの ≥1 構成が BH-FDR 通過
  - (b) 同構成の point EV ≥ **+0.5 p/t** (事前設定の shrinkage 床 — stage-1 の ratio≥1.2 床の EV 版)
  - (c) 同構成の WF 3-fold 符号 ≥ 2/3 が正
  - (d) OOS-2 の セル N ≥ 30
  - (e) **§3b TV canon ゲート PASS** (同セル)
- **全体 verdict**: PASS セル ≥1 → **user 最終承認を経て実装提案へ** (shadow 導入から開始する R1 実装 pre-reg を別途起案 — 本 pre-reg は実装内容を拘束しない)。PASS ゼロ → **H0 採択 = 現行シグナル母集団からの EV 変換を断念、v2.3 WS3 は新シグナル系統 (外部仮説) の探索へ** (stage-1 FAIL 分岐と同じ着地)
- **Secondary (記述のみ、判定不使用)**: 探索窓・stage-1 OOS 窓での同 grid の EV (レジーム頑健性の記述) / 摩擦感度 (フロア 1.30 / stress) / TP-hit 率・timeout 率の内訳

## 5. ナイフエッジ3点検査 (verdict 時必須)

1. **メカニズム整合**: PASS 構成の EV 構成 (TP-hit 率 × payoff) が stage-1 の非対称 (MFE 優位) と同型か — MAE 側の偶発的縮小による見かけ EV でないか
2. **擬似反復**: 日次クラスタ補正内蔵 + lag-1 ρ 記録 (stage-1 同様)
3. **格子点孤立**: PASS 構成の隣接構成 (TP±1 段 / SL±1 段) の EV 符号と整合するか — 孤立格子点 PASS は棄却

## 6. 執行と監視

- **executor**: claude 直接実行 (user 承認 → LOCK 後)。タスク票 `20260709-1610-ws3-stage2-barrier-ev-prereg`
- **期日**: LOCK 日 + 10 日以内に verdict (T5 型ギャップ防止)
- **監視主体 (T5 教訓 — LOCK と同時に追加)**: `knowledge-base/wiki/decisions/prereg-trigger-registry.json` に deadline エントリ `ws3-stage2-verdict-deadline` を追加 (`tools/prereg_trigger_watch.py` が毎日評価)。**DRAFT 段階では追加しない** (LOCK 時の同一コミットで)
- **verdict 記録**: 本文書 §8 追記 + `raw/bt-results/` 保存 + session log + roadmap 反映

## 7. 除外・注意 (DRAFT 時点で明示)

- **live パラメータを一切変更しない** (純研究 stage-2)。stage-2 PASS 単独で promote しない — 実装は別 pre-reg + user 最終承認
- 探索標本の分位点アンカーは「barrier 候補の設計」にのみ使用 (§2 で今固定した grid が全て)。OOS-2 の結果を見て grid を動かすこと・hold を動かすこと・セルを追加することは禁止
- london_fix_reversal は戦略カード上 **PAIR_DEMOTED×USD_JPY / Phase0 Shadow** (60d BT WR75% → 365d 崩壊の overfit 前歴あり)。htf_false_breakout×AUD_JPY は**既存 365d BT テーブルに AUD_JPY 行が無い** (WS3 スキャンが初計測)。いずれも「stage-2 PASS = 戦略復権」ではなく「このセル×この barrier 幾何」限定の主張であることを verdict に明記
- AUD_JPY のエントリー母集団には v6.1 JPY 追加ゲート (RSI div / OB 接触) が適用済み — stage-1 と同一母集団なので整合。redesign_v2 フラグ (`HTF_FALSE_BREAKOUT_REDESIGN_V2`) は **OFF (legacy 経路)** で評価 (stage-1 と同一)
- lfr の実効ロジックは pre-fix 単純フェード (JPY/非JPY 分岐は形式上のみ) — TV replica 作成時にこの実装事実に忠実に写す (「あるべき論理」に直さない)
- 2023-24 窓 (OOS-2) は 2024-25 と異なるレジーム (AUD_JPY ボラ水準差 ~2 倍の逆側)。ratio ではなく絶対 pips barrier の EV 評価であるため、レジーム依存はそのまま結果に出る — それ自体が「絶対 barrier の頑健性」の検証であり、verdict に記述する
- KB 整合の棚卸し (本 pre-reg と同 PR で対応): `edge-pipeline.md` Stage 6 テーブルの stale 行 (london_fix_reversal×GBP = v8.6 時代の PROMOTED 残存) が check.py warn の原因 — カード側 (Phase0 Shadow / PAIR_DEMOTED×USD_JPY) が真実
