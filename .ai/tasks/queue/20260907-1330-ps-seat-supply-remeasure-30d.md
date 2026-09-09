---
id: 20260907-1330-ps-seat-supply-remeasure-30d
title: "[M3 スループット] ps 席供給是正 (PR #172) の 30d 供給率再計測 — capture ≥80% 検証 + 未達時 §8 補足検証"
owner: unclaimed
status: in_progress (harness merged 2026-09-09; awaiting window completion 2026-09-11)
created_at: 2026-09-07T13:30:00+0900
priority: P1
deadline: 2026-09-10 (registry `ps-seat-supply-remeasure-30d` — 期日厳守、T5 型実行ギャップ防止)
roadmap_gate: "M3 (clean live N≥30 セル×3) のスループット回復検証。ps×5 は LIVE 資格ロースタの中核 (現行 3 セル/30d の 2 本が ps 系)。旧 Gate 表現では Gate 1 (N 蓄積) 相当"
rule: R3 (計測・診断のみ。live パラメータ/tier/lot 変更は一切しない — demote 判断は別 registry `ps-carveout-regate-post-172` の領分)
prereq_artifacts:
  - knowledge-base/wiki/analyses/price-shock-seat-supply-audit-2026-07-29.md (§1-2 計測手法 / §8 補足検証項目 / §9 執行記録・検証計画 4)
  - knowledge-base/wiki/decisions/prereg-trigger-registry.json (`ps-seat-supply-remeasure-30d`)
  - knowledge-base/wiki/decisions/ps-carveout-firstweek-regate-disposition-2026-08-12.md (初週窓無効の判定経緯)
---

# 目的 (1タスク1目的)

