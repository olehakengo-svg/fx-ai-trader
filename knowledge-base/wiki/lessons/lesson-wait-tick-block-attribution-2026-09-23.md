# Lesson: ガードより前のゲートは、ガードの宣言を守らない (2026-09-23)

**発見日**: 2026-09-23 | **rule**: R3 | **計数器契約バグ 3 例目
**分析**: [[wait-tick-block-attribution-2026-09-23]] | **同 family**: [[rnb-dead-mode-and-block-estimand-2026-09-05]] (1 例目) / E23 計数器契約バグ 2026-08-18 (2 例目)

---

## 問題

`modules/demo_trader.py` `_tick_entry` の

```python
if signal == "WAIT":
    return  # WAITはカウントしない（大半がWAIT）
```

が、3 つの count ゲート (`max_per_mode_pair` / `hedge_block` / `max_open`) の **後ろ**に置かれていた。結果、建玉が 1 本でもある限り **WAIT tick が毎 tick それらの理由名で計上**されていた。

## 症状

本番 30d (`gate_block_daily`、2026-08-24〜09-23) で `hedge_block` が **block 理由 #1 = 59,881 件 (27.3%)** に見えた。

入口になった算数の不整合: OANDA 建玉 0 本の時間帯に、`daytrade:hedge_block` が **75 分で 79 件**立っていた。ヘッジ防止は「逆方向の建玉がある」ことが前提なので、建玉ゼロでこの頻度は成立しない。

## 原因

述語が **対象外入力で自明に真** になる 2 ゲートだけが汚染された。

- `hedge_block`: 述語は `_ot["direction"] != signal`。`_ot["direction"]` は必ず `"BUY"`/`"SELL"` なので `signal="WAIT"` では**恒真**
- `max_open`: 述語に `signal` が現れない (建玉総数のみ)

guard 自身のコメントが「WAITはカウントしない」と宣言していたのに、**その宣言が効いていたのは guard より後ろのゲートだけ**だった。宣言の射程 = ソース上の位置、という当たり前が抜けていた。

汚染率が `hedge_block` 92.2% / `max_open` 91.2% に対し **他の 20+ reason はすべて 0.0%** という綺麗な二分が、この機構の指紋になっている。

## 影響

補正後の真の順位は `hedge_block` **#1 (27.3%) → #5 (3.0%)**。真の #1 は `r2_shadow_demoted_cell` (36.4%)。

このカウンタは block 帰属の唯一の永続面で、hull funnel §8 残余帰属・ps-seat 供給監査・日次監視がすべて読んでいる。**2026-09-23 以前の `hedge_block` / `max_open` の件数は再計算なしに引用してはならない** (他 reason は汚染ゼロでそのまま可)。

## 検査 (この分類が本当に WAIT だと言えるか)

カウンタは `_record_entry_block` の `reason.split('(')[0]` で `:WAIT` 引数を捨てるため、**自分では WAIT と BUY を区別できない**。別経路で確定させた:

1. **判別テスト** — entry_type `unknown`/`wait` が現れる reason は `hedge_block` と `max_open` の **2 つだけ**。`score_gate` / `conf<30` / `same_price_*` / `order_bar_dedup` など方向や実体を要求する 20+ の reason には **1 件も現れない**
2. **trade 側** — 30d の記録 trade 1,800 本に entry_type `unknown`/`wait` は **0 本**
3. **counterfactual** — guard を旧位置に戻すと pin が落ち、本番と同型の `hedge_block(daytrade/USD_JPY:WAIT)` を返す
4. ⚠️ **反証に使えなかった証拠** — Render ログの `:WAIT)` grep は 0 件だが、`[SENTINEL_BLOCK_DIAG]` は sentinel entry_type にしか出ず、WAIT sig の `unknown` は sentinel ではない。**証拠が届かない経路の不在は不在の証拠ではない**

## 修正

guard を 3 つの count ゲートの直前へ移動。**取引挙動は不変** — WAIT は元々どの経路でもエントリーせず、移動区間に予約・dedup・DB 書込みの副作用は無い。

スコープは最小化した: 汚染ゼロだった `score_gate` / `r2_shadow_demoted_cell` は guard より**前のまま**にし、それを性質 pin で固定した。guard を上げ過ぎると今度はそれらの正当な block が消えるため ([[lesson-symmetric-side-check-2026-09-19]] の「自分が足したガードはほぼ毎回『広すぎる』方向に壊れる」の反映)。

pin: `tests/test_wait_tick_block_attribution.py` 6 本 (振る舞い 2 / **NG を返す既知の入力** 1 / 性質 3)。counterfactual は bytecode purge 後に実測。

## 教訓

**早期 return が「これは数えない」と宣言しても、その return より前のゲートには効かない。述語が対象外入力で自明に真になるゲート (方向比較・総数比較) は、ガードの後ろに置かれた瞬間に別物を数え始める。**

- ゲートを追加・移動したら、**上流にある早期 return の宣言がまだ成り立つか**を確認する
- カウンタが引数を捨てる設計なら、それは **自分の estimand を自己申告できない** ということ。分類は必ず別経路で検査する
- 証拠が構造的に届かない経路 (sentinel 限定ログなど) の **不在を反証に使わない**
- 本 family 3 例目の共通形は「**ラベルが estimand を運ぶと信じた**」。数字が直感と合わないとき、まず疑うのは数字ではなく定義
