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
| 4 | mof_intervention | **verdict 執行 2026-08-18 (開示 08-07 着地 +11d、期日 1 日超過を明記)** — [[mof-intervention-forward-prereg-2026-07-24]] §10 | 🟡 **PARTIAL — park (prior 減)、次の円買いエピソードで 1 回限り同一仕様再判定** (registry `mof-next-episode-reverdict`)。**E-A primary ✅ PASS p=0.0143** (D={04-30 ¥6.28T, 05-04 ¥0.78T, 05-06 ¥4.68T} 全て円買い、凍結 S={04-30,05-06} と overlap 2/2、S 再導出一致、rule ±20% 摂動不変) = **プロジェクト初の forward primary 的中・real-time 検知器の実証**。05-04 取り逃しは covert 型 (+0.20% close、2022-10-24 と同型)。E-D も的中 (k=3∈[2,5]、最大単日 ¥6.28T≥3T)。**E-C ❌ FAIL**: 予測 SELL band [−319.8,−43.6]p に対し median net_h10 **+188.1p (3/3 正、h1/h2/h5 も正)** = 2026-05 エピソードは完全リトレース+反転 (有効 N=1 エピソード、事後の符号反転主張は禁止)。**将来の介入系 family への一次 prior: 「介入後 SELL drift は 2026 で符号逆」**。Variant B は stage-2 に進めない。手続き教訓 = 四半期開示型トリガは予想着地日を deadline に刻む |
| 5 | cot_spec_extreme | **explore 完了 2026-07-24 — ❌ FAIL、pre-reg 起案せず** | net_pct_oi 3y percentile p10/p90 エピソード・オンセット × {1w,2w,4w} exit-free (release-lag +3 営業日凍結、lookahead assert 通過、SNB 2015-01 で方向マップ手検証)。**BH-FDR q=0.10 生存 0/36 (primary) + 0/6 (pooled)** — min p 0.0077 (GBP 2w cont、単一ホライズン孤立) > 閾値 0.0028。pooled 1w rev +22p は SNB 1 件が 63% (除外 median +0.9p)。サイド符号不一致・tercile 単調性 0/6・年次振動 = 点推定 incoherent (underpowered ではない)。**同型再試行 (percentile 窓/閾値変種) 非推奨。ban 範囲は「net_pct_oi レベル極値×週次」限定 — Δnet/flow・commercial 側は新 family として可**。OOS 2022+ は COT×価格ジョイント未接触のまま保存。`reports/cot_extreme_explore-2026-07-24.md` |
| 6 | equity_monthend_conditional | **explore 完了 2026-07-28 (TV)** — [[wave1-tv-explore-protocol-freeze-2026-07-28]] | ❌ **FAIL** — primary IC(1d) −0.052 p=0.608 (N=96ヶ月×6ペア)。無条件 WMR-fix NULL に続き条件付き形も死亡 → 月末リバランス系閉鎖。3d/5d の逆符号 IC (−0.26/−0.29) は事後選択・非単調で新規主張にしない。`reports/wave1-tv-explore-monthend-vix-2026-07-28.md` |
| 7 | vix_carry_unwind_continuation | **explore 完了 2026-07-28 (TV)** — 同上 | ❌ **FAIL (knife-edge)** — pooled short 3d +46.2p/event、**厳密 p=0.050091** (2²³ 全列挙、シード非依存) > BH 閾値 0.05 (m=2)。9e-5 差だが凍結ルールどおり kill、事後に閾値を動かさない。headroom 32-55× は全ペア通過 (power 不足型 FAIL)。**同型再試行 (VIXレベル閾値×JPYクロスshort×固定1-5d) 禁止**、再挑戦は新データ + 隣接差分節必須。OOS 2022+ 未接触保存 |
| 8 | E1 positioning | LOCKED 走行中 | first look 2026-10-15 |
| 9 | E7 surprise phase-1 | **verdict 完了 2026-08-17 (期日 08-28 の 11 日前倒し)** — [[e15-e7-event-modality-prereg-2026-07-18]] §13 | ❌ **FAIL (discovery 段、選抜 0/24 → m₁=0、OOS 非接触保存)** — 実効 12 combo (θ=0.5) の time-exit EV 全て負 (−0.31〜−8.15p、blocks 41–62) = サプライズ方向 drift の符号が系統的に逆 (SIGN-FLIP 記述記録、fade 追試は新 family + 敵対的検証必須で phase-0 CPI fade C5 が負の prior)。機械ガード: 台帳再現 13/13 + census §3.3c 完全一致 + 符号/estimand 手計算 spot check。**§8 固定分岐: 両 phase PASS=0 → イベントモダリティ (カレンダー/サプライズ × M15) 枯渇 → E12 を供給ライン主候補へ格上げ**。再試行禁止 = NFP/CPI headline z × sign-follow × M15 全変種 |
| 10 | E12 volume design | **forward pre-reg 🔒 LOCKED 2026-07-29 (W3-3 登録アクション、BH/wave スロット非消費・測定ゼロ)** — [[e12-volume-forward-prereg-2026-07-29]]。役割 split 凍結: backfill 2024-02-27〜2026-07-29 = explore / go-forward ≥2026-07-30 = OOS (first_bar は DB 実測で全 7 契約 2024-02-27T05:00Z 確定)。S1 設計無変更凍結 = unsigned abnormal volume primary + 対価格 momentum **増分 IC 必須検定** (BVC-signed は非 claimable secondary) | 未測定 — first look **2027-02-05** (cutoff 2027-01-31、registry `e12-volume-first-look-deadline`。wave-2 の「~3ヶ月」目安は検定力根拠付きで置換)、陳腐化 review 2026-11-30。**E13 再入場余地 = E12 unsigned primary PASS 時のみ MASSIVE tick volume 12y 拡張を新 family/R1 で可、FAIL 時は E13 ban 継続** (敵対的検証 [W3-3] 注記)。歴史 unlock (Databento) は user 決裁事項として記録のみ |
| 11 | htf_fb recheck | 受動 registry | deadline 2027-01-31 |
| 12 | sr_anti_hunt N≥30 | 受動 | — |
| 25 | e23_cb_statement_text (中銀声明テキスト差分、scan 第3次 §E23) | **採用 — S2 診断枠 2026-08-18** — [[e23-cb-text-adjudication-s2-2026-08-18]] (ゲート = E7 verdict、08-17 前倒し確定で解除。改訂 WIP 原則発動: 能動ライン 0 本)。claim = PR #188 + queue ticket | 未測定 (explore スロット未消費)。**probe 実測**: 凍結可能な外部特徴量 = Apel-Grimaldi 2012 辞書 (primary 候補、全窓先行・ライセンス制約なし) / Trillion Dollar Words FOMC-RoBERTa (公開・2023-05 凍結、**CC BY-NC = user 決裁事項**) / IMF WP 2025/109 は複製データ未確認 = 使用不可。**負の prior を明記**: 同一イベント面で E15+E7 二重 FAIL 済み — 残余仮説は「数値に現れないテキストニュアンス」のみ。**S2 設計方向 = multi-CB パネル** (Fed/ECB/BOE/BOJ+、blocks 4-6 倍 — FOMC 単独は OOS ~20 blocks で C3/C5 帯が既知)。残 = コーパスハーネス + testable form → 敵対的検証 → LOCK |
| 26 | family_c_rate_anchor_deviation (rates-anchor、user 水平線理論 機械核 v2) | **採用 — 臨時裁定 (改訂 WIP 原則: 能動枠 0 本) + user 直接承認 2026-08-19「進めて」、explore 枠 1/3 消費** — [[family-c-rate-anchor-explore-prereg-2026-08-19]] (片側 LONG onset イベント × +21bd、year-matched placebo = drift 直交内蔵、explore 2014-2021 介入ゼロ窓)。claim = PR #197 + edge-dev レーン承認 (cross-session)。敵対的検証 → 凍結 → two-pass 同日実行 | ❌ **FAIL (explore、2026-08-19 同日、OOS 2022+ 非接触封印)** — N=41 (Z_th=1.5 機械選定): **gross −20.5p / swap −1.6p / net −24.2p (adverse −32.1p)**、gate C demeaned p=0.527 (timing 超過なし)、LOYO 符号不安定 (JPY 増価年 2015/16/18 が負殺)。median +1.4p WR 51% = 左テール支配。h5 診断: 初週 +10.9p バウンス→21bd で逆転 (非 claim)。ablation: 価格のみ z はさらに悪い −65.8p (Jaccard 0.167 = 識別作動)。**クローズ = 日次金利差アンカー帯 × USD_JPY × 帯下 LONG × 5-63bd 全変種。水平線理論の機械核 v2 死亡、裁量スタック残余 = 執行層/exit 層のみ**。power caveat: MDE 131p だが点推定負 = 符号情報を持つ FAIL。詳細 §11 |
| 23 | e21_human_signal_stream (帰属分解、scan 第3次 §2.2) | **S2 標本量実測 完了 2026-08-17** — [[e21-attribution-s2-2026-08-17]] (診断枠、供給ラインとして数えない。WR/N 統計ではなく会計恒等分解) | ✅ **診断完了・クローズ (2026-08-18)** — user 提供の外部業者 CSV で帰属分解実行: 7週 N=247、+54,052円 = swap 28% + 価格 72%、**日次ブロック perm p=0.32・最大単一トレード寄与 68%・月次符号不安定 = 識別可能な α なし**。保有中央値 1.2h・ON 5% = 「長期キャリー」自己申告と不一致。3 ソース (bot 口座 40 往復/旧個人口座 45 往復/外部 247 往復) 全てで α 不検出 = **human-signal-stream 系統クローズ (α≈0 は情報、scan §2.2 想定どおり)**。非 claim 記述所見: 保有 8h+ 勝ち/<1h 負けの方向一貫 — 検証は forward 明細継続提供 + 観測前凍結の新 family のみ (月次スキャン再評価)。分解は観測前凍結なしの記述統計として実行された旨を doc に明記 (会計恒等式ゆえ verdict は頑健)。registry 消化済み |
| 14 | ppp_real_fx_gap_reversion | **explore 完了 2026-07-29 (同日、単独 wave)** — [[ppp-real-fx-explore-prereg-2026-07-29]] | ❌ **FAIL** — primary IC 42bd +0.113 p=0.129 (符号は回帰方向・年次 7/8 正だが有意水準未達) + quintile 隣接違反 3 (許容 1)。キャリー直交 102% / headroom 79-115× / 年次集中なしは通過 = 「方向は合うが弱い」型。explore 窓は USD 一方的割高 regime (z>2: 96 vs z<−2: 5) で割安側回帰がほぼ観測不能だった。**同型再試行禁止 (5y-z 月次×21-63bd)、再挑戦は実質金利差込みモデル等 + 明示差分 or 2022+ 込み split 再設計のみ**。OOS 未接触保存。`reports/ppp-real-fx-explore-2026-07-29.md` |
| 16 | cot_commercial_flow_weekly (W3-1) | **explore 完了 2026-07-29 (同日)** — [[cot-commercial-flow-explore-prereg-2026-07-29]] (単独 wave m=1、#5 の明示 carve-out。敵対的検証 6 条件解決済み) | ❌ **FAIL クローズ** — primary IC +0.0186 p=0.5652 (gate i ✗) + サイド split 非対称 (flow>0 −0.013 / flow<0 +0.076、gate iv ✗ = #5 と同じ incoherence 死型)。**鏡像恒等の実証 corr(Δcomm, −Δnoncomm)=0.93** = COT の母集団は実質 1 モダリティ。**同型再試行禁止 = COT Δ/flow×週次固定ホライズン全変種 (母集団問わず)** — #5 と合わせ週次 COT 設計空間は実質全クローズ。OOS 未接触。`reports/cot-commercial-flow-explore-2026-07-29.md` |
| 17 | fx_quote_spread_state (W3-2) | **explore 完了 2026-07-30 (同日)** — [[fx-quote-spread-state-explore-prereg-2026-07-30]] (単独 wave m=1。敵対的検証 6 条件解決済み: probe 7/7 HTTP200 / coverage 全 3 ペア×8 年 PASS / **headroom 事前ゲート PASS 13.5× fwd return 非接触** / entry=正常化後凍結 / NY ローカル grid + DST 除外 / primary fwd 24h 1 本) | ❌ **FAIL クローズ** — primary −0.237σ (−9.5p) 両側 p=**0.3228** (gate i ✗、knife-edge 外)。gates ii-vi 全通過 = 方向 (risk-ON、prior と逆) は 3 ペア・6 年一貫だが null と区別不能の弱効果死型 (#14 同型)。**副産物 = 反実仮想 onset-entry RT 5.9-9.5p (正常化後の 2-3 倍) — デスゾーン防御の初の実測正当化**。**同型再試行禁止 = 実測 BBO スプレッド状態 (オンセット/レベル/正常化) × 時間固定ホライズン fwd 方向 全変種**。OOS 未接触。スプレッドパネル (78k サンプル、`data/external/quote_spread/`) は摩擦研究インフラとして残置。`reports/fx-quote-spread-state-explore-2026-07-30.md` |
| 15 | holiday_liquidity_state (縮約 a+c) | **explore+OOS 完了 2026-07-29 (同日)** — [[holiday-liquidity-explore-prereg-2026-07-29]] (背景線、BH 分母独立。レグ b/d は wave-2 検証で削除済み) | ❌ **FAIL クローズ** — レグ c は explore で符号逆 (反転仮説に対し**継続** −7.61p p=0.973、機械 kill)。レグ a は explore PASS (+7.89p p=0.0163、LOYO 7/7) → **OOS 単一接触で崩壊** (+2.06p p=0.3145、最小効果 2.06<5p、LOYO 2025 除外で符号反転)。**同型再試行禁止 = 祝日/休場フラグ×日次 D1-D2 exit-free 全変種 (継続方向への事後反転含む)**。explore 通過品質 (p+LOYO) は OOS 生存を予測しない実例 13 件目。`reports/holiday-liquidity-explore-2026-07-29.md` |
| 13 | gotobi_tokyo_fix_usdjpy | **explore 完了 2026-07-28 (同日)** — [[gotobi-calibration-explore-prereg-2026-07-28]] | ✅❌ **較正成功 / 昇格 kill** — 規約 B (前営業日繰り) で公表効果を gross 回収 (+1.92p p=0.0032、N=557 vs 1352) = **測定ハーネス正当性を実証** + 規約矛盾解決。ただし効果は sub-friction (+1.9p < RT 2.14p)、P1 テール cell +1.38p p=0.43 → kill rule 機械的適用で family クローズ。OOS 未接触。**gotobi/仲値系の再昇格提案は執行コスト構造の変化なしに不可** (tokyo_nakane_momentum 同 family)。`reports/gotobi-calibration-explore-2026-07-28.md` |

| 18 | level_failed_break_d1 (wave-4 L-a) | **explore 完了 2026-07-31 (同日)** — [[level-failed-break-d1-explore-prereg-2026-07-31]] (🔒 凍結コミット 5ea2d4dc 後に測定。敵対的検証 12 条件解決済み) | ❌ **FAIL クローズ** — primary pooled fade 5d **−4.91p (符号逆)** p=0.702 (N=290、週 block perm、knife-edge 圏外)。年次 3/8・LOYO 7/8 負・net EV −8.8p。**同型再試行禁止 = 長 lookback 極値の D1 close 確定失敗ブレイク×fade×multi-day 全変種。継続方向も p≈0.30 n.s. — 事後符号反転主張禁止 (holiday レグ c 前例)**。htf_fb 機構は D1/55d へ外挿不能と実証 (#11 には影響なし)。**正の副産物 = Gate A 8/8: D1 イベント系 headroom (MFE5d p50 51-92p ≥ 10×RT) は実在 — 律速は摩擦でなく signal**。QA 2 件 (Monday bar UTC 誤ラベル修正 / cross-check 7 ペア符号・量級一致)。OOS 非接触。`reports/level-fb-d1-explore-2026-07-31.md` |
| 19 | round_number_major_level (wave-4 L-b) | **explore 完了 2026-07-31 (同日)** — [[round-number-level-explore-prereg-2026-07-31]] (🔒 凍結コミット 7bc04410 後に測定。敵対的検証 12 条件解決済み) | ❌ **FAIL クローズ** — primary pooled 反転 3d **+6.34p (方向正) p=0.117** (N=1,088/実効 326 週、knife-edge 圏外) + 年次 5/8。net EV 点推定 +2.9p 正だが null と区別不能 — **「方向は合うが弱い」死型 3 例目 (ppp/quote-spread 同型)**。headroom 6/6 (62-89p)・LOYO 8/8 正・Brexit 週 31%・#18 重複 13.5%。**同型再試行禁止 = 00 grid fresh-approach×D1 反転×固定ホライズン全変種。事後スライス (S サイド/GBPUSD/USDJPY/5d 切り出し) は winner's curse 再演として禁止 — 再挑戦は新 family + 事前差分節のみ**。Osler 機構の D1 外挿は認定不能と実証、rnb_usdjpy には設計参照のみ供給。OOS 非接触。`reports/round-number-explore-2026-07-31.md`。**→ wave-4 全 family 決着: 平行線 3 候補 = 敵対的検証 KILL / 水平線 2 候補 = explore FAIL ×2 — 「ページのライン→エッジ」差分空間も全滅で完全クローズ** |
| 20 | composite_weak_signal_portfolio (wave-5) | **敵対的検証完了 2026-07-31 — 🅿️ 予約のみ (アクティブ枠非消費、凍結・測定・OOS 未起動)** — payload `raw/analysis/wave5-composite-portfolio-candidates-2026-07-31.json` / verdict `raw/analysis/wave5-composite-adversarial-verification-2026-07-31.md` | 🅿️ **PARK-UNTIL — 現構成 (K=2) 不成立** (user 承認 charter 2026-07-31「方向正・弱」凍結 family の合成 portfolio estimand)。member 裁定: **rn #19 + ppp #14 = ADMIT-WITH-CONDITIONS** / qs #17 = EXCLUDE (方向が explore 学習の事後符号 — prior は逆) / gotobi #13 = EXCLUDE (「規約 B を昇格根拠にしない」凍結誓約が dispositive + baseline RT で net 負) / **vix #7 = EXCLUDE-PENDING-USER** (user 委任は絞り込みで拡張は scope 外 + #7 ban「再挑戦は新データ必須」を explore 窓参加は満たさない + CAD_JPY 価格/swap とも in-repo ゼロで data-blocked)。K=2 book は最楽観 (観測 IR 真値扱い・ρ̄0.1・activity 等化) でも OOS t≈1.37/power<50% → **いかなる explore 結果でも OOS burn 不当**。復帰条件 = (a) E7 verdict 08-28 後の membership 再評価で K≥3、or (b) user が M5 scope 追加 + #7 ban 例外を on-record 決裁 — いずれも改訂 payload + LOCK-前 17 条件 (verdict §9) + **新規敵対的検証**必須。恒久条項: member 5 家系の FAIL verdict/ban は不変、composite の結果を member 再評価根拠に引用禁止。OOS 全 member 未接触保存 |
| 21 | commodity_cross_range_mr (wave-6 EA-a) | **explore 完了 2026-08-05 (同日)** — [[cc-mr-explore-prereg-2026-08-05]] (🔒 凍結 `1913f958` → pass-1 `1b4ece1b` → 測定、two-pass、敵対的検証 [[wave6-cc-mr-adversarial-verification-2026-08-05|GO-WITH-CONDITIONS 21 条]] 全消化)。先行 G0 ✅ PASS 3/3 2026-08-03 ([[commodity-cross-g0-rt-freeze-2026-08-03]] freeze `981ae119`、stressed_RT 3.70-3.90p、21:00 UTC 毒窓発見) | ❌ **explore FAIL — gate C+D 同時不通過でクローズ** (2026-08-05、`reports/cc-mr-explore-2026-08-05.md`)。pooled mean fade net5d **+3.96p** (方向正) だが block-perm 片側 **p=0.266** ≫0.05 (MDE 14.5p の ~1/4) + stressed-net **−3.7p adverse / −2.6p favorable 端でも負**。gate A 3/3 (MFE5 p50 51-78p) / B (N=255, blocks 140) / E/F/G は通過、2014 デシンク年 −22.6p = regime-kill prior 実証。**「方向は合うが弱い」slow-MR 死型の 4 例目確定** (ppp/qs/rn/cc-mr)。**クローズ範囲 (pre-reg §9 凍結どおり発効): slow location-anchor (mean/percentile/regression) band fade × multi-day × 3 クロス全 anchor 着せ替え — variant B 明示的に含む**。B 復活 = 新 family + 事前差分節 + 新規敵対的検証のみ。skip 版診断 +6.4p > 全 onset +3.96p = 条件 11 が PASS バイアスを実測阻止 / 合成 RW null 較正 −0.87p±0.53 = エスティメータ無バイアス実証 / OANDA 独立 D1 照合 87=87 (偏差 0%)。OOS 2022+ 非接触封印。残置: 3 クロス 12y 被覆修復 (+2,177 行 backfill) + cc-g0-rt 日次 financing sampler 稼働継続。explore スロット解放 → アクティブ 0/3 |
| 24 | e22_fx_variance_risk_premium (vol、scan 第3次 §2/§2.1) | **explore 完了 2026-08-17 (同日、単独 wave m=1)** — [[e22-vrp-explore-prereg-2026-08-17]] (🔒 凍結 `f50b680a` → pass-1 `0287371e` → pass-2 測定、two-pass。敵対的検証 [[../raw/analysis/e22-vrp-adversarial-verification-2026-08-17\|GO-WITH-CONDITIONS 17 条/blocking 10]] 全消化。E9 round-2 条件付き採用の正当な再裁定)。§2.1 事前コミット節 (PASS=Databento user 決裁点のみ / FAIL=vol モダリティ恒久クローズ / 0/15 正直 prior) を逐語内蔵 | ❌ **explore FAIL — gate C+D+F 同時不通過でクローズ** (`reports/e22-vrp-explore-2026-08-17.md`)。VRP=EVZ−RV21 × EUR_USD × 21bd 時系列 IC (両側、circular-shift null B=10k、N=2,066/窓 98) = **IC −0.0249、p=0.760** の完全 null (「方向は合うが弱い」型にすら非該当) + stressed-net **−11.2p adverse / −3.1p point 端でも負** (swap −16.2p が gross +8.9p を支配 = 21bd hold の事前記録どおり) + 年次符号 5/8・LOYO 7/8。**クローズ範囲 (凍結どおり発効): 通貨 VRP (IV−RV 差分/レベル/比率 全変種) × G10 × 日次〜月次 + 無料 proxy 系列 — E24/E25 棄却と合わせ vol モダリティ恒久クローズ**。**power caveat (引用時必読): FAIL ≠ 効果不在の証明 (検出力 8–17%、ただし点推定自体 ≈0) — 「VRP は falsified」型引用は estimand 監査なしに禁止**。復活 = 有償 OTC 面 + 新 family + 新敵対的検証のみ。OOS 2022-01..2025-03-11 **非接触封印**。Databento 調達決裁は不要化 (PASS 時のみの決裁点)。副産物 = **EUR_USD 15m の 2020-10 ベンダー穴修復 (+1,440 行 OANDA mid、選挙週回収、`tools/e22_gap_backfill.py`)** + EVZCLS git 追跡化 + circular-shift IC ハーネス流用可。explore スロット解放 → アクティブ 0/3、能動可能系統 = E21 のみ |
| 22 | equity_curve_shadow_gating (wave-6 EA-b) | **forward pre-reg 🔒 LOCKED 2026-08-03 (v2)** — [[equity-curve-shadow-gating-explore-prereg-2026-08-03]]。**遡及 explore 案 (v1) は敵対的検証 3 レンズで KILL → forward 転換** (統計: 窓中の一度きり構造ブレークで偽陽性 100%/robustness 全素通しを合成データ実証 + 週層化は真の検出力も殺す = 遡及窓で識別不能。交絡: 対象 10 セル中 6 は decay で R2 停止されたセル自身 = outcome-conditioned truncation + Fidelity Cutoff 04-08 前汚染。→ #4 MoF/#10 E12 前例の forward 化で構造解決、**遡及窓は未測定のまま保存 = burn なし**) | 未測定 — **first look 2026-11-06** (forward 窓 [08-04, 11-01) 13週、registry `ecg-forward-first-look`、backstop 2027-01-31)。primary = **active 4 セル** (session_time_bias×GBP/EUR, vol_momentum_scalp×GBP, xs_momentum×GBP) × K{5,10,20}、**m=12**。estimand 正直化 = 「gate 条件付き期待値改善 (源泉は持続性+市場ドリフトの合成で可、engine artifact は epoch 層化 permutation で除外)」。primary p = unique-spaced 系列。retired 6 セルは完全除外 (banned 家系再訴訟の遮断)。**first look まで gate×outcome ジョイント計算全面禁止 (P-10 型)**。PASS でも live gate R1 は forward 再現後のみ |

## wave-6 候補 triage (2026-07-31、敵対的検証済み — `raw/analysis/ea-landscape-sweep-2026-07-31.json`)

**発端**: user 指示 2026-07-31「勝てている EA を全力で海外 WEB 含め大規模調査 → 勝てるエッジ探索」。
方法 = 31-agent workflow (13 ソース並列スイープ 113 findings → 上位 18 敵対的検証)。詳細: [[ea-landscape-sweep-2026-07-31]]。
verdict: GO 3 (実質 2 family = #21/#22) / ADJACENT-BANNED 3 / RISK-ILLUSION 2 / NOT-FEASIBLE-RETAIL 10:

- **ナイトスキャルパー家系 (Night Hunter Pro/SFE/White Bear 等、5 重複検出)**: ❌ NOT-FEASIBLE — 機構実在 (板崩壊 overshoot→東京回帰) だがエッジはブローカーの overnight スプレッド封筒内側にあり政策変更で回収済み (cohort 2022-23 フラット化)。グロス 5-15p < headroom 要求 21.4p + 発火窓 = デスゾーン (実測 RT 2-3 倍) と自己矛盾。gotobi (#13) 同型。**再入場 = 執行コスト構造の変化なしに不可**
- **Thales/THA (Darwinex 首位 event-driven)**: ⚠️ LOCKED E7 と同一 estimand 衝突 — 処分 = **E7 prior 加点として記録** (verdict 08-28 の解釈材料)。残余 = 中銀声明テキスト差分モダリティは 08-28 後に新 family として再評価可
- **グリッド/ナンピン形態 (Waka Waka/NoPain 等)**: ❌ RISK-ILLUSION — negative-skew 変形、per-position 核のみ #20 に分離。**グリッド形態での再提案は archetype として不可**
- parked: NY cut オプション期日ボード条件付き (prior 6、#14 隣接差分 = expiry notional 条件を pre-reg で固定要) / Osler stop-cascade 貫通継続 (velocity 条件付き — #4/#14 との差分は貫通側のみ) / momentum-decay trailing exit (一本勝ち型 — exit 側は T2+stage-2 完全否定の negative prior、正 EV ホスト不在で mafe exit と同棚)

## wave-5 candidate triage (2026-07-31、敵対的検証済み — `raw/analysis/wave5-composite-adversarial-verification-2026-07-31.md`)

**発端**: user 承認 2026-07-31「『方向は正しいが単体では認定閾値未満』の凍結済み弱シグナル群を合成した portfolio-level エッジの検定」。
**estimand (新)**: ex-ante 固定重み・リスク正規化の日次 mark-to-market ブックの portfolio net EV / IR — family 単体の主張は一切しない。単体 ban (同型再試行禁止) の対象外だが、**中心の罠 = メタ選択バイアス** (membership が explore 方向正に条件付く) を payload が自己申告し、explore 推論は「selection-conditioned permutation による escalation filter」に降格 (claim 資格は OOS 単独) と裁定された。

- **verdict = 🅿️ PARK-UNTIL (現構成 K=2 不成立)** — 詳細は台帳 #20 行。委任 scope 内の admissible member (rn #19 / ppp #14) だけでは power が構造不足 (最楽観 OOS t≈1.37)。「degraded design より 不成立」の charter 凍結解釈を適用。**待機コスト ≈ ゼロ / 待機利得 = E7 (08-28)・E1 (10-15) の新規 member 供給 + OOS 窓の自然延伸** — 非対称につき測定せず待つのが最適
- **統計裁定の要点 (復帰時に継承)**: composite null = **暦半期 16 block 全列挙 (2¹⁶) joint sign-flip** + per-member 選択統計量 conditioning (ppp は IC>0、mean>0 ではない)。ISO 週 block は ppp 42bd 重複 cohort に対し anti-conservative で不可。G2 相関閾値は 0.35。1/K+1/ATR 案は ppp が年率分散を支配するため家系別年率リスク等化が必須 (等化係数は returns 非参照で導出)
- **横断データ発見 (payload の price_source 誤りから確定、将来 wave の恒久事実)**: ① `data/cache/massive/` の plain `_1d` parquet は**土日行 + UTC 境界で素のまま使用不能** (NY17:00 再構築必須、#18 QA の同型)。② **CAD_JPY は 1d/1h/15m とも in-repo ゼロ** (e20 swap 列も無し)。③ **EUR_JPY のフル系列は 15m のみ** (`_1d` は 2016-04 開始、1h は 2021-12 開始)。④ GBP_JPY 1h も短窓 (2021-12+)。⑤ 凍結 pin は「main checkout」等のラベルではなく**ファイル実体 + sha256** で
- **恒久条項**: composite の verdict は member family の FAIL verdict/ban を一切更新しない。composite PASS を「member は実は有望だった」の根拠に引用することを恒久禁止 (gotobi 誓約の一般化)
- **M5 (vix #7) の将来決裁メモ**: merits は正確 (方向 pre-reg 済み・m=2 BH のみが死因・headroom カタログ最良) だが、#7 ban の再挑戦条件「新データ必須」を explore 窓参加は満たさない → admit には user の on-record ban 例外決裁が必要。**E7 経由の新 vix-family が成立するならそちらが常に優先** (ban 例外不要)

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
