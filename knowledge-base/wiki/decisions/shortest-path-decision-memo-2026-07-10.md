# 決裁メモ: 月利目標への最短経路 — ゼロベース再検討と承認パッケージ (2026-07-10)

**経緯**: user 依頼「最短経路を改めてまっさらな状態で検討して、目標達成に向けた提案もらえない？」(2026-07-09) → 8-agent workflow (調査4視点 + 統合 + 敵対的レビュー3レンズ、21 findings 反映) で再導出 → 決裁メニュー提示 → **user 承認「進めて」(2026-07-10、決裁メニューへの直接応答、ミッション委任 `feedback_mission_monthly_21_6pct` 準拠)**
**関連**: [[roadmap-v2.3-payoff-friction-repair]] / [[ws3-stage2-barrier-ev-prereg-2026-07-09]] (🔒LOCKED) / [[monthly-target-rederivation-2026-07-10]] (D5 の R3 導出本体)

---

## 1. ゼロベース再検討で確定した構造的事実 (2026-07-09/10 実測)

### 1a. agg-Kelly gate の実質恒久閉鎖 (最重要発見)
- live 転送は aggregate Kelly < 0 の間、以下を除き全ブロック (`modules/demo_trader.py` L6469-6492 付近): (a) N<10 sentinel、(b) minlot bypass 契約 3 戦略 (vix_carry_unwind / usdjpy_carry_dip_accumulator / sweep_reversion_eurgbp_late、≤1000u、L9153 frozenset)、(c) `edge_cell_force_live`、(d) control-panel sentinel mode
- **gate の母体は rolling 30d ではなく固定 cutoff (_FIDELITY_CUTOFF=2026-04-16) 以降の累積 clean トレード** (L9103-9145)。現値 −0.2758。月 5〜8 件の新セルでは累積を反転できない → **正 EV セルを昇格させても carve-out なしでは live 発火ゼロ**
- 実測: gate 実効化 (07-02) 以降の live fill は 7 日で 4 件のみ (全て N<10 sentinel)。trendline_sweep は shadow 23 / live 0
- **含意**: 「正セル成立 → live N 蓄積 → Kelly 学習 → 月利」の橋は、**per-cell carve-out の決裁が必ず挟まる**。エッジ探索と資本配管は同格の律速

### 1b. 出血の現況 (stale ベースラインの訂正)
- −245p/30d の大半は gate 実効化前のレジームの実現損。**gate 後 run-rate は ~−40p/30d 相当 (~17 fill/30d)**。追加 R2 停止の前向き増分は小さい (敗者事後選択バイアス込みで評価すること)
- N≈17/30d の book では月次 PnL はノイズ支配 (per-trade σ≈6.5p、VaR95 14.1p) — 「30d EV>0」単独を防御解除トリガーにしてはならない

### 1c. 月利の天井 (詳細 = [[monthly-target-rederivation-2026-07-10]])
- 21.6% の導出母体 (12-cell、2026-06-05) は live 経路残存 1〜2/12 でほぼ消滅。BE/Trail 水増し込み shadow 推定の二重楽観
- 現候補 2 セル (stage-2 対象) の天井: PASS 床 EV (+0.5〜1p/t) で **~0.15〜0.5%/月**、楽観 (+3p/t、LOT_CAP 10,000u) でも **~0.7〜2.4%/月**。21.6% = 60,244 JPY/月は stage-2 級セル ~15〜90 個相当 — **セル数が唯一のスケール変数**
- DD 防御 0.2x は +928.1p 回復が必要なラチェット構造 (DD_LOT_TIERS、eq_peak 非減衰、分母 1000p) — **取引による解除は数学的に不可能**。解除 = 再基準化のコード変更 (user 決裁事項)

## 2. 承認された決裁 (user「進めて」2026-07-10)

