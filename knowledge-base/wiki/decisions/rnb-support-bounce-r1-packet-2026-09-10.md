# rnb_support_bounce 登録 R1 パケット (2026-09-10 起案 — user 決裁待ち)

**rule**: R3 (起案・分析) / 執行は R1 (user 最終承認必須)
**背景**: [[process-meta-audit-2026-09-07]] §4.2 R1(a) — 「live 層の無料 N 源回収」の前倒し起案 (user 2026-09-10「全て進めて」承認は*起案*に対するもの。登録の執行承認は本パケット §7)。
**一次資料**: [[../analyses/rnb-dead-mode-and-block-estimand-2026-09-05]] (153 日登録漏れ) / registry `rnb-support-bounce-registration-decision` (期日 2026-10-06) / BT evidence: `raw/bt-results/rnb-support-bounce-ablated-bt-2026-09-10.md`
**本パケットは文書のみ。live コード変更なし。**

---

## 0. 要約 (決裁者向け 5 行)

1. `rnb_support_bounce` は 2026-04-05 から QUALIFIED_TYPES 未登録 = shadow 1 行も出せない dead mode (158 日目)。エンジンは 30s tick 継続中で、登録すれば **~3.0 setups/週の無料 shadow N 源** (現行最速 live セル usdjpy_carry_dip 2.10/週 超)。
2. **365d BE/Trail-ablated BT (本日実施): net EV +0.04p ≈ ゼロ、NS (p=0.082)、2026-03 単月依存、730d は −2.20p** — **live 昇格根拠はない**。config コメントの「BUY EV=+7.7」は ablation 前の数字で引用不可 (確認済み)。
3. よって提案は **stage-1: 構造的 shadow-only 登録** (`shadow_only: True`、OANDA 送信全経路 block、daytrade_audjpy 前例) に限定。live minlot はこの packet では開けない。
4. live 実測頻度の中間読みは**現時点で無情報** (block counter は再起動リセット、active hours を含む窓が snapshot されずに 2 回消滅 — §2)。期日 10-06 の判定には §2.3 の読み手手順が必要。
5. 採用境界・棄却境界・pre-reg LOCK 草案は §5-6。**user 決裁欄 §7**。

---

## 1. 現状 (事実)

| 項目 | 値 |
|---|---|
| 登録状態 | `rnb_support_bounce` ∉ QUALIFIED ∪ CONDITIONAL (2026-04-05 db5e3e4c 以来) |
| gate | `_tick_entry` の `unknown_type:` block は shadow bypass なし → **行ゼロ保証** |
| エンジン | `rnb_usdjpy` auto_start=True、30s tick 継続 (本日 tick 736、engine ok) |
| ドリフト pin | `tests/test_rnb_block_reason_estimand.py::test_auto_start_modes_have_no_unknown_registration_drift` が既知集合と**完全一致**で pin — 登録解消時も落ちる = 同コミット更新必須 |
| 確定足頻度 | 365d 156 setups = **2.99/週** (12.8y 平均 3.3/週) — 本日再現確認 |
| 09-05 estimand 分離の検証 | 予測 1 (`direction_filter`→恒久 0) ✓、予測 2 (`no_signal`≈tick 数: 732/736) ✓ — 本番実測で確認済み。予測 3 (unknown_type 可視化) は §2 |

## 2. live 実測頻度の中間読み (2026-09-10 06:33 UTC)

### 2.1 実測

- 現在 counter 窓: 最終デプロイ `dep-dagum8h5efls7399otbg` (2026-09-09 23:28 UTC) 以降。`rnb_usdjpy` tick=736 (≈6.1h 市場オープン時間)
- `rnb_usdjpy:unknown_type:rnb_support_bounce` = **0 件** / `no_signal` = 732 / `direction_filter` = 0

### 2.2 制約 — この 0 件は無情報

