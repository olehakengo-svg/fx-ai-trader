# MC ruin 100% 反転の解剖と修復 + 549250 事故の disposition (rule:R3, 2026-08-05)

## Status
**EXECUTED (R3)** — dashboard MC の資本整合修正 + pin テスト。live 挙動変更なし。
起点: `raw/trade-logs/2026-08-04.md` (daily report) の Key Observations #1-#6 (price_shock 549250 −123.2p 事故)。

## TL;DR
- **運用凍結は起きていない**: live 送信を実際に止める ruin gate (`_get_ruin_probability`,
  post-cutoff 全 N=566 + JPY 整合資本 5,801pips) の実測 = **ruin 0.0** (2026-08-05 再現)。
  audit 300 行に `mc_ruin` block ゼロ。次回 wg イベント (08-09) は ruin gate では止まらない
- **「ruin 100%」は dashboard 専用の三重 artifact**: ①30d 窓が n=10 に縮小 ②資本が旧 1000pips
  ハードコード (D-b が gate 側だけ修正し dashboard 側が取り残された「同じ事実の片方欠落」)
  ③単位不均一 pip 系列 (wide-stop 1000u JPY-cross の −123.2p = ¥1,232 を等重量扱い)
- **修復**: `/api/risk/dashboard` の `compute_risk_dashboard` 呼び出しに gate 側と同一式の
  `initial_capital` (OANDA_EQ_BASE_JPY / OANDA_JPY_PER_PIP_AVG ≈ 5,801pips) を接続 +
  n<20 低信頼フラグ。同一 n=10 系列で **ruin 1.0 → 0.0** (median_final −38 → +4,762)。
  pin: `tests/test_mc_ruin_dashboard_capital_align.py`

## 数値検証 (2026-08-05 実測)
| MC 経路 | 系列 | 資本 | ruin |
|---|---|---|---|
| gate (`_get_ruin_probability`) | post-cutoff 全 N=566 (mean −1.25 / std 8.8) | 5,801p (D-b 整合済み) | **0.0** |
| dashboard (旧) | 30d n=10 (mean −17.4 / std 38.4、549250 含む) | **1,000p (取り残し)** | **1.0** |
| dashboard (修正後) | 同上 n=10 | 5,801p | **0.0** |

副次: app.py の昇格 Gate 2-4 (`ruin_prob <0.7/<0.3/<0.1`) も dashboard 値を参照 —
修正で false-restrictive が解消される方向だが、agg Kelly −58.6% / PnL −705p のため
Gate 2-4 は引き続き全て閉 (lot 拡大は発生しない)。

## 549250 事故の Key Observations disposition
| # | 論点 | disposition |
|---|---|---|
| #1 | −123.2p = 帳簿最悪 fill | 実資本 ¥1,232 = NAV 0.34% (JPY 台帳 +1,232.00 で独立確認済み)。設計 horizon exit・SL 非接触・MIN-lot 契約遵守 — **LOCK 済み estimand の範囲内の負け** |
| #2 | live_tier_exempt が regime 全否決を素通し | **pre-reg 承認済みの設計**: price_shock の検証済み estimand は「regime 無条件エントリー + 12h horizon」(12.3y BT N=426 は regime フィルタなしで計測)。live に regime veto を足すことは **BT⇄live estimand 乖離の再導入 + LOCK の Post-hoc tune 禁止に抵触** — §7 (07-29) で exit 側の同種乖離を除去したばかり。変更するなら R1 amendment + user |
| #3 | 自動 tripwire の死角 (N=2 は watchdog N≥10 未達) | **user 決裁事項として提示** (下記) |
| #4 | tp=151.25 (3,926p) | **バグではない**: `price_shock_reversion_base.py:85` `tp = price + sl_distance*10.0` — 「time-stop 専用、pipeline が正 TP 距離を要求するための placeholder」とコード明記。111.992+39.26円=151.25 で実測一致。R3 チェック完了・修正不要 |
| #5 | pip-DD 116% vs JPY-DD 9.56% の 36 倍乖離 | 既知 (D-b で SSOT は JPY 台帳)。**本修正で MC 側の同族 artifact も解消**。pip-DD の表示廃止は cosmetic 枠 |
| #6 | MC ruin 100% | **本修正で解消** (上表) |
| #7 | wg 08-02 非約定 | **解消済み** (別セッション、main 2cf940f7: cancel reason = MARKET_HALTED 実測確定) |

## #3 price_shock_rev_aud_jpy demote 可否 — 判断材料 (user 決裁)
**推奨: demote しない (LOCK の watchdog に委ねる)**。理由:
1. LOCK 済み demote 基準 (watchdog Live N≥10 EV<0 / N=15 Wilson<0.40 / 2週連続 EV<0 /
   catastrophic SL率>30%) は **いずれも未発動** (Live N=2: +0.6p / −123.2p)
2. −0.31R は設計分布の範囲内 (12.3y BT WR63.8% EV+32.25p は同種の負けを含んで正)。
   1 トレードでの demote は [[lesson-reactive-changes]] + LOCK の実験停止規則改変
   (early stopping bias) に該当
3. 実損 ¥1,232 = 0.34% NAV。情報価値 (Track C で再武装したばかりの live N 蓄積) が上回る —
   vix pilot の 07-07 継続裁定と同じ構図 (あちらは shadow エッジ崩壊で後に demote、
   ps は forward 証拠がまだ N=2)
4. **demote する場合の正当化も存在する** (user が M1 の月次符号保護を最優先するなら):
   単一 fill が月次符号を支配し得る (−123.2p vs 月間 live 総量 ~数十p)。その場合は
   demote ではなく **horizon 損失 cap (例: 12h 中間で −60p 到達時 early close) の R1
   amendment** が estimand 温存的な代替案
判断はいずれも live 変更のため保留 — user 指示があれば即実装。

## 残タスク (chips)
- wiki-daily の audit 取得窓 (limit=30 → date filter / limit≥500) — daily report 自身の提言
- MC/VaR の pnl 系列の per-trade JPY 換算 (単位不均一の根治。DB に units 列が無く
  D-b 台帳と同じソースの配線が必要 — 調査込み)

## Related
- [[track-c-capital-plumbing-decision-packet-2026-07-28]] (D-b) / [[price-shock-rev-promote-criteria-2026-05-18]]
- [[price-shock-rev-aud-jpy-h1-long]] / raw/trade-logs/2026-08-04.md
