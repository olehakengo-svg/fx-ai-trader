# Track C 資本配管監査 — carve-out 欠落で「live 10 セル」は実質 wg×3 (2026-07-28)

**性格**: 構造診断 (Rule 3 類型の発見) + M1 会計の訂正。live 変更なし — 是正は
[[track-c-capital-plumbing-decision-packet-2026-07-28]] (R1 DRAFT) で user 決裁に付す。
**方法**: 7-agent workflow (wf_f1c7ed60-c19) → 敵対的検証 2 本 → **主要クレームは本セッションで
コード直接検証済み** (行番号は 2026-07-28 の main 相当)。

---

## 発見 1 (P0): agg-Kelly gate carve-out 欠落 — user 決裁「7 席再武装」が配管で無効化

**因果チェーン (全段コード検証済み)**:
1. ps×5 / dmb×2 は `_PAIR_PROMOTED` → `modules/demo_trader.py:6528-6532` で
   `_is_pair_boosted=True` となり **N<10 sentinel 免除から明示的に除外**
2. gate 本体 `demo_trader.py:7050-7079`: `_is_promoted ∧ mode≠sentinel ∧ ¬_is_sentinel ∧
   ¬_edge_cell_force_live` で agg-Kelly を評価
3. 累積 Kelly = **−0.22** (本番 API 実測 07-28。固定 cutoff 2026-04-16 以降の累積 N=563、
   月 ~17 fill では数学的に反転不能 = 恒久負、[[shortest-path-decision-memo-2026-07-10]] §1a どおり)
4. bypass frozenset `demo_trader.py:9848-9859` = {vix_carry_unwind, usdjpy_carry_dip_accumulator,
   sweep_reversion_eurgbp_late, weekend_gap_fade} のみ — **price_shock_rev×5 / donchian×2 は不在**
   → `blocked` → shadow 落ちが code 上確定

frozenset のコメント自身が 07-24 の weekend_gap 追加時に「agg-Kelly は恒久負のため min-lot bypass
不在だと live 発火が構造的に不能」と明文化している。07-28 の preserve 型 7 席再武装 (commit f01f92b7)
でこの手順が抜けた — **[[lesson]] _is_xau_inst (3.5 ヶ月送信死) と同類の「決裁執行の配管漏れ」**。
preserve バグ期間中は gate まで到達しなかったため未露呈、day-1 は該当イベント未発生で fill N=0 のため
無症状。**次の qualify シグナルで初めて blocked ログが出る**。

## 発見 2: 防御可能な live book 月次 EV は wg×3 の +22〜26p のみ (M1 会計の訂正)

初期集計 (+105p/月) は敵対的検証で棄却。訂正後の正準:

| セル群 | live 発火可否 | 月次 EV 点推定 | 根拠 |
|---|---|---|---|
| weekend_gap_fade ×3 | ✅ (bypass 内) | **+22〜26p** (実測 RT +7.90p/event × 執行 2.8-3.0/月) | 唯一の OOS-PASS。σ_month≈63p、単月負 34% は設計内 |
| price_shock ×5 | ❌ (発見 1) | **算入禁止 (不明)** | live exit が 3 層オーバーレイ (BE_LOCK B + ATR-BE/trail) で LOCK 済み horizon-exit 設計と乖離中 (R1 未決裁、[[preserve-exit-overlay-2026-07-28]]) + live N=0。DB ev_pip は feed artifact 込みで使用禁止 |
| donchian ×2 | ❌ (発見 1) | **算入禁止** | shadow N=14/16 小 N 昇格 (postmortem「N≤40 正 EV 全滅」パターン)、365d BT は CI 全負で FAIL |
| legacy (bypass 内) | ✅ vix_carry_unwind / usdjpy_carry_dip | ≈0 (直近 5 窓 fill 0) | vix_carry Overlap pilot は 06-09〜07-15 実現 **−23.2p (N=13)** — R2 レビュー項目としてパケットに収載 |
| legacy (bypass 外) | ❌ gate が全て block | 0 | 旧 −242.6p/月の bleed は gate 閉鎖により forward では停止済み (07-15 以降 live fill ゼロの正体) |

