# 📝 Pre-registration DRAFT: weekend_gap family #3 — stage-2 執行設計 (rule:R1 step②)

> **⚠️ DRAFT — user 最終承認待ち (R1 step③)。live 変更なし。**
> 本文書は起案のみ — 実装・live パラメータ変更・LOCK 執行は一切行っていない。user 承認 (§7 オプション選択) 後に本文書を LOCKED 化して条項凍結 → 実装 PR (登録は deploy 担当) の順。承認が得られない場合、本 DRAFT は棚上げのまま live 変更ゼロ。

**起案日**: 2026-07-24
**Status**: 📝 **DRAFT** (user 決裁待ち)
**起点**: [[weekend-gap-oos-prereg-2026-07-24]] §11 verdict — **arm B PASS** (pooled {EUR_USD, USD_JPY, AUD_USD} 4h fade、stressed-net +9.04p、knife-edge 4/4 flip なし) → §9 R1 手続き (i) 完了 (`reports/sunday_open_spread-2026-07-24.md`: 実測 RT 置換後も EV +7.90p mean / +3.26p p90 tail で正 EV 保存) → 本文書 = 手続き (ii) 執行設計 pre-reg → 手続き (iii) user 最終承認
**様式**: [[weekend-gap-oos-prereg-2026-07-24]] 踏襲

---

## 0. 決裁サマリ (user 向け 3 行)

1. **何を**: OOS-PASS 済み weekend_gap fade (3 ペア pooled、日曜 open 成行 → +4h time-exit) を **固定 1000u (MIN lot)** で執行検証する。BT 期待値は実測摩擦込みで **+7.9p/イベント (tail p90 でも +3.3p)**、頻度 **~3.3 イベント/月**。
2. **いくら**: 月次期待 **+22〜26 pip ≈ +$2 前後** (1000u)。金額はノイズレベル — 目的は利益ではなく**本プロジェクト初の OOS-PASS 外部仮説エッジの前向き執行検証** (残存不確実性 = 薄い板の実 slippage は live でしか測れない)。
3. **決めてほしいこと**: §7 の (a) shadow-first / (b) 直接 live MIN lot / (c) 追加実測後再提示 / (d) 見送り — **起案者推奨は (b)** (R2 自動停止ゲート併設、テールリスク ~$15/イベント)。

## 1. 前提 — 確定済み事実 (本 DRAFT で再検証しない)

| 項目 | 値 | 出典 |
|---|---|---|
| OOS verdict | arm B PASS (N=177 / 112 週末、gross +15.60p、weekend-block p<1e-4、stressed-net +9.04p、knife-edge 4/4 維持) | [[weekend-gap-oos-prereg-2026-07-24]] §11 |
| 実測 RT 置換 (R1 step①) | pooled 初バー実測 RT: mean 7.70p / p50 6.65p / p90 12.34p → stressed-net **+7.90p / +8.95p / +3.26p** — 正 EV 保存 | `reports/sunday_open_spread-2026-07-24.md` §3 |
| spread 構造 | 二値構造: 21:04〜22:00 UTC は高原状 (4〜8p、decay なし、schedule cap EUR/JPY 10p・AUD 15p に張り付き)、**22:01 UTC に一段崩落**して通常圏。exit +4h は完全に通常スプレッド (1.3〜1.9p) | 同 §2 |
| entry 遅延変種の裁定 | 中間遅延 (15/30/45m) は無意味 (節約ゼロで初動のみ失う)。22:01 遅延は estimand 変更 = OOS 再検証不能 → 採用するなら前向き検証のみ | 同 §4 |
| 頻度 | OOS 実測 39.4 qualifying イベント/年 (= 3.28/月)、2.07 qualifying 週末/月、同一週末複数ペア分布 1:62 / 2:35 / 3:15 | OOS report §6 |
| AUD_USD RT 2.5p は理論仮置き | → 実測 1.8p で**保守的**と確認済み。qualify 閾値 (凍結ピップ値) の再計算は禁止のまま | spread report §1 |

## 2. 執行仕様 (凍結案 — 承認時にこのまま LOCK)

### 2.1 シグナル定義 (OOS estimand と同一 — 変更禁止)

