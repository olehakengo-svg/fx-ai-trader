# 仮説カタログ + グローバル多重検定台帳 — 2026-07-24 (user 指示: 探索最大化)

**user 指示 (2026-07-24)**: 「探索を爆速で走らせる・複数本並列 OK・仮説は網羅的に」
**実装形**: 生成は無差別 (7 レンズ × 12+ 本 = 87 本生成)、入場は規律 (headroom≥10x / 再試行禁止 / 台帳)。
**方法**: 14-agent workflow (7 レンズ並列生成 → KB 再試行禁止チェック → triage)。
**Raw**: `knowledge-base/raw/analysis/hypothesis-catalog-2026-07-24.json` (87 本全量 + ban verdicts)
**前提**: [[edge-dev-postmortem-2026-07-24]] の処方箋 (§6) の実装。live は一切触らない。昇格は R1。

---

## 運用ルール (凍結)

- **並列アクティブ上限 3 本** (E1/E7 のロック走行 2 本とは別枠)。compute は安価だが OOS 窓と pre-reg スロットが希少資源 — ファミリ追加は全員の Bonferroni 分母を膨らませる
- **台帳 m=12**: 新規 7 ファミリ (sweep_reversion 再検証 / price_shock 監査 / gap / MoF / COT / month-end-conditional / VIX-unwind) + 既登録 5 (E1 / E7 phase-1 / E12-design / htf_fb recheck / sr_anti_hunt)。parked は昇格時のみ台帳入り
- **全 pre-reg 共通ハード条件**: exit 機構フリー固定ホライズン測定 / explore 窓で headroom≥10x 実証後に LOCK / multi-week は swap を EV に純額込み / E1・E7 ロック窓は覗かない / banned 隣接ファミリは pre-reg に明示差分節を必須

## 凍結探索プロトコル (wave-0 ファミリ、実行前凍結)

- **データ**: `data/cache/massive/` parquet (12y)。**explore = 2014-01-01〜2021-12-31 / OOS = 2022-01-01〜2026-06-30**。OOS は候補凍結後に 1 回だけ接触
- **測定**: exit-free forward MFE/MAE + 方向純移動、h ∈ {4h, 12h, 24h, 72h, 120h}
- **統計**: event-block bootstrap、BH-FDR q=0.10 (wave ファミリ横断)、headroom 判定 = MFE p50 ≥ 10× ペア RT friction (理論値 + floor 1.30p 感度)
- **例外**: MoF 介入は事象が 2022 以降に集中し temporal split 不能 → 全事象記述統計 + permutation null + **将来介入への forward pre-reg** 形式に切替 (低 N 設計)

## Wave 構成 (score = prior × headroom × testability × 独立性)

### wave-0-now (本日着手、in-repo データ)
| score | 仮説 | 骨子 |
|---|---|---|
| 72 | **sweep_reversion_eurgbp 再検証** | 12.4y Bonferroni 生存 (t=4.46)・execution 死のみの唯一資産。exit-free 固定ホライズンで 12.4y 再測定 (exit-artifact 排除確認)。gate 修復は別線 (P-S1(a) R1 決裁パケット準備中、トリガ unique N≥10 まであと 2 イベント) |
| 58 | **price_shock 5席 exit-free 監査** | 12y+Bonferroni 昇格済みだが BE/Trail artifact 暴露後に未再測定の検証負債。shock 幅なら headroom≥10x が期待できる — explore 窓で確認 |
| 47 | **weekend_gap_fill_multiday** | KB 死亡記録 54 件に不在 = 未検証。gap≥20p のみ対象 (headroom gate)。トラップされた保有者の強制解消メカニズム。バックグラウンド線 — explore IC が綺麗な場合のみ pre-reg スロット消費 |

