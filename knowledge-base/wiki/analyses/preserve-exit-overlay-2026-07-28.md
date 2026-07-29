# preserve 型 live/shadow への exit オーバーレイ — estimand 逸脱の記録と決裁パケット (2026-07-28)

**種別**: live 10 セル初週監視 day-1 の finding (分析のみ、live 変更なし)
**発見経緯**: PR #119 (chronic UnboundLocalError 修復 + 7 セル再武装) デプロイ当日の送信経路監視

---

## 1. Day-1 監視サマリ (2026-07-28)

| 項目 | 結果 |
|---|---|
| PR #119 deploy | 04:16:09 UTC live 確定 (dep-d9k2oqm7bikc73f5c1tg, commit 3a918e83) |
| fix の main 到達 | **PR #119 マージ (04:13 UTC) が初** — fix commit b1f8196c は research ブランチ上にあり、02:23 UTC デプロイ (d20d0e50) には未含有 (`git merge-base --is-ancestor` で確認) |
| デプロイ後エラー | ゼロ ([UnboundLocalError / tick error / PRESERVE_REARM] 全て 0 件) |
| デプロイ後 preserve シグナル | **未発火** (live fill N=0 — fill 品質検証は次シグナル待ち) |
| `_PRESERVE_REARM_LIVE_PIN` | 空 frozenset で deploy 済み (pin ログが出ないのは正常 — pin は空の状態で本番到達) |
| hull / sweep code pin | false 維持 (/api/demo/live-enable-flags 実測) |
| ps watchdog (4h cron) | 04:17 UTC (deploy 1 分後) 正常完走、全席 WATCH / live N=0 |
| E1 positioning ingest | 13 ペア健全 (~500 rows/pair、鮮度 <35min、連続失敗 0) |
| sweep P-S1(a) | shadow unique N=8/10 — 07-24 から進捗なし、執行条件未達で待機継続 |
| registry (prereg_trigger_watch) | triggered=0、mof-q2 / wg G1・G2 含め全て正常 WATCHING |

### バグ時代最後の犠牲 row (デプロイ前、実損なし)
- **id=14318** (03:38 UTC, price_shock_rev_aud_jpy_h1_long×AUD_JPY): 無タグ shadow。BE_LOCK_B で +2.0p クリップ (→ §2)
- **id=14319** (03:58 UTC, 同セル): dedup_violation=1 の重複 row。03:58:56 の Render error ログ `_tick_entry error: cannot access local variable '_is_xau_inst'` がバグ経路の最後の実射証拠 (デプロイ 17 分前)
- 分析時の注意: 両 row とも `oanda_trade_id=''` の bug-era artifact。live 集計 (`oanda_trade_id != ''`) には自動的に入らない

---

## 2. Finding: preserve 型に exit オーバーレイ 3 層が適用されている

`_1H_PRESERVE_SLTP` の「SL/TP 完全保存」契約は **entry 時の初期 SL/TP のみ**。position 管理 loop の
exit オーバーレイは preserve 型にも適用される (`modules/demo_trader.py`):

| 層 | 発火条件 | 効果 | price_shock | dmb | weekend_gap |
|---|---|---|---|---|---|
| **BE_LOCK A/B (env 実験)** | group B (50%) ∧ MFE ≥ 2.0p | SL→entry+1.0p | ⚠️ **適用** (override なし = default trig 2.0p) | OFF (trig 0.0) | OFF (trig 0.0, pre-reg §2.3) |
| **ATR-BE** | favorable ≥ 0.8×ATR | SL→建値+spread | ⚠️ **適用** | ⚠️ **適用** | 免除 (`not _is_weekend_gap`) |
| **ATR-trail** | favorable ≥ 1.5×ATR | SL=price∓0.5×ATR | ⚠️ **適用** | ⚠️ **適用** | 免除 |

