# Track C 資本配管修復 決裁パケット — DRAFT (rule:R1、user 最終承認待ち)

**Status**: DRAFT 2026-07-28。SLA: D3 準拠 48h。
**診断**: [[track-c-plumbing-audit-2026-07-28]] (全クレーム code 検証済み)
**位置づけ**: [[shortest-path-decision-memo-2026-07-10]] トラック C (D4 carve-out 設計 + 防御解除ラダー) の執行。
**最重要事実**: user 決裁 07-28「7 席全部再武装」は agg-Kelly gate の carve-out 欠落により
**code 上無効化されている** (ps×5 + dmb×2 は次の qualify シグナルで shadow 落ち確定)。
live 発火可能なのは wg×3 + legacy 2 型のみ。

---

## 決裁事項 (4 分割 — 個別に承認/却下可能)

### D-a: JPY 台帳の再構成 【R3 測定のみ — ✅ 実測完了 2026-07-28】
broker 実約定 (oanda_trades.realized_pl、口座通貨 JPY = 換算誤差ゼロ) で clean 期 live N=339 を再構成:

| 指標 | 実測値 |
|---|---|
| clean live JPY 累積 (04-13〜07-15) | **−32,632 JPY** (pip 台帳同母集団 −527.0p、加重 61.9 JPY/pip) |
| **実 DD% (max)** | **9.14%** (対初期資本 359,105 JPY) / 10.35% (対実 clean 開始 NAV) |
| tier 判定 | **全測定法で 0.20x に一致** — 現時点の defensive posture は数値として正当 |
| **0.40x 復帰に必要な回復** | JPY 実測 **+4,088 JPY (≈+66p 相当)** vs pip 台帳 **+928.1p** — **14 倍の非対称 = 現行台帳は事実上の恒久ロック** |
| 100.8% の分解 | 実測 9.1% × 母集団インフレ ~1.9x (KV cum −991p のうち **−335.3p が現 DB から再現不能** = 監査可能性欠損) × 分母過小 5.8x (1000p ≈ 61.9k JPY 相当 vs 実 359k) |
| 台帳忠実度 | demo vs OANDA pnl_pips \|差\| median 0.20p / p90 1.80p — 良好 |

**D-b の位置づけを訂正**: 目的は「守りを緩める」ではなく **(i) 回復経路を数学的に開通させる**
(実 NAV 基準なら +4.1k JPY で 0.40x 復帰圏)、**(ii) 監査可能な台帳に置換する** (母集団を
`oanda_trade_id != ''` broker 実約定に限定 — Live 厳格分離原則と一致)。

**⚠️ D-a で発見された追加決裁事項 (D-e として下記追加)**: post-cutoff の **orphan fills 28 件
(net −4,792 JPY、うち 2026-07-10/13 の USD_JPY 30000u × 7 件 = preserve 系経路)** が demo 台帳に
link されず equity ガードの母集団外。30000u は clean live 最大 lot (10000u) の 3 倍 (≈300 JPY/pip) —
**ガードが見ていない場所に最大の JPY 感応度がある**。

### D-b: DD defensive の estimand を pip/1000 → NAV 比 (JPY 台帳) へ切替 + 再基準化 【R1】
- **変えないもの**: DD_LOT_TIERS の段構造 (2/4/6/8% → 0.8/0.6/0.4/0.2x)、MC ruin gate (>0.7 block)
- **変えるもの**: 分母と台帳のみ (測り方の訂正)。切替後の multiplier は **D-a の実測値が決める**
  (1.0 復帰を前提にしない — 実測 ≥8% なら 0.2x のまま)
- ruin 計量 (`_get_ruin_probability` の 1000pip/500pip) も同時に NAV 比へ統一 (二重基準防止)
- 整合: ruin 63% 教訓と矛盾しない (lot 増を含まない)。「0.2x が ruin 0% を保つ」観測には
  D-d のセル単位ラダー存続で応答

### D-c: ps×5 + dmb×2 の agg-Kelly carve-out 【R1 — 本パケットの核心】
07-28 再武装決裁を実効化する配管修理。ただし 2 論点が絡むため選択肢を分離:

