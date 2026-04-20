# Lessons Learned — 間違い・修正・教訓の蓄積

## なぜこのページが必要か
同じ間違いを繰り返さないために、「何を間違えて、なぜ間違えて、どう修正したか」を記録する。
次のセッション開始時にwiki/index.mdから辿れるようにすることで、判断の精度が複利で向上する。

## 追加基準（いつ lesson を作るか）
以下のいずれかに該当する事象が発生したら、lesson ページを作成する:
1. **バグ修正**: コード上のバグを発見・修正した場合（特に統計やデータ選択に関わるもの）
2. **想定外の結果**: BT/Live乖離 >15pp、または分析結果が直感と大きく矛盾した場合
3. **判断変更**: 過去の判断が覆された場合（audit rejection, 戦略停止/復活, パラメータ巻き戻し）
4. **同じ間違いの繰り返し**: 過去lessonに類似の問題が再発した場合（根本原因が未解決の証拠）
5. **システム設計の教訓**: 開発フロー・KBフロー・自動化で構造的問題が発覚した場合

### ページテンプレート
```markdown
### [[lesson-名前]]
**発見日**: YYYY-MM-DD | **修正**: vX.Y
- 問題: （何が起きたか）
- 症状: （どう表面化したか）
- 原因: （なぜ起きたか）
- 修正: （どう直したか）
- 教訓: **（一文で一般化した学び）**
```

### セッション中の候補検出
PreCompact hookがセッション中の以下のキーワードからlesson候補を自動検出する:
`fix`, `bug`, `バグ`, `間違`, `修正`, `想定外`, `乖離`, `覆`, `REJECT`, `DEMOTE`

## バグ・設計ミスの教訓

### [[lesson-shadow-contamination]]
**発見日**: 2026-04-10 | **修正**: v8.4
- 問題: get_stats()がShadowトレードを含めてWR/EVを算出 → 統計が実態を反映しない
- 症状: bb_rsi WR=52.2%(post-cut) vs 34.0%(current window)の矛盾
- 原因: is_shadow=0フィルターの欠如
- 修正: get_stats() + get_all_closed()にexclude_shadow=Trueデフォルト追加
- 教訓: **統計を出す前に「このデータに何が含まれているか」を常に確認する**

### [[lesson-xau-friction-distortion]]
**発見日**: 2026-04-10 | **修正**: v8.4
- 問題: avg_friction=7.04pip/tradeは「全戦略がフリクションに負けている」と誤解させた
- 実態: FX-only friction=2.14pip、XAU=217.5pip。XAUが平均を30倍に歪めていた
- 修正: XAU停止 + ペア別摩擦分離分析
- 教訓: **集計値は必ずセグメント分解する。平均値は嘘をつく**

### [[lesson-bt-endpoint-hardcoded]]
**発見日**: 2026-04-12 | **修正**: v8.5
- 問題: DTのBTエンドポイントがUSD_JPYハードコード → EUR/GBP/EURJPYのBTが不可能
- 発見経緯: 新エッジ戦略のBTで他ペアが動かずユーザーが指摘
- 修正: symbolとdaysをリクエストパラメータ化
- 教訓: **BT/本番統一原則は「ロジック統一」だけでなく「ペア・期間のパラメータ化」も含む**

### [[lesson-1m-scalp-not-the-problem]]
**発見日**: 2026-04-10 | **修正**: なし（誤った提案を却下）
- 問題: 独立監査が「1m scalpを全廃し15m DTへ移行」を勧告
- 実態: bb_rsi×JPYはPost-cutoffでPF>1の実測データがある唯一の戦略
- FX-onlyのPost-cutoff PnL=+96.8pip（当時黒字、後に-646pipへ悪化）→ 当時の判断根拠は正しかったが、N不足で結論が反転した
- 教訓: **理論計算(friction/SL=43-71%)が実測データ(PF=1.13)と矛盾する場合、Nが十分か確認してから実測を信じる**

### [[lesson-macdh-absorption-risk]]
**発見日**: 2026-04-10 | **修正**: 提案を却下（独立監査勧告）
- 問題: macdh_reversalをbb_rsiに+0.5スコアボーナスとして吸収する提案
- リスク: 唯一のPF>1戦略(edge=0.45pip)を汚染し、エッジ消滅の可能性
- 教訓: **唯一の正エッジ戦略に対する実験は、リスク/リワードが非対称（最悪=エッジ消滅）**

