### `[[lesson-is-shadow-filter-mandatory-2026-04-30]]`
**発見日**: 2026-04-30 | **修正**: `_gen_cell_stats.py` is_shadow 分離対応 + lesson 化 (本ページ) + `live_only_query()` wrapper 提案 (未実装)

## 問題
ad-hoc 集計スクリプト (`knowledge-base/raw/audits/codex-2026-04-30/_gen_cell_stats.py` 初版) が `demo_trades.db` の全 CLOSED トレードを `is_shadow` フィルター無しで集計し、LIVE (`is_shadow=0`) と Shadow (`is_shadow=1`) を**混在**させて Aggregate Kelly / 累計 PnL を算出した。

## 症状
- 混在値: **N=473, 累計 PnL=-661.9pip, Aggregate Kelly=-0.165**
- LIVE 単独: **N=36, 累計 PnL=+6pip (turtle_soup -170pip outlier 除外で +176pip), Aggregate Kelly=+0.385**
- 146 cell のうち LIVE は 15 cell のみ。**全トレードの 92.4% が Shadow**
- この混在値を根拠に v1 senior quant memo (`99-senior-quant-memo.md` 12:50 版) が **「LIVE 緊急停止 + 戦略撤退 + cell kill」** と提言
- v1 提言は CLAUDE.md 原則 #4「攻撃は最大の防御、データ蓄積を優先」と真逆の判断
- ユーザー指摘「なぜ毎回保守的発言ばかりか、戦略今ほとんどshadowなんじゃないの」で初めて発覚