### 実証 (Render ログ 2026-07-28 03:48 UTC)
```
🔒 [BE_LOCK_B] price_shock_rev_aud_jpy_h1_long×AUD_JPY MFE=2.0p≥trig2.0 → SL→entry+1.0p (id=4381338f)
📤 OUT: ✅ WIN | BUY @ 114.348 → 114.368 | PnL: +2.0 pips | Reason: sl_2atr
```
- SL (2×ATR = 46.3p 下方) には一切到達していないのに close_reason=`sl_2atr` — **ラベル汚染**:
  price_shock の SL 系 close は BE/trail/BE_LOCK 発火も一律 `sl_2atr` と記録され、実 catastrophic stop と区別不能 (L3077)

### LOCK 済み設計との差
- 各 price-shock-rev カードの Exit 定義: 「**12 bars horizon close または 2×ATR catastrophic SL のみ**」
- 昇格根拠 (12.3y MASSIVE grid, BH-FDR m=3744) も 2026-07-24 exit-free 監査 (全席 p=0.0001) も **horizon-exit estimand で採点**
- [[price-shock-rev-live-activation-2026-05-18]] / [[price-shock-rev-promote-criteria-2026-05-18]] に exit オーバーレイの記載なし
- weekend_gap (2026-07-24 pre-reg) は §2.3 で BE/Trail/TP を明示禁止 = 現行基準ではこの差分は estimand 逸脱として扱う

### BE_LOCK の live 適用は設計自身の制約とも矛盾
[[mfe-be-lock-design-2026-06-03]] §5: 「shadow-only deploy は R1 不要、**BE-lock 設定の Live promotion は Rule-1 証拠必須**」。
しかし実装の BE_LOCK ブロックに `is_shadow` フィルタは無く、**live trade にも group B が適用される**
(SL persist 分岐は live=OANDA mirror / shadow=DB 直書き — 適用有無の分岐ではない)。
これまで flat book (preserve バグで live 送信死) のため顕在化しなかったが、**再武装した price_shock ×5 の live fill は
50% の確率で R1 未通過の実験レバーに晒される**。

---

## 3. 定量エビデンス

### 3.1 直近窓の price_shock closed rows (API 窓 2026-07-06〜07-28, N=7)
| close_reason | pnl_pips |
|---|---|
| sl_2atr (= BE/trail/BE_LOCK) | **+2.0 / +1.6 / +11.2** (全て正 = 実 catastrophic stop 到達ゼロ) |
| horizon | −22.9 / −20.6 / −3.9 / +5.7 |

窓 EV −3.8p/t (N=7、有意性なし)。ただし構造は v2.3/T3 診断 ([[payoff-asymmetry-diagnosis-2026-07-07]]) と同型:
**勝ちがクリップされ、負けは horizon まで走る**。

### 3.2 BE_LOCK A/B モニタ (deploy 2026-06-03 から 55 日、tools/be_lock_ab_monitor.py 実測 2026-07-28)
- N_A=2,906 / N_B=2,986 (shadow 非XAU)
- **ΔEV(B−A) = −0.034 p/t、Welch p = 0.855 → INCONCLUSIVE**
- WR: A 45.4% → B 60.5% (+15pp) / **PF: A 0.635 → B 0.505 (悪化)** — MEMORY `project_be_trail_inflates_python_bt_wr` の実 live 版
- 設計の promotion 基準 (per-strategy Welch p<0.05 ∧ ΔEV>0 ∧ Bonferroni、aggregate p<0.01) は**全て不成立**
- 30-day 判定期日 (~2026-07-03) は **25 日超過** — verdict 未実施のまま実験が走り続けている
- price_shock 単体は N_A/N_B < 10 で cell-level 判定不能

---

## 4. 含意 (初週監視への影響)

1. **G-gate/watchdog の estimand ずれ**: ps watchdog / promote evaluator の six-week EV gate は realized
   (オーバーレイ込み) 系列で判定する。昇格根拠 (horizon) と異なる量なので、signal が有効でも
   オーバーレイが EV を削れば watchdog が demote し得る = **再武装の空振りリスク**
