# Pre-reg (explore): ZZ pivot確定 × 水平線ターゲット — user裁量手法の機械核 (2026-08-12)

**Status: 🔒 explore self-LOCK (本ファイル commit 時点で §2-§6 凍結)**
**Rule: R1 系探索 (新シグナル)。live 実装・OOS 接触は本 explore の範囲外。**
**起点: user 指示 2026-08-05〜12「水平線・平行線の検証は僕の見える形でやっていない、検証済みは時期尚早」→ ban-scope 全数監査 (6並列抽出) で未検証 estimand を確認済み。**

## §0 目的と主張スコープ (過大主張の再発防止)

user 裁量手法「zigzag が頂点/底を付けたら逆張りを考え始め、過去の頂点・底の水平線を反発目処に使う。実行は 15m 方向 + 1m 足形/MA/MACD/RSI(70/30)」のうち、**機械化可能な構造核**のみを測る:

> **H1: zigzag 頂点/底の確定イベントを条件に、確定時点から「最寄りの反対側ピボット水準 (目処)」への到達が、同距離の逆行より先に起きる確率的非対称が存在する (摩擦込み正EV)。**

**主張スコープの明示**: 本 explore の FAIL は「user の裁量スタック全体」を反証しない。反証されるのは上記 H1 (1H 粒度の機械核) のみ。15m/1m 執行レイヤー・裁量的ライン選択は本測定の外 (FAIL 時の次段は human-signal-stream 検証)。

## §1 差分節 (既存 falsification との estimand 不一致の根拠)

2026-08-05 の原本監査 (decision doc + ハーネスコード全数抽出) による:

| 既存反証 | テスト済み estimand | 本件との差分 |
|---|---|---|
| h4-level-edge (06-22) | 水準**タッチ**イベント×15m→固定horizon IC。TP=次wall は Stage-2 設計のみで**未実行** | entry=pivot確定 (タッチでない)、水準=**exit目処** |
| channel-edge (06-25) | 回帰±2σ/swing平行の**連続特徴量** IC×15m | イベント条件付き、水準は水平 (チャネル境界でない)、目処=exit |
| sweep-reclaim (06-25) | 水準**貫通→戻し**トリガー、TP=ATR×2固定 | トリガー=pivot確定、TP=水準そのもの |
| wave-4 #18/#19 (07-31) | D1 Donchian 失敗ブレイク / 00グリッド接近、exit-free | 水準定義=zigzagピボット由来、1H、目処race設計。#18/#19 の ban 変種族の外 |
| zigzag_swing_ic (06-25) | swing構造**連続特徴量** IC (EUR_USD のみ、\|IC\|<0.02) | イベント研究・6ペア・目処相対アウトカム。**adverse prior として明記** |

wave-4 敵対的検証の on-record 裁定「ban は TF/estimand-scoped であり identity-BAN ではない。将来提案は IC-first + 明示差分節」に従う。IC-first 条項は本件ではイベント条件付き直接測定 (permutation 検定) で充足 (連続IC より強い設計)。

## §2 凍結メカニズム定義 (ZZ Spec Visualizer v1 と同一アルゴリズム)

- **TF**: 1H (MASSIVE 15m parquet を UTC 時間境界で resample: O=first/H=max/L=min/C=last、空ビン drop)
- **ATR**: Wilder RMA (ewm alpha=1/14)、期間14
- **ZigZag**: 振幅ベース確定型。上昇レグ中: high>extP で extreme 更新、extP−low ≥ thr で「頂点確定」(確定バー=当該バー)。下降レグ鏡像。thr = ATR14(当該バー) × mult。**mult ∈ {1.0, 1.5, 2.0, 3.0} (宣言済み感度グリッド、計4)**
- **水準**: 確定済み直近 **10** ピボット (高安両方、当該イベントより前に確定したもののみ = 因果)
- **イベント**: 頂点確定 → SELL / 底確定 → BUY
- **目処 (target)**: SELL は close(確定バー) より下の低ピボット水準の最大値。BUY は上の高ピボット水準の最小値。無ければ skip (計数)
- **entry**: 確定バーの**次バー Open**。D = |entry − target| (pips)。entry が target を gap で越えていれば skip (計数)
- **primary outcome (race)**: entry から favorable barrier (=target) と adverse barrier (=entry から逆側に同距離 D) のどちらが先に触れるか。同一バー内で両方触れたら**保守的に loss**。MAX_HOLD=500 本 (1H) で未決着なら timeout: pnl = 方向符号×(Close−entry) で計上 (除外しない)
- **per-event pnl (pips)**: win=+D, loss=−D, timeout=実現net移動。全てから RT を控除

