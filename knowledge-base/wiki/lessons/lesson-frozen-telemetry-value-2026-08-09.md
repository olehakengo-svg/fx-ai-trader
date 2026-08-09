# 教訓: 計装した値が「動いているか」を判定表に入れていなかった (2026-08-09)

**分類**: 観測性 / 判定プロトコル
**発生**: DT `ctx.hour_utc` の live 凍結バグ ([[dt-ctx-hour-utc-live-freeze-2026-08-09]])
**損失**: 検出が 34 日遅れた (QUALBAR 導入 2026-07-06 → 発見 2026-08-09)。
バグ自体の潜伏は 123 日

---

## 何が起きたか

2026-07-06 (roadmap T9) に「0-fire の分母を取る」目的で `[kalman_d7] QUALBAR`
テレメトリを入れた。判定表はこうだった:

| QUALBAR 数 | 発火数 | 結論 |
|---|---|---|
| 0 | 0 | (a) 設計通り dormant — 異常なし |
| >0, 全 emit=False | 0 | (b) filter 落ち — breakdown 列で原因特定 |
| >0, emit=True あり | 0 | (c) 経路ブロック — R3 forensic 即時起票 |

実際のログは (b) に該当していた。**そして (b) の指示通り breakdown 列を見れば、
`session_pass=False` かつ `hour=12` が全行に並んでいた**。

問題は、(b) が「filter で落ちた = 市場条件が設計対象外」という**含意**を持って
書かれていたことだった。breakdown を見る動機が「どのフィルタで落ちたか」に留まり、
「そのフィルタの入力値が妥当か」まで届かなかった。結果、34 日間ログは出ていたのに
誰も `hour=12` が全行同一であることに気づかなかった。

---

## 教訓

### 1. 判定表には「値が動いているか」の欄を必ず入れる

分母を取る計装は、分母そのものが壊れうる。(b) の行は本来こう書かれるべきだった:

| QUALBAR 数 | 発火数 | 追加条件 | 結論 |
|---|---|---|---|
| >0, 全 emit=False | 0 | **breakdown 入力値が複数バーで変化している** | filter 落ち (市場条件) |
| >0, 全 emit=False | 0 | **breakdown 入力値が定数に張り付いている** | **計装/ctx のバグ — R3** |

**一般形**: テレメトリを追加するときは同時に「この値が定数だったら異常」という
不変条件を書く。時刻・価格・ATR のような本来変動する量が N バー連続で同値なら、
市場ではなくコードを疑う。

### 2. 同じ値を別経路で取り直すコードは、基盤バグの症状

`turtle_soup.py:284-287` と `london_session_breakout.py:255` は
`ctx.hour_utc` を使わず `ctx.df.index[-1].hour` から時刻を取り直していた。
これは誰かが症状に気づいて**局所的に回避した痕跡**だったが、
「なぜ ctx を信用していないのか」を遡る動きにならなかった。

**行動指針**: 既存の値を無視して別経路で取り直しているコードを見たら、
その場で「元の経路は壊れているのか?」を確認する。回避策はバグ報告である。

### 2.5. sentinel 値は「ありえない値」にする — もっともらしい既定値は回避策を無効化する

本件で最も一般化できる教訓。`ema200_reversal.py:36-48` は**正しい形の回避策**を持っていた:

```python
def _hour_utc(self, ctx):
    if ctx.bar_time is not None and hasattr(ctx.bar_time, "hour"):
        return int(ctx.bar_time.hour)
    hour = getattr(ctx, "hour_utc", None)
    if hour is not None:          # ← ここで 12 を「有効な値」として受理してしまう
        return int(hour)
    try:
        return int(ctx.df.index[-1].hour)   # ← 本来はここに落ちてほしかった
    except Exception:
        pass
    return 12
```

live では `ctx.bar_time is None` かつ `ctx.hour_utc == 12` (None ではない) のため、
**`df.index` へのフォールバックに到達できない**。この戦略の作者は多段フォールバックを
正しく書いていたのに、上流の sentinel が `None` ではなく**値域内のもっともらしい整数 12**
だったせいで回避策が無効化された。

- `hour_utc: int = 12` (dataclass default) は「未設定」と「本当に 12 時」を**区別不能**にする
- 12 は UTC 0-23 の値域内なので、どの `is not None` / `if hour:` チェックも通過する
- しかも 12 は「昼」= 一見それらしいので、ログを読んでも違和感が出にくい

**行動指針**: 「未設定」を表す既定値は `None` にするか、値域外の番兵 (`-1`) にするか、
未設定アクセスで例外を投げる。**値域内のもっともらしい値を既定にしてはいけない** —
下流の防御的フォールバックを全て黙って素通りさせる。
`SignalContext.hour_utc` は現状 `int = 12` のままだが、本 PR で live の供給元を修正したため
実害は解消済み。将来 `Optional[int] = None` へ移す場合は全消費者の `is not None` 分岐を
同時に見直すこと (今回は scope 外)。

### 3. 「一度直したバグ」は回帰テストが無ければ必ず戻る

`london_session_breakout.py:71` のコメントが証拠を残していた:

> DISABLED: context fix (2026-04-04) で hour_utc が正しく渡されるようになり、初めて実BT可能に

2026-04-04 に直り、**4 日後の 2026-04-08 (`9c849cef` DT構造改革)** で
新しいコンストラクタ経路と共に再混入した。回帰テストがあれば 4 日で検出できた。

**行動指針**: R3 修正には必ず回帰テストを同梱し、**修正前のソースで落ちることを
検証する** (落ちないテストは何も守っていない)。本件では
`tests/test_dt_ctx_hour_utc_live.py` 9 件のうち 7 件が旧ソースで落ちることを確認した。

### 4. 同一入力の解釈は 1 箇所に正規化する

`compute_daytrade_signal` の中で `bar_time` は 3 通りに解釈されていた:

| 箇所 | 降り方 | 正しさ |
|---|---|---|
| `is_trade_prohibited` (4 行上) | `bar_time or now(UTC)` | ✅ |
| `SignalContext.from_df` (scalp 経路) | `bar_time → row.name → now()` | ✅ |
| `_DtCtx(...)` 直接構築 (DT 経路) | `bar_time or **定数 12**` | ❌ |

**行動指針**: 同じ入力を複数箇所で解釈する関数では、降り方をヘルパに切り出すか、
最低限「他の箇所と同じ降り方か」をレビュー項目にする。

---

## 波及チェックリスト (今後の類似調査で使う)

0-fire / 過少発火を調べるときは、この順で:

1. 分子 (発火数) を数える — trades API
2. 分母 (qualifying bar 数) をログで取る
3. **分母の内訳の各入力値が、バー間で変化しているか確認する** ← 本件で欠けていた
4. 同じ量を別経路で取り直しているコードが無いか grep する
5. BT 経路と live 経路で当該入力の供給元が同じか確認する

---

## References

- 本体分析: [[dt-ctx-hour-utc-live-freeze-2026-08-09]]
- 計装の出典: [[pre-reg-kalman-d7-shadow-fire-recovery-2026-05-28]] §7 追補 (2026-07-06 roadmap T9)
- 同型 (監視が沈黙して執行が遅れた): MEMORY `project_t5_jpy_cap_prereg_executed` (18 日ギャップ)
- 関連: [[lesson-reactive-changes]] / MEMORY `project_engine_reconstruction_live_dedup_dead`