2. **live fill 品質検証の解釈**: 初週の live EV は「signal + オーバーレイ」の合成。slippage/G1 検証 (執行品質) とは独立に、
   exit 過程の混入を分離して読む必要がある
3. **weekend_gap は清浄**: BE_LOCK trig 0.0 + ATR-BE/trail 免除 + TP/C1/SIGNAL_REVERSE 非適用 — pre-reg §2.3 完全遵守を code で確認済み。08-02 イベントに影響なし

---

## 5. 決裁パケット (user R1 事項 — 本日は live 変更なし)

| 案 | 内容 | Pros | Cons |
|---|---|---|---|
| **(a) 推奨: price_shock_rev ×5 を BE_LOCK OFF (trig 0.0) に追加** | `MFE_BE_LOCK_STRATEGY_TRIGGERS` に 5 entry_type を 0.0 で追加 (dmb/wg と同じ扱い) | LOCK 設計に一歩近づく / R1 未通過レバーの live 波及を遮断 / A/B 母集団の他戦略は不変 (実験継続可) | ATR-BE/trail は残る (完全な estimand 整合ではない) |
| (b) 完全整合: (a) + price_shock を ATR-BE/trail からも免除 (weekend_gap 型) | exit を LOCK 設計 (horizon or 2×ATR) に完全一致 | estimand 完全整合、G-gate が昇格根拠と同じ量を測る | 3.5 ヶ月の shadow 系列と過程が非連続になる (watchdog series が折れる) / live EV 過程の変更幅が大きい |
| (c) 現状維持 | 変更なし | series 連続 | R1 未通過実験が live に適用され続ける / 昇格 estimand と乖離したまま G-gate 判定 |

**推奨 = (a) を即時、(b) は 3.5 ヶ月 shadow rows (N≈30-40) の horizon-exit counterfactual (H1 bar 12 本後 close 再採点 vs realized) を
定量化してから第 2 段として判断。** T2 exit-repair FAIL の教訓どおり、exit 側の変更は counterfactual なしに広げない。
また BE_LOCK 実験自体の verdict (期日超過) を A/B 設計の基準で正式にクローズすべき — aggregate p=0.855 で
promotion 不成立が濃厚、その場合 env OFF (全 A 化) が自然な帰結。

### 決裁記録 (2026-07-28)

- **user 決裁: 案 (a) 執行承認** — 本パケット提示 (推奨 = (a) を即時) への「進めて」応答 (2026-07-28)。同時に (b) の判断材料となる
  horizon-exit counterfactual 分析タスクを user が別セッションで起動済み — 推奨プラン ((a) 即時 + (b) は定量化後) と同構成
- **執行 (rule:R1)**: `MFE_BE_LOCK_STRATEGY_TRIGGERS` に PRICE_SHOCK_REV_TIER1_TYPES 5 種を 0.0 で追加 + regression pin
  `tests/test_mfe_be_lock.py::test_price_shock_rev_disabled_returns_zero` (family パラメタライズ、追加 drift を強制検知)
- **保留 (別決裁)**: (b) ATR-BE/trail 免除 = counterfactual 結果待ち / BE_LOCK 実験の env OFF = A/B 正式 verdict 後

---

## 関連
- [[lesson-preserve-sltp-unboundlocal-2026-07-28]] — 本監視の対象バグ
- [[price-shock-reversion]] / [[price-shock-rev-live-activation-2026-05-18]] / [[price-shock-rev-promote-criteria-2026-05-18]]
- [[weekend-gap-stage2-execution-prereg-2026-07-24]] §2.3 — 免除の先例 (新基準)
- [[mfe-be-lock-design-2026-06-03]] — BE_LOCK 設計 + 検証計画 (期日超過)
- [[payoff-asymmetry-diagnosis-2026-07-07]] — 同型の構造診断 (v2.3 T3)
- MEMORY: `project_be_trail_inflates_python_bt_wr` / `project_preserve_bug_fixed_10cells_live_2026_07_28`
