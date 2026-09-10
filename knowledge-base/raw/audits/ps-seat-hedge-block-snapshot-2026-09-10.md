# ps 席 hedge_block カウンタ — 即日スナップショット (2026-09-10)

**目的**: §8-2 検証 (ps-carveout-regate、blocker-refutation-2026-09-10 の P4) が使う hedge_block 蓄積の**窓開始基準値**を確定する。`_block_counts` はプロセス内カウンタで**再デプロイの度にゼロリセット**されるため、窓開始時刻と初期値を即日記録しないと以後の読み値が解釈不能になる (rule:R3)。

## 1. 窓開始時刻 = 本日デプロイ時刻 (カウンタリセット時点)

- **現行 live deploy**: `dep-dah92lnavr4c73e7nqpg` / commit `1edd2ce2` (PR #239 merge: wg 執行契約 B) / **live 到達 2026-09-10T11:17:39Z** — Render MCP `list_deploys` 実測
- **→ §8-2 検証の窓開始時刻 = 2026-09-10T11:17:39Z**。本日はこれ以前にも 4 デプロイあり (08:24 / 10:18 / 10:34 / 11:02 finish) — 11:17:39Z より前のカウンタは全て消失済み
- **スナップショット取得時刻**: 2026-09-10T14:45:44Z (`GET /api/demo/block-counts`、蓄積時間 ~3.47h)

## 2. ps 席 5 ペアの block counts (mode 別、取得時点全ラベル)

ps 席 = `price_shock_rev_*_h1_long` ×5 (EUR_GBP / EUR_AUD / USD_CAD / NZD_JPY / AUD_JPY、全席 1000u 固定契約)。`_block_counts` は mode キーのため、各ペアの搬送 mode の全ラベルを記録する (MODE_CONFIG 実測マッピング):

| ペア | mode | hedge_block | その他ラベル |
|---|---|---|---|
| EUR_GBP | daytrade_eurgbp | **129** | order_bar_dedup 50 / session_pair 3 / same_price_0pip 1 / recent_emit 1 |
| EUR_GBP | daytrade_1h_eurgbp | 0 | order_bar_dedup 8 / session_pair 1 |
| EUR_AUD | daytrade_1h_euraud | 0 | (ラベル無し = 全 block 0) |
| USD_CAD | daytrade_1h_usdcad | 0 | order_bar_dedup 16 / recent_emit 1 / spread_wide 1 |
| NZD_JPY | daytrade_1h_nzdjpy | 0 | score_gate 23 |
| AUD_JPY | daytrade_audjpy | **109** | order_bar_dedup 44 / r2_shadow_demoted_cell 16 / recent_emit 1 / same_price_5pip 1 |
| AUD_JPY | daytrade_1h_audjpy | 0 | (ラベル無し = 全 block 0) |

## 3. hedge_block 全体像 (mode 全体、取得時点)

hedge_block を持つ全 mode: daytrade 121 / daytrade_eurgbp 129 / daytrade_audjpy 109 / daytrade_gbpusd 100 / daytrade_eurjpy 86 / daytrade_eur 64 / daytrade_1h 50 / scalp 50 / daytrade_gbpjpy 8 / scalp_5m_eur 4。**総 block 数 (全ラベル計) = 2233**。

per-strategy 側 (`per_strategy_counts`) の hedge_block 内訳: `unknown` 596 / `wait` 104 / `session_time_bias` 14 / `htf_false_breakout` 6 / `dt_sr_channel_reversal` 1 — **`price_shock_rev_*` 名義の hedge_block は取得時点で 0 件** (帰属の大半が `unknown` に落ちる点は per-strategy 帰属の既知の弱さ。§8-2 の読みは mode キー側を正とする)。

## 4. 生データ

取得 JSON 全文 (72 mode ラベル + 69 per-strategy ラベル) はセッション scratchpad `block_counts_snapshot.json` に取得済みだが、恒久保全は本ファイルの §2-§3 抜粋を SSOT とする。再取得: `curl https://fx-ai-trader.onrender.com/api/demo/block-counts` (読み取り専用 API、`?strategy=` で per-strategy filter 可)。

## 5. §8-2 検証者への注意

1. 窓開始 11:17:39Z 以後に**再デプロイが挟まれば窓は無効** — 検証時に `list_deploys` で dep-dah92lnavr4c73e7nqpg が依然 live であることを必ず確認する。無効化されていたら新 deploy 時刻から窓を引き直す (本ファイルの §2 は初期値としてではなく「~3.47h でこの規模の蓄積速度」という cadence 参照値として使う)
2. hedge_block は `_block(f"hedge_block({_base_mode}/{instrument}:{signal})")` (demo_trader.py L5198) 由来 — carry-dip の shadow 行が席の BUY を最大 18h 再抑制し得る経路 (L4600 コメント) の実測がこのカウンタの意味
3. EUR_GBP (129) と AUD_JPY (109) の 2 席のみが ~3.5h で 3 桁 — 蓄積は席間で極端に非一様。ペア別に読むこと
