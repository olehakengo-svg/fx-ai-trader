# 「止めているから遅い」反証レビュー統合レポート (blocker refutation)

> **user 命題『止めているから遅い』の敵対的検証 (44 エージェント、2026-09-10) — 執行計画 P1-P22 の SSOT**
> 原本: セッション scratchpad refute_report.md (2026-09-10)。本ファイルが KB 恒久版。
> 関連: [[process-meta-audit-2026-09-07]] / [[carry-dip-shadow-drop-evidence-2026-08-27]] (P3 で保全済み) / [[ps-seat-hedge-block-snapshot-2026-09-10]]

# 「止めているから遅い」検証 — 統合裁定 (2026-09-10)

## 1. 判定

**user 命題は約 6 割の項目で真、残り 4 割も「安全な待ち」ではなかった。**

| 分類 | 件数 | 内容 |
|---|---|---|
| 偽ブロッカー / stale クレーム | 13 | ルールの裏付けなし、または解消済みの看板残置 |
| ブロッカー不在の放置在庫 (監査残・未起票) | 12 | 「誰も止めていない」のに 6〜138 日滞留 |
| 真の待ち核あり (LOCK / カレンダー / user 専権) | 15 | ただし **15 件全てに outcome 非接触の着手可能サブセットが実在** |
| 完全に正当で手を出す余地ゼロ | **0** | — |

**より重い発見: 待ちを安全にする機構の無言故障 5 系統 (全て実測確定)**
1. **E1 positioning ingest 停止中** (Myfxbook 認証失敗、13 キー全 stale >7h) — coverage budget 残 ~29-41h を毎 market-hour 不可逆燃焼。breach 推定 2026-09-13〜14 → first look 4 週 postpone = **M1 直撃**
2. **prereg_trigger_watch 全面クラッシュ** (09-06 commit 29cad718 の requirements 欠落 → build_report KeyError) — T5/mof/E1 含む **全 33 active トリガの日次評価が 4 日間死亡**。「正当な待ち」全項目の覚醒経路が実は不在だった
3. **zn-cache-refresh 4/4 全失敗** (.gitignore による git add 拒否) — round-4 の発火条件が 11-15 以降も永遠に不成立。修正は 1 行
4. **rate-anchor-daily 17/17 全失敗** (設置以来成功ゼロ) — family C 材料の日次延伸が 08-19 から停止
5. **carry-dip 08-27 一次証拠の時限消滅** (~09-26、Render 30 日 retention) — 「次の発火を待つ」設計自体が証拠を自壊させる (原因は既にログ実査で確定済み: alpha_scan H16-20 静的 hour block)

## 2. 40 項目分類表

