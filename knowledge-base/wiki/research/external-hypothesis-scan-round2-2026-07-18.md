# 外部仮説スキャン第2次 (E7–E19) — E1 FAIL 時の後継供給ライン裁定 2026-07-18

検証方針: 前回スキャン ([[external-hypothesis-scan-2026-07-13]]) と同一の hard constraints C1–C6。データ実在主張は本セッションで一次確認済み (敵対的検査: EPSOFT CSV 実取得 / faireconomy JSON 実 fetch / FRED EVZCLS 4,530行 DL / yfinance 6E=F 1h 13,733 bars 実測 / Databento $125 credit 原文確認 / Lee & Wang RAPS 2025 実在確認 / FOMC calendar 200 + FRED release/dates endpoint 実在)。

| # | 仮説 (lens) | C1 データ | C2 falsified除外 | C3 非重複 | C4 摩擦生存 | C5 反curve-fit | C6 revealed-edge整合 | 判定 |
|---|---|---|---|---|---|---|---|---|
| **E7** | **event-surprise directional** — 指標サプライズ z 化 × 発表後 5–15min entry × 1h–24h hold (event) | ✅ FF パネル 19y 分単位 (EPSOFT 実取得で列構成確認) + faireconomy go-forward (実 fetch、**Actual なし→補完 ingest 要**)。2023-04〜現在 ~170週の gap scrape は工数のみ | ✅ 外生イベント時刻+コンセンサス乖離 = 価格外情報の条件付け。Mesfin 2026 (無条件 OHLCV falsification) と非矛盾 | ✅ イベント戦略ゼロ (tokyo_nakane は時刻固定・サプライズ非条件、grep 確認済との記載を KB 側でも整合確認)。E1 positioning と直交 | ✅ イベント時変動 数十–150p >> 2–4.5p、スプレッド収縮 30s–2min 後 entry で死圏回避、既存 Spread/SL Gate がそのまま執行ガード | ✅ 単一変数 (z-surprise 符号)。ただし horizon×指標クラス×pair の discovery は BH-FDR pre-reg 必須 (WS3 round-1/2 同一方法論) | ✅ イベントは流動性 sweep を誘発 — trendline_sweep の斜めTL流動性仮説と整合的 | **採用 — 本命 (E15 と同一 pre-reg family で phase-1)** |
| E8 | pre-announcement drift — 発表前 30–120min のサプライズ方向ドリフト追随 (event) | ✅ E7 と同一 | ✅ | ✅ | ❌ **構造的衝突**: エッジ存在窓 = 発表直前のスプレッド拡大窓そのもの。動的デスゾーン検出が entry を正しくブロックする時間帯 | △ | — | **棄却 (C4 構造 FAIL + 2015年公刊で減衰濃厚 + 先物→FX現物外挿未確認)** |
| E9 | 通貨 VRP contrarian (IV−RV) — CME オプション settlement 自前 IV パネル (vol) | ✅ 無料 probe: EVZCLS 4,530営業日 実DL 確認 (2007-11→2025-03、廃止済) × MASSIVE 12y。深化: Databento $125 credit (原文確認、**6ヶ月失効**)。live forward は CME settlement scrape (無料、要今から蓄積) | ✅ オプション市場価格 = 価格モダリティ 3周 FAIL の外 | ✅ E1/E3 と独立データ源 | △ daily 頻度・hold 数日〜 = 帳簿上限側。摩擦は horizon で償却可だが要検証 (Della Corte 2016 は月次リバランス) | ✅ 単一指標 simple-first | — 中立 | **条件付き採用 — 第2線。無料 probe (EVZCLS×EURUSD) を先行、IC 正なら Databento クレジット消費** |
| E10 | 25Δ RR skew — crash-risk ゲート (vol) | ✅ E9 相乗り (追加コストゼロ)、OTM settlement 復元誤差は未検証 | ✅ | ✅ | — (ゲート用途) | △ | ❌ **文献上の実態は方向エッジでなく防御ゲート = 4原則「防御フィルタ積み上げ<攻め」と緊張** | **保留 — 単独供給ラインにならず。E9 採択時の secondary としてのみ** |
| E11 | ATM IV→実現レンジ予測 — barrier/size conditioning (vol) | ✅ E9 と同一の無料 probe 経路 | ✅ | ✅ | — (方向でなくレンジ) | ✅ | — | **保留 — 新規エッジ供給でなく既存セル conditioning、M3 寄与は間接。E9 probe の副産物として IC だけ測る** |
| **E12** | **CME FX 先物実約定 volume flow proxy** — unsigned abnormal volume primary / BVC-signed secondary × spot 15m–1h (flow) | ✅ **本セッション再実測**: yfinance 6E=F/6J=F 1h = 13,733–13,735 bars (2024-02-23→2026-07-17)、非ゼロ volume 96.5% = 「今 2y + 今から蓄積」両充足。**730d rolling = 蓄積開始しないと歴史が延びない**。日足 volume 列は壊 (1h 必須) | ✅ 取引所実約定 volume = falsified 6系統+3周が未使用の新モダリティ。COT weekly とは変数/頻度/母集団の三点で別 | ✅ | △ 要検証 — pre-reg で価格 momentum 単体に対する**増分 IC を必須検定** (BVC sign は価格由来のため) | ✅ unsigned primary / signed secondary の分離設計が candidate 自身に内蔵 | — 中立 | **採用 — 第2モダリティ。E7/E15 と並走可、インフラ即開始 (infra 参照)** |
| E13 | BVC × MASSIVE tick volume 12y (flow) | ✅ in-house 追加コストゼロ | ❌ **grey**: BVC sign = 価格変化そのもの → 実質 volume 加重 momentum で price-modality 3周 FAIL と距離が近い | ✅ | △ | △ | — | **棄却 — E2 棄却理由「tick volume は弱 proxy」を覆す新証拠なし (相関 0.85–0.9 は非学術一次)。E12 が上位互換** |
| E14 | CME 日次 volume/OI regime フィルタ (flow) | △ volume 2y 再構築可 / **OI は無料経路で歴史ゼロ = 今から蓄積のみ、verdict 最低 1y 先** (E1 と同じ構造的弱点) | △ COT「先物建玉」ファミリーと境界曖昧 | △ | — (単独エッジでない) | ✅ | — | **保留 — 供給ラインとして非自立。OI 日次 capture だけ E9 settlement scrape に相乗りで低コスト開始 (infra 参照)** |
| **E15** | **FOMC/NFP/CPI イベント窓プレミア/リバーサル** — post-FOMC 12–24h fade 等 (fresh) | ✅ **今すぐ BT 可**: MASSIVE 12y×13ペア 15m (in-house) + FOMC calendar (HTTP 200 確認、14:00 ET 固定) + FRED release/dates (endpoint 実在確認、無料キーのみ)。~380 イベント×13ペア。**蓄積待ちゼロ = E1 first look (2026-10-15) より先に verdict を出せる唯一の候補** | ✅ イベントカレンダー条件付け = 未検証領域。T11 (LDN朝×counter-USD) とは条件付け変数が別 (pre-reg で明示)、WMR fix REJECT とはイベント種が別 | ✅ E1 と完全非重複 | ✅ Lee & Wang RAPS 2025 実在確認 (65% 反転 / 12–24h)。イベント後 vol >> 摩擦、発表直後死圏は 12–24h horizon で回避 | ✅ イベント種 3 × 方向 2 × horizon 少数の小さい探索空間。E7 と**同一 pre-reg family に統合し multiplicity 二重取りを禁止** | ✅ | **採用 — 最優先着手 (phase-0)。round-4 discovery として即 pre-reg 可** |
| E16 | メディアトーン currency factor (fresh) | ❌ 論文データ proprietary 明言、GDELT 代替は未検証の別仮説 | ✅ | ✅ | ❌ horizon 6ヶ月 = 15m–daily 帳簿と不整合 | — | — | **棄却 (C1+時間軸の二重 FAIL)** |
| E17 | global currency volatility risk (fresh) | ❌ 17通貨 OTC IV パネル有償のみ。RV 版は OHLCV 派生 | ❌ RV 構成は価格モダリティ再試行の疑い | △ | ❌ 予測力 horizon 3ヶ月超 | — | — | **棄却** |
| E18 | currency factor timing ML (fresh) | ❌ forward rates 必要 = E5 と同型で不能、月次 | ✅ | △ | ❌ 月次 | ❌ ML ensemble 原則棄却 (E6 同型) | — | **棄却** |
| E19 | LOB cross-currency 予測 (fresh) | ❌ FX スポット LOB は EBS/LSEG 有償のみ、蓄積しても LOB 粒度に届かない | ❌ cross-currency 予測は E4 lead-lag 閉鎖 (2026-07-13 実証) と重複 | ❌ | — | — | — | **棄却 (データ・重複の二重 FAIL)** |

