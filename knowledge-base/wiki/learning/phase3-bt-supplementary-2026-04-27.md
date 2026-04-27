# Phase 3 BT Supplementary Considerations (LOCK 外、変更可能)

**Session**: curried-ritchie (Wave 2 Day 4 Quant Rigor R1 revision)
**Date**: 2026-04-27 14:30 JST (= 05:30 UTC)
**Status**: LOCK 外の補足記録、内容は変更可能 (HARKing 防止規律)
**位置付け**: `phase3-bt-pre-reg-lock.md` (commit `34c404c` で時刻署名済) は **LOCK terms 不変**。本文書は LOCK 後に発生した状況変化を追跡する **non-binding supplementary record**。

> **重要**: 本文書の内容を LOCK terms に組み込む場合は、新規 Pre-reg LOCK (別 commit) を発行する必要がある。本文書を LOCK 文書側に merge することは禁止 (HARKing pattern 該当)。

---

## 0. 背景

Pre-reg LOCK 文書 commit (`34c404c`, 2026-04-26 23:18 UTC) 後、以下 5 changes が短時間内 (~5h) に連続 deploy された:

1. **Wave 1 R2-A suppress** (commit `f1cc1aa`, 2026-04-26 14:18 UTC) — 4 cells confidence ×0.5
2. **U18 4-bin quartile fix** (commit `e362254`, 2026-04-27 23:27 UTC) — Phase 4d-II 互換 cuts
3. **Wave2 A2/A3/A4** (commit `4df389f`, rule:R1-bypass) — SL pip clamp + cost throttle + vol scale
4. **C2-SUPPRESS expansion** (commit `795d4af`) — `_R2A_SUPPRESS` に `(ema_trend_scalp, Overlap, q0)` 追加
5. **fib_reversal C1-PROMOTE** (commit `7437e19`) — Live 0.05 lot 昇格 (rule:R1)

これらは LOCK 後に observed されたため、**LOCK terms には含まれていない**。

---

## 1. Multi-Change Confounded Period 認識

5 changes 同時 deploy で個別 effect の clean attribution は困難。具体的影響:

- Phase 3 BT が baseline 比較する pre-deploy データは Wave 1 R2-A 直前 (04-19〜04-26) のみで「clean baseline」の確保が困難
- 各 change の effect を distinct に測定するには randomized A/B test が必要だが production deploy では実施不可
- post-hoc decomposition (logit 多変量回帰) は observational で causal claim 弱い

**詳細**: [`wave2-deconfounding-plan.md`](wave2-deconfounding-plan.md) §0-§3

---

## 2. Quant 観点の supplementary considerations (LOCK 不変、参考事項)

LOCK terms (§6 採用基準等) は変更しない前提で、Phase 3 BT 実行時に **追加で考慮すべき事項**:

### 2.1 Measurement period quality awareness

- Phase 3 BT 着手の "go" 判断は LOCK §6.1 (Live N≥30 + Wilson lower > BEV + Bonferroni p<0.00714) のみで決定する
- ただし結果解釈時に "multi-change confounded measurement period" を文脈として明記
- BT 結果 documentation で当該 period の trades にフラグ付け

### 2.2 Hold-out validation の重要性増大

- LOCK §7.3 の hold-out validation set (2026-05-01 以降) は当初 "additional gate" として位置付けられたが、confounded period の影響を考えると **primary validation gate** に格上げするのが望ましい
- 本変更は LOCK §6/§7 の改訂を要するため、Phase 3 BT 完了後の new Pre-reg LOCK で正式化

### 2.3 4-arm BT design の検討余地 (LOCK 外提案)

LOCK §4 は Mode A vs Mode B の 2-arm 設計だが、Wave 2 confounding を考慮すると以下の 4-arm が情報量上は理想的:

- Arm 1: Mode A 単独 (Wave 2 changes off)
- Arm 2: Mode B 単独 (Wave 2 changes off)
- Arm 3: Mode A + Wave 2 (current production)
- Arm 4: Mode B + Wave 2

