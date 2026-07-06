# 反証: mtf_regime_switch の SELL 非対称は摩擦で死ぬ (2026-06-25)

- **判定**: REJECT / 棚上げ。TV の SELL 非対称は本物だが**摩擦込みで負**。現行ロジックを Live/Shadow promote しない。
- **rule**: R1 相当（TV再現 → friction判定 → drift検定 → slow-edge救済試行 を full rigor で → 負）。
- **動機**: TV Strategy Tester で `mtf_regime_switch` が「SELL 優位の非対称」を見せた。TV は本アカウントで 15m≈10ヶ月 (N≈400) しか BT できないため、Parquet 4.4年 (2022-01〜2026-05) で同一ロジックを回し、構造エッジか期間方向バイアスかを判別。
- **関連**: [[feedback_tv_edge_discovery_loop]] (Live>TV>Python BT, bb_rsi/xs_momentum と同型) / [[channel-edge-falsification-2026-06-25]] / tool `tools/mtf_regime_switch_explore.py` / TV `bt-results/tv-overlays/mtf_regime_switch-EURUSD-15m*.pine`

## 手法 (2パス, 因果性厳守)
- tool: `tools/mtf_regime_switch_explore.py`。MTF(1h/4h)は確定bar参照(lookahead無)、entry=signal bar close、exit=次bar以降intrabar SL/TP、train60%/holdout40%分離、regime×方向×session 分解。
- Pass1 friction=0 で TV 数値再現 → Pass2 friction=2.0pip(EUR_USD RT) で EV 判定。

## 結果
**Pass1 (friction=0, TV再現)**: 全期間 N=1990 PF=1.01 EV=+0.07pip。SELL非対称は**再現**: SELL PF=1.11 EV=+0.73 vs BUY PF=0.92 EV=-0.61。ただしグロスでほぼ損益分岐。

**Pass2 (friction=2.0)**: 全期間 EV=**-1.93pip** PF=0.77。全4 regime・train/holdout すべて負。
- diagnose(2) R:R算術: RANGE BEV_WR(f2.0)=53.6% vs 実WR45.3% (**-8.4pp届かず**) / TREND BEV43.7% vs 37.7% (-6.0pp)。摩擦込み損益分岐に届かない。

**drift か否か (重要)**: 無条件 SELL fwd12 = 全期間-0.033 / TRAIN+0.076(価格1.136→1.096下落) / HOLDOUT-0.196(価格1.095→1.166**上昇**)。
- RANGE SELL の signal-conditional fwd は +0.82(1h)/+1.85(3h)/+4.89pip(12h)、hit55%。無条件を ~1.9pip 上回り、**holdout の上昇相場でも SELL が勝った** → **純粋な drift ではなく本物の条件付きシグナル**。ただし fwd12=+1.85pip < 摩擦2.0pip = **sub-friction**。

**slow-edge 救済試行** (fwd48 が摩擦超なので保有延長/トレールで取れるか; RANGE SELL train/holdout):
| 出口 | train EV/PF | holdout EV/PF |
|---|---|---|
| max-hold 48 | -1.41/0.82 | +0.77/1.13 |
| trail 2.0 | +0.13/1.02 | +0.60/1.11 |
| trail 2.0 + hold48 | +0.38/1.05 | -0.10/0.98 |
| trail 3.0 + hold96 | +1.50/1.17 | **-3.41/0.61** |
- train+holdout 両正は `trail 2.0` のみだが EV+0.1〜0.6pip・PF~1.05 のノイズ域、N=147/81 小。出口を変えると符号崩壊 (保有延長で holdout 崩壊=過剰最適化)。**安定した正EV配置なし**。

## 結論
**mtf_regime_switch 全体は摩擦込みで REJECT。** TV の SELL 非対称は「本物だが極小の条件付きシグナル」で、honest multi-year cross-check では 2.0pip 摩擦を安定して超えない。[[feedback_tv_edge_discovery_loop]] の bb_rsi/xs_momentum と同型 (TVグロスで良く見え摩擦で死ぬ)。

## 残骸 / 留意
- **RANGE SELL** は無条件ドリフトを上回る残存シグナルを持つが、PF~1.05・N=147・出口依存で不安定 → **promote不可・grid-search禁止**(カーブフィット)。将来やるなら別ペアでの cross-pair 再現性 + pre-reg LOCK が前提。
- `tools/mtf_regime_switch_explore.py` は他 TV 戦略の multi-year friction cross-check ハーネスに転用可。

## 再発防止
TV で「方向非対称が強い」と見えた戦略を提案する前に本ページ参照。friction=0 のグロス非対称は摩擦で消える典型。必ず multi-year friction cross-check + drift検定 (無条件 fwd vs signal-conditional fwd) を通す。
