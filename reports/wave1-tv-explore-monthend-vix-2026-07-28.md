# wave-1 TV explore verdict — equity_monthend_conditional ❌ / vix_carry_unwind ❌ (2026-07-28)

**結論: 両ファミリとも凍結 primary test で FAIL → healthy kill ×2。台帳 #6/#7 クローズ。OOS 2022+ は未接触のまま保存。**

- Protocol (観測前凍結): `knowledge-base/wiki/analyses/wave1-tv-explore-protocol-freeze-2026-07-28.md`
- Raw: `knowledge-base/raw/bt-results/wave1-tv-explore-{monthend-cond,vix-unwind,stats}-2026-07-28.json`
- Pine: `bt-results/tv-overlays/wave1_{monthend_cond,vix_unwind}_export.pine`
- Stats: `tools/wave1_tv_explore_stats.py` (seed=20260728, permutation 10,000, BH-FDR q=0.10 across 2 primaries)
- 測定: TradingView OANDA D1 (TV=測定カノン)、exit 機構フリー固定ホライズン {1,3,5}d、explore 2014-2021

## データ整合性

- 全 12 データセット (2 family × 6 pairs): 土曜バー 0、イベント日付は全ペア一致 (assert 通過)
- H2 イベント日付は既知 VIX 史実と一致 (2015-08-21, Brexit 2016-06-24, 2018-02-05 volmageddon,
  2018-12-18, 2020-02-24 COVID, 2021-01-27 GME): 機構整合 OK
- H1 MTD 値は史実一致 (2020-03 −11.1%, 2020-04 +13.7%, 2018-12 −9.9%)
- SPX close 16:00 ET / VIX close 16:15 ET < FX D1 close 17:00 ET → 同日シグナルに先読みなし

## H1: equity_monthend_conditional (台帳 #6) — ❌ FAIL

| test | 値 | verdict |
|---|---|---|
| **primary: pooled Spearman IC (MTD × USD-adjusted 1d fwd), N=96** | IC = −0.052, **p = 0.608** | ❌ 完敗 |
| unconditional 月末ドリフト (対比) | mean −1.1p ≈ 0 | 棄却済み WMR-fix NULL と整合 |
| headroom (MFE p50 / RT) | 15.7–39.8× 全ペア通過 | ✅ (単独では無意味) |

- **条件付き仮説は死亡**: 無条件形 (2026-06-18 REJECT) に続き、Melvin-Prins 型の条件付き形も
  1d ホライズンで IC ゼロ。月末リバランス・フローの FX 転写は探索空間として閉鎖
- **診断ノート (新規主張ではない)**: supporting horizon 3d/5d に**仮説と逆符号**の IC
  (−0.258 p=0.012 / −0.285 p=0.005)。tercile 分解では低 MTD tercile (株弱月) に片寄り
  (5d: lo +52.3p / mid −20.8p / hi −20.7p = **非単調**)。「株弱月の月末後に USD 安」という
  事後ストーリーは作れるが、(a) 凍結 primary ではない、(b) 事後ホライズン選択 = round-3
  winner's curse の型 (OOS 8/8 符号反転の前科)、(c) 非単調 = COT 型 incoherence。
  **→ 新 family として登録しない (healthy kill 原則: 無理に候補を作らない)**

## H2: vix_carry_unwind_continuation (台帳 #7) — ❌ FAIL (knife-edge)

| test | 値 | verdict |
|---|---|---|
| **primary: pooled short 3d mean (イベント横断), N=23** | **+46.2 p/event, 厳密 p = 0.050091** (2²³ 全列挙; 10k permutation 推定 0.0511) | ❌ BH 閾値 0.05 (q=0.10, m=2, k=1) 不通過 |
| supporting 1d / 5d | +25.7p p=0.111 / +27.0p p=0.141 (厳密) | ❌ |
| 集中度 (凍結 kill: 単一イベント >50%) | top event 2015-08-21 share 34.7% | 通過 (kill 非該当) |
| leave-one-out (診断) | LOO mean +31.5p, p=0.0998 | 頑健性は中程度 |
| headroom (short MFE p50 / RT) | **31.9–54.9× 全ペア通過** (floor 1.30p なら 67–141×) | ✅ カタログ中最良級 |
| win rate (3d) | 60.9% (14/23)、median +18.3p | mean は右裾 (危機イベント) 依存 |

- **凍結ルールどおり kill、MC ノイズ除去済み**: 10k permutation の p̂=0.0511 は標準誤差 ±0.0022 が
  閾値 0.05 を跨ぐため (シード次第で verdict 反転リスク)、2²³=8.4M 通りの sign-flip を**全列挙して
  厳密 p = 0.050091 > 0.05 を確定** (meet-in-the-middle、`exact_p_signflip`)。verdict はシード非依存。
  **単独 family なら q=0.10 で通過していた** — 並列 2 本の多重性コスト (Bonferroni 分母の共有) を
  観測前に受け入れた設計の帰結であり、事後に閾値を動かさない (T11 ナイフエッジ教訓の裏面)
- 機構は「存在しないと証明された」わけではない (IC-null 型ではなく power 不足型の FAIL)。
  ただし**同型再試行 (VIX レベル閾値 × JPY クロス short × 固定 {1,3,5}d) は禁止**。
  再挑戦は新データ (E7 サプライズ軸、または 2022+ を含む将来の独立 family) でのみ —
  その場合も観測前 pre-reg + 本 explore との隣接差分節が必須
- OOS 2022+ (2022 円急落 + 2024-08-05 VIX 65 を含む) は**未接触のまま保存**

## 台帳への影響

- m=12 → #6/#7 verdict 追記 (クローズ)。アクティブ探索枠は 0/3 に戻る
- wave-1 fetch queue は全消化。残る供給ライン = E1 (first look 10-15) / E7 phase-1 (verdict 08-28) /
  MoF forward (Q2 開示 +10d) / 受動 registry 2 本
- **postmortem §6 の予測どおり**: 外部条件データ (SPX/VIX) でも「無料日次データ × 週次/月次イベント」の
  edge < 認定閾値。仮説単価の低い TV ネイティブ空間の期待値は今回で較正された —
  次の探索資源は E1/E7 級 (蓄積系・非価格モダリティ) へ

## 教訓 (プロセス)

- TV MCP の per-event table export (pine array 蓄積 → table → `data_get_pine_tables`) は
  1 ファミリ 6 ペア ≈ 15 分で explore 一周できる。fetch 工程不要の外部条件系列 (指数/VIX/金利系)
  の探索単価を大幅に下げた — 今後の wave でも第一選択
- 並列 family 数は検定力とトレードオフ (H2 は m=1 なら通過)。**「メカニズム prior が強い家系は
  単独 wave で走らせる」を今後の wave 設計に反映する** (headroom 100x 級の MoF を単独で
  走らせた判断は正しかった)