## 原因
1. **技術的ミス**: `_gen_cell_stats.py` 初版の SQL に `is_shadow` 区分が無かった
2. **構造的バイアス**: 大きな負け数字 (-661pip) を見た瞬間に「撤退」モードに入り、お金が動いている範囲 (LIVE=is_shadow=0) を確認しないまま結論
3. **設計意図の忘却**: Shadow は「データ蓄積中の学習資産」(CLAUDE.md 原則 #4) であって PnL 評価対象ではない、という設計が監査スクリプト作成時に抜け落ちた
4. **lesson-shadow-contamination (2026-04-10) の再発**: 同じ間違いを 6 ヶ月放置し、ad-hoc 集計で再生産

## 修正
- `_gen_cell_stats.py` を is_shadow 分離対応版に書き直し、`06a-live-cell-stats.csv` (LIVE 15 cell) と `06b-strategy-aggregate.csv` (venue 列付き 45 行) を新規生成
- `06-losing-edge.md` v1→v2 全面書き直し: 「LIVE 緊急停止 + 戦略撤退」→「bb_rsi_reversion lot up + Shadow 継続 + 昇格基準厳格化」に 180 度転換
- `07-roadmap-progress.md` v1→v2 全面書き直し: Gate 1 判定 ❌ → ✅ 逆転、ガバナンス課題 Section 10 新設
- `99-senior-quant-memo.md` v2 完成: 10 sub-audit 横串統合、Sev1 を LIVE/Shadow/BT 影響別に再分類

## 提案するコードレベル safeguard (未実装)

### A. `live_only_query()` wrapper in `modules/demo_db.py`

ad-hoc 集計スクリプトが demo_trades を直接 SQL する経路を封じる。`get_all_closed(exclude_shadow=True)` / `get_stats(exclude_shadow=True)` は既存だが、監査スクリプトはこれらを使わず生 SQL を書く傾向がある (codex sub-audit が複数同様パターンで失敗)。

```python
# modules/demo_db.py に追加
def live_only_query(self, sql: str, params: tuple = ()) -> list:
    """LIVE-only クエリ強制 wrapper. SQL に is_shadow 条件が無ければ自動付与。

    監査スクリプトは demo_trades 直接 SQL ではなく必ずこの関数を経由する。
    sql に WHERE 句が無ければ ' WHERE is_shadow=0 ' を付与、
    既存 WHERE 句があれば ' AND is_shadow=0 ' を付与。
    is_shadow を明示的に指定済みの場合は二重付与を避ける。
    """
    sql_lower = sql.lower()
    if "is_shadow" in sql_lower:
        # 呼び出し側が意図的に shadow を含める場合 (sentinel 監視等)
        # 必ず is_shadow=1 か is_shadow IS NOT NULL のような明示が必要
        pass
    elif " where " in sql_lower:
        sql = sql.replace(" where ", " WHERE is_shadow=0 AND ", 1) \
                 if " where " in sql else sql + " WHERE is_shadow=0"
    else:
        # WHERE 句が無い → 末尾に追加 (ORDER BY/GROUP BY の前)
        sql = self._inject_where_clause(sql, "is_shadow=0")
    with self._safe_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
```

### B. PreToolUse hook (推奨優先度高)

監査スクリプト (`knowledge-base/raw/audits/**/*.py`, `tools/audit_*.py`, `tools/*_stats.py` 等) を `Write`/`Edit` する際に、SQL 文字列が `FROM demo_trades` を含むのに `is_shadow` を含まなければブロック。

```bash
# .claude/hooks/pretool-shadow-filter-check.sh
# Write/Edit の new_string が "FROM demo_trades" を含み "is_shadow" を含まない場合、警告を返す
```

### C. テンプレート化 (Sub 8 governance に直結)

`tools/templates/audit_script_template.py` を作成し、新規監査スクリプトの雛形に `is_shadow` カラム必須 + venue 列出力を組み込む。

## 教訓
**LIVE PnL を集計する全スクリプトは `is_shadow=0` フィルターを必須前提とせよ**。Shadow は「データ蓄積中の学習資産」(CLAUDE.md 原則 #4) であり、お金が動いている範囲 (LIVE) と統計上同列に扱ってはならない。

**Why**: 混在集計は (1) Live 経路の真のエッジを過小評価し撤退提言を誘発する (構造的保守バイアス)、(2) Shadow の負けトレードが Live 戦略の意思決定を支配する逆転を生む、(3) 「累計 PnL マイナス」を見た瞬間に判断が歪むため、SQL レベルで分離が固定されていないと毎回再発する (lesson-shadow-contamination 2026-04-10 → 本 lesson 2026-04-30 で 6 ヶ月後に再発が証明された)。

**How to apply**:
1. `demo_trades` を SELECT する SQL を書く時、`is_shadow=0` を付け忘れていないか必ず確認
2. ad-hoc 集計スクリプトは `DemoDB.get_all_closed()` / `get_stats()` を使い、生 SQL を書かない
3. 「累計 PnL マイナス」「Kelly 負」を見た時、最初の質問は「これは LIVE 単独か?」
4. 「保守的すぎる」「撤退提言ばかり」というユーザー challenge は構造的バイアスの診断信号 ([[lesson-user-challenge-as-signal]] 適用)
5. 監査スクリプトの新規作成時は是非 `live_only_query()` wrapper を経由する設計にする (実装後)

## 参照
- [[lesson-shadow-contamination]] (2026-04-10) — 同じ問題の初出。get_stats/get_all_closed には fix 済み、ad-hoc スクリプトには未浸透
- [[lesson-resend-shadow-leak]] (2026-04-20) — `_resend_pending_oanda_trades` で同種 fix
- [[lesson-sentinel-n-measurement-bug]] (2026-04-20) — 逆方向 (Sentinel/Shadow 監視で is_shadow=0 固定だった bug)
- [[lesson-user-challenge-as-signal]] (2026-04-20) — 「保守的すぎる」challenge を診断信号として扱う
- `knowledge-base/raw/audits/codex-2026-04-30/99-senior-quant-memo.md` §メタ教訓 (本 lesson の出所)
- `knowledge-base/raw/audits/codex-2026-04-30/_gen_cell_stats.py` (修正版、is_shadow 分離対応)
