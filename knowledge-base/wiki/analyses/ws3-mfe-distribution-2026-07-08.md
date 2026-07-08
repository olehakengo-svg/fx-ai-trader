# WS3 MFE 分布診断 — 「20p 走る場所」は存在するか (2026-07-08)

**Status**: 確定 (R3 純診断、live 変更なし)。**rule:R3**
**タスク**: `20260708-1130-ws3-mfe-distribution-diagnosis` / **起点**: [[exit-repair-tp-sl-prereg-2026-07-07]] §8 (T2 FAIL → WS3 全振り)
**データ**: 365d 15m BT baseline (本番 signal 関数、V2 parity 3flag、診断窓 2026-06-07〜 除外)、6 pair (GBP_USD/EUR_USD/USD_JPY/EUR_JPY/GBP_JPY/AUD_JPY)、**N=6,995 entries / 104 cells**。各 entry から forward H∈{6,12,24,48,96} bars の MFE/MAE を exit 非依存で計測。
**再現**: `tools/ws3_mfe_scan.py` / 生データ `raw/bt-results/ws3_mfe_scan_2026_07.{json,md}`

## 1. TL;DR — 問いの答えは「Yes, but」で、WS3 の選抜基準を修正する

1. **MFE の絶対量は豊富**: h24 (6h) で大半のセルが MFE p50 15〜30p、P(MFE≥20p) 0.5〜0.75 のセルが多数。**「現行シグナルは 5p しか走らない」という live 診断の数字 ([[payoff-asymmetry-diagnosis-2026-07-07]] §1 の winners MFE 5.18p) は exit 時点打ち切りのアーティファクト**と確定 (診断自身の caveat §10-2 の通り)。BE/trail が med 9 分で決済した後も、価格は平均して 20p 級まで走っていた。
2. **しかし MAE も同規模** — 母集団の MFE/MAE 比 (h24, N≥20 の 79 cells) は**中央値 0.88**。価格は走るが**シグナル方向に走らない**。これは負 EV の現実・IC null の falsification 履歴・「高WR×負EV」構造の全てと整合する。
3. **真の希少資源は「方向性非対称 (MFE ≫ MAE)」**: ratio ≥1.3 は **7/79 cells**、≥1.5 は 4/79 のみ。**WS3 の選抜基準を「MFE 絶対量 ≥20p」から「MFE/MAE 非対称 + horizon 持続性」へ修正する** (roadmap WS3 節の改訂事項)。

## 2. 方向性非対称の上位セル (h24 ratio、N≥20 のみ)

| cell | N | MFE p50 | MAE p50 | **ratio h24** | ratio h96 | P(≥20p) | 備考 |
|---|---|---|---|---|---|---|---|
| htf_false_breakout×EUR_JPY | 24 | 28.7 | 15.9 | **1.81** | 0.90 | 0.62 | 短期非対称、h96 で消滅 (減衰型) |
| trendline_sweep×EUR_USD | 45 | 20.3 | 12.3 | **1.65** | 0.82 | 0.51 | ELITE_LIVE の EUR 側。減衰型 |
| dt_sr_channel_reversal×EUR_USD | 25 | 17.5 | 11.3 | **1.55** | 1.18 | 0.44 | exit-repair 近接セル (EUR_JPY) の同戦略別ペア |
| london_fix_reversal×EUR_USD | 36 | 14.3 | 9.5 | **1.51** | 1.24 | 0.19 | 非対称はあるが絶対量小 |
| htf_false_breakout×AUD_JPY | 27 | 22.1 | 15.9 | 1.39 | 1.02 | 0.59 | |
| lin_reg_channel×EUR_USD | 24 | 19.4 | 14.0 | 1.38 | **1.94** | 0.46 | **h96 で増幅 (持続型)**。※channel 系 IC null の falsification ([[project-channel-edge-falsified]]) は「ライン接触→方向」の別仮説 — 本計測は entry 条件付き forward 分布で仮説が異なるが、慎重に扱う |
| hull_donchian_fade×EUR_USD | 46 | 17.9 | 13.8 | 1.30 | 0.97 | 0.39 | T7 retire 経路監視中のセル |
| dt_fib_reversal×USD_JPY | 24 | 23.9 | 18.5 | 1.29 | **2.05** | 0.62 | **h96 で増幅 (持続型)** |

観察:
- **減衰型 vs 持続型の分離**: 多くの上位セルは h24→h96 で非対称が消える (エントリー後 6h だけ僅かに走る) 一方、lin_reg_channel×EUR_USD / dt_fib_reversal×USD_JPY は horizon を伸ばすほど非対称が増幅 — トレンド持続性を捉えている可能性。保有時間の設計 (現行 MAX_HOLD 24 bars = 6h) がこの2型で逆になる点は張り替え設計に直結。
- GBP_JPY クラスタ (vsg/wick/sr_fib 等、MFE p50 25-33p) は絶対量最大だが ratio ~1.1-1.2 = **単に高volなだけ**。非対称なしに barrier 幾何で勝つには payoff 工学が必要で、T2 FAIL が示した通りそれは黒字化しない。

## 3. クオンツ判断 (この診断から直接主張できること・できないこと)

**できること (記述)**:
- 現行母集団の forward 価格挙動はほぼ対称 (median ratio 0.88) — 「exit を直せば勝てる」仮説の完全棄却 (T2 FAIL) の機構的裏付け
- 非対称の候補テールは存在する (7/79)。うち2つは horizon 持続型

**できないこと (禁止)**:
- 上位セルの promote — **m=79 の事後選択**であり、この標本での ratio は選択バイアス込み。N も 24-46 と小さい
- 閾値 (ratio≥1.3 等) の確定 — この標本で fit してはならない (カーブフィッティング禁止)

## 4. 次アクション (R1 pre-reg 起案の素材)

1. **候補セット固定**: 本診断の ratio≥1.3 の 7 cells + 持続型 2 cells を「探索標本由来の候補」として列挙 (この文書が固定記録)
2. **検証プロトコル (次の pre-reg で LOCK)**: (a) TV Pine canon での再現 (Python BT 不信の規律) (b) 本診断の 365d 窓と**重ならない期間** (Massive 12y データで 2024-2025 等) での out-of-sample ratio 再計測 (c) 多重性 m=9 補正 (d) 非対称→EV 変換の barrier 設計 (持続型は long-hold、減衰型は short-hold)
3. exit-repair 近接セル dt_sr_channel_reversal×EUR_JPY (EV_floor +0.41) は本診断では ratio 1.13 (h24)・0.87 (h96) — 非対称乏しく、**単独候補としては弱い**と判定材料が更新された

## 5. Caveats

1. MFE/MAE はバー粒度 (High/Low ベース、tick 未満不可視)。sequencing (どちらの barrier に先に触れるか) は本計測に含まれない — WR への変換は barrier シミュレーション (grid BT 型) が別途必要
2. ep は摩擦込み fill 価格 (BT と同一) — MFE は net 方向の走り
3. baseline BT のエントリー母集団は cooldown/HTF gate 込みの本番 parity — シグナル理論値でなく「実際に取れるエントリー」の分布
4. 診断窓除外済みだが、365d 標本自体が exploration に使われたため、**この標本での数値を promote 根拠にすることは禁止** (§3)
