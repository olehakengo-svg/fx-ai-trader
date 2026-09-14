# レンジ境界指値フェード探索 — 統合レポート (2026-09-14)

- Spec (凍結グリッド): `knowledge-base/raw/bt-results/range-fade-scan-2026-09-14/range_fade_spec.json` (ハーネス・結果 JSON・freeze manifest も同ディレクトリ)
- 台帳: hypothesis-catalog-2026-07-24 #28 / MEMORY: `project_range_fade_limit_scan_fail_2026_09_14`
- グリッド: 32 セル (4 ペア × lookback {96, 192} × vol {any, lowvol} × exit {midasym, sym1r})、Bonferroni α = 0.05/32 = **0.0015625**
- 総トレード数 N = 4,648 (USD_JPY 1,500 / EUR_USD 1,182 / GBP_USD 410 / EUR_JPY 1,556)

---

## TL;DR — Verdict: **FAIL_NO_SURVIVORS**

- **事前宣言ゲート (p_block < 0.0015625) 通過: 0/32 セル**。全セル最小の p_block = 0.1133 で、閾値まで約 2 桁届かない。ゲート通過ゼロのため反証 3 レンズは適用対象なし (生存 0)。
- **ハーネスは妥当** (harness_valid = true)。positive control (10× friction) が決定論的予測と厳密一致 (全セル EV シフト = −22.5p = −9×RT 2.5、p_block → 1.0)、内部整合 32/32、parquet sha256 一致。**集計 NULL は真の結果であり計測アーティファクトではない**。
- 唯一の正 EV クラスタ (EUR_JPY lb96 lowvol: EV +1.846 / +3.3321 pips) はゲート非有意で、かつ **非同時 BT 窓 (2025-07-21..2026-07-21、他 3 ペアは 2025-09-14..2026-09-14) という caveat 付き**。エッジ候補と呼べる水準にない。
- **FAIL の範囲**: この estimand (直近 rolling レンジ極値への指値 penetration fade × 15m × 固定 TP/SL × 365 日窓 × 本グリッドのパラメータ) の FAIL であって、**裁量レンジトレード全体・レンジフェード機構一般の反証ではない**。特に asia_range_fade_v1 (OPEN、別 estimand) には影響しない。
- 採用・昇格・shadow 化のアクションは一切なし。slow-MR「方向は合うが弱い」死型 (ppp / qs / rn / cc-mr) の負 prior と整合する **5 例目相当の傍証** として KB に記録する。

---

## 1. 監査 — 同型回避の根拠 (ban 監査 17 系統)

falsification 引用前の estimand 監査 (feedback_audit_past_verdicts 恒久指示) に基づき、fade / MR / レベル系の過去 verdict 全系統を突合した。

### 1.1 高リスク系統と回避根拠

| 系統 | verdict | same_form_risk | 回避根拠 (spec に反映) |
|---|---|---|---|
| H4 horizontal-level edge (2026-06 頃) | falsified — IC null (方向性エッジ無し) | **partial〜yes (本監査最大リスク)** | 「水平レベル接触 × 15m × 反転」とほぼ同型になり得るため、レンジ定義・fill・exit の差分 (指値 penetration fill / 固定 TP=0.5W / min_width=20×RT の摩擦床) を pre-reg 差分節に明示。指値化だけでは同型回避にならないことを認め、差分節を立てた上で着手 |
| sr_channel_reversal (KILL / RETIRED 恒久 2026-06-12, R2) | friction/TP 比 23.7% + タッチ成行に予測力なし | **yes/partial** | 退役主因 2 点を直接潰す設計: (1) min_width = 20×RT → TP 0.5W ≥ 10×RT で **friction/TP ≤ 10%**、(2) タッチ成行でなく **指値 penetration fill** (entry 価格改善)。リブランド再試行に当たらないことを estimand 監査で文書化 |
| asia_range_fade_v1 (OPEN — Phase 3 BT 待ち) | falsified でも採用でもない | **partial (核メカニズム同一)** | estimand 差分 3 点を事前文書化: (a) 指値 penetration fill vs 成行+rejection 確認+RSI、(b) セッション無限定 vs Asia 限定、(c) 固定 TP/SL + time stop vs range 中央/time stop。既存 LOCK 仮説の非公式先読み (P-10 型 OOS burn) 回避のための差分宣言済み |
| Horizontal sweep&reclaim (falsified 2026-06-25, 負 EV) | 流動性狩りは斜め TL 固有と結論 | **partial (機構ファミリ同一)** | 本 spec の保守的 fill (Low が指値を厳密に下回った時のみ約定) は「sweep 最中に受ける」構造であり、adverse selection 最大点で受けることを認識した上で pre-reg に負 prior として明記。entry トリガが異なるため estimand は非同一 |
| ナイトスキャルパー家系 (NOT-FEASIBLE-RETAIL, triage KILL) | エッジがスプレッド封筒の内側 | **partial** | 時間帯無条件設計だが、アジア窓の寄与分解を pre-reg 要求として継承 (min_width=20×RT の摩擦床が小 TP スキャルプ帯を構造的に除外) |
| dt_sr_channel_reversal (UNIVERSAL_SENTINEL、未 falsified) | SR 境界 fade は gross edge +2.25p が friction 3.32p で消える | **partial (生きた事前情報)** | 最重要の生きた prior として設計に直結: 指値 fill による価格改善 + tight-spread pair 中心 (EUR_USD 2.00p / USD_JPY 2.14p) で friction 側から攻める設計 |

