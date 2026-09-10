# MoF 通信モダリティ データ基盤 — 介入 ground-truth / 会見 transcript / lexicon ladder (2026-08-18)

> **rule:R3 (データ基盤、live 無関係)** — 収集のみ。live 発注経路・戦略・Kelly・価格データには一切触れない。
> **起点**: user 介入主張のスコーピング (wf_32d378df、2026-08-18) — 「7 月の負けは介入をくらったから。片山財務相の発言傾向が介入を示唆」→ 4 並列スコーピングの帰結 = **主軸は「当局発言ラダー lexicon × 公式介入ラベル」、X は不使用**。MEMORY `user_manual_edge_usdjpy_carry_2026_08_12` 追記4。
> **関連**: [[mof-intervention-forward-prereg-2026-07-24]] (#4、価格モダリティ側の 🔒 LOCK) / [[t5-restore-eval-and-carrydip-revival-2026-08-10]] (cross-LOCK 運用規約) / [[external-hypothesis-scan-round3-2026-08-14]] (供給ライン枯渇の文脈) / [[e1-positioning-ingest-2026-07-14]] (同型の「今から蓄積」基盤)

## 0. ⚠️ 規律境界 (最重要 — 着手前に必読)

1. **本基盤は収集のみ**。発言×介入×価格の**ジョイント測定 (IC / EV / overlap / イベントスタディ) は、別 pre-reg (hypothesis-catalog 登録 + 観測前凍結 + 敵対的検証) まで全面禁止**。
2. **2026 年の介入日を価格から推定することは禁止** — #4 pre-reg §2.2 の凍結識別 rule の再実装にあたり、OOS を burn する (T5 cross-LOCK 運用規約: 介入日の認定ソースは MoF 公式開示 = 外部一次情報のみ)。
3. **2022-2024 の介入ラベルは explore 専用** (#4 §7 P-1 で会計済み)。この上での発言→介入の関係測定は #4 と別 estimand (通信 vs 価格シグネチャ) なので #4 verdict を待つ必要はないが、**測定開始そのものが (1) の pre-reg を要する**。
4. **2026 窓 (04-28..05-27 + 現行 7-8 月エピソード) は #4 verdict まで発言→価格反応の測定からも除外** (発言 anchor forward が P-10 量を事実上再構成するリークになるため — wf_32d378df lock 監査の保守境界)。
5. **X (Twitter) スクレイピングは一切しない** (ToS 明示禁止。CME ToS 403 の教訓と同型)。

## 1. なぜ今か

- E21 (human-signal-stream) / E22 (VRP) が 2026-08-17/18 に FAIL クローズし、**能動供給ラインがゼロ** (残りは全て calendar-lock)。通信モダリティは未検証の新系統。
- 学術 prior = **中** (wf_32d378df): エスカレーション構造は実在 (Bernal-Gnabo ordered probit 反応関数、2022-09-14 レートチェック→09-22 実介入) だが、verbal 単体の価格効果は減衰中 (2026-07 片山「断固」で円動かず = false positive 実例)。family 分割は (A) 発言ラダー→介入確率 (prior 中) / (B) 介入イベント→回避・ショート (weekend_gap_fade 型、別 family)。
- **transcript は「今しか取れない」データではないが、MoF がオンライン保持を purge する** (現行 2023-04〜のみ、旧分は WARP 依存)。corpus の repo 内固定に archival 価値がある。会見は forward で日次追記。
- 介入 ground-truth (日次明細) は四半期ラグ、月次総額は約 1 ヶ月ラグ → **forward の real-time 変数は発言側のみ**という設計制約が (B) family の estimand 設計に効く。

## 2. 集めるもの (3 系統 + 検証)

| # | 系統 | 出力 | 更新 |
|---|---|---|---|
| 1 | 介入 ground-truth | `data/external/mof_statements/interventions_daily.csv` (1991-04〜、公式日次明細) + `interventions_monthly_pending.csv` (月次総額窓) | daily cron |
| 2 | 会見 transcript | `conferences/{YYYYMM}.jsonl` — 2022-01〜2023-03 = NDL WARP (pywb `id_` 原本)、2023-04〜 = mof.go.jp。role タグ (opening/question/answer) 付き全文 | daily cron (追記) |
| 3 | 報道強度 + 新着 | `gdelt/*.csv` (DOC timelinevol 2017〜) + `rss_items.csv` (news.rss 為替関連) | daily cron |
| 4 | lexicon スコア | `lexicon_scores.csv` (L0-L5 + no_comment) — corpus から決定的再生成 | daily cron |

実装: `tools/mof_statements_lexicon.py` (純関数、テスト `tests/test_mof_statements_lexicon.py`) / `tools/mof_statements_ingest.py` (backfill) / `tools/mof_statements_daily.py` + `.github/workflows/mof-statements-daily.yml` (forward、JST 06:30)。データ詳細: `data/external/mof_statements/README.md`。

## 3. lexicon ladder v1 (設計根拠)

Gnabo 系 talk/act 離散化 (no-talk / talk / talk+act の ordered probit) + 実務 escalation ladder (「excessive moves 懸念 < あらゆる選択肢 < decisive action < レートチェック」) のコード化:

| L | 名前 | 代表パターン | ladder 上の意味 |
|---|---|---|---|
| 0 | — | (為替言及なし / ラダー語なし) | ベースライン |
| 1 | watch | 注視 / 動向を見守る | 常套句 (ほぼ毎会見) |
| 2 | concern | 過度な変動 / 急速な変動 / 一方的な動き / 憂慮 / 緊張感 | 懸念表明 |
| 3 | readiness | あらゆる選択肢 / 排除しない / 適切な・万全な対応 / 投機 | 行動準備の示唆 |
| 4 | resolute | 断固 / 毅然 | 行動切迫の定型句 |
| 5 | action | 介入を実施 / 平衡操作 / レートチェック | talk+act (実行言及) |

設計上の要点 (テストで固定):
- **大臣側発言 (冒頭発言 + 答) のみスコア** — 記者が質問で「断固たる措置をとる用意は？」と引用してもスコアに入れない。
- 答弁の為替文脈は直前の質問から継承 (大臣は「為替」と繰り返さないことが多い)。
- `no_comment` (コメント差し控え) は**レベルではなく別フラグ** — 介入実施期の「ノーコメント」急増自体が情報 (2022-09-22 当日の答弁が典型)。
- スコアは **max level** (会見内の最大到達段)。段別マッチ句も全記録し、lexicon 改訂時の監査を可能にする。

## 4. 整合確認 — 既存 `mof_interventions.csv` (383 events) との突合 (2026-08-18 実施)

- 行単位 (date, pair, direction, amount) 突合: **383/383 完全一致、mismatch 0、legacy 側のみの行 0**
- 新規は 2026 Q2 開示の 3 行のみ (下記 §7)。3 行合計 ¥11,734.8bn ≒ 月次総額 ¥11,734.9bn (丸め整合) — legacy の monthly-aggregate 行と符合
- 月次 pending: **2026-06-29〜07-29 窓 = 介入額 0 (公式)**。07-30 以降のラベルは次回月次公表 (~08-29) まで未開示 — user の「7 月介入」主張のうち 07-10 を含む窓は公式にゼロと確定、07-30/31 は未開示のまま (価格からの推定は禁止)
- 凍結 legacy CSV は #4 pre-reg の参照物のため本基盤からは不変更 (SSOT は新 `interventions_daily.csv` 側で前進)

## 4.1 収集時に発見した構造事実 (2026-08-18)

- **MoF 会見 index には欠落月が実在する**: 202310-12 / 202601-04 の月ページは作成されておらず (当時の WARP キャプチャでも不存在)、個別 transcript (`my{YYYYMMDD}.html`) は**未リンク孤児として存在** — 日付総当たりプローブで 62 会見を回収。forward cron にも同フォールバックを実装済み (index 依存だと将来も盲点化するため)
- **2023-04 のサイト改修で旧ページは `.htm`→`.html` に改名**。WARP 経由の 2022 年分は `.htm` 名で取得 (両拡張子対応)
- corpus には大臣会見のほか、**神田財務官 単独会見 2 本 (2023-08-19 / 2023-12-07)**・日銀総裁共同会見・G7 議長会見も含まれる (話者フィールドで区別)

## 5. 検証 — lexicon スコアの目視チェック (2022-09 / 2024-04-05)

判定基準 (目視、統計なし): レートチェック (2022-09-14) → 09-22 介入、および 2024-04 末 → 04-29/05-01 介入の前に、会見スコアがベースライン (L1) からエスカレーション (L3-L4) を示すか。介入ラベルは 2022/2024 の**公式開示済み** (explore 専用会計) のみ使用。**価格データは不使用**。

詳細テーブル: `reports/mof_statements_backfill-2026-08-18.md`

**判定: PASS (目視)** — corpus 502 会見 (2022-01-07〜2026-08-05、うち ladder 語あり 202。L1=27/L2=37/L3=115/L4=16/L5=7):

- **2022 窓**: 8 月ベースライン L0-L2 → 09-02 以降 **L3 常態化** (適切な対応/投機/憂慮) → 09-29 **L4 (断固)** → 10-03 **L5 (「介入を行い」実施明言)** → 10 月中 L3-L4 持続。介入 3 日のうち会見日は 10-21 のみ (09-22/10-24 は会見なし日)
- **2024 窓**: 3 月中旬まで L0 → 03-22 L2 → 03-26 以降 **L3 常態化** (行き過ぎた動き/万全の対応) → 04-02 **L5 (「介入を行う」条件付き言及)** → 4 月 L3 持続 → 介入 04-29/05-01 (いずれも祝日/連休 = 会見なし日) → 5 月に L2-L3 へ減衰
- 含意 (記述のみ、検定なし): エスカレーション構造は両エピソードで可視。ただし (a) 介入当日は会見が無いことが多い (real-time 検知には財務官発言/報道系の補完が必要)、(b) L3 は 2024 年以降ほぼ常態化しており、単体では特異度が低い — family (A) 設計時は L4/L5 への遷移や no_comment との複合を検討すべき (これは設計メモであり測定ではない)

## 6. 既知の限界と次の決裁点

- **大臣会見のみ**: 2022/2024 の実務上の主発信者だった財務官 (神田) のぶら下がり発言は transcript 非公開。GDELT 報道強度が代理。→ family (A) の設計時は「会見スコア」と「報道強度」を別変数として扱うこと。
- **X は forward の従属チャネル候補** (公式 API pay-per-use、user 決裁 + クレカ登録が必要)。片山大臣在任 <1 年で単独 family は power 不足 — 主軸にはしない (wf_32d378df)。
- **次の決裁点**: family (A) 発言ラダー→介入確率 の explore pre-reg 起案は、**#4 verdict 執行後** (E-A/E-C の帰結で family (B) の設計が変わるため) + 月次スキャンでの台帳登録を経ること。本基盤はそれまで純粋に蓄積のみ。

## 7. 2026 Q2 開示の着地 (収集時の観察事実)

backfill 時点 (2026-08-18) で、公式 CSV は **2026 Q2 (4-6 月) の日次明細を含む** (2026-08-07 公表)。行はそのまま `interventions_daily.csv` に格納した (公式一次情報の収集であり LOCK 非抵触)。**#4 pre-reg の verdict 執行 (E-A overlap / E-C forward net の計算 + §8 ナイフエッジ 3 点検査) は本基盤のタスク外** — registry `mof-q2-2026-disclosure-verdict` (期日: 着地+10 日、backstop 09-30) が監視主体であり、期日超過が疑われるため別タスクとして起票済み。**本 doc・本ツール群では E-A/E-C 量を計算していない** (P-10 遵守)。