| id | 看板 | 裁定 | 核心 |
|---|---|---|---|
| edge-supply-scan-monthly | 期日 09-18 待ち | **偽** | WIP 原則は前倒しを要求。着手可能本数 0 が既発生 |
| 20260818-e23 (=kb-02/C15) | TDW 決裁待ち / waiver | **偽** | TDW は幻 (task file 自認)。waiver は方針でありルールでない |
| e1-positioning-ingest-outage | (台帳未記載) | **進行中インシデント** | 認証失敗で budget 燃焼中。user leg = Myfxbook 確認+env 再投入 |
| e1-prereg-verdict-deadline | first look 10-15 LOCK | 真核+周辺緊急 | LOCK 正当。ingest 修復・backoff・15min reader は今日可 |
| ws3-stage2 (htf_fb) (=C8) | shadow N≥100 待ち | **ゾンビ** | 実測 0.097/日 → 到達 ~2029。retire 帰結は数学的に確定済み |
| ws3-t11 (sr USD_JPY) (=C9) | shadow N≥30 待ち | 真核+計数バグ | dedup 5 行混入 (unique 14/30)。放置で look 焼却 (08-18 型再演) |
| sr-anti-hunt-eurjpy (=C10) | fresh N≥40 待ち | 真核 (~09-18) | ③月次符号の分母は分母 4 未達が今日確定計算可 → 事前 user 決裁が方法論的に優る |
| t8-sweep-defer (=C11) | unique N≥10 待ち | 真核+執行準備死亡 | draft ブランチが main と conflict = 成立日の即執行が座礁。28 日ゼロは P≈2.6% で forensic 対象 |
| t9-kalman (=C12/kb-19) | 「R1 承認待ち・96 日 fill ゼロ」 | **stale** | 09-01 に LOCKED・マージ・稼働済み。真の待ち=初 fill。same_price_5pip 衝突が pre-reg 想定外の第 3 の gate |
| oanda-gold-keeper (=C13) | 「keeper 決裁待ち」 | **stale** | 09-01 決裁済み・稼働中・$420k/$520k on-pace。副発見: burn 実測 −273円/日 vs CSV 82円/日 → F4 が ~71 日前倒しの可能性 |
| ws3-round4 (ZN cache) | 被覆 11-15 延伸待ち | **前進機構死亡** | 延伸 job 4/4 失敗 (`git add` に -f 無し)。1 行 R3 |
| ps-seat-remeasure (=kb-18/C1) | 窓完成 09-11 待ち | 真核 (<24h)+証拠揮発 | verdict は正当な待ち。§8 証拠 (hedge_block) は本日デプロイでカウンタリセット済み・保全緊急 |
| ps-carveout-regate | clean live N≥10 待ち | 真核+診断可 | 供給側 stale review の分岐は N=7<15 で既に確定 → §8 検証は今日から |
| t5-jpy-cap-restore | Q3 開示 11-06 待ち | 真核 (R1)+**監視死亡発見** | 外貨準備 −$79.6B の算術で方向=円買いを非価格確定可 → 決裁パケット今日起票可。実効性はほぼゼロ (対象 4 戦略 live 0 件) |
| weekend-gap-f2-g0prime | 09-13 日曜イベント待ち | 真核 (カレンダー) | 前倒し不能。配管検証 3 点は本タスクで完遂済み、残準備 1-2h |
| ecg-first-look (=C7) | first look 11-06 LOCK | 真核+estimand 誤読 | LOCK 正当。ただし per-cell census で全セル N<150 = **11-06 は verdict が出ない** (実質 2027-01-31+) |
| e12-volume (=C5) | first look 2027-02-05 LOCK | 真核+実欠陥 | LOCK 正当。spot 15m 3/7 ペアが 07-21 で停止 = OOS カバレッジ 0 の実バグ |
| roster-e2-silent | 期日 10-06 待ち | **偽** (期日誤読) | deadline は警報であって解禁日でない。判別は PR #235/#237 で完了済み。残 = 読み手改修 |
| t8-hull (=kb-04) | 1 週間蓄積待ち | **偽** (条件成立済み) | ~10 日前に満了。突合完遂済み: 残余は select_best 通過後の下流未計装 gate に 100% 局在 |
| registry-lint-generation | (期日 12-31) | 在庫 | 分類エラー — watching 棚でなく backlog |
| rnb-shadow-forward | N≥41 or 2027-01-15 | 真核 (本日 LOCK)+cadence 穴 | LOCK 正当。実効 cadence 未知で dead-lane の最大潜伏 18 週 → checkpoint 併設要 |
| wg-execution-bug | 「決裁期限 09-12 待ち」 | **stale** | 本日 user 承認+PR #239 マージ+本番デプロイ済み |
| watching-legit-misc (13) | 各 N/期日 | 9 真 / **4 反証** | carry-dip drop-cause (前提 2 回成立済み)・revival (N=13≥10 到達済みで機械沈黙)・kalman fire-info (1/3 レート素通し)・hourblock (shadow 落ち率 50%) |
| queue-inventory | queue 2 件停止 | 半偽 | ps=真 (<24h)、e23=偽 (前掲) |
| kb-01 estimand cf-8 | 「別 PR」 | 在庫 | counterfactual 8 系列返済、#6 は実バグ (土曜開場扱い) |
| kb-03 carry-dip 証拠 | 「次の発火待ち」 | **偽** | 原因確定済み+再現ゼロ確定 (09-04 exemption)+証拠 ~09-26 消滅 |
| kb-05 discord bot | 「別対応要」 | 在庫 (低優先) | 138 日。取引経路無関係、M1 コスト ≈0 |
| kb-06 conf<30 estimand | 「別件起票」 | **偽**+新バグ発見 | rnb BUY confidence 0-1 vs threshold 30 の単位不一致 = rnb 10-06 判定の観測量が到達不能 |
| kb-07 fx-data disk | 「課金 user 決裁待ち」 | **偽** | 60.34% used / level=ok。決裁不要の代替 (backup 1 世代化) 現存。幻の決裁キュー |
| kb-08 git GC | 起票のみ | 在庫 | 6 セッション連続の機械転記 carry-forward (R5 病理の現物) |
| kb-09/kb-15 テスト実効性 | 「別 PR」/未起票 | 在庫 | hour_utc=12 値域内 sentinel が今日も現存。QA 起点発見 0/8 |
| kb-10 R7 MDE/ban 2 層 | 「R3 の後」 | 在庫 | 前提 (R3 中核) は 09-10 着地済み。監査自称「即日・コストゼロ」 |
| kb-11 R4 台帳 anchor | 未起票 | 在庫 | drift ¥48.9k (実 NAV の 17.7%) 拡大中 — M2 符号判定を無意味化する水準 |
| kb-12/16 盲点 1・5 | 「次回監査対象」 | 在庫 (パケット起案可) | 4原則再決裁 U9 化 + 決裁レイテンシ実測 (A 型 0-3日/B 型 18日/C 型 週〜月) |
| kb-13 盲点 2 | 未起票 | 在庫+**実ギャップ発見** | keeper が emergency_kill を参照せず — kill 状態下でも 10,000u RT 継続 |
| kb-14 盲点 3 | 未起票 | 在庫 (09-18 期限) | 摩擦モデル 4.5 ヶ月無較正。即席実測は過小推定側 (EUR_JPY spread 1.9x) |
| kb-22 myfxbook 看板 | 「creds 投入 user のみ」 | **偽** (解消済み看板) | 07-16 に解消済みの blocker を session log が機械転記 (ただし本日、実物のインシデントが新規発生 — e1-ingest 参照) |