### 1.2 非同型 (no) だが制約を継承した系統

| 系統 | verdict | 継承した制約 |
|---|---|---|
| Channel edge + wave-4 L-d 裁定 | falsified (IC null) / triage KILL | 幾何が異なる (傾斜チャネル vs 水平レンジ) が ADJACENT。L-d 条項一般形 (IC-first + 明示差分節) を適用 |
| #21 commodity_cross_range_mr (wave-6 EA-a) | explore FAIL (gate C+D 不通過) | slow-MR「方向正だが弱い」4 連敗 (ppp/qs/rn/cc-mr) を band-fade 一般への負 prior として pre-reg 明記。保有は intraday (time stop 48 bars) に制限し multi-day 隣接化を回避 |
| #18 level_failed_break_d1 (wave-4 L-a) | explore FAIL (符号逆) | D1 では極値到達 fade が符号逆 (継続) だった事実を差分節の負 prior に記載 |
| #19 round_number_major_level (wave-4 L-b) | explore FAIL (方向正だが弱い 3 例目) | 事後スライス禁止条項を継承 (USD_JPY で 00 レベル一致事象の事後切り出し禁止) |
| bb_rsi_reversion T10 | KILL (friction>edge) | 「15m MR は摩擦が edge を食う」実測前例 → headroom ゲートを名目でなく net で通す制約 (全 PnL から RT 控除) |
| mtf_regime_switch SELL asymmetry | falsified (sub-friction) | gross で見える効果の net 移送可否を pre-reg 段階で問う制約 |
| #14 ppp_real_fx_gap_reversion | explore FAIL | slow-MR 死型 prior の構成要素としてのみ関連 |
| #15 holiday_liquidity_state | FAIL クローズ | (1) explore 通過品質は OOS 生存を予測しない、(2) 事後符号反転禁止、を継承 |
| #1 sweep_reversion_eurgbp (ban ではない唯一の生存 MR 資産) | PASS (ただし max-t 選択効果未解消) | **EUR_GBP を universe から除外** (標本重複回避)。正の prior「15m 系 MR の有効ホライズン 4-12h」→ time stop 48 bars (12h) の設計根拠 |
| T11 LDN 朝 × counter-USD MR (PR #46) | 敵対的検証 REJECT | ナイフエッジ 3 点検査の手続き制約を継承 |
| oanda_labs_h4 fade (parked) | E1 校正入力専用凍結 | positioning 系特徴量は一切不使用 (E1 LOCK 非抵触) |
| #17 fx_quote_spread_state | FAIL (副産物: スプレッド異常オンセット時 RT は正常化後の 2-3 倍) | レンジ境界貫通の瞬間はスプレッド異常と相関しやすい → 名目 RT net 計算は楽観であり stressed RT 感度が必要 (§5 caveat 参照)。方向予測にスプレッド状態は不使用 |

### 1.3 共通規律の遵守 (ハーネス検証で確認済み)

- **E12 volume LOCK**: OHLC-only parquet load をコードレベルで確認 — volume/vwap 列不使用
- **BE/Trail 禁止**: 実装ゼロを確認 (固定 TP/SL + time stop のみ)
- **摩擦控除**: RT 2.14 (USD_JPY) / 2.00 (EUR_USD) / 4.53 (GBP_USD) / 2.50 (EUR_JPY) を全トレードから控除
- **カーブフィッティング禁止**: グリッド事前宣言、途中のセル追加・パラメータ調整なし

---

## 2. 手法

### 2.1 Fill モデル (保守側に設計)

- **指値 penetration fill**: 買い指値 L は bar の Low が L を**厳密に下回った**場合のみ約定、entry = L (sell 側対称)
- **SL 先着**: 同一バー内で TP と SL が両方レンジ内なら SL 先着 (保守)
- **エントリーバー TP は Close-proof 必須** (レビュー修正 C1 — fill 前価格パスの look-ahead を排除)
- **両側同時貫通バー**: エントリーなし (spec 宣言済み。ただし live 乖離要因 — §2.4 issue 2 参照)
- 境界は shift(1) で当該バーを除外 / ATR・lowvol 特徴量は前日値のみ / 1 セル 1 ポジション / time stop 48 bars

### 2.2 統計・事前宣言ゲート

- **primary gate**: recentered stationary block bootstrap (mean block 10、10,000 iter、H0 = 平均 0・依存構造保存) の **p_block < α = 0.05/32 = 0.0015625**
- 補助統計: Wilson 下限、walk-forward fold 符号、p_boot (random-entry null、500 iter)
- **p_boot はゲート統計量ではない** (meta に p_boot_is_spec_gate_statistic=false と明記)。理由 2 点:
  1. 解像度不足: add-one 平滑化での最小到達可能 p = 1/501 = 0.001996 > α = 0.0015625 — **完璧なセルでも p_boot ではゲートを通せない**
  2. friction 不変性: random-entry null も同じ RT を控除するため、摩擦水準の誤りを検出できない (positive control で確認: 10× friction でも p_boot ほぼ不変、p_block は 1.0 へ)

### 2.3 BT 窓・データ凍結

- 365 日窓。USD_JPY / EUR_USD / GBP_USD = 2025-09-14..2026-09-14
- **EUR_JPY のみ 2025-07-21..2026-07-21 (非同時窓、凍結 parquet 末尾が stale)** — spec bt_windows.caveat_eur_jpy に事前宣言済み。正 EV セルは全てこの窓上にあり、cross-pair pooling・同時レジーム主張は禁止
- 凍結: on-disk parquet sha256 == meta.data_sha256 を 4 ペアで独立再検証済み。ただし manifest は freeze-on-first-run (計測時自己証明) であり、pre-registered independent freeze の方が強い (caveat)

### 2.4 レビューで検出・修正した issue (計測前に修正)

1. **エントリーバー TP 判定の look-ahead**: simulate_exit が fill 前の価格パス (バー全体の High/Low) で TP を判定 — WR/EV を一方向に水増しするバグ。ボラ急騰バー (バーレンジ ≥ 0.5W、USD_JPY で ~21p 超) に集中発生。→ Close-proof 必須の保守形に修正 (C1)
2. **両側同時貫通スキップの look-ahead 性**: 注文時点で知り得ない bar 全体のパスに基づく fill 取り消し。現実のレスティング指値は先着側が必ず約定する。除外されるのは幅 W を丸ごと走る最も暴力的なバー = whipsaw SL 損失候補の選択的除去 (水増し方向の選択バイアス疑い)。spec 準拠ではあるが **spec レベルの live 乖離要因として caveat 化** (本レポート §5)
3. **BT 窓が parquet 末尾から導出され spec 凍結窓と契約されていない**: キャッシュ更新で窓が宣言日以降へ黙ってスライドするメタ look-ahead リスク → sha256 検証で on-disk 一致を確認 (EUR_JPY の窓差異は caveat として明示)
4. **p_boot の解像度不足** (500 iter → 最小 p 0.001996 > α): ゲートに流用すると全セル機械的 FAIL または閾値緩和圧力を生む footgun → p_block をゲート統計量として明確化
5. **random-entry null の保有時間設計が分散過小で anti-conservative**: null クローンが実トレードの realized hold_bars を複製し大半 time-exit ≈ 0−RT に集中、null mean 分布が −RT 周りに過剰に締まる → p_boot を非ゲート・参考統計に降格 (spec ゲートは recentered block bootstrap)

### 2.5 ハーネス妥当性検証 (両方向)

- **Positive control**: EUR_JPY 10× friction → 全セル EV シフトが**厳密に** −22.5 pips (= −9×RT 2.5)、N・median hold 同一、p_block → 1.0、wf_signs → [−1,−1,−1]。決定論的予測との厳密一致で PnL/摩擦会計パスと fill の friction 非依存性を pin
- 内部整合 32/32 (n_buy+n_sell==n / exit_reasons 合計==n / ev×n==total_pips / wf 符号一致)、spec cell_id == 結果 cell_id、K=32 == Bonferroni α 整合
- WR 分布 21.4%–58.0% は宣言ジオメトリ (TP 0.5W ≥ SL 0.35–0.5W → 構造的 WR ≤ ~50%) と整合。p 分布は非退化 (p_boot 0.0090–0.9836 / p_block 0.1133–1.0)
- **VERDICT: harness valid in both directions — 集計 NULL は真の結果**

---

## 3. 結果 — 全 32 セル

**事前宣言ゲート (p_block < 0.0015625) 通過: 0 セル。生存セルなし (太字対象なし)。** 全セル最小 p_block = 0.1133。p_boot は参考統計 (非ゲート、§2.2)。

### USD_JPY (RT 2.14p) — 8/8 セル負 EV

| cell_id | N | WR | wilson_lo | EV (pips) | total (pips) | p_boot | wf+folds | gate |
|---|---|---|---|---|---|---|---|---|
| USD_JPY_lb96_any_midasym | 241 | 0.432 | 0.371 | -1.67 | -403.6 | 0.3306 | 1 | FAIL |
| USD_JPY_lb96_any_sym1r | 236 | 0.479 | 0.416 | -2.19 | -517 | 0.4691 | 0 | FAIL |
| USD_JPY_lb96_lowvol_midasym | 170 | 0.441 | 0.369 | -1.7 | -289.4 | 0.3545 | 1 | FAIL |
| USD_JPY_lb96_lowvol_sym1r | 165 | 0.485 | 0.41 | -2.44 | -402.4 | 0.5214 | 1 | FAIL |
| USD_JPY_lb192_any_midasym | 201 | 0.433 | 0.366 | -4.35 | -873.4 | 0.7678 | 1 | FAIL |
| USD_JPY_lb192_any_sym1r | 199 | 0.462 | 0.394 | -4.46 | -887.1 | 0.7663 | 1 | FAIL |
| USD_JPY_lb192_lowvol_midasym | 145 | 0.434 | 0.357 | -4.27 | -618.5 | 0.7327 | 1 | FAIL |
| USD_JPY_lb192_lowvol_sym1r | 143 | 0.476 | 0.395 | -4.03 | -576.7 | 0.6966 | 1 | FAIL |

### EUR_USD (RT 2.00p) — 8/8 セル負 EV

| cell_id | N | WR | wilson_lo | EV (pips) | total (pips) | p_boot | wf+folds | gate |
|---|---|---|---|---|---|---|---|---|
| EUR_USD_lb96_any_midasym | 177 | 0.4237 | 0.3533 | -1.5899 | -281.42 | 0.3549 | 1 | FAIL |
| EUR_USD_lb96_any_sym1r | 174 | 0.4828 | 0.4097 | -1.6879 | -293.7 | 0.4260 | 1 | FAIL |
| EUR_USD_lb96_lowvol_midasym | 123 | 0.4634 | 0.3777 | -0.6016 | -74 | 0.1972 | 1 | FAIL |
| EUR_USD_lb96_lowvol_sym1r | 120 | 0.5083 | 0.42 | -1.4988 | -179.85 | 0.4057 | 1 | FAIL |
| EUR_USD_lb192_any_midasym | 170 | 0.3706 | 0.3016 | -4.6551 | -791.37 | 0.9284 | 0 | FAIL |
| EUR_USD_lb192_any_sym1r | 169 | 0.4201 | 0.3483 | -3.0609 | -517.3 | 0.7155 | 1 | FAIL |
| EUR_USD_lb192_lowvol_midasym | 125 | 0.392 | 0.3109 | -3.5975 | -449.69 | 0.7747 | 0 | FAIL |
| EUR_USD_lb192_lowvol_sym1r | 124 | 0.4355 | 0.3515 | -2.1484 | -266.4 | 0.5183 | 1 | FAIL |

### GBP_USD (RT 4.53p) — 6/8 セル負 EV、lb96 lowvol は underpowered (n=14/13)

| cell_id | N | WR | wilson_lo | EV (pips) | total (pips) | p_boot | wf+folds | gate |
|---|---|---|---|---|---|---|---|---|
| GBP_USD_lb96_any_midasym | 43 | 0.4651 | 0.3251 | -3.09 | -132.86 | 0.3436 | 1 | FAIL |
| GBP_USD_lb96_any_sym1r | 42 | 0.5238 | 0.3772 | -3.73 | -156.66 | 0.4217 | 1 | FAIL |
| GBP_USD_lb96_lowvol_midasym | 14 | 0.2143 | 0.0757 | -18.84 | -263.73 | 0.9598 | 0 | FAIL |
| GBP_USD_lb96_lowvol_sym1r | 13 | 0.3077 | 0.127 | -24.18 | -314.3 | 0.9836 | 0 | FAIL |
| GBP_USD_lb192_any_midasym | 101 | 0.5149 | 0.419 | +1.13 | +114.6 | 0.0389 | 1 | FAIL |
| GBP_USD_lb192_any_sym1r | 99 | 0.5152 | 0.418 | +0.46 | +45.8 | 0.0717 | 2 | FAIL |
| GBP_USD_lb192_lowvol_midasym | 50 | 0.42 | 0.294 | -6.97 | -348.5 | 0.6983 | 0 | FAIL |
| GBP_USD_lb192_lowvol_sym1r | 48 | 0.4167 | 0.288 | -8.23 | -395 | 0.7802 | 0 | FAIL |

注: lb96 lowvol の 2 セル (n=14/13) は eligibility 交差がほぼ空 (min_width 90.6 pips = 20×4.53 RT 床 + lowvol + 1.5×ATR cap) による小標本ノイズであり、どちら向きの証拠力も持たない (p_block=1.0 は強負平均の数学的必然)。

### EUR_JPY (RT 2.50p、**非同時窓 2025-07-21..2026-07-21**) — 正 EV 5 セルあるが全て非有意

| cell_id | N | WR | wilson_lo | EV (pips) | total (pips) | p_boot | wf+folds | gate |
|---|---|---|---|---|---|---|---|---|
| EUR_JPY_lb96_any_midasym | 263 | 0.4677 | 0.4083 | +0.1469 | +38.62 | 0.0441 | 1 | FAIL |
| EUR_JPY_lb96_any_sym1r | 256 | 0.5391 | 0.4779 | +0.8774 | +224.61 | 0.0562 | 2 | FAIL |
| EUR_JPY_lb96_lowvol_midasym | 178 | 0.5 | 0.4273 | +1.846 | +328.59 | 0.0118 | 3 | FAIL |
| EUR_JPY_lb96_lowvol_sym1r | 174 | 0.5805 | 0.5062 | +3.3321 | +579.78 | 0.009 | 3 | FAIL |
| EUR_JPY_lb192_any_midasym | 199 | 0.4824 | 0.414 | -1.1715 | -233.12 | 0.2296 | 0 | FAIL |
| EUR_JPY_lb192_any_sym1r | 197 | 0.5076 | 0.4383 | -1.9486 | -383.87 | 0.3762 | 0 | FAIL |
| EUR_JPY_lb192_lowvol_midasym | 145 | 0.5241 | 0.4433 | +1.0667 | +154.68 | 0.0759 | 2 | FAIL |
| EUR_JPY_lb192_lowvol_sym1r | 144 | 0.5417 | 0.4603 | -0.7085 | -102.02 | 0.2616 | 1 | FAIL |

(p_boot は表示上 4 桁丸め。USD_JPY/EUR_USD の元値はハーネス出力 JSON に完全精度で保存)

### 集計所見

- 32 セル中 25 セルが負 EV。正 EV 7 セル (EUR_JPY 5 + GBP_USD lb192 any 2) はいずれも p_block ゲートに遠く及ばない (min p_block = 0.1133 vs α = 0.0015625)
- 最良クラスタ EUR_JPY lb96 lowvol (EV +1.846/+3.3321、wf 3/3 fold 正、p_boot 0.0118/0.009) も: (1) p_boot は非ゲート統計かつ解像度床 0.001996 で α に構造的到達不能、(2) 非同時窓上、(3) 32 セル max-t 選択下 — エッジ候補と認定できない
- lb96 (直近 24h レンジ) が lb192 より系統的にマシ、lowvol フィルタは EUR_JPY でのみ改善方向 — ただし全て非有意の記述的観察であり、事後スライスによる主張は禁止 (継承制約 §1.2)

---

## 4. 反証結果

**適用対象なし。** 事前宣言ゲート通過 0 セルのため、反証 3 レンズ (敵対的検証パイプライン) に進んだセルはゼロ。反証詳細 = [] (空)。

- 生存 0 はレンズによる棄却ではなく、**ゲート手前での一括 NULL**。「レンズが通した/落とした」という情報は本スキャンからは得られない
- ハーネス妥当性検証 (§2.5) が negative direction の反証 (計測失敗説) を棄却済み: NULL は本物

---

## 5. 結論と次アクション

### 5.1 結論

**FAIL_NO_SURVIVORS。採用アクションなし。**

- 仮に生存セルがあった場合でも規律上は「edge 候補 — 採用は Rule 1 (fresh forward pre-reg、中間再計算禁止) + user 承認が必要」であって採用ではない。本スキャンはその手前 (ゲート 0 通過) で確定
- **FAIL の正確な範囲**: 「直近 rolling レンジ極値 (lb 96/192 bars) への指値 penetration fade、15m、固定 TP 0.5W / SL 0.35–0.5W、time stop 48 bars、majors/JPY 4 ペア、365 日窓」という本グリッドの estimand の FAIL。**裁量レンジトレード全体、セッション確定レンジ等の別定義、他 TF・他 exit 設計の反証ではない**
- asia_range_fade_v1 (OPEN、Phase 3 BT 待ち) は estimand が異なる (成行+rejection 確認+RSI / Asia 限定 / range 中央 exit) ため、本結果はその採否に対する直接証拠にならない
- 機構ファミリへの含意: slow-MR / band-fade「方向は合うが弱い or 負」系列 (ppp / qs / rn / cc-mr) と整合する追加傍証。dt_sr_channel_reversal の生きた prior (gross +2.25p が friction で消える) に対し、本スキャンは「指値 fill + friction/TP ≤ 10% 床でも majors 同時窓では正 EV が立たない」ことを示した

### 5.2 Live 乖離 caveat (将来この spec を引用する際の必須注記)

1. 両側同時貫通バーの no-entry は live で再現不能 (レスティング指値は先着約定) — 最も暴力的なバーの除外であり、live はこの BT より悪化する方向 (§2.4 issue 2)
2. 名目 RT での net 計算は楽観 — レンジ境界貫通の瞬間はスプレッド異常と相関しやすく、実測でオンセット時 RT は正常化後の 2-3 倍 (#17 副産物)。stressed RT では負 EV 側へさらに沈む
3. EUR_JPY の数字は非同時窓 (2025-07-21..2026-07-21) 上 — 同時レジーム比較・pooling 禁止

### 5.3 次アクション

1. **KB 反映**: hypothesis catalog に explore FAIL としてクローズ登録。band-fade / slow-MR 死型系列にエントリ追加。同型再試行禁止 (L-d 条項一般形: 再試行には IC-first + 本レポート差分節を超える明示差分が必要)
2. **EUR_JPY lb96 lowvol クラスタの扱い**: 追跡するなら「事後スライスの深掘り」ではなく、新規 pre-reg (同時窓 + fresh forward + 中間再計算禁止、Rule 1) が必要。ただし (a) 非同時窓、(b) max-t 選択効果、(c) slow-MR 負 prior、(d) min p_block 0.1133 の距離感を踏まえ**優先度は低 — 推奨はクローズ**。E1 供給ライン (first look 2026-10-15) 等の既存 pre-reg を優先し、資源配分 6:4 (研究:執行/摩擦) を維持
3. **ハーネス資産の回収**: recentered block bootstrap ゲート + positive control (決定論的 friction スケール検証) + freeze manifest の 3 点は再利用可能な計測資産として保全。次回スキャンでは (a) p_boot iters を α 到達可能水準へ引き上げ or 廃止、(b) pre-registered independent freeze (計測前 sha256 宣言)、(c) spec 凍結窓 == ファイル末尾の assert をハーネス内に実装
4. **user 決裁は不要** (Rule 外: 採用提案なし、tier 変更なし、資金影響なし)。本レポートは記録のみ

---
*Generated 2026-09-14 / grid spec: range_fade_spec.json (K=32, Bonferroni α=0.0015625) / harness_valid=true / gate pass 0/32 / survivors 0*
