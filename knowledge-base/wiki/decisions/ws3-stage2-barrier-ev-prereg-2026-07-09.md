# Pre-registration DRAFT: WS3 stage-2 — barrier/EV 設計 + TV Pine canon 再現 (rule:R1 stage-2)

**起案日**: 2026-07-09 (grid BT / TV 検証の実行前に設計固定 — カーブフィッティング禁止の遵守)。敵対的レビュー 3 レンズ (リーク/統計/KB整合) 済み — 18 findings を反映した改訂版
**Status**: 📝 **DRAFT — user 最終承認待ち**。承認で 🔒 LOCKED 化。**LOCK 前の grid BT / barrier シミュレーション / TV 検証の実行は禁止** (結果を見た後の設計変更を構造的に排除するため)。承認後の本文書の変更はレビュー必須 PR のみ
**起点**: [[ws3-asymmetry-oos-prereg-2026-07-09]] §8 (stage-1 verdict: ✅ PASS 2/8、2026-07-09) / [[roadmap-v2.3-payoff-friction-repair]] WS3
**承認**: 本 DRAFT の LOCK 化に user 承認が必要 (stage-1 §8.3 の固定分岐)。さらに **stage-2 PASS でも live/shadow 実装は別途 user 最終承認** — 本 pre-reg は評価のみで live パラメータを一切変更しない
**タスク票**: `.ai/tasks/queue/20260709-1610-ws3-stage2-barrier-ev-prereg.md` (排他 claim 済み)

## 1. 仮説 (H1)

stage-1 で OOS 再現した方向性非対称 2 セル (london_fix_reversal×EUR_USD h24 / htf_false_breakout×AUD_JPY h24) は、**h24 アンカーの固定 TP/SL barrier + 24 bar timeout の下で、摩擦控除後も正 EV に変換できる**。

H0: 全 barrier 構成の摩擦調整 EV ≤ 0 (非対称は実在しても摩擦・先着順序 (sequencing) が EV 化を阻む)。

**stage-1 との estimand の違い (明示)**: stage-1 は forward MFE/MAE 比 (barrier 非依存・sequencing 無視)。stage-2 は first-touch barrier シミュレーションによる EV — MFE≥TP でも SL 先着なら負け。この変換が非自明であることが本検証の存在理由。

**T2 exit-repair FAIL ([[exit-repair-tp-sl-prereg-2026-07-07]] §8) との関係 (明示)**: T2 は非対称スクリーン無しの pooled 母集団 (診断窓 clean live 6 entry_type — trendline_sweep/wick/zz_pivot/vix/dt_sr_channel/vsg。**本 stage-2 の 2 セルはいずれも含まれない非交差集合**) に対し現行 ATR 設計 TP/SL の乗数 grid を適用して FAIL した。その H0「exit 再設計では黒字化せず、シグナル張り替えが唯一の経路」の"張り替え"を、WS3 は「MFE/MAE 非対称セルへの母集団選抜」として実装した。本 stage-2 は (i) 非対称が OOS 再現した 2 セル限定 (母集団中央値 ratio 0.88 の pooled とは別物)、(ii) 現行設計の縮尺ではなく実測 MFE/MAE 分位点にアンカーした絶対 pips barrier、の 2 点で T2 と estimand が異なる。**T2 FAIL の再試行ではなく、T2 の固定分岐が指した WS3 経路そのものである**。

## 2. 対象セルと barrier grid (a priori 固定、m=18)

**対象は stage-1 PASS 2 セルのみ** (§8.3 拘束: trendline_sweep×EUR_USD 追加禁止 / london_fix_reversal×GBP_USD 負EV 前歴の EUR_USD への横展開禁止 / fail 6 セルの入れ替え禁止)。