## §3 データ・窓・摩擦 (wave-1 protocol 継承)

- ペア (6): EUR_USD, GBP_USD, USD_JPY, EUR_JPY, AUD_USD, USD_CAD (`data/cache/massive/{pair}_15m.parquet`、12y 被覆確認済み 2026-08-12)
- **explore 窓: 2014-01-01 〜 2021-12-31。OOS (2022+) はハーネスが hard-clamp で不可触**
- 凍結 RT (pips): USDJPY 2.14 / EURUSD 2.00 / GBPUSD 4.53 / EURJPY 2.50 / AUDUSD 2.50 / USDCAD 2.80 (wave-1 protocol / level_fb_d1_explore_stats.py と同一)。stressed 感度 = RT×1.25 と RT_FLOOR 1.30 の両方を併記

## §4 two-pass 接触順序 (fwd-look 汚染防止)

1. **pass-1 headroom** (`--stage headroom`): イベント数 N、D の中央値、確定ラグ逆行の中央値**のみ**計算。方向アウトカム計算コードはこの stage から呼出し不能。**Gate A: per pair×mult で median(D) ≥ 10×RT かつ N ≥ 200**。生存 ≥3 pair×mult 組で pass-2 へ (組が跨る mult は問わない)
2. **pass-2 primary** (`--stage primary`): headroom verdict ファイル必須 (無ければ REFUSED)。生存組のみ race 計算

## §5 判定ゲート (explore)

- **Gate B (power)**: N ≥ 200 / 組
- **Gate C (primary)**: per-event pnl の ISO週 block sign-flip permutation (10,000 draws, seed **20260812**)、片側 p (mean>0)。**24 検定 (6ペア×4mult) を BH-FDR q=0.10** で補正
- **Gate D (friction)**: q-pass 組は stressed RT (×1.25) でも mean pnl > 0
- **Gate E (集中)**: 最大単一 ISO週寄与 ≤ 50%
- **explore verdict**: 全ゲート通過組 ≥1 で PROCEED (→ user のスペック凍結 + 本 pre-reg の OOS 拡張を**別 LOCK** で起案)。ゼロで FAIL (同型再試行禁止範囲は verdict 時に確定)
- **禁止事項**: 事後スライス (サイド別/ペア別の勝ち残り切り出しを PASS 根拠にしない)。mult グリッド外の追加探索。OOS 接触。timeout 除外への変更

## §6 可視化との対応 (user 見える形の担保)

- 本ハーネスのアルゴリズムは TV「ZZ Spec Visualizer v1」(`bt-results/tv-overlays/zz_spec_visualizer_v1.pine`) と同一。TV 側実測 (USDJPY 1H, ATR×2, ロード履歴 N=2360: 確定ラグ中央値3本 / 逆行中央値 44.1p / 目処距離中央値 25.9p) と Python 側の同統計の**整合チェックを pass-1 で必須実施** (乖離 >20% なら測定を止めて原因調査 — Live>TV>Python 序列)
- pass-2 は per-event CSV を出力し、任意イベントを TV チャート上で目視追跡可能にする

## §7 事前予測 (falsifiable、拘束力なし)

