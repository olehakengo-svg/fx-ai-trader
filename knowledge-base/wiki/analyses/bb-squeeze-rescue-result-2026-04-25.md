---
pre_reg: bb-squeeze-rescue-2026-04-25
status: ALL_REJECT (per §6, _FORCE_DEMOTED 推奨)
verdict: 0 SURVIVOR / 0 CANDIDATE / 6 REJECT (N=2,704)
generated: 2026-04-25T~10:00 UTC
---

# bb_squeeze_breakout Rescue — BT Result (2026-04-25)

**Pre-registration**: [[bb-squeeze-rescue-2026-04-25]] (LOCKED 2026-04-25)
**BT window**: 2025-04-26 → 2026-04-25 (365 days)
**Pairs**: USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY (XAU除外)
**Target**: `bb_squeeze_breakout` (Shadow, Live N=113 EV=-0.26)
**N (baseline)**: 2,704 trades
**α_cell (Bonferroni, M=4 main)**: 0.0125
**Execution**: Render Shell (PID 875, 73分)

## 0. TL;DR — ALL_REJECT

> **SURVIVOR=0 / CANDIDATE=0 / REJECT=6** (4 main + 2 secondary)
>
> A1 (Cell only) で EV +2.93p 改善 (-4.39 → -1.46) が観測されたが、
> N=54 で Bonferroni α=0.0125 を満たさず (p_welch=0.096).
> A2 (Time only) は EV を逆悪化 (-4.39 → -4.99). MAE_BREAKER 9.9% で
> 「20分待つ間に -15pip 級の逆行」が 270件発生 = 生存者バイアスが現実.
>
> **Pre-reg §6 REJECT パス自動発動**:
> bb_squeeze_breakout を `_FORCE_DEMOTED` 追加候補として記録.
> ただし time_floor_meta BT 完了 (estimated 2026-04-25 18:00 UTC) まで待って
> 一括判断 (時間軸救済可能性は time_floor 結果次第).

## 1. Verdict matrix (4 main + 2 secondary)

| Cell | Filter | Time Floor | N | WR% | EV | PF | Wlo% | BE_req% | p_welch | WF | MAE!% | Verdict |
|------|--------|-----------|---|-----|-----|-----|------|---------|---------|-----|-------|---------|
| A0   | none | none | 2704 | 23.6 | **-4.39** | 0.46 | 22.1 | 323 | -        | 4/4 | 0.0% | REJECT |
| A1   | USDJPY×Lond×TBEAR | none | 54 | 29.6 | -1.46 | 0.77 | 19.1 | 237 | 0.096 | 3/4 | 0.0% | REJECT |
| A2   | none | ≥20min | 2704 | 24.6 | **-4.99** | 0.44 | 23.0 | 307 | 0.099 | 4/4 | **9.9%** | REJECT |
| A3   | USDJPY×Lond×TBEAR | ≥20min | 54 | 31.5 | -1.45 | 0.78 | 20.7 | 218 | 0.113 | 3/4 | 7.4% | REJECT |
| A4 (sec) | USDJPY×Lond×any | ≥20min | 172 | 30.8 | -2.37 | 0.68 | 24.4 | 224 | 0.050 | 4/4 | 7.6% | REJECT |
| A5 (sec) | USDJPY×any×TBEAR | ≥20min | 178 | 31.5 | -2.03 | 0.71 | 25.1 | 218 | 0.021 | 3/4 | 7.9% | REJECT |

### 1.1 Cell-by-cell 解釈

**A0 baseline (REJECT)**:
- Live 観測 EV=-0.26 → BT 365日 EV=-4.39 で 17倍悪化
- 摩擦 v2 + slippage が Live の集計より厳しく BT に反映 (Live は demo 計上で
  slippage 集計が緩い)
- WR 23.6% << BE required 323% (= RR 0.31, 既存設定では数学的に不可能)

**A1 cell only (REJECT, 改善観測)**:
- Filter (USDJPY × London UTC 6-13 × TREND_BEAR) で EV -4.39→-1.46 に **+2.93p 改善**
- WR 29.6% (Live 観測 9件 44.4% から大幅後退、Live 集計バイアスを示唆)
- N=54 で Bonferroni α=0.0125 を満たさない (p_welch=0.096)
- Cell 仮説自体は否定されないが、**運用に必要な統計力に達していない**