**裁定サマリ**: 採用 3 (E15 phase-0 / E7 phase-1 / E12 並走)、条件付き採用 1 (E9)、保留 3 (E10/E11/E14)、棄却 6 (E8/E13/E16/E17/E18/E19)。イベントモダリティ (E15+E7) と実約定フローモダリティ (E12) の 2 系統が、前回スキャンの結論「供給は新データモダリティからしか来ない」に対する具体的な後継ライン。

---

## 統合推奨 (top recommendation)

E15 (FOMC/NFP/CPI イベント窓プレミア) を phase-0 として即着手し、E7 (指標サプライズ条件付き directional) を phase-1 とする「イベントモダリティ・プログラム」を単一 pre-reg family で起案するのが最短経路。根拠: (1) E15 は in-house MASSIVE 12y + 無料カレンダー (FOMC ページ 200 / FRED release/dates 実在を本セッション確認) だけで今日から BT 可能 — 全候補中唯一、E1 first look (2026-10-15) より前に verdict を出せる。E1 FAIL 時の空白期間をゼロにできる。(2) E7 は EPSOFT 19y 分単位パネル (実取得検証済) で discovery 深度が最大、文献も Lee & Wang RAPS 2025 (実在確認、post-FOMC 65% 反転 12–24h) で現行。(3) 両者は同一モダリティなので pre-reg を分割すると multiplicity の二重取りになる — WS3 round-1/2 と同一方法論 (discovery diagnostic → 候補固定 → clean OOS、BH-FDR + first-touch EV + ナイフエッジ3点) で family 統合すること。並走で E12 (CME 先物実約定 volume flow) を第2モダリティとしてインフラだけ即開始 (下記)。E9 (VRP) は EVZCLS×EURUSD の無料 IC probe を先に走らせ、正なら Databento クレジット消費 — クレジット 6ヶ月失効のため probe は 2026-Q4 までに判定。

