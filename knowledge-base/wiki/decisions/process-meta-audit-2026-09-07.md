> **種別**: プロセス/仕組みのメタ監査 (rule:R3 — 診断のみ、live 変更なし)
> **発注**: user 2026-09-07「そもそも進め方、および Codex 利用なども含めて仕組みとして最適なのか。大規模監査を改めて行って欲しい。数ヶ月やってるけど成功まで時間かかりすぎ」
> **実施**: Claude (session cd1f73fd) — 37 エージェント並列監査 workflow (7 次元 audit → major 以上 finding の敵対的 verify → 統合)。全 findings は一次ソース (KB / git / 本番 API read-only GET) で再現検証済み。REFUTED sub-claim は本文根拠から排除 (§7)。
> **user 決裁待ち**: §5 U1〜U8。本文書の提言は user 承認まで執行しない (R1 相当の方針転換を含むため)。

# プロセス大規模メタ監査 2026-09-07 — 進め方・Codex 分業・仕組み全体は最適か

- **監査日**: 2026-09-07 / **対象期間**: 2026-03-21 (first commit) 〜 2026-09-07 (~5.5 ヶ月)
- **発注主旨**: 「数ヶ月やっているが成功まで時間がかかりすぎ。今までの延長で考えず、進め方・Codex 利用も含めて仕組みとして最適なのか」— 監査対象は戦略ではなく**プロセス/仕組み**
- **方法**: 7 次元 (ファネル/統計規律/Codex/欠陥税/目標構造/アーキテクチャ/到達可能性) の独立監査 → 全 findings を一次ソース (KB・git・本番 API 実測) で敵対的に再検証 → 本統合。verdict=REFUTED の主張は本文根拠に不使用、PARTIAL は訂正版 (corrected) のみ使用、未検証 (verify pass 未実施) は明記。

---

## 1. 総括 verdict — 「仕組みは最適か」

**部分 (是 2 / 非 4)。**

**是である部分 (毀損してはならない資産):**
- 検証規律 (pre-reg / Bonferroni / 観測前 LOCK / 敵対的検証) は本物。healthy-kill:false-claim 比は Era-1 の 0:10 → Era-3/4 の 30:0、観測前 LOCK 体制以降 false positive の live 到達 = 0 (edge-dev-postmortem-2026-07-24.md、未検証だが postmortem は 13-agent 検証済み文書)。round-3 top-8 の OOS 全反転や T11 の Bonferroni PASS 覆滅は「統計を緩めていれば偽陽性を live に流しただけ」の直接証拠 (rigor-1 PARTIAL 訂正版) ✅
- 検証**キャパ**は律速ではない。in-repo 系は凍結→two-pass→verdict が同日完了 ×10 本、バースト期 (07-22〜08-19 の 28 日) に decisive verdict 23 本、前倒し verdict 4 件、全件 OOS 非接触・凍結遵守 (funnel-4 CONFIRMED) ✅

**非である部分 — 時間がかかっている根本原因の順位 (定量根拠付き):**

| # | 根本原因 | 定量根拠 | verdict |
|---|---|---|---|
| 1 | **探索空間の真の base rate ≈4%** — 無料 OHLCV×intraday×リテール摩擦にはほぼエッジが無い。仕組みの欠陥ではなく「どこを探すか」の戦略問題で、外部の独立同型反証 (Mesfin 2026, arXiv:2605.04004、14 family 全滅・実在確認済) と一致 | ~5.5 ヶ月で家族級 verdict 約 25 件 (補正後 26〜35)、OOS 確定 PASS 1 件のみ = 4.0% [Wilson 95% CI 0.7–19.5%]。探索→OOS 生存 0/15〜17 系統 | viability-1 CONFIRMED / viability-4 PARTIAL |
| 2 | **live 転換層の故障** — 唯一の OOS PASS (weekend_gap) が live 約定通算ゼロ (0/3 qualifying イベント: バグ・MARKET_HALTED・fill なし)、「PASS→live PnL」変換係数はプロジェクト開始以来**一度も測定されていない**。LIVE 発火は 124→3 セル/30d、M3 最短 ~14 ヶ月 (2027-11) | 本番 tx 549258 ORDER_CANCEL=MARKET_HALTED を一次確認、closed 全 17,176 行の独立集計で wg live=0 再現 | funnel-2 CONFIRMED |
| 3 | **欠陥税** — 直近 10 週の PR 195 本のうち欠陥税 (監視基盤修理 + estimand/write-only/配線欠陥) は約 55〜70 本で研究と同規模、08-21 以降は 28 本中 ~21 本 (75%)・研究 1 本のみ。主要 8 インシデントの潜伏は平均 ~111 日/中央値 ~124 日、**発見の QA 起点は 0/8** (全て事故・手動監査・🔴 の人手追跡) | defect-tax-1/2 PARTIAL 訂正版。テスト 2,997 本は「現状」を pin し「estimand」を pin しない (rnb ではバグを設計として pin) | PARTIAL×2 (訂正済) |
| 4 | **読ませる仕組みの崩壊 + enforcement 不在** — 毎プロンプト ~17.6KB の同一再注入 (差分ロジック未実装)・MEMORY.md 1.71 倍超過で最新 9 エントリ (OANDA 口座存続条件含む) が毎セッション無言欠落・SessionStart 注入は 5 ヶ月前の v2.1/demote 済み戦略を「必ず確認」ラベルで供給。改訂 WIP 原則「今日着手可能 ≥1」は明文化済みなのに 08-19 の枯渇後 19 日間不発動、E23 は幻ブロッカーで 17 日滞留 | arch-1/2/3 CONFIRMED、funnel-3 CONFIRMED、rigor-4 PARTIAL 訂正版 | CONFIRMED 多数 |
| 5 | **目標・資本前提の未接続** — ミッション 20%/月と M3 (+2〜3%) の 6.7〜10 倍乖離は 2 回決裁済みだが、橋渡し前提 (セル在庫「年内 2-3 本」) が崩れた後の再決裁が未起票 (~1 ヶ月)。M3 完全達成でも現 NAV では月 6,500〜9,700 円で、資本スケール上限は KB のどこにも凍結されていない。NAV floor 到達 (2027-02〜04 中心推定) が M3 ETA (2027-11) より早いのに枯渇予測日はどの KPI にも無い | goals-1/2 PARTIAL 訂正版、viability-6 (未検証) | PARTIAL (訂正済) |
| 6 | **Codex 分業の死亡 + レビューの write-only 化** — owner=codex の最終 done は 2026-07-06 (以後 2 ヶ月ゼロ)。ただし「独立レビュー不在」は誤りで、GitHub Codex connector が PR #75 以降ほぼ全 PR を実質レビュー (P1/P2 付き) している — 真の欠陥は**読まれずにマージされる**こと (レビュー→マージ間隔 56 秒〜2 分が常態、P1 指摘が無対応マージ) | codex-1/2/7 PARTIAL 訂正版 | PARTIAL (訂正済) |

