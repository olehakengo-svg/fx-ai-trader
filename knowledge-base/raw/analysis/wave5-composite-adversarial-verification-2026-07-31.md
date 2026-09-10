# wave-5 composite weak-signal portfolio (台帳 #20 候補) 敵対的検証 verdict (2026-07-31)

**検証者**: 独立 subagent (payload はファイル渡し: `wave5-composite-portfolio-candidates-2026-07-31.json`)。
一次ソース精読照合: hypothesis-catalog md (台帳 #1-#19 全行 + 運用ルール) / edge-dev-postmortem /
level-family 敵対的検証 (品質前例) / rn #19 report+prereg+**pass2 raw JSON 全 1,088 行再集計** /
ppp #14 report+prereg+raw JSON (per_obs 672 行・orientation・per-pair RT 実文) / qs #17 report+raw JSON+
`tools/fx_quote_spread_explore.py` / gotobi #13 report+**raw JSON (n_treat 557 / n_control 1352 実確認)** /
wave-1 report+protocol-freeze (RT 凍結表) + **vix raw JSON 23×6 行から pooled +46.16p/share 34.7%/WR 60.9% を再現** /
holiday #15 / level-fb #18 / COT #5+#16 各 report / `tools/round_number_explore_stats.py` 全文 /
`e20_carry_level.csv` ヘッダ+日付域 / main checkout `data/cache/massive/` **parquet 実測 (行数・first/last・曜日集合)** /
`data/external/quote_spread/` (worktree 42 parquet 実在)。OOS 2022+ の forward return には一切接触していない。
member/composite P&L の新規計算はゼロ (再現は raw JSON 内の記録済み集計の算術のみ)。

**サマリ: M1 (rn) / M2 (ppp) = ADMIT-WITH-CONDITIONS、M3 (qs) / M4 (gotobi) = EXCLUDE、
M5 (vix) = EXCLUDE-PENDING-USER (委任 scope 外 + #7 ban の「新データ必須」条項)。
生存 K=2 では payload 自身の power 算術により OOS burn を正当化できない → 現構成は 不成立。
family verdict = PARK-UNTIL-(E7 verdict 2026-08-28 以降の membership 再評価、または user の M5 明示決裁)。
default で進行させない: K≥3 が成立しない限り凍結・測定・OOS いずれも起動禁止。**

---

## 1. grounding facts 照合結果 (Task A)

### 1.1 検証済み (payload 正)

| # | claim | 照合 |
|---|---|---|
| 1 | rn #19: +6.34p / p=0.117 / N=1,088 / 326 実効週 / net +2.88p / headroom 6/6 (62.3-89.0p) / LOYO 8/8 / 年次 5/8 / Brexit 31.3% | ✅ report と一致。**raw pass2 JSON 全行再集計で mean +6.34 / 326 週 / 2016-W25 share 0.313 を独立再現**。per-pair 148-227 行、9 フィールド形式も payload どおり |
| 2 | vix #7: +46.2p / 厳密 p=0.050091 (2²³ 全列挙) / N=23×6 / headroom 31.9-54.9× / top share 34.7% / WR 60.9% / 「m=2 BH のみが死因」 | ✅ 全て report と一致 + **raw JSON から pooled +46.16p / share 0.347 / WR 14/23 を独立再現**。「単独 family なら通過していた」も report 実文 |
| 3 | ppp #14: IC42 +0.113 両側 p=0.129 / 672 obs / 年次 7/8 正 / carry 直交 102% / headroom 79-115× / quintile 隣接違反 3 / z>2: 96 vs z<−2: 5 | ✅ raw JSON `pass_condition_inputs` と全一致。orientation 凍結「高 z=USD 実質割高 → FC return 正」も `reversion_direction_sign` 実文どおり |
| 4 | ppp 再入場 path (b) 文言 =「2022+ を explore に含められる将来の split 再設計」→ composite OOS touch がこれを汚染 | ✅ report §再試行スコープ実文と一致。burn-cost 開示は正確 |
| 5 | qs #17: −0.237σ/−9.5p 両側 p=0.323 / N=65 (2014-15 構造ゼロ) / 3 ペア・全年方向一貫 / 実現 headroom 15.1× / prior (flight-to-quality 継続) と観測 (risk-ON) が**逆** | ✅ report + raw JSON 一致。events は **events_sample 5 行のみ永続** (payload 主張どおり)、`frozen` dict + seed 20260729 で決定的再生成可、パネル 42 parquet は repo 追跡済み実在 |
| 6 | gotobi #13: 規約 B +1.92p p=0.0032 (N=557 vs 1352) / 規約 A +0.33 p=0.60 / baseline net −0.22p / floor net +0.62p | ✅ raw JSON `C1_fix_convB_diag` (n_treat 557 / n_control 1352) 実確認。誓約文言「規約 B の有意性 (+1.92p) を根拠に fix-window cell を『有望』と再解釈しない (昇格に使えば宣言違反)」は report に逐語で実在 |
| 7 | 除外根拠: #15 = OOS 接触済み (レグ a OOS 単一接触で崩壊) / #18 = 符号逆 (−4.91p、継続側も p≈0.30 n.s.) / #5+#16 = incoherent (サイド split 非対称 + 鏡像恒等 0.93) / #6 = null + 逆符号 3d/5d は登録拒否済み事後スライス / #1 = P-S1(a) 生存資産 / #2 = live 5 席 | ✅ 全 report 実文と一致。mandatory_exclusions は全件支持 |
| 8 | RT 凍結表 (wave-1 freeze): USD_JPY 2.14 / EUR_USD 2.00 / GBP_USD 4.53 / EUR_JPY 2.50 / AUD_JPY 3.00 / AUD_USD 2.50 / NZD_USD 3.00 / USD_CAD 2.80 + **GBP_JPY 4.50 / NZD_JPY 3.50 / CAD_JPY 3.50** (未実測=保守設定と明記) / floor 1.30p | ✅ M5 の 3 クロスも wave-1 freeze doc に実在 (payload の確認要求に回答) |
| 9 | e20_carry_level.csv: 2013-01-01〜2022-12-30、13 ペア列、explore 窓完全カバー、OOS には e20_rates_ingest 機械 refresh 必要 | ✅ ヘッダ+末尾実測一致。**ただし §1.2-4 の CAD_JPY 欠落を参照** |
| 10 | power 算術: z 変換 (0.117→1.19 / 0.129→1.52 / 0.050091→1.645 / 0.323→0.99 / 0.0032→2.95)、IR (0.42/0.54/0.58/0.40/1.04)、IR_c 式、K=2: 0.65→t 1.37→p~0.085、K=3: 0.81→t 1.72→p~0.04、haircut 0.25: 0.42→t 0.89、MDE (80%: 1.17 / 50%: 0.78) | ✅ **全再計算一致** — 算術に誤りなし。ただし §8.3 の前提バイアス (ρ̄・activity share) を参照 |
| 11 | ledger 状態: #1-#19 使用済み→#20、active non-locked 0、locked/passive 列挙、cap 3、E15/E7 refreeze 08-21 前 `--verify-only` | ✅ catalog + MEMORY と整合 |
| 12 | T9 crisis 重複の実在: Brexit 2016-06-24 は **vix イベント日** ∧ rn の top week **2016-W25** | ✅ 両 raw JSON の日付で確認 — 懸念は仮説ではなく実データ |

### 1.2 訂正 (payload 誤 — level-family 前例と同水準の重要度順)

1. **[重大 / data-blocked] CAD_JPY はローカルに一切存在しない** — `data/cache/massive/` に CAD_JPY の parquet は **1d も 1h も 15m もゼロ** (glob 実測 `[]`)。payload の「GBP_JPY/NZD_JPY/CAD_JPY exist only as 1h → same resample convention」は**虚偽** (未検証の願望記述)。さらに **e20_carry_level.csv の 13 列にも CAD_JPY は無い** (「all 13 pairs」は字義的に真だが M5 必要ペアを含まない)。M5 を admit する場合、価格は新規 fetch、swap は宣言済み導出 (CAD_JPY 差 = USD_JPY 列 − USD_CAD 列) が freeze 前に必須 — 現状のままでは M5 は merits 以前に data-blocked。
2. **[重大] GBP_JPY_1h は短窓** (実測 2021-12-24 開始) — フル系列は `GBP_JPY_15m.parquet` (2013-10-24〜) と `GBP_JPY_5m_2014_2026.parquet` のみ。宣言された「1h resample fallback」は GBP_JPY で実行不能。
3. **[重大] EUR_JPY (M1 の 6 ペアの一つ) のフル D1/1h が不在** — `EUR_JPY_1d.parquet` は **2016-04-18 開始** (explore 窓の 2014-2016Q1 を欠く)、`EUR_JPY_1h.parquet` は 2021-12-24 開始の短窓、`EUR_JPY_1d_2014_2026` は存在しない。フル系列は `EUR_JPY_15m.parquet` (2013-10-24〜、E15/E7 凍結ファイル) のみ。payload の price_source は M1 コアペアで既に破綻しており、G0 で事後発見される前に規約を直すべき (§9 条件 2)。
4. **[重大] massive D1 parquet は素のままでは使用不能** — plain `_1d` (2016-04 開始) にも `_1d_2014_2026` にも**土日行が実在** (曜日集合 {0..6} を実測)。バー境界は UTC 系で TV OANDA D1 (NY 17:00) と非整合 — これは #18 の QA 記録 (「短窓 _1d + 日曜バー混入で比較無効 → 1h フル版から NY17:00 再構築が正」) の同型再演。「main-checkout D1 parquet を primary、1h resample を fallback」という二段構えは成立せず、**最初から全ペア intraday→NY17:00 D1 再構築の単一規約**にすべき (§9 条件 2)。
5. **[中] RT USD_CHF「~2.5」は誤り** — wave-1 freeze doc に USD_CHF は**存在せず** (payload の確認指示先も誤り)、ppp 凍結ハーネス `tools/ppp_real_fx_explore.py` の実文は **3.00p**。composite の ppp 脚は 3.00p を継承すること。
6. **[中] 「main checkout」はラベルとして pin にならない** — 実測で main checkout は branch `research/trendline-sweep-12y-pairscope-2026-07-13` 上にあり、working dir には quote_spread パネルすら不在 (repo 追跡はされている)。MASSIVE 歴史バー drift の教訓どおり、**凍結はファイル実体 + sha256** で行う (§9 条件 3)。
7. **[中] ハーネス「流用」の過大表現** — `round_number_explore_stats.py` の swap は per-event × 固定 4.2 暦日 (`HOLD_CAL_DAYS`)、permutation は単一 stream の週 block flip。composite が要る「日次 accrual」「多 stream 同時 flip + acceptance filter」は**新実装**。流用できるのは ISO 週 blocking の骨格と e20 読み出しのみ — 「新規測定コードは G0 で実データ検証してから」の教訓 (payload 自身が G0 に引用) がフルに適用される。
8. **[中/宣言漏れ] OOS touch は member シグナルの再生成を要する** — rn pass2 JSON は **explore 窓の 1,088 行のみ** (2022+ 行ゼロ、実測)、vix も 23 explore イベントのみ (ev_all=70-73 中 ev_exp=23 のみ export)、ppp per_obs も 672 行 explore のみで、ハーネスは `GRID_END=2022-04-30` + 「OOS シグナルは生成しない」がハードコード。つまり OOS 単一接触には rn/vix の **TV 再 export** と ppp ハーネスの**定数拡張 (コード変更)** が必要。payload は e20 refresh しか宣言していない — OOS pre-reg に「凍結 Pine 無変更再 export + ppp 定数のみ diff 公開」の機械的宣言が必須 (§9 条件 12)。
9. **[小] per_obs の内容は payload 記述より豊か** — z/quintile に加え **r21/r42/r63 (FRED fwd return) と rd_fc_pct を含む**。これは訂正というより好材料: G0 を「IC 許容誤差」ではなく per-obs return 照合にできる (§9 条件 7)。
10. **[小] ppp には spec 解釈履歴がある** — 凍結式の S 向き内部不整合を測定 agent が解決した記録 (`signal_orientation_resolution`) と、字面 mix 構成 **IC +0.084** の診断が raw JSON に残る。composite G0 の ±0.03 許容はこの 0.084 を「通過」させ得る — §8.4 の穴として裁定。

**meta 監査**: 台帳 #20 / m=1 / cap 整合 ✅。orchestrator の自己申告 (bias 開示、M3/M4 EXCLUDE lean、
「M5 なしなら K=2 で不成立かもしれないと明示的に言え」) は誠実 — wave-3/wave-4 水準。誤りは
**データ実在ブロックに集中**しており、これは「TV coverage / panel probe を測定前 assert に」という
W3-2 以来の横断警告を payload 自身が (他所で引用しながら) 自分の price_source に適用し損ねた形。

---

## 2. verdict サマリ (Task B)

| member | verdict | ban 照合 | 一言 |
|---|---|---|---|
| M1 rn #19 | **ADMIT-WITH-CONDITIONS** | ADJACENT (再挑戦条項「新 family + 事前差分節」に適合) | 方向 pre-reg 済みの最清浄 member。EUR_JPY 価格規約の修正が前提 |
| M2 ppp #14 | **ADMIT-WITH-CONDITIONS** | ADJACENT (再計算ゼロ・family 主張ゼロ) | path (b) 汚染は user ゲートで逐語開示。G0 は二重基準に強化 |
| M3 qs #17 | **EXCLUDE** | ADJACENT だが方向が事後 | 事後方向の凍結は不可能 — 「data-mined sign を book に埋める」ことに等しい |
| M4 gotobi #13 | **EXCLUDE** | **誓約が dispositive** | 逐語誓約 + friction モデル依存符号 + 勝ち規約選択の三重失格 |
| M5 vix #7 | **EXCLUDE-PENDING-USER** | ⚠️ #7 再挑戦条項は「**新データ必須**」— explore 窓参加はこれを満たさない | scope 外 + ban 例外要 + CAD_JPY data-blocked。正規経路 = E7 (08-28) |
| **family #20** | **PARK-UNTIL** (K=2 は 不成立) | — | §11 |

---

## 3. [M1] round_number #19 — ADMIT-WITH-CONDITIONS

### ban 照合 (on-record 裁定)

- #19 の記録済み ban =「00 grid fresh-approach × D1 反転 × 固定ホライズン全変種 + 事後スライス
  (S サイド/GBPUSD/USDJPY/5d) 禁止、**再挑戦は新 family + 事前差分節のみ**」。composite は
  (i) 摂動ゼロ (1,088 イベント逐語継承、実確認済み)、(ii) スライスゼロ (全量・両サイド・6 ペア・3d のみ)、
  (iii) #19-level 主張ゼロ — **新 family (#20) + 事前差分節**の形式要件を満たす。
- **争点の裁定**: rn report の「本 explore の数値を選択根拠に使うことを禁止する」は、文脈上
  「勝ち残り組合せの切り出し」(winner's-curse スライス) を対象とする条項であり、family 単位の
  membership 選択には直接適用されない — と裁定する。**ただし** membership 選択が explore 結果
  (方向正) に条件付いている事実そのものが本 wave の central trap であり、この裁定は
  「explore verdict は feasibility screen のみ・claimable は OOS 単独」(payload 凍結宣言) が
  逐語で freeze doc に生きることを**条件とする**。宣言が落ちた瞬間、この裁定は失効する。

### 条件 (member 固有)

- (a) 差分節を pre-reg に逐語再掲: 「#20 の verdict は #19 の FAIL verdict を一切更新しない。
  composite PASS を『rn は実は有望だった』の根拠に引用することを恒久禁止する」(gotobi 誓約の一般化)。
- (b) 価格規約: EUR_JPY は 15m フル版 (2013-10-24〜) からの NY17:00 D1 再構築 — §9 条件 2 の単一規約に従う。
- (c) OOS イベントは凍結 Pine (`round_number_export.pine`) の無変更再 export のみ (§9 条件 12)。
- (d) G0 = JSON 行からの純算術で mean net3 = +6.34p 正確再現 (本検証で再現済みなので事実上リスクゼロ) +
  massive 再構築価格での per-event net3 照合 (誤差分布を報告、乖離時 STOP)。

---

## 4. [M2] ppp #14 — ADMIT-WITH-CONDITIONS

### ban 照合

- #14 ban =「5y-z 月次 × 21-63bd の同型再試行禁止、再挑戦 = (a) 実質金利差込みモデル / (b) 2022+ 込み
  split 再設計」。composite は z の再計算ゼロ・チューニングゼロ・family 主張ゼロで ADJACENT 成立。
- **rank-portfolio 化は新 DoF だが最小**: Spearman IC の canonical な書換えであり、代替変換
  (z-加重 / Q5−Q1) は **declared non-tested** として凍結すること (§9 条件 5)。quintile 非単調 (違反 3) を
  知った上で「quintile を使わず rank を使う」選択に見える余地があるため、rank 採用理由 =
  「primary 推定量 (Spearman) との同型性」を pre-reg に明記し、Q5−Q1 型は変種として試すことを禁止する。
- **membership 資格**: 「方向正 + not incoherent」— quintile 非単調は片側 regime (z<−2 が 5 obs) と
  不可分という記録済み診断、年次 7/8 正、carry 直交 102% から incoherent 型 (#5/#16) とは別と裁定。
  catalog 自身が #14 を「方向は合うが弱い」型に分類しており整合。

### 条件 (member 固有)

- (a) **G0 二重基準** (±0.03 の穴を閉じる、§8.4): per-obs r42 (FRED、672 行に永続済み) と massive 再構築
  return の相関 ≥ 0.995 ∧ |IC_massive − 0.1130| ≤ **0.02**。どちらか不成立 → MEASUREMENT STOP
  (「許容内 PASS」処理を禁止 — 字面 mix 構成の IC 0.084 が payload の ±0.03 帯の内側にある)。
- (b) swap: ppp 凍結規約 (純額・e20 パネル・pay/earn 対称、earn 側 25% haircut 感度) を無変更継承。
  RT は ppp 凍結ハーネス実値 (USD_CHF **3.00p**)。
- (c) composite null の block 長は ppp の 42bd 自己相関を支配する長さ (§8.2 — 半期 block)。
- (d) G4 acceptance の ppp 選択事象は **IC > 0** (mean > 0 ではない — §8.1)。
- (e) OOS touch が path (b) を殺すことの逐語開示を user ゲート必須文面に (payload 宣言どおり、脱落禁止)。
- (f) OOS シグナル生成はハーネス定数拡張のみの diff 公開 (§9 条件 12)。

---

## 5. [M3] qs #17 — EXCLUDE

1. **事後方向が単独で dispositive**: 凍結 prior は flight-to-quality **継続**、観測は risk-ON (**逆**)。
   book に載せる方向は explore データから学習した符号そのものであり、「ex-ante 継承」という wave-5 の
   estimand 前提を満たす方向が存在しない。#18 (符号逆) を mandatory exclusion にした基準と整合的に
   扱うなら、「prior と逆向きに有意ですらない (p=0.32)」M3 を admit する理屈は立たない。
2. **ban 隣接が最も濃い**: #17 ban は「実測 BBO スプレッド状態 × 時間固定ホライズン fwd 方向 **全変種**
   (閾値・持続定義・ホライズン・ペア・feed の別を問わない)」— 凍結イベント集合の逐語継承であっても、
   その事後方向で fwd 方向を取引する行為は ban の核心 (スプレッド状態→方向) の再演に最接近する。
3. **費用対効果**: IR 寄与 ~0.1 (正直 haircut 後)、2014-15 構造死 (8 年中 2 年無音)、両側 selection
   encoding の複雑化、M5 と危機週重複 — 得るものがない。
4. orchestrator lean (EXCLUDE) を支持。パネル (78k サンプル) は摩擦研究インフラとして残置 —
   本 verdict は防御用途に影響しない。再入場経路: なし (composite 文脈では)。

---

## 6. [M4] gotobi #13 — EXCLUDE

1. **誓約が dispositive**: report 逐語「規約 B の有意性 (+1.92p) を根拠に fix-window cell を『有望』と
   再解釈しない — 昇格に使えば宣言違反」。composite は explore PASS → OOS → (R1 経由の) live という
   昇格経路を持つ設計であり、B を book member にすることは**まさにこの再解釈**。凍結誓約の
   override は不可能と裁定 (orchestrator の「honestly impossible」を支持)。
2. **符号が friction モデル依存**: baseline RT 2.14p で net −0.22p / floor 1.30p で +0.62p —
   G3 が「base AND 全感度で正」を要求する設計に、base で負の member を入れることは自己矛盾。
   portfolio 化は分散を割るが**別執行の per-trade 摩擦は 1 円も割らない** — payload の算術は正しい。
3. **勝ち規約選択**: 凍結 primary は規約 A (+0.33 p=0.60、FAIL)。B は較正診断として宣言済み。
   max-over-conventions の selection は encoding 可能だが、(1)(2) が先に立つ。
4. catalog ban「gotobi/仲値系の再昇格提案は執行コスト構造の変化なしに不可」も本件に直接適用される。
   user が明示列挙した候補の除外であるため、本 §をもって on-record の却下理由とする (silent drop ではない)。

---

## 7. [M5] vix #7 — EXCLUDE-PENDING-USER

### 第一裁定: user scope (payload の要求どおり最初に)

user brief は 4 候補 + COT 委任 + 2 mandatory exclusion を列挙し、「admissibility は敵対的検証で裁定 —
全部使う前提にしない」と**絞り込みを**委任した。M5 はこのリストに無い orchestrator 追加であり、
リストの**拡張**は委任の射程外と裁定する。**追加には独立した user 決裁が必要 → EXCLUDE-PENDING-USER。**

### 第二裁定 (user 決裁の判断材料として on-record): merits と ban

- **merits (payload 主張は正確)**: 方向 pre-reg 済み・m=2 BH のみが死因・headroom カタログ最良・
  estimand (「方向正だが閾値未満」) への適合は全候補中最良。K=2→3 の power 寄与も最大。全て事実。
- **しかし ban 条項が他 member と非対称**: #7 の記録済み再挑戦条件は「**新データ** + 隣接差分節 + pre-reg」
  (wave-1 report 逐語: 「再挑戦は新データ (E7 サプライズ軸、または 2022+ を含む将来の独立 family) でのみ」)。
  composite の explore 窓 (2014-2021) は**同一の 23 イベント・同一方向・同一 3d ホライズン**であり
  新データ要件を満たさない。rn の ban (「新 family + 差分節」で足りる) とはここが違う —
  M5 の explore 参加を認めることは **#7 ban の明示的例外を user が on-record で承認する**ことを要する。
  「OOS 側だけ新データ」という読み替え (explore は診断限定・G4 非参加の OOS-only member) は
  explore screen と OOS book の非対称を生み、estimand を壊すため不採用と裁定。
- **data-blocked (§1.2-1)**: CAD_JPY は価格ゼロ・swap 列ゼロ。GBP_JPY は 15m 再構築要。
  admit するなら fetch + 導出宣言が freeze 前必須。
- **G5 構造ストレス**: top event share 34.7% + 危機週クラスタ (Brexit 週は rn top week と同一週、実確認)
  — M5 込み book は G5 (単一週 ≤50%) を通っても「2-3 週が composite を支配する」形が残る。
  payload 自身の honest argument AGAINST と一致。
- **6-legs-1-event 規則が book 構築規約と矛盾** (§9 条件 5): unit ブロックは「全ポジション 1/ATR20」、
  M5 ブロックは「per-event 1 risk unit を 6 分割」— 両立しない。admit 時は要凍結解決。
- **正規経路が 4 週間後にある**: E7 phase-1 verdict = **2026-08-28** は #7 の記録済み再挑戦経路
  (「E7 サプライズ軸」) そのもの。ban 例外を切ってまで今 admit する時間価値は無い — これが §11 の
  PARK-UNTIL の主根拠。

---

## 8. 統計裁定 (Task C — Q1/Q5/Q6)

### 8.1 selection-conditioned permutation は「維持、ただし降格 + 3 修正」

**Q1 裁定: explore 推論は捨てないが、「escalation filter」に降格する (claim 資格なし)。**
payload の凍結宣言 (「explore PASS は feasibility screen のみ、claimable は OOS 単独」) を
そのまま採択し、G4 の役割は「user に OOS burn を提示してよいかの機械フィルタ」に限定する。
機械 gate のみ (G0-G3/G5/G6) に落とす案は棄却 — 点推定正 (G3) だけで user 昇格できてしまい
フィルタとして弱すぎる。conditional p は不完全でも「selection が製造する水準を超えたか」の
下限チェックとして機能する。

sign-conditioning の妥当性: **attestation 付きなら可**。ただし 3 修正を必須とする:
1. **acceptance 事象は member の実際の選択統計量に一致させる** — rn/vix = pooled mean > 0、
   **ppp = IC > 0** (payload の「every member's permuted stream mean > 0」は ppp の選択事象を
   誤指定している)。book 化後の ppp stream mean と IC は符号がずれ得る。
2. **magnitude 条件の欠落を定量開示**: 選択は実際には「方向正 + 目立つ大きさ」で行われた
   (rn p=0.117 は p=0.49 ではない)。sign-only conditioning の anti-conservatism は残る —
   attestation 逐語継承 + 「conditional p は下限であり真の p はこれより大きい」を report 文面に固定。
3. **acceptance 率の報告義務**: 条件付け後の有効 draw 数 (K=2 で名目 ~25%、相関で変動) を
   report に記載し、有効 draw < 10,000 なら draw 総数を増やす (または §8.2 の全列挙を使う)。

### 8.2 block 粒度 (Q5): ISO 週は ppp に対して不適 → **半期 (6m) joint block + 全列挙**

ppp の 42bd 重複 cohort は ~9 週の系列相関を stream P&L に注入する。週 block flip はこの相関を
無視して帰無分散を過小評価する — selection bias の上に**さらに** anti-conservative を重ねることになり
不可。裁定:
- **composite null = 暦半期 block (2014H1〜2021H2 の 16 block) を全 member stream で同時 sign-flip**。
  ppp 自身の凍結 bootstrap (6 ヶ月 block × 全ペア同時) と同型で、家系間整合が取れる。
- 16 block → **2¹⁶ = 65,536 通りの全列挙が可能** — vix #7 の厳密 p 前例に倣い、MC 誤差もシード依存も
  ゼロにできる。acceptance filter (8.1) を全列挙上で適用し、conditional p は正確値として報告する。
- 週 block 版と月 block 版は感度診断として併記 (選択に使わない)。
- stationary bootstrap は棄却 — ブロック長パラメータという新 DoF を持ち込み、全列挙の決定性を失う。

### 8.3 power 算術の前提 2 点 (payload 見落としの指摘)

- **ρ̄=0.1 は未検証仮定で、G2 閾値 (|ρ|≤0.5) と不整合**: G2 を 0.5 ぎりぎりで通過する book の
  K=3 IR_c は 0.81 ではなく ~0.63 (denom √(3+6·0.5)=2.449)。G2 閾値は **0.35** に締め、
  power 提示は ρ̄ ∈ {0.1, 0.35} の両シナリオで行うこと。
- **activity share の不整合 (構造問題)**: 1/K + 1/ATR は「アクティブ日のリスク」を等化するが、
  年率リスク寄与はアクティブ日数に比例する。ppp は常時 7 ペア稼働、rn は ~2.6 event/週 × 3d、
  vix は 8 年で 23 event — **book の年率分散は ppp が支配し、rn/vix の実効 weight は名目 1/K を
  大きく割る**。すると (a) power_preanalysis の IR_c = ΣIR/√(K+…) は book の実装と一致しない
  (過大)、(b) G6 (composite IR > best member IR) は「ppp 単独 + 希釈ノイズ」構造で機械的に
  FAIL しやすい。**修正を §9 条件 6 で凍結すること** (家系別年率リスク等化 — 等化係数は
  記録済みイベント数のみから導出、returns は見ない)。等化しないなら power 表を activity 加重で
  下方修正し、その数字で user 判断を仰ぐ。

### 8.4 G0 許容誤差の裁定 (Q6 の一部)

rn/vix「exact」は妥当 (純算術)。**ppp の「±0.03」は穴** — 記録済みの字面 mix 構成 (IC 0.084) が
帯内に収まり、orientation 取り違えを「価格ソース差」として通過させ得る。§4 条件 (a) の二重基準
(per-obs return 相関 ≥0.995 ∧ |ΔIC| ≤0.02、miss = STOP) に置換する。

### 8.5 台帳/BH 構造 (Q6)

単独 family #20 / m=1 / primary = G4 conditional p (escalation filter として) — locked 線
(E1/E7/E12/MoF/#11/#12) と分母共有なし。**member family の verdict は composite の結果に
かかわらず不変** (FAIL のまま) を台帳に明記。干渉なしを確認した。

---

## 9. DoF 監査 (Task D) → 復帰時 LOCK-前 必須条件 (17 条)

1. **membership 凍結**: K と member 集合は freeze 時に固定。explore 測定後の member 追加/削除は
   いかなる理由でも禁止 (特に「explore を K=2 で見てから M5 を足す」は二重 look で即 INVALID)。
2. **価格規約の単一宣言 (fallback 分岐の廃止)**: 全ペア **intraday parquet → NY17:00 境界 D1 再構築**
   の単一規約。ソース: USD_JPY/EUR_USD/GBP_USD/AUD_USD/NZD_USD/USD_CAD/USD_CHF = `_1h_2014_2026`
   (GBP_USD は `_1h_12y_massive`)、AUD_JPY/NZD_JPY = `_1h_12y_audit`、EUR_JPY/GBP_JPY = `_15m`。
   plain `_1d` は**禁止** (2016-04 開始 + 土日行 + UTC 境界、実測 §1.2-3/4)。土曜/日曜バー除外 +
   bars/week≈5 assert を wave-1 QA から無変更継承。「G0 誤差を見てから規約を選ぶ」二段構えは
   look-dependent な DoF なので**廃止** — 規約は測定前に一意。
3. **sha256 pin**: 全入力 (価格 parquet・e20 csv・member raw JSON・ハーネス) の sha256 を freeze doc に
   記載 (MASSIVE drift 実測 −25 行の教訓)。「main checkout」というラベルへの依存禁止 (現に research
   branch 上にあることを実測済み)。
4. **ATR 凍結**: Wilder ATR20、pips 単位、再構築 D1 上、entry bar close で確定・保有中不変。
   履歴 20 bar 未満のイベントは **skip (件数報告)** — 補間や短縮窓の裁量禁止。knife-edge {14,28}。
5. **book 規約の統一**: 全 member 「1 ポジション = 1/ATR20 risk unit」。ppp rank weights
   (w = rank(z) − (n+1)/2、Σ|w|=1、42bd hold、max 2 cohort 平均) を凍結し、z-加重/quintile 変換は
   declared non-tested。M5 型「per-event 1 unit 分割」規則は本規約と矛盾するため、将来 admit 時に
   要事前解決。hold-day 境界規則 (event bar を day 0 とし close-to-close) を明文凍結。
6. **家系別年率リスク等化** (§8.3): λ_f = (1/K) × c_f、c_f は記録済みイベント数・保有日数のみから
   導出する年率アクティブ日等化係数 (returns 非参照、導出式を freeze doc に)。等化しない選択も可だが
   その場合 power 表を activity 加重で再計算して user ゲートに出すこと。primary はどちらか一方のみ。
7. **G0 (ppp) 二重基準**: per-obs r42 相関 ≥0.995 ∧ |ΔIC| ≤0.02、miss = MEASUREMENT STOP (§8.4)。
8. **G0 (rn/vix) exact**: JSON 純算術で +6.34p / +46.2p (本検証で再現済み)。qs は将来も
   n=65 / −0.237σ の exact 再生成 (admit されない限り不要)。
9. **G4**: 半期 16 block 全列挙 joint sign-flip + per-member 選択統計量 conditioning +
   anti-conservatism attestation 逐語 + acceptance 率報告 (§8.1/8.2)。explore verdict の語彙は
   「FEASIBILITY PASS/FAIL」に固定し「edge PASS」の表記を禁止。
10. **escalation 規則 (Q7)**: user への OOS burn 提示は
    {G0-G3・G5・G6 全 PASS} ∧ {G4 conditional p < 0.05} ∧ {K ≥ 3} のときのみ。
    ひとつでも欠けたら **auto-close FAIL (OOS 非接触、user エスカレーションなし)**。
11. **user ゲート文面凍結**: burn-cost (ppp path (b) 死亡、vix 経路汚染、全 member の per-family OOS
    知識リーク) + power 表 (ρ̄ 2 シナリオ × haircut 有無) + **UNDERPOWERED 分岐** (OOS
    fail-to-reject ≠ falsified) を逐語で含む。省略・要約禁止。
12. **OOS 機械宣言**: rn/vix = 凍結 Pine 無変更再 export、ppp = `GRID_END`/窓定数のみの diff 公開、
    e20 = `e20_rates_ingest` 機械 refresh。これ以外のコード変更は OOS verdict を無効化する。
13. **swap**: e20 歴史 proxy + markup 0.50%/yr ±50% + 日次 accrual (新実装 — G0 で rn Gate D の
    per-event 値 +2.88p との整合を検算)。将来 M5 admit 時の CAD_JPY は宣言済み導出
    (USD_JPY 列 − USD_CAD 列) のみ。
14. **E15/E7 凍結ファイル保全**: EUR_JPY/GBP_JPY の 15m parquet は read-only 使用。08-21 前の
    `e15_e7_data_refreeze.py --verify-only` 義務と非干渉であることを freeze doc に明記
    (bytes に触れない、gap-fill・再 fetch 禁止)。
15. **T9 診断義務**: cross-member event-week overlap (≥2 member 稼働週の |P&L| share) を report 必須。
    Brexit 2016-W25 (rn top week ∧ vix イベント週、実確認済み) を名指しで検査。
16. **接触規律**: PASS ≠ live。tier action ゼロ、rnb_usdjpy/htf_fb shadow 非使用、R1 + user 承認は別線。
17. **台帳言語**: #20 登録時に per-member 差分節を逐語収録し、「composite の verdict は member family
    の FAIL verdict を更新しない」「composite PASS を member 再評価の根拠に引用禁止」を恒久条項化。

G1 は維持 (ppp 在籍中は事実上無拘束であることを注記)。G2 は **|ρ| ≤ 0.35 + 推定には重複稼働
≥30 週を要求** (未満 pair は gate 免除・報告のみ) に強化。G3/G5 は原案どおり。G6 は条件 6 の
等化を前提に維持。knife-edge は ATR {14,28} + hold 境界のみ — **trailing-vol parity は仕様未凍結の
まま verdict に影響し得る位置に置かない** (Q3 裁定: λ=1/K が唯一の primary、vol parity は完全仕様を
書けるなら診断として併記可、書けないなら削除)。

---

## 10. power / burn 裁定 (Task E — Q2/Q4/Q7)

- payload の算術は**全再計算で一致** (§1.1-10)。ただし §8.3 の 2 前提修正後の正直な表:
  K=2 (M1+M2) は最楽観 (観測 IR を真値扱い・ρ̄=0.1・activity 等化済み) ですら t_oos~1.37 /
  power <50%。selection haircut か activity 非等化のどちらか一つでも現実になれば t_oos <1 —
  **「4.5 年待って高確率で null を引き、その代償に 2 family の OOS を恒久消費する」取引**であり、
  M1 (月次符号転換) への期待寄与は負。K=2 での OOS burn は**いかなる explore 結果でも不当**と裁定。
- K=3 (M5 込み) でも最楽観 ~55% / haircut 後 hopeless — burn を正当化するのは「user が
  full-power 表を見た上で意識的にコイントスを買う」場合のみ。その決裁自体が M5 scope 決裁と
  同一ゲートで行われるべきもの。
- **PARK の優位性は非対称**: 待つことのコスト ≈ ゼロ (member artifact は凍結済み・腐らない、
  OOS 窓は保存されたまま)、待つことの利得 = (a) E7 verdict **2026-08-28** — #7 の記録済み正規
  再挑戦経路そのもの + 新 weak-positive family の供給可能性、(b) E1 first look **2026-10-15** — 同、
  (c) M5 scope の user 決裁を burn 決裁と統合できる、(d) OOS 窓は時間とともに伸びる
  (将来の再凍結で 2026 後半以降を含められれば power は単調増加)。
- **Q7 の閾値** (条件 10 に凍結): {全機械 gate PASS ∧ G4 p<0.05 ∧ K≥3} 未満は user 提示なしで
  auto-close。「弱くても user に聞いてみる」経路を残さない — bias 開示済み orchestrator の
  session-deliverable インセンティブに対する構造ガード。

---

## 11. family verdict (Task F)

**PARK-UNTIL-(次のいずれか早い方): (a) E7 phase-1 verdict 2026-08-28 後の membership 再評価で
admissible member が K≥3 に到達、(b) user が M5 の scope 追加 + #7 ban 例外を on-record で明示決裁。**

- **現構成 (委任 scope 内で admissible = M1+M2 の K=2) は 不成立** — 設計が壊れているからではなく
  (M1/M2 の継承・統計は条件付きで健全化可能)、**power が構造的に不足し OOS burn が正当化できない**
  から。charter の「degraded design より 不成立 を選ぶ」条項をここに適用する。
- default 進行の禁止: 本 verdict の PARK は「保留のまま自然に freeze へ進む」ことを許さない。
  復帰時は (i) K≥3 の member 集合を明記した改訂 payload、(ii) §9 の 17 条件の解決、
  (iii) **新規の敵対的検証** (本 report の条件消化の照合を含む) を経ること。
- 復帰時に M5 を含める場合: user 決裁文面に「#7 の再挑戦条件 (新データ必須) の例外承認」を
  明示的に含めること — 黙示承認・包括承認は不可。E7 経由の新 vix-family が成立するなら
  そちらが常に優先 (ban 例外が不要になるため)。
- 台帳処理: #20 は**予約のみ** (verdict 欄 = 「PARK 2026-07-31、敵対的検証で K=2 不成立、
  復帰条件付き」)。アクティブ枠を消費しない (locked/passive 扱い)。
- KB 永続化: 本 report + payload を raw/analysis に、台帳 1 行を catalog に。member 5 家系の
  verdict/ban は一切変更しない。

### 実行順序 (復帰した場合)

1. 改訂 payload (K≥3) → 敵対的再検証 → §9 条件解決 → pre-reg DRAFT → **凍結コミット** (rule:R1、
   sha256 pin 込み) → G0 → G1-G6 → (条件 10 充足時のみ) user ゲート → OOS 単一接触。
2. E15/E7 refreeze `--verify-only` (08-21 期限) と資源競合なし — ただし条件 14 の read-only 保全を
   両者の間で明文化。

---

## 12. score honesty 監査

- **orchestrator の自己申告は wave-3/4 水準で誠実**: bias 開示、M3/M4 の EXCLUDE lean と理由、
  M5 の scope flag を自ら立てた点、「K=2 なら 不成立 と言え」の明示、residual anti-conservatism
  attestation、UNDERPOWERED 分岐の要求 — いずれも本検証の結論と一致または本検証が採択。
- **膨張が残った箇所**: (i) price_source ブロック — 実在検証なしの断定 3 件 (§1.2-1/2/3)。これは
  「進めたい方向にデータ実在を仮定する」型の bias 漏出であり、W3-2 の probe-first 教訓の不履行。
  (ii)「Stats harness reuse」— 実際は骨格流用 + 主要部新実装 (§1.2-7)。(iii) M5 の ban 記述は
  文言引用こそ正確だが、「新データ必須」が explore 参加を塞ぐという帰結を明示せず
  「arbitrate whether portfolio membership constitutes a de-facto second bite」に薄めた —
  帰結を書けば ADMIT-WITH-CONDITIONS lean が成立しないことを考えると、ここが本 payload の
  最も bias に近い箇所。(iv) power 表は算術こそ正確だが ρ̄=0.1 と activity 等化の 2 前提が
  無検証のまま「K=3 marginal」の見出しを支えていた (§8.3)。
- **健全だった点**: mandatory_exclusions 6 件は全件一次ソースで支持され、恣意的な除外・温存は
  検出されなかった。member の recorded_explore 数値は 5/5 家系で一次ソースと完全一致 —
  数字の捏造・盛りはゼロ。

---

**総括**: 「方向は合うが弱い」死型 3 家系 (+多重性死 1) を束ねる portfolio estimand は、
設計としては条件付きで健全化可能であり、meta-selection bias の自己申告と部分補正は本プロジェクトの
検証文化の到達点を示している。しかし委任 scope 内の admissible member は 2 家系で、その K=2 book は
payload 自身の power 算術 (本検証で再計算一致) が「burn に値しない」と告げている。最良の一手は
測定ではなく待機である — E7 (08-28) が #7 の正規再挑戦経路と新規供給の両方を 4 週間後に運んでくる。
charter の凍結解釈に従い、現構成 不成立 / PARK-UNTIL を正直に記録する。
