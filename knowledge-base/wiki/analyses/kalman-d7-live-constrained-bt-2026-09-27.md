# kalman_d7_po_dn_flip — live exit スタック (C0〜C6) 付き制約 BT: 診断 (2026-09-27、rule:R3)

**目的**: registry `kalman-d7-live-exit-spec-mismatch-disposition` (期日 2026-10-08) の **user 決裁 packet** に、(1) どの overlay が BT edge を削るか、(2) winner / loser 別の hold・exit 分布、(3) 8h 以内に完結する winner の割合、(4) C0 感度 (BT 側 what-if) を供給する。Codex queue `20260925-0300-kalman-d7-live-constrained-bt` を Claude が Python port で実行 (TV は本セッションで CDP 接続不可、v17 canon Pine はリポジトリ不在 = TV slot 2026-05-21 上書き)。

**判定の扱い (task 文書の凍結ラベルを継承)**: 本 BT の数字から keep / demote を決めない。走 0′〜4 は「C0 近似 + intrabar 順序近似」、走 5 は「C6 近似 (参考値)」。**加えて本走は harness 未検証 (下記 §1) — 全数値は引用禁止で、packet に載せるのは分解の順位・向き・exit 種別の構造のみ。**

- ツール: `tools/kalman_d7_live_constrained_bt.py` / pin: `tests/test_kalman_d7_live_constrained_bt.py` (17 本、各 overlay の発火 / 不発 両側 + 順序仮定で結果が変わる bar)
- 生成物: `knowledge-base/raw/bt-results/kalman_d7_live_constrained_bt_2026_09_27.{json,md}` (全走の trade 明細付き)
- データ: Massive USD_JPY M15 (`data/cache/massive/USD_JPY_15m.parquet`)、window 2025-07-01 → 2026-05-19 (canon と同じ)、warmup 2025-04-01、window 内 21,842 bars / raw entry signal 92 (po_up_start 712)
- 摩擦: USD_JPY RT 2.14 pip / trade ([[friction-analysis]])。WR / PF / EV は net、harness 比較のみ gross
- live 定数の出典: `modules/demo_trader.py` (origin/main a0614e42) — C0a `_atr_mult["daytrade"]=1.0` / `_sl_margin=0.3×ATR` / RR 床 1.0 / MIN_SL 0.050 / MAX_SL 0.200、C0c 低流動性 {0,1,18,19,20,21}Z +0.2×ATR / rn 0.5 刻み ±2p → 2.5p 外側、C0b ×0.85、C0d ×1.3、C1 28,800s、C2 金曜 21:45Z、C3 BE 0.8×ATR (+spread 0.008)、C4 trail 1.5×ATR 到達後 0.5×ATR、C5 14,400s 超で含み損、C6 hold ≥600s ∧ 含み益 ≤0.3×ATR ∧ PO 崩れ (サロゲート)

## §0 新規所見 — 宣言仕様 (TP 5×ATR / SL 1.5×ATR) は BT canon の exit ではない (算術で確定、データ不要)

カード BT: N=46 / WR 23.91% / PF 3.866 / Avg Win 122 JPY / Avg Loss 9.94 JPY / winner 平均 458 bars。
PF = payoff × WR/(1−WR) ⇒ **payoff = 3.866 × 0.7609 / 0.2391 = 12.3×** (Avg Win / Avg Loss = 12.27× と一致)。
固定 TP 5×ATR / SL 1.5×ATR の payoff 上限は **3.33×** (slippage 前) なので、canon の数字は **TP 到達で決済する exit からは出ない**。
Avg Loss 9.94 JPY は 10% equity qty (~66 units @150) で **≈15 pip = 1.5×ATR (ATR≈10p)** と整合 = SL 側は宣言どおり。Avg Win 122 JPY ≈ **185 pip ≫ 50 pip (5×ATR)** = winner は TP ではなく **PO-DN flip (regime 反転) まで ~458 bars 走らせて**決済している。

