# kalman_d7_po_dn_flip — live exit スタック (C0〜C6) 付き制約 BT: 診断 (2026-09-27、rule:R3)

**目的**: registry `kalman-d7-live-exit-spec-mismatch-disposition` (期日 2026-10-08) の **user 決裁 packet** に、(1) どの overlay が BT edge を削るか、(2) winner / loser 別の hold・exit 分布、(3) 8h 以内に完結する winner の割合、(4) C0 感度 (BT 側 what-if) を供給する。PR #302 レビュー 4 巡 (Codex P1 ×3 / P2 ×7、全件実欠陥) を反映済み (§5 レビュー反映)。Codex queue `20260925-0300-kalman-d7-live-constrained-bt` を Claude が Python port で実行 (TV は本セッションで CDP 接続不可、v17 canon Pine はリポジトリ不在 = TV slot 2026-05-21 上書き)。

**判定の扱い (task 文書の凍結ラベルを継承)**: 本 BT の数字から keep / demote を決めない。走 0′〜4 は「C0 近似 + intrabar 順序近似」、走 5 は「C6 近似 (参考値)」。**加えて本走は harness 未検証 (下記 §1) — 全数値は引用禁止で、packet に載せるのは分解の順位・向き・exit 種別の構造のみ。**

- ツール: `tools/kalman_d7_live_constrained_bt.py` / pin: `tests/test_kalman_d7_live_constrained_bt.py` (17 本、各 overlay の発火 / 不発 両側 + 順序仮定で結果が変わる bar)
- 生成物: `knowledge-base/raw/bt-results/kalman_d7_live_constrained_bt_2026_09_27.{json,md}` (全走の trade 明細付き)
- データ: Massive USD_JPY M15 (`data/cache/massive/USD_JPY_15m.parquet`)、window 2025-07-01 → 2026-05-19 (canon と同じ)、warmup 2025-04-01、window 内 21,842 bars / raw entry signal 92 (po_up_start 712)
- 摩擦: USD_JPY RT 2.14 pip / trade ([[friction-analysis]]、spread 0.7 + slippage 0.5 込み) を **slippage 無しの水準差 (raw)** から引く (slipped gross から引くと slippage が二重 — review P2 4114026093)。WR / PF / EV は net。harness 比較のみ **TV 基準** (slippage 1 tick + commission 0.002%×2、PF は equity 10% 逐次サイジングの cash)
- live 定数の出典: `modules/demo_trader.py` (origin/main a0614e42) — C0a `_atr_mult["daytrade"]=1.0` / `_sl_margin=0.3×ATR` / RR 床 1.0 / MIN_SL 0.050 / MAX_SL 0.200、C0c 低流動性 {0,1,18,19,20,21}Z +0.2×ATR / rn 0.5 刻み ±2p → 2.5p 外側、C0b ×0.85、C0d ×1.3、C1 28,800s、C2 金曜 21:45Z、C3 BE 0.8×ATR (+spread 0.008)、C4 trail 1.5×ATR 到達後 0.5×ATR、C5 14,400s 超で含み損、C6 hold ≥600s ∧ 含み益 ≤0.3×ATR ∧ PO 崩れ (サロゲート)

## §0 新規所見 — 宣言仕様 (TP 5×ATR / SL 1.5×ATR) は BT canon の exit ではない **可能性が高い** (aggregate payoff の算術 = 強い示唆、確定ではない)

カード BT: N=46 / WR 23.91% / PF 3.866 / Avg Win 122 JPY / Avg Loss 9.94 JPY / winner 平均 458 bars。
PF = payoff × WR/(1−WR) ⇒ **aggregate payoff = 3.866 × 0.7609 / 0.2391 = 12.3×** (Avg Win / Avg Loss = 12.27× と一致)。
固定 TP 5×ATR / SL 1.5×ATR で **各トレードの ATR が同じで全 loser が stop まで走る**なら payoff は 3.33× が上限で、12.3× は出ない。

