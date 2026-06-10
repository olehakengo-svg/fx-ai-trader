# usdjpy_carry_dip_accumulator

- **Status**: SHADOW (2026-06-08 登録) / LIVE は **Rule-1 意図的例外 pending**（要 user 最終承認 + lot 確定）
- **Mode**: hourly (H1) / **Pair**: USD_JPY only / **Direction**: LONG only

## 概要
現レジーム固有の順張りロング dip-buy。USD_JPY H1 で RSI(14) が 45 を**下抜けた瞬間**（押し目入口）に、close が天井 159.5 未満なら LONG。SL = entry-1.5円（介入ギャップ前提の per-trade テールキャップ）、TP = entry+0.8円、hold ≤ 24 H1。同一押し目クラスタは 12h cooldown で1エントリーに畳む。

## 思想（因果）
現レジーム = 155-160.7 高位レンジ。160 = MOF/BOJ 介入の政策壁（2024 介入水準）。
ドリフトは**上**:
1. **金利差キャリー**: 米 10Y 4.47 / 2Y 4.05 高止まり、BOJ 0.75%（正常化緩慢）。
2. **コストプッシュ**: 2026 イラン戦争/ホルムズ封鎖オイルショック → 資源輸入の日本は貿易赤字拡大 → 実需の円売り。円は逃避通貨の地位喪失。

介入は方向転換でなく「天井で撃ち落とす単発」（4月 160.7→155.5 は回復基調）。→ **ドリフト順張りロング + 押し目拾い、160壁に張り付かない**。
ショートフェードは誤り（TV H4 BT で負け8/9=ドリフトに轢かれた）。

## BT 結果（2026-06-08, Claude 直接実装・一次データ）
- **オフライン BT (TV H4 500本, 2026-02-11〜06-08, 4月介入クラッシュ込み, MtM DD)**:
  tail-cap v3 = **N=10 cycles, WR 90.9%, PF 4.35**, 最悪テール **-2.0円ハードキャップ**。
  （制御なし v2 は 100%WR だが構造テール -14円=満載災害 → 棄却）
- **H1 (2026-05-08〜06-08) 再検証**: max 同時トランシェ=1 → 現レジームでは単発に縮退。
- **発火検証 (E2E, 2026-06-08)**: H1 500本で 7 emits/月（cooldown 後）、runaway なし。
  level→edge トリガ修正 + cooldown で 49→19→7 に是正。

## エントリー
- closed bar (Live: iloc[-2], BT: iloc[-1], rule:R3) で RSI(14) が 45 を下抜け AND close < 159.5
- BOJ/Fed 窓 (2026-06-15..18 UTC) は新規停止
- per-bar dedup + 12h re-entry cooldown

## Exit
- TP = entry + 0.8円 / SL = entry - 1.5円 / hold ≤ 24 H1 bars

## ⚠️ Rule-1 意図的 LIVE 例外（pending）
本戦略は **N<30・単一4ヶ月レジーム・非Bonferroni** で Rule-1（365日BT or Live N≥30 + Bonferroni + Pre-reg LOCK）を**未充足**。
User 判断: 低頻度（~月2-7発火）ゆえ shadow でも蓄積速度は同じ → 小ロット LIVE で実 fill を貯める。
Kalman D7 / vix_carry / ZZ v60 と同系の意図的例外。**LIVE flip は別途 user 承認 + lot 確定 + この card 更新が条件**。

## Pre-registration（LIVE flip 時に LOCK）
- 評価 N: Live closed trades（is_shadow=0）N≥30 まで観測。
- KPI: Live WR, EV/trade, PF, max DD, qualifying-bar 数。
- retreat（どれか → kill / shadow 降格）:
  1. BOJ ガチ利上げ/タカ派転換でドリフト反転
  2. オイル完全沈静化で円高転換（ホルムズ再開）
  3. Live 累積 DD が閾値超（watchdog）/ Live EV<0 N≥10

## 関連
- 戦略コード: `strategies/hourly/usdjpy_carry_dip_accumulator.py`
- 登録: `strategies/hourly/__init__.py` (_shadow_always), `modules/demo_trader.py` QUALIFIED_TYPES
- オフライン BT: `/Users/jg-n-012/test/bt_v2.py`（TV H4/H1 生データ）
- TV Pine: 「USDJPY Carry Dip-Accumulator v3」(TradingView)
- MEMORY: `project_usdjpy_carry_dip_accumulator_2026_06_08`
