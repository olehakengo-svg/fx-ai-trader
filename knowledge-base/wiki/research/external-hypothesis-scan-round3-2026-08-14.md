# 外部仮説スキャン第3次 (E21–E25) + 四半期モダリティ棚卸し — 2026-08-14

**位置づけ**: [[edge-development-pipeline-2026-07-18]] §4 月次 cadence の第3回 (registry `edge-supply-scan-monthly`、期日 2026-08-18 を 4 日前倒し)。
3 回に 1 回の**四半期モダリティ棚卸し**を同乗 (§3)。
**前回**: [[external-hypothesis-scan-2026-07-13]] (E1-E6) / [[external-hypothesis-scan-round2-2026-07-18]] (E7-E19)。

**起動理由 (期日前倒し)**: WIP 原則 §3「常時 ≥2 仮説が S1〜S4 に存在」は名目上 3 系統で充足しているが、**実態は 5 系統すべてが calendar-lock 待ちで探索アクティブ枠 = 0/3** (台帳 #21 クローズ 2026-08-05 以降 9 日間ゼロ)。「待ちしかない」状態は WIP 原則が防ごうとしている状態そのものと判定し、期日を待たず起動した (R3)。

---

## 1. データ入手性 re-check (全て本セッションで一次実測)

月次スキャンの中核は文献ではなく**入手性の再確認** — 入手性は時間で変わり、**今回は 2 件が悪化・1 件が構造欠陥**だった。

| 資産 | 前回記録 | 本日実測 | 判定 |
|---|---|---|---|
| **E1 Myfxbook positioning** | 2026-07-15 credentials 待ち | `/api/positioning/status`: `source=myfxbook` / `configured=true` / `logged_in=true` / 13 ペア × 1,357-1,557 行 / stale 1,290s | ✅ **健全** — 評価窓 (08-13 開始) に間に合っている |
| **E12 CME 先物 1h volume** | 7 契約 capture 稼働 | registry freshness: 7/7 契約 fresh (14.8h) | ✅ 健全 |
| **FF calendar (E7)** | R4F import 完了 | verified:ff_calendar 5.1h | ✅ 健全 |
| **MASSIVE 15m 12y** | — | USD_JPY 314,181 行 / EUR_USD 316,901 行、右端 2026-08-14 | ✅ 健全 |
| **ZN=F 1h (round-4 conditional の発火条件)** | cache 延伸を前提 | **右端 2026-05-15 で停止、mtime 07-24** | ❌ **構造欠陥 → 本 PR で修復** (§1.1) |
| **EVZCLS (E9 VRP の無料 probe 系列)** | 4,530 行 (2007-11→2025-03、廃止済) | FRED 実 DL **4,529 行、右端 2025-03-11 で確定終了**。yfinance `^EVZ` も delisted (rows=0) | ⚠️ **悪化確定** — forward 経路は無料では存在しない (§2 E22) |
| **VXFXICLS** | — | 2,848 行、右端 **2022-02-11** で終了 | ❌ 代替にならない |
| **CME 無料 settlement scrape** | ToS 403 (MEMORY で再提案禁止) | 再確認せず (禁止事項) | ❌ 恒久クローズ |

### 1.1 ZN=F キャッシュの構造欠陥 (rule:R3、本 PR で修復済み)

`modules/yield_data.py:fetch_zn_intraday` は fetch 結果を **`df.to_parquet(cache_path)` で無条件 overwrite** していた。
yfinance の intraday 窓は rolling (1h=730d / sub-hour=60d) なので、**窓外に出たバーはキャッシュファイルにしか存在しない**。

実測した損害と回復:

| 項目 | 値 |
|---|---|
| 修復前キャッシュ | 12,760 行 / 2024-02-18 → **2026-05-15** |
| 本日 yfinance が返す 1h 窓 (period=730d) | 13,663 行 / **2024-03-21** → 2026-08-14 |
| **ファイル固有 (再取得不能) の区間** | **2024-02-18 → 2024-03-21** (約 1 ヶ月) |
| 旧コードが 1h で選んでいた period | **`60d`** (1,162 行) — 実行すれば 12,760 行を 1,162 行で上書き |
| 修復後 (union-merge で実行) | **14,175 行 / 2024-02-18 → 2026-08-14** (+1,415 行、左端保持) |

**二重の帰結**:
1. **データ損失ハザード** — 誰かが `fetch_zn_intraday(interval="1h")` を一度呼べば歴史が消える。MEMORY「MASSIVE 歴史バーは drift する = 凍結はファイル実体 + sha256 で」と同型の罠。
2. **registry トリガの構造的到達不能** — `ws3-round4-eur-divergence-conditional` の発火条件は「cache が 2026-11-15+ まで延伸」。キャッシュを伸ばす経路が存在しなかったため、このトリガは**永久に watching のまま**だった。伸長を担う定期ジョブも存在しなかった。

**修復**: `merge_bar_cache()` を新設し union-merge (重複は fresh 採用 / 行数単調非減少) に変更 + 1h の period を 730d へ。不変条件は `tests/test_yield_data_cache_merge.py` (7 tests) で pin。
**伸長経路**: `.github/workflows/zn-cache-refresh.yml` (週次 UTC 月 06:40、cc-g0-rt.yml と同一の PAT bypass) を新設。これで round-4 conditional は 2026-11-15 到達で実際に発火しうる状態になった。

**教訓 (lessons へ)**: **rolling 窓のベンダー API を叩くキャッシュは union-merge が既定であるべき。overwrite 実装は「取得できる期間 = 保有できる期間」と暗黙に仮定しており、その仮定は rolling API では常に偽。** さらに、**「条件付き registry トリガを登録したら、その条件に到達する経路が実在するかを同時に検査する」** — 到達経路のない条件は監視ではなく飾りである。

---

## 2. 新規/再裁定候補 (C1-C6、round-2 と同一 hard constraints)

| # | 仮説 (lens) | C1 データ | C2 falsified 除外 | C3 非重複 | C4 摩擦生存 | C5 反curve-fit | C6 revealed-edge | 判定 |
|---|---|---|---|---|---|---|---|---|
| **E21** | **human_signal_stream — user 手動トレード実績の帰属分解** (revealed) | ✅ OANDA transaction API 経路実在・実運用中 (`list_transactions` / `get_transactions_id_range`、`tools/transactions_shadow_drift_audit.py` が使用)。財務取引 (financing/swap) も同 API。**標本量は未計測 = S2 の最初の測定項目** | ✅ zz pivot×線目処 FAIL (2026-08-12) が殺したのは**テクニカル手法の estimand**。本候補は user 明言 (2026-08-12)「優位の正体は USD_JPY 長期キャリー」に対する**会計分解**であり別 estimand | ✅ システム対応物 carry_dip v3 は稼働中だが、それは**仮説の実装**であって**実績の帰属**ではない | △ 長期保有ゆえ摩擦は償却されるが、**収益源が swap なら 15m-daily 帳簿とは別カテゴリ** = M2/M3 への直接寄与は小さい (正直に前置) | ✅ **最強** — arXiv 2302.01010 の 4 分解 (FX rate / rate change / carry-time / residual) は**会計恒等式**で探索自由度が構造的にほぼゼロ | ✅ user 実績そのものが revealed edge | **採用 — ただし「供給ライン」ではなく S2 診断枠** (下記) |
| **E22** | **fx_variance_risk_premium (E9 の入手性 re-裁定)** (vol) | ⚠️ **explore+OOS は無料で完結可** (EVZCLS 4,529 行 2007-11→2025-03 × MASSIVE 12y)。**forward は無料経路ゼロ** (EVZCLS 廃止確定 / ^EVZ delisted / CME scrape は ToS 禁止 / Databento は有償) | ✅ オプション市場価格 = 価格モダリティ 3 周 FAIL の外側。E20 (金利差) とも変数が別 | ✅ E1/E7/E12 と独立データ源 | △ daily 頻度・hold 数日〜。文献 (Della Corte 2016 / Macrosynergy) の主張は EM 中心 — G10 での減衰は pre-reg で正面から扱う | ✅ 単一指標 (IV−RV) simple-first | — 中立 | **条件付き採用 — explore 枠の第一候補。ただし §2.1 の事前コミット節が必須** |
| E23 | central_bank_statement_text differential (event/text) | ✅ 中銀声明は公開。IMF WP 2025 が 169 中銀 / 74,882 文書のデータセットを提示 | ⚠️ **E7 (指標サプライズ) と同一 family の疑い** — wave-6 の THA/Thales 裁定で「08-28 後に新 family として再評価可」と既に処分済み | ⚠️ E7 verdict 前は判定不能 | ✅ 声明時の変動は摩擦を大きく超える | △ テキスト特徴量は自由度が大きく、pre-reg で語彙・スコアを事前凍結しないと curve-fit 温床 | — | **保留 — 08-28 (E7 verdict) までゲート。前倒し起案は multiplicity 二重取り** |
| E24 | global_currency_volatility_risk (vol) | ❌ 17 通貨 OTC IV パネルは有償のみ (round-2 と不変) | ✅ | △ E22 と近接 | ❌ **2026 年新研究が「予測力は 3 ヶ月超の horizon」と再確認** — 当プロジェクトの帳簿 (15m-daily) と構造的に不整合 | — | — | **棄却 — round-2 の E17 棄却を新証拠が補強。再提案禁止** |
| E25 | synthetic FX vol surface (yfinance 由来の RR/BF 推定) (vol) | ✅ 無料・キー不要と称する実装が存在 | ❌ **推定値は Yahoo Finance の価格系列から導出** = 実質 realized vol の変換 → **価格モダリティ 3 周 FAIL の再着せ替え**。E13 (BVC tick volume) 棄却と同型 | ❌ | — | — | — | **棄却 (C2+C3 の二重 FAIL)。E22 の代替として提案し直すことを禁止** |

### 2.1 E22 に必須の事前コミット節 (explore 枠を使う条件)

E22 は **verdict までは完全無料**だが、**PASS しても無料の forward データが存在しない**。この非対称を pre-reg 起案前に on-record 化する:

- explore 窓 2014-01→2021-12 / OOS 窓 2022-01→**2025-03-11** (EVZCLS 終端)。OOS は候補凍結後 1 回のみ接触 — 既存規約どおり。
- **PASS 時の帰結を先に凍結**: PASS は「live 実装の承認」ではなく「**有償データ (Databento) 調達の user 決裁点**」に到達したことのみを意味する。user が調達しない判断をした場合、E22 は PASS のまま **implementable でない**として棚上げし、**その事実をもって設計を緩める再訴訟を禁止**する。
- **FAIL 時の帰結**: vol モダリティを (E24/E25 の棄却と合わせて) 恒久クローズ扱いにでき、探索空間が確定的に縮む。
- **期待値の正直な見積り**: 当プロジェクトの explore→OOS 生存率は現時点で **0/15 系統**。よって「有償決裁点に到達する」確率は低く、**無料で vol モダリティに白黒をつけられること自体が主たる価値**。この非対称 (コストほぼゼロ / 情報価値は高い) が、forward 経路が閉じているにもかかわらず枠を使う正当化である。

### 2.2 E21 の estimand とスコープ制限 (誤用防止)

- **estimand**: user 手動 USD_JPY ポジションの実現 PnL を **(a) financing/swap 累計 (b) 保有期間の spot ドリフト (β) (c) エントリー/エグジット・タイミングの残差 (α) (d) サイズ変更の寄与** に分解する会計。**WR / N≥30 の勝率統計ではない** (MEMORY `user_manual_edge_usdjpy_carry_2026_08_12` の明示指示)。
- **供給ラインとして数えない**: α≈0 が結論でも、それは「新エッジ供給ゼロ」であって失敗ではない — **human-signal-stream 系統を恒久クローズでき、探索空間が縮む**という情報価値がある。α>0 なら初めて新 family の起点になる。
- **M2/M3 寄与の前置**: 無レバ carry は +0.3-0.4%/月 規模で、月次目標に届かせるには ~25x レバ = unwind 即死 (MEMORY 既算)。したがって **E21 の PASS はバラスト用途の確認であり、目標達成の主経路ではない**。この前置を pre-reg にも複写する。
- **live 無関係**: 読み取り専用。tier/lot/live は一切触らない。

---

## 3. 四半期モダリティ棚卸し (3 回に 1 回、今回が初回)

「閉鎖」判定の前提が崩れていないかの再確認。**前提が崩れたものはゼロ**、逆に 1 件が補強された。

| モダリティ | 閉鎖根拠 | 前提は今も有効か |
|---|---|---|
| 価格/OHLCV 内部 + cross-asset lead-lag | 3 周 FAIL + Mesfin 2026 外部 falsification | ✅ 有効 (新反証なし) |
| 水平線/平行線/斜め TL/ラウンドナンバー (wave-4) | 5 候補全滅 (KILL 3 + explore FAIL 2) | ✅ 有効。zz pivot×線目処 FAIL (08-12) が**さらに補強** |
| 週次 COT (level / Δ / commercial) | #5 + #16、鏡像恒等 0.93 で実質 1 モダリティと実証 | ✅ 有効 |
| BBO スプレッド状態 | #17 FAIL、全変種 ban | ✅ 有効 |
| 祝日/休場フラグ × D1-D2 | #15 explore PASS → OOS 崩壊 | ✅ 有効 |
| 月末リバランス (無条件 + 条件付き) | WMR-fix REJECT + #6 FAIL | ✅ 有効 |
| VIX レベル × JPY クロス short 1-5d | #7 knife-edge kill (p=0.050091) | ✅ 有効 (ban 例外は user 決裁事項のまま) |
| PPP 実質為替 / slow location-anchor MR | #14 + #21 ほか「方向は合うが弱い」死型 4 例 | ✅ 有効 |
| tick volume (E2/E13) | 弱 proxy、E12 が上位互換 | ✅ 有効。**E25 (synthetic vol surface) が同型で本日棄却** |
| 無条件イベント窓 (E15) | phase-0 FAIL 0/6 | ✅ 有効 |
| 金利差 carry-rank / mom63 (E20) | S2 棄却 | ✅ 有効。**user 明言 (08-12) で USD_JPY は例外的に正 = E20 自身の記録と整合** |
| **17 通貨 global vol risk (E17)** | round-2 で horizon 不整合により棄却 | ✅ **強化** — 2026 年新研究が「3 ヶ月超 horizon」と再確認 |

**棚卸しの結論**: 閉鎖判定の巻き戻しはゼロ。**生存モダリティは (a) イベントサプライズ E7 (b) 実約定フロー E12 (c) 非価格 sentiment E1 (d) equity-curve gating #22 (e) オプション IV E22 (f) 実績帰属 E21 — の 6 系統のみ**。うち (a)-(d) は calendar-lock 待ちで作業不能、**能動的に動かせるのは (e)(f) の 2 系統だけ**である。

---

## 4. 裁定サマリと次アクション

**裁定**: 採用 2 (E21 診断枠 / E22 explore 枠・条件付き)、保留 1 (E23、08-28 ゲート)、棄却 2 (E24 / E25)。

**推奨する枠配置** (モダリティ分散を満たす):
1. **E22 (VRP) を explore アクティブ枠 1/3 へ** — §2.1 の事前コミット節を pre-reg に内蔵させた上で S2 (R3 診断、`tools/rapid_edge_probe.py` 経路) から起動。無料で vol モダリティに白黒がつく。
2. **E21 (帰属分解) を並行 S2 診断へ** — OANDA transaction API で標本量の実測から。§2.2 のスコープ制限を複写。
3. **E23 は 08-28 まで着手禁止** (E7 verdict の multiplicity 二重取りを避ける)。

**本 PR で執行済み**: §1.1 の ZN=F 構造欠陥修復 (union-merge + 週次リフレッシュ workflow + test pin 7 件) とキャッシュ回復 (12,760→14,175 行)。

**live への影響**: ゼロ。本スキャンは live/tier/lot/Kelly を一切変更しない。

**registry 更新**:
- `edge-supply-scan-monthly`: deadline 2026-08-18 → **2026-09-18** (第4次、四半期棚卸しは第6次に同乗)
- `ws3-round4-eur-divergence-conditional`: 到達経路が実在しなかった旨と修復を message へ追記

---

## 参考文献 (本セッションで実在確認)

- Performance attribution with respect to interest rates, FX, carry, and residual market risks — arXiv 2302.01010 (E21 の 4 分解の骨子)
- Global currency volatility risk and currency return predictability — ScienceDirect S0927539826000551 (E24 棄却の補強、horizon >3ヶ月)
- From Text to Quantified Insights: A Large-Scale LLM Analysis of Central Bank Communication — IMF WP 2025/109 (E23 のデータ実在根拠)
- Information in central bank sentiment: An analysis of Fed and ECB communication — ScienceDirect S104244312600051X (E23)
- Volatility risk premia and exchange rate predictability — Della Corte et al., JFE 2016 (E22 の基礎文献、round-2 から継続)
