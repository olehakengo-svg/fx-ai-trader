# 勝てている EA 大規模調査 (EA Landscape Sweep) — 2026-07-31

> **rule:R3 (診断・スクリーン)**。live/shadow 不変更。エッジ主張なし。
> **起点**: user 指示 (2026-07-31)「勝てている EA を全力で海外の WEB 含めて、blog、記事など全て大規模調査して、勝てるエッジ探索をして」。
> **方法**: 31-agent workflow (13 ソース並列 Web スイープ → 113 findings → 上位 18 を敵対的検証)。検証基準 = banned 19 ファミリー + LOCKED 4 本 (E1/E7/E12/MoF) との隣接判定 / 生存バイアス・マーチン偽装検出 / OANDA RT 摩擦 headroom 10× 実現性。
> **Raw**: `knowledge-base/raw/analysis/ea-landscape-sweep-2026-07-31.json` (113 findings + 18 verdicts + 13 source_notes 全量)
> **関連**: [[external-hypothesis-scan-2026-07-13]] / [[external-hypothesis-scan-round2-2026-07-18]] / [[hypothesis-catalog-2026-07-24]] (台帳) / [[edge-dev-postmortem-2026-07-24]]

---

## 1. 結論先出し

**「勝てている EA」の世界は、multi-year verified live で見ると実質 2 アーキタイプに収斂する。** 13 ソース (MQL5/Myfxbook/FX Blue/Darwinex/海外フォーラム/Reddit/クオンツ blog/国内 GogoJungle/学術/prop firm/GitHub OSS/SMC-ICT/生存率研究) が独立に同じ絵に到達した:

1. **ナイトスキャルパー (Asia セッション MR)** — 機構は実在 (NY クローズ後の板崩壊 → overshoot → 東京流動性到着で回帰、Krohn 系研究と整合) だが、**エッジの正体は「最タイトな overnight スプレッドを持つ者だけが収穫できる流動性プレミアム」**。ブローカー側がスプレッド政策 (アジア時間 +0.3-0.8p 常時拡大、ロールオーバー 10-20p スパイク) で回収済みで、cohort 全体が 2022-2023 からフラット化。グロスアノマリー 5-15p vs headroom 10× 要求 21.4p (USD_JPY) で**構造的に門前払い、しかも発火窓 = 当プロジェクト実測のスプレッド異常窓 (RT 2-3 倍) そのもの** = デスゾーン動的防御と自己矛盾。gotobi (#13) と同型の「効果は実在するが sub-friction」で**クローズ**。
2. **コモディティ・クロス (AUD_NZD/AUD_CAD/NZD_CAD) のグリッド** — 表層 (グリッド/ナンピン) は negative-skew リスク変形で **RISK-ILLUSION** (Waka Waka: 「69 ヶ月連続プラス」と DD 66.5% + 2024 ユーザー破綻報告が両立)。しかし**独立ベンダー 4 系統以上 (Waka Waka 8y / Boring Pips 3.3y PF2.34 / NoPain 5y / Perceptrader 4y) が別ロジックで同一の三角クロスから抜いている = エッジは EA 固有でなくペア構造 (コモディティブロックの政策共動・20 年超レンジ) に宿る**。この per-position 形は banned に不在で、内部では session-mr-cross-wave1 (2026-05-11、`raw/bt-results/session-mr-cross-wave1-2026-05-11.json` — 全セル missing_cache) が **BLOCKED_DATA で verdict 未達のまま眠っていた** (banned ではなく未完、当時の欠損は現在 MASSIVE 12y で解消可能)。→ **GO 候補 #20**。
3. **メタ層の発見: equity-curve gating (Forex Flex EA の "virtual trades")** — 市場エッジではなく「自戦略 P&L の短期持続性を条件とする露出配分」。banned 全 19 ファミリーはシグナル族でこれは配分層 = estimand が異なる。**検証は内部 shadow ログのみで完結・新規データゼロ・新規摩擦ゼロ** = 供給枯渇下で突出して安い検証。4原則 #3 の LIVE 側「勝てる場所で勝つ条件だけ転送」ドクトリンと設計整合。→ **GO 候補 #21**。
4. **E7 への外部確認**: Darwinex 首位 THA (event-driven、11.5y gross +832%、AUM $12.78M、FCA/CNMV 規制下の独立リスク管理) の機構 = 「サプライズ条件付き under/over-reaction」は **LOCKED E7 と同一 estimand** — 新提案は不可だが、**E7 の事前確率を上げる外部エビデンス**として記録 (verdict 08-28 の解釈材料)。
5. **トレンドフォロー / ニュース / gold / SMC-ICT のマーケティング系**: 3y+ 独立 verified の代表個体が** 1 つも見つからない** (マーケティング密度と生存証拠が逆相関)。SMC 唯一の pro 側学術検証 (Agarwal 2023) は著者自己撤回済み (2025-11)。MQL5 トップセラーの ~60% は XAU グリッド系で、当プロジェクトの XAU 停止判断と整合。
6. **死因の順位 (フォーラム横断)**: ①ブローカー対抗措置 ②negative-skew tail 顕在化 ③regime expiry ④ベンダー放棄 — **「他プレイヤーの裁定によるアルファ減衰」で死んだ明確例はリテール EA 界隈にほぼ無い**。死は市場でなく執行レイヤーと risk 構造で起きる = headroom 10× 規律が①を事前排除する設計であることの外部裏付け。

**verdict 分布 (敵対的検証 18 件)**: GO 3 (実質 2 ファミリー) / ADJACENT-BANNED 3 (E7 衝突 1 + グリッド着せ替え 2) / RISK-ILLUSION 2 / NOT-FEASIBLE-RETAIL 10。

## 2. 生存率ベースレート (全 findings への割引関数、survivorship agent)

| 階層 | 実測生存率 | 推奨割引 |
|---|---|---|
| マーケティング BT のみ | — | エッジ実在確率 ~0-5% (実質ゼロ) |
| MQL5 live シグナル (品質フィルタ済) | 5 ヶ月で ~50% 消滅 (月次ハザード 10-13%) | verified <1y は表示エッジ × 0.1-0.2 |
| GogoJungle 全 4,963 EA | ベンダー自身のフォワードで 50% が PF<1.0、「堅実」4.5% | 同上 |
| verified live 3y+ かつ非負スキュー (WR 50-70%/PF 1.3-2.0/DD 10-20%) | 例外的少数 | × 0.3-0.5 が上限 |
| WR>90% or avg loss ≫ avg win | — | grid/martingale とみなし**破産確率で評価 (エッジ割引でなく除外)** |
| 査読済み学術アノマリー | OOS −26% / 公表後 −58% (McLean-Pontiff) | 公表時点で −35〜58% + 公表年が新しいほど年 +5ppt 減衰 |

指標ゲーミングの実測 (Myfxbook 実査): Gain% は出金操作で膨張 (Seagull: 表示 +2,276% vs abs +9.3%)、DD% は floating loss 非計上で圧縮、**「$ 正 & pips 負」はマーチンゲール増玉の指紋**。「直近成績最高」での選抜は decay 中戦略を優先的に掴む (Penasse repricing bias) — 「今勝っている EA」リストは定義上このバイアスの極大点。

## 3. 敵対的検証 18 件の verdict 一覧

| 候補 | verdict | score | 要旨 |
|---|---|---|---|
| コモディティ・クロス均衡回帰 (Waka Waka 家系の per-position 核) | ✅ **GO** | 63 | §4.1。グリッド剥がした D1 multi-day fade。banned #3 (回帰チャネル) はメジャー 6 ペア×15m×≤48bar のみで非該当を実査確認 |
| Boring Pips (同三角クロス別ロジック) | ✅ **GO** | 56 | §4.1 に統合。M5 形態は即死、H1-D1 range-percentile 形のみ。G0 = OANDA RT 実測が最初のゲート |
| Forex Flex EA "virtual trades" メタゲーティング | ✅ **GO** | 55 | §4.2。ベンダー実績は証拠価値ゼロと認定した上で、機構 (equity-curve gating) の内部 counterfactual 検証が突出して安い |
| Thales / DARWIN THA | ⚠️ ADJACENT-BANNED | 30 | **LOCKED E7 と同一 estimand の正面衝突**。処分 = E7 prior 加点として記録、CB 声明テキスト・モダリティは 08-28 後に再評価 |
| Waka Waka EA (グリッド形態そのもの) ×2 | ❌ RISK-ILLUSION / ADJ-BANNED | 12/8 | negative-skew 変形。per-position 核は上記 GO に分離済み |
| NoPain MT5 | ❌ RISK-ILLUSION | 10 | 同上 (グリッド) |
| 一本勝ち (USDJPY 15m、国内) | ❌ NOT-FEASIBLE | 12 | ただし §5.2 の exit 整形仮説を供出 |
| Night Hunter Pro 家系 (ナイトスキャルパー ×5 重複検出) | ❌ NOT-FEASIBLE | 3-12 | §1.1 の通り。機構実在・OANDA 移植構造的不能 |
| 生存率研究 4 本 (Penasse/McLean-Pontiff/Falck/Chague) | ❌ NOT-FEASIBLE (戦略でない) | 8-10 | §2 の割引関数として KB 収載 |

## 4. GO 候補 (台帳 queued — [[hypothesis-catalog-2026-07-24]] #20/#21)

### 4.1 #20 `commodity_cross_range_mr` — コモディティ三角クロスの per-position レンジ MR (score 63)

- **機構**: AU/NZ/CA は輸出構造・金利サイクルが共動するコモディティ経済で、そのクロス (AUD_NZD は 2002 年以降 0.615-0.99) は FX で数少ない構造的レンジ。取る相手 = レンジ内でブレイクを追う trend-chaser。**消えない理由 = capacity 極小 (数百万ドル以下) + negative-skew divergence 保有プレミアム + レイテンシ非依存** — broker 軍拡競争と無縁な珍しい型。
- **外部証拠の扱い**: EA live 実績 (WR74%/PF1.70 等) は**ナンピン構造の産物で per-position エッジの証拠価値ほぼゼロと認定** — GO の根拠は track record でなく構造 prior (20 年超レンジ + 独立ベンダー 4 系統の収斂 + 学術 cointegration 支持)。
- **内部照合**: session-mr-cross-wave1 (2026-05-11、5m セッション窓 MR) が BLOCKED_DATA で未完 — 本 family は D1/H1 multi-day で estimand も別。banned 隣接は #3 回帰チャネル (幾何 fit / メジャー / intraday — 非該当をハーネス実査で確認) / #14 PPP (月次 5y-z — ホライズン別) / E20 (→ **金利差調整アンカー変種は禁止、v1 は純価格アンカーのみ**)。
- **負の prior (正直に)**: 遅い均衡回帰系は「方向は合うが弱い」死型 3 例 (ppp/quote-spread/round-number) の家系。RBA/RBNZ 政策デシンク局面 (2014-15, 2022-24) でエッジが死ぬ regime 依存が実証済み (2024 の Waka ユーザー破綻) → **OOS に敵対的窓として必須組込**。AUDNZD MR は機関 RV デスクの定番でもあり、リテール残余のみの可能性。
- **G0 (必須事前ゲート、シグナル計算前)**: OANDA の 3 クロス実測 RT (rollover 込み ≥1 週間)。RT 未収載ペアのため**ここで落ちる確率が最も高く、落ちたら即クローズ**。保守見積 RT ~4-6p、multi-day swap を stressed-net に算入 (weekend_gap 基準踏襲)。
- **testable form (pre-reg 起案時に primary 1 本へ凍結)**:
  - 変種 A (D1): `z = (close − SMA200d) / std60d`、D1 close 確定 |z|≥2.0 fade、fwd 5d/10d 固定
  - 変種 B (H1): `range_pct = (close − 20d低値)/(20dレンジ)`、≥0.90 SHORT / ≤0.10 LONG + D1 trend veto、fwd 5d
  - 共通: **single-entry のみ (grid/averaging は評価対象外)**、3 ペア × 2 サイド Bonferroni、explore/OOS 時分割、event-block bootstrap、D1 曜日ラベル罠 (wave-4 教訓) 対策
- **kill 基準**: G0 fail / explore IC 符号逆 / stressed-net EV ≤ 0 → クローズ、着せ替え再試行なし。
- **独立性**: 生存中ファミリー (斜め TL sweep MR / weekend_gap / price_shock / MoF / E1 / E7 / E12) と機構・ペア・ホライズン全て非重複。対象 3 ペアはポートフォリオに不在 = ペア分散にも寄与。

### 4.2 #21 `equity_curve_shadow_gating` — shadow 損益条件付き live 転送のメタ配分層 (score 55)

- **機構仮説**: 戦略リターンの regime 持続性 — 「セルが直近勝っている市場状態は自己相関する」。市場エッジではなく露出配分ルールなので他者と競合せず、裁定で消えない。
- **学術 prior は mixed〜negative** (戦略リターンの系列相関は通常 ≈0、gate は回復局面を取り逃す) — **低 prior・低コスト枠**としての台帳入り。期待値でなく検証コストの安さ (内部 shadow ログのみ・新規摩擦ゼロ・LOCKED 非接触) が正当化。
- **testable form**: 各セル (closed shadow N≥300、12-18 ヶ月): 直近 K∈{5,10,20} closed shadow trades の合計 pips > 0 を gate とし、`uplift = mean(pnl_net | gate_on) − mean(pnl_net | all)` を block-bootstrap null で検定。Bonferroni (セル数 × 3)。**閾値 0 固定・K は 3 点のみ (最適化禁止)**。
- **交絡遮断**: watchdog/R2 停止が live 転送を変えた期間は shadow book 側でのみ counterfactual 計算。既存の R2 損失停止 / watchdog stage 減衰は**片側 ad hoc 版の先行実装** — pre-reg で差分 (対称・事前登録・counterfactual 測定) を明示しないと二重ゲート交絡になる。
- **規律**: explore は R3 (読むだけ)。**live gate 化は R1 フル手続き + user 承認**。Python BT 系列は使わない (BE/Trail 20pp 過大の教訓) — 本番 shadow closed P&L のみ。
- **PASS 時の OOS**: 次の 90d shadow forward を second look として pre-reg。

## 5. 非 GO だが記録価値のある抽出物

1. **THA → E7 prior 加点** (§1.4)。E7 verdict (08-28) の解釈材料。**残余モダリティ = 中銀声明テキストのニュアンス差分 (票割れ・ガイダンス一語差) は E7 の数値サプライズに不含** — 08-28 後の新規台帳候補として再評価可 (今やるとイベント系の多重比較汚染)。
2. **momentum-decay トレーリング exit (一本勝ち型、国内)**: フォワード PF > BT PF の個体が存在 = エッジが entry でなく exit 整形に宿る例。v2.3 の「勝ち側 exit 執行崩壊」診断と正対するが、**exit 側改善は T2+stage-2 で完全否定済みという強い内部 negative prior** — 正 EV ホストセルが復活するまで parked (mafe exit 復活と同じ棚)。
3. **NY cut オプション期日ボード条件付き intraday** (academic agent、prior 6): 状態変数が毎日無料公開・機構は義務的ガンマヘッジフロー。**#14 ラウンドナンバー隣接のため、pre-reg 設計時に「expiry notional 条件の有無」で差分固定が必須**。次スロット空きの際の候補 (台帳未登録)。
4. **Osler 型 stop-cluster cascade 継続** (SMC agent): 実 order book で hourly 有意の唯一の機構実証ライン。#4/#14 隣接 — テスト可能差分は「クラスタ帯**貫通後の継続** (velocity/displacement 条件付き)」のみ (あちらは reclaim 反転)。parked。
5. **Financial Hacker 再現シリーズの meta 結論**: 単体インジケータのシグナル化はほぼ全 FAIL、生き残るのは **regime filter 用途** — 外部発「新インジケータ」持ち込みは filter 用途以外事前確率ゼロで扱ってよい。
6. **prop firm ルールの逆読み**: firm が禁止する行為 (ニュース窓/HFT/マーチン) は「firm のシミュ環境から金を移転できる行為」の revealed-preference — 大半は執行/制度アーティファクトで実弾 OANDA に移植不能。funded 平均寿命 4.7 ヶ月、出金到達 ~7%。
7. **Robot Wealth の独立同定**: LDN/NY overlap intraday reversal「実在するがコストで即死」= 内部 #15 系の外部裏付け。weekend gap は persistent と独立判定 = **live wg×3 の外部確認**。
8. **検証衛生の集合知 (Reddit ex-prop)**: live DD は BT の 2-3 倍 (独立 2 名) / MT5 real-tick BT は信頼・Python BT は疑う (TV>Python 教義と一致) / 「機関のコストハードル (年 $1M 未満は捨てられる) を下回るキャパの戦略が私的には良い収入になる」。

## 6. 台帳への反映と次アクション

- [[hypothesis-catalog-2026-07-24]] に **#20 commodity_cross_range_mr (queued)** / **#21 equity_curve_shadow_gating (queued)** を追記 (本コミット)。並列アクティブ上限 3 本ルール: wave-3/4 全クローズ済みでアクティブ 0 → 2 本着手可。
- **#20 の最初のアクション = G0 (OANDA 3 クロス RT 実測、≥1 週間、rollover 込み)** — シグナル計算ゼロの摩擦測定なので即着手可、pre-reg スロットも消費しない。G0 通過時のみ explore pre-reg 起案。
- **#21 の最初のアクション = explore pre-reg 起案** (K/閾値グリッド凍結、交絡遮断規定、Bonferroni 分母確定) → self-LOCK → 単一実行。
- 本調査自体の再実行価値: 低 (構造的結論は安定)。次に外部を見るのは E7 verdict (08-28) / E1 first look (10-15) の後で十分。

## 7. 調査の限界 (正直に)

- ForexFactory / Steve Hopwood / GogoJungle 公式フォワード / SSRN 一部は bot 403 — 独立レビュー・widget API・キャッシュ経由の間接取得で補完 (一次ページ精読不可のものあり)。
- SMC agent は検索予算到達で日本語ソース × darwinex 照合が未走査。
- Myfxbook「verified」バッジは口座の真正性のみで戦略母集団の選択を補正しない — §2 の割引を常時適用のこと。
- dedup は製品名ベースのため同一ファミリーが複数 verdict を持つ (Waka Waka 系 4 件) — family 単位の結論は本文 §1/§4 が正。検証スキップ 95 findings は raw JSON 参照 (上位 18 のみ敵対的検証済み)。
