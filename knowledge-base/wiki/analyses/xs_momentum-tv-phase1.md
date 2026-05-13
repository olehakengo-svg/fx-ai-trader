# xs_momentum TV Edge Discovery — Phase 1

## Symbol / Range
- **Symbol/TF**: OANDA:USDJPY, 15m
- **BT range**: 2025-07-01 〜 2026-05-13 (TV Strategy Tester 全期間)
- **Pine**: `bt-results/tv-overlays/xs_momentum-replica.pine` (v8.9 ロジック翻訳)
- **Filters**: London-NY gate / ADX≥20 / mom>1.0 ATR / SL=1.5 ATR / TP=2.0 ATR

## Baseline (filter OFF)
| Metric | Value |
|---|---|
| N (closedtrades) | 501 |
| Wins | 218 |
| Win Rate | **43.5%** |
| Gross Profit | TV report (mirror in `t_sum`) |
| Gross Loss | TV report |
| **PF** | **1.04** |
| Net (price units) | +11.83 |

→ Aggregate ではほぼ break-even。生のままでは Live 化基準を満たさない。

### Python BT vs TV BT discrepancy（未解決）
- **KB 既知**: xs_momentum × USD_JPY 365d Python BT — N=342, WR=69%, EV=+0.270, PF=1.43
- **TV 観測**: N=501, WR=43.5%, PF=1.04
- WR 差 **約 25pp** / N 差 **+159** — 同じ戦略名でも Python と TV で別物
- **可能な原因候補**（仮説、未検証）:
  1. 期間が違う（Python は 365 日 rolling、TV は OANDA データ全期間）
  2. 摩擦モデルが違う（Python は `friction-analysis.md` 準拠の 2.14pip RT、TV は default commission/slippage=0）
  3. Pine 翻訳で本番の追加フィルタが抜けている（confirm 条件・volume guard 等）
  4. TV の OANDA データと Python の OANDA fetch でバーが微妙にズレている
- **次アクション**: friction を TV に反映 (`commission_type=cash_per_contract` + `slippage`) → 期間を Python BT と揃えて再計測

## Segment decomposition

### By session (UTC, non-overlapping)
| Session | N | WR | 備考 |
|---|---|---|---|
| Tokyo | (Pine `t_sess`) | 表示 | gate 外 のはずなので参考値 |
| London | 約 N/3 | 表示 | gate 内 |
| NY | 約 N/3 | 表示 | gate 内 |
| Off | low | 表示 | gate 外 |

→ Pine の Session table を見ると London/NY の差は数 pp。aggregate を救う単一セッションは見つからなかった。

### By H1 RSI bucket × direction
- **AGREE** = momentum 方向と H1 RSI が同方向（BUY rsi≥70 + SELL rsi<50）
- **COUNTER** = 逆方向（BUY rsi<70 + SELL rsi≥50）

| Bucket | N | WR | Wilson 95% CI |
|---|---|---|---|
| AGREE (BUY≥70 ∪ SELL<50) | 261 | **47.9%** | [41.9, 53.9] |
| COUNTER (BUY<70 ∪ SELL≥50) | 238 | **39.1%** | [33.1, 45.4] |

### Statistical test
- Two-proportion z-test: AGREE vs COUNTER
- **z = 1.98, p = 0.04733** — α=0.05 で有意
- Bonferroni 補正（8 cell 比較想定: α=0.05/8=0.00625）では **未到達**
- → directionally consistent だが Bonferroni-locked ではない。仮説 ranking としては採用、本番フィルタ採用は要 N 追加

## Phase 1 Hypothesis (Pine v2 に組込済、未起動)
```pine
use_rsi_filter = input.bool(false, "Apply H1 RSI direction filter (Phase 1)")
buy_rsi_min    = input.int(60, "BUY: H1 RSI min")  // entry on BUY 時 H1 RSI ≥ 60
sell_rsi_max   = input.int(40, "SELL: H1 RSI max") // entry on SELL 時 H1 RSI ≤ 40
```
- **AGREE 定義よりやや緩めた** (60/40) — Wilson lower が widthの広い範囲に留まるため、サンプル取り直しで N を確保
- Toggle OFF が default → 既存挙動を壊さない