席供給是正 (PR #172、2026-08-11 deploy: 席優先 select_best + live feed MASSIVE 統一) が、
price_shock_rev family の供給率を design の ~31% (監査 §1 実測) から **capture ≥80%** へ
回復させたかを、監査 §2 と同一手法で再計測し、verdict を KB + registry に記録する。

# 仮説

「ps family 無発火の主因 = HourlyEngine winner-take-all × score 非対称 (root cause §3) であり、
席優先 select で design 供給率が回復する」。これが正しければ:
- ps×5 の N 蓄積レートが design (~0.4/日 × 5 席) に戻り、`ps-carveout-regate-post-172`
  (09-30、clean live N≥10 → EV 判定) と lot ladder 昇格判定への N 供給が確保される
- M3 スループット律速 (LIVE 発火 3 セル/30d、到達 ~14 ヶ月) の一角が解消し、
  「発火機会不足は摩擦調整 EV 不在の帰結」仮説 ([[live-roster-attrition-2026-09-06]]) の
  検証材料が増える

# 対象データとデータ分離 (混合禁止)

| 系列 | ソース | 用途 |
|---|---|---|
| design 期待 | MASSIVE H1 canonical (ローカル parquet cache)。本番と同一 signal 条件 (log_return ≤ rolling 1%-tile ∧ vol_q、監査 §1 と同一コード経路) を再計算した signal bar 数 | 分母 |
| 観測 rows | 本番 Render API `/api/demo/trades` (全ページ取得)。window = **2026-08-11T00:00Z 〜 2026-09-10T23:59Z** | 分子 |

- 観測 rows は **LIVE (`oanda_trade_id != ''`) と shadow を別々に計数**して併記する (合算 capture が主指標)。
- dedup: `dedup_violation != 1`、key = `(entry_type, instrument, direction, bar_ts)`。
- **EV / WR / PnL は計算しない** — 本タスクは供給率のみ。EV 判定は `ps-carveout-regate-post-172` (N≥10 到達時) の凍結手続きに委ね、joint 計算で look を burn しない。
- 対象 = ps 5 席: EUR_GBP / AUD_JPY / NZD_JPY / EUR_AUD / USD_CAD (vol_q 条件は監査 §1 の表と同一に凍結)。

# 実行手順

1. **早期実施チェック** (実行日が 09-10 より前の場合): 観測 rows N≥15 なら即実行可 (registry 規定、design ~0.4/日 × 30d ≈ 12-14 = capture ~100% 相当)。N<15 なら 09-10 まで待って window を完全にしてから実行する (中途窓での verdict 禁止)。
2. design 期待の再計算 (§1 手法)。`tools/price_shock_exit_counterfactual.py` の population 手順を流用可。新スクリプト化する場合は `tools/ps_seat_supply_remeasure.py` — **module top での副作用禁止** (os.environ / parse_args / chdir、lessons 準拠)。
3. pair × (design 期待, 観測 LIVE, 観測 shadow, capture) の表を作成。Wilson 区間を併記 (小 N の点推定単独引用を防ぐ)。
4. capture < 80% の場合のみ **§8 補足検証**を同タスク内で実施:
   - AUD_JPY hedge_block (15m shadow SELL 由来、実測 56 件/5.5h の前例) の寄与分離 — block ログ/telemetry で「signal bar × hedge_block 同時刻」の件数を数える
   - 再起動 blackout 床の実測 — Render deploy 一覧 (deploy churn は PR #201 でゼロ化済みのはずだが実測で確認) × warmup 時間 → 恒常取りこぼし率の床
   - 残余 = 未説明分として正直に記録 (帰属を盛らない — roster-attrition の E カテゴリ規律)
5. KB 記録: `knowledge-base/wiki/analyses/ps-seat-supply-remeasure-2026-09-10.md` (監査ページ §9 検証計画 4 への back-link 付き) + 監査ページ末尾に verdict 1 行追記 + registry エントリ更新 (下記 verdict に応じ resolve or roll) — **全て同一コミット**。

# 採用/保留/棄却の境界 (数値)

- **ACCEPT (供給回復)**: design 期待 N≥15 ∧ capture_total ≥80% → registry `ps-seat-supply-remeasure-30d` を resolved 化。`ps-carveout-regate-post-172` の N≥10 到達見込み日を実測レートで更新。
- **NEEDS_MORE_EVIDENCE**: design 期待 N<15 (市場が signal を出さなかった = 検証 power 不足) → capture 判定は保留、§8 精査はスキップ可、registry deadline を +30d roll して再計測条件 (design N≥15) を明記。
- **REJECT (供給未回復)**: design 期待 N≥15 ∧ capture_total <80% → §8 補足検証を完遂し、pair×要因の定量表を出す。是正案がある場合も**実装しない** — 別パケット (R1/R3 の別タスク) として起案のみ。

# 受け入れ条件

- [ ] pair×5 の capture 表 (design/LIVE/shadow/capture/Wilson) が analyses ページに存在
- [ ] verdict (ACCEPT / NEEDS_MORE_EVIDENCE / REJECT) が上記境界の数値とともに明記
- [ ] registry 更新が同一コミットに含まれる (`python3 tools/sync_kb_index.py --write` 済み)
- [ ] `python3 -m pytest tests/ -x -q` green / `python3 scripts/check.py` pass
- [ ] コミットメッセージに `rule:R3` 明示

# 検証コマンド

```
python3 -m pytest tests/ -x -q
python3 scripts/check.py
python3 tools/sync_kb_index.py --check
```

# 禁止事項

- 本番 DB / Render env / `.env` / OANDA 秘密情報への書込み・変更は禁止 (本番 API は read-only 取得のみ)
- live パラメータ・tier・lot・gate の変更禁止 (計測タスク。REJECT でも是正実装は別タスク)
- EV×outcome の joint 計算禁止 (P-10 型 look 保全 — EV 判定は ps-carveout-regate-post-172 の凍結手続きのみ)
- 既存の未コミット変更 (ローカル main working tree に他ジョブ由来の変更あり) を壊さない — **作業は worktree で行う** (main checkout 座礁教訓)


---

# 進捗 (2026-09-09、rule:R3 — Claude autopilot)

**ハーネス実装・マージ済み**: `tools/ps_seat_supply_remeasure.py` + `tests/test_ps_seat_supply_remeasure.py` (19 pins)。
判定境界 (design N>=15 / capture 80% / 早期実施 N>=15) と「中途窓での verdict 禁止」は
prose ではなく `decide_verdict` にコード実装済み。

**手順 1 (早期実施チェック) の結果 = 実施不可**: 観測 unique N=**7** < 15。
→ 規定どおり 09-10 の窓完成を待つ。中途窓 verdict は出していない。

**中途窓 diagnostic (as-of 2026-09-09T03:00Z、実効 29.1/31 日)**:
design 期待 **34** / 観測 unique **7** (LIVE 6 / shadow 1) / capture **21%** [Wilson 10-37%]。
NZD_JPY / EUR_AUD / USD_CAD は観測ゼロ (design は 6/7/4 本存在)。
design 34 は既に判定床 N>=15 を超えているため、**窓完成時の分岐は REJECT がほぼ確定**
(残り ~1.9 日で観測が +27 件になる経路は無い) → §8 補足検証が発動する見込み。

**追加 finding (§2 of the analyses page)**: 観測 7 行のうち closed-bar design signal に
対応するのは 1 行のみ。live は forming bar を評価するため、capture の分子と分母が
ほぼ交わらない別母集団になっている。§8 の 3 項目に含まれない第 4 の要因であり、
別 R3 パケット (P-1) として起案済み。pre-reg 中の指標書き換えは行わない。

**残タスク (09-11 以降、1 コマンド)**:
```
python3 tools/ps_seat_supply_remeasure.py --json
```
→ verdict 確定 → REJECT なら §8 補足検証 (hedge_block 寄与 / blackout 床 / 未説明残余) を完遂
→ analyses に verdict 追記 + 親監査 §9 に 1 行 + registry resolve/roll を同一コミット。

KB: `knowledge-base/wiki/analyses/ps-seat-supply-remeasure-2026-09-10.md`