### wave-1-fetch (公開データ取得後)
| score | 仮説 | 骨子 |
|---|---|---|
| 66 | **mof_intervention_proximity_usdjpy** | カタログ中最強メカニズム (政策的強制カウンターパーティ、300-500p vs RT 2.14p = 100x+ headroom)。S4 は data-blocked (falsified ではない) — 財務省四半期開示リストで解除。fetch 即時開始 |
| 50 | **cot_spec_positioning_extreme_weekly** | 機関投機筋 (E1 のリテールと別母集団、部分独立ペナルティ適用済)。週次・数十年ヒストリで蓄積待ちゼロ。E1 データは覗かない |
| 43 | **equity_conditional_monthend_rebalance** | 条件付き月末フロー (株指数の月中騰落に比例)。**棄却済み無条件 WMR-fix と隣接** — explore IC が無条件形を明確に上回らなければ即 kill |
| 41 | **vix_riskoff_carry_unwind_jpy_crosses** | VIX スパイク → キャリー強制解消の continuation。E20 凍結 (carry-rank/mom63) とは別 estimand だが pre-reg 時に隣接性の敵対的チェック必須 |

### wave-2-accumulating (蓄積待ち・受動)
E7 phase-1 (verdict 08-28) / E1 (first look 10-15) / E12 volume (forward pre-reg 🔒 LOCKED 2026-07-29、first look 2027-02-05 — 「~3ヶ月」目安は [[e12-volume-forward-prereg-2026-07-29]] §6 で置換) / htf_fb recheck (受動、実測ペースでは deadline 2027-01-31 に N≈15-30 で stale クローズ公算) / sr_anti_hunt N≥30 (受動)

### parked (台帳外)
oanda_labs_h4 fade (**E1 と同一メカニズムの double-bet — E1 校正入力専用**) / fred_cpi surprise (E7 重複) / tsmom weekly (E20 隣接) / mafe exit 復活 (正 EV ホスト不在) / yield_spread 残差 (07-24 口頭評価 HOLD) / sub-friction gross 構造 / E15 型無条件イベント窓

### BANNED (生成 87 本中 2 本除去)
london-4pm-fix-conditional-reversal (= london_fix_reversal の再着せ替え) / copper-china-demand-aud (= E4 lead-lag 同型)

## 実行順序 (triage 決定)

1. 本日: sweep_reversion 再検証 + price_shock 監査 起動 (アクティブ 2 本)
2. 本日: MoF fetch 発火 → 着地次第 3 本目のアクティブ線に
3. gap はバックグラウンド explore (スロット消費なし)
4. COT / month-end / VIX-unwind は今週 fetch まで、wave-0 解決に応じて順次昇格
5. 各 wave-0 線は explore verdict まで ~1 日

## 台帳 (verdict 追記式 — 全結果 PASS/FAIL 問わず記録)