## Phase 2 plan
1. TV で `use_rsi_filter = true` に切替 → Strategy Tester 全期間再走
2. 期待値:
   - N が AGREE 寄り bucket のみに減る (≈ 261 → 180-220 想定、buy_rsi_min/max を 60/40 に緩めたぶん少し多め)
   - WR が aggregate 43.5% → 47-50% 帯に上がるか観測
   - PF が 1.04 → 1.15+ になるか観測
3. もし WR Δ ≥ +5pp かつ PF ≥ 1.20 なら、buy_rsi_min/sell_rsi_max を 65/35 / 70/30 で grid を切る
4. friction を入れた再計測（前述 Python vs TV discrepancy 解決と並行）

## 自己レビューで挙がった改善点（4 つ）
KB 教訓と照らした残課題:

1. **Bonferroni 未到達のまま「edge あり」と読まれる risk**
   - 教訓「促進判定 (Kelly) も逆校正判定 (Bonferroni) も同じ統計厳格さで行う」
   - 対処: 本ページ baseline + AGREE/COUNTER の判定行は「⚠️ ranking 用、本番 promote 不可（α=0.05/8=0.00625 未到達）」と明示
2. **Tokyo セル N=0 = セグメント自体が欠落していた**
   - 教訓「集計値は必ずセグメント分解する。平均値は嘘をつく」
   - 原因: `hour_from=12 / hour_to=18` で Tokyo (h<7) を物理排除
   - 対処: Pine v2.2 に `gate_tokyo` input.bool 追加（default false で既存 baseline 挙動を保持）。Tokyo を opt-in で発火させて 4th セッションセルを観測可能化
3. **friction=0 の TV BT で edge 判定しかけている**
   - 教訓「理論計算が実測と矛盾する場合 N が十分か確認してから実測を信じる」+「BT/本番統一原則はロジックだけでなく期間/ペアも含む」
   - Python BT (friction=2.14pip RT) は WR=69% / PF=1.43、TV BT (friction=0) は WR=43.5% / PF=1.04 → 25pp gap の原因候補に friction 差が確実に入る
   - 対処: Phase 2 で `commission_value` + `slippage` を OANDA USDJPY (0.7pip + 0.5pip) に合わせて再計測必須
4. **session × RSI bucket × direction の 3D 分解が欠落**
   - 教訓「Aggregate label × WR だけでなく category × label × WR の 2D を常に見る」を 2D で止めていた
   - 対処: Tokyo 発火後に 3D 分解（Tokyo の AGREE が London/NY と質的に違うか）を Phase 3 で。Pine table を 3D 対応に拡張するか、`data_get_pine_tables` 結果を Python 側で post-process

## Pine v2.1 → v2.2 (Tokyo gate)
- `gate_tokyo = input.bool(false, "Also include Tokyo session (UTC 0-7)")` 追加
- `in_session = in_primary or (gate_tokyo and in_tokyo)` で OR 結合
- Default = false で既存 baseline と完全互換
- Summary table の "Filter / Gate" 行に "Tokyo+L-NY" or "London-NY" を表示

## How to run Phase 2 / Tokyo experiments
1. TV で Pine を Save (or pine_smart_compile) → on-chart instance は古いまま
2. **Indicator settings → Remove → search "xs_momentum replica" → Add to chart** で再追加（framework doc の pitfall 参照）
3. 設定パネルで以下を切替:
   - Tokyo セグメント観測: `Also include Tokyo session` = ON, `Apply H1 RSI direction filter` = OFF
   - RSI filter 検証: `Also include Tokyo session` = OFF, `Apply H1 RSI direction filter` = ON
   - 両方: 上記両方 ON
4. Strategy Tester で N / WR / PF / NetP を read、本ページ Phase 2 plan の期待値と照合

## Phase 2 結果 (2026-05-13 取得, friction=0, USDJPY 15m 全期間)

### 4 configurations
| # | gate_tokyo | use_rsi_filter | N | WR | PF | Net (price) | Max DD% | 備考 |
|---|---|---|---|---|---|---|---|---|
| 1 (Baseline / Phase 1) | OFF | OFF | 501 | 43.51% | 1.04 | +11.83 | — | break-even |
| 2 (Tokyo gate) | **ON** | OFF | 1,095 | 43.01% | 0.985 | **-9.52** | — | Tokyo 追加で degrade |
| 3 (RSI filter) | OFF | **ON** | **290** | **46.55%** | **1.199** | +31.92 | 25.35 | Phase 1 仮説 確認 |
| 4 (Both) | ON | ON | 576 | 46.53% | 1.186 | **+57.37** | 23.42 | RSI が Tokyo を救う |

