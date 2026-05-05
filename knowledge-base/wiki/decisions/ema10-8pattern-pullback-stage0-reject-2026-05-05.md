# EMA10 × M15 × 4-Pattern Pullback Stage 0 REJECT (2026-05-05)

## Status
**rule:R1** — Stage 0 sanity BT (USD_JPY 12.3y, primary cell pre-registered) で **5/5 Gate 全 FAIL**。Wave 1 / Stage 1 / Shadow 投入なし。完全棄却。

## Verdict: REJECT

| Gate | 閾値 | 観測値 | 判定 |
|---|---:|---:|:---:|
| PF | ≥ 1.10 | **0.2835** | 🔴 FAIL (-74.2%) |
| Wilson_lo (95%) | ≥ 0.50 | **0.2593** | 🔴 FAIL (-48.1%) |
| N | ≥ 150 | 45,080 | ✅ PASS (300×) |
| profit_year_concentration | < 0.55 | **1.0000** | 🔴 FAIL |
| EV_pip / trade | > 0 | **-4.4038** | 🔴 FAIL |

**統計的不確実性ゼロ**: N=45,080 で 12.3 年フルカバー、Wilson 95% CI 上限 ≈ 0.27 → BEV 想定 0.50 を 23 ポイント下回る。

## Yearly stability (13 年連続損失)

```
Year   N      PF     EV_pip
2014   3541   0.21   -4.26
2015   3667   0.25   -4.52
2016   3709   0.32   -4.63
2017   3639   0.24   -4.67
2018   3762   0.18   -4.46
2019   3462   0.14   -4.41
2020   3336   0.22   -4.08
2021   4022   0.16   -4.13
2022   3791   0.37   -4.50
2023   3604   0.38   -4.15
2024   3603   0.39   -4.36
2025   3670   0.38   -4.56
2026   1274   0.31   -4.65
```

**全 13 年で PF < 0.40, EV_pip < -4.0**。年次レジーム変動・通貨取引コスト変化を貫通する**構造的負け戦略**。

Equity curve は単調 drawdown（2014→2026 で max_dd_pip = 198,545 ≈ -19.85% / 単利 100k unit）、Sharpe = -6.95。

## Why 完全 NO EDGE か

事前見立て（[`pre-reg`](./ema10-8pattern-pullback-pre-reg-2026-05-05.md) §構造的弱点 4 件、計画書 [zany-soaring-dolphin.md](../../../../.claude/plans/zany-soaring-dolphin.md)）と完全に一致した結果。最も強く効いた要因:

1. **4-pattern union による無差別シグナル化**: pinbar / hammer-bear / engulfing / harami breakout の OR 結合で 12.3y 45,080 件にまでシグナル数が膨張。trend pullback 機会のうち pattern filter による noise 除去率がほぼゼロに近づき、edge が希釈された。
2. **avg_rr = 0.79**: 直近 swing high/low ベースの SL/TP 設定で R/R が 1 を割る。WR が 50%+ でも EV+ 達成困難なのに、観測 WR は 26% → 構造的負け。
3. **Spread/slippage 2.0 pip 往復**: 観測 ev_pip=-4.4 のうち約半分は cost。仮に cost 0 でも ev_pip ≈ -2.4 で **edge は cost 不在でも存在しない**。これは「spread を絞れば勝てる」では救えない設計。
4. **Trend cross 強制 close の偏り**: 強制 close 比率が高い（`tools/bt/ema10_8pattern_pullback.py` レポート §Sanity checks 参照）→ 早期 cut で R/R が抑制。

memory `feedback_partial_quant_trap.md` の罠は今回回避: PF 単独ではなく Wilson_lo + N + profit_year_concentration + EV まで揃えた上での REJECT。

## Codex 実装の評価

戦略は REJECT だが **Codex の実装と pre-reg LOCK 遵守は ACCEPT**:

| 評価項目 | 結果 |
|---|---|
| Primary cell exact match | ✅ pair=USD_JPY, all_four, sl=1.0, tp_lookback=20, spread=1.5, slip=0.5 |
| Forbidden files unchanged | ✅ strategies/, demo_trader.py, app.py, render.yaml, .env all unchanged |
| pre-reg LOCK 遵守 | ✅ §Stage 0 結果のみ末尾追記、本文改竄なし |
| CLI exit code | ✅ 0 |
| pytest with real fixture | ✅ 4 passed (USD_JPY M15 2024Q1 real OHLC) |
| JSON schema exact match | ✅ |
| gate_decision 明示 | ✅ "FAIL" (not INCONCLUSIVE) |
| fail_reasons enumeration | ✅ 5 件全列挙 |
| 完了所要時間 | 697 秒 (~11.6 分) |
| Commit | [`5bb5fa9`](https://github.com/olehakengo-svg/fx-ai-trader/commit/5bb5fa9) |

**Notable note from Codex**: 「pre-reg 指定の cache `data/cache/massive/USD_JPY_5m_2014_2026.parquet` が absent、代わりに `data/cache/massive/USD_JPY_5m.parquet` を使用 (row count + date coverage 一致)」 → 自己検証の上で同等性を確認しているため問題なし。

唯一の data quality 注意点 missing_pct=2.946% (Gate 2% 超過) は:
- 他 4 Gate が圧倒的 FAIL のため data 完全化で結果反転の余地ゼロ
- 仮に 0% にしても ev_pip = -4.4 → ほぼ -4.4 のまま (欠損 bar の偏り影響は noise レベル)
- 実装上の限界ではなく現実のソース data の欠損

## Implications

### 1. 既存戦略との比較示唆

ユーザー手法は memory `feedback_ma_filter_breaks_mr.md` の **逆** を示した:
- MR (e.g. bb_rsi_reversion) では H1 EMA200 整合 filter が edge を破壊
- TF pullback では 4-pattern union のみで filter なし → edge そのものが存在しない

**示唆**: 既存 [`ema_pullback`](../../../strategies/scalp/ema_pullback.py) の ADX/RSI/BB/MACD/Stoch filter 群は noise 除去で edge を **作り出している**可能性が高い。今回 ablation を行わなかったが、今回の baseline (PF=0.28) と既存 ema_pullback の Live PF を比較すれば filter の貢献度を間接測定できる。

### 2. CLAUDE.md 「思想は正、設計が誤」フレーム

- **思想**: trend pullback + bar confirmation → 部分的に妥当（既存 ema_pullback と同じ基盤思想）
- **設計**: 4-pattern union + filter なし + R/R<1 → **DESIGN_BROKEN** (memory `project_w4_eda_complete_2026_05_05.md` の 91% パターンに該当)

W4-EDA フレームワークで言えば「設計が誤」だが、ユーザー指示で再設計はスコープ外。

### 3. Roadmap への寄与

- Stage 1 / Stage 2 / Shadow 投入なし
- tier-master.md 登録なし（ユーザー指示通り、永続的に未登録）
- Wave 4 進行中タスク (NSG-1 / HIP-1 / VFO-1 / SFT-1 / W4P1) には影響なし

## Action items

- [x] 棄却 decision doc 作成（本ファイル）
- [ ] memory `project_ema10_8pattern_2026_05_05.md` に Stage 0 REJECT 結果を追記
- [ ] MEMORY.md 索引の short description を更新（"pre-reg" → "REJECT (PF=0.28, 13y losing)"）
- [ ] task `20260505-0930-ema10-8pattern-stage0.md` は既に done/ 配下、追加 housekeeping 不要

## What did we learn

- 公開 SNS で流通する手法を **pre-reg + 12.3y BT で literally 検証する** プロトコルが機能した。司令塔の事前見立て (構造的弱点 4 件) と実測結果が完全一致。
- 機械化の DoF を LOCK して post-hoc selection 罠 (W3-3 S4 型) を回避できた。
- Codex の pre-reg 遵守規律は高水準。今回のような literal BT で 700 秒以内に完走する作業は今後も委任して問題ない。

## References

- Pre-reg LOCK: [`ema10-8pattern-pullback-pre-reg-2026-05-05.md`](./ema10-8pattern-pullback-pre-reg-2026-05-05.md)
- Stage 0 result md: [`ema10-8pattern-stage0-2026-05-05.md`](../../raw/audits/ema10-8pattern-stage0-2026-05-05.md)
- Stage 0 result json: [`ema10-8pattern-stage0-2026-05-05.json`](../../raw/audits/ema10-8pattern-stage0-2026-05-05.json)
- Task spec (done): [`20260505-0930-ema10-8pattern-stage0.md`](../../../.ai/tasks/done/20260505-0930-ema10-8pattern-stage0.md)
- Plan: [zany-soaring-dolphin.md](../../../../.claude/plans/zany-soaring-dolphin.md)
- Implementation: [`tools/bt/ema10_8pattern_pullback.py`](../../../tools/bt/ema10_8pattern_pullback.py) (797 行), [`tests/test_ema10_8pattern_pullback.py`](../../../tests/test_ema10_8pattern_pullback.py) (124 行)
- Commit: [`5bb5fa9`](https://github.com/olehakengo-svg/fx-ai-trader/commit/5bb5fa9)
