---
id: 20260817-e7-phase1-discovery-oos
title: "[v2.3 供給ライン] E7 phase-1 — discovery→凍結→OOS verdict 執行 (前倒し: 凍結期日 08-21 / verdict 期日 08-28)"
owner: claude (session sharp-pike-eec3e7)
status: done
claimed_at: 2026-08-17T05:10:00+0000
priority: P1
roadmap_gate: "トラックB 供給ライン最終 2026 マイルストーン。pre-reg = [[e15-e7-event-modality-prereg-2026-07-18]] §6 (🔒 phase-0 FULL LOCK 済み family)。純研究、live/shadow/Kelly 変更なし"
rule: R1 手続き (pre-reg 執行、判定は機械。設計自由度ゼロ)
executor_note: "pre-flight §3.3c 完了済み (panel 凍結、実効 12 combo = θ=0.5 のみ、modal 予想 C3/C5)。phase-0 の 9 日前倒し前例に準拠して前倒し執行。排他 claim = 本 ticket + draft PR"
prereq_artifacts:
  - knowledge-base/wiki/decisions/e15-e7-event-modality-prereg-2026-07-18.md   # SSOT §6/§5b/§5c/§8
  - raw/bt-results/e7/e7_surprise_panel.csv                                     # 凍結サプライズパネル (§3.3c)
  - tools/event_modality_lib.py                                                 # 共有実行機構 (event_trade/ATR/canary)
---

# 要求仕様 (pre-reg §6 の執行 — phase-0 ticket と同型)

1. **ハーネス拡張**: E7 sign-follow (z>+θ→USD long / z<−θ→USD short、fade 禁止)、entry = t_e 後 {+1,+2} 本目 M15 open、h∈{1h,4h,24h}、24 combo (θ=1.0 は §5b(iii) ゲートで機械脱落見込み — grid 定義は変更しない)。z は凍結パネルから join のみ (再計算禁止)。
2. **discovery** (§5a 準拠、探索窓 〜2023-12-31、OOS 接触禁止): 選抜 4 条件 (EV_te>0 ∧ EV_ft>0 ∧ N≥60 ∧ blocks≥40 ∧ fold 2/3) → 凍結規則 (fold → EV-per-vol → イベント種 ≤3) で m₁ ≤ 8。
3. **候補凍結**: pre-reg §6 へ凍結表追記コミット = 🔒 + `raw/bt-results/e7_frozen_candidates.json`。
4. **OOS verdict** (§5c 完全同一: block bootstrap B=10k + IM t / max(p) / BH q=0.05 (m=m₁) / レグ B 経済性 / ナイフエッジ 4 点)。canary/join 契約を tests/ に pin してから OOS 接触 (§10-6)。verdict は pre-reg §13 追記 + registry `e15-e7-event-prereg-phase1-verdict` resolve + changelog。
5. モジュールトップ副作用禁止 / silent except 禁止 / 既存テスト green + check.py。KB 同一コミット。


---

## 完了 (2026-08-17、同日)

- discovery 0/24 選抜通過 → m₁=0、OOS 非接触で phase-1 FAIL 確定 (pre-reg §13)。
- 機械ガード: 台帳再現 13/13 / census §3.3c 一致 / 符号・estimand spot check / self-test 24-combo。
- §8 分岐: 両 phase PASS=0 → イベントモダリティ枯渇 → E12 格上げ。registry resolved。

## Claude Review

**レビュー実施**: 2026-08-17 (実行者と同一セッションだが敵対的自己検証を明記)。

- **手続きの pre-reg 忠実性**: discovery-e7 は §6 grid (24 combo、θ/entry/h の凍結値) と §5b
  選抜 4 条件 + 凍結辞書式規則を phase-0 と同一関数 (`select_and_freeze`) で執行。grid から
  θ=1.0 を外さず、ゲートに機械的に落とさせた (§3.3c 予告との整合)。OOS 窓は結合統計に
  非接触のまま (m₁=0 で OOS ステップ自体が発生せず)。✅
- **look-ahead 排除**: estimand は lib SSOT (`event_trade`) を無変更で再利用 — entry=t_e 後
  +1/+2 本目バー open (w0_min=15/30)、ATR は entry 前完結 daily のみ。z は凍結パネルからの
  join のみで再計算ゼロ (panel 側の look-ahead canary は既存 test pin)。✅
- **反証チェック (FAIL 側の検証)**: 符号規約 (`usd_leg_dir`) の直接検査 + 2020-06-05 NFP
  (z=+30.79) × USD_JPY のハーネス外手計算で time-exit +10.46p 完全一致・方向 +1 —
  「符号逆実装による偽 FAIL」を排除。census-e7 (counts のみ) が §3.3c pre-flight の
  block 実測 8 値すべてを再現 = panel join と窓分割の正しさを独立確認。✅
- **成果物整合**: e7_discovery.json (24 cells) / e7_frozen_candidates.json (m₁=0) /
  test pin 4 件 (combo 空間・census 再現・self-test・artifact 整合) green。✅