⇒ **カードの「TP 5.0×ATR (PO-DN regime flip approximation)」は Python live 実装 (`KalmanD7PODNFlip.tp_atr_mul=5.0`) の近似であって、BT canon の exit は flip**。結論として **決裁肢 (a)「live exit を宣言仕様に合わせる」は、宣言 = TP 5×ATR のままでは BT を回復しない** — 走 0 `tp5` 変種 (下記) は payoff ~3.0 / winner の 55% が 8h 以内に完結する別の戦略になる。(a) を採る場合は「flip exit + SL 1.5×ATR + 480 bars (市場 bar 数)」として再定義する必要がある (Rule 1、本頁は提案しない)。

## §1 Harness 検証 = ❌ FAIL (走 0 の 2 変種 + flip 定義 5 候補のいずれも canon を ±10% で再現しない)

| 走 0 変種 | N | WR (gross) | PF (gross) | avg winner bars | canon |
|---|---|---|---|---|---|
| `flip` (perfect_dn = EMA200 > EMA75 > EMA25、SL 1.5×ATR、480 cap) | 60 | 18.3% | 2.27 | 373 | 46 / 23.91% / 3.866 / 458 |
| `tp5` (TP 5×ATR、SL 1.5×ATR、480 cap) | 74 | 29.7% | 1.53 | 37 | 同上 |

flip 定義の識別 (entry / SL / cap 固定、gross): perfect_dn N=60 PF 2.27 avgWin 373 / not_perfect_up N=92 PF 0.98 avgWin 26 / close<EMA75 N=77 PF 2.33 avgWin 107 / close<EMA200 N=65 PF 2.58 avgWin 243 / EMA25<EMA75 N=67 PF 2.87 avgWin 252。**形状 (payoff 8–9×、winner 250–470 bars、winner の 8h 内完結 0%) は flip 系だけが canon に近く、tp5 は形状ごと別物**。ただしどれも ±10% に入らない。

要因 (順不同、切り分け不能): (1) v17 Pine 不在で flip 条件・cap の実装が推定 / (2) Massive vs OANDA (TV) のベンダー差 — EMA 交差の 1 bar ずれで PO 遷移の有無が変わる / (3) percentile・EMA 初期化の実装差。**TV で canon を再走できるまで harness は未検証**。task 文書「走 0 が現行 BT を再現できないまま制約付きの数字を出さない」に従い、§2〜§4 の数値は**引用禁止** (packet に載せるのは順位・向き・構造のみ)。

## §2 走 0〜5 の分解 (harness 未検証 — 順位・向きのみ読む)

順序仮定 = adverse_first (既定・保守側: 同一 bar で BE/trail 発動と SL 到達が両方あり得るときは SL を先に処理):

| 走 | N | WR | PF net | EV net p/t | payoff | winner ≤8h | winner hold bars med | exit 種別 (上位) |
|---|---|---|---|---|---|---|---|---|
| 走 0 flip (canon 形状) | 60 | 18.3% | 1.96 | +13.6 | 8.7 | **0%** | 330 | SL 48 / FLIP 9 / CAP480 3 |
| 走 0 tp5 (宣言) | 74 | 29.7% | 1.28 | +3.4 | 3.0 | 55% | 30 | SL 52 / TP 22 |
| 走 0′ +C0 | 80 | 21.2% | 0.96 | −0.4 | 3.6 | 76% | 18 | SL 63 / TP 17 |
| 走 1 +C1 (8h) | 81 | 27.2% | 1.15 | +1.6 | 3.1 | 64% | 26 | SL 56 / MAX_HOLD 14 / TP 11 |
| 走 2 +C2 (金曜) | 81 | 27.2% | 0.99 | −0.1 | 2.7 | 64% | 25 | SL 56 / TP 11 / MAX_HOLD 10 / WKND 4 |
| 走 3 +C3C4 (BE/trail) | 85 | 24.7% | **0.63** | **−2.7** | 1.9 | 100% | 6 | SL 46 / TRAIL 17 / BE 17 |
| 走 4 +C5 (4h 含み損) | 85 | 24.7% | 0.63 | −2.7 | 1.9 | 100% | 6 | (走 3 と同一 — BE/trail 後に C5 が掛かる建玉が無い) |
| 走 5 +C6 近似 (参考) | 92 | 20.7% | 0.64 | −2.2 | 2.5 | 100% | 5 | SR_APPROX 32 / SL 25 / TRAIL 15 / BE 15 |