| 項目 | 凍結値 | 根拠 |
|---|---|---|
| 対象ペア | **EUR_USD / USD_JPY / AUD_USD** のみ (GBP_USD は永久対象外 — 逆符号 family 用に OOS 清浄維持) | OOS arm B 定義 |
| Friday close 基準 | Fri **21:00 UTC** 固定境界前の最終 15m バー Close (≤6h guard)、**mid 価格** | stage-1 §2.1 (DST 感度検査済み、flip なし) |
| Sunday open 基準 | Sun **21:00 UTC** 以降の最初の complete バー Open (≤24h guard)、mid 価格。実測では OANDA 初 M1 バー = 夏 21:04 / 冬 22:04 UTC | 同上 |
| qualify | \|gap\| ≥ 凍結ピップ値: **EUR_USD 20.0p / USD_JPY 21.4p / AUD_USD 25.0p** (10× 通常 RT。2026 実測スプレッドでの再計算は定義ドリフト = 禁止) | stage-1 §2 |
| 方向 | **gap fade**: gap up (Sun open > Fri close) → SELL / gap down → BUY | OOS estimand |

### 2.2 entry (凍結案)

- **成行 @ Sunday open 初バー確定後の最初の評価 tick** (目標 21:05±2 分 / 冬 22:05±2 分)。**1 週末 1 ペア 1 回のみ、リトライなし** — スプレッド低下を待つ再試行は entry タイミングの条件付け = estimand 逸脱経路のため禁止。
- **発注時 spread cap (凍結): quoted spread > 10.0p → live 発注スキップ**。
  - **cap 根拠**: 実測初バー spread p90 ≈ 10p (EUR 9.89 / JPY 10.0 = OANDA schedule cap)。cap 境界 (10.0p) でも RT = 10.5p vs gross mean +15.6p → **+5.1p の正 EV マージン**。AUD の 15p schedule-cap 張り付き週末 (実測 2/12) を自動排除。
  - **超過時の扱い**: live 発注せず、**shadow row + 「未執行イベント」として DB/ログに記録** (`block_cause=weekend_gap_spread_cap`、quoted spread 実値を保存)。前向き検証の分母 (§5) に必ず算入 — 「スキップの闇損失」を作らない。
  - 実測ベースの予想 skip 率: 平穏週末で ~6% (36 pair-weekend 中 2 件、いずれも AUD 15p)。qualify する news-weekend は wide 側に寄ると仮定し**計画値 10〜20%**。
- 指値変種 (BT 参照価格指値) は fill 率未知 + adverse selection (gap 続伸時のみ fill) のため**今回は不採用**。shadow 側の気配記録で fill 率を並行観測し、採用するなら別途 R1 (spread report §4(b))。

### 2.3 exit (凍結案 — estimand 保存)

- **entry + 4h (14400s) 成行 time-exit のみ**。close_reason = `horizon`。exit 時刻 (01:05 / 冬 02:05 UTC) のスプレッドは通常域 (実測 1.3〜1.9p) — exit 側 stress 会計は不要。
- **TP なし / BE なし / Trail なし / BE_LOCK なし / C1 半分時点損切りなし / SIGNAL_REVERSE 対象外** — MEMORY `project_be_trail_inflates_python_bt_wr` (BE/Trail は BT WR を ~20pp 水増し) 準拠。exit-free 4h が検証された estimand であり、これを崩す一切の「改善」は禁止。
- **disaster SL のみ例外**: entry ∓ **150p** (エンジンが SL フィールドを要求 + フラッシュクラッシュ型テール防御)。OOS 4h MAE p50 9.9p、\|gap\| p90 ~90-100p に対し 150p は発火期待 ~0。発火時は forward 集計で**個別 flag** (estimand 逸脱イベントとして gate 判定に注記)。1000u での金額上限 = ~$15。
- swap: 保有 4h のため無視可 (stage-1 §2 と同一)。

### 2.4 同時ポジション規律 (3 ペア同時 qualify 時)

- **全 qualifying ペアに entry** (最大 3 ポジ同時) — pooled arm の estimand は pair-event 単位であり、選択的執行は新たな selection を持ち込むため禁止。cap スキップのみが正当な未執行。
- 構造的整合の確認済み事項: 金曜 21:45 UTC の **WEEKEND_CLOSE 全ポジ強制クローズ** (demo_trader.py 実装済み) により日曜 open 時点の book は必ず flat → max_open 4 / per-pair 1 制限と衝突しない。3×1000u は ExposureManager 20,000u 制限内 (同一 USD 方向に 3 ポジ整列しても 3,000u)。
- **統計上の注意 (凍結)**: 同一週末の複数ペアは相関 1 イベント — forward 検証 (§5) の統計検定は OOS と同一の weekend-block 集計で行う。

