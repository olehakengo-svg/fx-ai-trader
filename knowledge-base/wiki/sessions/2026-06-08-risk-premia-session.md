# 2026-06-08 セッション — 低 friction 高 TF risk-premia 3脈の検証と戦略再構築

owner: claude (一次実装) | rule: R1

## 経緯
「なぜ勝てないか」の雑談監査から、**低 friction 高 TF risk-premia** 仮説を立て、3脈を Claude 直接実装で検証 → 結果を踏まえ方針を再構築した。

## 成果物 (本コミットの帰属アンカー)
> 注: 下記ファイル群は並行自律セッションの commit (`fix(r2-audit)...`) に巻き込まれて
> tracked 化された (経緯: [[feedback_concurrent_agent_repo_hazard]] / tag `claude-risk-premia-2026-06-08`)。
> 本 session note はその作業の正規の帰属記録。

- **Phase 0**: `tools/fetch_massive_data.py` に 1d TF 追加 → 8 pair D1 backfill
- **TSMOM basket BT**: `tools/tsmom_basket_bt.py` / 結果 `raw/bt-results/tsmom_basket_2026_06_08.json`
- **判定 docs**:
  - `wiki/decisions/d1-tsmom-basket-pre-reg-2026-06-08.md` — TSMOM **NULL**
  - `wiki/decisions/price-shock-promote-readiness-2026-06-08.md` — Price-Shock **正常稼働・Shadow N 蓄積待ち** (訂正版)
  - `wiki/syntheses/strategy-rethink-2026-06-08.md` — **戦略再構築**
- **pre-reg specs**: `.ai/plans/claude/` 3本 (Price-Shock 再監査 / TSMOM / Carry)

## 結論
- TSMOM: NULL (gross からエッジ無し、USD 集中 54%、2016-26 hostile regime)
- Price-Shock: wiring 正常、1%-percentile shock の希少さで N 蓄積に数ヶ月、近道なし
- **再構築**: friction は二次の税、一次は edge-per-trade。**探索 → 検証済 narrow edge (orb_trap|GBP_USD|SELL 等) の N 蓄積へ軸足移動**

## 次アクション候補
(A) orb_trap|GBP_USD|SELL の現 Shadow N 確認 → ramp 計画 (B) 検証済 narrow edge portfolio tracker (C) Carry 保留