**M1 の正しい枠組み** (検証 agent の訂正): M1 = 符号転換 + 統計確認 (セル live N≥30 正 EV ≥1 ∧
book Wilson 下限 >0 相当)。律速は EV の大きさではなく **N 蓄積タイムライン** — wg 単独では
N=30 ≈ 2027-05。carve-out が直れば ps の頻度 (清浄監査トリガ率 ~24.5/月、guard 通過後は不明) が
N 蓄積を大幅加速しうる — これが carve-out 決裁の M1 上の意味。

## 発見 3: DD 100.8% は 3 層の測定 artifact (実 NAV −22.3%)

- `app.py:15296-15306`: 表示 `dd_pct = dd / max(1000.0, 1.0)` — **分母 1000 ハードコード**
  (env `OANDA_EQ_BASE_PIPS` すら見ない)
- `demo_trader.py:917-919 / 3236-3246`: equity = clean 期 pnl_pips の**lot-blind 単純和**
  (1000u の 1pip と 10000u の 1pip を等価積算) + eq_peak 非減衰ラチェット
- 実口座 (07-28 実測): NAV=279,009 JPY / 累積 −80,096 JPY → **実 NAV −22.3%**、うち大半は
  pip 台帳が除外済みの XAU 期 (−2,280p) の損 — **2 つの台帳は別物を測っているのに両方「DD」と呼称**
- 同族: `demo_trader.py:10004-10009` `_get_ruin_probability()` も initial_capital=1000pip ハードコード
- ⚠️ 分母修正 = 即 0.2x 解除ではない。clean 期 JPY 台帳の実測 (D-a、実行中) が先 —
  1000u 主体なら DD ≈3-4% (→0.60x) だが混在 lot なら ≥8% (→0.20x 維持) もあり得る

## サイジング拘束の順序 (何を直すと何が変わるか)

1. **carve-out 欠落** (発見 1) — DD をいくら直してもここが先に塞ぐ。是正は D-c
2. **固定 1000u pre-reg 契約** (wg/ps) — lot chain を上書きするため DD 0.2x 解除の影響ゼロ。
   lot↑ は各セル live N≥30 ∧ EV>0 後の個別 R1 のみ (既定どおり)
3. **DD defensive 0.2x** — 現在バインドするのは dmb×2 と将来 edge-cell carve-out
   (`demo_trader.py:6912-6914`: 5000u pre-reg が 0.2x で 1000u に潰される構造) のみ。是正は D-b
4. agg-Kelly 上方 boost (`9939-9973`) は累積 Kelly<0 の間 1.0 固定 — Kelly Half 3.0x への
   aggregate 経路は構造的に死んでいる (変更提案なし、事実の記録)
5. 複利: equity が pip 建てのため複利サイジングの概念自体が配管に不在。JPY 台帳化 (D-a/D-b) が前提

## ruin 63% 教訓との整合

- ruin 63% の負け筋は「lot scaling vs 薄いエッジ」(証拠金 4×NAV) であり DD 分母の測り方ではない —
  本是正はいかなる aggregate lot 増も含まない
- ただし index.md (07-07)「realized ruin 0% は 0.2x cap が保っている」に正直に向き合う:
  累積 Kelly<0 の book で無条件 1.0x 復帰は ruin を実際に増やす → パケットは
  「tiers/MC ruin gate は正しい分母で存続 + セル単位解除ラダー」を拘束条項化
- ruin 計量 (1000pip/閾値 500pip) も同時に NAV 比へ揃えないと gate が二重基準になる

## 教訓 (lessons 昇格候補)

**「決裁の執行」には、その決裁を無効化しうる全 gate の carve-out 監査が含まれる。**
live 化決裁の checklist に「送信経路の全 gate (agg-Kelly / spike / spread / dedup / HTF /
watchdog) を列挙し、当該セルの通過可否を code で確認」を必須化する。_is_xau_inst (transport 層) と
本件 (risk gate 層) は同じ死型の別レイヤー再発。