| # | family | 状態 | verdict |
|---|---|---|---|
| 1 | sweep_reversion 再検証 | **explore 完了 2026-07-24** | ✅ **exit-free で生存** — 12h net med +5.10p/mean +7.72p (p<1e-4)、RT3.0p 控除後 +4.72p、11/13 年正。exit-artifact 説を棄却。同一標本の限界 (max-t 選択効果は新データでのみ解消可) → P-S1(a) 決裁パケットへ供給 |
| 2 | price_shock 監査 | **監査完了 2026-07-24** | ✅ demotion flag 0/5 (クリーニング後も全席 p=0.0001、headroom 6.5-35x)。⚠️ **feed artifact 発見**: 土曜行 + spike-revert 不良プリントが各席トレードの 4-12.8% を汚染、grid ev_pip は過大 (USD_CAD 97.9→42.4p)。⚠️ EUR_AUD/USD_CAD/AUD_JPY は pre-2021 OOS が 0 と分離不能 → regime watch (tier action なし) |
| 3 | weekend_gap | **OOS verdict 完了 2026-07-24 (単一実行、期日 7 日前倒し)** — [[weekend-gap-oos-prereg-2026-07-24]] §11。**R1 step① 完了 (同日)**: 日曜 spread 12 週末遡及実測 | ✅ **family PASS 候補 (arm B)** — pooled exGBP 4h: N=177/112wk、gross +15.60p (weekend-block p<1e-4)、stressed-net (−6.56p) **+9.04p**、headroom 24.8p≥21.9p、knife-edge 4/4 flip なし。❌ arm A は 12h p=0.1189 で BH 落ち → クローズ。**R1 step① 実測**: 3× 仮定は USD_JPY で楽観的 (実測 p50 7.55p) だが**実測 RT 再計算で EV +7.90p / p90 +3.26p = PASS 保存**。spread は 22:01 UTC で段差崩落の二値構造 (stage-2 入力)。**残 = step② stage-2 執行 pre-reg (起案中) → step③ user 最終承認** |
| 4 | mof_intervention | **forward pre-reg 🔒 LOCKED (2026-07-24、期限 12 日前倒し)** — [[mof-intervention-forward-prereg-2026-07-24]]、verdict = Q2 開示 +10d (backstop 09-30、registry 登録済) | 識別 rule (X,Y)=(2.0, 0.25%) 裁量ゼロ凍結 (hit 6/7、FP 5.03%)。**candidate S={04-30, 05-06} 凍結 → E-D 予測下の PASS ≒ 両日とも開示介入日** (超幾何 α=0.10、k_eff 規約)。E-C: h*=10d、SELL 予測、band [−319.8, −43.6]p。敵対的レビュー全反映、P-10 forward 未計算 attestation 付き |
| 5 | cot_spec_extreme | **explore 完了 2026-07-24 — ❌ FAIL、pre-reg 起案せず** | net_pct_oi 3y percentile p10/p90 エピソード・オンセット × {1w,2w,4w} exit-free (release-lag +3 営業日凍結、lookahead assert 通過、SNB 2015-01 で方向マップ手検証)。**BH-FDR q=0.10 生存 0/36 (primary) + 0/6 (pooled)** — min p 0.0077 (GBP 2w cont、単一ホライズン孤立) > 閾値 0.0028。pooled 1w rev +22p は SNB 1 件が 63% (除外 median +0.9p)。サイド符号不一致・tercile 単調性 0/6・年次振動 = 点推定 incoherent (underpowered ではない)。**同型再試行 (percentile 窓/閾値変種) 非推奨。ban 範囲は「net_pct_oi レベル極値×週次」限定 — Δnet/flow・commercial 側は新 family として可**。OOS 2022+ は COT×価格ジョイント未接触のまま保存。`reports/cot_extreme_explore-2026-07-24.md` |
| 6 | equity_monthend_conditional | **explore 完了 2026-07-28 (TV)** — [[wave1-tv-explore-protocol-freeze-2026-07-28]] | ❌ **FAIL** — primary IC(1d) −0.052 p=0.608 (N=96ヶ月×6ペア)。無条件 WMR-fix NULL に続き条件付き形も死亡 → 月末リバランス系閉鎖。3d/5d の逆符号 IC (−0.26/−0.29) は事後選択・非単調で新規主張にしない。`reports/wave1-tv-explore-monthend-vix-2026-07-28.md` |
| 7 | vix_carry_unwind_continuation | **explore 完了 2026-07-28 (TV)** — 同上 | ❌ **FAIL (knife-edge)** — pooled short 3d +46.2p/event、**厳密 p=0.050091** (2²³ 全列挙、シード非依存) > BH 閾値 0.05 (m=2)。9e-5 差だが凍結ルールどおり kill、事後に閾値を動かさない。headroom 32-55× は全ペア通過 (power 不足型 FAIL)。**同型再試行 (VIXレベル閾値×JPYクロスshort×固定1-5d) 禁止**、再挑戦は新データ + 隣接差分節必須。OOS 2022+ 未接触保存 |
| 8 | E1 positioning | LOCKED 走行中 | first look 2026-10-15 |
| 9 | E7 surprise phase-1 | LOCKED 走行中 | verdict 2026-08-28 |
| 10 | E12 volume design | **forward pre-reg 🔒 LOCKED 2026-07-29 (W3-3 登録アクション、BH/wave スロット非消費・測定ゼロ)** — [[e12-volume-forward-prereg-2026-07-29]]。役割 split 凍結: backfill 2024-02-27〜2026-07-29 = explore / go-forward ≥2026-07-30 = OOS (first_bar は DB 実測で全 7 契約 2024-02-27T05:00Z 確定)。S1 設計無変更凍結 = unsigned abnormal volume primary + 対価格 momentum **増分 IC 必須検定** (BVC-signed は非 claimable secondary) | 未測定 — first look **2027-02-05** (cutoff 2027-01-31、registry `e12-volume-first-look-deadline`。wave-2 の「~3ヶ月」目安は検定力根拠付きで置換)、陳腐化 review 2026-11-30。**E13 再入場余地 = E12 unsigned primary PASS 時のみ MASSIVE tick volume 12y 拡張を新 family/R1 で可、FAIL 時は E13 ban 継続** (敵対的検証 [W3-3] 注記)。歴史 unlock (Databento) は user 決裁事項として記録のみ |
| 11 | htf_fb recheck | 受動 registry | deadline 2027-01-31 |
| 12 | sr_anti_hunt N≥30 | 受動 | — |
| 14 | ppp_real_fx_gap_reversion | **explore 完了 2026-07-29 (同日、単独 wave)** — [[ppp-real-fx-explore-prereg-2026-07-29]] | ❌ **FAIL** — primary IC 42bd +0.113 p=0.129 (符号は回帰方向・年次 7/8 正だが有意水準未達) + quintile 隣接違反 3 (許容 1)。キャリー直交 102% / headroom 79-115× / 年次集中なしは通過 = 「方向は合うが弱い」型。explore 窓は USD 一方的割高 regime (z>2: 96 vs z<−2: 5) で割安側回帰がほぼ観測不能だった。**同型再試行禁止 (5y-z 月次×21-63bd)、再挑戦は実質金利差込みモデル等 + 明示差分 or 2022+ 込み split 再設計のみ**。OOS 未接触保存。`reports/ppp-real-fx-explore-2026-07-29.md` |
| 16 | cot_commercial_flow_weekly (W3-1) | **explore 完了 2026-07-29 (同日)** — [[cot-commercial-flow-explore-prereg-2026-07-29]] (単独 wave m=1、#5 の明示 carve-out。敵対的検証 6 条件解決済み) | ❌ **FAIL クローズ** — primary IC +0.0186 p=0.5652 (gate i ✗) + サイド split 非対称 (flow>0 −0.013 / flow<0 +0.076、gate iv ✗ = #5 と同じ incoherence 死型)。**鏡像恒等の実証 corr(Δcomm, −Δnoncomm)=0.93** = COT の母集団は実質 1 モダリティ。**同型再試行禁止 = COT Δ/flow×週次固定ホライズン全変種 (母集団問わず)** — #5 と合わせ週次 COT 設計空間は実質全クローズ。OOS 未接触。`reports/cot-commercial-flow-explore-2026-07-29.md` |
| 17 | fx_quote_spread_state (W3-2) | **explore 完了 2026-07-30 (同日)** — [[fx-quote-spread-state-explore-prereg-2026-07-30]] (単独 wave m=1。敵対的検証 6 条件解決済み: probe 7/7 HTTP200 / coverage 全 3 ペア×8 年 PASS / **headroom 事前ゲート PASS 13.5× fwd return 非接触** / entry=正常化後凍結 / NY ローカル grid + DST 除外 / primary fwd 24h 1 本) | ❌ **FAIL クローズ** — primary −0.237σ (−9.5p) 両側 p=**0.3228** (gate i ✗、knife-edge 外)。gates ii-vi 全通過 = 方向 (risk-ON、prior と逆) は 3 ペア・6 年一貫だが null と区別不能の弱効果死型 (#14 同型)。**副産物 = 反実仮想 onset-entry RT 5.9-9.5p (正常化後の 2-3 倍) — デスゾーン防御の初の実測正当化**。**同型再試行禁止 = 実測 BBO スプレッド状態 (オンセット/レベル/正常化) × 時間固定ホライズン fwd 方向 全変種**。OOS 未接触。スプレッドパネル (78k サンプル、`data/external/quote_spread/`) は摩擦研究インフラとして残置。`reports/fx-quote-spread-state-explore-2026-07-30.md` |
| 15 | holiday_liquidity_state (縮約 a+c) | **explore+OOS 完了 2026-07-29 (同日)** — [[holiday-liquidity-explore-prereg-2026-07-29]] (背景線、BH 分母独立。レグ b/d は wave-2 検証で削除済み) | ❌ **FAIL クローズ** — レグ c は explore で符号逆 (反転仮説に対し**継続** −7.61p p=0.973、機械 kill)。レグ a は explore PASS (+7.89p p=0.0163、LOYO 7/7) → **OOS 単一接触で崩壊** (+2.06p p=0.3145、最小効果 2.06<5p、LOYO 2025 除外で符号反転)。**同型再試行禁止 = 祝日/休場フラグ×日次 D1-D2 exit-free 全変種 (継続方向への事後反転含む)**。explore 通過品質 (p+LOYO) は OOS 生存を予測しない実例 13 件目。`reports/holiday-liquidity-explore-2026-07-29.md` |
| 13 | gotobi_tokyo_fix_usdjpy | **explore 完了 2026-07-28 (同日)** — [[gotobi-calibration-explore-prereg-2026-07-28]] | ✅❌ **較正成功 / 昇格 kill** — 規約 B (前営業日繰り) で公表効果を gross 回収 (+1.92p p=0.0032、N=557 vs 1352) = **測定ハーネス正当性を実証** + 規約矛盾解決。ただし効果は sub-friction (+1.9p < RT 2.14p)、P1 テール cell +1.38p p=0.43 → kill rule 機械的適用で family クローズ。OOS 未接触。**gotobi/仲値系の再昇格提案は執行コスト構造の変化なしに不可** (tokyo_nakane_momentum 同 family)。`reports/gotobi-calibration-explore-2026-07-28.md` |

| 18 | level_failed_break_d1 (wave-4 L-a) | **explore 完了 2026-07-31 (同日)** — [[level-failed-break-d1-explore-prereg-2026-07-31]] (🔒 凍結コミット 5ea2d4dc 後に測定。敵対的検証 12 条件解決済み) | ❌ **FAIL クローズ** — primary pooled fade 5d **−4.91p (符号逆)** p=0.702 (N=290、週 block perm、knife-edge 圏外)。年次 3/8・LOYO 7/8 負・net EV −8.8p。**同型再試行禁止 = 長 lookback 極値の D1 close 確定失敗ブレイク×fade×multi-day 全変種。継続方向も p≈0.30 n.s. — 事後符号反転主張禁止 (holiday レグ c 前例)**。htf_fb 機構は D1/55d へ外挿不能と実証 (#11 には影響なし)。**正の副産物 = Gate A 8/8: D1 イベント系 headroom (MFE5d p50 51-92p ≥ 10×RT) は実在 — 律速は摩擦でなく signal**。QA 2 件 (Monday bar UTC 誤ラベル修正 / cross-check 7 ペア符号・量級一致)。OOS 非接触。`reports/level-fb-d1-explore-2026-07-31.md` |
| 19 | round_number_major_level (wave-4 L-b) | **登録済み queued** — 敵対的検証 GO-WITH-CONDITIONS (12 条件、[[level-family-adversarial-verification-2026-07-31]] §4)。#18 explore verdict 後に単独 wave。準備 (level grid / coverage assert / mof 重複下ごしらえ) は look 非該当につき並行可 | 未着手 |

## wave-4 候補 triage (2026-07-31、敵対的検証済み — `raw/analysis/level-family-adversarial-verification-2026-07-31.md`)

**発端**: user 委任 2026-07-30「並行チャネル、水平線でエッジ開発。TV で勝てる方向性を探す」+ 07-31 補強。
候補 5 本 (payload `raw/analysis/level-family-candidates-2026-07-31.json`) → 生存 2 (L-a=#18 / L-b=#19、水平線側)。
**並行線側は 3 候補全滅** — 検定回避ではなく敵対的検証によるデータ忠実な triage KILL (ban ではない、各再入場経路あり):

- **L-c anchored_vwap_deviation_reversion**: ❌ KILL — 機構が実約定 volume を要求するが FX spot に不在。tick 加重は anchored average price に退化 = ppp 型 slow reversion 死型 + E2「tick volume 弱 proxy」/E13 ban 隣接 + power 最弱 (explore 64-128)。**再入場 = E12 unsigned PASS 後に実約定 volume (CME) アンカー版を新 family/R1 でのみ。tick-volume 版再提案は E2/E13 の再着せ替えとして棄却対象**
- **L-d d1_regression_channel_reversion**: ❌ KILL — **ban scope 裁定 on-record: 06-25 決定は「この特徴量セット・チャネル定義では」と自己 scope + 別 lookback を IC-first で明示許容 → identity-BANNED ではなく ADJACENT**。kill 理由 = 同一幾何が 15m massive-N (48-59k) で決定的 null + 最近傍死型 (ppp/holiday/quote-spread「方向は合うが弱い」) 3/3 + price_shock family との低独立性 + スロット希少 (**power は足りる — kill 理由ではないと正直記録**)。再入場経路なし (同構造)。将来の並行線提案は決定文条項 (回帰±2σ/swing平行以外 + IC-first + 明示差分節) に従う
- **L-e d1_diagonal_trendline_sweep**: ❌ KILL — 機構の唯一の支持 (trendline_sweep live WR80%) が 12y で崩壊済み (41-44%、gross +0.94p sub-friction)。死んだ戦略の TF 変え再訴訟に近く、差分軸 (D1 化・multi-day・低頻度) は L-a が上位互換で担う + DoF 面が set 中最大。**再入場 = L-a explore gates 通過後に限り、線構築参照実装 + 全 DoF 凍結 + 敵対的再検証付き新提案として可。L-a explore FAIL なら D1 diagonal 変種も不可 (同 modality 供給死)**

## wave-2 候補 triage (2026-07-28、敵対的検証済み — `raw/analysis/new-angle-adversarial-verification-2026-07-28.md`)

- **ppp_real_fx_gap_reversion**: GO-WITH-CONDITIONS — **次の単独 wave** (強 prior 家系)。LOCK 前解決必須: 5y rolling z の explore 窓崩壊 (pre-2014 FX ソース or 窓再設計) / スワップ会計一本化 / 極値レグ secondary 降格 / USD 因子ブロック bootstrap / CPI NSA・vintage
- **holiday_liquidity_state_family**: 2 レグ縮約 (祝日前日 + 米休場翌日反転) の**背景 explore** (スロット非消費、BH 分母独立)。レグ (b)/(d) は power 死の実測反証で削除。祝日カレンダー定義検証 + structural_events refresh 前提
- **vol_state_gates**: ✅ **registry 登録済み 2026-07-29** — `volstate-split-htf-fb-recheck` + `volstate-split-weekend-gap-recheck` (観測前 forward split 宣言、look 追加なし、選択に使わない)
- **pre_fomc_fx_transcription**: ❌ triage KILL (headroom 4-12x < 10x ゲート、power 不能)。再入場 = E7 PASS 後の新 pre-reg のみ
- **move_bondvol_shock_jpy_unwind**: ❌ triage KILL (killed-VIX とイベント集合重複 + post-2022 反転 + 現行 split で検証不能)。再入場 = 将来の split 再設計 or forward 型のみ
- rejected_as_banned 3 系統 (MSCI/FTSE リバランス、equity-stress JPY re-dress、GPIF quarter-end) は検証で支持済み

## wave-0 実行記録 (2026-07-24、全線敵対的レビュー通過 — INVALID ゼロ)

- **成果物**: `tools/{sweep_reversion_exitfree_reverify,price_shock_exitfree_audit,weekend_gap_fill_explore,mof_interventions_fetch,build_cot_panel}.py` / `bt-results/*-2026-07-24.json` ×5 / `reports/*-2026-07-24.md` ×5 / `data/external/{mof_interventions.csv,cot_fx_panel.parquet}`
- **sweep_reversion**: 凍結トリガの完全再現 (N=543/t=4.46 一致) の上で exit-free 生存を確認。エッジは **~12h 平均回帰** (MFE/MAE 非対称は 4h/12h のみ、≥24h で反転 — 長ホールドへ外挿禁止)。レビュー指摘: bar-time≠wall-clock (週末跨ぎ ~11%)、72h/120h bootstrap は窓重複で過小分散
- **price_shock**: トリガ忠実度 1.003-1.020 で 5 席再現。**横断発見 = MASSIVE feed の土曜行 + 不良プリント汚染** (BT 全般に影響しうる infra 課題 → chip 化)。pre-2021 pure-OOS が有意なのは EUR_GBP (+6.1p p=4e-4) と NZD_JPY (+9.4p p=1e-3) のみ
- **weekend_gap**: fill は速く短命 (t-half 中央値 1-2h、full-fill 9-15h、120h fill 率 82-84%)。「爆速で走らせつつ FP を作らない」原則どおり、狭候補のみ OOS へ
- **MoF**: 開示ラグを利用した観測前 pre-reg 機会は**時限付き** — Q2 開示 (~2026-08) 前に LOCK 必須
- **横断規律メモ**: 週末境界の DST 問題 (21:00 UTC 固定 vs 実クローズ 22:00 冬時間) は pre-reg で定義凍結必須。bootstrap p の床 (1/(N+1)) は「p<1e-4」表記に統一
