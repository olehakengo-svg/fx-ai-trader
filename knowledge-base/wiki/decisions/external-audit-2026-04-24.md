# External Audit — 2026-04-24

> **セッション冒頭で要請された冷徹・第三者視点の外部監査 (quant-fund-board level) の記録.**
> 以降のセッションで判断材料として参照する. 再評価・更新時は新規 audit ページを作成、
> 本ページは historical snapshot として保持する.

## 0. Audit Scope
1. **Gap Analysis** — Roadmap v2.1 の約束 vs 実態
2. **Over-engineering / "means-to-an-end syndrome"** — 形骸化検出
3. **Resource allocation** — 研究過多 / 実装不足の検証
4. **MVP critical path re-roadmap** — To-Don't / Must-Do list

観察日時: 2026-04-24 (Tokyo morning)
評価者: Claude Opus 4.7 (as 外部クオンツアナリスト)

## 1. Gap Analysis: Roadmap v2.1 promises vs reality

### 公約 (roadmap-v2.1.md)
- DT "trunk" 年 **+433 pip** (3 ELITE 戦略で)
- Scalp "branch" 年 +200 pip
- 合計 年 +633 pip
- Gate 1 (Kelly>0): Week 1-2
- Gate 2 (Monthly 100%): Week 2-3

### 実態 (本監査時点)
| 指標 | Roadmap 前提 | 実測 | Gap |
|-----|------------|------|-----|
| DD | < 20% | **28.01%** | 過剰防御発動 (lot 0.2x) |
| Live PnL (post-cutoff 16d) | 月 +100%ペース | **-171.9 pip** | **乖離** |
| Aggregate Kelly | > 0 (Gate 1) | **0.0** | N 不足 + 負 EV |
| Ruin Probability | < 0.1% | **0.78%** | 20x 悪化 |
| ELITE 3 戦略 fire 率 | Live 主力 | **2.4%** (97.6% shadow) | **重大: gate bug** |
| vwap_mr Live EV | BT +1.025 再現 | **-4.77 pip/trade (N=10)** | **重大: 濃毒化** |

### Gap の構造的原因
1. **Gate 実装漏れ** (本監査で特定) — ELITE を MTF/Q4 gate が把握せず 97.6% shadow.
   KB "ELITE_LIVE (never shadowed)" 宣言と実挙動の乖離.
2. **BT-Live divergence** — vwap_mr 等で BT vs Live で ~5pip/trade の差.
   lesson-bt-live-divergence に 6つの楽観バイアス記載済だが実対策未着手.
3. **N 蓄積ペース** — Live N=14 (目標 20) で Kelly 計算不能. ELITE fire 率低下が原因.
4. **KB-reality divergence** — "vwap_mean_reversion が Live N の ~80% 占有" と記述
   (unresolved list) だが実測は bb_rsi_reversion が 50% dominant、vwap_mr は 4%.
   → **自動 sync KB だが判断材料として古い**.

## 2. Over-engineering / "means-to-an-end syndrome"

### 検出事例
| 系統 | 投入リソース | 実装 output | 判定 |
|------|-----------|------------|------|
| Phase 4a-e regime classifier 進化 | ~6 セッション | Phase 4c/4d 全て null | 🔴 過剰 |
| MTF regime engine | 4 phase 改版 | Phase 2a.1 deploy 保留中 (5/7 まで) | 🟡 良い規律 but slow |
| Pre-registration framework | 極めて elaborate | 実装に繋がる率 低 | 🟡 統計厳格 but heavy |
| Confidence_v2 rollout | 別 pre-reg + Q4 gate safety net | 本監査で ELITE bypass 判明 | 🔴 patch-on-patch |
| Shadow tracking system | 成熟 | clean-data 蓄積 slow | 🟡 infrastructure OK |

### 核心的所見
- **Research-heavy, shipping-light**: KB 追加速度 >> コード修正速度. 本監査直前まで ELITE
  97.6% shadow の **基礎 gate bug** が未特定だった. Phase 4a-e の 2D/3D cell 探索より
  先に Phase0/MTF/Q4 gate の整合検査 (5 行 grep で済む) が優先されるべきだった.
- **Null result の固執**: Phase 4c/4d で Scenario A (null) が続いても「Signal B (ADX) で
  再検証」「v7 feature 再設計」と延長. `lesson-premature-neutralization` 遵守は良いが、
  N power 不足は 16 日 Live では絶対に解決不能 — **時間軸ミスマッチ**.
- **Means-to-end の逆転**: pre-registration framework 自体が目的化しつつあった. 本来は
  エッジ確認のツールだが、Phase ナンバリングとログ生成が主成果に見える.

## 3. Resource allocation

### 投入ログ (直近 5 セッション)
- **分析セッション**: ~70% (cell-level scan, MTF regime, TP-hit causal, confidence q4 paradox 等)
- **実装セッション**: ~20% (Phase 2a.1 preparation, confidence_v2 rollout 等)
- **KB 整備**: ~10%

### 最適配分への乖離
- ELITE gate bug の特定は **30 分**で済んだ (code read + grep) — **6 セッション早くやるべきだった**
- vwap_mr 緊急トリップの判断は **16 日 Live データ**で可能 — しかし「BT と Live の乖離」lesson
  が既にあるのに適用されず
