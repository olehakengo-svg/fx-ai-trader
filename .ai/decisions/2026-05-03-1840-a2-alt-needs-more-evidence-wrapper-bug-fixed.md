---
date: 2026-05-03T18:40:00+0900
verdict: NEEDS_MORE_EVIDENCE
rule: R1
roadmap_gate: Gate 1 (Scalp 枝 N-acceleration)
task: 20260503-1700-a2-alt-simple-structure-scalp-pre-reg
codex_job: task-mopkic7h-qqa4x6
codex_session: 019ded2a-adbe-7c11-b0a7-c97dc5f6c5a2
run_dir: .ai/runs/20260503-182807-20260503-1700-a2-alt-simple-structure-scalp-pre-reg
---

# 判定: NEEDS_MORE_EVIDENCE (verdict pending) / ACCEPT (Codex deliverable)

## Codex 担当部分 (ACCEPT)

| 観点 | 結果 |
|---|---|
| 仕様準拠 | LOCKED constants、4候補メタ、Bonferroni K=4、threshold ロジック、verdict 関数、aggregate 機能、stale JSON 拒否すべて実装。`--dry-run` 動作確認 (K=4, alpha/K=0.0125, BEV_WR USD_JPY=34.4 / EUR_USD=39.7)。|
| ユニットテスト | `tests/test_scalp_alt_pre_reg_bt.py` 13/13 pass。|
| R3 ゲート連携 | aggregate 実行で stale `scalp-alt-bb_squeeze-2026-05-03.json` を fingerprint mismatch で exit=2 拒否を再現。R3 ゲートが効いている。|
| Scope guard | `app.py` / `modules/` / `strategies/` / `wiki/decisions/` / `wiki/index.md` 編集 0件。|
| 仕様遵守 | タスク仕様の line 70 / 116 / 158「parent Claude が foreground で BT を実行」を遵守し、Codex はサンドボックス内で長時間 BT を試みなかった。|

## A2-alt verdict 部分 (NEEDS_MORE_EVIDENCE)

4 候補 BT データが未取得のため、verdict (Promote / Shadow / Reject / Insufficient) は出せない。Codex は意図通り wrapper を整備して停止した。

## Parent Claude 側で発見した wrapper bug (R3 即時修正)

BT を foreground で実行した際、4 候補すべてが `KeyError: 'Close'` で停止することが判明:

```
File "modules/indicators.py", line 21, in add_indicators
    c, h, l = df["Close"], df["High"], df["Low"]
KeyError: 'Close'
```

### 根本原因

`tools/scalp_alt_pre_reg_bt.py:434` `load_local_bt_frame` が `_load_local_cache` (modules/bt_vec_harness.py) から DataFrame を取得すると、parquet キャッシュ由来で **lowercase columns** (`open`, `high`, `low`, `close`, `volume`) が返る。一方 `app.add_indicators` (modules/indicators.py:21) は **capitalized** `Close`, `High`, `Low` を要求する。両者の case mismatch で BT 全候補が常に空データで verdict Insufficient になっていた (R3 の `/tmp/_single_candidate.json` の `bars_fetched: None / window_start_utc: None` がエビデンス)。

### 修正

`load_local_bt_frame` 内で `add_indicators` 呼び出し直前に column rename を 1 行追加:

```python
df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
df = app.add_indicators(df.copy()).dropna()
```

### Fingerprint 影響

R3 fingerprint は **PnL extraction AST + LOCKED constants + CANDIDATES のみ**をハッシュする設計。今回の修正は infra (data loading) であり verdict logic に無影響なので、fingerprint は不変 (`b6d7386b5c48789871894a76b07f61c3a741fba176353e90e9250014a9533e02`)。R3 ゲート設計の正当性が実例で確認できた。

## 残作業 (parent Claude foreground)

1. 4 候補 BT を current wrapper (column-fix 後) で再生成
2. aggregate 実行で 4 verdict + summary table を生成
3. verdict が Promote/Shadow を含むか、全 Reject か確認

## 教訓化候補

- **Codex のサンドボックス内 unit test だけでは「wrapper が実データに対して走るか」を検証できない**。実 parquet データロードの層は parent Claude foreground 実行時のみ初めて壊れることが判明する。Codex タスク設計時、wrapper には **smoke E2E テスト** (実データ 1000 行で `--candidate` を1分以内で完走) を必須化すべき。
- **R3 fingerprint 設計の正当性が実例で確認**: PnL/verdict logic に無影響な infra fix では fingerprint が不変なので、aggregate gate を誤動作させずに緊急 hotfix が打てる。逆に、PnL helper を変更すれば fingerprint が変化し、必ず aggregate を refuse させる。期待通りの非対称性。