順序仮定 = favorable_first (感度): 走 0′ +0.2 / 走 1 +2.2 / 走 2 +0.5 / **走 3 −6.0 (PF 0.20、BE 26)** / 走 5 −5.0。**分解の順位は両仮定で不変**、大きさは走 3 で 2 倍以上ぶれる (BE の同 bar 発動が多い) — packet にはこの幅を書く。

限界分解 (走 0′ に overlay を単独で載せる、adverse_first): C1 のみ **+1.6** / C2 のみ −0.9 / **C3C4 のみ −3.0** / C5 のみ −1.0 (TIME_DECAY 9 本) / C6 近似のみ −2.4 (SR_APPROX 49 本、参考) / C0+C1+C2+C5 (C3C4 抜き) +0.3。

### 読み (順位・向きのみ)

1. **edge を最も削る overlay は C3/C4 (ATR BE 0.8 → trail 1.5/0.5)** — 単独でも累積でも最大の負の寄与で、両順序仮定で一貫。BE/trail は winner の hold を中央値 25 → 6 bars に潰し (winner の 100% が 8h 以内)、payoff を 3 → 2 に落とす。「BE/Trail が Python BT の WR を +20pp 水増しする」([[project_be_trail_inflates_python_bt_wr]]) の鏡像で、**保持依存の TF 戦略では BE/trail が EV を削る側に出る**。
2. **C0 (entry 時 SL/TP 置換) は 2 番目** — 宣言 tp5 の +3.4 を −0.4 へ。内訳は what-if (§3): broker TP ×0.85 (−1.2)、低流動性 +0.2×ATR バッファ (−0.5)、SL 1.5→1.0×ATR (主因、what-if (i) は base と同一なので差分は走 0 tp5 との比較で読む)。
3. **C1 (8h cap) はこのデータでは正の寄与** (+1.6〜+2.2) — MAX_HOLD 14 本の PnL は [−86.6, −13.7, −3.0, +1.8, +15.5 … +203.3] で、8h で切られた建玉の大半は**その後 SL に落ちる負け候補**だった (tp5 exit 下では)。⚠️ これは「宣言 = tp5」上での話で、canon (flip) の winner は 8h 内完結 **0%** — **flip 形状の edge は C1 と両立しない** (走 0 flip の winner 11 本は全て 259–480 bars)。
4. **C2 (金曜クローズ) は小さな負** (−0.9〜−1.5、WEEKEND_CLOSE 4 本)。canon flip 形状なら winner 平均 ~330–460 bars ≈ 3.5–5 営業日で、**大半が金曜に打ち切られる** (走 0 flip の winner は cap 無しでも金曜を 3–4 回跨ぐ)。
5. **C5 (4h 含み損) は単独で −1.0 (9 本) だが BE/trail の後ろでは 0 本** — 打ち切り経路の重複。「負け側も打ち切られる」(09-25 訂正) は実在するが、BE/trail が先に同じ建玉を処理する。
6. **C6 近似は 32–49 本を早期に切り WR を 11–21% に落とす** — ただしサロゲート (conf/score/ADX/他戦略 stream 無し) なので**向きも大きさも判定に使わない**。
7. **winner / loser 別 hold**: 走 0 flip の loser は中央値 9 bars (p75 32) で 12/49 が 8h 超 — **C1 は canon 形状の loser も 1/4 切る**が、winner (100% が 8h 超) を全滅させる方が支配的。走 0 tp5 の loser 中央値 5.5 bars。

## §3 C0 感度 (BT 側 what-if、走 0′〜4、adverse_first、harness 未検証)