**アンカー方針**: TP/SL の分位点アンカーは**探索標本 (2025-07-08〜2026-06-07) h24 を主とし、stage-1 OOS (2024-25) の WIN/LOSS 分離統計を補助参照として grid 端点の選定に用いた**。つまり grid 設計は探索標本と stage-1 OOS の**両方を消費した** — 従って両窓での本 grid の EV は Secondary 記述に留め、stage-2 verdict・後続の実装 pre-reg のいずれにおいても確認的根拠として引用することを**禁止**する (確認的判定に使える窓は §3 の OOS-2 のみ)。**OOS-2 の統計を設計に使うことは全面禁止**。ホールドは **24 bars (15m×24 = 6h) 固定** — 探索診断 [[ws3-mfe-distribution-2026-07-08]] の減衰型分類 (h24 ピーク) に従う。BE/Trail は **OFF 固定** (MEMORY `project_be_trail_inflates_python_bt_wr`: +20pp 水増し源。ablated が全エンジン default 済み)。

| cell | TP grid (pips) | SL grid (pips) | アンカー根拠 |
|---|---|---|---|
| london_fix_reversal×EUR_USD | {14, 18, 24} | {10, 14, 18} | 探索 h24: MFE p50=14.35 / p75=18.68、MAE p50=9.5。補助 (stage-1 OOS): TP20 の WIN/LOSS 判別 0.65 vs 0.19 |
| htf_false_breakout×AUD_JPY | {20, 28, 36} | {16, 24, 30} | 探索 h24: MFE p50=22.1 / p75=35.75、MAE p50=15.9。補助 (stage-1 OOS): WIN MAE p90=29.7 / LOSS MAE p50=32.5 の分離点 = SL 25-30p |

- 自由度は各セル TP×SL の 2 つのみ (3×3=9 構成/セル、計 18 構成)。hold/BE/Trail/エントリー定義は固定 — grid をこれ以上拡張することは禁止
- 各セルのエントリー母集団は stage-1 と同一 (本番 signal 関数 baseline、V2 parity 3flag)。戦略ネイティブの exit (lfr: SL=ATR×1.0/TP=ATR×1.5/hold 4 bars、htf_fb: hold 8 bars) は**使わない** — 本検証は「exit を h24 幾何に張り替えたときの EV」を問う
- grid には RR<1.2 の構成を含む (lfr TP14/SL18=0.78 等) — [[edge-pipeline]] Stage 2→3 Gate の「最低RR≥1.2」は対称 payoff 前提の基準であり、本検証の estimand (非対称セルの first-touch EV) とはカテゴリーが異なる (lesson: pre-reg gate は機構の作用方向と同軸の指標で)。PASS 構成が RR<1.2 の場合、実装 pre-reg でこの逸脱を明示し user 判断を仰ぐ

## 3. 評価プロトコル