### 2.5 dedup / エンジン既知問題への対応

- **既知問題**: エンジン毎 tick 再構築で strategy instance の per-bar dedup は live 無効 (MEMORY `project_engine_reconstruction_live_dedup_dead`)、実効層は recent_emit (60s) のみ。本戦略の entry 窓 (~数分〜15 分) > 60s のため **recent_emit 単独では不十分**。
- **対策 (凍結)**: **per-pair per-weekend latch を system_kv に永続化** (key 例: `weekend_gap_fade:{pair}:{sunday_date}`、値 = EXECUTED / SKIPPED_SPREAD)。latch 済みペアは同一週末に再発火しない。デプロイ再起動でも system_kv 永続 (Deploy-Safe State Persistence) で生存。加えて per-pair 1 position 制限が保有中 (4h) の二重発注を防ぐ二重防御。order 層 min-spacing の追加は**不要** (週 1 回 × latch で構造的に排除。影響が小さいという task 想定を、latch を正とすることで担保)。

### 2.6 実装経路の実在確認 (existence check — 実装は承認後)

全メカニズムに本番コードの前例あり (新規発明ゼロ):

| 要件 | 前例 (modules/demo_trader.py) |
|---|---|
| entry_type 固定 1000u sentinel | `PRICE_SHOCK_REV_MIN_UNITS = 1000` + `PRICE_SHOCK_REV_MIN_LOT` 経路 (L6030 付近)。T5 教訓の floor 1000u と同型 |
| time-exit (horizon) | `_ENTRY_TYPE_MAX_HOLD` per-entry_type override → `close_reason="horizon"` (L2432/L2972) |
| TP-skip / C1 免除 | `PRICE_SHOCK_REV_TIER1_TYPES` の TP-hit スキップ (L2943) + C1 免除 (L2983、sweep_reversion/hull_donchian にも前例) |
| 週末境界 | WEEKEND_CLOSE (Fri 21:45 UTC、L2410) — 日曜 entry +4h (月曜 01:05 close) と非干渉 |
| latch 永続 | system_kv (Deploy-Safe State Persistence) |
| slippage/spread 実測 | 既存 DB 列 signal_price / spread_at_entry / spread_at_exit / slippage_pips (Production Monitoring) |

**必要な新規例外 (実装時の要注意点)**: E1 スプレッドフィルター (EUR 1.2p / JPY 1.0p / AUD 1.5p、L5134) と spread_gate Layer 0 は日曜 open の 4〜15p を**必ずブロックする** → 本 entry_type に限り**専用 cap 10.0p で置換** (全面バイパスではない)。4原則#2 (デスゾーン = スプレッド異常の動的検出) との整合: 本戦略は「異常スプレッドを既知の摩擦としてEVに織込済み + cap で上限を切る」設計であり、cap 自体が実測 p90 由来の動的防御。**SHADOW_ALWAYS 型バイパスには R2 demotion gate 併設**の教訓 → §5 G1/G2 が対応物。

## 3. サイジングと月次期待値

### 3.1 サイジング (凍結案)

- **固定 1000u** (OANDA 実用最小ロット級)。DD 防御 0.2x 環境 (現行 lot_mult=0.2x defensive) とは独立 — 0.2x を掛けても floor 1000u に張り付くため、price_shock_rev と同じ**固定 sentinel** とする (lot 3-factor モデル非適用)。
- pip 価値 @1000u: EUR_USD / AUD_USD = $0.10/pip、USD_JPY ≈ $0.065/pip (150 円台)。OOS N 構成 (46/65/66) 加重 ≈ **$0.087/pip**。
- 1 イベントの露出: 想定 notional ~$1,000、テール損失 (disaster SL 150p) ~$15。3 ペア同時でも ~$45。証拠金負荷は無視可能。

### 3.2 月次期待値と分散 (導出明示 — 公表済み凍結統計のみ使用、OOS 再接触なし)

