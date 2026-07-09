# BE/Trail ablation を全 BT エンジンへ展開 (P1-2, 2026-07-09)

**Status**: 完了 (R3 構造バグ fix、live 変更なし)。**rule:R3**
**起点**: [[fable5-system-audit-2026-07-02]] P1-2 / roadmap [[roadmap-v2.3-payoff-friction-repair]] WS4 T14
**MEMORY**: `project_be_trail_inflates_python_bt_wr`

## 1. 問題

MEMORY 確定事実: BE/Trail 発動後の SL touch を **fake-WIN** (0.6×TP距離の勝ち) として
カウントするロジックが Python BT の WR を TV Pine 比 **+20pp 水増し**する
(divergence-ablation 2026-05-14、xs_momentum×USDJPY で WR 62.7%→39.8% ≈ TV 43.5%)。

daytrade エンジン (`run_daytrade_backtest`) では 2026-05-15 に `_BT_ABLATE_BE_TRAIL`
(default True、`BT_OPTIMISTIC=1` で旧挙動復元) で既に排除済みだった。しかし
**残り 3 エンジンに水増しが残存**していた (Fable5 監査 P1-2 で診断):

| エンジン | 関数 | fake-WIN 機構 |
|---|---|---|
| 1H (SR構造) | `run_backtest` | partial-TP trailing: `hi-ep >= tp_dist*0.6` で BE、SL touch を WIN 化 |
| scalp 1m/5m | `run_scalp_backtest` | ATR-BE/TS: `_fav>=ATR*0.8` で BE、`>=ATR*1.5` で trail、SL touch を WIN 化 |
| 1H zone | `run_1h_backtest` | 70%TP で BE+30%利益確保 + 1.2ATR trail、SL touch を WIN 化 |

**影響**: これら 3 エンジン由来の EV/WR を昇格判断に使うと誤判定。WS3 のシグナル
張り替え候補 (dt_fib_reversal×USD_JPY 等) の barrier/EV 評価にも直結する。

## 2. 修正 (daytrade と同期)

各エンジンの trade 生成ループ冒頭に flag を定義:
```python
_BT_OPTIMISTIC = os.environ.get("BT_OPTIMISTIC") == "1"
_BT_ABLATE_BE_TRAIL = (not _BT_OPTIMISTIC) or (os.environ.get("BT_ABLATE_BE_TRAIL") == "1")
```
- **scalp**: daytrade と同じく閾値を `float("inf")` にして BE/TS を到達不能化。
- **1H / 1H zone**: BE/Trail 発動ブロックを `if not _BT_ABLATE_BE_TRAIL:` で gate。

Time-decay SL tightening (`_current_sl=max(_current_sl,ep)`) は `_be_activated` を
セットしないため fake-WIN 経路に乗らず、ablation 対象外 (daytrade と同じ扱い)。

**cache key**: 3 エンジンの BT cache key に ablation フラグを追加
(`_abl{BT_OPTIMISTIC}{BT_ABLATE_BE_TRAIL}`)。A/B 比較で stale cache が
別モードの結果を返すのを防止 (daytrade fingerprint L6436 と同じ設計)。

## 3. 行動証拠 (fixture, `_df_override` 経由 scalp BT)

`tests/fixtures/usd_jpy_m15_2024q1.parquet` (6,095 bars) を scalp エンジンに注入:

| モード | env | N | WR |
|---|---|---|---|
| **ablated (default, 本修正)** | (なし) | 84 | **46.4%** |
| optimistic (旧挙動) | `BT_OPTIMISTIC=1` | 102 | **56.9%** |

**WR inflation = +10.5pp** を default で排除。方向・規模とも MEMORY 確定事実と整合
(fixture 依存で +20pp より小さいが、fake-WIN 機構が WR を持ち上げる方向は一致)。
N が 84→102 と変わるのは、BE 決済が後続エントリーの cooldown/eligibility を
シフトさせるため (単なる再分類ではなく trade sequence が変わる)。

## 4. 回帰テスト

`tests/test_be_trail_ablation_all_engines.py` (AST 構造 pin、offline/deterministic):
1. 4 エンジン全てで `_BT_ABLATE_BE_TRAIL` が `_BT_OPTIMISTIC` 依存で定義される
   (= default ablated) ことを pin。
2. `_be_activated = True` 代入が全て `_BT_ABLATE_BE_TRAIL` guard 配下、
   または閾値=inf ablation の配下にあることを pin (guard 除去 = inflation 再発の検知)。

## 5. 影響と後続

- **live トレード影響なし** — BT 評価ロジックのみ。本番 signal/OANDA 転送は不変。
- **過去 scalp/1H verdict の再解釈が必要** (監査 §注記): 旧 BT 結果は水増し込み。
  今後の昇格判断は本修正後の default (ablated) EV/WR を使う。
- **残 (P1-2b, P2)**: 同一バー TP+SL 同時ヒットの tie-break が `fut_close` 基準
  (保守的 SL 優先でない) — 全 4 エンジン共通の副次的楽観バイアス。別途対応
  (WS4 の後続、寄与度は BE/Trail より小)。
