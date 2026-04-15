# マクロ補助データ分析プロトコル

## 目的

DXY/VIX/TNX/JPY先物はBTフィルターに使用されているが、事後分析で活用されていない。
補助データを「取得するだけ」ではなく「分析に使う」ためのフロー。

## 補助データ一覧

| データ | ソース | 用途 | 分析観点 |
|---|---|---|---|
| DXY (ドル指数) | yFinance `DX-Y.NYB` | ドル強弱マクロ判定 | DXY方向×ペア×WR |
| VIX (恐怖指数) | yFinance `^VIX` | ボラティリティレジーム | VIXレベル×戦略×WR |
| TNX (米10年金利) | yFinance `^TNX` | 金利差ファンダメンタル | 金利変動×通貨ペア |
| JPY先物 (6J=F) | yFinance `6J=F` | 円ポジショニング | JPYモメンタム×戦略 |

## 分析フロー（BT実行後に必ず実施）

### Step 1: VIXレジーム別分析

```
低VIX (< 15):   リスクオン → キャリートレード有利
中VIX (15-25):  通常環境
高VIX (> 25):   リスクオフ → JPY買い/安全通貨強化

分析: 各戦略のWR/EVをVIXレジーム別に集計
期待: vix_carry_unwindは高VIX時のみ正EV
     session_time_biasはVIX非依存（時間帯効果）
```

### Step 2: DXY方向別分析

```
DXY上昇: USD強 → USD_JPY BUY/EUR_USD SELL有利
DXY下降: USD弱 → USD_JPY SELL/EUR_USD BUY有利
DXYレンジ: 方向不明 → MR戦略有利

分析: DXY 20日移動平均の傾き → 上昇/下降/レンジ分類
     各分類×ペア×戦略のWR/EV
```

### Step 3: 3次元クロス分析

```
時間帯 × VIXレジーム × 戦略 → WR/EV
例: 「London session × 低VIX × session_time_bias → WR=85%」
   「NY session × 高VIX × vix_carry_unwind → WR=75%」

目的: マクロ条件付きαの発見
     「この条件の時にだけ正EVな戦略」を特定
```

### Step 4: 判断への反映

分析結果に基づき:
1. マクロ条件付きで発火/抑制するフィルターの改善提案
2. VIXレジーム別の戦略ウェイト調整の根拠
3. 新しいマクロ条件付きエッジの仮説生成

**注意**: 分析結果をパラメータ変更に使う場合は判断プロトコル（CLAUDE.md）に従う。
365日BT or Live N≥30の根拠が必要。1回のBT分析だけでフィルター追加は禁止。

## BT実行時の補助データ方針

- **本番**: DXY/VIX/TNX/JPY先物を取得継続
- **BT**: 補助データ取得を維持（スキップしない）
- **理由**: 補助データはフィルターとして結果に影響する。スキップするとBT/Live乖離が発生
- **代償**: BT実行時間が1ペアあたり+30-60秒（補助データ取得待ち）
- **対策**: 補助データもParquetキャッシュに追加することで高速化可能（将来実装）

## Related
- [[friction-analysis]] — ペア別摩擦
- [[bt-live-divergence]] — 6つの構造的楽観バイアス
- [[roadmap-v2.1]] — 戦略ポートフォリオ
- [[lesson-reactive-changes]] — 分析と対策の分離
