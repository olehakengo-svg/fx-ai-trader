# Live-Bleeder Demotions — 2026-07-02 (rule:R2)

**Rule**: R2（損失停止/demotion — 数トレード〜N=10で即断可）
**目的**: roadmap v2.2 **M2**（負けクラスタ寄与 > -10p/30d）への直接寄与。負けLIVE経路を閉じ、Shadow蓄積は全量維持（原則3）。
**根拠データ**: 本番 Render API 実測 2026-07-02（`/api/demo/stats?live_only=true` 30d rolling n=112 + `/api/demo/trades` 個票）
**user承認**: 2026-07-02「いいよ、進めて」（LIVE停止方向の推奨承認）+「進め方はまかせる」

## 判定サマリ（30d clean live 全戦略スキャン）

| strategy × pair | 30d N | WR | PnL | 判定 | 根拠 |
|---|---|---|---|---|---|
| wick_imbalance_reversion × GBP_USD (E10経由) | 9 | 22.2% | **-52.5p** | **E10 code-level DISABLE** | E10 force-live が主経路 (9/12件)。pre-reg forensic 2026-06-22 が独立に同セルを dominant loser 特定 (9/9負けが d1∈{0,-1} knife-catch)。watchdog生存なら auto-demote 済みの水準 |
| dt_sr_channel_reversal × EUR_JPY | 10 | 40.0% | **-30.9p** | **PAIR_PROMOTED除去** | 昇格根拠 (shadow N=12 EV+14.28 small-N / BT EV+0.178 marginal) を live が反証。Wlo=16.8 BFlo=9.5 |
| zz_pivot_v60_sr(+_lo) × EUR_USD | 11 | 54.5% | **-30.5p** | **PAIR_PROMOTED除去** | mean -2.77、損大利小 (-12.1/-10.5/-8.5 vs +1.8前後)。昇格は TV-only Path-B例外 (Wilson_lo 0.434 FAIL)。**05-28 pre-reg撤回条件 (N=30) を Rule 2 + user 07-02 指示で上書き**。_lo は同一戦略ユニットとして同時除去 (30d live 0件) |
| vix_carry_unwind × USD_JPY | 10 | 50.0% | -19.0p | **維持（誤殺回避）** | 個票検証: 10件全て UTC08-09 London = **06-18修正済みGRAILリーク由来**。Overlap pilot (12-16 UTC) の fill は 0件 → pre-reg demote gate (Cell-Live N≥10) 未充足。0-fire 自体は要診断 (T7類似) |
| trendline_sweep (ELITE) | 19 | 63.2% | -44.7p | **維持** | 唯一の12y BT正エッジ (EUR +0.927 / GBP +0.599)。live WR 63%はBT/Live乖離メモリ (BE/trail +20pp) と整合し方向edge自体は保持と判断。負けは損大利小サイズ非対称。教訓「唯一の正エッジ戦略への実験はリスク非対称」に従い demote せず、DD防御0.2x + FLAT units 継続 |
| bb_rsi_reversion (30d n=10 -9.8p) | 10 | 30.0% | -9.8p | **保留（経路未検証）** | trades API 直近3000件に該当行なし = live経路を特定できず。**未検証** — 日次ループで追跡 |
| sr_anti_hunt_bounce / sr_fib_confluence / ema200 / doji / orb_trap / xs_momentum_rsi | ≤3 | — | -7〜-26p | 維持 | N<10、R2証拠不足 |

## 実装

- `modules/edge_cell_promote.py`: `DISABLED_CELLS = {"E8", "E10"}`（E8前例 d00f441e と同機構、KVリセット耐性）
- `modules/demo_trader.py`: `_PAIR_PROMOTED` から dt_sr_channel_reversal×EUR_JPY / zz_pivot_v60_sr×EUR_USD / zz_pivot_v60_sr_lo×EUR_USD 除去 + zz lot boost整合性除去
- pin tests: `tests/test_edge_cell_promote.py` (E10) / `tests/test_volume_live_promote_routing.py`
- **再昇格は全て R1 のみ**（12y BT + Bonferroni + Pre-reg LOCK）

## 期待効果（M2）

閉鎖3経路の30d寄与 = **-113.9pip**（E10 -52.5 + dt_sr -30.9 + zz -30.5）。30d負けクラスタの主要部。session_time_bias（-58.6p、9e508ee2で閉鎖済み）と合わせ、直近30dの負け上位5経路のうち4経路が封鎖済みとなる。

## 未処理・関連

- vix_carry Overlap pilot 0-fire 診断（T7 carry dip 0-fire と同類の発火診断）
- bb_rsi_reversion の live 経路特定（未検証）
- 本決定は **main へのデプロイで初めて有効**（[[claude-codex-division-of-labor-2026-07-02]] セッションの hotfix 参照）