**D-c-1 (ps×5)**: `_AGG_KELLY_GATE_MINLOT_BYPASS_TYPES` へ price_shock_rev 5 型を追加
(全席 1000u 固定契約 = bypass の ≤1000u 条件と同水準、承認済みリスクから増分ゼロ)
- ⚠️ 前提論点: live exit が 3 層オーバーレイ (BE_LOCK B + ATR-BE/trail) で **LOCK 済み
  horizon-exit 設計と乖離中** ([[preserve-exit-overlay-2026-07-28]] §5、R1 未決裁)。
  このまま arm すると live EV の estimand が pre-reg と別物になり N 蓄積の解釈が汚染される
- **推奨**: exit overlay 決裁 (horizon-exit へ復元 or overlay 容認を pre-reg 修正として明文化)
  と carve-out を**同一 PR で同時執行** — 「発火するが測れない」状態を作らない
- 併設 R2: 既存 ps watchdog (4h) + 復帰初週ゲート (wg テンプレ踏襲)

**D-c-2 (dmb×2)**: 選択肢 3 つ
- (i) 1000u pin + bypass 追加 (再武装決裁の字義どおりの実効化)
- (ii) **bypass 追加せず shadow のまま N 蓄積** ← **Claude 推奨**。根拠: 365d BT FAIL
  (N=136/236、bootstrap CI 全負)、昇格根拠は shadow N=14/16 の小 N (postmortem「N≤40 正 EV
  全滅」該当)。gate が偶然正しい判断をしている状態 — withdrawal pre-reg (live N=10 EV<−0.5p
  → FORCE_DEMOTED) の存在自体が期待 EV の弱さの自認
- (iii) FORCE_DEMOTED へ正式降格 (R2)
- (i) を選ぶ場合は live N=10 auto-demote gate 併設を必須条件とする

### D-e: equity ガード母集団の補修 【R1 — D-a で新発見】
- 台帳母集団を broker 実約定 (`oanda_trade_id != ''` join) に限定し、遡及 shadow 化・再現不能残差
  (−335.3p) を構造的に排除
- **orphan fills (preserve 系 30000u 経路含む) を equity ガード母集団に含めるか明示決裁** —
  現状 DD 管理の死角。30000u 経路の出所特定 (どの送信経路が demo 台帳を迂回したか) を
  実装前調査として同梱

### D-d: 防御解除ラダーの再確認 【宣言のみ】
aggregate 一括解除の禁止を再確認。解除はセル単位 live N≥30 ∧ Wilson 下限 EV>0 → 2 段
(0.2x→1000u→5000u)、各段 R2 復帰条件付き (07-10 決裁の却下条項をそのまま拘束に)。

## 付帯 R2 レビュー項目 (このパケットでの決裁は求めない、記録のみ)
- vix_carry_unwind Overlap pilot: 06-09〜07-15 実現 **−23.2p (N=13)**、bypass 内で live 発火可能な
  まま。pilot 自身の週次ゲート状態の確認と、N≥10 負 EV での R2 停止判断を別線で起票

## M1 への寄与 (なぜ今これが最短経路か)
- 供給ライン (E1 10-15 / E7 08-28 / MoF Q2) は全て受動待ち — **今日動かせる M1 レバーは
  「検証済みセルの live N 蓄積速度」だけ**
- wg 単独では N=30 ≈ 2027-05。ps×5 が発火可能になれば (トリガ率 ~24.5/月、guard 通過後は要実測)
  N 蓄積が桁で加速し、M1 の統計確認 (live N≥30 正 EV セル ≥1) の期日が数ヶ月前倒しされうる
- ただし ps の EV 点推定は現時点で「不明」が正 — carve-out は「EV を live で測れるようにする」
  決裁であり「正 EV を約束する」決裁ではない。downside は 1000u × watchdog/R2 で有界

## 実行順序 (承認後)
D-a 実測追記 → user 決裁 (D-b/D-c) → 単一 PR (carve-out + exit 決裁反映 + 表示修正 + テスト
[gate bypass unit test / tests/test_preserve_types_tick_entry.py 整合] + KB 同一コミット) →
復帰初週ゲート監視 (registry 登録)
