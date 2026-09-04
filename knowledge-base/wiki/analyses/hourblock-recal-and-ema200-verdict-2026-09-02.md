# 静的 hour block 再較正 + ema200 診断 — verdict (2026-09-02、探索的 study。pre-reg 数値ではない)

user 承認 (2026-09-01「進めて」) の 2 分析。Workflow 3 エージェント (study ×2 + 敵対的検証)。
一次データ: `knowledge-base/raw/analysis/hourblock-recal-2026-09-02.json`。LOCK 遵守: vix 165 行 / sr_anti_hunt×EUR_JPY 97 行を母集団から除外、vix の EV 非計算。

## Study 1: v8.9 静的 hour block 再較正 (較正 2026-04 N=9〜54 → 今回 N=73〜352)

**中心結論 (敵対的検証で独立窓 04-14〜06-02 でも複製・頑健): 較正時の毒性は 6/6 block 全てで再現しない。**「block 帯が非 block 帯より悪い」は名目有意ですら 0/6 (Welch p=0.019〜0.74、有意だった 1 件は block 側が良い方向)。較正時 WR 9.5〜28.6% → 現行 34.8〜51.1% に正常化。per-strategy sign 集計も全 block で null = 系統的悪化構造は現存しない。

**敵対的検証による降格 (重要)**:
- H7-8×EUR_USD「block 帯の方が有意に良い (p=0.0074)」→ **複製窓で p=0.98、効果ゼロ**。正しい強度は「悪くない (parity)」であって「良い (superiority)」ではない
- LateNY WR 劣位 (Fisher p=1.7e-4) → **6 月以降にのみ出現、04-06 月窓では消滅** = 「構造」ではなく「直近 3 ヶ月の観測」
- 検証副産物: **API は 2026-04-02 まで 16,891 行を返す** (「保持 90 日」は API レベルで偽 — purge タイミング未検証、複製窓を使う分析は早期にデータ凍結すべき)

**冷や水 (最重要の横断所見)**: clean 比較対象自体が負 EV (USD_JPY −1.33 / EUR_USD −1.24 p/trade)。**どの時間帯も「勝てる場所」ではない** — block を外して得られる live 増は carry_dip の ~3 イベント/月 (帰属も交絡) のみ。**London/NY 実弾の律速は hour block ではなく「検証済みセルの供給」** (roadmap v2.3 の診断と一致)。

**verdict 表 (探索的分類、執行は全て別途 R1)**:
| block | verdict | 備考 |
|---|---|---|
| H13×USD_JPY | 撤去候補/セル限定免除候補 | 毒性消滅だが期間符号反転で不安定 |
| H16-20×USD_JPY | 維持 | 今も負け (mean −0.99、P2 −1.81)。相対悪化の証拠もない |
| H11×EUR_USD | 維持 (弱) | N=73 最小。複製窓では符号逆 |
| H7-8×EUR_USD | 撤去候補 (parity 根拠) | superiority 根拠は検証で崩壊 |
| EUR_USD Tokyo | 維持 | P2 で悪化方向 |
| EUR_USD LateNY | 維持 | WR 劣位は直近限定、EV は block 側良。gate コメントの WR9.5% は要更新 (R3 cosmetic) |

**推奨経路**: 個別撤去ではなく **「live 資格セル (min-lot carve-out 契約群) の静的 hour block class exemption」1 本の R1** — 根拠は「全窓で毒性証拠なし + per-cell リスクは 1000u 契約 + R2 ゲートで有界」。期待効果 +3 イベント/月 (小)。前例 = sweep gbp_asia 免除パケット (user 承認 2026-08-03)。

## Study 2: ema200_trend_reversal×USD_JPY units:0 — 根本原因確定 (R3 診断)

**バグではなく設計痕 + 窓アーティファクト**。audit の units:0 は `_open_shadow_emit_trade` (select_best 敗北候補の並行 shadow 記録、demo_trader.py L1486) が **リテラル units=0 をハードコード**する経路のマーカー。「100%」は監査窓 (08-12〜08-21、N=4) のアーティファクトで、広窓では 17 行中 12 行 (経路B) + 5 行 units=5000 (経路A)。**live 送信リスクはゼロ** (sent/filled 33 行は全て units>0)。実害 = audit units を size 換算に使う分析が経路 B 行で壊れる。

**R1 起票 (live 化) は非推奨 — 候補は精査で死亡**:
1. **quant-eval 07-31 の Bonferroni PASS (N=79 p=2.6e-6) は直近 90d で再現しない**: N=72 WR62.5% だが BEV 63.3% で mean EV −0.09p、二項 **p=0.608**。8 月は Overlap 自体が負転 (N=5 −22.1p、N 不足につき「消滅確定」ではない)
2. **重複 N 汚染 (新発見・重要)**: 同方向 <120s の近接重複 22 ペア (最短 0.4s) = **60s recent_emit dedup を突破**、実効 N≈50。07-31 の N=79 PASS は重複込み — `project_engine_reconstruction_live_dedup_dead` の変種 (dedup 系 5 例目相当)。**別 R3 診断起票**
3. live 累計は負 (2 行 −5.6p×2)、365d BT (04-20) は N=32 EV−0.183 と shadow に逆符号
→ 「過去 verdict 自体を疑え」(user 恒久指示 2026-08-05) の実践例: Overlap 勝ちセル筆頭候補は estimand 監査で棄却。

**修正 (R3、✅ 実装済み 2026-09-02)**: 機構は「in-memory dedup ゲートがプロセス境界を越えられない + boot 時 backfill が write-time ギャップを残す」と確定 (単一インスタンスで `shadow_called=1` なのに shadow_emit 2 行 = 2 行目は別プロセス由来)。→ `demo_db.open_trade` に **write-time の DB 参照 dedup flag** を追加 (共有 DB を見て同一キー・TF 窓内の dv=0 先行行があれば新 shadow 行を dedup_violation=1、挙動不変・行は保持)。**他戦略への影響 = 集計は 0.04% (90d intra-window dup 1,434 行中 1,431 は boot backfill が既に回収、未 flag は 3 行のみ) だが point-in-time 分析が水増しを見る**のが実害 (07-31 N=79 がその例)。同 PR で audit `block_reason` を `shadow_tracking(shadow_emit_no_lot)` に自己記述化 (units=0 = ロット未割当マーカー、サイズ非使用)。詳細: [[../lessons/lesson-shadow-emit-dedup-writetime-2026-09-02]]。

## 帰結: London/NY 実弾の残る経路 (優先順)
1. **新セル供給 (主戦線、変わらず)**: P-S1(a) N=9/10 待ち / E1 first look 10-15 / kalman 初 fill 監視
2. class exemption R1 (+3 イベント/月、衛生価値) — ✅ **執行済み 2026-09-02** (user 承認「どちらも進めて」)。pre-reg: [[../decisions/hourblock-class-exemption-prereg-2026-09-02]] / rollback: registry `hourblock-class-exempt-r2-rollback`
3. ema200 は候補から除外 / donchian×NZD は D-c-2(ii) 決裁通り shadow 蓄積継続 / orb_trap は FORCE_DEMOTED のまま
