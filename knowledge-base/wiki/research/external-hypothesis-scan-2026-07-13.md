# 外部仮説スクリーン 2026-07-13 — WS3 供給ラインの「モダリティ転換」

> **rule:R3 (診断・スクリーン)**。live/shadow 不変更。エッジ主張なし。
> **起点**: WS3 内部母集団探索が **2 周で FAIL** — round-1 stage-2 の barrier/EV 化 FAIL ([[ws3-stage2-barrier-ev-prereg-2026-07-09]] §8) + round-2 OOS **0/5** ([[ws3-round2-explore-prereg-2026-07-10]] §8)。両 pre-reg の固定分岐 = 「本番 shadow 母集団内の軸は枯渇 → **外部仮説 (新シグナル系統) の探索へ転進**」。本ノートはその転進の正式な入口。
> **関連**: [[shortest-path-decision-memo-2026-07-10]] (トラックB=供給ライン) / [[roadmap-v2.3-payoff-friction-repair]] WS3 / [[research/index]]

---

## 1. 何を確定させたか (結論先出し)

**供給ラインの律速は「どの OHLCV パターンを試すか」ではなく「データモダリティ」である。** 3 本の独立な証拠が収束する:

1. **内部 2 周 FAIL** — 現行エンジンの entry × pair × direction × horizon 母集団に、OOS 再現する方向性非対称 + 固定 barrier EV の組は存在しない (2 周一貫)。
2. **外部の同型 falsification** — Mesfin (2026, arXiv:2605.04004) が MNQ 先物 947 日で OHLCV 由来 14 signal family を strict 検証 → **"No signal satisfies all criteria simultaneously"**、gross edge 0.07–1.50 pt は 2pt 往復コスト未満で「構造的に不成立」。**本プロジェクトの内部結論と独立に一致。**
3. **価格 lead-lag の実証的閉鎖 (本セッション probe)** — 下記 §3。OHLCV 内部でも cross-asset でも、≥1h バーの tradeable な先行構造は裁定消滅。

→ **残る OHLCV パターン軸 (lead-lag / term-structure / ML) はいずれも閉鎖・不能・原則違反** (§4)。次の実効的なエッジ供給は **新しいデータモダリティ** (価格以外 or 価格の非先行的利用) からしか来ない。

## 2. 外部仮説プールの再取得 (2024–2026 文献リフレッシュ)

2026-04-12 の 25-paper sweep ([[research/index]]) 以降の現行文献を再スキャンし、制約下で新規かつ実装可能なものを抽出:

| # | 仮説系統 | 出典 (現行) | 必要データ | 新規性 vs portfolio |
|---|---|---|---|---|
| E1 | **retail positioning contrarian** — 個人フローの逆側に intraday 予測性 (個人は uninformed) | News & intraday retail order flow in FX, *JIFMIM* 101 (2025) | broker 建玉比率 (OANDA position ratio / IG client sentiment) | ★ 新規 (sentiment 戦略なし) |
| E2 | **order-flow imbalance** — signed flow が intraday price impact を予測 | arXiv:2508.06788 (2025); Fed Treasury note (2025-11) | signed/tick order flow | ★ 新規だが data 未取得 |
| E3 | **cross-asset (rates/equity → FX)** — 金利・株の macro linkage | Iwanaga & Sakemoto (2024, KB既載 ★★★); 本プロジェクト rates cache | rates/equity futures (ZN cache 済、yfinance 到達可) | ★ 新規 (cross-asset 戦略なし) |
| E4 | HF cross-pair lead-lag | Hasbrouck (2003) framework (KB "Still Unexplored") | 多ペア同期 intraday OHLCV | — (§3 で **閉鎖**) |
| E5 | FX term-structure / forward-rate bias | KB "Still Unexplored" | forward/swap points | — (spot only = **不能**) |
| E6 | ML ensemble (Gu-Kelly-Xiu framework) | KB "Still Unexplored" | (任意) | — (§4 で **原則棄却**) |

## 3. 実証 probe — 価格ベース lead-lag の閉鎖 (rule:R3)

`tools/ws3_leadlag_ic_explore.py` / 生成物 [[ws3_leadlag_ic_2026_07]] (raw/bt-results)。read-only feasibility probe (verdict でない、OOS 窓非消費)。

**A. 内部 cross-pair lead-lag (1h, 13 pair, N=20,443, 2023–2026)**
- **naive scan の罠**: max|IC lag1| = **0.373** (EUR_GBP→AUD_JPY)、Bonferroni-sig **50 pairs** (r_crit=0.025)。素朴には「大量の有意 lead-lag 発見」に見える。
- **敵対的検査 (Lo-MacKinlay 非同期取引バイアス)**: top hit を liquid-hours + destale で再計測 → IC **0.0041 に崩壊**。own lag-1 autocorr は EUR_GBP **−0.41** / AUD_JPY **−0.32** (= bid-ask bounce / stale-quote シグネチャ)。**50 pairs は全て非同期取引の spurious cross-autocorrelation。**
- **liquid majors only**: max|IC lag1| = **0.027** → 捕捉 ~0.17p/t、friction 2–4.5p 未満。**tradeable エッジなし。**

**B. cross-asset lead (ZN 10y T-note fut → USD_JPY, 1h)**
- contemporaneous IC = **−0.585** (強い・符号整合: yields↑=ZN↓⇒USDJPY↑) — **macro linkage は本物。**
- **lag-1 lead IC (ZN→USDJPY) = 0.0075** → 捕捉 ~0.09p/t vs 2.14p friction。**tradeable な先行なし** (情報は同時反映)。※ ZN cache は 1 ヶ月 (438 bar) = feasibility 限定、verdict ではない。

