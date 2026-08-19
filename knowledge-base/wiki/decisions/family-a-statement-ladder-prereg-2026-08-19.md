# 📝 DRAFT: family A statement_ladder — 発言ラダー→介入確率 explore pre-reg 起案 (2026-08-19)

**Status: DRAFT — 未採用・未凍結・未測定。** 採否 (台帳登録 + explore 枠付与) は **09-18 edge-supply-scan-monthly の A/B/C 統合裁定**。採用 → 敵対的検証 (blocking 条件解決) → 凍結コミット → two-pass 測定 の順。**それまで発言×介入ラベルのジョイント量 (hit/FA 率、リード時間、条件付き確率等) は計算禁止** — 本 doc 起草でも一切計算していない。

**起点**: registry `statement-ladder-foundation-readiness` resolve (PR #195、条件 = 収集基盤 PR #194 の main 着地) + user「進めて」(2026-08-19)。claim = `.ai/tasks/queue/20260819-family-a-statement-ladder-prereg-draft.md` + 本 PR。
**基盤**: [[mof-communication-data-infrastructure]] (`data/external/mof_statements/`、収集 daily cron 稼働中)
**裁定材料**: `knowledge-base/raw/analysis/intervention-history-anatomy-2026-08-18.md` (dossier) / [[mof-intervention-forward-prereg-2026-07-24]] §10 verdict (PARTIAL)
**様式踏襲**: [[mof-intervention-forward-prereg-2026-07-24]] / [[e22-vrp-explore-prereg-2026-08-17]] (two-pass + 敵対的検証)

---

## 0. 規律境界 (最重要)

1. **価格データ全面不使用**。family A の estimand は「発言→介入**ラベル**」のみ。価格反応・トレーダビリティは扱わない (それは family B = 介入イベント→回避/執行、**別 family・別 pre-reg**。family B には #4 E-C の必須負 prior「介入後 SELL drift は 2026 で符号逆 (+188.1p)」を継承させること)。
2. **2026 介入日を価格から推定しない** (T5 cross-LOCK 運用規約継承 — ラベルは MoF 公式開示のみ)。
3. **ラベル被覆の境界**: explore はラベルが公式確定した期間のみ (§3)。未開示期間 (現在 2026-07-30 以降) は接触禁止 = forward OOS の種。
4. lexicon v1 (`tools/mof_statements_lexicon.py` @ PR #194 commit `569dbe3f`) を**測定用スコアラーとして pin**。運用側 (daily cron) の将来の語彙追補は自由だが、family A の explore/OOS 測定は pin 版で行う (比較可能性の凍結)。

## 1. 背景と prior (中)

- **学術 prior 中**: エスカレーション構造は実在 (Bernal-Gnabo ordered probit 反応関数 = talk は act と同一反応関数上の前段 / 2022-09-14 レートチェック→09-22 実介入)。一方 verbal 単体の効果は減衰実例あり (2026-07 片山「断固」で円動かず — ただしこの期間のラベルは未開示なので false positive とはまだ呼べない、§4 P-A5)。
- **dossier の位置づけ**: 初撃の事前条件 4 点のうち「発言ラダー先行」は N=4 の記述で、**「152 円到達で 13 営業日放置」の反例が既知 = false positive 率が未測定**。→ **family A の仕事 = ladder 検出器の較正 (hit 率 / false alarm 率) の測定**。
- **収集時の目視所見** (PR #194、ジョイント統計なし): 2022/2024 とも介入前に L3 以上へのエスカレーションが可視。ただし **L3 は 2024 以降ほぼ常態化 = 単体では特異度が低い見込み** → primary は L≥4 遷移に置く設計仮説 (§2)。

## 2. Estimand (検出器較正、価格なし)

- **単位**: 東京営業日 d (MoF 開示ラベルのカレンダー)。
- **Signal 状態系列 X_d**: `lexicon_scores.csv` (大臣側発言のみ、会見単位 L0-L5) から日次化。会見日 = 当日 max_level、非会見日 = 直近会見値の carry-forward (窓 T 営業日、超過で L0 落ち)。
- **Primary 検出器イベント E_d (1 本に凍結予定)**: X が「低位帯から L≥4 に初到達」する遷移 (rearm 規約: 直近 R 営業日に L≥4 が無いこと)。
- **Primary endpoint**: E_d から H 営業日以内に公式円買い介入日が存在する確率 (hit) と、介入が続かない E_d の率 (false alarm) を、base rate (無条件の H 窓介入確率) と対比。
- **パラメータ候補空間 (起草時宣言、凍結は敵対的検証後)**: T ∈ {3, 5, 10} / R ∈ {10, 20} / H ∈ {5, 10, 20}。**凍結値は設計論拠のみで 1 セルを選ぶ (データによる較正は不可能 — 較正に使えば唯一の explore データを消費するため)**。起草時の設計仮説: (T, R, H) = (5, 20, 20)。敵対的検証はこの選択を**論拠でのみ**動かせる。
- **Secondary (記述のみ、判定不使用)**: L3 到達イベントの同型集計 / `no_comment` 急増 / E_d→介入のリード時間分布 / GDELT 強度との併走 / 話者別 (鈴木・加藤・片山 — 人物間スタイル移転は未検証と明記)。

## 3. データと窓

| 項目 | 定義 |
|---|---|
| Signal | `conferences/*.jsonl` → lexicon v1 (pin `569dbe3f`) スコア。被覆 2022-01-07〜 (daily cron で続伸) |
| Labels | `interventions_daily.csv` (MoF 公式日次明細)。**円買い (sell_USD_buy_JPY) のみ**。1991-2004/2010-2011 円売りレジームは母集団外 (#4 と同一判断) |
| Explore 窓 | **2022-01-07 〜 2026-07-29** (ラベル確定端 = 日次開示 2026-06-30 + 月次ゼロ窓 06-29..07-29。以後の開示で端は前進するが、**凍結時点の端で固定**) |
| Episodes | gap≥30d 規約 (#4 §4.1): 2022-09/10 (3日) / 2024-04/05 (2日) / 2024-07 (2日) / 2026-04/05 (3日) = **4 blocks / 10 介入日** |
| 2026 エピソードの会計 | #4 が OOS を接触消費済み + verdict 済み → family A の **explore には使用可、genuine OOS には使用不可**。ladder 語彙選定にも非使用だった (§4 P-A1 の半クリーン領域) |
| OOS | **forward のみ**: 2026-07-30 以降、将来の新規円買いエピソード (開示 cadence = 四半期。`mof-next-episode-reverdict` と同じ開示イベントを見るが estimand は別 — §7) |

## 4. Peek 会計 (起草時点の正直な固定)

| # | 情報 | 状態 |
|---|---|---|
| P-A1 | **lexicon v1 の語彙は 2022/2024 エスカレーション窓の目視検証を経て確定** (PR #194 の検証タスク) | **in-sample 汚染チャネル**: 2022/2024 上の explore 結果は「語彙選定に条件付き」の記述級。2026 エピソードは目視検証に使っていない (半クリーン)。**クリーンな判定は forward OOS のみ** — 本 family の主張上限を §6 で拘束 |
| P-A2 | 目視チェック表 (`reports/mof_statements_backfill-2026-08-18.md`) は会見スコア×介入日の**並置**を公開済み | ジョイント統計は未計算。ただし並置の視認自体が事前信念に入っている — 隠さない |
| P-A3 | dossier の「発言ラダー先行 (N=4)」記述 + 反例 1 件 | 既観測。primary を「較正 (FP 率)」に置く動機そのもの |
| P-A4 | #4 verdict (E-A p=0.0143 / E-C +188.1p) | 既観測。family A は価格を使わないため統計的干渉なし。E-C は family B へ隔離 |
| P-A5 | 月次開示: 2026-06-29..07-29 = 介入 0。**07-30 以降は未開示** | 2026-07 の「断固」発言群を false positive と呼ぶのは 08-29 月次 + Q3 日次開示まで禁止 |

## 5. 統計設計 (数値の最終凍結は敵対的検証後のコミットで)

- **Null**: ラベル系列の episode-block circular-shift (block 構造を保ったまま signal に対して一様シフト、B=10,000、explore 窓内)。統計量 = primary 検出器の joint hit 指標 (凍結時に 1 本確定: 候補 = hit−FA 差 or リード付き overlap 計数)。
- **⚠️ 検定力の正直な事前宣言**: 有効 N = **4 episode blocks** — **いかなる結果も記述級** (#4 §6 と同じ拘束: Bonferroni 級 edge 主張には決してカウントしない)。permutation p は粒度が粗く、PASS でも「機構が記述的に成立 + forward 監視に値する」以上を主張しない。
- **within-family 多重性**: 検定エンドポイントは primary 1 本 (m=1)。secondary は全て記述。
- **verdict 固定分岐**:

| verdict | 条件 (凍結時に数値確定) | 帰結 |
|---|---|---|
| PASS (記述級) | 検出器の hit/FA 分離が block-null 比で有意水準内 + FP 率が宣言上限内 | forward OOS 継続 (§6) + family B 設計の入力資格。**edge 主張・live 変更ゼロ** |
| FAIL | 分離なし or FP 過多 | **ladder 検出器は介入確率に情報なしと記録**。family B は発言層なしで設計 (or 独立に裁定)。lexicon 基盤は収集継続 (アーカイブ価値は独立) |
| UNDERPOWERED | イベント数が判定不能域 (凍結時に基準明記) | park、forward 蓄積のみ継続 |

## 6. Forward OOS (クリーン判定の本体)

- 収集は稼働済み (daily cron): 会見スコアは観測前に毎日確定・git 履歴で改竄不能。
- **OOS 判定イベント**: 新規円買いエピソードの四半期開示ごと (最初の機会 = Q3-2026 開示 ~2026-11-06)。エピソードゼロの四半期は「FP 側のみの検証」(検出器が鳴らなかったか) として同様に記録 — **鳴らない期間の無事故も検証対象** (152 円反例の教訓)。
- forward 窓の gate×outcome 計算は各開示着地までの間、全面禁止 (P-10 型)。
- **主張の上限**: forward で複数エピソードを跨いでも、月次〜四半期粒度の低頻度イベントゆえ edge 級主張には年単位を要する — 本 family の価値は edge claim ではなく **family B (回避設計) と T5 型運用判断への較正済み入力**。

## 7. 台帳・独立性

- **登録案: 台帳 #26 `statement_ladder_intervention_prob`** (裁定 = 09-18 scan の A/B/C 統合裁定)。
- **#4 (mof_intervention) との関係**: 同じ開示イベントを見るが estimand は直交 (価格シグネチャ→ラベル vs 発言→ラベル)。#4 の PARTIAL 再判定 (`mof-next-episode-reverdict`) と**同一開示を双方が使うことは二重主張ではない** (検定対象が異なる) — ただし verdict 文書は相互参照すること。
- **#25 E23 (中銀声明テキスト) との関係**: E23 = 多中銀声明×資産リターン (price-facing)。family A = MoF 介入コミュニケーション×介入ラベル (label-facing)。特徴量空間の一部 (テキスト) は近いが endpoint が直交。**両方が採用される場合、テキスト系 family の同時多重性はグローバル台帳で会計** (scan 裁定時に明記)。
- **family B/C との統合**: dossier どおり C (金利アンカー帯) をアンカー層とする統合設計の裁定に本 DRAFT を材料として供する。family A 単独の採否と統合設計の採否は独立に裁定可能な構造にしてある (本 estimand は他 family に依存しない)。

## 8. 実行手続き (採用時)

1. 09-18 scan 裁定 (採用/棄却/park + explore 枠の消費判断) — 改訂 WIP 原則下で現在の能動ラインは E23 のみ (1 本) であることを裁定時に再確認
2. 敵対的検証 1 本 (blocking 条件解決、パラメータ凍結は論拠のみで確定)
3. 凍結コミット (sha 明記) → two-pass 測定 (pass-1 = ハーネス dry-run/ラベル無接触、pass-2 = 測定)
4. verdict 追記 + 台帳更新 + registry (`family-a-explore-verdict` 期日型、予想日を deadline に刻む — #4 手続き教訓の継承)

## 9. 非 claim・除外 (DRAFT 時点で明示)

- 価格・EV・トレーダビリティの主張なし。live/tier/lot 変更ゼロ。
- 「介入後ショート/ロング」方向主張なし (family B の領分、E-C 負 prior 継承)。
- X (Twitter) データ不使用 (ToS)。財務官ぶら下がり発言は corpus 外 — 検出器の miss 側バイアス要因として verdict で言及必須 (2022 の主発信者は神田財務官)。
- 話者交代 (片山 2025-10〜) による語彙分布シフトは既知リスク — forward で検出器が沈黙し続ける場合、FAIL ではなく「語彙陳腐化」の可能性を verdict で区別 (pin 版と運用版の乖離レポート)。
