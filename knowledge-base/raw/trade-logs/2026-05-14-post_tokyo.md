# Post-Tokyo Report: 2026-05-14

## Analyst Report
# Post-Tokyo Session Report（JST 15:00 / UTC 06:00）
**生成時刻: 2026-05-14 08:44 UTC**

---

## 1. 東京セッション結果

| 項目 | 値 |
|---|---|
| セッション時間 | UTC 00:00–06:00 |
| トレード数（N） | 1 |
| WR | 100.0%（参考値：N<5） |
| PnL | **+1.9 pips** |
| 対象戦略 | vsg_jpy_reversal / EUR_JPY |

> ⚠️ **N=1は統計的に無意味**。単独セッション結果として解釈せず、傾向把握の参考値として扱う。

---

## 2. What Worked

| 戦略 | ペア | 方向 | PnL | 成功要因 |
|---|---|---|---|---|
| vsg_jpy_reversal | EUR_JPY | BUY | +1.9 pips | EUR_JPY RANGING＋ATR%ile=83%という高ボラ環境で、逆張り系の短期リバーサルが機能。SL/TP到達による適切なポジション管理。 |

---

## 3. What Didn't Work

**失敗トレード: 該当なし**（N=1のため損失トレードゼロ）

ただし、**実質的な失敗**として以下を記録：

- **シグナル発生が極めて低調**：17モード稼働中（ONは12モード）で東京セッション成立トレードは1件のみ
- **ブロック主因**（参考）：
  - `scalp_eur` / `scalp` / `scalp_5m`: `r2_shadow_demoted_cell`による大量ブロック（合計21件）
  - `hedge_block` 多発（daytrade系4戦略で31件合計）
  - `rnb_usdjpy`: `direction_filter`で7件全止め

---

## 4. 戦略調整判断

**判断: NO（パラメータ変更なし）**

| 戦略 | 状況 | 判断根拠 |
|---|---|---|
| vsg_jpy_reversal | N=1（Sentinel）、Cutoff後累計N=3 | N=30到達前。判断不可 |
| scalp_eur | r2_shadow_demoted_cellブロック13件 | Shadow demote済みセルが機能している。正常動作 |
| rnb_usdjpy | direction_filter 7件止め | フィルタが現レジームを拒絶中。これはフィルタの正常動作 |
| xs_momentum (GBP_USD) | WR_Live=25% vs WR_BT=63.5%、ΔWR=▲38.5pp 🔴 | N_Live=4で判断には不足。ただし要注視 |

> **パラメータ変更の必要条件（N≥30）を満たす戦略が現在ゼロ**。変更判断の根拠が存在しない。

---

## 5. ロンドンセッション準備（UTC 07:00–16:00）

### ATR/レジーム変化予測

| 観点 | 現況 → ロンドン予測 |
|---|---|
| EUR_JPY | RANGING、ATR%ile=83%（高）→ ロンドン初動でスプレッド拡大、ボラ持続の可能性 |
| EUR_USD | RANGING、ATR%ile=36%（低）→ 欧州経済指標次第でブレイク候補、ただし現状は静穏 |
| GBP_JPY | RANGING、ATR%ile=79%（高）→ ロンドン参入でトレンド発生リスクあり、hedge_blockが継続する可能性 |
| GBP_USD | RANGING、ATR%ile=53%（中）→ 中立。スキャルプ・DTともに発動余地あり |
| USD_JPY | RANGING、ATR%ile=78%（高）→ SMA20 Slope=-0.0029でJPY強め継続。reversal系に不利 |

**全ペアがRANGINGレジーム**。SMA20 Slopeはほぼ全通貨でJPY強（マイナス傾斜）。トレンドフォロー戦略には不利な環境が継続。

### 推奨戦略配分

| 優先度 | 戦略 | ペア | 根拠 |
|---|---|---|---|
| 監視継続 | vsg_jpy_reversal | EUR_JPY | 今日唯一の成立戦略。RANGING×高ATRで相性あり |
| 期待低 | daytrade系全般 | 全ペア | hedge_blockが多発中。ロンドン移行後も即座の改善は見込みにくい |
| 要注視のみ | xs_momentum | GBP_USD | BT比▲38.5pp乖離あり。N=4でアクションは早いがモニタリング継続 |

**→ NO ACTION推奨**

**根拠:**
1. N<5のSentinel戦略ばかりで判断基準（N≥30）に達している戦略がゼロ
2. DD=28.01%でDD防御0.2x発動中（Kelly縮小状態）
3. 全ペアRANGINGかつJPY強で、方向性が定まらない環境
4. OANDA転送率8%（50件中4件のみ本番送信）＝Shadow運用主体のフェーズ。この段階でアクションを起こすべき根拠がない

---

## 6. クオンツ見解

### 最重要シグナル

**⚠️ xs_momentum (GBP_USD): BT乖離▲38.5pp（WR 63.5%→25%）— N=4の早期警戒信号**

N=4はまだ統計的に「ノイズ」の範疇だが、乖離幅▲38.5ppは平均回帰で説明しにくい水準。現在のGBP_USD RANGING（ATR%ile=53%）環境ではモメンタム戦略の構造的相性劣化が疑われる。**N=15到達時点で中間審査を実施し、N=30を待たずに傾向をトラッキングすること**を強く推奨する。

---

**構造的観察（補足）:**

本日の最大の観察は「17モード稼働中、東京セッションで1件しか成立しなかった」という**フィルタ過剰遮断の可能性**である。block_countの内訳を見ると、hedge_block（31件）・r2_shadow_demoted_cell（21件）・direction_filter（7件）が大半を占める。これらは設計通りの動作だが、**有効なシグナルをすべて食い尽くしているとすれば、Sentinel N蓄積速度の問題でもある**。月利100%目標に対し、データ蓄積速度が最大のボトルネックになっている状態が続いている。