- 現在窓 (23:28→06:33 UTC) は **active hours (UTC 7-20) を 1 分も含まない**。`compute_rnb_signal` は UTC 7-20 外で全 WAIT → セットアップ期待値 0。0 件は設計整合であって頻度の証拠ではない。
- 09-05 デプロイ以降の counter 窓 5 本のうち、active hours を含んだのは W2 (09-06 12:20→09-08 23:31、~26 active h) と W4 (09-09 04:03→23:28、~13 active h) の 2 本。**どちらも snapshot されずに次デプロイの再起動で消滅** — block_counts は揮発 (再起動リセット) で、日次 monitor は block family を KB に永続化していない。
- ⚠️ さらに estimand 注意: block counter は **forming-bar 30s tick** の観測。確定足推定 2.99/週 とは母集団が異なる (MEMORY `project_ps_capture_estimand_disjoint_2026_09_09` と同型)。tick share 予測 ~0.5-0.7% は forming-bar 側では上下どちらにもズレうる。

### 2.3 期日 10-06 判定を成立させる読み手 (コード変更なしの手順提案)

- 営業日 5 日、**UTC 19:50-19:59 (active window 終端直前)** に `GET /api/demo/block-counts?strategy=rnb_usdjpy` を pull し、`raw/trade-logs/YYYY-MM-DD-rnb-freq.md` に counter 値 + tick 数 + 直前デプロイ ID を記録する (窓の分母を明示)。
- 5 営業日 × 13h の実測から setups/週 に換算。デプロイで窓が切れた日は分母から除外。
- (別 task 提案、R3) `/api/demo/status` の日次 monitor が block family を KB へ永続化する経路の新設 — 今回の「取れたはずの 39 active 時間が消えた」の再発防止。

## 3. BT evidence (365d、Rule 1 要件)

詳細: `raw/bt-results/rnb-support-bounce-ablated-bt-2026-09-10.md` (ハーネス: `raw/session-scripts/rnb-support-bounce-ablated-bt-2026-09-10.py`、本番 signal 関数 backtest_mode=True、ペア×期間パラメータ化済み)

| 窓 | N | WR | Wilson_lo | net EV (f2.14) | 備考 |
|---|---:|---:|---:|---:|---|
| **365d** | 126 | 55.6% | 46.8% | **+0.04p** | p=0.082 NS。2026-03 単月 +160.9p が全て (他 12 ヶ月計 −155.4p) |
| 730d | 295 | 44.8% | 39.2% | **−2.20p** | 前年は明確に負け |
| 90d | 23 | 52.2% | 33.0% | **−3.95p** | 直近も負け |

- friction 込み BEV_WR = 49.0%。**Wilson_lo 46.8% < 49.0% = 昇格 gate 不成立** (lot ladder テンプレの N_required=41・Wilson gate 準拠の判定)
- BE/Trail ablated・悲観側 tie-break・単一ポジション — 水増し要因は排除済み
- **結論: 「勝てる戦略の登録」ではなく「観測レーンの開通」としてのみ正当化可能**

## 4. 登録変更の仕様 (stage-1: 構造的 shadow-only)

執行は deploy エージェント規約 (4 箇所同期チェックリスト) に従うが、rnb は DaytradeEngine 戦略ではなく mode 直結 signal_fn のため、実際の同期点は以下:

| # | ファイル | 変更 |
|---|---|---|
| 1 | `modules/demo_trader.py` QUALIFIED_TYPES | `"rnb_support_bounce"` 追加 (コメントに本パケット ID) |
| 2 | `modules/demo_trader.py` MODE_CONFIG["rnb_usdjpy"] | `"shadow_only": True` 追加 — **構造的 shadow-only 保証** (`_mode_is_shadow_only`、送信ガード最終段/再送 gate/write-path の 3 点 block。前例 daytrade_audjpy、user 承認 D2 2026-07-10) |
| 3 | `tests/test_rnb_block_reason_estimand.py` | known-drift 集合を空に更新 (完全一致 pin のため**同コミット必須**) + `shadow_only` の存在を新規 pin |
| 4 | KB 同期 | `tools/sync_kb_index.py --write` && `tools/tier_integrity_check.py --write` + strategy card `wiki/strategies/rnb-usdjpy.md` 更新 |