### [[lesson-tier-classification-data-mixing]]
**発見日**: 2026-04-10
- 問題: bb_rsiを全ペア混合でWR=44.3%→「Tier 3」と分類
- 実態: USD_JPY限定ではWR=54.7% PF=1.13 → 正しくはTier 1
- 教訓: **ペア×戦略の粒度で評価しないと、「勝てるペア」と「勝てないペア」が相殺される**

### [[lesson-kb-drift-on-context-limit]]
**発見日**: 2026-04-13 | **修正**: 手動整合
- 問題: v8.6-v8.8のコード変更がgitにコミットされたが、changelog/wiki/session logに未反映
- 原因: KB構築(Phase 4)後にv8.6-v8.8の実装が進行→使用量制限でセッションが途切れ、KB更新が実行されなかった
- 症状: changelog=v8.4止まり、index.md=v8.4、未解決事項に「DSR未実装」「GBPアジア除外未実装」（実際は実装済み）
- 修正: git log全件精査→changelog/index/session log/edge-pipeline を実態に合わせて更新
- 教訓: **コード変更とKB更新は同一コミットで行う。コードだけ先にコミットしてKBを後回しにすると、セッション断で不整合が固定化する**
- 対策: feat()コミット時に関連するchangelog/wiki更新も同じコミットに含める。セッション終了が近い場合はコード変更よりKB更新を優先する