| # | 決裁 | 状態 |
|---|---|---|
| D1 | stage-2 pre-reg の LOCK | **zen-mahavira セッションが独立に執行済み** (2026-07-09 PR #73、user 承認「進めて」同日) — 本セッション提案の「§4 未定義分岐の本文修正」は **実施しない** (下記 §3) |
| D2 | 15m AUD_JPY shadow-only モード新設 (live 変更なし) | 実装中 (本セッション、worktree 隔離、別 PR) |
| D3 | **決裁 SLA 48h**: stage-2 verdict / 実装 pre-reg 等、pre-reg が user 承認を予定する提出物は、提出から 48h 以内に承認/差し戻しを目安とする (user 合意 2026-07-10)。滞留は registry (`prereg_trigger_watch`) が監視 | 有効 |
| D4 | **実装 pre-reg の必須項目** (stage-2 PASS 時に起案する R1 実装 pre-reg を拘束): (i) agg-Kelly gate per-cell carve-out 設計 (`edge_cell_force_live` 経路 or minlot bypass 契約準拠) (ii) R2 自動降格ゲート併設 (教訓: bypass 機構には必ず R2 gate) (iii) 判定はセル単位 (pool 判定は口座レベル判断専用 — M6 ゲートに使わない) (iv) shadow parity 検証 (fill/spread/slippage vs BT 前提) | 有効 |
| D5 | 月利目標の段階化: M1 (clean live 月次符号転換) → M2 (+0.5%/月) → M3 (+2〜3%/月、正EVセル5個以上が必要) → 21.6% は aspirational anchor に格下げ | [[monthly-target-rederivation-2026-07-10]] で文書化、index/CLAUDE.md 反映済み |
| 通知 | 探索2周目 stage-1 pre-reg を純研究として self-LOCK 予定 (stage-1 前例準拠) — 提案時に通知済み、user 異議なし | 起案中 |

**承認されなかった/取り下げた項目** (敵対的レビューにより provision 前に修正):
- ~~将来の実装 pre-reg への包括事前承認~~ → R1 個別承認の骨抜きになるため D3 (SLA) に置換
- ~~live 判定の 2 セル pool 化~~ → M6 セル単位ゲートと矛盾 (教訓: 集計は相殺する)。口座レベル判断専用に限定
- ~~LOCK 前の TV replica Pine 下書き~~ → pre-reg §3 の「検証装置は LOCK 後実装」と二重基準になるため中止
- ~~防御解除トリガー「clean live 30d EV>0」単独~~ → N≈17/30d ではノイズ。解除条件は「セル単位 live N≥30 ∧ Wilson 下限 EV>0 + 2 段ラダー (0.2x→1000u→5000u) + 各段 R2 復帰条件」を実装 pre-reg 側で規定する

## 3. stage-2 pre-reg §4 の未定義分岐の扱い (a priori 宣言)

- §4 の全体 verdict 3 分岐 (PASS / REJECT / UNDERPOWERED) は「(a) 通過だが (b)/(d)/(e) 不達」(例: 統計 PASS だが TV canon FAIL) を明示的にカバーしていない
- 本セッションは LOCK 前の本文修正を提案したが、**LOCK 執行 (07-09) と barrier sim の実行が先行しており、結果観測後の分岐定義変更は pre-reg 規律違反になるため実施しない**
- **扱い (今宣言)**: verdict が未定義領域に着地した場合、verdict 文書に「§4 未定義領域」と明示フラグし、帰属は user 裁定に委ねる (D3 SLA 48h 適用)。執行セッションによる暗黙の帰属は行わない

## 4. 分担 (2026-07-10 時点)

| 担当 | 領域 |
|---|---|
| zen-mahavira セッション (排他 claim `20260709-1610-ws3-stage2-barrier-ev-prereg`) | stage-2 執行 → **verdict 確定 2026-07-10 (PR #75、9日前倒し): ❌ PASS ゼロ / UNDERPOWERED** — lfr×EUR_USD クローズ、htf_fb×AUD_JPY は shadow N≥100 で1回限り再判定 (registry `ws3-stage2-underpowered-recheck`)。詳細 = [[ws3-stage2-barrier-ev-prereg-2026-07-09]] §8 |
| 本セッション | 決裁メモ (本文書) / D5 目標段階化 / D2 15m AUD_JPY shadow モード / 探索2周目 pre-reg 起案 |
| 別セッション (継続) | T-MTF 構造調査 (task_566c4c4d) / slippage 列 API 輸出 (task_d932525c) |

## 5. 最短経路の全体像 (承認済みプランの要旨)

```
トラックA (エッジ確定): stage-2 verdict (〜07-19) → PASS なら実装 pre-reg (D4 必須項目内蔵) → user 承認 (D3 SLA)
   → shadow parity (lfr ~4.9-5.9件/月, htf_fb ~2.5-3.3件/月) → live pilot 1000u (carve-out) → セル単位 live N≥30
トラックB (供給ライン): 探索2周目以降を常時運転 — セル数だけが月利をスケールさせる。stage-2 の結果に依存しない
トラックC (資本配管): carve-out 設計 (D4) / 防御解除ラダー (実装 pre-reg で規定) / OANDA_FORCE_FLAT_UNITS 再スコープ (正エッジ実証後に別 PR)
```

**正直なタイムライン**: 統計確認済み月次プラス (M1) = 最短 2026 Q4 末、現実的 2027 前半 (stage-2 PASS + 決裁順調の条件付き)。月次符号は 2026 Q4 にも揺らぎで出得るがノイズと区別しない。

## 6. 追記 (2026-07-10 同日): stage-2 verdict 着地によるトラック更新

- **stage-2 verdict = ❌ PASS ゼロ / UNDERPOWERED** ([[ws3-stage2-barrier-ev-prereg-2026-07-09]] §8、期日 9 日前倒し)。「MFE/MAE 非対称 ≠ 固定 barrier で EV 化可能」が実証され (lfr は SL 先着率 44-75% で全構成深負)、T2 exit-repair と合わせ **現行シグナル母集団の exit 側改善は完全否定**
- **トラックA は縮退**: 残るのは (i) htf_fb×AUD_JPY の shadow N≥100 再判定 (発火 ~2.5-3.3件/月では長期 — **D2 の 15m AUD_JPY shadow モードが到達の前提条件**) (ii) trendline_sweep×EUR_USD の live N 蓄積再評価
- **主戦線はトラックB (供給ライン) へ移行**: 探索2周目 ([[ws3-round2-explore-prereg-2026-07-10]]) は verdict の教訓を **LOCK 前・スキャン結果観測前に反映済み** — 選抜と OOS 判定の両方に first-touch EV レグを追加 (ratio 単独スクリーンの failure mode を構造的に排除)。加えて roadmap WS3 の T10 (gbp_deep_pullback) / T11 (sr_anti_hunt_bounce) 診断、および外部仮説 (学術/TV 由来) が既定候補
- **M1 タイムラインへの影響**: 「stage-2 PASS → 8月 live pilot」の最短分岐は消滅。M1 は供給ラインからの新 survivor (EV レグ込み) が前提となり、**最短でも 2027 前半、現実的には 2027 央** に後ろ倒し。トラックC (carve-out / 防御解除ラダー) の設計は survivor 到達時に即使えるよう D4 で維持
