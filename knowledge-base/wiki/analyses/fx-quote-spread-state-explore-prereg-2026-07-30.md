# fx_quote_spread_state 凍結探索プロトコル — 単独 wave (2026-07-30)

**性格**: 観測前プロトコル凍結 (explore 段階 + PASS 時 OOS 単一接触ルール込み)。tier action なし、
live 変更なし (デスゾーン防御 gate には一切触れない)。台帳 **#17** 執行 (**単独 family、m=1** —
wave-1 教訓の分母規律 + wave-3 実行順序指定どおり W3-1 (#16 FAIL クローズ) verdict 後の単独 wave)。
**敵対的検証**: GO-WITH-CONDITIONS (`raw/analysis/wave3-adversarial-verification-2026-07-29.md`
[W3-2]) — **LOCK 前 6 条件を本ドキュメントで全て解決してから凍結** (§条件解決)。
**メカニズム**: スプレッド急拡大 (同スロット trailing baseline 対比の異常オンセット、時計条件でなく
異常条件) = ディーラーのリスク退避・流動性退出。live 側では本プロジェクト自身が「デスゾーン =
スプレッド異常」として防御に使う実証済み状態変数だが、エッジ (事後の方向構造) としては未検証。
**prior は正直に low (composite 48、headroom 35 が最弱)** — FRICTION-KILL / POWER-BLOCKED /
FAIL いずれも healthy kill として記録する前提で登録。

---

## 条件解決 (敵対的検証 [W3-2] 6 条件)

1. **イベント条件付き摩擦 headroom gate を forward return 非接触で先行実施** ✅ —
   ハーネス `tools/fx_quote_spread_explore.py` を stage 分離 (`--stage headroom` は forward
   return 系列 (`build_return_grid`) を一切呼ばないコードパス)。RT_event = KB_RT − KB_spread +
   r_entry × KB_spread (実測 BBO の相対 elevation r_entry = entry spread / onset 時 baseline を、
   配備先 (OANDA) のベース摩擦へ乗法変換 — baseline RT 直用ではない)。分子 = entry 時点の後方
   trailing 同スロット 60 営業日 median |24h move| (forward 非接触)。gate: per-pair median ≥ 10 ∧
   pooled median ≥ 10、不通過ペアは除外 (ex-ante 宣言)、生存 <2 ペアで family kill。
   **実測結果 (2026-07-30、fwd return 未接触で執行): PASS** — EUR_USD 19.27× (n=28) /
   GBP_USD 10.73× (n=27、ゲート至近) / USD_JPY 14.09× (n=10)、pooled median 13.5×、
   usable N=65 (正常化不能 drop 4)。反実仮想 onset-entry RT = 7.25 / 9.47 / 5.87p (正常化 entry の
   約 2-3 倍) — デスゾーン防御の定量的正当化を副産物として実証
2. **配備経路ブロッカー解消** ✅ — entry を「スプレッド正常化後の最初の有効サンプル」に凍結
   (spread ≤ 1.5 × onset 時点の同スロット baseline、onset 後 16 サンプル ≈ 48h 以内。未正常化
   イベントは drop + 件数開示)。デスゾーン live gate はスプレッド異常時の執行をブロックするため、
   正常化後 entry は PASS 時配備形とそのまま同型 (追加の live 変更なしで配備可能な形)。onset 時点
   entry の反実仮想 RT は診断で開示 (上記)
3. **feed QA 観測前凍結** ✅ — (a) 土曜行: グリッド生成側で閉場窓 (金 15:00 NY 後〜日 18:00 NY 前)
   を構造的に排除 + ハーネス assert。(b) 同時刻複数 sample median 化: 各サンプル = [target,
   +30min] 窓内 quote (limit 200) の median (単一 quote 不使用)。(c) 異常持続 ≥2 連続サンプル:
   onset ratio ≥3.0 ∧ 次有効サンプル (6h 以内必須) ratio ≥2.0。(d) スプレッド上限 sanity:
   spread > mid の 0.5% は invalid。加えて crossed/locked quote (spread≤0、2019 年 probe 実測
   43%) は spread 統計から除外 + share 90% 超サンプル invalid、bid/ask ≤ 0 除外、有効サンプル =
   窓内 ≥30 quotes ∧ 初 quote lag ≤ 15min。price_shock 監査 (MASSIVE 土曜行/不良プリント 4-12.8%
   汚染) の前科への直接対応
4. **DST 補正** ✅ — サンプリンググリッドを **America/New_York ローカル固定 8 スロット/日**
   (18,21,0,3,6,9,12,15 時) に凍結 = ローカル時刻基準を採択 (NY セッション diurnal と 17:00 NY
   ロールオーバーが年間同一スロットに整列)。残余の EU/US DST 不整合窓 (~3 週/年) は
   **不整合日のオンセットを除外** (Europe/London vs America/New_York の DST 状態比較、機械判定)
5. **probe 未検証の解消 + coverage assert** ✅ — /v3/quotes を probe で実在確認 (7 点全 HTTP 200、
   fields = bid_price/ask_price/participant_timestamp、密度 200 quotes/12-306s、土曜クエリは偽行を
   返さず次開場へスキップ)。**feed 構造変化を実測**: 2014 は ~2.3p 固定スプレッド様式 (diurnal
   変動僅少、年 max 3.9p) / 2019+ は sub-pip + crossed 混入 → QA (c)(d) + 比率ベース設計 +
   絶対 elevation floor で吸収。**年次 coverage assert (凍結、事後緩和禁止)**: pair×年 valid
   share ≥ 0.80、explore 8 年中 skip 許容 ≤1 年/pair、不通過 pair は除外、生存 <2 pair で
   **data-blocked クローズ**。**実測: 全 3 ペア × 全 8 年 PASS (最低 USD_JPY 2020 = 0.888)、
   skip ゼロ** (fetch 実績 78,000 サンプル / valid 97.97% / empty 0 / 通信失敗 0)
6. **primary 1 本** ✅ — **fwd 24h (同 NY スロット翌営業日) の 1 本のみ** (4h はグリッド 3h で
   正確に取れず、正常化待ち後の残余も乏しいため不採用 — ex-ante 理由明記)。年末薄商い (12/15–1/5)
   重複 share は gate (vi) (≤50%) + 診断で開示

## 凍結事項 (ハーネス定数と同値、grid なし)

- **データ**: `data/external/quote_spread/{PAIR}_{YYYY}.parquet` (MASSIVE /v3/quotes サンプリング、
  NY ローカル 8 スロット/日 × limit 200、warmup 2013-10-01〜)。ペア = **EUR_USD / GBP_USD /
  USD_JPY** (最深流動性 + KB RT 凍結値保有)。fetch はデータ獲得で look 非該当
- **イベント (単一凍結構成)**: onset = spread_med ≥ **3.0×** 同スロット trailing 60 有効サンプル
  median (min 40、shift(1) で自サンプル除外) ∧ 絶対 elevation ≥ **1.0 pip** (sub-pip feed 期の
  擬似比率対策) ∧ 同時 |Δlog mid| ≤ **2.0×** 同スロット trailing median (**price_shock live 5 席
  との分離条件**) ∧ 持続 (次有効サンプル ≤6h で ratio ≥2.0)。dedup 24h (8 サンプル)。DST 不整合日
  除外。**entry** = onset 後 ≤16 サンプルで spread ≤ **1.5×** (onset 時点凍結 slot baseline) の
  最初の有効サンプル
- **方向規約 (凍結)**: **short-pair pooled (risk-off +)** — EUR_USD/GBP_USD/USD_JPY とも
  ペア価格下落方向を + とする (流動性退出 → flight-to-quality の prior。two-sided 検定なので
  規約は pooling の符号整列にのみ作用)
- **primary test (m=1、α=0.05 両側)**: pooled mean **標準化 fwd 24h return** (ret_pips ÷ entry
  時点 trailing scale24)。null = **全ペア同時・営業日単位 circular shift** (イベント位置を一様
  ランダム k 営業日シフト、リターン grid 固定、10,000 回、seed 20260729、配置 ≥80% 必須)。
  クラスタリング/自己相関/ペア間同時性を保存
- **必須合格条件 (すべて、機械適用)**:
  - (i) primary 両側 p < 0.05
  - (ii) magnitude coherence: peak ratio tercile 3 分位すべての mean が pooled と同符号
  - (iii) 集中ガード: LOYO (イベント保有年) 全て符号不変 ∧ 単一年 |寄与| share ≤50% ∧
    最大単一イベント除外で符号不変 ∧ SNB 窓 (2015-01 onset) 除外で符号不変
  - (iv) cross-pair coherence: leave-one-pair-out 全て符号不変 ∧ ≥2/3 ペア mean 同符号
  - (v) 実現 headroom: median |realized 24h move| ≥ 10 × median RT_event (事前ゲートの実現側検証)
  - (vi) 年末薄商い: 12/15–1/5 のイベント share ≤ 50%
  - **最小 N**: 測定可能イベント ≥ **30** — 未達は POWER-BLOCKED クローズ (閾値の事後調整禁止)
- **窓**: explore = onset **2014-01-01〜2021-12-31** (パネル cutoff 2022-01-31 は exit バッファ、
  OOS 域の onset には非接触)。**OOS = 2022-01-01〜2026-06-30、PASS 時のみ単一接触**
- **kill rule**: いずれか不成立 → **family FAIL クローズ、OOS 未接触保存**、台帳 verdict 記録。
  **同型再試行禁止スコープ = 「実測 BBO スプレッド状態 (異常オンセット/レベル/正常化) × 時間固定
  ホライズン fwd 方向」全変種** (閾値・持続定義・ホライズン・ペア・feed の別を問わない)。
  デスゾーン防御 (live gate) は本 verdict の影響を受けない (防御用途の正当性は独立)
- **knife-edge**: p ∈ (0.025, 0.10) なら 3 点検査 (LOYO 済 / null を slot-shift 変種で再実行 /
  seed 変更) 全通過で初めて PASS
- **OOS (PASS 時のみ)**: 同一定義・同一統計、explore 符号に固定した片側 α=0.05、gates (ii)-(vi)
  同一適用 (LOYO は 2022-2026)。**OOS PASS → R1 パケット起案で停止** (live 実装なし、user 最終
  承認まで)
- **診断 (選択に使わない)**: per-pair mean / 年次分布 / raw pips mean / fwd 48h (参考) /
  正常化不能 drop 件数 / r_onset 反実仮想 RT / crossed share / DST 除外件数 / 年末 share /
  swap 上限バウンド (1 晩 rollover ≤ ~1.3p (2019 EUR_USD 金利差 3% 相当)、両側規約でネット寄与は
  さらに小 — per-event join は行わず bound 開示)

## 隣接差分 (必須節)

- **session/hour バケット (REJECT `session-time-bias.md:97`)**: 同 REJECT は「毎日再帰する時計
  バケットの無条件ドリフト」。本 family は同時刻 baseline **対比の異常オンセット条件付け** =
  時計効果は構成で除去される (estimand 別)。サンプリング格子が時計なのは測定機構であって条件では
  ない
- **holiday ban (#15 FAIL、日次×カレンダー)**: 認可再挑戦経路「新モダリティ (intraday マイクロ
  ストラクチャ等) + 明示差分節」に該当 — 本 family は実測 BBO tick モダリティ (カレンダーフラグ
  不使用)
- **price_shock (live 5 席)**: |Δlog mid| ≤ 2× 同スロット median の分離条件で「大きな価格変動なき
  純粋な流動性退出」に限定 (shock 席と背反)
- **VIX onset kill (wave-1 #7)**: VIX 不使用
- **デスゾーン live gate**: 防御 (執行しない) 用途は本 explore と独立、live 変更ゼロ

## 事前宣言 — 期待の較正

composite 48 は wave-3 生成時から誠実。headroom gate は通過したが (13.5×)、GBP_USD は 10.73× と
ゲート至近であり、実現側 gate (v) で落ちる余地は残る。早期 feed (2014-2015) は固定スプレッド様式で
イベントが構造的に希薄 — 測定可能 N < 30 なら POWER-BLOCKED を正直に記録する。**探索 explore 通過
品質が OOS 生存を予測しない実例は既に 13 件** — PASS でも OOS 単一接触までは何も主張しない。

## 成果物

`tools/fx_quote_spread_fetch.py` / `tools/fx_quote_spread_explore.py` /
`data/external/quote_spread/*.parquet` /
`knowledge-base/raw/bt-results/fx-quote-spread-state-explore-2026-07-30.json` /
`reports/fx-quote-spread-state-explore-2026-07-30.md` / 台帳 #17 verdict 追記