⚠️ **PR #302 review P1 (4113955117) による訂正 — 上の条件が外れると aggregate は 3.33× を超え得る**: (i) ATR は entry ごとに違う (winner の ATR が loser より大きければ比は膨らむ)、(ii) 480 bars cap は stop 到達前に loser を小さな損で閉じ得る。したがって「canon exit = flip」は **aggregate payoff から機械的には確定できない**。確定には TV 再走で **winner ごとの entry ATR と exit 種別**を読む必要がある (queue `20260927-0300-kalman-d7-v17-canon-tv-harness` 手順 1)。

それでも示唆が強い理由 (いずれも間接証拠、Massive 側の観測を含む):
- (i) の寄与の上界: 本 window の entry signal 92 本の entry ATR は p20 8.6p / median 10.0p / p80 11.5p (p80/p20 = **1.33**、max/min 2.34、ATR Q2–Q4 フィルタで帯が狭い)。12.3× を ATR 異質性だけで説明するには winner/loser の ATR 比 ≈ **3.7** が要り、観測帯の外
- (ii) の寄与: 残る因子 ≈ 12.3 / (3.33 × 1.33) ≈ 2.8 ⇒ loser の平均損失が stop の **≈36%** で閉じている必要がある = 大半の loser が cap (480 bars = 5 営業日) まで stop にも TP にも触れず小さな含み損で終わる形。Massive tp5 走では 74 本全て 480 bars 内に TP/SL のどちらかへ到達し CAP 決済 0 本 — この形は観測されない
- カードの **winner 平均 458 bars** は 5×ATR (≈50p) の TP 到達時間として不整合 (Massive tp5 走の winner 平均 37 bars、flip 走 373 bars)。TP 到達なら 5 営業日は要らない
- Avg Loss 9.94 JPY は 10% equity qty (~66 units @150) で ≈15 pip = 1.5×ATR (ATR≈10p) と整合 = SL 側は宣言どおりに見える (qty 前提込み)

⇒ **決裁肢 (a)「live exit を宣言仕様に合わせる」の宣言 = TP 5×ATR が canon の exit である保証は無い**。(a) を定義する前に TV 再走で canon exit を確定する (flip なら (a) = flip exit + SL 1.5×ATR + 市場 bar 480 本、tp5 なら宣言のまま)。走 0 `tp5` 変種 (下記) は payoff ~3.0 / winner の 45–48% が 8h 以内に完結する形状で、canon の「458 bars 保持」と形が違う。
## §1 Harness 検証 = ❌ FAIL (走 0 の 2 変種 + flip 定義 5 候補のいずれも canon を ±10% で再現しない)

