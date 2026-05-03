# Parquet Schema Drift Audit — USD_JPY_5m / GBP_JPY_5m lowercase columns

date: 2026-05-03
rule: R3 (Immediate — structural data path bug)
gate_impact: Gate 1 (Scalp 枝 N-acceleration ブロック中)
discovered_during: A2-alt foreground BT execution

## 1. 発見

`tools/scalp_alt_pre_reg_bt.py --candidate bb_squeeze_breakout` (USD_JPY 5m) が以下で fail:

```
File ".../modules/indicators.py", line 21, in add_indicators
    c, h, l = df["Close"], df["High"], df["Low"]
KeyError: 'Close'
```

## 2. 根因 — parquet schema drift

`data/cache/massive/` の OHLCV parquet 24 ファイルを全数列名監査:

| Parquet | columns casing | 影響 |
|---|---|---|
| **USD_JPY_5m.parquet** | `[open, high, low, close, volume, vwap, n_transactions]` | **lowercase + 7列** |
| **GBP_JPY_5m.parquet** | `[open, high, low, close, volume, vwap, n_transactions]` | **lowercase + 7列** |
| その他 22 ファイル | `[Open, High, Low, Close, Volume, vwap]` | PascalCase + 6列 (正常) |

**24 中 2 ファイルのみ schema drift**。明確に「polygon-style backfill (lowercase + n_transactions)」が混入し、yfinance/yahoo schema (PascalCase + 6列) と共存している状態。

## 3. 影響範囲

- `modules/indicators.py:21` の `add_indicators` は **PascalCase 必須**
- 結果として **USD_JPY 5m / GBP_JPY 5m を使う全 BT パスが KeyError で死ぬ**
- A2-alt 4 候補のうち 2 候補 (USD_JPY 5m: `bb_squeeze_breakout`, `engulfing_bb`) が BT 実行不能
- `modules/bt_vec_harness.py:299` の `compute_m15_features` は M15 を使うので回避済み (M15 は全 PascalCase)

## 4. 既存 bb_squeeze JSON との関係

`knowledge-base/raw/bt-results/scalp-alt-bb_squeeze-2026-05-03.json` (87,060 token, stale) は:
- `wrapper_fingerprint` 欠如
- `stats { n=23, wins=0, losses=0 }` (算数破綻)
- `entry_breakdown wins=18` と矛盾

→ **おそらく lowercase parquet がまだ存在しなかった時点で別経路 (yfinance fetch) から生成された artifact**。現行 wrapper では再現不能。

## 5. 修正案 (実装は別タスク)

### Option A — wrapper 側で column 正規化 (R3 surgical)

`tools/scalp_alt_pre_reg_bt.py:441` を:

```python
df = df.rename(columns={c: c.title() for c in df.columns if c.lower() in {'open','high','low','close','volume'}})
df = app.add_indicators(df.copy()).dropna()
```

長所: 1 ファイル変更。`add_indicators` を保護する防御。
短所: 個別ツールごとに同じ rename を書く羽目になる。

### Option B — parquet 再生成 (data layer 修正)

`USD_JPY_5m.parquet` と `GBP_JPY_5m.parquet` を上書き:

```python
import pandas as pd
for path in ['data/cache/massive/USD_JPY_5m.parquet', 'data/cache/massive/GBP_JPY_5m.parquet']:
    df = pd.read_parquet(path)
    df = df.rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'})
    df = df[['Open','High','Low','Close','Volume','vwap']]  # n_transactions drop
    df.to_parquet(path)
```

長所: 全消費者が透過的に救済される (本番含む)。
短所: 上書き; 元の polygon backfill は失う; volume/n_transactions の差異を消すので再 backfill 時に再発する可能性。

### Option C — `_load_local_cache` 出力レイヤで正規化 (recommended)

`modules/bt_vec_harness.py:96` の `_load_local_cache` 終端に:

```python
rename_map = {c: c.title() for c in df.columns if c.lower() in {'open','high','low','close','volume'}}
if rename_map:
    df = df.rename(columns=rename_map)
return df if len(df) >= 50 else None
```

長所: 全 BT 経路 (scalp_alt_pre_reg_bt, vec_harness, etc.) が透過的に救済される。本番 `app.py:651` 等は `fetch_ohlcv` 経由なので影響なし。
短所: 1 関数を変更するが 1 関数なので blast radius は限定。

## 6. ロードマップ影響

- **Gate 1 (Scalp 枝 N-acceleration)**: USD_JPY 5m 候補 (bb_squeeze_breakout, engulfing_bb) の verdict 取得不可。EUR_USD 候補 2 件は実行:
  - `sr_channel_reversal × EUR_USD 5m`: **Promote** (N=52, WR=61.5%, Wilson_lo=48.0%, EV=+0.37, PF=2.72, Bonferroni p=0.0042 < 0.0125, max DD=14.8%)
  - `fib_reversal × EUR_USD 1m`: **INSUFFICIENT** — engine timeout (600s) 後、post-processing が 2h+ ハング。SIGTERM でも JSON 出力なし。**追加 R3 issue**: wrapper の post-engine WF split / stats が空 trade set で無限ループする可能性

## 6-2. 追加 R3 issue — wrapper post-engine hang

`fib_reversal × EUR_USD 1m` (180k bar 1m) で engine_timeout=600 が fire した後、wrapper の post-engine 処理が **2h+ で完了せず**。RSS は 848MB → 124MB に低下したが process は alive。SIGTERM で kill, multiprocessing semaphore leak warning。

**仮説**: `capture_run_scalp_trades` の trace hook が engine timeout 後に空 trades を返し、`extract_strategy_trades` または `walk_forward_split` が n=0 の edge case で無限 loop / hang。

**修正案**: `tools/scalp_alt_pre_reg_bt.py` の post-engine 処理に **30s timeout + n=0 short-circuit** を追加。verdict は INSUFFICIENT_RUNTIME として書き出す。
- 本 schema drift が他のオフライン解析や R2 / R3 / W3 タスクで再発する潜在的リスク。

## 7. 提案 next task

**`r3-parquet-schema-normalize-2026-05-03`** (Codex Rule 3 task):

- Option C (`modules/bt_vec_harness._load_local_cache` 内正規化) を実装
- USD_JPY 5m parquet で再現テスト追加
- 本番経路 (`app.py` の `add_indicators` 呼び出し) に影響しないことを単体テストで保証
- 後続: A2-alt USD_JPY 5m 2 候補 BT 再実行 → aggregate verdict 完成

## 8. データ分離確認

- 本 audit はローカル parquet (BT 用キャッシュ) のみ参照
- Live / Shadow / OANDA / 本番 DB / `.env` / production credentials への接触なし
