# Lesson: 生存者バイアス防衛コードが Time-Floor 戦略の幻想を打ち砕いた (2026-04-25)

## 背景

R&D 解剖 ([[rd-target-rescue-anatomy-2026-04-25]]) で 7 戦略の hold-time 別 EV を観察:

| Strategy | hold<5m EV | hold 20-40m EV | hold 40-80m EV |
|---|---|---|---|
| bb_squeeze_breakout | -1.5 | **+5.04** | **+11.00** |
| stoch_trend_pullback | -2.5 | +2.56 | +8.65 |
| sr_channel_reversal | -1.7 | +1.70 | +7.19 |

→ **「20分以上保持で EV+ 転換」は全戦略で観測される魅力的なパターン**.

仮説: TIME_DECAY_EXIT の早期切捨てが edge 顕在化前に勝ちトレードを切っている.

## 起こったこと

[bb-squeeze-rescue-2026-04-25](../analyses/bb-squeeze-rescue-2026-04-25.md) pre-reg で
**MAE_CATASTROPHIC_PIPS = 15** の生存者バイアス防衛コードを事前に組み込み:

```python
# bb_squeeze_rescue_bt.py:simulate_pnl()
if not floor_reached and mae >= MAE_CATASTROPHIC_PIPS:
    realized = -mae - fric_exit_half  # 強制 SL (loss) として集計
    exit_reason = "MAE_BREAKER"
    break
```

365日 BT で実行した結果:

| Cell | MAE_BREAKER 件数 | 全 trade 比率 | 期待 EV | 実測 EV |
|---|---|---|---|---|
| A0 (no floor) | 0 / 2704 | 0.0% | -0.26 (Live) | -4.39 (BT) |
| **A2 (≥20m floor)** | **~268 / 2704** | **9.9%** | **+5.04 (Live推定)** | **-4.99 (BT)** |

**期待と実測の乖離 ΔEV = -10p/trade (期待+5p → 実測-5p) → 完全な逆転**.

## 失敗の構造

Live 観測の「hold≥20m で EV+5p」は次の集計バイアスを含んでいた:

1. **生存者バイアス**: Live で hold≥20m まで残った trade は、20分耐えられた = MAE が
   ある程度浅かった trade のみ. 20分の間に -15pip 越え逆行した trade は SL_HIT or
   MANUAL_CLOSE で hold<10m に分類されていた.
2. **集計の見せかけ**: hold ビン別 EV は「ビン内に分類された trade の EV」であって、
   「強制的に hold>=20m まで保持した時の EV」ではない.

BT で「全 trade を 20分強制保持 (catastrophic MAE breaker 付き)」シミュレーションして
初めて実態が見えた:

- A2 trade 2704件中 268件 (9.9%) が **20分の間に -15pip 突破** で強制 loss
- これらの trade は Live では SL で打ち切られていたが、Time Floor 仮説では
  「20分待つ」必要があった = **追加 4-12pip の損失** を被る
- 結果 EV を -4.39 → -4.99 に悪化させた (改善どころか後退)

## 教訓

### 1. 「ビン別 EV」を見るときは生存者バイアスを必ず疑う

特に時間軸の関数 (hold 時間、bar 数等) で集計するとき、**ビン内の存在自体が
特定の条件 (耐えた、約定した、SL に届かなかった等) でフィルタされている**.

生存者バイアスのチェックリスト:
- そのビンに入る前に脱落した trade はどこにいるか?
- 強制保持シミュレーションで再評価したらどうなるか?
- catastrophic threshold (MAE/MFE 上限) を超えた trade の扱いは?

### 2. Pre-reg に生存者バイアス防衛コードを必ず組み込む

[bb-squeeze-rescue-2026-04-25 §1](../analyses/bb-squeeze-rescue-2026-04-25.md):

```python
# 防衛コード (今回機能した実例)
MAE_CATASTROPHIC_PIPS = 15.0
if not floor_reached and mae >= MAE_CATASTROPHIC_PIPS:
    realized = -mae - fric_exit_half  # 強制 SL
    exit_reason = "MAE_BREAKER"
```

これが無ければ A2 BT で「強制保持で MAE 拡大」のケースを 0 とカウントし、
**EV+5p の幻想が承認され、deploy 後に口座吹き飛ばし** になっていた可能性が高い.

### 3. Live 観測 → BT 検証 → deploy の 3 段階を厳守

「Live で観測された pattern」は仮説の出発点であって結論ではない.
BT 検証 (特に強制保持/強制実行 simulation) でバイアスを除去してから初めて
deploy 候補として検討する.

## 今後の pre-reg に追加すべき項目

すべての時間軸または特定条件強制シミュレーション系 BT には以下の防衛コードが必須:

1. **catastrophic MAE breaker**: 一定深度の逆行で強制 loss 集計
2. **infeasibility flag**: breaker 発火率 > 30% の cell は FLOOR_INFEASIBLE 警告
3. **diagnostic 出力**: 各 cell の breaker_pct を必ず summary.json に含める
4. **pre-reg 宣言**: §11 「リスク」項目で生存者バイアスを明記

## 関連

- [[bb-squeeze-rescue-result-2026-04-25]] — 本 lesson の発見元
- [[time-floor-meta-rescue-2026-04-25]] — 同種の生存者バイアスを 7 戦略横断で検定中
- [[lesson-preregistration-gate-mechanism-mismatch]] — pre-reg 設計の他の落とし穴
- [[lesson-reactive-changes]] — 一般的な反射改修の禁止
