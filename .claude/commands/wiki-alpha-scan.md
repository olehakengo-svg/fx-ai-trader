# Alpha Scan — ファクター分解によるアルファ自動探索

本番トレードデータを多次元ファクター分解し、正EVセルと負EVセルを自動検出する。
**目的: エッジがどこに隠れているか（攻め）と、どこで漏れているか（止血）を同時に発見する。**

## 実行手順

### Step 1: 単因子スキャン
以下の各因子で`/api/demo/factors`を実行し、正EV/負EVを特定:

```
GET /api/demo/factors?factors=strategy&min_n=5
GET /api/demo/factors?factors=instrument&min_n=5
GET /api/demo/factors?factors=direction&min_n=5
GET /api/demo/factors?factors=hour&min_n=5
GET /api/demo/factors?factors=regime&min_n=5
GET /api/demo/factors?factors=confidence&min_n=5
GET /api/demo/factors?factors=close_reason&min_n=5
GET /api/demo/factors?factors=holding_time&min_n=5
GET /api/demo/factors?factors=spread_tier&min_n=5
```

各結果からEV>0のセルを「正EV候補」、EV<-1.0のセルを「毒性候補」として記録。

### Step 2: 2因子交差スキャン
Step 1で有望だった因子の組合せで交差分解:

```
GET /api/demo/factors?factors=hour,instrument&min_n=5
GET /api/demo/factors?factors=strategy,instrument&min_n=5
GET /api/demo/factors?factors=direction,instrument&min_n=5
GET /api/demo/factors?factors=regime,strategy&min_n=5
GET /api/demo/factors?factors=direction,regime&min_n=5
GET /api/demo/factors?factors=confidence,strategy&min_n=5
```

### Step 3: 3因子深掘り（正EV候補のみ）
Step 2で発見された正EVセル（EV>+0.5, N≥10）に対して3因子で深掘り:

```
GET /api/demo/factors?factors=hour,instrument,direction&min_n=5
GET /api/demo/factors?factors=strategy,instrument,regime&min_n=5
```

### Step 4: 統計検定
正EVセル（EV>0, N≥10）に対して:
- **二項検定**: WR > BEV(breakeven WR)かどうか
- **DSR**: 多重検定補正後も有意か（N_trials = 総セル数）
- **Kelly**: 正なら賭ける価値あり、負なら偽陽性

### Step 5: 結果をKBに記録
`knowledge-base/raw/audits/alpha-scan-YYYY-MM-DD.md` に保存:

```markdown
# Alpha Scan: YYYY-MM-DD

## 正EV候補 (sorted by EV, DSR-filtered)
| Factors | N | WR | EV | PF | Kelly | DSR | Action |
|---------|---|-----|-----|-----|-------|-----|--------|

## 毒性候補 (sorted by total PnL damage)
| Factors | N | WR | EV | PnL | Action |
|---------|---|-----|-----|------|--------|

## 推奨アクション
- PROMOTE候補: [...]
- BLOCK候補: [...]
- 新戦略仮説: [...]
```

### Step 6: BT検証（正EV候補のみ）
alpha-scanで発見された正EVセルをBTで独立検証:
- `/api/backtest-long` で該当ペア×期間を実行
- BT結果と本番結果の乖離を計算
- 乖離<10ppなら信頼できるエッジ

## ルール
- **全数値はAPI実測値** — 推測禁止
- **XAU除外、Shadow除外** — FX-only non-shadow
- **N<5のセルは無視** — 統計的に無意味
- **多重検定を意識** — 100セル検査すればEV>0が5個出るのは偶然。DSRで補正
- **毒性候補の除去はアルファ発見と同等の価値** — 止血も攻め
