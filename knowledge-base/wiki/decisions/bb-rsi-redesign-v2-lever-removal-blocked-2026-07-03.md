# BB_RSI_REDESIGN_V2 レバー撤去判断: BLOCKED (2026-07-03)

**Rule**: R3 (構造 evidence / code derivation、BT 不要)。本判断による挙動変更なし (docs のみ)。
**経緯**: [[edge-cell-e1-e4-code-disable-2026-07-02]] 「判明した KB 上の不整合」節で残置とした凍結実験レバー `BB_RSI_REDESIGN_V2` / `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` の撤去可否判断タスク。前提条件は「本番 env に未設定であることの確認」だった。

## 判定: 撤去不可 (BLOCKED) — 本番 env に BB_RSI_REDESIGN_V2=1 が設定済み

検証方法: Render 本番 web サービス (fx-ai-trader, srv-d6va1of5r7bs73en10vg) へ `render ssh` 相当 (`ssh srv-d6va1of5r7bs73en10vg@ssh.oregon.render.com`) で接続し、実行中インスタンスの `printenv` を直接確認 (2026-07-03)。dashboard 目視より強い証拠 (env group 経由も含む実効ランタイム値)。

結果:

| 環境変数 | 本番状態 | 備考 |
|---|---|---|
| `BB_RSI_REDESIGN_V2` | **=1 設定済み** | 撤去 gate に該当 |
| `BB_RSI_REDESIGN_V2_SHADOW_PROMOTE` | 未設定 | split_shadow_always は AND 条件で不発 |
| `DT_BB_RSI_MR_REDESIGN_V2` | =1 設定済み | **別戦略** dt_bb_rsi_mr (PAIR_PROMOTED) 用。T10 kill 対象外。名前類似につき混同注意 |
| `DT_BB_RSI_MR_REDESIGN_V2_SHADOW_PROMOTE` | =1 設定済み | 同上 |

## 由来

- **W4-Shadow-Redesign v2 プログラム** (2026-05-05, `.ai/tasks/done/20260505-1905-w4-shadow-redesign-v2-bb_rsi.md`, rule:R1)。BT verdict `INSUFFICIENT_BT_EVIDENCE` (proposed N=0 全4ペア) → v2 LOCK 規則「INSUFFICIENT_BT_EVIDENCE → shadow promote 推奨」→ 同 task Step 6「env flag で worker に登録」に従い Render に設定されたと推定。
- SHADOW_PROMOTE 側が当初から未設定だったか後に除去されたかは、記録がなく不明。
- **KB sessions / changelog に env 設定の明示記録なし** (運用穴)。R2 監視アラート (`raw/audits/shadow-promote-r2-alert-*`) は 2026-05-07 以降このレバーを既知として監視し続けている。

## 現在の実効性 (V2=1 の効果)

1. **split_shadow_always 節** (`strategies/scalp/__init__.py:163`): 不発 — SHADOW_PROMOTE 未設定 (AND 条件) に加え、consumer 側も 2026-06-12 `SHADOW_RETIRED_STRATEGIES` (`[R2_SHADOW_DEMOTE] skipped shadow_emit`) で不達の二重遮断。
2. **bb_rsi.py conf bypass** (`_v2_jpy_high_adx_tail`, `strategies/scalp/bb_rsi.py:302` 付近): **コード上は活性**。`BBRsiReversion()` は候補生成を継続中 (`strategies/scalp/__init__.py:57`) のため、JPY & ADX>=30 シグナルで MR anti-trend penalty が非適用になり conf が legacy 値のままになる。ただし row 経路ゼロ (live=E4 pin / shadow=06-12 retirement / loser emit=不達) のため **persisted rows・OANDA・lot への影響はゼロ**。score race も不変 (bypass は conf のみを変え、select_best は score 基準)。

帰結: フラグは「設定済みだが実質無風」。ただし redesign v2 の「default OFF preserves live behavior」設計前提が本番で崩れた状態であり、この env 設定下でのコード撤去は「挙動変更なしの証明」ができないため gate どおり BLOCKED。

## 撤去への正順 (提案、user 判断待ち)

1. Render dashboard で `BB_RSI_REDESIGN_V2` を削除 (redeploy 発生)。挙動差は bb_rsi 候補の conf 計算のみ = rows ゼロで無風、設計意図の default-off に復帰。
2. env 削除を再検証 (`render ssh` + `printenv`) 後、**別コミット**でコード撤去: `strategies/scalp/bb_rsi.py` の `_redesign_v2_enabled` + JPY high-ADX bypass / `strategies/scalp/__init__.py` の bb_rsi_reversion 節 / `tools/bb_rsi_shadow_bt.py` / `tests/test_bb_rsi_shadow_redesign_v2.py`。

### テストの扱い (前提3への回答)

`tests/test_bb_rsi_shadow_redesign_v2.py` は env 削除まで**維持**。default-off / double-flag gate を pin する regression テストであり、フラグが本番=1 になっている現状ではむしろ防御価値が高い。撤去時はコードと同一コミットで削除する。

### スコープ注意

- `tests/test_bb_rsi_ema_aligned_shadow_redesign_v2.py` は別レバー (`BB_RSI_EMA_ALIGNED_REDESIGN_V2`、戦略は REDESIGN_PENDING でコメントアウト中) 用。本判断のスコープ外。
- `split_shadow_always` には同型レバーが十数戦略分並列に存在する。bb_rsi 節のみの部分撤去はパターン非対称を生むため、撤去時は「W4 レバー群全体の棚卸し」として扱う方が整合的 (R2 アラートの `R2 Demote Manual Action` 節が env 削除候補を継続提示している)。

## 教訓

- **「Render env 読取ツールなし」([[edge-cell-e1-e4-code-disable-2026-07-02]]) は誤りだった** — `ssh <srv-id>@ssh.<region>.render.com 'printenv'` で runtime env を直接検証できる。今後の env 検証はこの手順を正とする。
- **実験レバー env の設定/削除が KB に記録されない運用穴**。Render env 変更は decisions/ or sessions/ への同時記録を必須とすべき (「コード変更とKB更新は同一コミット」の env 版)。

**関連**: [[bb-rsi-t10-kill-2026-07-02]] / [[edge-cell-e1-e4-code-disable-2026-07-02]] / MEMORY: project_bb_rsi_reversion_falsified
