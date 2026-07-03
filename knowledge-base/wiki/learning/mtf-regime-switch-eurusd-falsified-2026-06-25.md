---
title: mtf_regime_switch (EUR_USD 15m) — エッジ探索と反証
date: 2026-06-25
status: falsified
pair: EUR_USD
timeframe: 15m
rule: R1 (新戦略 365日BT相当の複数年検証)
tags: [edge-discovery, regime-switch, mean-reversion, trend-following, mtf, falsified, friction]
related:
  - "[[tv-pine-edge-discovery-framework]]"
  - "[[friction-analysis]]"
  - "[[project_h4_level_edge_falsified]]"
  - "[[feedback_tv_edge_discovery_loop]]"
  - "[[project_be_trail_inflates_python_bt_wr]]"
---

# mtf_regime_switch (EUR_USD 15m) — エッジ探索と反証

## TL;DR

レジーム切替型 MTF 戦略 (MRで逆張り / トレンドで順張り) を EUR_USD 15m で設計・検証。
TV では魅力的 (PF1.39) に見えたが、**Python 複数年 (4.4年) × friction込みで全レジーム EV マイナス**。
5角度の分解で根本原因を確定: **エントリーの生エッジ (fwd < 1pip) < friction (RT 2.0pip)**。
exit 設計 (SL拡大 / 本物ダイバ / トレール) では覆せない。**土俵 (EUR_USD 15m) の問題**であり、
レジーム切替の設計思想自体は機能 (SELL非対称を正しく検出)。MACDダイバージェンス仮説は明確に反証。

---

## 1. 設計

ユーザー要望: RSI/MACD の買われすぎ売られすぎ (MR) + 一方向トレンド時は MR を撤廃しトレンド順張り。
EMA パーフェクトオーダー判定。15m ベース、1m/5m/1h/4h を MTF 補助。

| 項目 | 設計 |
|---|---|
| レジーム判定 | 15m EMA パーフェクトオーダー (8/21/55) + 1h/4h EMA(21/55) 整合 |
| MR エントリー | RSI<30/>70 (主) + MACD ダイバージェンス確認 (逆張り) |
| トレンドエントリー | PO方向に押し目順張り。RSI>80/<20 の超極端のみブロック |
| exit | MR: SL1.2/TP1.5 ATR、トレンド: SL1.5/TP2.5 ATR、24本タイムストップ |
| 通貨/TF | EUR_USD 15m (RT friction 2.0pip) |

成果物 (すべて research/h4-level-edge ブランチ、未コミット):
- `bt-results/tv-overlays/mtf_regime_switch-EURUSD-15m.pine` — TV版A (1m/5m補助あり)
- `bt-results/tv-overlays/mtf_regime_switch-EURUSD-15m-fullhist.pine` — TV版B (1m/5mなし)
- `tools/mtf_regime_switch_explore.py` — Python 複数年クロスチェックハーネス

---

## 2. TV 結果 (10ヶ月制限)

TV アカウントは 15m BT を ~20,000 bars ≈ 10ヶ月で打ち切る (プランのバー数上限)。

| 版 | N | WR | PF | Net% | 備考 |
|---|---|---|---|---|---|
| A (1m/5m補助あり) | 349 | 47.85% | 1.39 | +0.54% | |
| B (1m/5mなし) | 403 | 48.39% | 1.42 | — | **同じ10ヶ月** |

**発見1:** 版Bは版Aと同期間。→ 履歴制限の真因は 1m/5m ではなく TV プランのバー数上限。
**発見2:** 版B (1m/5mなし) の方が N多く PF良い。→ **1m/5m 補助はエッジを足していない**。MTF補助は 1h/4h で十分。

TV Regime テーブル (版B): TREND SELL PF1.63/+44.1、RANGE SELL PF2.25 WR64.6%、
TREND BUY PF1.09、RANGE BUY PF1.07。→ SELL優位の非対称、Tokyo最弱。

---

## 3. Python 複数年クロスチェック (4.4年, N≈1990)

データ: `data/cache/massive/EUR_USD_{15m,1h,4h}.parquet`、窓 2022-01〜2026-05 (1h/4h 深度で制約)。
train/holdout = 前半60%/後半40% chronological split。entry=signal bar close、causal MTF align。

| friction | overall PF | overall EV | 含意 |
|---|---|---|---|
| 0.0 (TV相当) | 1.01 | **+0.07pip** | ≈ノイズ。frictionゼロでもエッジほぼ無し |
| 2.0 (EUR_USD RT) | 0.77 | **−1.93pip** (sum −3837pip) | 全レジーム EV マイナス |