- **エンジン**: 新規 `tools/ws3_stage2_barrier_sim.py` (LOCK 後に実装)。ws3_mfe_scan 同様の per-entry forward scan 上で first-touch 判定: entry fill (ep) から 24 bars 内に TP/SL どちらが先に触れるか。**同一バー内 TP+SL 両ヒットは SL 優先 (両ヒット=LOSS)** — swing エンジンの保守規約を採用。4 barrier エンジンに P1-2b で pin 済みの fut_close tie-break より保守側であり、研究 verdict の偽陽性を抑える方向。感度として fut_close tie-break での EV を §8 (Secondary、判定不使用) に併記。24 bars 無接触は bar-24 close で決済
- **評価窓 (OOS-2)**: **2022-07-07〜2024-07-06 の 2 年間** — 探索窓 (2025-07-08〜2026-06-07)・stage-1 OOS 窓 (2024-07-07〜2025-07-07)・診断窓のいずれとも重複ゼロの**第3窓**。2 年固定は検定力の確保のため (1 年窓 N≈35 では SE≈2.6-4.1 p/t で power 不足 — 敵対的レビュー statistics 指摘)。stage-1 OOS 窓は「セル選択に使用済み」のため EV 判定に再使用しない (winner's curse 防止)。実装 = 隔離 worktree に末尾 2024-07-06 で切詰めた parquet (look-ahead 遮断、stage-1 と同方式)
- **執行順序 (結果非依存の 2 段階)**: (1) barrier sim 実行前に**エントリー抽出のみ**を行い、セル毎 N を確定して raw/ に保存。(2) 窓と N の確定後に初めて first-touch sim を実行する。確定後の窓の再延長・短縮・部分窓引用は禁止 (違反 = 当該セル FAIL)。N<30 のセルは §4(c) により機械的に FAIL (窓延長の裁量は設けない — 2 年窓で N≥60 が事前見込み)
- **データ制約 (a priori 宣言)**: EUR_USD 15m は 2014〜ローカルあり。AUD_JPY 15m の 2022-07〜2024-07 は Massive API から追加取得 (12y 履歴あり)。取得不能な区間が残る場合は取得可能な最長部分窓で評価し verdict に明記 (除外はしない — 部分窓は事実として記録)
- **摩擦 (判定値、往復控除)**: EUR_USD = **2.00 p/t** ([[friction-analysis]] 理論値)。AUD_JPY は理論テーブル不在のため **3.125 p/t** (EUR_JPY 2.50 + 25%) を検定の判定値とし、さらに **§4(e) で stress 4.0 p/t の符号頑健性を PASS 必須条件化** (宣言値の不確実性 ±0.9 p/t を無害化)。感度: 実測フロア 1.30 p/t / stress (EUR_USD 3.0) は §8 に記述併記
- **Walk-forward**: OOS-2 を期間等分 3-fold (約 8 ヶ月×3)。fold 毎 EV は全構成について記録 (判定には §5.4 の fold 集中検査のみ使用)

### 3b. TV Pine canon 再現ゲート (必須、stage-1 §8.3 (a))

Python BT エントリー母集団への系統疑義 (MEMORY `feedback_tv_edge_discovery_loop`: Live > TV > Python BT) に対する独立検証。**grid 判定 (§4) とは独立の barrier — 両方 PASS で初めて stage-2 PASS**:

1. **検証窓の事前確定 (window-shopping 封鎖)**: TV 数値取得前に次の手順で窓を確定する: (i) TV Deep BT の到達可能範囲をスクリーンショットで記録し raw/ に保存、(ii) OOS-2 (2022-07-07〜2024-07-06) と重複が取れる最長窓に確定。以後の窓変更は当該セル FAIL。(iii) 重複が物理的に取れない場合のみ直近 365d に fallback するが、この窓は探索窓と重複するため判定基準を「TV ratio ≥ 1.2」ではなく「**TV ratio が同窓 Python ratio の ±25% 以内 (canon 一致性)**」に置換する — 探索重複窓では ratio≥1.2 は選抜により無情報のため
2. **エントリー母集団の trade-level 突合** (aggregate 比較は不可 — N 乖離は aggregate で検出不能の教訓): `tools/tv_overlay_gen.py` で Python BT trade list を Pine overlay 化し、手書き strategy replica の発火と timestamp/方向を突合。エントリー数一致 ±20%。**帰属可能な機構クラスを今列挙する: feed 欠損バー / bar alignment (時刻境界) / spread・価格ガードフィルタ差 / セッション境界処理差。不一致エントリーのうちこれらに帰属できないものが Python エントリー総数の 5% を超えたら当該セル FAIL**
3. **非対称の TV feed 上での再現**: Pine `var array` accumulator で entry 後 h24 の MFE/MAE を集計し、確定窓で **ratio ≥ 1.2** (fallback 窓なら上記 1-(iii) の canon 一致性基準)。**TV と Python の同窓 MFE/MAE ratio 乖離が ±25% を超えたら、帰属説明の有無に関わらず当該セル FAIL** (AUDJPY feed 差 PF~20% の前歴に対する数値化)
4. **手続き衛生** (全て過去の失敗事例): "Update report" refresh 後の数字のみ採用 / on-chart instance の save 後 手動 Remove→再Add / `process_orders_on_close=true` semantics 統一 / 摩擦は `strategy.commission.percent` (per-side = RT/2) で TV 側に注入 / lfr replica は実装事実 (pre-fix 単純フェード) に忠実に写す — 「あるべき論理」に直さない

## 4. エンドポイント (固定)

- **Primary (セル毎)**: OOS-2 窓の摩擦調整 EV (p/t) = mean(per-trade pnl − friction判定値)。pnl = +TP (TP 先着) / −SL (SL 先着) / (close₂₄ − ep)×dir (timeout)
- **検定 (セル = 検定単位、stage-1 と整合)**: セル毎に、同一の日次 block resample (B=10,000、seed 固定) 上で 9 構成すべての摩擦調整 EV を同時計算し、**max 統計量 T = max_g EV_g** を用いる。null 分布は per-trade pnl をセル内で中心化した resample から生成 (**Westfall–Young max-T 型** — 構成間相関を resample が自動処理し、「9 構成の最良」の選択効果を null に織り込む)。p_cell = P(T_null ≥ T_obs)。**判定: p_cell ≤ 0.05 (2 セル Bonferroni で FWER 0.10** — stage-1 の q=0.10 と同水準の family 保証をセル単位で回復)。構成レベル BH-FDR (m=18) は Secondary (記述) に降格
- **PASS 条件 (セル毎、全て充足)**:
  - (a) p_cell ≤ 0.05 (上記 Westfall–Young max-T)
  - (b) 最良構成の **3×3 近傍 (TP±1 段 × SL±1 段、grid 端は存在する近傍のみ) の平均摩擦調整 EV ≥ +0.5 p/t** — 近傍平均は勝者選択バイアス (+1.5〜4 p/t 上振れ) をほぼ受けないため、shrinkage 床として実効
  - (c) OOS-2 のセル N ≥ 30
  - (d) **§3b TV canon ゲート PASS** (同セル)
  - (e) **AUD_JPY セルのみ**: 摩擦 stress 4.0 p/t 適用時にも最良構成の point EV > 0 (検定は 3.125 のまま — 符号頑健性のみ要求)
- **全体 verdict (3 分岐、a priori 固定)**:
  - **PASS** (セル ≥1 が (a)-(e) 充足) → user 最終承認を経て実装提案へ (shadow 導入から開始する R1 実装 pre-reg を別途起案 — 本 pre-reg は実装内容を拘束しない)
  - **REJECT** (両セルとも全 9 構成の点推定 EV ≤ 0 — 方向的にも否定) → 本 2 セル×h24 barrier 幾何からの EV 変換を断念し、v2.3 WS3 は新シグナル系統 (外部仮説) の探索へ。ただし stage-1 §8.3 (c) の trendline_sweep×EUR_USD live N 蓄積再評価は本 verdict の影響を受けず継続
  - **UNDERPOWERED** (点推定 EV > 0 の構成が存在するが (a) 不達) → 断念ではなく記録に留め、当該セルの shadow 蓄積 **累積 N ≥ 100 到達時に本 grid・本検定を変更せず 1 回限り再判定** (この再判定は新たな探索自由度を持たない — 今宣言)。再判定も不達なら REJECT と同じ分岐へ
- **Secondary (記述のみ、判定不使用)**: 構成レベル BH-FDR / 探索窓・stage-1 OOS 窓での同 grid の EV (レジーム頑健性の記述 — 確認的引用は §2 により禁止) / 摩擦感度 (フロア 1.30 / stress) / fut_close tie-break での EV / TP-hit・SL-hit・timeout 率の内訳

## 5. ナイフエッジ検査 (verdict 時必須、4 点)

1. **メカニズム整合 (timeout ドリフト排除)**: PASS 構成について、timeout トレードの price pnl を 0 に置換 (摩擦控除は維持) した **EV' ≥ 0** を要求。timeout 率と EV 分解 (barrier 成分 vs timeout 成分) を verdict に併記 — PASS の EV 源泉が first-touch barrier 側 (= stage-1 の非対称の EV 化という H1 そのもの) にあることを機構的に担保。timeout ドリフトのみで正になる構成は「別の仮説」であり本 pre-reg の PASS にしない
2. **擬似反復**: 日次クラスタ補正内蔵 + lag-1 ρ 記録 (stage-1 同様)
3. **格子点孤立**: PASS 構成の格子上隣接構成 (TP±1 段, SL±1 段、存在するもの最大 4) のうち**過半が摩擦調整 EV > 0** でなければ孤立格子点として棄却 (§4(b) の近傍平均床と相補 — こちらは符号の空間的整合)
4. **fold 集中**: PASS 構成について**最良 fold を除外した残り 2 fold の pooled EV > 0** を要求 (EV が単一 8 ヶ月クラスタ — 一つのレジームイベント — に依存する PASS を棄却)

## 6. 執行と監視

- **executor**: claude 直接実行 (user 承認 → LOCK 後)。タスク票 `20260709-1610-ws3-stage2-barrier-ev-prereg`
- **期日**: LOCK 日 + 10 日以内に verdict (T5 型ギャップ防止)
- **DRAFT 滞留監視 (T5 教訓の DRAFT 段階適用)**: 本 DRAFT コミットと**同一 PR** で `knowledge-base/wiki/decisions/prereg-trigger-registry.json` に `ws3-stage2-lock-decision-stale` (type: deadline_info, deadline: **2026-07-16**, doc: 本文書) を追加 — 期日までに user 決裁 (LOCK or 差し戻し) が無ければ stale アラート (`tools/prereg_trigger_watch.py` が毎日評価)
- **LOCK 時**: 上記エントリを resolved 化し、verdict 期日エントリ `ws3-stage2-verdict-deadline` (LOCK+10d) に置換
- **verdict 記録**: 本文書 §8 追記 + `raw/bt-results/` 保存 + session log + roadmap 反映

## 7. 除外・注意 (DRAFT 時点で明示)

- **live パラメータを一切変更しない** (純研究 stage-2)。stage-2 PASS 単独で promote しない — 実装は別 pre-reg + user 最終承認
- 探索標本 + stage-1 OOS の統計は「barrier 候補の設計」にのみ使用済み (§2 で今固定した grid が全て)。OOS-2 の結果を見て grid を動かすこと・hold を動かすこと・セルを追加することは禁止
- london_fix_reversal は戦略カード上 **PAIR_DEMOTED×USD_JPY / Phase0 Shadow** (60d BT WR75% → 365d 崩壊の overfit 前歴あり)。**EUR_USD セル自身もネイティブ exit (ATR 設計) の 365d BT で EV −0.103 の前歴あり** (v9.1、demo_trader.py 記録) — 本検証はこのネイティブ exit を使わず h24 幾何 barrier に張り替えた EV を問うものであり、負 EV 前歴の再試行ではなく **exit 幾何の交換実験**である。htf_false_breakout×AUD_JPY は既存 365d BT テーブルに AUD_JPY 行が無い (WS3 スキャンが初計測)。いずれも「stage-2 PASS = 戦略復権」ではなく「このセル×この barrier 幾何」限定の主張であることを verdict に明記
- AUD_JPY のエントリー母集団には v6.1 JPY 追加ゲート (RSI div / OB 接触) が適用済み — stage-1 と同一母集団なので整合。redesign_v2 フラグ (`HTF_FALSE_BREAKOUT_REDESIGN_V2`) は **OFF (legacy 経路)** で評価 (stage-1 と同一)
- OOS-2 (2022-24) は探索窓 (2025-26)・stage-1 OOS (2024-25) と異なるレジーム (2022 は JPY 介入期を含む)。絶対 pips barrier の EV 評価であるためレジーム依存はそのまま結果に出る — それ自体が「絶対 barrier の頑健性」の検証であり、verdict に記述する
- KB 整合の棚卸し (本 pre-reg と同 PR で対応): london_fix_reversal×GBP の stale PROMOTED 残存は **`wiki/strategies/edge-pipeline.md` Stage 6 表 + `wiki/edge-pipeline.md` の 2 箇所** — カード側 (Phase0 Shadow / PAIR_DEMOTED×USD_JPY) が真実 (check.py warn の原因)
