# E23 central_bank_statement_text (台帳 #25) explore pre-reg — testable form (2026-09-10)

**状態**: 🔒 **FROZEN (2026-09-10 — 本 LOCK commit が凍結点。以後の定義・閾値・語彙変更禁止、逸脱は verdict 無効)**。DRAFT 起草 + 敵対的検証 (自己、§7) は先行 commit `325359ef`。**凍結辞書 pin**: `tools/e23_lexicon_apel_grimaldi.py` sha256 = `f49586cad6e40e9c53e24adefeba78dcc5c9b925496c4b5b3808636c84b7bde8` (@ `325359ef`) — 測定ハーネスは実行時にこの sha を assert すること。**explore 枠 1/3 を本 LOCK で消費** (0/3 → 1/3)。**測定ハーネス実行まで、イベント×リターン結合統計は全面計算禁止 (S2 規律 / P-10 型)。本 doc 起草〜LOCK で結合量は一切計算していない。** registry: `e23-explore-verdict-deadline` (2026-09-20) 併設。
**family**: text モダリティ (中銀声明 tone 差分 × 自国通貨方向)。台帳 #25 (採用 = S2 診断枠 2026-08-18、[[../research/e23-cb-text-adjudication-s2-2026-08-18|裁定 doc]])。
**起点**: `.ai/tasks/queue/20260818-e23-cb-text-adjudication-s2.md` 残 item 3 (SLA waiver 期限 09-18 を scan#4 前倒し 2026-09-10 に同乗して処理 — [[../research/external-hypothesis-scan-round4-2026-09-10|scan#4]] §5)。
**先行物流**: [[../../raw/analysis/e23-data-availability-dossier-2026-08-18|データ実在 dossier]] (2026-08-18、45 tool 参照)。
**様式踏襲**: [[e22-vrp-explore-prereg-2026-08-17]] (事前コミット節) / [[family-c-rate-anchor-explore-prereg-2026-08-19]] (two-pass + 敵対的検証消化形式)。

## §0 規律境界 (最重要)

1. **live/shadow/tier/lot/Kelly 変更ゼロ**。本 family は探索であり、PASS しても stage-2 (執行設計 pre-reg + user 最終承認) の起草権を得るのみ。
2. **測定は LOCK 後の別タスク** (scan#4 の探索は S1-S2 まで、user 指示)。two-pass 厳守: pass-0 (コーパス census、outcome 非接触) → コミット → pass-1 (イベント列挙、fwd 非接触) → コミット → pass-2 (測定)。
3. **凍結辞書 primary**: `tools/e23_lexicon_apel_grimaldi.py` (本 PR 同梱、Apel & Blix Grimaldi 2012 = WP 261 の逐語転記、全観測窓に先行公刊)。**語彙の追加・削除・重み・否定処理の後付けは恒久禁止** (in-house 語彙 DoF の構造封鎖 = 裁定 doc 判定軸 2)。LOCK commit で本モジュールの sha256 を pin。
4. **TDW (Trillion Dollar Words, CC BY-NC) は secondary のまま保留** — E22 §2.1 型事前コミット: 使用開始は user のライセンス解釈決裁後のみ、かつ記述併記に限る (primary 判定に不使用)。**WCB_380k (gtfintechlab, CC BY-NC-SA) も同じ条項** — explore/研究利用は可、live 転送資格は PASS でも発生しない。
5. MoF 発言ラダー (family A、台帳 #27) とは **endpoint 直交** (label-facing vs price-facing) — BH 分母は合流しない。ただし text モダリティ 2 本の同時走行は両 doc に相互参照で on-record (scan#4 §3.2)。

## §1 仮説と prior (正直申告)

**H1 (sign-follow、片側)**: 中銀の政策声明の net-hawkishness が前回声明から上昇 (ΔNH > 0) した場合、その中銀の自国通貨は +5 営業日で超過的に増価する (下降なら減価)。

**機構**: 声明テキストの tone 差分は、数値 (金利変更・経済指標) に現れない政策傾斜の情報を運ぶ。即時のヘッドライン反応では消化しきれない nuance が D1+ の drift として残る、が残余仮説。

**負の prior (正直、裁定 doc §3 転記 + 更新)**:
1. **同一イベント面で二重 FAIL 済み**: E15 (FOMC/NFP/CPI 無条件窓、phase-0 C5) + E7 (数値サプライズ条件付け、discovery 0/24 符号系統逆)。残余仮説「数値に現れないテキストニュアンスのみが方向情報を持つ」は**狭い**。
2. 外部/新規 family の explore→OOS 生存 **0/17 系統** (base rate 4% [CI 0.7-19.5%])。
3. 公表後減衰 prior: CB communication の FX 反応は分単位が主 (Conrad & Lamla 2010 ほか) — D1+ 設計はその残差を狙う分、効果量は小さい側に賭けている。
4. E7 corpse の家系 (予定イベント条件付け) である事実は §8 で正面から扱う。

**正の差分 prior**: (i) 特徴量が外部凍結 (2012 公刊 — 探索自由度が構造ゼロ、ABG 辞書は lexicon 比較研究で最良分離の報告 [Quality & Quantity 2024])、(ii) multi-CB パネル (4 中銀) で blocks を E15 の 4-6 倍へ、(iii) D1 設計は BoJ 公表時刻不定 (11:30-12:30+遅延) を日境界で吸収 (dossier §5)、(iv) 無料で白黒 (E22 型)。

## §2 データ (pass-0 で census 確定、LOCK 時に取得ハーネス仕様を凍結)

| 項目 | 凍結値 |
|---|---|
| 対象文書 (**1 中銀 = 1 文書種に凍結**) | Fed: FOMC statement (パブリックドメイン) / ECB: monetary policy decisions press release / BOE: MPS (Monetary Policy Summary) / BoJ: Statement on Monetary Policy (**英語公式版のみ**、無い回は機械的欠測)。minutes・スピーチ・会見 Q&A は**全 CB で対象外** (DoF 封鎖) |
| 取得 | 各中銀公式サイト primary。WCB_380k は backfill/クロスチェックのみ (§0-4 条項下)。タイムスタンプ = 公式発表日時 (Fed 14:00 ET 固定 2013+ / ECB 13:45→14:15 CET 変更 2022-07-21 は D1 設計で非依存 / BoJ は日付のみ使用) |
| 価格 | `data/cache/massive/` 15m 凍結系 parquet → **UTC-day D1 再構築** (family C §2 と同一規約: date group / n_bars≥24 valid / D1 close = 最終バー close)。sha256 + 行数 manifest pin (LOCK 後の測定ハーネスで assert) |
| CB→ペア写像と方向 (凍結) | hawkish shift (d=+1) = 自国通貨増価: **ECB→EUR_USD (+d)** / **BOE→GBP_USD (+d)** / **BoJ→USD_JPY (−d)** / **Fed→EUR_USD (−d)** (USD の相手は EUR 1 本に凍結 — DXY 合成や複数ペア化の DoF を封鎖) |
| 同日衝突 | Fed と ECB が同一 UTC 日に声明 → **両イベント void** (同一ペアの二重賦課防止、件数 census 報告) |
| Explore 窓 | **声明日 2014-01-01 〜 2023-12-31** (E15/E7 と同一 split — 窓消費の会計は family 別に有効、裁定 doc §4-2) |
| OOS 窓 | **2024-01-01 〜 2026-06-30**、explore 全 binding gate PASS 時のみ単一接触 |
| 見込み N (dossier 実測見積、census で確定) | ~8/年 × 4 CB × 10 年 ≈ **explore 300 声明 → ΔNH≠0 イベントはその部分集合** (census 前は未知と正直に記録) |

**pass-0 census gates (outcome 非接触、機械判定)**:
- per-CB 被覆: explore 窓の各年 ≥6 声明を 80% 以上の年で確保できない CB は**機械的に除外** (件数報告)。
- 生存 CB < 2 → **DATA-BLOCKED** (pass-1 非解錠、設計変更禁止、正直クローズ)。

## §3 シグナル定義 (全 DoF 凍結)

| 要素 | 凍結値 |
|---|---|
| スコア | NH = (#hawk − #dove)/(#hawk + #dove + 1) — 凍結辞書モジュール (§0-3) |
| シグナル | **ΔNH_t = NH_t − NH_{t−1}** (同一中銀・同一文書種の直前声明比) |
| staleness | 直前声明との間隔 > **120 暦日** → 当該イベント void (比較可能性、件数報告) |
| イベント | ΔNH ≠ 0 の声明。**|ΔNH| の閾値・大きさ加重は使わない** (等加重、DoF 封鎖) |
| t0 | 声明公表の UTC 日。**公表日が valid D1 でない場合 (例: 2020-03-15 日曜緊急 FOMC) は次の valid D1 を t0 とする** (エントリは常に t0 close = 公表より後) |
| horizon | **PRIMARY = +5 valid D1** の close-to-close 方向純移動。SECONDARY (記述のみ、判定不使用) = +1 / +21 valid D1 |
| 計測単位 | pooling は **bp (log-return × 10⁴) × d** (クロスペア合算のため)。摩擦 gate は per-pair pips で併記 |
| drift 除去 | イベント寄与 = d × (r_{t0→t0+5} − μ_{pair,year}) — μ = 同ペア同暦年の全 valid 日無条件 5d リターン平均 (family C gate C の年内 demean を継承) |

## §4 統計 gates (凍結 — 数値の最終確定は LOCK commit、以後変更禁止)

- **Gate A (headroom、pass-1)**: 各生存ペアの無条件 median |fwd5| ≥ 10× RT (point)。不通過ペアは除外、全滅なら family KILL。
- **Gate B (power)**: pooled イベント N ≥ **100** (explore)。未達 = UNDERPOWERED (park、窓拡張・閾値救済禁止)。
- **Gate C (primary、m=1)**: 統計量 = §3 の demeaned 寄与の pooled mean (bp)。null = **CB×暦四半期 block の sign-flip permutation** (イベント間相関保存、B=10,000、seed 20260910)。**片側 p ≤ 0.05**。
- **Gate D (経済 floor)**: pooled mean net (per-pair pips、stressed RT ×2 控除、swap は 5bd 保有につき |bound| 1.5p を adverse 側へ計上) > 0。
- **Gate E (集中)**: max_y |S_y| / Σ_y |S_y| ≤ 0.50 (S_y = 暦年イベント寄与和)。
- **Gate F (一貫性)**: 年次 mean 符号正 ≥ 60% (N_y≥3 の年) ∧ LOYO pooled 符号不変 ∧ **LOCO (中銀 1 本抜き) pooled 符号不変**。
- **Gate G (dose-response、弱)**: |ΔNH| tercile T3−T1 の mean 寄与符号 = 正 (false-kill リスクは family C 前例どおり意図的に受容)。
- **knife-edge (全 gate PASS 後のみ、選択不使用)**: (i) h=+3/+10、(ii) entry t0+1 close、(iii) staleness 90/150 日。**符号反転 → FAIL**。辞書の摂動変種は**存在しない** (凍結辞書 1 冊 — それが本 family の設計思想)。
- verdict: 全 binding (A-G) 通過 = explore PASS → OOS pass (単一接触、gate C/D 同一様式 + OOS N≥40 floor)。gate B/census 未達 = UNDERPOWERED / DATA-BLOCKED。他 = FAIL クローズ。

**正直 MDE (事前記録)**: σ_5d ≈ 90-130bp、N=150-300 → mean-寄与 MDE ≈ 2.485×σ/√N×1.2 ≈ **18-32bp**。communication drift の文献効果量 (数 bp〜数十 bp) の下側は検出不能 — FAIL ≠ falsified の power caveat を §6 で凍結。

## §5 peek 会計 (起草時点で固定)

| # | 情報 | 状態 |
|---|---|---|
| P-E1 | E15/E7 の FAIL verdict (同一イベント面の M15 結果) | 既観測 — §1 負 prior 1 に転記。E23 の D1 estimand とは接触しない |
| P-E2 | ABG 辞書は 2012 公刊 | 全窓先行 = in-sample 汚染チャネルなし (本 family の核) |
| P-E3 | 声明コーパス本体 | **未読** — 本 doc 起草でスコアも分布も計算していない。pass-0 census が初接触 (outcome 非接触) |
| P-E4 | 2022-07-21 ECB 公表時刻変更 / 2020-03 緊急 FOMC 等の制度知識 | 公知の制度事実のみ設計に使用 (t0 規則へ) |

## §6 分岐と事前コミット節 (凍結)

- **PASS**: stage-2 起草権のみ。**かつ WCB/TDW の CC BY-NC 条項により、live 実装可否はライセンス/代替データの user 決裁点** (公式サイト自前コーパス + 凍結辞書のみで実装するなら NC 制約は非該当 — その場合も stage-2 R1 は別途必要)。
- **FAIL クローズ範囲**: 「凍結公刊辞書 tone 差分 × G4 中銀政策声明 × 自国通貨 sign-follow × 1-21bd 固定ホライズン」の全変種。**power caveat 義務**: MDE 18-32bp 未満の効果は検出不能 — 「CB テキストは falsified」型引用は estimand 監査なしに禁止。復活経路 = 新特徴量系 (公刊凍結モデル as-is 推論等) + 新 family + 事前差分節 + 新敵対的検証のみ。
- **UNDERPOWERED / DATA-BLOCKED**: park。コーパス蓄積は継続 (アーカイブ価値独立)。救済的窓拡張・CB 追加は禁止 (再開は split 再設計の新 pre-reg のみ)。
- 動機記録: WIP 原則 (能動測定ライン 0 本、2026-08-19 以降) + queue ticket SLA (waiver 期限 09-18) + user 承認済みの scan#4 前倒し原則。感情的動機なし。

## §7 敵対的検証 (自己、2026-09-10 — blocking は全て本文へ反映済み)

| # | 指摘 (レンズ) | 処置 |
|---|---|---|
| V1 | Fed/ECB が同一ペア (EUR_USD) を共有 — 同日衝突で二重賦課 (統計) | §2 同日 void 規則を凍結、census 報告 |
| V2 | 緊急会合 (非定例) は声明間隔が数日 — ΔNH の意味が変わる (estimand) | §3 staleness 下限は設けず (非定例も政策情報)、ただし間隔 > 120 日 void + **census で定例/非定例の件数を記述** (選択不使用) |
| V3 | BoJ 英語版の公表遅延があると t0 close 前にテキストが存在しない可能性 (lookahead) | §2 英語版のみ + **pass-0 で英語版同時公表の実在を確認、同時性が確認できない期間は当該 CB を除外** (機械規則) |
| V4 | "unemployment" 反転が WP 261 本文から直接読めない (出典忠実性) | 反転は二次文献 (Q&Q 2024) の ABG 仕様記述に従い**凍結**、lexicon docstring に出典明示 + census で反転該当 bigram 件数を報告 (監査可能化) |
| V5 | prefix wildcard の偽陽性 ("highlight"→high* 等) (測定) | 凍結辞書の既知限界として記録 — 修正しない (修正 = in-house 語彙編集の再開)。census で matched bigram 頻度上位を報告し監査可能に |
| V6 | 文境界規則がないと "low. Price" 型の偽 bigram (測定) | lexicon 実装に文境界 split を内蔵 + test pin (`tests/test_e23_lexicon.py`) |
| V7 | E7 corpse 家系の再着せ替えでないか (ban 隣接) | §8 差分節 — E7 ban の字義 scope 外 + 特徴量モダリティが別。family resemblance は §1 負 prior 1 で正直申告 |
| V8 | pooling の通貨規模差 (JPY pips ≠ EUR pips) (統計) | §3 bp 単位へ凍結 (pips は摩擦 gate 併記のみ) |
| V9 | ΔNH=0 (両声明無ヒット) が大量なら実効 N が census 前に不明 (power) | 正直に「イベント N は census 前は未知」と §2 に記録、gate B が機械防衛 |
| V10 | 否定文 ("did not raise") の誤極性 (測定) | ABG 原設計に否定処理は無い — 追加しない (C5)。既知限界として §6 power caveat と合わせ記録 |

## §8 ban 隣接差分節 (必須)

- **E7 (凍結 ban 原文: 「NFP/CPI headline z × sign-follow × M15 全変種」)**: E23 は (i) イベント種 = 金融政策声明 (経済指標でない)、(ii) 条件付け = テキスト tone 差分 (headline z でない)、(iii) ホライズン = D1+ (M15 でない) — **連言 ban の 3 要素すべて外**。sign-follow 構造の類似は §1 負 prior で正直申告 (E7 は符号系統逆で死亡 — E23 が同じ死に方をするなら §6 のクローズ範囲がそれを記録する)。
- **E15 (無条件イベント窓の棄却)**: E23 は ΔNH 符号で条件付け = 無条件窓ではない。
- **THA/Thales (wave-6 ADJACENT 処分)**: 「08-28 (E7 verdict) 後に新 family として再評価可」の処分どおり — 本 pre-reg がその再評価の実体 (E7 verdict は 08-17 前倒し確定済み)。
- **family A (#27 statement_ladder)**: MoF 発言 → **介入ラベル** (label-facing)。E23 は 中銀声明 → **価格** (price-facing)。特徴量空間 (テキスト) は近いが endpoint 直交 — BH 分母は合流しない。両方の verdict doc に相互参照を義務付け (scan#4 §3.2 で会計)。
- **P-10 系 (E12 volume / ECG #22 / E1)**: 全て非接触 (本設計は volume・equity curve・positioning を一切使わない)。
- **MoF #4 cross-LOCK**: 介入ラベル・介入日推定は不使用 (USD_JPY は BoJ 声明イベントのみ)。

## §9 実行手続き

1. 本 DRAFT (本コミット) → **LOCK = 別 commit** (lexicon sha256 pin + registry `e23-explore-verdict-deadline` 併設 + 台帳 #25 更新 + queue ticket done 移送 + SLA waiver 削除)。
2. LOCK 後の別タスク: pass-0 コーパス取得ハーネス + census (outcome 非接触) → コミット → pass-1/pass-2 (two-pass、seed 20260910)。
3. verdict 追記 + 台帳更新。explore スロット消費は **LOCK 時に 1/3 を宣言** (現在 0/3)。