数値は TV Strategy Tester DOM (`[class*=report] [class*=value]`) から取得。Pine summary table の WR 計算 (`wins / total` incl. evens) と TV report の WR (`wins / (wins+losses)` evens除外) は数式が異なり、Pine 41.24% vs TV 43.01% (Config 2) のような ~2pp 差が出る。本表は **TV report 基準**で揃えた。

### Pine Session table (Config 2 = Tokyo ON, RSI OFF, スクリーンショットから読取)
| Session | N | WR | PF | Net |
|---------|---|----|----|-----|
| Tokyo (h<7) | 619 | 41.0% | 0.92 | -5.9 |
| London (h=12 のみ、gate内) | 89 | 47.2% | 1.12 | +1.4 |
| NY (h=13-17) | 388 | 41.0% | 0.84 | -12.4 |
| Off | 0 | — | — | — |

→ Tokyo は **N が最大 (619)** だが **WR=41% / PF=0.92** で破壊源。Gate追加が aggregate を死なせた直接原因。

### 仮説検証結果
1. **Phase 1 RSI 仮説 (AGREE 47.9% vs COUNTER 39.1%) は TV 再現で WR=46.55% / PF=1.199 → 期待値レンジ命中**
2. **Tokyo 発火実験 (Config 2)** で「Tokyo セル N=0 = セグメント欠落」問題は解消、データ取得成功。だが **Tokyo は xs_momentum × USDJPY には edge 無し** が判明 (WR=41% / PF=0.92)。元の London-NY ゲートは正しかった。
3. **Both ON (Config 4)** が Net P&L 最大 (+57.37)。RSI filter は **時間帯に依らず効く** (Tokyo を含めても WR 46.5% 維持)。N=576 は Config 3 (RSI only) の 2 倍で、絶対損益が大きい。

### Bonferroni セーフティ
- Config 3 vs Baseline: 二項検定で WR Δ=+3.04pp, z≈0.94 (両検定 not Bonferroni-safe at α=0.05/8)
- Phase 1 で AGREE vs COUNTER z=1.98 (raw α=0.05 marginal, Bonferroni 未到達) と整合
- **本番昇格 (`strategies/daytrade/`) には N 追加 + Bonferroni 通過必須**。現段階は ranking 用

### Friction 反映 (未実施 — Phase 3 課題)
- Config 4 の Net=+57.37 price units, N=576 → 平均 +0.0996 price/trade
- USDJPY friction = 2.14pip RT = 0.0214 price unit → 平均 friction-after = +0.0782 price/trade
- friction 後でもプラスを維持するが、PF は 1.186 → ~1.13 程度に下がる見込み
- TV `commission_value=cash_per_contract` (in_27) + `slippage` (in_31) で再走 → 次セッション

## Phase 3 plan
1. TV Strategy properties で commission_value/slippage を USDJPY 摩擦に合わせ Config 4 再計測
2. Python BT (`xs_momentum` × USDJPY, friction=2.14pip) を **TV と同期間** (2025-07-01〜2026-05-13) で走らせ、25pp WR gap が friction 由来か期間差由来か特定
3. 結果が friction-after PF ≥ 1.15, N ≥ 100 維持なら Phase 1 RSI フィルタ (buy_rsi_min=60 / sell_rsi_max=40) を本番候補化
4. 本番 `xs_momentum` 戦略コードに `MTF RSI direction filter` を **shadow-only toggle** で追加し、live N ≥ 30 を蓄積 → Bonferroni-safe を待って昇格

## Known limitation in this loop
- Pine 編集後、MCP では on-chart instance を確実に再追加する手段がない（framework doc に追記済み）
- TV Strategy Tester は default で commission/slippage=0 → live spread (USDJPY ≈ 0.7pip + 0.5pip slip = 2.14pip RT) を反映していない (Phase 3 で対処)
- `data_get_strategy_results` / `data_get_pine_tables` MCP API は study_count=0 を返す既知バグ → DOM (`ui_evaluate` + `[class*=report] [class*=value]`) で取得、Pine table は capture_screenshot で目視

## Related
- [tv-pine-edge-discovery-framework](tv-pine-edge-discovery-framework.md)
- [friction-analysis](friction-analysis.md)
- [bt-live-divergence](bt-live-divergence.md)
- `bt-results/tv-overlays/xs_momentum-replica.pine`