- **頻度**: 177 イベント / 54 ヶ月 = **3.28 イベント/月** (2.07 週末/月)。cap skip 計画値 10〜20% → live 執行 **~2.8〜3.0 イベント/月**。
- **EV/イベント**: +7.90p (実測 mean RT) / +9.04p (凍結 3× 仮定) / **+3.26p (実測 p90 tail — news-weekend 参照ケース)**。cap skip は worst-RT イベントを除去するため、執行済みセットの per-event EV は +7.9p に対し改善方向。
- **月次期待値**: 2.8〜3.3 × 7.9p ≈ **+22〜26 pip/月** ≈ **+$1.9〜2.3/月** @1000u (tail ケース: +9〜11p/月)。年間 ≈ +310p ≈ +$27。
- **分散**: weekend-block bootstrap p<1e-4 (p 床) → z ≥ 3.72 → se ≤ 15.60/3.72 = 4.19p → σ_weekend ≤ 4.19×√112 ≈ **44p** (上界)。月 2.07 週末 → **σ_month ≈ 63p** → 単月の P(負) ≈ 34%。**符号の安定は年スケールで顕在化する** — 月次で一喜一憂しない設計 (§5 の N ベース gate がこれを制度化)。
- **M1 (clean live 月次符号転換) への寄与 — 正直な評価**: clean live 30d = −242.6p (roadmap v2.3) に対し +26p/月は**約 11% の是正でしかなく、M1 単独達成手段ではない**。本件の価値は (i) 三重確認済みの内部供給枯渇の中で**プロジェクト初の OOS-PASS 検証済み正EVセル**を live 台帳に立てること、(ii) 検証通過後の lot ladder (pip 期待は不変、$ は lot 線形) の土台、(iii) 週末窓は既存戦略とゼロ重複 = 相関コストなしの純増、の 3 点。

## 4. shadow-first vs 直接 live MIN lot

### 4.0 どちらでも共通の設計 (4原則#3 の Shadow/LIVE 非対称に整合)

**Shadow は cap 無視で全 qualifying イベントを記録し (統計 power 保全、削らない)、live 転送側にのみ spread cap を適用する (勝てる条件だけ転送)。** つまり cap は LIVE 側 winning-location フィルタであり、shadow 分母は常に完全。これは選択したオプションに依らず実装する。

### 4.1 オプション比較

| 観点 | (a) shadow-first (8〜12 週末 → live 昇格) | (b) 直接 live MIN lot |
|---|---|---|
| 得られる情報 | 配管検証 (発火時刻 / latch / exit 実行 / cap 判定ログ)。demo bid/ask fill での擬似 net | 左に加え**実 slippage** (薄い板の成行 — 残存不確実性の本体。candle からは測定不能で shadow でも不能) |
| 得られない情報 | **実 slippage** — shadow を何ヶ月やっても §6-2 リスクは未解消のまま | なし (live が最終検証形) |
| タイムライン | live 開始 +2〜3 ヶ月遅延 → §5 G3 到達 ~13 ヶ月 | G3 到達 ~10 ヶ月 |
| リスク | ほぼゼロ (発注なし) | 配管バグ誤発注 — ただし 1000u 固定 + latch + per-pair 1 + disaster SL で上限 ~$15/イベント。月次期待損失の最悪ケースでも $10 未満 |
| 4原則整合 | #1 (機会を逃すのが最大の敵) に反する遅延。shadow が新情報を生まない点で #4 とも不整合 | #1/#4 整合。R2 auto-stop (§5) 併設で規律担保 |

**起案者推奨 = (b)**。定量根拠: (a) が回避するリスクの上限 (~$15/イベント × 少数イベント) は (a) が失う情報 (実 slippage、EV の最大不確定要素) の価値より小さい。live 最初の 2 週末を G0 配管検証を兼ねた運用とすれば、(a) の便益はほぼ全て (b) に内包される。

## 5. 前向き検証ゲート (凍結案 — R2 自動停止併設)

**N の定義**: live 執行済み pair-event 数 (cap skip は分母記録のみ)。統計検定は weekend-block。**監視主体 (T5 教訓: 執行されない pre-reg を作らない)**: 週次戦略監査 (`raw/audits/`) に weekend_gap 行を追加 + 月曜 daily report で前週末イベントを必ず言及 + gate 抵触時は Discord AlertManager 通知。gate 執行者 = Claude (code pin PR、rule:R2)。