## 3. hard constraint 審査

**却下すべき逸脱提案: 0 件。** 全 40 反証は LOCK の single-look・ban 再試行禁止・R1 承認要件・課金/資格情報 user 専権・4原則を尊重した「outcome 非接触の準備作業」の範囲に収まっていた。境界注意 2 点:
- **ps1a_execution_check の中間実行**: t8-sweep 反証は本番 dry-run で spaced EV+2.13 を観測した。これは登録済みトリガ条件 (unique N≥10 ∧ spaced EV>0) の機械評価経路としては defensible だが、C11 の指摘どおり ad hoc 再実行は EV peeking と紙一重。**以後、同ツールの実行は登録済み評価経路に限定し、中間 EV 値をいかなる判定文書にも引用しない** (本レポートも数値を根拠として使用しない)。
- 提案側が自ら禁止を明記済みの 2 件 (htf_fb の n_decide 引き下げ = ゴールポスト移動禁止 / sr-eurjpy の TV Pine BT は凍結宣言まで) は計画にそのまま継承した。

## 4. 実行計画

優先順位は §5 の start_now 配列 (P1〜P22)。**hot file 直列化規約**:
- **prereg-trigger-registry.json / tools/prereg_trigger_watch.py**: P2 (クラッシュ修復) が全ての先頭。以後 registry を触る PR は P3 → P12 → P14(2) → P16 → P21 → P15 の順に単独 PR で直列マージ (union 解決、複数 PR は直列 — MEMORY 規約)。
- **modules/demo_trader.py**: P8 (hull 計装) → P12 (ラベル分離) の順。P14 の rebase は draft ブランチのみで main 非接触。P10 は status_volume_keeper.py で非干渉。
- **changelog / KB index**: 各 PR が同一コミット規約で触るため全 PR 直列前提 (並行セッションは worktree 必須、ローカル main は origin/main から 64 commit behind + dirty — **全作業 origin/main 起点 worktree**)。