- TV 実測 (逆行44.1p > 目処残距離25.9p @ATR×2) から、**ATR×2 では負EV を予測**。エッジがあるなら「確定が早く目処が遠い」低 mult 側 (×1.0/×1.5) に出るはず
- zigzag_swing_ic の \|IC\|<0.02 (EUR_USD 連続) は adverse prior。cross-pair で立つ確率は低いと予測 (それでも測る価値 = user 指摘の未検証 estimand を数値で閉じる/開くため)

— 起案・self-LOCK: Claude (autopilot, rule:R1 explore)。user 承認事項: OOS 拡張のみ (explore は自走範囲)。

---

## §8 VERDICT: ❌ FAIL (2026-08-12、同日決着)

### 実測
- **TV 整合チェック (§6)**: ✅ Python vs TV Pine — lag 3本=3本 / adverse 43.2p vs 44.1p / D 26.4p vs 25.9p (全乖離 ≤2%)
- **pass-1 headroom**: 24 セル中 Gate A 生存 **3** (EUR_USD/USD_JPY/EUR_JPY × mult 3.0) — ぎりぎり MIN_SURVIVORS。**全 24 セルで「確定までの逆行中央値 > 目処までの残距離中央値」** (例: ×1.0 で逆行 13-20p vs 残距離 9-14p) = 確定ラグが値幅の過半を食う構造は全ペア・全感度で成立
- **pass-2 primary**: 3 セル全 FAIL — WR(decided, tie=loss) 44.2-45.9% / mean net −0.83〜−3.94p / perm p (片側 mean>0) 0.767〜0.9999 / BH-FDR 通過ゼロ

### 敵対的検証 (3並列、全て CLEAN — 2026-08-12)
1. **コードレビュー**: 因果性・off-by-one・resample 帰属・timeout 符号・permutation 実装に欠陥なし。loss_tie (decided の 8-10%) を 15m 足で実解決しても mean net −0.49〜−3.70p / p 0.66〜0.999 で FAIL 不変。全 tie を win 扱いの極端仮定でも stressed net 全セル負
2. **独立再計算** (コード非参照・仕様のみから再実装): USD_JPY×3.0 全 2,255 イベントで t/side/entry/target/D/result **完全一致**、WR 0.441715 一致
3. **死型診断**: 純 decided WR 48-51% (コイントス) − 摩擦 ~2.2p = 実測 mean net −2.42p と一致。side/年別 (2014-2021 全8年負)/lag/D 四分位/逆行幅のどの軸にも救済構造なし。**逆行幅は outcome を全く予測しない (corr +0.003)**

### 帰結
- **H1 棄却**: zigzag 頂点/底の確定イベントに方向情報は無い (1H、6ペア、explore 2014-2021)。「線=目処」exit 設計は entry 側に情報がないため作動する土台がなかった。H4 水平線 / sweep&reclaim の IC null と同型の死
- **同型再試行禁止**: 振幅型 zigzag 確定 × 逆張り × ピボット由来水準ターゲット (mult/levelsN/TF 1H-4H の摂動、race/固定 horizon の exit 変種を含む)。事後スライス (side/pair/lag/距離) からの復活提案も禁止
- **§0 スコープの再確認**: 本 FAIL は user 裁量スタック全体の反証**ではない**。15m/1m 執行レイヤー・裁量的ライン選択・トレード選別は未測定のまま。次の検証可能経路 = **user 実トレードストリームの統計検証 (human-signal-stream)** — 口座履歴 or forward マーキング
- 残置資産: 本ハーネス (tools/zz_pivot_line_target_explore.py、two-pass + 独立検証済み) / TV 可視化 (zz_spec_visualizer_v1.pine) は user 目視検証インフラとして流用可
- 検証記録: workflow wf_c0639ace-fab (ban-scope 監査) / wf_feebfceb-ae2 (敵対的検証)。イベント全件 = raw/bt-results/zz-pivot-line-target-events-2026-08-12.csv (TV チャートで任意イベント追跡可)
