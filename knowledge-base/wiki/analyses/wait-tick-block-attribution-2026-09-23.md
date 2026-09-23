# WAIT tick が block 帰属を汚染していた — 計数器契約バグ 3 例目 (2026-09-23)

**rule**: R3 (構造バグ / 計数器契約バグ — 365日BT スキップ、code derivation + 本番実測で文書化)
**PR**: fix/wait-guard-before-count-gates-2026-09-23
**母集団**: 本番 `gate_block_daily` 30d 窓 **2026-08-24〜2026-09-23** (Render 一次ソース、`/api/demo/block-counts?days=30`)
**関連**: [[rnb-dead-mode-and-block-estimand-2026-09-05]] (同 family 1 例目) / [[e23-adoption-watch-fix-2026-08-18]] (2 例目) / [[hull-fire-rate-funnel-2026-08-24]] §8 (本カウンタの主な消費者)

---

## 1. 結論

`_tick_entry` の `if signal == "WAIT": return` guard が **3 つの count ゲートより後ろ**に置かれていたため、建玉がある限り **WAIT tick が毎回 `hedge_block` / `max_open` として計上されていた**。

| reason | 30d 総数 | entry_type unknown/wait | 汚染率 | 真の件数 |
|---|---:|---:|---:|---:|
| `hedge_block` | 59,881 | 55,219 | **92.2%** | 4,662 |
| `max_open` | 6,501 | 5,928 | **91.2%** | 573 |
| 他の全 reason (20+) | 150,882 | 0 | **0.0%** | 150,882 |

**補正前後の順位** (30d, block reason 別):

| 順位 | 補正前 (汚染込み) | share | 補正後 (真の候補のみ) | share |
|---|---|---:|---|---:|
| 1 | **hedge_block** | 27.3% | r2_shadow_demoted_cell | 36.4% |
| 2 | r2_shadow_demoted_cell | 26.0% | no_signal | 25.0% |
| 3 | no_signal | 17.9% | order_bar_dedup | 24.9% |
| 4 | order_bar_dedup | 17.7% | score_gate | 6.4% |
| 5 | score_gate | 4.6% | **hedge_block** | **3.0%** |

