# 反証: チャネル(平行線/回帰) × 15m に方向性エッジ無し (2026-06-25)

- **判定**: REJECT / 棚上げ。**再試行禁止**（この特徴量セット・チャネル定義では）。
- **rule**: R1 相当（新規エッジ評価を full statistical rigor で実施 → null）。
- **動機**: user が本番ページ (https://fx-ai-trader.onrender.com/) に描画される「平行線(チャネル)・水平線」を見て「これを活用してエッジ開発できないか」と提案。水平線(swing×touch)は [[h4-level-edge-falsification-2026-06-22]] で null 確定済みのため、未検証の**平行線(チャネル)側**を data-driven に探索した。
- **関連**: [[h4-level-edge-falsification-2026-06-22]] / [[feedback_tv_edge_discovery_loop]] / tool `tools/channel_edge_ic_explore.py`

## 対象（本番ページが実際に描くオブジェクト）
- **回帰チャネル** `get_regression_channel` (app.py): `close[i-50:i]` 線形回帰 ±2σ。学術根拠 Lo-Mamaysky-Wang(2000)/Brock(1992)。
- **平行チャネル** `find_parallel_channel` (app.py): swing高に上限・swing安に下限を fit（チャート上のオレンジ点線）。

## 手法 (Stage-1 IC, 因果性厳守)
- tool: `tools/channel_edge_ic_explore.py`（`zigzag_swing_ic_explore.py` / `h4_level_edge_explore.py` と同型）。
- 規律: 回帰は過去bar(`close[i-L+1:i+1]`)のみ・平行はFractal n=2の確定swing(`confirm_idx<=i`)のみ＝lookahead無し / train 60% (2022-01〜2024-08) / holdout不参照 / Spearman IC のみ＝閾値最適化なし / silent except 禁止。
- 特徴量8 (`reg_/par_` × `dev_sigma, pos, slope_atr, width_atr`) × ターゲット2 (`raw, abs`) × horizon3 (1h/3h/12h) = 48検定, Bonferroni α=0.05/48≈0.00104。
- **主役**: `*_dev_sigma × raw` の IC 符号で機構判別 — IC<0=平均回帰(境界反発) / IC>0=ブレイクアウト / IC≈0=エッジ無し。
- **事前登録 falsification 基準**: |IC|≥0.05 かつ p<Bonferroni かつ 6ペア中≥4ペアで同符号 → 生存。

## 結果 (6ペア: EUR_USD/GBP_USD/USD_JPY/AUD_USD/USD_CAD/EUR_JPY, N≈48k-59k/ペア)
- **CROSS-PAIR 生存ゼロ。**
- 方向性 (`*_dev_sigma`, `*_pos` × raw): meanIC ≈ −0.005〜−0.02、|IC|は閾値0.05の **1/3以下**、Bonferroni★を満たすペア=0。**平均回帰でもブレイクアウトでもない**（弱い負符号は再現するが大きさが無い）。
- `*_slope_atr × raw`: meanIC ≈ −0.005〜−0.008（傾きの弱い平均回帰=トレンド消耗の気配）だが |IC|≪0.05 で死。
- 最大|IC|は `reg_width_atr × abs` (meanIC −0.03〜−0.05) = **方向中立のボラ予測**。しかも符号がペア間で不安定（EUR_USD h4 では par_width が +0.074 だが cross では混在）で 4-of-6 を満たさず。

## 結論
**チャネル(回帰・平行線)は H4水平線と同じく「方向」を当てない。** N≈5万/ペアで方向性ICが立たない=サンプル不足でなく**本当に無い**。回帰チャネルの平均回帰仮説(Brock/Lo)は FX 15m・摩擦込みの本データでは再現せず。width のボラ予測は既存 ATR と共線で新規情報ゼロ。

## 残骸の活用余地（別タスク）
- `*_width_atr→abs` のボラ予測は ATR と冗長。単体で戦略にならず、TP/SLスケーリングは既存ATRで足りる。
- `tools/channel_edge_ic_explore.py` は他のチャネル/回帰系定義 (Donchian中心線・Keltner・別lookback) の IC 探索に再利用可能なハーネス。

## 再発防止
次に「チャネル/回帰/平行線で反発・ブレイク」系を提案する前に本ページを参照。回帰±2σ・swing平行 定義は null 確定済み。別定義を試すなら IC ハーネスで先に方向性 IC を確認してから実装。トレンドライン系で唯一生きているのは [[trendline-sweep]] (ELITE_LIVE) のみ — これは「線で反発/ブレイク」ではなく sweep(流動性狩り)構造のエッジで、本反証の対象外。
