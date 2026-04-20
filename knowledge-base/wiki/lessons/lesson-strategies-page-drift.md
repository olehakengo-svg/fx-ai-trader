# Strategies Page Drift — wiki/strategies/*.md と tier-master の乖離

**発見日**: 2026-04-20 (Priority 4 KB 整合修正)
**修正**: `tools/strategies_drift_check.py` + 13 ページの Status 書き換え
**Related lessons**: [[lesson-kb-drift-on-context-limit]]

## 何が起きたか

`tools/tier_integrity_check.py --write` で生成される `wiki/tier-master.md` / `tier-master.json`
（自動生成 = Source of Truth）と、手書きの `wiki/strategies/*.md` の Status/Stage 見出しが
乖離していた。

顕著な例:

| ページ | 古い Status (md) | 実態 (tier-master) |
|---|---|---|
| `bb-rsi-reversion.md` | "Tier 1 (PAIR_PROMOTED x USD_JPY)" | SCALP_SENTINEL + PAIR_DEMOTED x 全 4 ペア (v8.9 で降格) |
| `orb-trap.md` | "Tier 1 (PAIR_PROMOTED x USD_JPY, EUR_USD, GBP_USD)" | FORCE_DEMOTED (v9.1 で 365d BT 負EV 確定) |
| `trendline-sweep.md` | "ELITE_LIVE; FORCE_DEMOTED globally but PAIR_PROMOTED on EUR/GBP" | ELITE_LIVE のみ (v9.0 で FD/PP 整理済み) |
| `bb-squeeze-breakout.md` | "FORCE_DEMOTED / PAIR_PROMOTED on USD_JPY, EUR_USD" | FORCE_DEMOTED (v9.1 死コード削除) |
| `engulfing-bb.md` | "EUR_USD PAIR_PROMOTED" | FORCE_DEMOTED (v9.1 死コード削除) |
| `sr-channel-reversal.md` | "EUR_USD PAIR_PROMOTED" | FORCE_DEMOTED |
| `ema-pullback.md` | "USD_JPY PAIR_PROMOTED" | FORCE_DEMOTED |
| `london-fix-reversal.md` | "GBP_USD PAIR_PROMOTED" | Phase0 Shadow Gate (v9.1 で PP 削除) |
| `vol-momentum-scalp.md` | "SHADOW" | PAIR_PROMOTED x EUR_JPY |
| `three-bar-reversal.md` | "UNIVERSAL_SENTINEL" | Phase0 Shadow Gate |
| `doji-breakout.md` | Stage のみ (Status 不明) | UNIVERSAL_SENTINEL + PAIR_PROMOTED (GBP/USDJPY) |
| `stoch-trend-pullback.md` | "Sentinel" | FORCE_DEMOTED (v8.9 昇格剥奪) |
| `vol-surge-detector.md` | "Sentinel" | SCALP_SENTINEL + PAIR_DEMOTED x EUR_JPY/USD_JPY |

## 根本原因

1. **tier-master.md は自動生成、strategies/*.md は手書き** — 昇格/降格コミットで後者が更新
   されないと恒久的にズレる。
2. **lesson-kb-drift-on-context-limit** と同じ症状: コード変更に KB 更新が同梱されない。
3. `tools/tier_integrity_check.py` は demo_trader.py 内の Python リスト整合のみ検証しており、
   `wiki/strategies/*.md` の内容は走査していなかった。
4. `bb_rsi_reversion` は v6.3→v8.8 まで「The only strategy with PF > 1」のヒーロー戦略だった
   ため、v8.9 の降格後も "Tier 1" 記述がレビューで見過ごされやすかった。

## 影響

- 次セッションで戦略状態を確認するときに `wiki/strategies/{name}.md` の冒頭だけ読むと、
  実装と矛盾する判断材料に基づいて分析してしまう。
- 「bb_rsi_reversion は Tier 1 だから継続」のような感情的ロックインが発生する。
- 外部 reviewer に KB を共有したとき、自動生成 tier-master と手書き strategies/ どちらを
  信じるか不明確になる。

## 対策

### ルール 4 (追加): Tier 変更時に strategies/*.md の Status 行も必ず更新

CLAUDE.md KB 運用ルールに以下を追加する運用:
- Tier 変更コミットには `wiki/strategies/{affected}.md` の Status 書き換えを**同梱**
- 旧 Status は `**履歴**:` / `Previously ...` で明示的に残す（削除禁止）
- `python3 tools/strategies_drift_check.py` が exit 0 であることをコミット前に確認

### 仕組み化: `tools/strategies_drift_check.py`

- `wiki/tier-master.json` (自動生成 snapshot) を truth source として読み込む
- 各 `wiki/strategies/*.md` の冒頭 40 行から `## Status:` / `- **Status**:` を抽出
- 以下の矛盾で exit 1:
  - ELITE_LIVE / FORCE_DEMOTED / SCALP_SENTINEL / UNIVERSAL_SENTINEL の誤主張
  - PAIR_PROMOTED の scope 内で宣言されたペアが truth に存在しない
  - strategy が truth で FORCE_DEMOTED / ELITE_LIVE だが header ラベル欠落
  - PAIR_PROMOTED 主張ペアが実は PAIR_DEMOTED
- 「not in ELITE_LIVE...」のような否定コンテキストは `_NEG_RE` でスキップ
- 「履歴:」「Previously ...」等は `_HISTORY_MARKERS` でスキップ（現行状態と分離）

### 独立ツールとした理由

`tier_integrity_check.py` はコード (demo_trader.py) の内部整合チェックが責務で、KB 文書の
文面検証とはスコープが異なる。結合すると `tier-master.json` 生成 → md 検証の循環依存が
読みにくくなるため、独立ツールとして `strategies_drift_check.py` を分離した。pre-commit
/ CI では両方を順に呼べばよい:

```bash
python3 tools/tier_integrity_check.py --write  # 1. truth を更新
python3 tools/strategies_drift_check.py        # 2. 手書きKBを検証
```

### テスト

`tests/test_strategies_drift_check.py` に 11 ケース:
- クリーンページ通過
- `bb_rsi_reversion` の PP x USD_JPY 回帰検出
- ELITE / FORCE_DEMOTED の誤主張検出
- 否定コンテキストのスキップ
- scope を跨いだペア抽出 (PAIR_PROMOTED 後、PAIR_DEMOTED 前まで)
- 真に FD の戦略の header 欠落検出
- Status 欠落検出
- 実 KB に対する end-to-end 回帰テスト

## Related

- [[lesson-kb-drift-on-context-limit]] — 同じ病理（コード/KB 別コミット）の旧ケース
- [[tier-master]] — Source of Truth (自動生成)
- [[changelog]] — v9.x エントリにドリフト修正を記録