**A2 time only (REJECT, 悪化)**:
- EV を -4.39 → -4.99 に悪化
- **MAE_BREAKER 9.9%** = 365日中 ~270件で「20分待つ間に -15pip 級の逆行で
  口座吹き飛ばし」発生
- 「20分待てば EV+ になる」仮説は **時間軸全体での生存者バイアス** に依存する幻想だった
- pre-reg リスク §11.1 (生存者バイアス) が定量実証

**A3 cell+time (REJECT)**:
- A1 と同等 (N=54)、Time Floor 上乗せ効果なし
- MAE_BREAKER 7.4% = Cell filter でも生存者バイアス完全には消えない

**A4/A5 secondary (REJECT, p<0.05 だが Bonferroni 対象外)**:
- N が大きい (172/178) と p_welch < 0.05 達成、しかし EV 依然負 (-2 〜 -2.4)
- MAE_BREAKER 7-8% で生存者バイアス継続
- secondary なので採択不可

## 2. 重要発見 — MAE_BREAKER 生存者バイアス防衛が機能

[time-floor-meta-rescue-2026-04-25 §11.1](time-floor-meta-rescue-2026-04-25.md) で
事前宣言した生存者バイアスリスクが、**bb_squeeze 365日 BT で定量実証された**:

| Cell | MAE_BREAKER 件数 | 全 trade に占める比率 |
|------|------------------|---------------------|
| A0 | 0 | 0.0% |
| A1 | 0 | 0.0% |
| **A2** | **~268 / 2704** | **9.9%** |
| A3 | ~4 / 54 | 7.4% |
| A4 | ~13 / 172 | 7.6% |
| A5 | ~14 / 178 | 7.9% |

### 解釈

Live 観測の **「hold≥20m で EV+5 〜 +11p」** は **20分耐えた trade のみ**を集計
していた = **耐えきれず途中で口座吹き飛ばすケース 8-10% が除外されていた**.

365日 BT で強制保持シミュレーションすると、これら "脱落者" の損失 (-15p 以上)
が EV を引き下げ、**+ になるどころか time-floor は EV を悪化させる**.

[lesson-survivor-bias-mae-breaker-2026-04-25.md](lesson-survivor-bias-mae-breaker-2026-04-25.md)
として独立 lesson 起案.

## 3. 派生決定 (pre-reg §6 自動発動)

### 3.1 即時 (待機中)

- **bb_squeeze_breakout の deploy 状態維持** (Shadow): time_floor BT 完了まで暫定
- **`BB_SQUEEZE_OANDA_TRIP` 緊急トリップは追加しない**: Live N=113 で EV-0.26 と
  bb_rsi (EV-0.58) ほど深刻ではなく、Live は既に Shadow で OANDA未送信

### 3.2 time_floor 完了後 (Estimated 2026-04-25 18:00 UTC)

- time_floor で `bb_squeeze_breakout × hold≥X` cell が SURVIVOR なら時間軸救済を再評価
- time_floor でも REJECT なら `_FORCE_DEMOTED` 正式追加 (deploy pre-reg 別途)

### 3.3 拒否 (HARKing 回避)

- A1/A4/A5 で観測された EV 改善 (+2 〜 +3p) を理由に、Bonferroni を緩めた再解析を
  起こさない
- N が増えるまで pre-reg lock 維持 → Phase 1 holdout (5/7) 後に再検定検討

## 4. メモリ整合性

- [部分的クオンツの罠]: PF/Wilson_lo/p_welch/WF/MAE_BREAKER 全て表で出力 ✅
- [ラベル実測主義]: BT 365日実測のみで判定、コード演繹なし ✅
- [成功するまでやる]: REJECT で短絡 closure せず、time_floor 結果統合判断へ繰越 ✅
- [XAU除外]: PAIRS 5本のみ (XAU除外) ✅

## 5. 参照

- [[bb-squeeze-rescue-2026-04-25]] (本 BT の pre-reg)
- [[rd-target-rescue-anatomy-2026-04-25]] (本 BT の根拠データ)
- [[time-floor-meta-rescue-2026-04-25]] (並走 BT, 結果待ち)
- [[lesson-survivor-bias-mae-breaker-2026-04-25]] (本 BT で得た知見)
- [[mafe-dynamic-exit-result-2026-04-24]] (前 BT, MAFE 系統と整合)