| gate | 発動点 | 判定 (凍結) | アクション |
|---|---|---|---|
| **G0 配管** | 最初の 2 qualifying 週末 | 発火時刻 21:05±5m (冬 22:05±5m) / latch 動作 / exit 4h±10m / cap 判定ログ完全 | 不備 = R3 即修正 (live は修正まで停止、shadow 継続) |
| **G1 slippage** | live N ≥ 6 (rolling) | entry 実測 slippage (fill vs signal_price、spread とは独立) の rolling mean > **+2.0p** | **R2: live 停止** → shadow 継続 + 原因分析。根拠: +2p 超過で mean EV +7.9→+5.9p、tail +3.26p は僅少化 |
| **G2 first-look** | live N = 12 (~4 ヶ月) | cumulative net < **−60p** (≈ mean −5p/event。OOS mean +15.6p・σ≤44p 下で z≈−1.8 相当の異常) | **R2: live demote → shadow-only**。family は live-execution 保留として記録 |
| **G3 confirm** | live N = 30 (~10 ヶ月) | ① mean net > 0 (OOS 効果が実在なら P(sign 誤り)≈3%) ② **BT/live 乖離チェック**: live WR(net>0) ≥ **35%** — OOS 凍結統計は median +6.2p>0 → WR>50% が下界であり、15pp 乖離ルール ([[bt-live-divergence]]) を「50%−15pp」として適用 (OOS 再集計は §9 で禁止のため WR 実値は使わない) ③ disaster SL 発火 0 件 (発火時は個別審査) | 全充足 → **lot ladder は別途 R1 起案権を獲得** (自動増額はしない)。①不充足 → live 恒久停止 + family へ live-execution FAIL 追記 |
| **常設** | 毎週末 | OANDA schedule cap 変化 / 冬時間初週末 (11 月) の spread 構造を read-only 実測 (`tools/sunday_open_spread_measure.py` 月次 re-run) | 実測 p90 が cap 10p を恒常超過 → cap 見直しは R1 (凍結値変更のため) |

**G2/G3 の設計思想**: 昇格判定 (Rule 1) ではなく停止判定 — 停止側は Rule 2 (Fast & Reactive) で軽く、増額側は必ず新規 R1。SHADOW_ALWAYS 型バイパス (E1 置換) に対する demotion gate 併設の教訓に準拠。

## 6. リスク列挙 (事前宣言)

1. **news-weekend の cap 側リスク (p90 マージン +3.26p は薄い)**: 実測 12 週末は全て**非 qualify の平穏週末** — qualify する週末 (定義上大きく動いた週末) の spread は cap 側に寄る相関が予想される。防御 = cap skip (EV 悪化週末を執行しない) + G1。ただし skip 率が計画値 20% を大幅超過すると頻度が縮み G2/G3 期日が後ズレする (EV は守られる)。
2. **slippage 下方バイアス**: 0.5p 仮定は通常市場のもの。21:05 の薄い板での成行は candle から測定不能で、実際は上回る可能性が高い (spread report §留保 1)。**これが live でしか解消できない最大の未知数** — G1 (+2.0p 閾値) が防波堤。
3. **12 週末実測は夏時間・平穏期のみ**: 冬時間 (open 22:04 UTC) の spread 構造・22:01 崩落の冬相当時刻は**未実測**。11 月最初の週末を G0 相当の注視対象とし、月次 read-only 実測で追跡。
4. **regime 構成シフト (stage-1 §6 宣言の継続)**: OOS 発生率 39/年は explore (21/年) の 1.9 倍 = 2022+ 高ボラ regime の産物。ボラ正常化で頻度と効果量が同時に縮退しうる (2026H1 は 27 件/半年とやや減速)。gate は N ベースのため壊れないが、期日が延びる。
5. **OANDA 週明けスケジュール cap の変更リスク**: schedule cap (EUR/JPY 10p / AUD 15p) はブローカー裁量。引き上げ → skip 率上昇 (EV 保全・頻度低下)。撤廃/緩和 → 有利。月次実測で検出。
6. **週末ショックへの相関集中**: 3 ペア同時 qualify は単一週末ショックへの 3 重露出 (実効 N は週末数)。悪い週末 1 回で −60〜100p (合算) が可能 → Circuit Breaker (Daily −30pip) が月曜朝の他戦略を巻き込んで停止させる干渉に注意 (実装時に breaker のスコープを確認、必要なら本 entry_type の損失を breaker 集計から分離するかを実装 PR で明記)。
7. **disaster SL の estimand 汚染**: 発火すれば測定分布が BT と乖離する — 発火は個別 flag し G3 で審査 (③)。
8. **GBP 汚染防止の継続**: GBP_USD は本執行の対象外を維持 (コード上も instrument allowlist を 3 ペアに固定)。

## 7. user 決裁オプション表 (step③ — いずれかを選択してください)