比較基準 = **TV 基準** (slippage 1 tick + commission 0.002% × 2 order ≈ 0.6p、**PF は equity 10% 逐次サイジングの cash PnL** — canon の PF 3.866 は TV strategy() の monetary gross profit / loss。PR #302 review P2 4113955123 / 4114026095: 旧「gross」は slippage 込み・commission 抜き、旧 PF は pips 合計で、いずれも TV と基準不一致だった)。ギャップ fill (open が stop を割っていれば open で fill、review P1 4114077247) と exit bar の close 再エントリ (review P1 4114077249) を反映。

| 走 0 変種 | N | WR (tv) | PF (tv cash) | avg winner bars | canon |
|---|---|---|---|---|---|
| `flip` (perfect_dn = EMA200 > EMA75 > EMA25、SL 1.5×ATR、480 cap) | 60 | 18.3% | 1.99 | 373 | 46 / 23.91% / 3.866 / 458 |
| `tp5` (TP 5×ATR、SL 1.5×ATR、480 cap) | 74 | 29.7% | 1.49 | 37 | 同上 |

flip 定義の識別 (entry / SL / cap 固定、TV 基準): perfect_dn N=60 PF 1.99 avgWin 373 payoff 8.0 / not_perfect_up N=92 PF 0.78 avgWin 26 payoff 3.6 / close_lt_ema75 N=77 PF 2.00 avgWin 107 payoff 5.8 / close_lt_ema200 N=65 PF 2.25 avgWin 243 payoff 7.3 / ema25_lt_ema75 N=67 PF 2.52 avgWin 252 payoff 7.9。**形状 (payoff 5.8–8.0×、winner 100–370 bars、winner の 8h 内完結 0%) は flip 系だけが canon に近く、tp5 は形状ごと別物**。ただしどれも ±10% に入らない。

要因 (順不同、切り分け不能): (1) v17 Pine 不在で flip 条件・cap の実装が推定 / (2) Massive vs OANDA (TV) のベンダー差 — EMA 交差の 1 bar ずれで PO 遷移の有無が変わる / (3) percentile・EMA 初期化の実装差 / (4) 週末ギャップの fill 価格 (Massive の日曜 open vs OANDA の実 fill)。**TV で canon を再走できるまで harness は未検証**。task 文書「走 0 が現行 BT を再現できないまま制約付きの数字を出さない」に従い、§2〜§4 の数値は**引用禁止** (packet に載せるのは順位・向き・構造のみ)。

## §2 走 0〜5 の分解 (harness 未検証 — 順位・向きのみ読む)

順序仮定 = adverse_first (既定・保守側: 同一 bar で BE/trail 発動と SL 到達が両方あり得るときは SL を先に処理)。`winner ≤8h` は **壁時計 hold_sec ≤ 28,800s** (review P2 4113955120):

| 走 | N | WR | PF net | EV net p/t | payoff | winner ≤8h | winner hold bars med | exit 種別 (上位) |
|---|---|---|---|---|---|---|---|---|
| 走 0 flip (canon 形状) | 60 | 18.3% | 1.80 | +12.3 | 8.0 | **0%** | 330 | SL 48 / FLIP 9 / CAP480 3 |
| 走 0 tp5 (宣言) | 74 | 29.7% | 1.34 | +4.5 | 3.2 | **45%** | 30 | SL 52 / TP 22 |
| 走 0′ +C0 | 80 | 21.2% | 1.06 | +0.7 | 3.9 | **65%** | 18 | SL 63 / TP 17 |
| 走 1 +C1 (8h) | 81 | 27.2% | 1.17 | +1.8 | 3.1 | **86%** | 26 | SL 56 / MAX_HOLD 14 / TP 11 |
| 走 2 +C2 (金曜/日曜 fill) | 81 | 27.2% | 1.13 | +1.3 | 3.0 | **91%** | 25 | SL 56 / TP 11 / MAX_HOLD 9 / WKND_SUN 4 / WKND_FRI 1 |
| 走 3 +C3C4 (BE/trail) | 85 | 23.5% | 0.54 | -3.8 | 1.8 | **95%** | 6 | SL 46 / TRAIL 17 / BE 17 / WKND_SUN 3 / TP 1 |
| 走 4 +C5 (4h 含み損) | 85 | 23.5% | 0.54 | -3.8 | 1.8 | **95%** | 6 | SL 46 / TRAIL 17 / BE 17 / WKND_SUN 3 / TP 1 |
| 走 5 +C6 近似 (参考) | 92 | 19.6% | 0.53 | -3.2 | 2.2 | **94%** | 5 | SR_APPROX 32 / SL 25 / TRAIL 15 / BE 15 / WKND_SUN 3 |

順序仮定 = favorable_first (感度、同 bar では BE/trail 発動と TP 到達を SL より先に処理):

| 走 | N | WR | PF net | EV net p/t | payoff | winner ≤8h | winner hold bars med | exit 種別 (上位) |
|---|---|---|---|---|---|---|---|---|
| 走 0 flip (canon 形状) | 60 | 18.3% | 1.80 | +12.3 | 8.0 | **0%** | 330 | SL 48 / FLIP 9 / CAP480 3 |
| 走 0 tp5 (宣言) | 74 | 31.1% | 1.41 | +5.3 | 3.1 | **48%** | 28 | SL 51 / TP 23 |
| 走 0′ +C0 | 80 | 22.5% | 1.11 | +1.3 | 3.8 | **67%** | 17 | SL 62 / TP 18 |
| 走 1 +C1 (8h) | 81 | 28.4% | 1.24 | +2.3 | 3.1 | **87%** | 24 | SL 55 / MAX_HOLD 14 / TP 12 |
| 走 2 +C2 (金曜/日曜 fill) | 81 | 28.4% | 1.19 | +1.9 | 3.0 | **91%** | 23 | SL 55 / TP 12 / MAX_HOLD 9 / WKND_SUN 4 / WKND_FRI 1 |
| 走 3 +C3C4 (BE/trail) | 85 | 14.1% | 0.21 | -5.9 | 1.3 | **92%** | 4 | SL 46 / BE 26 / TRAIL 11 / WKND_SUN 2 |
| 走 4 +C5 (4h 含み損) | 85 | 14.1% | 0.21 | -5.9 | 1.3 | **92%** | 4 | SL 46 / BE 26 / TRAIL 11 / WKND_SUN 2 |
| 走 5 +C6 近似 (参考) | 92 | 10.9% | 0.20 | -4.9 | 1.6 | **90%** | 4 | SR_APPROX 32 / SL 25 / BE 24 / TRAIL 9 / WKND_SUN 2 |

限界分解 (走 0′ に overlay を単独で載せる。adverse / favorable):

| overlay 単独 | EV net p/t (adv / fav) | 発火本数 | 備考 |
|---|---|---|---|
| C1 (8h cap) | **+1.8 / +2.3** | MAX_HOLD 14 | 切られた建玉の PnL 分布 [-86.4, -13.5, -2.8] … [54.1, 203.5] |
| C2 (金曜 21:45Z / 夏は日曜 open fill) | +0.7 / +1.3 | 日曜 fill 4 + 金曜 1 | 累積 (走 1→走 2) では -0.4 / -0.4 — 符号は積み方とギャップの向きで変わる |
| **C3C4 (BE 0.8 → trail 1.5/0.5)** | **-3.8 / -6.3** | BE 18 / TRAIL 17 | 最大の負、両順序仮定で一貫 |
| C5 (4h 含み損、連続パス近似) | +1.5 / +2.1 | TIME_DECAY 12 | ⚠️ 符号は intrabar 順序仮定に依存 (review P2 4114077250 前の「SL 先」版では −0.9 / −0.3) |
| C6 近似 (参考) | -3.2 / -2.7 | SR_APPROX 49 | サロゲート、判定に使わない |
| C0+C1+C2+C5 (C3C4 抜き) | +1.8 / +2.3 | | BE/trail を外すと累積は正に戻る |

### 読み (順位・向きのみ)

1. **edge を最も削る overlay は C3/C4 (ATR BE 0.8 → trail 1.5/0.5)** — 単独 (-3.8 / -6.3) でも累積 (走 2→走 3: -5.2 / -7.8) でも最大の負の寄与で、両順序仮定・全 C0 what-if で一貫。BE/trail は winner の hold を中央値 25 → 6 bars に潰し (winner の 95% / 92% が壁時計 8h 以内 — 累積走 3、adverse / favorable。単独では 95% / 100%)、payoff を 3.0 → 1.8 に落とす。「BE/Trail が Python BT の WR を +20pp 水増しする」([[project_be_trail_inflates_python_bt_wr]]) の鏡像で、**保持依存の TF 戦略では BE/trail が EV を削る側に出る**。
2. **C0 (entry 時 SL/TP 置換) は 2 番目の削減** — 宣言 tp5 の +4.5 を +0.7 へ (Δ -3.8)。内訳は what-if (§3): broker TP ×0.85 / 低流動性 +0.2×ATR / SL 1.5→1.0×ATR (主因)。
3. **C1 (8h cap) はこのデータでは正の寄与** (+1.8 / +2.3) — MAX_HOLD 14 本の PnL は [-86.4, -13.5, -2.8, 2.0, 15.7, 16.1, 16.2, 18.2, 18.9, 25.7, 32.5, 43.9, 54.1, 203.5] で、8h で切られた建玉の大半は**その後 SL に落ちる負け候補**だった (tp5 exit 下では)。⚠️ これは「宣言 = tp5」上での話で、canon 形状 (flip 走) の winner は壁時計 8h 内完結 **0%** (11 本の hold は 65h〜168h) — **flip 形状の edge は C1 と両立しない**。
4. **C2 (金曜 21:45Z クローズ) の寄与は小さく、符号は積み方で変わる (累積 走 1→走 2 で -0.4 / -0.4、走 0′ 単独では +0.7 / +1.3) — 週末ギャップの向きを含み性質ではない**: live の 21:45Z 指示は **冬時間 (22:00Z 閉場) は 21:45 bar で執行、夏時間 (21:00Z 閉場) は閉場後なので日曜 open で fill** (KB 実例 carry_dip #709598、review P2 4114026089)。本 window の C2 fill は日曜 4 本 + 金曜 21:45 1 本 = **5 件の週末ギャップ**。N=5 の符号を寄与の向きとして引用しない。**構造的な事実**は「C2 は建玉を週末に持ち越させない (日曜 open では即クローズ)」= flip 形状 (winner が必ず週末を跨ぐ) と両立しないこと (§2-3)。
5. **C5 (4h 含み損) の符号は intrabar 順序仮定に依存する** — 連続パス近似 (4h 超で open ≥ entry の bar が entry と SL を両方割るなら entry 割れの tick が先、review P2 4114077250) では単独 +1.5 / +2.1 (12 本 = stop まで走らず entry 近傍で切る)、「SL 先」版では −0.9 / −0.3。**累積では BE/trail の後ろで 0 本** (走 3 = 走 4) — 打ち切り経路の重複。「負け側も打ち切られる」(09-25 訂正) は実在するが、BE/trail が先に同じ建玉を処理する。
6. **C6 近似は 49 本 (単独) / 32 本 (累積) を早期に切り WR を 20% / 11% に落とす** — ただしサロゲート (conf/score/ADX/他戦略 stream 無し) なので**向きも大きさも判定に使わない**。
7. **winner / loser 別 hold**: flip 走の loser は中央値 9 bars (p75 32) で 12/49 が 32 bars 超 — **C1 は canon 形状の loser も 1/4 切る**が、winner (100% が 8h 超) を全滅させる方が支配的。tp5 走の loser 中央値 6.5 bars。
8. **ギャップ fill と再エントリの影響 (4 巡目)**: 週末ギャップが stop を飛び越えると fill は日曜 open (flip 走の EV は +13.8 → +12.3、PF 2.21 → 1.99) — canon 形状は週末保持が前提なのでギャップ露出を含めて評価する必要がある。exit bar の close 再エントリは本 window では N を変えなかった (92 signal のうち exit bar と重なるものが再エントリしても後続 signal と置き換わるだけ)。

## §3 C0 感度 (BT 側 what-if、走 0′〜4、adverse_first、harness 未検証)

| what-if | 走 0′ EV | 走 1 | 走 2 | 走 3 | 走 4 | 順位が変わるか |
|---|---|---|---|---|---|---|
| base (ATR×1.0 / clamp / lowliq / rn / broker 0.85 / MTF 1.0) | **+0.7** | +1.8 | +1.3 | -3.8 | -3.8 | — |
| (i) ATR のみ | = base (SR 未使用なので同一) | | | | | 変わらず |
| (ii) SR 優先 (port A: `find_sr_levels_weighted` 直近 500 bars、⚠️ live の fetch 本数は未確認) | **+4.4** (N 68、sr 67 / clamp_max 32) | +2.5 | +2.3 | -3.8 | -3.5 | 微小、順位不変 |
| (iii) clamp 無し | = base (ATR×1.0 ≈ 10p は 5–20p 帯内) | | | | | 変わらず |
| (iv) 低流動性バッファ無し | **+1.2** | +2.3 | +1.8 | -3.6 | -3.6 | 微小、順位不変 |
| (v) MTF ×1.3 | **+2.9** | +2.7 | +2.3 | -3.8 | -3.8 | 微小、順位不変 |
| (vi) rn nudge 無し | **+0.9** | +1.9 | +1.5 | -3.9 | -3.9 | 微小、順位不変 |
| (vii) broker TP 0.85 無し | **+1.7** | +2.1 | +1.7 | -3.8 | -3.8 | 微小、順位不変 |

**分解の順位 (C3C4 ≫ C0 > C6近似 > C5 ≈ C2、C1 は正) はどの what-if でも変わらない。変わるのは走 0′〜2 の符号 (SR 優先 / MTF 1.3 / broker TP 無しで正)**。live 実測率 (SR 採用率 / lowliq / rn / MTF 一致率) は `[SLTP_CONSTRUCT]` marker (PR #300、09-26 デプロイ後の fill) が溜まってから差し替える — 現時点で 0 fill。fast-SL 拡幅は未再現。

## §4 packet 用の所見 (registry 10-08、判定は書かない)

- **決裁肢 (a) は「宣言 = canon exit か」を TV 再走で確定してから定義する**: §0 の aggregate payoff は canon exit が flip であることの**強い示唆であって確定ではない** (review P1)。flip と確定した場合の (a) = flip exit (PO-DN、定義は TV canon で確定) + SL 1.5×ATR + 市場 bar 480 本 + C0〜C6 全免除 — **BE/trail 免除が最重要** (§2-1)、次に C0 免除、8h cap と金曜クローズは flip 形状 (winner が必ず週末を跨ぐ) と両立しない (§2-3,4 — 本 window の C2 の符号はギャップ運で性質ではない、C5 の符号は順序仮定依存 §2-5)。週末ギャップ露出 + 1 建玉が最大 5 営業日拘束される。tp5 と確定した場合の (a) = 宣言のまま C0〜C6 免除 (この場合 走 0 tp5 の形状が対象)。
- **(b) 現状維持 = 「BT の無い戦略」**: live の実効仕様は「SL ≈1×ATR (SR 優先時は広い) / broker TP ≈4.25×ATR / BE 0.8 / trail 1.5→0.5 / 8h / 金曜 / 4h 含み損 / SIGNAL_REVERSE」で、この形状の BT は harness 未検証の走 3〜5 しかない (向き = 負、大きさ不明)。fill を canon 検証の N に数えない規律は継続。
- **(c) shadow 降格**: 本 BT は根拠にならない (task 規律)。通常の live 損失停止規律 (Rule 2、realized N ベース) のみ。
- **harness を閉じる唯一の経路 = TV で v17 canon を再走** (Pine の再構築 → flip 定義の確定 → 同 feed で走 0 一致 → 制約付き走を Pine 側で再現)。Python 側は Massive でしか走れないので、**TV 接続が要る = 対話セッションでの user 操作 (TV desktop 起動) が前提**。それまで本頁の数字は「方向・構造のみ」。

## §5 ツール規律

- **レビュー反映 (PR #302、4 巡目)**: P1 4114077247 — open が stop を割っていれば fill は open (sl − tick ではない): 週末ギャップで flip 走の EV +13.8 → +12.3、PF 2.21 → 1.99 (pin: −70p ギャップは open で fill、TP 側は open で有利 fill) / P1 4114077249 — bar 内 / open で exit した bar は close でフラット → その bar の signal で再エントリ (close 時点 exit の FLIP / SR / CAP / EOD は次 bar から。pin: TP bar の再 signal で 2 本、flip bar では 1 本) / P2 4114077250 — 4h 超で open ≥ entry の bar が entry と SL を両方割るとき連続パスでは entry 割れが先 (SL < entry のとき) → C5 単独が −0.9 → +1.5 に反転 = **符号は順序仮定依存**と §2-5 に明記 (pin: SL 先 / BE 後は BE 経路) / P2 4114077254 — winner ≤8h を「95% (両順序仮定)」と書いていたが favorable は 92% → 累積 / 単独を両順序で明記
- **レビュー反映 (PR #302、3 巡目)**: P2 4114026089 — 夏時間 (21:00Z 閉場) の 21:45Z クローズは執行不能で日曜 open fill になる (KB 実例 #709598) → `_c2_exit_at_open` で冬 21:45 bar open / 夏 日曜初 bar open の 2 レジームに (2 巡目の「金曜 close 合成」は撤回)。C2 の符号が −0.8 → +0.7 (日曜 fill 4 件のギャップが順行) に変わったが、性質ではなく小 N のギャップ運として記載 / P2 4114026093 — RT 摩擦 2.14p (slippage 込み) を slipped gross から引いて 0.1–0.2p 二重計上 → `raw_pips` (水準差) から引く / P2 4114026095 — TV PF を pips 合計から **equity 10% 逐次サイジングの cash PnL** に (PF 2.17→2.21、判定不変)。pin: 夏 = 日曜 open fill でギャップを食う / 冬 = 21:45 bar open / raw と gross の差 = tick 数 / cash PF ≠ pips PF
- **レビュー反映 (PR #302、2 巡目)**: P2 4113998538 — 金曜最終 bar (20:45) の signal は entry (21:00) 直後の 21:45Z に live がクローズするが、ループが日曜 bar から始まるため週末を跨いで保持していた → entry 時点で WEEKEND_CLOSE を合成 (hold 45 分、bars 0)。C2 の WEEKEND_CLOSE は 4→5 本、走 2 以降の EV は −0.05 程度動くが順位不変 (pin: 金曜 20:45 signal は c2 で WEEKEND_CLOSE / c2 無しで日曜 TP)
- **レビュー反映 (PR #302、1 巡目)**: P1 4113955117 — §0「算術で確定」を「強い示唆」へ格下げ (ATR 異質性 + cap 早期クローズで aggregate payoff は 3.33× を超え得る、確定は TV 再走の per-trade ATR / exit 種別) / P2 4113955120 — `winner ≤8h` を bars ≤32 から `hold_sec ≤ 28,800` へ (pin: 週末跨ぎ 20 bars = 8h 外、32 bars = 8h 内、33 bars = 8h 外) / P2 4113955123 — harness 比較を TV コスト後 (`tv_net_pips`、commission 0.002%×2) に統一 (pin: gross +0.3p の winner は TV では loser)

- 標準ラベル: JSON `harness_unverified: true` を出力し、MD 冒頭に 🔴 バナー。harness が通るまで数値引用を許さない
- record-only: live コードを import せず (indicator は `tools/kalman_d7_v18e_python_port`、SR は `modules/indicators`)、tier / lot / 配線に触れない
- counterfactual (pin 設計): C1 flag 無しで EOD、C5 は含み益側で不発、C2 は非金曜で不発、順序仮定で同 bar の結果が SL_HIT ⇄ BE に変わることを pin。`harness_check` は canon 一致 dict で True / 本走の値で False

関連: [[kalman-d7-po-dn-flip]] (09-24 節) / [[kalman-d7-carveout-postfill-packet-2026-09-17]] / [[friction-analysis]] / [[project_kalman_live_exit_stack_mismatch_2026_09_25]] / [[2026-09-27-session]]
