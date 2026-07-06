# 反証: 水平流動性 sweep & reclaim × 15m は負EV (2026-06-25)

- **判定**: REJECT / 棚上げ。**再試行禁止**（水平水準での sweep&reclaim 定義では）。
- **rule**: R1 相当（イベントEV + フィルタablation + strict + cross-pair を full rigor で → 負）。
- **動機**: チャネル反証 ([[channel-edge-falsification-2026-06-25]]) で「ライン系」発想を継続。生きている `trendline_sweep`(ELITE_LIVE, WR80%)は斜めTLの sweep 構造。「同じ sweep 構造を**水平**水準に適用すれば取れるのでは」を data-driven 検証 (Osler 2003: リテール逆指値は水平な直近高安に集中 → 大口 sweep → reclaim 反転)。
- **関連**: [[channel-edge-falsification-2026-06-25]] / [[h4-level-edge-falsification-2026-06-22]] / [[trendline-sweep]] / [[feedback_tv_edge_discovery_loop]] / tool `tools/sweep_reclaim_explore.py`

## 仮説（反証済みの「水平線反発」とは別物）
- 反証済み = 「価格が水準に来たら反転」（方向IC null）。
- 本件 = 「**wick が確定水準を貫通 → close が水準内に戻す = 他人のSL狩り (reclaim) イベント**」をトリガー。trendline_sweep が斜めTLで実証する sweep 構造を水平水準へ。

## 手法 (因果性厳守, friction込み, train/holdout)
- tool: `tools/sweep_reclaim_explore.py`。pivot=Fractal n=2 確定後のみ / entry=reclaim bar close / exit=次bar以降 intrabar SL/TP / friction=EUR_USD RT 2.0pip / train60%・holdout40%分離 / direction×session 分解。
- まずイベント単体EV → フィルタ(session/htf/adx/rsi) ablation → strict(reclaim方向確認/sweep深度/sweepバー幅) で改善するか。

## 結果
**EUR_USD イベント単体**: 全体 N=6456 WR=46.9% PF=0.79 **EV=-1.92pip** (train -2.00 / holdout -1.80, 一貫負)。R:R=1.27 → BEV≈44%、WR は +3pp で Stage2→3 ゲート(+5pp)未達。

**フィルタ ablation (どれも救済不可)**:
| filt | train EV/PF | holdout EV/PF |
|---|---|---|
| session | -1.91 / 0.81 | -1.69 / 0.82 |
| session,htf | -2.51 / 0.75 | -2.27 / 0.76 |
| session,htf,adx | -2.48 / 0.76 | -2.15 / 0.77 |
| session,htf,adx,rsi | -2.19 / 0.75 | -1.44 / 0.82 |
- htf整合は**悪化**、rsiはWR39%に低下。全組合せ PF<1。

**strict モード**: `strict-depth 0.5` が最安定だが train/holdout とも PF≈0.84・EV≈-1.55 で堅く負。`strict-reclaim+session` は train PF0.88 に見えるが **holdout PF0.77 に悪化=過剰最適化**。

**cross-pair (holdout, イベント単体)**: 6ペア全て負。AUD_USD が最良でも EV=-0.48 PF=0.94。USD_JPY -3.06 / GBP_USD -2.97 / USD_CAD -2.44 / EUR_JPY -2.24。**正EVゼロ**。

## 結論
**水平水準での sweep & reclaim は摩擦込みで頑健に負EV。** フィルタ・strict・6ペアいずれでも正に転じない。流動性狩りエッジは **斜めトレンドライン構造 ([[trendline-sweep]]) に固有**で、水平/静的ライン全般には存在しない。

これで「本番ページのライン → エッジ」発想は3系統 (水平反発=H4 / 平行チャネル / 水平sweep) すべて null/負 確定。生存は斜めTL sweep のみ。

## 残骸の活用余地（別タスク）
- `tools/sweep_reclaim_explore.py` は trendline_sweep の斜めTL 版 sweep イベントの IC/EV 再計測ハーネスに転用可（水平→斜め に level 定義を差し替え）。

## 再発防止
次に「水平 SR/高安/PDH-PDL の sweep・stop-hunt・reclaim」系を提案する前に本ページ参照。null 確定済み。sweep 構造を試すなら斜めTLに限定し、別 level 定義は IC/EV ハーネスで先に確認。