## 今から始めないと不可逆なインフラ (infra_needed_now)

E1 型「history は今からしか貯まらない」が 3 件あり、着手遅延 = verdict 後ろ倒しに直結する。(1) **[最優先] ForexFactory Actual 補完 ingest**: faireconomy 週次 JSON (実 fetch 確認) には forecast/previous/impact はあるが **Actual フィールドが無い** — 発表後の Actual を FF 再 scrape または翌期 previous 逆引きで週次 capture する軽量 job を今から回さないと、E7 の clean OOS 区間 (go-forward 蓄積分) が永遠に始まらない。歴史側 19y (EPSOFT、2023-03 まで) は取得済み経路なので、2023-04〜現在の gap ~170 週の一括 scrape も同 job に含める (一回きりの工数)。(2) **CME FX 先物 1h volume の永続 capture**: yfinance 60m は **730d rolling 窓** (本セッション実測: 2024-02-23 が現在の左端) — 今取れる 2y は毎日 1 日ずつ消えていく。週次で 1h バーを SQLite に追記する capture を今開始すれば、E12 の検証歴史が 2y から単調に延伸する。放置すると 2y 固定のまま。(3) **CME オプション settlement / OI の日次 scrape**: CME 無料 settlement は ~7 日窓のみ — E9 (VRP) / E10 (RR) / E14 (OI) の forward データは今から貯める以外に無料経路がない。1 本の日次 scrape job で ATM IV・25Δ・OI を同時 capture でき、3 候補のインフラが相乗りになる。なお Databento $125 無料クレジットは**サインアップ後 6 ヶ月失効**のため、E9 probe (EVZCLS×MASSIVE、無料・即可) の結果を見てからサインアップする順序が正しい (先に登録するとクレジット時計だけ進む)。いずれも read-only snapshot で live 無関係 = Rule 外のデータ基盤投資、E1 positioning ingest (2026-07-14 GO 済) と同じ決裁枠。

---

## 本スキャンの位置づけ

- 実行: 2026-07-18、[[edge-development-pipeline-2026-07-18]] §4 月次 cadence の初回 (E1 FAIL 時の後継準備、WIP 原則の充足)
- 手法: 4 レンズ並列調査 (event/vol/flow/新文献) → C1-C6 統合裁定 + 敵対的データ実在検査 (5-agent workflow)。データ実在は全て一次確認 (実 fetch/実 DL/bars 実測)
- 前回: [[external-hypothesis-scan-2026-07-13]] (E1-E6)。本スキャンで E7-E19 を裁定
- **次アクション**: (1) E15+E7 イベントモダリティ・プログラムの pre-reg 起案 (round-1/2 同一方法論、単一 family) (2) インフラ 3 件の ingest job 実装 (R3、E1 positioning ingest と同じ決裁枠) (3) E9 は EVZCLS×EURUSD 無料 probe 先行 (Databento サインアップはその後 — クレジット 6 ヶ月失効のため)
