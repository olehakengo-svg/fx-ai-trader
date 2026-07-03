# Lesson — TV BT Cache Stale + Pine→Python Port Bug が偽 edge を捏造 (2026-06-03)

## 事案

Kalman D7 v18e LIVE (USDJPY M15、本番稼働中) を **JPY cross 3 pair (EURJPY/GBPJPY/AUDJPY) に展開試行**。TradingView Strategy Tester で:

- **AUDJPY: PF 1.606 (N=72 WR 68%)** — USDJPY 本家 (PF 1.184) 圧倒
- **GBPJPY: PF 1.235 (N=128)** — USDJPY 超え
- **EURJPY: PF 1.039 (N=106)** — 控えめ

「Cross-pair edge 発見、shadow promote 候補!」と判断しかけた。

## 真相

3 つの問題が重なって**偽 edge を捏造**していた:

### 1. TV cache stale (~10-23% PF inflation)

Strategy Tester の "Date Range: Last 365 days" 上で**前回 BT 結果がキャッシュ残存**。"All / 5Y" タブで長期 TF (1W, 1M) load 後 M15 に戻すと、TV は新しいデータで recompute しないまま古い数字を表示。`"Update report"` ボタン押すと真の数字に refresh:

| Pair | TV stale (Stage 0) | TV refreshed | 差 |
|---|---:|---:|---:|
| USDJPY | PF 1.184, N=58 | PF 1.089, N=71 | -9% |
| AUDJPY | PF 1.606, N=72 | PF 1.372, N=90 | -23% |

### 2. Python port `strategy.exit` semantics 誤実装 (~25% PF deflation)

Pine `process_orders_on_close=true` 下では **`strategy.exit` の stop fill も next-bar-open** で execute される (intra-bar OHLC fire ではない)。私の最初の Python port は intra-bar high/low check で stop fire → systematic に **早期 exit → 余分な entry signal を捕獲** (AUDJPY +38 trades, GBPJPY +23 trades, USDJPY +5 trades)。

修正後 (Codex agent `codex:codex-rescue` が next-open exit を implement):
- USDJPY: PF 0.879 → **1.101** (TV 1.089 と 1% 一致 ✅)
- AUDJPY: PF 0.647 → **1.097** (TV 1.372 とまだ 20% gap)

### 3. Data feed 差 (AUDJPY 20% residual gap)

修正後 port でも AUDJPY だけ TV と 20% gap 残存。原因:
- MASSIVE parquet (Polygon-derived aggregation) ≠ TV (OANDA-direct feed)
- AUDJPY parquet end 2026-06-01 vs TV target 2026-06-03 (window 2-day 差)

USDJPY (data 差小) は port-fix だけで TV と一致したのに、AUDJPY は data 差が visible。Cross-pair edge claim は**同じ data source で port 検証必須** (TV-only or MASSIVE-only では決まらない)。

## 真の edge picture (修正版 Python = ground truth)

| Pair | Stage 0 TV | Refresh TV | Corrected Python |
|---|---:|---:|---:|
| USDJPY | 1.184 | 1.089 | **1.101** |
| EURJPY | 1.039 | — | **1.076** |
| GBPJPY | 1.235 | — | 0.987 |
| AUDJPY | **1.606** | 1.372 | **1.097** |

→ **AUDJPY は USDJPY と同程度の marginal edge (PF ~1.10)**、Stage 0 の "1.6 圧倒" は幻。

## 反省

1. **TV BT cache を信用するな**: "Update report" ボタンが出ているうちは stale 確定。"All / 5Y" 操作後は特に注意。
2. **TV-only BT で promote 判断するな**: 独立 implementation (Python BT 等) で再現確認しないと bug + cache が偽 edge を生む
3. **`process_orders_on_close=true` の semantics を熟知せよ**: exit にも適用、intra-bar OHLC simulation は誤実装パターン
4. **Cross-pair claim は同じ data source で検証必須**: MASSIVE vs OANDA で 20% PF 動く

## 適用 Rule

- Rule R1 (Slow & Strict pair promotion) 完全適用: 365日BT (実施済、修正済 port で), Bonferroni m≥pair数, Pre-reg LOCK 必須
- Shadow-first: PF 1.07-1.10 では Live 直行不可、shadow tier で N≥30 蓄積 + BH-FDR 後判定

## 関連

- Pine source (canonical): `/Users/jg-n-012/test/kalman_d7_strategies/v18e_05ATR_trail.pine`
- Python port (修正済): `/Users/jg-n-012/test/fx-ai-trader/tools/kalman_d7_v18e_jpy_cross_bt.py`
- Memory: `project_kalman_d7_jpy_cross_2026_06_03.md`
- 既存教訓: `feedback_codex_mock_test_trap.md` (本件は典型再現), `feedback_bt_must_use_massive.md` (MASSIVE 必須だが OANDA との差も意識せよ)