⇒ **`hedge_block` は「最大の block 要因」ではなかった** (#1 27.3% → #5 3.0%)。本カウンタ由来の「最大の抑制要因」型の主張は、2026-09-23 以前のものは全て再計算が必要。

## 2. メカニズム (code derivation)

`modules/demo_trader.py` `_tick_entry`。旧実装の評価順:

```
  … score_gate / r2_shadow_demoted_cell / weekend_gap_* …   ← WAIT では述語が偽
  max_per_mode_pair  (slot cap)
  hedge_block        ← 述語 `_ot["direction"] != signal`
  max_open           ← 述語が signal 非依存 (建玉総数のみ)
  if signal == "WAIT": return   # ← コメント「WAITはカウントしない（大半がWAIT）」
```

`signal="WAIT"` のとき:

- `hedge_block`: `_ot["direction"]` は必ず `"BUY"` か `"SELL"` なので `!= "WAIT"` は**恒真**。建玉が 1 本でもあれば毎 tick 発火
- `max_open`: 述語に signal が現れない

guard 自身のコメントが「WAITはカウントしない」と宣言していたのに、**その宣言が守られていたのは guard より後ろのゲートだけ**だった。宣言と実装のズレが汚染の正体。

汚染が 2 reason に限られるのは「WAIT で述語が真になるゲート」がこの 2 つだけだからで、実測 0.0% / 92% の綺麗な二分がそれを裏づける。

## 3. estimand の妥当性検査 (この分類は本当に WAIT か)

`gate_block_daily` は `reason.split('(')[0]` で引数を捨てるため (`_record_entry_block`)、**カウンタ自身は `:WAIT` と `:BUY` を区別できない**。よって entry_type による分類が正しいことを別経路で確かめた。

1. **判別テスト (決定的)** — entry_type `unknown`/`wait` が出現する reason は **`hedge_block` と `max_open` の 2 つだけ**。`score_gate` / `conf<30` / `same_price_*` / `order_bar_dedup` / `no_signal` / `r2_shadow_demoted_cell` など**方向や実体を要求する 20+ の reason には 1 件も現れない**。「unknown 候補」が実在するなら、それらのゲートにも掛かるはずである。
2. **trade 側** — 30d の記録 trade 1,800 本に entry_type `unknown`/`wait` は **0 本** (distinct entry_type 61 種)。
3. **counterfactual (code)** — guard を旧位置に戻すと pin が落ち、ブロック理由が本番と同型の `hedge_block(daytrade/USD_JPY:WAIT)` を返す。
4. ⚠️ **Render ログは本件の検査に使えない** — `:WAIT)` の grep は 0 件だが、`[SENTINEL_BLOCK_DIAG]` は sentinel entry_type にしか出ず、WAIT sig の entry_type (`unknown`) は sentinel ではない。**不在は反証ではない** (証拠が届かない経路)。
5. **残る上界性** — 実 entry_type を持ちつつ `signal="WAIT"` を返す戦略があれば、その分は「真の件数」側に紛れる。よって **真の件数 4,662 / 573 は上界**。

## 4. 影響範囲 (引用時の注意)

本カウンタは block 帰属の**唯一の永続面**で、以下が消費者:

- [[hull-fire-rate-funnel-2026-08-24]] §8 残余帰属
- [[ps-seat-supply-remeasure-2026-09-10]] §8 / `raw/audits/ps-seat-hedge-block-snapshot-2026-09-10.md`
  — 「3 桁が立つのは 15m 側 `daytrade_eurgbp` 129 / `daytrade_audjpy` 109 のみ」「hedge_block は **AUD_JPY 固有**」の数値は WAIT 込み。
  ⚠️ ただし当該監査の**結論 (hedge_block 寄与 = 0 本)** は別経路 (`MODE_CONFIG` 実測で 3 席に対向 mode が存在せず原理的に bind 不能) で導かれており、**本汚染では覆らない**。覆るのは併記された**件数**のみ
- `/api/demo/block-counts` と `/api/demo/status` の `block_counts` を読む全ての監視・日次レポート

**引用規律**: 2026-09-23 より前の `hedge_block` / `max_open` の**件数**は、WAIT を除いた再計算なしに引用しない。他 reason の件数は汚染ゼロなので**そのまま引用可**。

## 5. 修理

guard を **3 つの count ゲートの直前**へ移動 (slot cap の手前)。

- **取引挙動は不変** — WAIT は元々どの経路でもエントリーしない。移動区間 (score_gate〜max_open) に予約・dedup・DB 書込みの副作用は無く、変化するのは block カウンタと 3 ゲートの診断ログ (`[SHADOW] Slot bypass` 等が WAIT で出なくなる) のみ
- **スコープを最小化** — 汚染ゼロだったゲート (`score_gate` / `r2_shadow_demoted_cell`) は guard より前のまま。guard を上げ過ぎると今度はそれらの正当な block が消えるため、両方向を pin した

pin: `tests/test_wait_tick_block_attribution.py` (6 本)

| # | 種別 | 内容 |
|---|---|---|
| 1 | 振る舞い | 建玉あり WAIT tick が count ゲート理由を 1 件も計上しない |
| 2 | 振る舞い | WAIT tick が trade/送信を生まない (挙動不変の確認) |
| 3 | **NG を返す既知の入力** | 本物の逆方向 SELL は従来どおり `hedge_block` される (「全部素通し」でも通るテストにしない) |
| 4 | 性質 (順序) | WAIT guard が 3 つの count ゲートすべてより前に出現 |
| 5 | 性質 | guard の出現回数 = 1 (二重挿入防止) |
| 6 | 性質 (スコープ) | 汚染ゼロゲートは guard より前のまま (fix のスコープ超過検知) |

**counterfactual 実測** (bytecode purge 後): guard を旧位置へ戻すと #1 と #4 が落ちる。#2 は両方で通る = 挙動不変の証拠。恒真な pin ではない。

## 6. 副産物: hedge 抑制の継続長は 2026-04-30 決定の前提と乖離 (未執行・R1 候補)

[[per-cell-shadow-cap-2026-04-30]] H2 は hedge shadow bypass を撤廃した際、コスト上界をこう置いた:

> 60s dedup gate が同一 (entry_type, instrument, signal) tuple で 60s ブロックするので signal 反転時は **60s 経過後に shadow 化可能**。dedup の存在により本ヘッジ bypass は不要。

実装上の抑制継続長は **dedup の 60s ではなく建玉の保有時間**である。本番 30d の closed trade N=1,798 実測:

| 指標 | 実測 |
|---|---|
| 保有時間 中央値 | **22.0 分** (= 前提 60s の約 22 倍) |
| p90 / p95 / p99 | 132.2 / 209.8 / 283.2 分 |
| 最大 | 720.0 分 (12h) |
| **≤60s の割合** | **1.61%** |

方向別の被拘束時間 (30d = 720h 窓、片方向が塞がれていた時間):

| base_mode/pair | 建玉数 | SELL 塞 (h) | BUY 塞 (h) | 片方向塞 計 (h) | 窓比 | うち shadow 単独 (h) |
|---|---:|---:|---:|---:|---:|---:|
| daytrade/USD_JPY | 479 | 126.0 | 95.8 | 218.0 | 30.3% | 213.0 |
| daytrade/GBP_USD | 302 | 70.0 | 123.3 | 189.4 | 26.3% | 189.4 |
| daytrade/EUR_USD | 191 | 58.4 | 123.5 | 180.1 | 25.0% | 180.1 |
| daytrade/AUD_JPY | 167 | 109.1 | 43.8 | 152.7 | 21.2% | 152.7 |
| daytrade/EUR_JPY | 206 | 56.8 | 64.3 | 120.8 | 16.8% | 120.8 |

建玉 1,798 本中 **1,788 本 (99.4%) が shadow** (live = `oanda_trade_id != ''` は 10 本) で、上表の被拘束時間はほぼ全て shadow 行が作っている。

**⚠️ ここから施策を導かないこと。** 判断に必要な点:

- 本節の「**真の** hedge_block = 4,662 件/30d (全 block の 3.0%)」が上の被拘束時間の経済的重みであり、**被拘束時間そのものは失われた観測数ではない** (その窓にシグナルが出た保証がない)
- 抑制が live 側にも及ぶ経路は実在する (shadow 建玉が live 候補を塞ぐ) が、`_COUNT_GATE_BYPASS_LIVE_EXCEPTIONS` の 6 type (kalman_d7 ×3 / zz_pivot ×2 / pivot_detector) は hedge を bypass する。**今月唯一 live 約定した kalman_d7 はこの免除側**なので、live 約定枯渇の説明に hedge_block を充てるのは現時点で根拠がない
- 2026-04-30 の H2 は**統計的動機**(同時刻の逆方向 sample が score-max ランキングを壊す)で採択された R2 決定である。22 分離れた別バーの sample は「同時刻の二重記録」ではないため**動機と実装のスコープはずれている**が、これを緩めるのは live 経路を含むゲート変更 = **Rule 1** (365d BT + Bonferroni + pre-reg LOCK + user 決裁)

⇒ 本 PR では**一切触らない**。registry `hedge-gate-duration-vs-2026-04-30-premise` (期日 2026-10-20) に R1 候補として起票し、判断材料 (真の件数・被拘束時間・免除集合) を凍結する。

## 7. 教訓

**計数器は「自分が数えている母集団」を述語で宣言するが、評価順序がその宣言を壊す。** 早期 return が「これは数えない」と宣言していても、その return より前のゲートには効かない。**述語が対象外入力で自明に真になるゲート**(方向比較・総数比較) は、ガードの後ろに置かれた瞬間に別物を数え始める。

本 family 3 例目 (`direction_filter` 100% WAIT / 計数器契約バグ / 本件) の共通形は「**ラベルが estimand を運ぶと信じた**」こと。8 回同じ 🔴 が出たら数字でなく定義を疑う ([[rnb-dead-mode-and-block-estimand-2026-09-05]]) の一般形として: **ゲートを追加・移動したら、その上流にある早期 return の宣言がまだ成り立つかを確認する。**