**意図的にやらないこと**:
- `_UNIVERSAL_SENTINEL` への追加 (sentinel = minlot **live** 経路。stage-1 では開けない)
- `direction_filter`/パラメータの変更 (BUY-only のまま)
- app.py `DT_QUALIFIED` / DaytradeEngine 側 (rnb 非該当)

lot floor: stage-1 は shadow のため発注なし。**stage-2 (live) 移行時は 1000u 固定** (lot ladder テンプレ第 1 段、PR #165 凍結) — stage-2 自体が別途 R1。

## 5. R2 自動 demote gate 併設案 (「無条件 emit は EV<0 で汚染源化」教訓の適用)

| stage | gate | 発動 |
|---|---|---|
| stage-1 (shadow) | shadow N≥30 (dedup_violation=0) で WR の Wilson_hi < 42.9% (gross BEV) | `auto_start: False` 化を R2 起案 (shadow DB 汚染源化の停止) |
| stage-1 (shadow) | 既存 shadow-promote R2 alert (30d N≥10 EV<0 → WARN / N≥30 → CRITICAL) | 監視対象に自動包含 (QUALIFIED 化で alert の母集団に入る) |
| stage-2 (live 1000u、将来) | live N≥10 EV<0 | `SHADOW_DEMOTED_CELLS` へのセル登録 = R2 即断 (lot ladder テンプレの降格則) |

## 6. Pre-reg LOCK 草案 (stage-1 forward)

- **LOCK ID 案**: `rnb-support-bounce-shadow-forward` (登録デプロイ日に確定)
- **estimand**: 登録デプロイ後の forward shadow rows (USD_JPY, BUY, dedup_violation=0, bucket 3 分割準拠) の WR / net EV (friction 2.14p)
- **first look**: shadow N≥41 到達時 or 2027-01-15 の早い方。**それまで gate×outcome joint 計算禁止 (P-10 型)**。中間再計算禁止 (sr_anti_hunt forward 枠と同型)
- **採用境界 (stage-2 R1 起案条件)**: N≥41 で Wilson_lo(WR) > 49.0% ∧ net EV > 0
- **棄却境界**: Wilson_hi(WR) < 42.9% (gross BEV) → クローズ + auto_start=False 提案
- **どちらでもない場合**: N≥82 まで継続し再判定 (1 回限り)
- **頻度前提の検証**: registry 期日 10-06 に §2.3 の実測で forming-bar 頻度を読む。active-hours 窓込み実測 < 1.0/週 → registry 既定により登録提案ごとクローズ

## 7. user 決裁欄

| # | 決裁事項 | 選択肢 |
|---|---|---|
| D1 | stage-1 shadow-only 登録 (§4) を執行するか | [ ] GO / [ ] NO-GO / [ ] 期日 10-06 の頻度実測 (§2.3) を見てから再提出 |
| D2 | §6 pre-reg LOCK 草案の承認 (D1 GO の場合のみ) | [ ] 承認 / [ ] 修正指示 |
| D3 | §2.3 の block-counts 日次読み手 (手順のみ、コード変更なし) の実施 | [ ] GO / [ ] 不要 |

**推奨**: D3 = GO (期日 10-06 の判定成立に必須)。D1 は「shadow N 源の価値 (2.99/週、M1/M3 の統計 power への寄与) が登録複雑性を上回る」かの判断 — BT evidence は昇格を支持しないが登録 (観測) を妨げる水準でもない (net EV +0.04p は境界内。net EV < −1.0p なら起案自体を見送る基準で設計)。

## 8. registry 変更提案 (本セッションでは registry を変更しない)

- `rnb-support-bounce-registration-decision` の message に追記: 「R1 パケット起案済み ([[rnb-support-bounce-r1-packet-2026-09-10]])。BT evidence は昇格 gate 不成立 (net EV +0.04p / Wilson_lo 46.8% < BEV 49.0%)。期日判定は §2.3 の active-hours 込み実測で行う。決裁は packet §7」
- D1 GO 時: `rnb-support-bounce-shadow-forward` LOCK エントリ新設 (§6 の数値境界をそのまま転記)