| opt | 内容 | 期待値 | リスク | 起案者評価 |
|---|---|---|---|---|
| **(a)** | **shadow-first 承認** — 8〜12 週末 shadow (cap 無視全件記録) → G0 相当の機械的配管確認後、live MIN lot 自動昇格 | live 収益開始 +2〜3 ヶ月遅延。G3 到達 ~13 ヶ月。月次期待は昇格後 +22〜26p | ほぼゼロ。ただし**実 slippage は未解消のまま昇格判断**することになる (shadow で得られない) | 安全だが情報効率が悪い。(b) の初期 2 週末が実質これを内包 |
| **(b)** | **直接 live MIN lot 承認 (推奨)** — §2 凍結仕様どおり 1000u で即開始、G0〜G3 併設 | 月次 +22〜26p (~+$2) @1000u、σ_month ≈ 63p。G3 到達 ~10 ヶ月。slippage 実測が即時開始 | 配管バグ誤発注 (上限 ~$15/イベント、latch+1000u+disaster SL で bound)。単月マイナスは 34% で正常挙動 | **推奨**。4原則#1/#4 整合、R2 停止ゲートで非対称に防御 |
| **(c)** | **追加実測後に再提示** — qualify 級 news-weekend の実 spread 観測を N≥3 蓄積してから再決裁 | 追加情報: news-weekend の cap 側分布。ただし受動待ちで **~半年** (qualify 週末 ~2/月 × 観測のみ) | 機会損失 ~6 ヶ月。しかもこの観測は (a)(b) の稼働と**同時に可能** — 純粋待機の固有便益なし | 劣後。観測は §5 常設 gate に内蔵済み |
| **(d)** | **見送り** — family #3 を PASS 候補のまま棚上げ | 0 | 内部供給枯渇 (三重確認済み) の下で、唯一の OOS-PASS 済み外部仮説エッジを未検証のまま放置。E1 positioning の first look は 2026-10-15 でそれまで供給ゼロ | 機会費用が最大。選ぶ場合は棚上げ理由の KB 記録を推奨 |

**補足**: (a)(b) いずれでも §4.0 の Shadow 全件記録 + §5 gate + §6 リスク宣言は同一に適用。(b) 承認の場合、本文書を LOCKED 化 → 実装 PR (strategies 登録・E1 置換・latch・horizon exit — 登録は deploy 担当) → 初回運用は次の日曜 open から。

## 8. 承認後の手続きと禁止事項

- **承認 → LOCK**: user 選択を §7 に追記し Status を LOCKED 化。以降 §2/§3/§5 の凍結値変更は R1。
- **実装**: 別 PR (deploy 担当が `strategies/daytrade/__init__.py` / `modules/demo_trader.py` 登録)。実装 PR には: 3 ペア allowlist / cap 10.0p / latch / horizon 14400s / disaster SL 150p / E1 置換 / gate 監視配線 (週次監査行 + AlertManager) を含め、pre-reg 条項との突合チェックリストを PR 本文に付す。
- **禁止**: OOS 再接触・再集計 (WR 等の新統計算出を含む) / qualify 閾値・endpoint・cap の事後変更 / entry リトライやスプレッド待ち等の estimand 逸脱「改善」/ BE/Trail/TP の追加 / GBP_USD への拡張 / gate を経ない lot 増額。
- **KB**: 承認時に `wiki/strategies/weekend_gap_fade.md` を実装コミットと同時作成 (KB 運用ルール)。台帳 [[hypothesis-catalog-2026-07-24]] row #3 に stage-2 決裁結果を追記。

## 参照

- stage-1 OOS pre-reg + verdict: [[weekend-gap-oos-prereg-2026-07-24]] / `reports/weekend_gap_oos_confirm-2026-07-24.md` / `bt-results/weekend_gap_oos_confirm-2026-07-24.json`
- R1 step① 実測: `reports/sunday_open_spread-2026-07-24.md` / `bt-results/sunday_open_spread-2026-07-24.json` / `tools/sunday_open_spread_measure.py`
- 執行系現行仕様: [[system-reference]] (E1 spread filter / WEEKEND_CLOSE / Circuit Breaker / Production Monitoring / Deploy-Safe Persistence)
- 教訓: MEMORY `project_be_trail_inflates_python_bt_wr` (exit-free 保存) / `project_engine_reconstruction_live_dedup_dead` (latch 必要性) / `project_t5_jpy_cap_prereg_executed` (監視主体併設) / `project_t8_week1_gate_breach` (R2 停止 code pin) / [[lesson-asymmetric-agility-2026-04-25]] (停止=R2 軽 / 増額=R1 重)