ただし:
- K=7 strategies × 4 arms × 2 WFA = 56 BT runs (現 28 の 2 倍)
- Bonferroni 補正下の detection power 低下
- production rollback ("Wave 2 changes off") は practical に困難

**提案 (LOCK 不変、参考)**: Phase 3 BT 当初 LOCK 通り 2-arm で実行、結果が ambiguous な場合に Wave 3 の new Pre-reg LOCK で 4-arm 検討。

### 2.4 Phase γ-η 計測 schedule (任意 reference)

LOCK 文書に schedule は含まれていない (Phase 3 BT 着手 timing は "Wave 1 monitor δ +72h で initial 評価" のみ §9.2 に記載)。本 supplementary では Wave 1+2 効果計測の reference schedule として:

| Phase | timing (JST) | reference action |
|-------|--------------|-------------------|
| α (済) | +6h 04-27 06:00 | qualitative gate-fire check |
| β | +12h 04-27 12:00 | London 開始、R2-A target cells 初発火 reference |
| γ | +24h 04-27 24:00 | initial logit fit (de-confounding plan §4.3) |
| δ | +72h 04-30 02:00 | Bonferroni K=5 で initial β |
| ε | +7d 05-04 | Phase 3 BT 着手 reference timing (LOCK §6.1 達成評価) |
| ζ | +14d 05-11 | full effect map、ε で N 不足ならば継続 |
| η | +30d 05-27 | long-term equilibrium reference |

これらは LOCK 上の binding deadline ではない。Phase 3 BT GO/NO-GO は LOCK §6 採用基準のみで判定。

---

## 3. 本 supplementary の運用規律

### 3.1 LOCK との分離

- 本文書の内容は **LOCK 文書 (phase3-bt-pre-reg-lock.md) に merge してはいけない**
- LOCK terms (K, α, WFA, G1-G5, 採用基準) を変更する場合は new Pre-reg LOCK を発行
- 本 supplementary は "context" として参照、判定基準には使わない

### 3.2 修正可能性

- 本文書は **measurement period 中も修正可能** (LOCK と異なり)
- 修正履歴を git で追跡、後の transparency 確保
- ただし重要な context 変更は Phase 3 BT 結果文書に再録

### 3.3 Phase 3 BT 完了後の扱い

- Phase 3 BT 完了後に本文書の content を:
  - (a) `phase3-bt-result-2026-XX.md` の context section に取り込む
  - (b) または new Pre-reg LOCK の background section に格上げ
- 本 supplementary を deprecate (新文書に内容移管後、archive)

---

## 4. 関連文書 (cross-reference)

| 文書 | 関係 |
|------|------|
| `phase3-bt-pre-reg-lock.md` (LOCK, commit `34c404c`) | binding terms |
| `wave2-deconfounding-plan.md` | de-confounding 統計設計 (本 supplementary が参照) |
| `wave1-r2a-power-analysis.md` | Wave 1 単独 effect 計測の事前 power calc |
| `u3-vol-momentum-scalp-deepdive.md` | G1-G5 hypothesis source |
| `u11-mechanism-audit-aggregate.md` | K=7 universe selection 根拠 |
| `phase3-bt-skeleton-design.md` | tools/phase3_bt.py の interface 設計 |

---

## 5. R1 Revision 経緯

**事象**: 2026-04-27 13:40 JST に当初 phase3-bt-pre-reg-lock.md §9.1.bis として multi-change confounded considerations を追記。

**問題**: LOCK 文書を BT data 観測前に修正する行為自体が HARKing pattern。LOCK §10 で明記された "本 LOCK の K, α, WFA, G1-G5, 採用基準は BT 完了まで不変" 規律違反。

**修正 (R1, 2026-04-27 14:30 JST)**:
1. LOCK 文書 §9.1.bis を revert (LOCK terms 不変回復)
2. 本 supplementary 文書を LOCK 外に作成、同内容を移管
3. LOCK §9.1 末尾に "本 supplementary 文書への reference" を追加 (LOCK 内容変更ではなく link 追加のみ)
4. Quant rigor 規律の実効化を確認