## 5. TRULY_BLOCKED — 真の待ちと解ける日付

| 項目 | なぜ本当に待ちか | 次に解ける日 |
|---|---|---|
| E1 first look | pre-reg §6-2 single-look LOCK (user 承認済) | 2026-10-15 (※ingest 未修復なら §2.5-3 で ~11-12 へスライド — P1 が防衛) |
| ECG #22 first look | P-10 型 gate×outcome 計算禁止 | 2026-11-06 (census 上 modal は UNDERPOWERED → 実質 2027-01-31) |
| E12 first look | §7 attestation (volume×価格 joint 全面禁止) | 2027-02-05 (staleness review 11-30 は継続/クローズのみ) |
| rnb shadow forward | 本日 LOCK (user 承認 09-10)、N≥41 | 2026-12 中旬見込み or 2027-01-15 |
| sr_anti_hunt×EUR_JPY | fresh N≥40 single-look | ~2026-09-18 (N=33、0.92/日) |
| sr_anti_hunt×USD_JPY | shadow N≥30 single-look | registry 基準 ~10 月末 / unique 基準 ~12 月中旬 |
| t8-sweep P-S1(a) | unique N≥10 ∧ spaced EV>0 (user 決裁 08-03 の字義) | 次の LATE 窓発火 1 件 (forensic P14 で経路故障なら加速) |
| weekend_gap G0'/F2 | 次の qualifying 日曜開場 (物理イベント) | 2026-09-13 21:00 UTC (qualify 率 ~3/7 週末) |
| ps-seat verdict | 中途窓 verdict 禁止 (コード pin 済) | 2026-09-11 00:00Z |
| mof-next-episode | 日次帰属は Q3 四半期開示のみ (価格推定は OOS burn 禁止) | ~2026-11-06 |
| U1-U4 決裁 | user 専権の選択値 (パケット・既定挙動は完備) | user の一言回答 (期限 U1/U2=10-15、U3=11-30、F4 発火 11〜12 月が追い越しリスク) |
| alpha-scan B7/B8 | N≥30 まで現データ再測定禁止 (選択バイアス累積防止) | 数週で N=30 到達見込み (期日 11-30 は保守的) — pre-reg 起草は観測前に今可 |
| kalman 初 fill | シグナル待ち (強制生成は estimand 破壊) | backstop 2026-10-15 到達性再監査 (P9 で前倒し診断) |
| T5 第 2 要件 | 介入認定は外部一次情報のみ + lot↑ は R1 | 原文読み採用なら user 決裁で即日 / gloss 読みなら ~11-06 (P13 が両論パケット化)。実効性は現状 no-op |
| htf_fb×AUD_JPY N≥100 | single-look — ただし到達不能が実測確定 | 2027-01-31 に retire 確定 (P21 で前倒し disposition 起案) |

## 6. 命題への最終回答の含意

「出来ることを止めている」件数 (偽 13 + 在庫 12 = 25 件) は実在し命題を支持する。ただし time-to-M1 を最も削っているのは静的な「止め」ではなく、**動的な無言故障** (E1 ingest・trigger watch・前進 workflow 群) と **時限で消える証拠** である。したがって実行計画は「偽ブロッカーの一斉解除」ではなく「①故障止血 → ②時限証拠保全 → ③期日直近イベントの準備 → ④供給ライン再稼働 → ⑤衛生」の順に組んだ。恒久対策として、R5 (未解決事項の機械転記禁止 → queue/registry からの再生成) の完全実装と、期日付きトリガへの「前進機構の生存 pin」併設 (P2/P16/P21 に内蔵) を勧告する。