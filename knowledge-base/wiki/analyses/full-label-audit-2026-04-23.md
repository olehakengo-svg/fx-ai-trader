# Full Label Audit (2026-04-23)

**Scope**: shadow post-cutoff 2026-04-08 / XAU除外 / N=2057
**Script**: `/tmp/full_label_audit.py`
**Trigger**: [feedback_label_empirical_audit](/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/feedback_label_empirical_audit.md)

## Executive Summary

全 reasons ラベルを `has/no` で WR/EV 分解した結果、以下のラベルが逆校正 (Delta WR ≤ −5pp) と判明:

| Rank | Label | Delta WR | N_has | TF Delta | MR Delta | Status |
|------|-------|----------|-------|----------|----------|--------|
| 1 | **方向一致** | **-8.8pp** | 1086 | **-16.7** | -6.7 | 🚨 INV (meta-level) |
| 2 | **VWAPスロープ** | **-7.0pp** | 1647 | -13.3 | -4.1 | 🚨 INV (conf_adj 既中立化) |
| 3 | **売り優勢** | **-6.4pp** | 370 | -10.7 | -5.8 | 🚨 INV (conf_adj 既中立化) |
| 4 | **機関フロー** | **-6.3pp** | 700 | -9.5 | -5.5 | 🚨 INV (既対策済) |
| 5 | **HVN** | **-6.1pp** | 686 | -6.4 | -5.9 | 🚨 INV (既対策済) |
| 6 | **S/R確度UP** | **-6.0pp** | 681 | -6.8 | -5.6 | 🚨 INV (既対策済) |
| 7 | **ブレイク** | **-5.8pp** | 157 | n/a | n/a | 🚨 INV (新規発見) |

**正の効果 (+3pp 以上)**:
| Label | Delta WR | N_has |
|-------|----------|-------|
| ADX弱 | +7.2pp | 42 |
| レンジ | +4.9pp | 355 |
| Stoch | +4.1pp | 780 |
| LVN | +3.6pp | 642 |

**中立 (−3 〜 +3)**: VWAP上位, 確度UP, 買い優勢, トレンド, BB, 過伸長, VWAP下位, HTF逆行,
EMA200, 反発, RR不足, 方向不一致

## Data caveat

**cutoff 2026-04-08 〜 2026-04-23 の 15日間、うち前セッション (2026-04-23) で**:
- HVN/LVN conf_adj 中立化 (`2a6d1da`)
- 機関フロー / 方向一致 conf_adj 中立化 (`2a6d1da`)
- VWAP deviation conf bonus 中立化 (`91f34ac`)
- VWAP conf_adj 中立化 (`b37ee8b`)
- VWAPスロープ conf_adj 中立化 (`b37ee8b` 同系)

従って **本監査の N=2057 のほぼ全て pre-neutralization データ**。
次回 (14日後) に再実施し、中立化が効果を示しているか verify する必要がある。

## Per-label deep dive

### 1. 方向一致 (Delta -8.8pp, N=1086)

- TF: -16.7pp (最強逆校正)
- MR: -6.7pp
- **根拠コード**:
  - 多数の strategy file に `reasons.append("✅ EMA短期方向一致")` 等 (label-only, conf_adj なし)
  - ~~`app.py:8869-8878` Layer 1 `大口方向一致` → `score *= 1.15`~~ → [[layer1-bias-direct-audit-2026-04-23]]
    で実測: 99% が neutral で未適用、適用時は +18.3pp 正校正。**Layer 1 は主因ではない**
  - `modules/massive_signals.py` 機関フロー は前セッションで既中立化 (conf_adj=0)
- **真の原因**: TF 戦略そのものの regime mismatch — EMA alignment 検出 = trend 終盤で
  fade される selection bias。戦略レベルの Tier 降格 / Sentinel で対処すべき。
- **推奨**: 個別 app.py Layer 1 修正は不要。TF 戦略群の Tier 再評価を優先。

### 2. VWAPスロープ (Delta -7.0pp, N=1647)

- TF: -13.3pp
- MR: -4.1pp
- 根拠コード: `modules/massive_signals.py:176-195`
- **対策状況**: 既に conf_adj 中立化済 (`b37ee8b` 系)、label のみ残存
- **次アクション**: label 文言を断定的→観察に変更 (`"VWAPスロープ rising"` → 削除 or
  `"[observed] vwap_slope=rising"`)

### 3. 売り優勢 (Delta -6.4pp, N=370)

- TF: -10.7pp
- MR: -5.8pp
- 根拠コード: `modules/massive_signals.py:354` `機関フロー: 売り優勢 (n/m本)`
- **対策状況**: conf_adj 既中立化 (`2a6d1da`)、label のみ残存

### 4-6. 機関フロー / HVN / S/R確度UP

すべて前セッションで conf_adj 中立化済。label 削除/観察化は次アクション候補。

### 7. ブレイク (Delta -5.8pp, N=157)

- カテゴリ細分化不足 (TF/MR 15サンプル以下)
- 根拠コード: 複数の strategy file (doji_breakout, london_breakout, tokyo_range_breakout, 等)
- **新規発見**: 過去の監査で未検出
- ブレイク戦略群のサンプル不足で category-level Wilson CI 算出不可。
- **推奨**: breakout カテゴリ (BR) 再定義 + N 蓄積待ち

## Labels with positive calibration (保持推奨)

| Label | Delta WR | 推奨 |
|-------|----------|------|
| ADX弱 | +7.2pp | 逆張り向き → MR の品質 filter として活用 |
| レンジ | +4.9pp | MR の gate として正 calibration |
| Stoch | +4.1pp | oscillator signal として有効 |
| LVN | +3.6pp | MR の pullback zone として正 calibration |

## Actionable items

### Immediate (label-only, 低リスク)

- [ ] `modules/massive_signals.py` の "売り優勢" / "買い優勢" / "VWAPスロープ rising" の
      断定口調を観察表記に変更
- [ ] `modules/massive_signals.py` の "機関フロー" ラベル削除 → 数値のみ残す (既済の場合 skip)

### User review required

- [ ] ~~`app.py:8869-8878` Layer 1 大口方向一致 `score *= 1.15` の中立化~~ → [[layer1-bias-direct-audit-2026-04-23]]
      で実測棄却。Layer 1 は正校正かつ dormant、修正不要。
- [ ] 多数 strategy files の "EMA方向一致" 等の label を "[observed] EMA alignment" に変更
      (低リスクだが範囲広、user 承認後に一括 edit)
- [ ] TF 戦略群の Tier 再評価 — regime mismatch は strategy gating で対処すべき (別タスク)

### Re-audit schedule

- 2026-05-07 (14 days) — 中立化後のデータで再監査、中立化が WR 収束を引き起こしたか verify

## References

- [feedback_label_empirical_audit](/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/feedback_label_empirical_audit.md)
- [[tf-inverse-rootcause-2026-04-23]]
- [[lesson-why-missed-inversion-meta-2026-04-23]]
- [[mtf-gate-category-audit-2026-04-23]]
- Raw output: `/tmp/full_label_audit_output.txt`