TREND SELL は複数年で PF1.07 に劣化 (TV 10ヶ月の 1.63 は期間バイアスで誇張)。

---

## 4. 「なぜ勝てないか」5角度の分解

ユーザーの challenge (「エッジなし判断は早すぎ。なぜ勝てないか分析を」) を受けた構造分解。

### (1) エントリーの生の予測力 (exit機構を外した forward-return)
- proxy版 RANGE SELL: fwd48 **+4.89pip** hit55.9% → 一見エッジに見えた。
- しかし (2) で反証される (proxy のアーティファクト)。

### (2) MACD ダイバージェンス — 本物 (pivot) にすると仮説反証 ★最重要
| | div有 (pivot, 本物) | div無 |
|---|---|---|
| RANGE SELL fwd12 | **−3.70pip** | **+0.90pip** |
| RANGE BUY fwd12 | −1.89pip | +0.93pip |

**本物のダイバージェンスはエッジを破壊する** (遅行 — swing 確定を待つ頃には反発が終わっている)。
proxy `low<low[8] & hist>hist[8]` は別物 (V字反発エントリー) を拾うアーティファクトだった。
→ 「MACDダイバで買われすぎ/売られすぎを取る」仮説は**明確に反証**。

### (3) SL が近すぎ
SL拡大で WR 40%→58%、EV(friction0) +0.07→+0.77。だが friction2.0込みでは依然マイナス。

### (4) トレール exit (「伸びに合わせてTP調整」)
div=none, friction2.0 でトレール幅 grid (mult 1.0/1.5/2.0/3.0 × max_hold 48/96):

| config | 全期間 EV | HOLDOUT EV | PF |
|---|---|---|---|
| 固定 (現行) | −1.56 | −1.30 | 0.80 |
| trail 2.0 / mh96 (最良) | −1.40 | −1.50 | 0.82 |
| trail 1.0 | −1.99 | −2.02 | 0.59 |

**全構成 EV マイナス、固定を上回らない。**
理由: **追うべき「伸び」が無い** — TREND SELL fwd12 +0.74 ≈ fwd48 +0.78 (3h以降頭打ち)。
EUR_USD 15m は mean-reverting でトレンド継続しない。トレールは含み益を吐くだけ。

### (5) R:R 算術
両レジームとも friction後 BEV_WR (RANGE 53.6%, TREND 43.7%) に実WRが 6-8pp 届かず。

---

## 5. 根本結論

> **エントリーの生エッジ (fwd < 1pip) < friction (EUR_USD RT 2.0pip)。**
> exit 設計を何に変えても、土俵 (EUR_USD 15m) のエッジがコストより小さい限り原理的に勝てない。

- レジーム切替の**設計思想自体は機能** (SELL非対称を正しく検出)。アイデア全否定ではない。
- MACDダイバージェンスは**反証** (本物にすると逆効果)。
- 「伸びに合わせる」は**伸びがある土俵でこそ有効**。EUR_USD 15m には伸びが無い。

次に活きる方向 (未検証、仮説):
- **higher TF (1h/4h)** — 値幅大で friction比小 + トレンドの伸びが出る (トレールが活きる)
- **トレンド性の高い銘柄** (GBP系・JPYクロス) — 伸びがあり順張りSELL+トレールが機能しうる

---

## 6. プロセス上の教訓

- **初回の「falsified」判断 (friction2.0 集計EVのみ) は手順として早計**だった。
  entry-vs-exit-vs-friction を分解せず断じた。KB教訓「集計値は嘘をつく」違反。
- ユーザーの challenge を受けて分解 → 結論は5角度から堅く確認され、
  かつ**ダイバージェンス仮説の反証**という追加知見を獲得。早計に断じていたら得られなかった。
- 教訓 (既存 KB と整合): **エッジ探索では「集計EVで falsified」の前に、
  必ず (a) エントリーの生予測力 (exit除いた forward-return)、(b) friction感度、
  (c) exit設計感度 を分解せよ。** どれが律速かで打ち手が変わる。

---

## 7. 再現

```bash
# Python 複数年クロスチェック
python3 tools/mtf_regime_switch_explore.py --pair EUR_USD --friction 2.0 --diagnose
# 本物のダイバージェンスで再評価
python3 tools/mtf_regime_switch_explore.py --pair EUR_USD --friction 2.0 --div pivot --diagnose
# トレール exit
python3 tools/mtf_regime_switch_explore.py --pair EUR_USD --friction 2.0 --div none --exit trail --trail-mult 2.0 --max-hold 96
```

ハーネス CLI: `--pair --friction --diagnose --div {proxy,pivot,none} --exit {fixed,trail} --trail-mult --max-hold`