**「時間かかりすぎでは？」への直接回答**: かかった時間は 2 種類に分解される。(a) **存在しないエッジを正しく棄却する時間** — これは正当かつ不可避で、外部文献とも整合し、緩めていれば実弾の損失に化けていた。(b) **欠陥税・live 層故障・enforcement 不在の待ち時間** — こちらは仕組みの欠陥であり短縮可能。監査の結論は「(a) を責めず (b) を構造遮断し、(a) の探索空間自体を user 決裁で変える」である。

---

## 2. 定量サマリ — 5.5 ヶ月の実績

| 指標 | 値 | 出典 |
|---|---|---|
| 仮説 family 総処理 | ≈76〜79 (4-7 月 ≈60 + 外部仮説期 19、部分重複あり) | edge-dev-postmortem §1 + hypothesis-catalog 台帳 (funnel-1 CONFIRMED) |
| 家族級終端 verdict | ~25 件 (補正分母 26〜35) | viability-1 CONFIRMED |
| OOS/forward 確定 PASS | **1** (weekend_gap arm B、stressed-net +9.04p/event) = base rate 4.0% | 台帳 #3 (CONFIRMED) |
| live 収益化セル (清浄 N≥30 正EV) | **0** | roadmap-v2.3 M3 行 (CONFIRMED) |
| PASS セルの live 約定 | **0** (live 化後 6 週、0/3 イベント) — 変換係数は測定不能 (0/1) | funnel-2 CONFIRMED |
| LIVE 発火セル/30d | 124 (2026-05) → **3** (2026-09)。88.7% は帰属済 = 主に意図的止血 (停止 83 セル = N609/−469.8p) | PR #226 帰属分析 |
| M3 到達 ETA | 最短 **~14 ヶ月** (2027-11)。return 版 M3 は 2027 年内径路確認できず | m1-kpi-readout §6 (goals-4 PARTIAL 訂正版) |
| 実口座 | ¥454,816 (04-12) → **¥276,304** (09-07 実測) = **−39.3%**。4〜7 月 ≈−13%/月 → 7 月以降 ≈−0.47%/月 (keeper コスト支配) | 本番 heartbeat 実測 (goals-5、未検証) |
| NAV floor (¥262,000) 到達 | 中心推定 **2027-02〜04** — 到達で OANDA API 停止 = 目標系は事実上全停止。M3 ETA より早い | goals-1 PARTIAL 訂正版 |
| commit 総数 / 構成 | ~4,500。07-01 以降 1,714: docs 833 / auto 336 / **fix 74 > feat 49** / docs+auto=68% | git log 実測 |
| PR 欠陥税 | 195 PR 中 ~55〜70 本 (研究 ~58〜66 と同規模)。08-21 以降 75% (28 本中 21)、研究は 1 本 | defect-tax-1 PARTIAL 訂正版 |
| 欠陥潜伏 | 平均 ~111 日 / 中央値 ~124 日 (8 件: 109/123/153/126/134/144/60/36)。**QA 起点発見 0/8** | defect-tax-2 PARTIAL 訂正版 |
| Codex 実行 | done 291 件の月別 264/14/11/2/0、owner=codex 最終 done **2026-07-06**。Render worker は稼働中 (3.4 ヶ月 pickup ゼロで Pro 課金継続) | codex-2 PARTIAL 訂正版 |
| 能動測定ライン | **0 本** (08-19 以降 19 日、確定空白は 09-18 scan#4 まで ~30 日)。残は全て時限 (E1 10-15 / ECG 11-06 / E12 2027-02-05) | funnel-3 CONFIRMED |
| 検証キャパ | バースト期 23 verdict/28 日、同日 two-pass ×10 — **律速ではない** | funnel-4 CONFIRMED |

---

## 3. 次元別所見 (CONFIRMED / PARTIAL 訂正版)

### 3.1 エッジ発見ファネル
- ✅ **CONFIRMED**: 約 79 family → OOS 確定 PASS 1 → live 収益化 0。主因は処理能力でなく探索空間のエッジ密度 (edge < リテール摩擦 + 認定閾値)。postmortem 後の独立測定 5 本も全滅で forward 補強済み (funnel-1)
- ✅ **CONFIRMED**: 終端故障 — weekend_gap live N=0 (0/3、うち 09-06 の第 3 イベントも fill なし = 原 claim より悪化)、kalman_d7 も通算ゼロ。ただし停止 83 セル (−469.8p) は復帰対象外 — 止血は正しかった。回収対象は「正/中立で非発火」のセルに限る (funnel-2)
- ✅ **CONFIRMED**: 供給枯渇 + WIP 原則不履行。E23 の「TDW ライセンス user 決裁待ち」は幻のブロッカー (primary の Apel-Grimaldi 辞書は決裁不要) で 17 日滞留、訂正 commit 後も session log が 3 日間誤 blocker を機械転記し続けた (funnel-3 + codex-3)
- ✅ **CONFIRMED**: 検証キャパ余剰 — 検証ハーネス・統計プロトコルの追加強化提案は却下してよい (funnel-4)
- ⚠️ 未検証 (計算モデル): 次の live-viable 正セルまで Jeffreys 事後で期待 ~53 family ≈ 供給 1-2 本/月では 2 年超 (funnel-5、confidence medium)。時限 3 系統の結合 first-look 通過確率 ≈11〜39% (モデル依存)
- ⚠️ 未検証 (minor): phase1b 日次 BT は 76/77 回 verdict=NULL で停止則なし (funnel-6)

### 3.2 統計規律 (rigor) — 全 4 findings PARTIAL、訂正版のみ採用
- **FAIL の内訳は sign-flip + null ≈59% で「仮説クラス自体の死」が支配的** — 統計を緩めても発見は増えず偽陽性を流しただけ (round-3 top-8 OOS 全反転が直接証拠)。ただし「weak-FAIL の処分が誤り」は過大で、6 件中 4 件は既に registry に条件付き復活枠あり。回復可能な探索空間は約 2 割ではなく実質 **3〜7%** (rigor-1 訂正版)
- **検出閾値の逆転は成立**: E1 first look の 80% power 検出可能効果 (+4〜7 p/t) > 事業計画の必要効果 (+2.8〜3.3 p/t)。ただし「必ず UNDERPOWERED に落ちる」は過大 (modal であって必然でない)。より深刻な見落とし: 低端の真エッジは second look でも power ~50% 弱で 3 回目 look 禁止のため**恒久 REJECT に落ち得る** — 「設計された遅延」は下端では「設計された棄却リスク」(rigor-2 訂正版、severity critical 維持)
- **live N≥30 は確認でなくスクリーン** (power 29〜64% @+2p/t)。Bonferroni 実測 m は 2〜**1728** (原 claim の 2〜224 は過小)。ただし「真の律速 = N 供給」は KB 自身の帰属分析 (88.7% = 意図的止血) と未整合 — N 供給難は「正 EV セル不在」の帰結であり独立原因と確定していない。それでも per-cell 固定 N + Bonferroni という検定設計が現実の標本供給と両立しない構造問題は成立 (rigor-3 訂正版)
- **探索空白の原因は保守 AND スタックではない** (スタックは暦時間を消費しない)。真因は (i) 歴史完結型仮説の枯渇 (ii) forward 設計のデータ蓄積待ち (iii) **空白解消規則の enforcement 不在** — WIP 原則は明文化・実施例まであるのに再発動されず、「能動枠=0」を検知する registry トリガが 51 件中に存在しない (rigor-4 訂正版)。是正は保守条件の降格 (時間短縮効果ゼロ) ではなくトリガの機械化
- ⚠️ 未検証: ban 2 層化 + MDE 事前スクリーン (rigor-5)、live 出血の主因はゲートのバイパス経路 −469.8p (rigor-6)、R2 執行遅延 10〜35 日 (rigor-7)、階層プーリング等 4 代替案の優先順位 (rigor-8) — いずれも一次文書引用は具体的で方向性は有力だが verify pass 未実施

### 3.3 Codex 分業
- **PARTIAL 訂正版 (重要)**: CLAUDE.md「Codex プラグインによる自動レビュー」は帰属が stale (stop-gate は両ストア false・実行記録ゼロ) だが、「独立レビュー不在」ではない — **GitHub Codex cloud connector が PR #75 (07-10) 以降ほぼ全 PR を自動レビューし P1/P2 付き実質指摘を出している**。真の欠陥は読まれないこと: レビュー→マージ間隔 56 秒〜2 分が常態 (PR #213 はレビュー到着の 6 秒**前**にマージ)、PR #224 の P1 指摘は無対応のまま 7 時間後マージ、connector 指摘への対応 commit・MEMORY 言及は 06-12 以降ゼロ。**最小コスト解は stopReviewGate ON 化ではなく「マージ前に connector レビューを読む/待つゲート」**(codex-1 訂正版)
- **PARTIAL 訂正版**: Codex 実行チャネルは 07-06 に事実上死亡 (done 264→14→11→2→0)。Render worker fx-codex-runner は**実査で稼働中・Pro 課金継続を確認** (3.4 ヶ月 pickup ゼロ = 純コスト)。凍結タスクは 66 件 (68 は誤記)。ただし **.ai/tasks 台帳自体は殺さない** — Claude セッションの排他 claim・SLA fallback・review-gate として現役 (codex-2/7 訂正版)
- ✅ **CONFIRMED**: SLA 機構は牙なし — e23 は SLA 3 日に対し 20 日滞留、check.py は WARN のみで exit 0。誤 blocker が carry-forward 機械転記で訂正後 3 日間も再生産 (codex-3)
- 独立レビューの概念自体には実証価値: T11 (Codex PASS を Claude 敵対検証が 3 独立欠陥で REJECT)、06-12 (Codex review が Critical 3 + Important 4 捕捉) — 再武装対象 (codex-7 訂正版)
- ⚠️ 未検証 (minor): failed 33 件は 100% コンテナ再起動 orphan = インフラ起因 (codex-4)、queue→done レイテンシ劣化 2.0h→97.3h (codex-5)、自動化スタック棚卸し (codex-6)

### 3.4 欠陥税 — 全 4 主要 findings PARTIAL、訂正版採用
- 欠陥税は PR 産出の研究と同規模 (~55-70/195)、08-21 以降 75% で人手の研究コミットは実質ゼロ (defect-tax-1 訂正版)
- 潜伏 8 件 = {109,123,153,126,134,144,60,36} 日、平均 ~111/中央値 ~124、live 経路系 6 件平均 ~131 日、**QA 起点 0/8** — rnb では既存テストがバグを「意図された設計」として pin していた (0/8 より悪い) (defect-tax-2 訂正版)
- **BT⇄live 二重実装クラスは実在し修正後も再発** (08-24 bar_time NULL、09-05 rnb 153 日)。SignalContext 構築は app.py 内 3 箇所に分散、`hour_utc: int = 12` の値域内 sentinel default は**今日も現存**。ただし「M1 分母を 3.5 ヶ月殺した」は 1 family への過大一般化で、現在の 3 セル律速の支配要因は意図的止血 — 単一ファクトリ化は有効だが単独で time-to-M1 を縮める保証はない (defect-tax-3 訂正版)
- 教訓の構造変換率 ~23% (82 件中 19)、同型再発 3〜4 回 (call-site 欠落 4 例 + 5 例目予防 pin / counterfactual 素通り 3・4 例目 / ZN 型 4 例目)。2026-08 以降は構造 pin 同時添付が事実上標準化しつつあるが制度化されていない (defect-tax-4 訂正版)
- ⚠️ 未検証: guard 自身の無検証 3 例 (defect-tax-5)、estimand 宣言表の不在 (defect-tax-6)、並行セッション座礁回収 PR 5 本超 + worktree 78/stash 180 (defect-tax-7)

### 3.5 目標構造 — 全 4 主要 findings PARTIAL、訂正版採用
- **資金枯渇時計**: keeper コストは月 ~¥2,080 (自動停止ガード込み、「¥5-7k/月」は誤り)。エッジドリフト併算で floor 到達 **2027-02〜04** — M3 ETA 2027-11 より早い。枯渇「予測日」はどの KPI にも無く、SVK は demo DB 非書込みのため risk dashboard から原理的に不可視。M2 の必要エッジは keeper 込みで実質 +1.25%/月へ 2.5 倍化しているが再導出されていない (goals-1 訂正版)
- **ミッション乖離 (6.7〜10 倍) は「13 ヶ月未決裁」ではない** (プロジェクト齢 5.6 ヶ月で数値的に不可能・2 回決裁済み)。真の欠陥は 08-05 橋渡し前提 (セル在庫「年内 2-3 本」) が全探索ライン FAIL で崩れた後の**再決裁が ~1 ヶ月未起票**であること。「20% が探索過剰を正当化」という機構は文書上不支持 (探索は M3 自体の必要条件)。severity は critical→medium (goals-2 訂正版)
- **M1 は縮退 KPI**: 機械的符号反転 (新規約定ゼロ・P(sum≤0)=0.426) + 分母縮小で満たしやすく、60 日読み手不在。承認済み強定義 (セル単位 live N≥30 正EV≥1 ∧ Wilson 下限>0) が 59 日未実装で、09-04 の起票は承認済み定義を**参照すらしていない** — 根因は承認文書間の M1 定義不整合 (goals-3 訂正版)。なお 09-07 実測では NOT_MET (−22.4p) へ再反転済み
- **M3 は 2 定義併存** (throughput 版 vs return 版)。基本 ETA 2027-11、rnb 楽観で 2027-03〜04。return 版は正EVセル実質 0〜1 (carry_dip +84.0p N=9、DSR not significant) で 2027 年内径路確認できず (goals-4 訂正版)
- ⚠️ 未検証: 実口座 −39.3% と累積基準の二重化 ¥95,707 差 (goals-5)、index.md 冒頭の廃止数値 + 台帳ドリフト ¥48k (goals-6)、目標設定プロセスの歴史的欠陥 — 根拠が 24h で崩れた目標が 2 ヶ月存続 ×2 回 (goals-7)

### 3.6 セッション/KB アーキテクチャ
- ✅ **CONFIRMED**: 毎プロンプト ~17.6KB 全量再注入 (ヘッダに「差分検出」と書きながら差分ロジック未実装)。SessionStart の 94.8% と重複、40 プロンプトで ~700KB。注入される 4 原則短縮形は 2026-05-28 の原則 3 改訂を落とした旧形 = 矛盾ドクトリンを毎プロンプト再注入 (arch-1)
- ✅ **CONFIRMED**: MEMORY.md 41,764B / 上限の 1.71 倍 — 最新 9 エントリ (**OANDA JP API 存続条件 = Gold $500k/月 + 残高 25 万**を含む) が毎セッション無言欠落、この致命制約は他のどの自動注入経路にも乗らない。先頭/末尾両追記で時系列も破壊 (arch-2)
- ✅ **CONFIRMED**: SessionStart QUICK_REF が roadmap-**v2.1** (現行 v2.3)・04-14 BT TOP5 (demote 済み trendline_sweep×GBP_USD 含む) を「判断前に必ず確認」ラベルで注入 (arch-3)
- **PARTIAL 訂正版**: session log 122 本中 85 本 (70%) placeholder 残置 (純スタブ 76 本=62%)、lesson 28/82 (34%) が hook 注入経路外、**注入見出しの 81% が 2026-04 産** (原 claim の 55% より深刻) — 直近の教訓ほど注入されない逆転構造。audit-index.md は最終 commit 07-03・実 session log からの参照 0 件で「必ず」条項は空文化。※「直近 16 log 中 KB 引用 5 本のみ」は誤り (実測 10/16) (arch-4 訂正版)
- ⚠️ 未検証: 並行セッション事故 ~週 1 件 + 直列化しても time-to-M 損失ほぼゼロ (arch-5、medium)、pre-commit 全 2,997 テスト税→background commit 回避策→cwd 罠事故の連鎖 (arch-6)、CLAUDE.md「92 tests」(実 2,997) (arch-7)、registry resolved 15 件同居 (arch-8)

### 3.7 到達可能性
- ✅ **CONFIRMED**: base rate 4.0% [0.7–19.5%]、live 変換 0/0 測定不能、能動ライン 0 本・残は全て calendar-lock。「もう 1 周スキャンすれば見つかる」型の期待は数字が禁止する (viability-1)
- **PARTIAL 訂正版**: time-to-M2 中央シナリオ **2027-Q4〜2028** (P(M2≤2027 末)≈15–25%)、M3 は楽観 2028・中央 2029+。訂正はいずれも悲観方向: ladder の Wilson gate N=41 到達は ~4.5〜20 ヶ月/セル、**wg 級 1 本では M2 に届かない** (disaster SL 150p binding で実効上限 L1=5000u → +0.46%/月 < 0.5%、かつ M2 定義自体が 2 セル要求) — M2 には第 2 セルの PASS→live 変換が必須 (viability-2 訂正版)
- **PARTIAL 訂正版**: weekend_gap の追跡欠落は誤り (4/5 週末は registry/session で追跡済み・qualifying ゼロで R1 起案条件不成立)。実欠陥は戦略カード SSOT 崩れ + gap 診断ログの KB 非永続 + **qualifying 供給枯渇と fill 不能の二重で live 変換検証が凍結**していること。severity は major→minor〜medium (viability-3 訂正版)
- **PARTIAL 訂正版**: 全滅 (wg 1 例を除く) は「探し方が悪い」でなく「そこに無い」を文献 3 系統が支持 — 手法への追加投資は不要、動かせるのは「どこを探すか」のみ (viability-4 訂正版)
- ⚠️ 未検証: 4 経路の機会費用比較 (viability-5)、目標金額とシステム規模のミスマッチ — M3 完全達成でも月 6,500〜9,700 円 (viability-6)、falsification 条件の提案 (viability-7、§6 に採用)

---

## 4. 構造再設計の提言 (優先順位付き)

### 4.1 やめること (足す前に引く — 即時、ほぼ全て Claude 自走可)

| やめる対象 | 根拠 | 回収 |
|---|---|---|
| **同型無料データスキャンの増産期待** — 09-18 scan#4 は実施するが、「もう 1 周で見つかる」を評価軸から排除し、p_pass=4% × 期待工数で期待値を先に計算してから承認 | base rate 4% (CONFIRMED)、C1 空間ほぼ枚挙済み | 空振り工数の恒久削減 |
| **検証プロトコルの更なる強化** (敵対的検証の追加段・スキャン頻度増) | postmortem §6「もう十分強い」+ funnel-4 CONFIRMED | 検証キャパを live 層修復へ転用 |
| **Codex 実行チャネル** — fx-run-codex-cloud skill、Render worker fx-codex-runner (suspend)、_paused 66 件 (archive)。※ .ai/tasks 台帳と check.py governance・on-demand rescue は**残す** | 2 ヶ月稼働ゼロ・worker は 3.4 ヶ月 pickup ゼロで課金継続 (codex-2 訂正版) | 課金停止 + 幽霊 SLA 儀式・誤 blocker 温床の除去 |
| **UserPromptSubmit の KB 全量再注入** — 差分 (新規 🔴/新規 lesson/registry 期日) のみに書換え、旧 4 原則短縮形は現行 CLAUDE.md から機械生成 | arch-1 CONFIRMED | 毎プロンプト ~6K トークン + 矛盾ドクトリン根絶 |
| **phase1b 日次 BT の無停止則反復** — 「survivors=0 が N 回連続で週次降格/非ゼロで日次復帰」を追加 | 76/77 回 NULL (未検証だが git 実測) | コミットノイズ削減 |
| **pre-commit での全 2,997 テスト無条件実行** — 差分が knowledge-base/ と *.md のみなら pytest スキップ (CI が全 suite を担保) | arch-6 (未検証、ただし 10 分超と cwd 罠事故は MEMORY 記録済み) | コミット税 ~10 分/回 + background commit 回避策の廃止 |
| **月利換算 (20%/21.6% anchor) での施策正当化** — スコアリング分母を「time-to-M2 短縮」に統一 (07-10 D5 の執行) | goals-8 (未検証、minor) | 優先順位の分母統一 |

### 4.2 直すこと (time-to-M1/M2/M3 寄与順)

**R1: live 層の「無料の N 源」回収** — 新エッジ発見を要さない唯一の M1/M3 短縮策
- 何を: (a) rnb_support_bounce 登録 R1 パケット (153 日未登録、推定 3.0/週 = 現最速セル超、registry 期日 10-06) の前倒し起案、(b) weekend_gap 執行契約 R1 改定パケット (halt 解除後エントリー繰下げ/限定 retry + fill 成立率の事前見積り) を次イベント前に、(c) E2_SILENT 4 セルの「意図的無効 vs 配線落ち」判別 (期日 10-06)
- 期待効果: LIVE 発火 3 → 最大 4〜8 セル。rnb が計画どおりなら M3 律速セル (13.8 ヶ月) の代替で ETA を 2027-11 → 2027-03〜04 へ短縮しうる (goals-4 訂正版の楽観径路)
- 工数: パケット起案 2〜3 セッション。リスク: rnb は全段未確定 (BT 頻度の live 実現は未検証)。**最終 R1 承認は user**

**R2: マージゲート — 既に走っている独立レビューに読み手を付ける** ✅ **執行済み 2026-09-08** ([[pr-review-gate-2026-09-08]])
- 何を: 自走マージ手順 (gh pr merge --admin) に「connector レビュー到着待ち + P1/P2 消化 or 明示 dismiss」を必須ゲートとして組込み、CLAUDE.md の Codex レビュー行を実機構 (GitHub connector) に修正
- 期待効果: 潜伏 100 日級 verdict/estimand 欠陥の検出遅延短縮。追加コストほぼゼロ (レビューは既に無料で届いている)
- 工数: 0.5 セッション。リスク: マージ律速 (数分〜数十分の待ち) — R1/verdict/live 経路 PR に限定する運用も可
- **執行結果 (2026-09-08)**: `tools/pr_review_gate.py` + CLAUDE.md 組込み。実測で本提言の前提が定量確認された — finding を持つ 35 PR の解決済みスレッド **0 件** / review→merge 中央値 **2.8 分**。同日、未読 P1 が原因の実害 (daily trigger watch が 51 エントリ 2 日間停止) を発見・修復

**R3: 欠陥税の一括返済 — estimand 宣言表 + fault-injection 常設**
- 何を: (a) freshness_policy 方式を一般化した estimand 宣言表 (名乗り/母集団/時計/分母/読み手) + CI 突合チェッカー、(b) counterfactual 注入を PR 儀式から常設 fault-injection 回帰スイートへ (全 ~10 検知器 + guard 自身の counterfactual を対で保持)、(c) SignalContext 単一ファクトリ + 値域内 sentinel default の lint、(d) 修理 PR に「混入日・発見日・発見手段」3 フィールド必須化と QA 起点発見率の月次 KPI 化
- 期待効果: 潜伏中央値 124 日 → デプロイ後初回市場オープンで検出 (目標 ≤14 日)、欠陥税率 75% → <20% を計測 KPI 化。※これ単独で M1 が縮む保証はない (律速の主因は正 EV セル不在) が、M1 判定を 60 日凍結させた類のバグの再発を作成時に遮断する
- 工数: 1〜2 週の明示予算化。リスク: 予算化しないと場当たり返済が続き研究 WIP ゼロが継続する

**R4: KPI・目標系の修復**
- 何を: (a) M1 強定義 (承認済み) の monitor 実装 + 文書間矛盾 (v2.3 KPI 表の弱定義 vs rederivation §4) の裁定起票、(b) M3 を M3a (throughput) / M3b (return) に正式分離し ETA を月次機械再計算、(c) **NAV floor 到達予測日**を Tier A cron の先頭 KPI に追加 + M2 を keeper 控除後で再導出、(d) 台帳 anchor の broker 実測再基準化 (乖離 ¥48k) + index.md L6 の廃止数値撤去、(e) 全符号系 KPI に N と roster サイズ併記
- 期待効果: 「達成に見えて達成でない」「止血が KPI 改善に見える」倒錯の排除、資金時計とロードマップの初の突合
- 工数: 1〜2 セッション (定義裁定のみ user)

**R5: 探索空白の enforcement 機械化**
- 何を: 「能動 explore 枠 = 0 が X 日継続」を registry の機械評価トリガとして登録 (TRIGGERED で臨時スキャン/裁定前倒しを強制)。ticket 起票時に「決裁不要の primary 経路で続行可能か」判定を S2/S3 出口条件に追加。SLA 超過を WARN→ERROR 格上げ。session log の未解決事項を機械転記でなく一次ソース (queue frontmatter/registry) から再生成
- 期待効果: E23 型 17 日滞留・19 日空白の再発防止。保守条件の降格は**行わない** (時間短縮効果ゼロ、rigor-4 訂正版)
- 工数: 1 セッション

**R6: コンテキスト衛生一括**
- 何を: MEMORY.md を 20KB 以下へ圧縮 (クローズ済み falsification 群の統合・prepend 統一) — **OANDA 存続条件の欠落を即日解消**。QUICK_REF ソースを最新版参照へ。lessons 注入を index 手書きリストから mtime 走査へ。worktree 78/stash 180/branch 381 の GC + main 書込みセッションの直列化 (post-commit push hook)
- 期待効果: 致命情報の欠落ゼロ化、事故由来復旧コスト (~5-8 セッション日/2 ヶ月) の除去
- 工数: 2〜3 セッション

**R7 (統計設計、未検証提案として R3 の後):** MDE 事前スクリーンを pre-reg テンプレ必須欄に (family C 型の「測定の名を借りた ban 消費」防止、即日・コストゼロ)。階層プーリングを「昇格候補の優先順位付け専用・α 消費ゼロ」層として R3 手続きで導入検討。ban の 2 層化 (FALSIFIED 恒久 / UNDERPOWERED-RIGHT-SIGN 条件付き復活) は処分コードの統一フィールド化として実施 — ただし回復余地は 3〜7% と小さい (rigor-1 訂正版)

---

## 5. user 決裁が必要な項目

| # | 決裁事項 | 選択肢 / 背景 |
|---|---|---|
| U1 | **ミッション実現可能性の再決裁** (08-05 橋渡し前提の崩壊後未起票) | (a) 資本・レバ制約の変更 (b) ミッションを M3 系列 (+2〜3%/月複利) へ正式改定 (c) 現行制約のまま継続 (20% は無期限)。20%/月には ~25x レバ = unwind 即死が user 自身の認識 |
| U2 | **資本スケール上限の一度きりの凍結** — 「M3 達成が確認できた場合に投入しうる資本上限」 | この 1 変数にプロジェクトの経済的意味が最も感応する。10M JPY なら M3 = 月 20-30 万円、現 NAV のままなら月 6,500〜9,700 円で、手動 carry (+0.3-0.4%/月 ≈ ¥1,000/月・工数ゼロ) との相対優位が変わる |
| U3 | **NAV floor 前の決裁点の事前設定** — floor 到達 2027-02〜04 (中心推定)、到達で OANDA API 停止 = 目標系全停止 | 入金 / 縮退 / 停止 を floor 到達**前** (遅くとも 2026-12) に決める。keeper 費用対効果 (¥2,080/月 vs エッジ収益 ≈0) を月次提示 |
| U4 | **供給空間の変更 (p_pass を動かす唯一のレバー)** | 有償データ (Databento — 決裁点は E22 で定義済) / daily+ クロスセクショナル (現 NAV では最小ロット粒度で不成立 — U2 に依存) / FX 以外。09-18 scan#4 に feasibility 1 本を添えて提示 |
| U5 | **Codex 実行チャネルの正式廃止** — Render worker fx-codex-runner の suspend (課金停止)、_paused 66 件 archive、CLAUDE.md レビュー行の実態化 | 「殺す」の正式決裁がないまま 07-04 以降 carry-forward から消えた項目の清算 |
| U6 | **rnb_support_bounce 登録 R1** (期日 10-06、前倒し推奨) + weekend_gap 執行契約 R1 | R4.2-R1 のパケットに対する最終承認 |
| U7 | **プロジェクト falsification 条件 (§6) の凍結承認** | 個別エッジと同じ pre-reg 規律をパイプライン自体に適用 |
| U8 | (小) vix #7 ban 例外 (weak-signal portfolio #20 の K=3 再開レバー、p=0.050091 knife-edge) — 未検証 finding 由来のため優先度低で再上程 | false-positive コストは knife-edge 1 件分 |

---

## 6. プロジェクト自体の falsification 条件 (registry 凍結案)

個別エッジには世界水準の pre-reg を課しながらパイプライン自体には棄却条件がない。時限 verdict の日付が揃っている今が凍結の適期 (viability-7 提案、E22 で「PASS 時の帰結の事前凍結」前例あり — 新規の方法論は不要)。

- **F1 (供給空間)**: **2027-02-05 (E12 first look) までに** E1 (first 10-15 / second 2027-01-06)・ECG (11-06)・E12 の 3 系統から OOS PASS がゼロ**ならば**、3 次スキャンで枚挙した C1 実現可能空間は消滅と認定 — 現行パイプラインを棄却し、有償データ / venue 変更 / 終了 の三択を user 決裁へ (結合 FAIL 確率 ~61〜89%)
- **F2 (執行変換)**: **2026-12-31 までに** weekend_gap の live 執行 N が依然 0 **ならば**、「PASS→live PnL」変換は未実証と正式認定し、以後の全 PASS の価値を執行実証まで割引く (pre-reg テンプレに fill 成立率の事前見積りを必須化)
- **F3 (M1 耐久)**: **2027-03 までに** clean live N≥30 で PnL>0 のセルが 1 本も立たない**ならば**、M1→M2→M3 の段階設計自体を再導出する
- **F4 (資金時計)**: **NAV floor 到達予測日が 90 日以内に入った時点で** 入金/縮退/停止の user 決裁を強制起票 (現行推定では 2026-11〜12 に発火)
- **Global stop**: 連続 2 四半期「新規 OOS PASS ゼロ ∧ live 正セル (N≥30) ゼロ」で全面棚卸し (初回判定 2027-03-31)

凍結の効果は双方向: sunk cost による延命判断の構造排除と、F1 通過時に「継続は正当」の on-record 根拠が立つこと。

---

## 7. 付録 — REFUTED となった主張 (本文の根拠に不使用)

whole-finding の REFUTED はゼロ。PARTIAL 内で反証された sub-claim を 1 行ずつ:

1. 「ミッション乖離が **13 ヶ月間**未決裁」(goals-2) — プロジェクト齢 5.6 ヶ月で数値的に不可能。実際は 2 回決裁済み + 再決裁未起票 ~1 ヶ月
2. 「07-06 以降 Claude の verdict に**独立レビュー層が存在しない**」(codex-1) — GitHub Codex connector が PR #75 以降稼働。真の欠陥はレビューが読まれずマージされること
3. 「直近 16 session log 中 KB 明示引用 **5 本のみ**」(arch-4) — 実測 10/16
4. 「weekend_gap の以降 5 週末分の追跡が KB 上で確認できない」(viability-3) — 4/5 週末は registry/session で追跡済み、qualifying ゼロで R1 起案条件は不成立 (起案漏れなし)
5. 「保守条件の AND スタックが探索空白を生んだ」(rigor-4) — スタックは暦時間を消費しない。真因は枯渇 + forward 待ち + enforcement 不在
6. 「weak-FAIL 6 件の処分が falsification と同型で**約 2 割回復可能**」(rigor-1) — 4 件は復活枠既存、回復余地は実質 3〜7%
7. 「M2 は weekend_gap 級セル **1 本で足りる**」(viability-2) — L1 上限 (disaster SL binding) で +0.46%/月 < 0.5%、M2 定義も 2 セル要求
8. 「keeper 実測ペース ~¥5,000/月」(goals-1) — 月次 target 到達で自動停止、上限 ~¥2,080〜2,600/月
9. 数値訂正群: _paused 68→**66** 件、08-20 以降 PR 34→**28** 本、欠陥税 78%→**75%** (21/28)、fix 系 20→**16** 本、PR 総数 194→**195**、トリガ評価器潜伏 44→**36** 日 (平均 112→**111** 日)、call-site 欠落「5 例目発生」→**4 例 + 5 例目予防 pin**、Bonferroni m 上限 224→**1728**、「86 本が放置スタブ」→**純スタブ 76 本** (85 本が placeholder 残置)



---

## 8. 監査自体の既知の盲点 (completeness critic 出力 — 次回監査/フォローアップ対象)

1. **4原則そのものの妥当性監査が欠落 (聖域化)。原則1「マーケット開いてる間は攻める」と原則4「攻撃は最大の防御」は clean live −242.6p 負エッジ + 欠陥潜伏中央値124日という実データの下では『欠陥税を実弾で払い続ける公理』であり、M1 最短経路 (shadow 蓄積 + live 最小化) と逆向きの可能性があるが、7次元のどれも公理の再導出を含まず、KB にも4原則自体の検証文書が見当たらない (claude-harness-design.md に該当記述なし、grep 確認済み)。**
   - なぜ重要か: 監査結論の最短縮レバー『live 層の回収』は、live で攻め続けることを命じる原則1/4 と正面衝突する。公理を user 再決裁の議題に載せない限り、プロセス改善提案は上位規範に却下され得る — time-to-M1 に直結する未検証の最上流変数。confidence: high (user 決裁事項だが監査対象からの除外理由は文書化されていない)。
2. **実弾システムの変更管理・資金安全ガバナンスが監査対象外。`gh pr merge --admin` (branch protection バイパス) の自走マージ → main auto-deploy → 本番 OANDA 口座という『人間レビューゼロでコードが実弾に到達する経路』が恒久承認されており (MEMORY 2026-07-06)、QA 起点発見 0/8 という defect-tax 所見と組み合わさる。code 側の防御 (_OANDA_LOT_CAP=10000 @demo_trader.py:10025、MAX_CURRENCY_EXPOSURE=20000 @exposure_manager.py) は実在するが、これらのカバレッジ検証・kill-switch の有無・Discord bot / 外部データ ingest 経由の prompt-injection 面は7次元に含まれない。**
   - なぜ重要か: 欠陥税の監査は『過去に払った税』の計測であり、549250 事故や watchdog 再武装バグ (E4 live 11発) の同型が将来 NAV を一撃で毀損する tail risk の統制評価はされていない。破滅イベント1回で time-to-M1 は無限大になる。confidence: high (経路と caps は実測、tail 確率は未定量)。
3. **BT 判定基盤のデータ品質・摩擦モデル妥当性が未監査。base rate ≈4% と26系統以上の ban/FAIL 判定は、drift が実測されている MASSIVE データ (AUD_USD −25行、2019-09/2020-10 ベンダー穴、EUR_USD 2020-10 選挙週穴 — いずれも MEMORY 記載) と stressed-net 摩擦モデルの上に立つが、摩擦モデルの較正を live 実測と突き合わせる独立監査、および FAIL 判定の偽陰性率推定が存在しない。**
   - なぜ重要か: funnel 次元の核心数字『真の base rate ≈4%』はデータ層の系統誤差をそのまま継承する。BE/Trail が Python BT WR を +20pp 水増しした前例 (逆方向バイアスの実証) がある以上、摩擦側に保守バイアスがあれば本物のエッジを ban 済み台帳に葬っている可能性が残り、『探索増産は無効』という戦略結論の頑健性が揺らぐ。confidence: medium (バイアスの存在は未実証、依存関係は確実)。
4. **本番コードの構造品質とテスト実効性が定量化されていない。demo_trader.py 10,775行 + app.py 16,250行の実質2ファイル・モノリスに対し test 関数 2,783 個 (実測 grep) が存在するのに欠陥潜伏中央値124日・QA 起点発見 0/8 — つまり『テストは大量にあるが欠陥を捕まえない』という実効性ギャップの根因分析 (モノリス構造・counterfactual なしの手組み fixture・CLAUDE.md の "92 tests" という桁違いの陳腐化) が欠陥税の税額計測から独立して行われていない。**
   - なぜ重要か: 欠陥税を『税額』として測るだけでは削減レバーが出ない。潜伏124日がモノリス+弱 assertion の関数なら、live 層回収の前提となる『新規欠陥の流入率削減』は構造リファクタか mutation-testing 型の検証強化が必要で、これは監査の是正提案の実行可能性を左右する。confidence: medium (architecture 次元が部分的に触れた可能性あり)。
5. **human-in-the-loop (user 関与) の設計とレイテンシが未計測。統合 verdict は最短縮レバーを『目標・資本前提の user 再決裁』としながら、user 決裁の実測ターンアラウンド (T5 発動後18日未執行、vix SELL 決裁待ち滞留、E21 外部 CSV 提供待ち3週間以上、D3 SLA 48h の遵守実績) と決裁を依頼するインターフェース設計 (Discord bot の決裁 UX、決裁待ちキューの可視化) が監査されていない。**
   - なぜ重要か: ボトルネックを Claude プロセスから user 決裁に移す提案は、user 側スループットが Claude 側より低ければ time-to-M1 をむしろ延ばす。単一決裁者のレイテンシ分布は是正計画の律速を決める一次変数であり、既存ログ (pre-reg registry の発動日 vs 執行日) から低コストで測定可能なのに読まれていない。confidence: high (滞留事例は MEMORY で複数実証済み、分布未計測)。

---

## 9. Provenance

- workflow run: `wf_25ffef0e-463` (37 agents / 675 tool uses / エラー 0)。次元別 findings 54 件、うち敵対的 verify 実施 25 件 (CONFIRMED 9 / PARTIAL 16 / whole-REFUTED 0)、未検証 (minor 等) 29 件は本文で「未検証」明記
- 検証済み per-dimension findings の全文 JSON はセッション成果物として保持 (要すれば raw/audits/ へ展開可)
- 関連: [[independent-audit-2026-04-10]] (初回独立監査) / [[fable5-system-audit-2026-07-02]] (システム監査) / [[edge-dev-postmortem-2026-07-24]] (エッジ開発 postmortem) — 本監査はこれらの後継で、初めて「プロセス自体」を対象化した
