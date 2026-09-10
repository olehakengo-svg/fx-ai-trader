# lesson: rolling 窓 API のキャッシュを overwrite すると歴史が不可逆に消える + 到達経路のない registry 条件は監視ではない

**発見日**: 2026-08-14 | **修正**: PR (research/edge-supply-scan-2026-08-14)、rule:R3
**発見経路**: [[external-hypothesis-scan-round3-2026-08-14]] §1 のデータ入手性 re-check (月次スキャンの機械実測パート)

## 問題 1 — overwrite キャッシュのデータ損失ハザード

`modules/yield_data.py:fetch_zn_intraday` は fetch 結果を `df.to_parquet(cache_path)` で**無条件上書き**していた。
yfinance の intraday 窓は **rolling** (1h=730d / sub-hour=60d) で、左端は毎日 1 日ずつ消える。
つまり **窓外に出たバーはキャッシュファイルにしか存在しない**。

### 症状 (実測)

| 項目 | 値 |
|---|---|
| キャッシュ | 12,760 行 / 2024-02-18 → 2026-05-15 |
| 当日 yfinance が返す窓 (period=730d) | 13,663 行 / **2024-03-21** → 2026-08-14 |
| **ファイル固有 = 再取得不能** | 2024-02-18 → 2024-03-21 (約 1 ヶ月) |
| 旧コードが `interval="1h"` で選ぶ period | **`60d`** (1,162 行) |

→ **誰かが `fetch_zn_intraday(interval="1h")` を一度呼ぶだけで 12,760 行が 1,162 行に潰れる。**
実害が出る前に発見できたのは、月次スキャンが「入手性の再確認」を機械実測でやる規約になっていたため。

### 原因

overwrite 実装は「**取得できる期間 = 保有できる期間**」を暗黙に仮定している。
この仮定は静的アーカイブ API では真だが、**rolling 窓 API では常に偽**。

### 修正

- `merge_bar_cache()` を新設し union-merge 化 (重複タイムスタンプは fresh 採用 = ベンダー訂正を反映、**行数は単調非減少**)。
- 1h の period マッピングを `60d` → `730d` (rolling 上限) へ。
- 不変条件を `tests/test_yield_data_cache_merge.py` (7 tests) で pin — 特に「fetch 窓より古いバーが保存される」が本丸。
- 結果: 12,760 → **14,175 行 / 2024-02-18 → 2026-08-14** (左端保持のまま右端 3 ヶ月回復)。

## 問題 2 — 到達経路のない registry 条件は「監視」ではなく飾り

registry `ws3-round4-eur-divergence-conditional` の発火条件は
**「FX + rates (ZN=F 1h) cache が 2026-11-15+ まで延伸したら発火」**。

しかし **キャッシュを伸ばす定期ジョブは存在しなかった** (最終更新 mtime 2026-07-24、右端 2026-05-15 で停止)。
条件が構造的に到達不能なので、このトリガは**永久に "watching" と表示され続ける**。
毎日 watch が回っていたので「監視されている」ように見えていたが、実体はゼロだった。

### 修正

`.github/workflows/zn-cache-refresh.yml` (週次 UTC 月 06:40、cc-g0-rt.yml と同一の PAT bypass 経路) を新設し、伸長経路を実在させた。

## 教訓

1. **rolling 窓のベンダー API を叩くキャッシュは union-merge が既定。** overwrite は「取得可能期間 = 保有可能期間」という偽の仮定を含む。凍結の単位はファイル実体 + sha256 (MEMORY `project_massive_vendor_gap_backfill_2026_07_29` の一般化)。
2. **条件付き registry トリガを登録したら、その条件に到達する経路が実在するかを同時に検査する。** 「条件を書く」と「条件が起こりうる」は別。到達経路のない条件は監視ではない。
   → **新規 pre-reg LOCK 時のチェックリストに「発火条件の到達経路 (どのジョブが状態を進めるか) を message に明記する」を追加**。
3. **`watching` 表示は健全性の証拠にならない。** 何も起きていないのか、起きえないのかを表示は区別しない。定期的に「この条件は物理的に到達しうるか」を棚卸しする (月次スキャン §1 の入手性 re-check がその場)。

## 関連

- [[external-hypothesis-scan-round3-2026-08-14]] §1.1 (発見の文脈と実測表)
- [[edge-development-pipeline-2026-07-18]] §4 月次 cadence (入手性 re-check がこの規約の産物)
- MEMORY `project_massive_vendor_gap_backfill_2026_07_29` (歴史バーの drift、凍結はファイル実体で)
- [[lesson-tv-bt-cache-stale-port-bug-2026-06-03]] (キャッシュ由来の別型の罠)
