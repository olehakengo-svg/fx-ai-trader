# BT scalp M15/M5 precompute cache — `id(df)` key の偽ヒットを内容指紋で閉じる (2026-10-16、rule:R3)

**発見日**: 2026-10-13 (PR #326 CI) → 2026-10-15 registry 起票 (`bt-scalp-mtf-cache-key-id-reuse-r3`、期日 10-29) → **2026-10-16 修復 (13 日前倒し)** | **rule**: R3 (構造バグ、戦略ロジック・閾値・母集団を変えない) | **範囲**: BT 専用 (`app._compute_bt_htf_bias(mode="scalp")` → `_build_bt_scalp_mtf_cache`)。live 経路は本 cache を使わない | 前段: [[lesson-wallclock-flaky-tests-2026-10-15]] (4 系統目)

## 1. 欠陥 (code derivation)

旧 key:

```python
def _bt_scalp_mtf_cache_key(df):
    return (id(df), len(df), df.index[0], df.index[-1])
```

`id(df)` は CPython ではオブジェクトのアドレスで、**GC 後に別オブジェクトへ再割当される**。`len` と index 両端が一致する別 df (別ペア・別内容) が旧 df の死後に同じ id を得ると、**内容が違っても cache hit** し、M15 (adx / ema / hurst / range_20) と M5 (close / swing / rsi divergence) の特徴量が前の df のものになる。再現: pytest で先行 test の同形 df が GC された後、`test_compute_bt_htf_bias_reuses_cached_scalp_mtf_precompute` の build が 0 回 (`assert 0 == 1`、PR #326 CI 2026-10-13 / main CI ×3)。

id 再利用は決定論的に起きうる (本セッションの最小再現: `a = DataFrame(...); ia = id(a); del a; b = DataFrame(...); id(b) == ia` → True)。

## 2. 経路調査 (registry の問い「同一プロセス内で同 index 範囲の df を作り直す経路があるか」)

| 経路 | 同一プロセスで複数 df | 同 len・同 index 両端になりうるか | cache clear | 判定 |
|---|---|---|---|---|
| `tools/bt_target_runner.py` (strategy × pair ループ → `app.run_scalp_backtest`) | **はい** (pair ごとに `fetch_ohlcv → add_indicators → dropna` で新オブジェクト) | **はい** — MASSIVE parquet の同一期間は主要 pair で bar 数・両端が一致しうる | `_dt_bt_cache` / `_scalp_bt_cache` のみ、**本 cache は clear していない** | 🔴 **cross-pair 汚染の実経路** |
| `app.py` `/api/backtest` chunked async (`_df_override=df_chunk`、同 symbol) | はい | chunk ごとに index 範囲が異なる → key 不一致 | — | 影響なし (ただし同プロセス長命 = 次の同窓リクエストで再取得 df が id 再利用の候補) |
| `tools/ma_trend_perfect_shadow_bt.py` | はい | はい | **`app._bt_scalp_mtf_precompute_cache.clear()` を明示** (回避策が既に書かれていた = 欠陥を知っていた痕跡) | 回避済み |
| `tools/sr_channel_reversal_shadow_bt.py` / `confluence_scalp_shadow_bt.py` | はい | はい | `data_mod._data_cache.clear()` のみ | 🔴 同上 |
| `modules/data.fetch_ohlcv` | — | — | cache hit は `.copy()` を返す → **毎回新オブジェクト** = id 再利用の母体 | — |

結論: **(b) 修正 PR**。「記録のみで resolve」の条件 (経路なし) は不成立。

## 3. 設計

key を **内容のみ**から導出する:

```
key = ("scalp_mtf_fp_v3", len(df), index[0], index[-1],
       blake2b_16(index.asi8 ‖ Open ‖ High ‖ Low ‖ Close ‖ Volume  — 全て順序付き bytes))
```

- 同一内容の別オブジェクト (deep copy、同じ parquet の再読込) → 同 key = 同じ特徴量を共有 (正しい)
- 同形で内容が異なる (別 pair / ベンダー訂正 1 bar / **内部 2 bar の入れ替え**) → digest が変わる → 別 key → 再計算
- `id(df)` は key に**含めない**

初版 (PR #333 1 巡目) は Close/High/Low の `nansum` 丸めを指紋にしていたが、Codex P2 4290930321「合計は順序非感応 — 内部 2 行を入れ替えると列合計は不変なのに `resample_df` が消費する時系列特徴量 (EMA/ATR/RSI/divergence) は変わる」で **順序付き digest に置換** (pin 3b)。
コスト: blake2b-128 over index int64 + OHLCV float64 bytes は O(n)。525,000 行 (365 日 1m 相当) で **11.9 ms/回** (実測、nansum ×3 は 1.55 ms だったが順序非感応で不採用、hash_pandas_object 7.4 ms も row hash の sum で同欠陥)。`_compute_bt_htf_bias` は scalp で 60 bar ごとに呼ばれるので 365d BT で ~8,700 回 → 毎回計算すると ~100 s。これを避けるため **オブジェクト単位の memo** `_bt_scalp_mtf_fp_memo: id(df) → (weakref.ref(df), key)` を置き、`memo_ref() is df` のときだけ再利用 (O(1))。weakref が死んでいる / 別オブジェクトを指す = id が再利用された、と判定して再計算する。memo 上限 16、満杯時は死んだ ref を刈る。

**保証しないこと**: 同一オブジェクトの**その場 (in-place) 変更**は memo 越しに旧 key を返す。BT 経路は source df を `add_indicators()/dropna()` で作り直すため該当経路なし (grep 済み)。将来 in-place 訂正を書く場合は `app._bt_scalp_mtf_fp_memo.clear()` を呼ぶ。

## 4. pin (`tests/test_bt_scalp_mtf_cache_key_fingerprint.py`、10 本)

1. key に `id(df)` が含まれない 2. 同内容別オブジェクト → 同 key 3. 同形別 Close → 別 key 4. 1 bar 訂正 → 別 key 4b. **内部 2 bar 入れ替え (列合計不変) → 別 key** 5. 指紋は live オブジェクトにつき 1 回 6. **id 再利用の決定論的再現** (memo に「別オブジェクトの weakref + 旧 key」を植える) → 旧 key を返さない 7. end-to-end: 同形 2 df で build 2 回、deep copy は 3 回目を起こさない 8. OHLC 列欠落で例外なし (index だけでも内容感応) 9. memo の上限と死 ref 刈り。既存 `tests/test_bt_htf_m15_m5_inject.py` の 2 本は不変 (cache.clear() は eviction 上限 4 との独立性のために残す)。

## 5. BT 不要の根拠 (R3)

戦略ロジック・閾値・母集団を変えない。変わるのは「別内容の df に対して正しい特徴量が計算される」ことだけで、既存 BT 結果のうち**単一 df を単一プロセスで回したもの**は同一 (key が変わっても同一 df 内では hit/miss パターンが同じ)。複数 pair を同一プロセスで回した過去の `bt_target_runner` 結果は理論上汚染の可能性があるが、(i) 発生条件 (bar 数・両端一致 ∧ id 再利用) の充足率は不明、(ii) 当該ツールの出力は raw/bt-results の Rule 1 根拠として引用されていない (2026-10-16 grep: `bt_target_runner` 由来の BT 結果を根拠に昇格した決裁なし) ため、再走は行わない (record-only)。

## 6. 関連
- registry `bt-scalp-mtf-cache-key-id-reuse-r3` → resolved 2026-10-16
- [[lesson-wallclock-flaky-tests-2026-10-15]] / [[2026-10-16-session]] / MEMORY `project_autopilot_2026_10_16_rescue_and_cache_key_fingerprint`