| what-if | 走 0′ EV | 走 1 | 走 2 | 走 3 | 走 4 | 順位が変わるか |
|---|---|---|---|---|---|---|
| base (ATR×1.0 / clamp / lowliq / rn / broker 0.85 / MTF 1.0) | −0.4 | +1.6 | −0.1 | −2.7 | −2.7 | — |
| (i) ATR のみ | = base (SR 未使用なので同一) | | | | | 変わらず |
| (ii) SR 優先 (port A: `find_sr_levels_weighted` 直近 500 bars、⚠️ live の fetch 本数は未確認) | **+3.0** (N 68、sr 67 / clamp_max 32) | +2.3 | +0.6 | −2.6 | −2.3 | **走 0′ の符号が変わる** (SR 採用で SL が広がり N が減る)。順位 (C3C4 最大) は不変 |
| (iii) clamp 無し | = base (ATR×1.0 ≈ 10p は 5–20p 帯内) | | | | | 変わらず |
| (iv) 低流動性バッファ無し | +0.2 | +2.1 | +0.3 | −2.6 | −2.6 | 走 0′ 符号のみ |
| (v) MTF ×1.3 | +2.1 (winner ≤8h 56%) | +2.5 | +0.9 | −2.7 | −2.7 | 走 0′〜2 の符号、走 3 以降不変 |
| (vi) rn nudge 無し | −0.2 | +1.8 | +0.1 | −2.7 | −2.7 | 微小 |
| (vii) broker TP 0.85 無し | +0.8 | +2.0 | +0.3 | −2.7 | −2.7 | 走 0′ 符号のみ |

**分解の順位 (C3C4 ≫ C0 > C6近似 > C5 ≈ C2、C1 は正) はどの what-if でも変わらない。変わるのは走 0′〜2 の符号 (SR 優先 / MTF 1.3 / broker TP 無しで正)**。live 実測率 (SR 採用率 / lowliq / rn / MTF 一致率) は `[SLTP_CONSTRUCT]` marker (PR #300、09-26 デプロイ後の fill) が溜まってから差し替える — 現時点で 0 fill。fast-SL 拡幅は未再現。

## §4 packet 用の所見 (registry 10-08、判定は書かない)

- **決裁肢 (a) の再定義が必要**: 「宣言仕様に合わせる」の宣言 = TP 5×ATR は canon の exit ではない (§0)。(a) を採るなら flip exit (PO-DN、定義は TV canon で確定要) + SL 1.5×ATR + 市場 bar 480 本 + C0〜C6 全免除 — **BE/trail 免除が最重要** (§2-1)、次に C0 免除、8h cap と金曜クローズは flip 形状と両立しない (§2-3,4)。週末ギャップ露出 + 1 建玉が最大 5 営業日拘束される。
- **(b) 現状維持 = 「BT の無い戦略」**: live の実効仕様は「SL ≈1×ATR (SR 優先時は広い) / broker TP ≈4.25×ATR / BE 0.8 / trail 1.5→0.5 / 8h / 金曜 / 4h 含み損 / SIGNAL_REVERSE」で、この形状の BT は harness 未検証の走 3〜5 しかない (向き = 負、大きさ不明)。fill を canon 検証の N に数えない規律は継続。
- **(c) shadow 降格**: 本 BT は根拠にならない (task 規律)。通常の live 損失停止規律 (Rule 2、realized N ベース) のみ。
- **harness を閉じる唯一の経路 = TV で v17 canon を再走** (Pine の再構築 → flip 定義の確定 → 同 feed で走 0 一致 → 制約付き走を Pine 側で再現)。Python 側は Massive でしか走れないので、**TV 接続が要る = 対話セッションでの user 操作 (TV desktop 起動) が前提**。それまで本頁の数字は「方向・構造のみ」。

## §5 ツール規律

- 標準ラベル: JSON `harness_unverified: true` を出力し、MD 冒頭に 🔴 バナー。harness が通るまで数値引用を許さない
- record-only: live コードを import せず (indicator は `tools/kalman_d7_v18e_python_port`、SR は `modules/indicators`)、tier / lot / 配線に触れない
- counterfactual (pin 設計): C1 flag 無しで EOD、C5 は含み益側で不発、C2 は非金曜で不発、順序仮定で同 bar の結果が SL_HIT ⇄ BE に変わることを pin。`harness_check` は canon 一致 dict で True / 本走の値で False

関連: [[kalman-d7-po-dn-flip]] (09-24 節) / [[kalman-d7-carveout-postfill-packet-2026-09-17]] / [[friction-analysis]] / [[project_kalman_live_exit_stack_mismatch_2026_09_25]] / [[2026-09-27-session]]
