# usdjpy_carry_dip_accumulator

- **Status**: **LIVE 稼働中** (1000u MIN lot、Rule-1 意図的例外) — 2026-08-14 以降 fill 実績あり。2026-06-08 登録
- **Mode**: hourly (H1) / **Pair**: USD_JPY only / **Direction**: LONG only

> ✅ **2026-08-20 更新 — zero-fire 解消 (外生要因)**: 07-02 診断の dormancy は **市場が thesis レンジに戻ったことで自然解消**。USD_JPY が ~159.47-159.62 まで下げ、`close < 159.50` ゲートが再武装 (`raw/trade-logs/2026-08-19-monitor.md`)。ceiling の再設定・retire は**不要になった** — 159.5 は結果的に妥当な壁位置だった。**本戦略は現在システム唯一の live 発火セル**。
> 詳細: [[2026-08-20]]

> ⚠️ **2026-07-02 zero-fire 診断 (解消済み、記録として保持)**: 06-12 LIVE enable 以降 fill 0 の根本原因は **CEILING=159.5 が市場 (161-162.8) に取り残されたこと**。06-03 以降の RSI dip cross 22 回が全て ceiling block、emit 自体ゼロ。thesis の「155-160.7 レンジ」仮定が (一時) 失効。QUALBAR logging (T7) 実装済み。
> 詳細: [[zero-fire-diagnosis-carrydip-vix-2026-07-02]] / [[carry-dip-ceiling-reeval-2026-07-02]] (当時の推奨 "hold" が結果的に正解 — 壁を動かさなかったので市場復帰と同時に再武装した)

## Live 実績 (post-cutoff 2026-04-08〜, is_shadow=0) — 2026-08-23 時点
| N | W/L | WR | PnL | EV/trade | DSR |
|---|---|---|---|---|---|
| **9** | 5W/4L | 55.6% | **+84.0 pip** | +9.33 | 0.424 (Sharpe 0.3363 < 閾値 0.4059、z=−0.192 → **依然として有意でない**) |

- vs 2026-08-20: **N 7→9 (+2、いずれも勝ち)**、PnL **+45.1→+84.0 (+38.9)**、WR 42.9→**55.6%**、EV/trade +6.44→**+9.33**。DSR は 0.3591→0.424 と閾値に近づいたが **z=−0.192 でまだ跨いでいない**。
- 全 9 fill が直近 30d 窓内 (risk API USD_JPY `n=10`, +53.9 — 差分は同窓の非carry-dip 1 本)。ポートフォリオ 30d の**唯一の正寄与**（他は AUD_JPY price-shock −122.6 / 🆕 EUR_GBP price-shock −9.8）。
- 確認済み OANDA fill (audit limit=800): **#677402** (08-14 06:02 UTC) / **#677910** (08-16 23:02) / **#677917** (08-17 06:52) / **#677924** (08-19 01:05) / 🆕 **#677931** (08-20 07:03) / 🆕 **#681149** (08-20 10:19) — いずれも USD_JPY BUY 1000u、real trade id 付き = false-sent ではない。`sent` 行は戦略名 `usdjpy_carry_dip_accumulator`、`filled` 行は mode 名 `daytrade_1h` (twin-meaning、`reference_oanda_audit_twin_meaning`)。
- **判定保留**: pre-reg の評価 N≥30 に対し **N=9/30**。2 連勝で WR が BT の 90.9% に向けて寄ったが、N=9 の 2 本移動で 42.9→55.6pp 動く不安定域であり、**サンプル追加以外の情報は出ていない**。N≥30 まで promote/demote いずれも判断しない。
- ⚠️ **本セルは 2026-08-23 時点でも「システム唯一の継続的な正の live セル」であり、book 全体の +29.1 pip 改善はこの 2 本が単独で作った**。ポートフォリオの見かけ上の好転をこのセル 1 本の draw に依存させている状態。

> 🔴 **未解決 — SL 契約の不一致**: 戦略宣言は SL = entry −1.5円 (**150 pip** のテールキャップ) だが、初 live fill で **18.8 pip の SL** に置換されて観測された (`_1H_PRESERVE_SLTP` 未登録)。live fill が 9 本に達した今、これは仮説ではなく**このセルのテール挙動を実際に支配している**問題。150p キャップ前提の BT (最悪テール −2.0円ハードキャップ) と live の risk profile が別物になる。R3 決裁待ち。

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
