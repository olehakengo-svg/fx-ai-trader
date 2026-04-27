# Pre-reg LOCK — bb_rsi_reversion × USD_JPY × scalp 復活案 [WATCH 確定]

**起案者**: 2026-04-27 evening session 後継 + Phase A audit (2026-04-27 19:30 JST)
**Rule**: R1 (Slow & Strict — Live promotion)
**承認状態**: ⛔ **OANDA_TRIP 解除は不採用 (Phase A 実測で前提崩壊)** → WATCH 維持確定
**最終更新**: 2026-04-27 (Phase A audit 完了後の append-only 結論)

---

## 1. 背景

H5 task (handover §1.5) は 4 並列 agent #3 (Aggregate Kelly path) の報告:
> bb_rsi_reversion × USD_JPY × scalp は Live 黒字 cell:
> Live N=74 WR=44.6% Wlo=33.8% ΣR=+7.21
> shadow-deep-mining-2026-04-24 の "全停止" は aggregate の話、cell 別では黒字

を起点に **OANDA_TRIP 解除 + 0.01 SENTINEL 復活** の Pre-reg LOCK 起案を求めた。

## 2. Phase A audit による前提崩壊 (確定)

`tools/phase_a_production_audit.py` で `/api/demo/trades?limit=2000` を direct read し、
post-cutoff (2026-04-16+) Live closed trade で再計測:

| 指標 | Agent#3 報告 | Phase A 実測 |
|---|---:|---:|
| bb_rsi × USD_JPY × scalp Live closed N | 74 | **8** |
| WR | 44.6% | **12.5%** |
| Wilson lower 95% | 33.8% | **5%以下 (推定)** |
| ΣR (or pip) | +7.21 R | **-20.8 pip** |

→ **Agent#3 報告は production と完全乖離**。同方向の符号一致もない (黒字 vs 赤字)。

詳細: `raw/audits/phase_a_production_audit_2026-04-27.md`

## 3. 結論 (確定)

**OANDA_TRIP 解除 を不採用**。**WATCH 維持** が確定。

根拠:
1. Phase A 実測で Live N=8 WR=12.5% は明確な赤字
2. 既存 emergency_trip (commit 4358-4374) の根拠 "USD_JPY×RANGE N=217 EV=-0.58" を覆す production 証拠なし
3. CLAUDE.md「ラベル実測主義」: production direct read を一次情報、Agent 報告は仮説扱い
4. CLAUDE.md「KB-defer 罠」回避と「Agent-defer 罠」回避 (lesson-agent-snapshot-bias-2026-04-28)

## 4. WATCH 維持の運用ルール

### 4.1 監視指標 (90 日 window)
- Live closed N (post-cutoff)
- Live WR
- Live Wilson lower 95%
- Live ΣPnL (pip)

### 4.2 自動 trigger (将来の OANDA_TRIP 解除候補)
以下を全て同時に満たした場合のみ、新たな Pre-reg LOCK を起案:
- Live N >= 30 (Bonferroni 補正前提)
- WR >= 50% (BEV 上回り明確化)
- Wilson lower >= 40%
- ΣPnL > +10 pip

### 4.3 永久 demote trigger
以下のいずれかを満たしたら entry_type レベルで FORCE_DEMOTED 維持:
- Live N >= 50 で WR < 35%
- 90 日継続で WR < 40%

## 5. 関連

- shadow-deep-mining-2026-04-24.md (aggregate 全停止の根拠 — 維持)
- emergency_trip implementation: modules/demo_trader.py:4358-4374 (BB_RSI_OANDA_TRIP)
- Phase A audit: `raw/audits/phase_a_production_audit_2026-04-27.{json,md}`
- Lesson: [[lesson-agent-snapshot-bias-2026-04-28]]
- Agent#3 出力: /private/tmp/claude-501/-Users-jg-n-012-test/d48e0764-.../tasks/a740bdb9... (要原因究明、別タスク)