### [[lesson-strategies-page-drift]]
**発見日**: 2026-04-20 | **修正**: v9.4 (tools/strategies_drift_check.py + 13 ページ書き換え)
- 問題: `wiki/strategies/*.md` の Status 行が `tier-master.md`（自動生成）と乖離
- 症状: bb-rsi-reversion.md が "Tier 1 (PAIR_PROMOTED x USD_JPY)" のまま — 実態は SCALP_SENTINEL + PAIR_DEMOTED(全4ペア)。orb-trap / trendline-sweep / bb-squeeze-breakout 等 13 ページで同種ドリフト
- 原因: lesson-kb-drift-on-context-limit と同じ病理（Tier 変更コミットに strategies/*.md の更新が同梱されない）。tier_integrity_check は code 内整合のみ検証し、md 文面は走査していなかった
- 修正: 13 ページの Status 行を tier-master.json と一致させ、旧 Status は「履歴」「Previously ...」で保持
- 対策: **仕組み化** — `tools/strategies_drift_check.py` 新規導入。tier-master.json を truth として md の Status 行を検証、exit 1 で pre-commit/CI に組み込み可能
- 教訓: **自動生成 KB と手書き KB は必ず機械的整合チェックで固定する** — レビューだけでは見逃す（bb_rsi はヒーロー戦略扱いで v8.9 降格後も Tier 1 記述が 7 日間放置された）

### [[lesson-raw-json-to-llm]]
**発見日**: 2026-04-13 | **修正**: v8.9
- 問題: daily_report.pyが500件の生JSONを `[:5000]` 文字列切断してClaude APIに送信 → 299件中4件しか分析不能
- 症状: レポートに「JSONが途中切断」「確認できた範囲4件」と記載。戦略別集計が不可能
- 原因: 「LLMは賢いから生データを渡せば集計してくれる」という設計思想
- 修正: Python側で戦略×ペア集計・セッション時間帯フィルタ・OANDA突合を事前計算し、集計テーブルをLLMに渡す
- 教訓: **LLMに渡すのは「判断材料（集計済みテーブル）」であって「生データ（JSON）」ではない**

## 開発プロセスの教訓

### [[lesson-bt-before-deploy]]
- ユーザー指摘: 「先にBTを行って欲しい」
- 問題: 6新エッジ戦略をBTなしでSentinelデプロイした
- 正しいフロー: 実装 → BT → BT結果で判断 → デプロイ
- 教訓: **Edge Pipeline Stage 2→3のGate（BT N≥30, WR>BEV+5pp）を飛ばさない**

### [[lesson-changelog-as-evaluation-anchor]]
- 発見: 「いつからのデータを使うか」で分析結論が180度変わる
- 例: bb_rsi WR=52.2%(post-cutoff) vs 34.0%(全体) → changelog参照で解決
- 教訓: **定量評価の最初のステップは「changelog.mdを読んでdate_fromを決める」**

### [[lesson-tool-verification-gap]]
**発見日**: 2026-04-13 | **修正**: v8.9
- 問題: BT乖離パーサーを実装したが、regexバグで0件出力。気付かずに戦略変更を実施
- 原因: (1) スモークテストが「壊れない」しか検証しない (2) ツール作成→忘却→直感で判断 (3) 並列実行で検証スキップ
- 修正: 正例テスト追加 (TestBtDivergenceParser)、パーサーregex修正、ファイル選択ロジック改善
- 教訓: **分析ツールは実データで「正しい出力が返る」ことを検証してから使う。空結果はバグ**
- 対策: [[claude-harness-design]] RC6対策ルール参照

### [[lesson-sentinel-promoted-conflict]]
**発見日**: 2026-04-13 (3回目: 2026-04-14) | **修正**: v8.9
- 問題: PAIR_PROMOTEDとUNIVERSAL_SENTINELの両方に同じ戦略 → shadow化 → OANDA遮断、QH/BE未適用
- 再発3回 (session_time_bias, london_fix_reversal, xs_momentum)
- 修正: post-commit-verifyにPAIR_PROMOTED×SENTINEL重複チェック追加
- 教訓: **PAIR_PROMOTEDに追加したら、SENTINEL/FORCE_DEMOTEDに残っていないか自動検出で確認する**

### [[lesson-reactive-changes]]
**発見日**: 2026-04-15 | **修正**: 判断プロトコル追加
- 問題: 4/14の1日データ分析で反射的に4件の対策を実装。「データを待て」と言いながら待たなかった
- 原因: 「分析」と「対策」を同じ思考プロセスで処理。問題発見→即修正のエンジニア的衝動
- 修正: 判断プロトコル追加（根拠データ日数/既存戦略整合性/バグvsパラメータ/動機記録）
- 教訓: **「分析」は1日で有用。「対策」は365日BTまたはLive N≥30に基づくこと。根拠が1日データなら実装保留。**

### [[lesson-dte-htf-bypass]]
**発見日**: 2026-04-16 | **修正**: v9.1 (36e5cbb)
- 問題: DTE戦略がHTF Hard Blockをバイパスし、GBP_USD session_time_bias 4/4 SELL全敗、dt_sr_channel_reversal 4/4全敗
- 症状: HTF=bullでSELLトレードが実行される。reasonsに「📈 4H+1D 上昇一致 → SELLブロック」が記録されているのにトレードが通過
- 原因: (1) DTE HTF Hard Blockが最善候補にのみ適用（リスト段階でフィルタリングしていなかった） (2) 個別戦略にHTFチェックがなかった
- 修正: 3重HTFガード実装 — (a) DTE候補リスト全体からHTF違反を除外 (b) session_time_bias.py/dt_sr_channel.py内にself-contained HTFチェック追加 (c) mainパイプラインのscore=0化
- 教訓: **セーフティネットは単一レイヤーに依存してはならない。戦略自身がHTFを知っているべき（self-contained guard）。中央フィルターのみに依存すると、パイプラインの構造変更でバイパスが生まれる**

### [[lesson-reactive-changes-repeat]]
**発見日**: 2026-04-16 | **修正**: ADX gate revert
- 問題: lesson-reactive-changesと同じ失敗を翌日に繰り返した。4日間N=628のインサンプルデータでADX>30閾値を3戦略に実装→即デプロイ→ユーザー指摘で巻き戻し
- 原因: IC分析・MAFE分析の「発見の興奮」で判断プロトコルを飛ばした。KBを1ページも読まずに実装に突入
- 修正: ADX gate revert。分析結果はKBに記録、実装はBT検証後に保留
- 教訓: **lesson-reactive-changesが存在するにも関わらず再発 = 判断プロトコルの遵守が構造的に担保されていない。pre-commitにKB参照チェックを入れるか、判断前の強制pause機構が必要**

### [[lesson-confidence-ic-zero]]
**発見日**: 2026-04-16 | **修正**: 未（分析結果として記録）
- 問題: 全戦略のconfidenceスコアのIC(Information Coefficient)が0.009 — 勝敗予測力ゼロ
- 分析: conf = min(85, 50 + score*4) の線形変換+capが予測力を破壊。scoreのIC=0.089は弱いが実在
- 発見: 12戦略(382/628=61%のトレード)がscore=0固定。scoreフィールドを返していない
- 発見: ema_conf IC=-0.058（逆相関: 高いほど負ける）
- 発見: レジーム×方向の順張り/逆張りでWR差なし（両方21-23%）→ レジーム判定が方向予測に寄与していない
- 教訓: **指標の有効性はIC計測で定量的に検証すべき。「理論的に正しいはず」は検証ではない。confidenceスコアの設計はBT段階でICを測定してから決めるべきだった**
- 次のアクション: (1) 全戦略にscore return義務化 (2) BT上でADX閾値の最適化検証 (3) HMM Phase 2でレジーム判定改善

### [[lesson-orb-trap-bt-divergence]]
**発見日**: 2026-04-16 | **修正**: v9.1 (36e5cbb)
- 問題: orb_trapが短期BT(60d)ではWR=79-83% EV>+0.5だったが、365d BTでは全ペア負EV (JPY=-0.854, EUR=-0.488, GBP=-0.258)
- 症状: PAIR_PROMOTED 3ペア + LOT_BOOST 1.5xで損失拡大
- 原因: 短期BTのカーブフィッティング。60日の好調期間がたまたまBTウィンドウに入っていた
- 修正: FORCE_DEMOTE + PAIR_PROMOTED削除 + LOT_BOOST削除
- 教訓: **短期BT(60d)のWR/EVを365d BTで必ず検証すべき。特にN<30の戦略は短期BTの分散が大きく、カーブフィッティングと区別がつかない**

## Related
- [[changelog]] — バージョン別変更タイムライン
- [[independent-audit-2026-04-10]] — 覆された判断の詳細
- [[edge-pipeline]] — Stage Gate（飛ばしてはいけない手順）

### [[lesson-conf-undefined-bug]]
**発見日**: 2026-04-14 | **修正**: v9.0 C1
- 問題: demo_trader.py L2974/2993/3035で `conf` 変数が未定義 → NameErrorで tick全体が中断
- 症状: RANGE+SELL, TREND_BULL+BUY, TREND_BEAR+BUY のシグナルが全て無音で消失。ログは「シグナル取得失敗」に誤分類
- 原因: `confidence` 変数を `conf` として参照（タイポ）
- 修正: `conf` → `confidence` に全箇所置換 + ログ文字列も修正
- 教訓: **変数名変更時は全参照箇所をgrepで確認する。新変数が既存フィルターで使われていないか検証する。**

### [[lesson-shadow-persistence-bug]]
**発見日**: 2026-04-16 | **修正**: v9.x
- 問題: FORCE_DEMOTED戦略がis_shadow=0でDBに書き込まれ、統計を汚染（114件）
- 症状: get_stats()でFORCE_DEMOTED戦略のトレードが非shadow扱い → PnL/WR/Kellyが実態より悪化
- 原因: open_trade() (L3890)でis_shadow書込み → 安全ネット(L4049)でis_shadow=True変更 → DB UPDATEなし。~160行の乖離
- 修正: (1) 安全ネット後にDB UPDATE追加 (2) 起動時マイグレーションで既存114件を修正
- 教訓: **DB書込み後にフラグを変更するロジックは、変更をDBに反映しないと無意味。書込みと後処理の順序を常に確認する**

### [[lesson-all-time-vs-post-cutoff-confusion]]
**発見日**: 2026-04-20 | **修正**: 判断プロトコル追加
- 問題: aggregate edge=-0.1348, strategy Kelly edge=-0.353 等を根拠に複数施策提案したが、全て all-time data 由来。post-cutoff Live N=14 EV=+0.36 (わずか正) が真の状態
- 原因: /api/demo/stats デフォルトが all-time、Risk dashboard の edge 計算ウィンドウ不明のまま使用、KB 確認を怠った
- 修正: 数値を信じる前に算出ウィンドウ確認、cutoff 明示指定、複数 source 比較前に filter を揃える
- 教訓: **All-time data は pre-cutoff 汚染を含むため Kelly/edge 判断に使ってはならない**

### [[lesson-user-challenge-as-signal]]
**発見日**: 2026-04-20 | **修正**: Challenge-Response Protocol 追加 ([[claude-harness-design]] 内)
- 問題: 同一セッション内でユーザー challenge を4回受け、各回で分析の欠陥を指摘されたが、challenge パターン自体を診断信号として扱わなかった。末に「次から気をつけます」と宣言し KB 未保存 = lesson-say-do-gap 再発
- 原因: Challenge を "修正の機会" として個別処理し、"構造欠陥の診断信号" として扱わなかった
- 修正: claude-harness-design.md に Challenge-Response Protocol 追加。trigger 発話別の強制応答、即 codify 原則
- 教訓: **ユーザーの challenge は自分の分析の診断信号。同セッション内反復は構造欠陥。「次から」は言行不一致、今すぐ KB に書け**

### [[lesson-late-stage-signal-override]]
**発見日**: 2026-04-16 | **修正**: v9.x
- 問題: vwap_mean_reversion/streak_reversalがSL/TP計算後にsignal方向を変更 → SL/TPが逆方向のまま + HTF Hard Blockをバイパス
- 症状: BUYなのにTPがentry下方(158.706→158.612)、0.3秒で即TP_HIT損失。HTF=bearなのにBUY発行
- 原因: compute_signal_daytrade()内の実行順序。SL/TP計算(L1707)→HTFブロック(L2464)→vwap/streak(L3092+)の順で、後段がSL/TPもHTFも無視
- 修正: (1) vwap/streak: signal変更後にSL/TP再計算 (2) 独立HTFチェック追加 (3) vwap: score上書き(旧方向のscore汚染防止)
- 教訓: **関数内で後段がsignal/SL/TPを変更する場合、前段の計算結果(SL/TP, HTF, score)との整合性を再確認する。直列処理の後段は前段の前提条件を壊しやすい**

### [[lesson-say-do-gap]]
**発見日**: 2026-04-13 | **修正**: ハーネスv2 原則0追加
- 問題: 「0.5秒でやる」と宣言→5分別スレッドを実装。「即時アクション」→数時間放置。繰り返し発生
- 原因: コンテキストウィンドウ内で中間タスクが割り込み、元の宣言を忘却。トラッキング仕組みなし
- 修正: ハーネス原則0(Say→Do→Verify)追加。TodoWriteでの宣言即タスク化を徹底
- 教訓: **「Xする」と言った瞬間にXを実行する。次のタスクに移る前にXの完了を確認する**

### [[lesson-resend-shadow-leak]]
**発見日**: 2026-04-20 | **修正**: v9.x hotfix (demo_db.py)
- 問題: `_resend_pending_oanda_trades()` が is_shadow フィルターなしで全 open trades を OANDA 送信
- 症状: is_shadow=1 の FORCE_DEMOTED/MTF-shadow 戦略に oanda_trade_id が設定される
- 原因: `get_open_trades_without_oanda()` SQL に `AND is_shadow=0` が欠如
- 修正: `AND is_shadow=0` 追加 (1行)
- 教訓: **補完送信パスは通常の OANDA 送信ガードと同じ is_shadow/is_promoted チェックを持つべき**

### [[lesson-sentinel-score-gate-gap]]
**発見日**: 2026-04-20 | **修正**: v9.x (task/priority1-sentinel-score-gate)
- 問題: Clean Slate後 Sentinel N=1 停滞。score_gate(score<0) が Sentinel 経路も一律ブロック → shadow すら蓄積できず
- 原因: spread_wide/spike は `_is_shadow_eligible` でバイパスしていたが、score_gate のみ Sentinel 非対称に厳しい
- 修正: score_gate に SCALP_SENTINEL ∪ UNIVERSAL_SENTINEL のバイパス追加。Live/FORCE_DEMOTED は従来通り
- 教訓: **Shadow経路のフィルターは「学習汚染リスク vs データ蓄積価値」で判断。is_shadow=1強制戦略はバイパスがデフォルト**

### [[lesson-sentinel-n-measurement-bug]]
**発見日**: 2026-04-20 | **修正**: v9.x (task/priority3-sentinel-n-measurement)
- 問題: UI で 62 戦略中 bb_squeeze_breakout のみ N=1 表示、他 61 戦略 N=0 (実態 shadow 1,466件)
- 原因: `_build_strategy_status_map` が `get_trades_for_learning` (is_shadow=0 固定) を使用 → Sentinel 統計が構造的に常にゼロ
- 修正: `get_shadow_trades_for_evaluation()` 新関数 (is_shadow=1 固定) + `/api/sentinel/stats` 新設
- 教訓: **is_shadow=0 フィルタは Kelly 学習用、Sentinel 監視用には別関数が必要。「見えない指標はゼロ」と誤認しないよう UI 側のソースを常に検証**