**帰結**: 価格の先行構造は OHLCV 内部でも cross-asset でも ≥1h で裁定消滅。E4 (lead-lag) を**閉鎖**。ただし B の **−0.585 という強い contemporaneous linkage** は、先行信号ではなく **divergence-reversion (FX が rate-implied 水準から乖離 → 回帰)** という**非先行構成**なら未検証の余地がある。

## 4. スクリーン判定 (hard constraints C1–C6)

制約: C1 データ実現可能性 / C2 falsified 6 系統除外 (H4 level / channel / horizontal sweep&reclaim / mtf SELL / bb_rsi / T11 counter-USD) / C3 portfolio 非重複 / C4 friction 生存 (MFE/MAE 非対称 ratio≥1.3) / C5 反カーブフィッティング (complex-gate-edge-destruction 教訓) / C6 revealed-edge 整合 (trendline_sweep = 唯一 ELITE_LIVE、斜めTL流動性)。

| 仮説 | C1 | C2 | C3 | C5 | 判定 |
|---|---|---|---|---|---|
| **E3 cross-asset divergence-reversion** | ✅ (rates/equity 到達可・ZN cache 済) | ✅ | ✅ | ✅ 単一 linkage で simple-first 可 | **採用 → round-3 pre-reg 候補 (自走可)** |
| E1 retail positioning contrarian | △ 建玉比率の history 蓄積パイプ要 (net 到達可だが persistent ingest 未整備) | ✅ | ✅ | ✅ | **保留 → infra 決定 (§5)** |
| E2 order-flow imbalance | ❌ signed flow 未取得 (OHLCV volume は弱 proxy) | ✅ | ✅ | ✅ | 棄却 (data) |
| E4 lead-lag | ✅ | — | — | — | **閉鎖 (§3 実証)** |
| E5 term-structure | ❌ spot only、forward curve なし | — | — | — | 棄却 (data 不能) |
| E6 ML ensemble | ✅ | — | — | ❌ データ蓄積フェーズで curve-fit + complex-gate 教訓に真っ向反 | 棄却 (原則) |

**唯一の自走可能な採用候補 = E3 cross-asset divergence-reversion。** §3B の強い contemporaneous linkage (−0.585) を「先行」ではなく「乖離の基準線」として使う非先行構成。

## 5. 判断 — 次の供給ライン投資 (ランク付き)

1. **【自走・即着手】E3 cross-asset divergence-reversion の round-3 探索** → [[ws3-round3-crossasset-divergence-prereg-2026-07-13]] (self-LOCK 予定、純研究)。データ到達済み・net 到達可のため Claude 完遂可。round-1/2 と同一方法論 (discovery diagnostic → 候補固定 → clean OOS verdict、BH-FDR + first-touch EV レグ + ナイフエッジ3点)。
2. **【user infra 決定】E1 retail positioning ingest** — 2025 文献で最も質の高いエッジ。OANDA は建玉比率を公開 (broker 整合)。ただし **positioning history を継続蓄積する ingest パイプの新設** が前提 (単発 fetch では OOS 不能)。これは戦略でなくデータ基盤投資 = 寄与度大だが user 決裁事項。**§6 に提案を drafting。**
3. **【将来】COT/CFTC 週次建玉** — public・DL 可だが週次 (15m/1h には低頻度)。regime filter 用途なら可。

**モダリティ転換の含意 (ボトルネック更新提案)**: roadmap v2.3 のボトルネックは「正の摩擦調整 EV セルの不在」だったが、供給ライン側の律速は本スクリーンで **「価格 OHLCV モダリティの枯渇 → 新モダリティ (cross-asset / positioning) への転換」** に更新される。M3 (正EVセル5個以上) への到達は、OHLCV パターン増産では不可能で、モダリティ追加が必要という構造認識。

## 6. E1 positioning-ingest 提案 (user 決裁用 drafting)

- **何を**: OANDA `positionbook`/`orderbook` または fxlabs 建玉比率を定期 snapshot し、`data/cache/positioning/` に時系列蓄積する ingest job (Render cron 型)。
- **なぜ**: 2025 文献の retail-contrarian エッジは positioning の**時系列**が無いと OOS 検証不能。history は「今から貯め始める」以外に入手経路がない (broker 建玉は過去分が非公開)。→ **着手が遅れるほど検証開始が後ろ倒し。**
- **リスク/コスト**: 低 (read-only snapshot、live 無関係)。net 到達は本環境で確認済 (Yahoo/OANDA REST)。
- **決裁事項**: (a) ingest job 新設の GO/NO-GO (b) OANDA API の建玉比率エンドポイント可用性確認 (本番 token)。**Rule 1 昇格ではなくデータ基盤なので即 GO 可能だが、cron 新設 = 運用面で user 通知が筋。**

---

## 参考文献 (本セッション取得)
- Mesfin, M. (2026). *Structural Limits of OHLCV-Based Intraday Signals in MNQ Futures: A Systematic Falsification Study.* arXiv:2605.04004.
- *News and intraday retail investor order flow in foreign exchange markets.* J. Int'l Financial Markets, Institutions & Money, 101 (2025).
- *Returns and Order Flow Imbalances: Intraday Dynamics and Macroeconomic News Effects.* arXiv:2508.06788 (2025).
- Iwanaga & Sakemoto (2024). Cross-Momentum: Equity × Currency (KB既載, [[research/index]] ★★★).
- Hasbrouck (2003) — HF lead-lag framework (KB "Still Unexplored", 本セッションで実証的に閉鎖)。