- 結論: **「高価な研究」よりも「安い実装検査」を優先する分配** への転換が必要

## 4. MVP critical path

### Catch-22 (核心問題)
1. BT STRONG α 戦略 (ELITE 3) は Live で fire せず
2. 結果として **fire している戦略は主に FORCE_DEMOTED Shadow** で学習汚染リスク
3. 一方で OANDA 送信される数少ない戦略 (vwap_mr 等) は **Live で負 EV**
4. → N 蓄積も Kelly 計算も両方 stuck

### Must-Do (優先順位)
1. **[DONE]** ELITE gate bug 修正 (Patch A, B) — PR #1 / merged 9ad84a0
2. **[DONE]** vwap_mr OANDA 停止 (Patch C) — 同 PR
3. **[DONE]** vwap_mr v2 filters Shadow 検証 (Patch D) — 同 PR, heuristic 閾値
4. **[PENDING]** 24-48h 観測: ELITE 3 shadow 率が 97.6% → 数% に低下することを API で確認
5. **[PENDING]** Render 環境変数 `VWAP_MR_OANDA_TRIP=1`, `VWAP_MR_V2=1` が有効なことを確認
6. **[PENDING]** Live N≥20 到達 (現 14 + ELITE fire 回復で ~2-3 日で達成見込)
7. **[PENDING]** Aggregate Kelly 初回有効計算
8. **[PENDING]** ELITE 3 の Live EV が BT と ±1 pip 以内で一致するか検証

### To-Don't (禁止事項)
1. 🚫 **新戦略リサーチ** — 既存 ELITE の Live 復活が先. Phase 4e/5 着手は Gate 1 通過まで保留.
2. 🚫 **MTF/classifier 追加改版** — Phase 4c/4d で null 2連 → feature engineering より
   **データ quantity** が律速. 同じ改版を Signal B/C/D で繰り返すのは定義的に reactive.
3. 🚫 **新 filter 閾値を BT 校正なしに production へ** — v2 filters は Shadow 限定で、
   OANDA 復活は Shadow N≥20 正 EV 確認まで.
4. 🚫 **KB のみの update commit** — コード変更と KB 更新は必ず同一 commit (CLAUDE.md ルール).
5. 🚫 **pre-reg なしの production code change** (bug fix 以外).

### Re-roadmap (2026-04-24 〜)
```
Week 1 (〜2026-05-01):
  - Patch A/B 効果観測 (ELITE fire 率回復)
  - vwap_mr Shadow v2 filter N 蓄積開始
  - Live N≥20 達成
Week 2 (〜2026-05-08):
  - Aggregate Kelly 有効化
  - Phase 1 holdout 2026-05-07 通過判定
  - vwap_mr v2 filter の Shadow EV 初回評価
Week 3-4 (〜2026-05-22):
  - Kelly>0 (Gate 1) 達成 or 次の stopping rule
  - ELITE 3 BT-Live divergence 定量評価 (BT EV vs Live EV ±1pip)
  - vwap_mr v2 閾値校正 (N≥50 達成時)
```

## 5. 本監査からの Action Items (tracked)

| # | Action | Owner | Status | Evidence |
|---|--------|-------|--------|----------|
| A1 | ELITE gate bug 修正 (Patch A/B) | Claude | ✅ DONE | PR #1 merged 9ad84a0 |
| A2 | vwap_mr OANDA 停止 (Patch C) | Claude | ✅ DONE | 同 PR |
| A3 | vwap_mr v2 filters Shadow 投入 (Patch D) | Claude | ✅ DONE | 同 PR |
| A4 | 24-48h ELITE fire 回復観測 | User | ⏳ PENDING | API query 後日 |
| A5 | Render 環境変数確認 | User | ⏳ PENDING | Render dashboard |
| A6 | Live N≥20 到達 | Market | ⏳ PENDING | `/api/demo/stats` |
| A7 | Aggregate Kelly 有効化 | Claude | ⏳ PENDING | A6 後 |
| A8 | vwap_mr v2 Shadow N≥20 達成 + EV 評価 | Market + Claude | ⏳ PENDING | 推定 2-3 週 |
| A9 | ELITE Live EV vs BT 一致検証 | Claude | ⏳ PENDING | N≥20 後 |

## 6. 本監査の限界
- 短期観察: 本監査はコード readonly grep + API 集計 1 スナップショットのみ. Walk-forward
  effect や市場 regime shift の影響は未評価.
- Heuristic 閾値: v2 filter (slope 0.3, ADX 22, hours 7-20) は BT 校正されていない.
- 監査者 (Claude) の訓練データ cutoff 2026-01 以降の market structure shift は未反映.

## References
- [[roadmap-v2.1]] (公約)
- [[elite-freeing-patch-2026-04-24]] (surgery 実装詳細)
- [[audit-completion-protocol]] (post-audit 完了追跡フロー)
- [[lesson-reactive-changes]] (1日データ判断禁止)
- [[lesson-bt-live-divergence]] (6 楽観バイアス)
- [[lesson-premature-neutralization-2026-04-23]] (Null closure 禁止)

## 更新履歴
| Date | Change | Reason |
|------|--------|--------|
| 2026-04-24 | 初版 | Session 冒頭監査の永続化 |
