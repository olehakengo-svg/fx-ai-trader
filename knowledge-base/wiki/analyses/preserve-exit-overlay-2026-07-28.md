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
  → **両方とも同日中に解消**: (b) は §6 定量化完了後の user「進めて」決裁で §7 執行、A/B verdict は [[mfe-be-lock-design-2026-06-03]] §8 で FAIL 確定
- (注) 同一 user 決裁を並行セッションが Track C **D-c-1** として main へ先着実装 (5 エントリ 0.0 は同値)。本セッション分の残存 delta = regression pin + 本決裁記録

→ **(b) の counterfactual 定量化は完了 — §6** (2026-07-28、実測 N=14 ≪ 想定 30-40)。

---

## 6. Option (b) 判断材料: 3.5 ヶ月 shadow rows の horizon-exit counterfactual (2026-07-28)

§5 推奨の第 2 段定量化。**分析のみ、live 変更なし (user R1 決裁待ち)。**

### 6.1 母集団とデータ

- **rows**: 本番 API `/api/demo/trades` closed、2026-04-10〜07-28、`entry_type` = price_shock_rev ×5、`dedup_violation != 1` → **N=14** (完全性は月別分割クエリで照合済み — §5 の想定 N≈30-40 は過大、family の実発火はこの頻度)
- cell 分布: **eur_gbp 8 / aud_jpy 5 / nzd_jpy 1 / eur_aud 0 / usd_cad 0**。全 row `is_shadow=1`・`oanda_trade_id=''` (preserve バグで live 送信死のため全席 shadow 系列)
- **eur_aud / usd_cad は 05-18 活性化以来 shadow row ゼロ** — 席は在るが供給が無い (seat-supply 観測、§6.6-5)
- id=14318 (07-28 03:38 entry) は horizon 未完了 (設計 exit close = 本日 16:00 UTC) のため paired から除外 → **paired N=13**。realized は +2.0p (BE_LOCK clip) で確定済み
- 価格 = **MASSIVE H1** (`data/cache/massive/*_1h_12y_audit.parquet`、07-24 exit-free 監査と同一 canonical + AUD_JPY のみ 07-28 08:00 UTC まで API top-up、重複 200 bars で max |ΔClose| 0.026 を確認)。OANDA mid 検算は不使用 (MEMORY `project_weekend_gap_fade_live_2026_07_25` 準拠)

### 6.2 採点規約 (再現手順) と副次 finding: live は forming bar 発火

**副次 finding**: entry 時刻が全て bar 中間 (:14〜:59) に散在し、entry 時点の partial log-return が rolling 1%-tile と sub-pip で一致
(例 id=14108: −0.00146 vs 閾値 −0.00147、id=10481: −0.00121 vs −0.00124)。つまり **live は「直前に閉じた bar」ではなく
「形成中 bar の partial return が閾値を初回クロスした瞬間」に entry している** (engine は forming bar を iloc[-1] として評価)。
BT (完成 bar close 判定 → 翌 bar open entry) より構造的に早い entry — これは entry 側の live/BT 乖離であり本 §の exit 比較とは独立。

counterfactual 規約 (grid BT `tools/price_shock_reversion_bt.py` と同アンカー):
- signal bar i = entry_time を含む H1 bar (forming bar)。**design exit = Close[i+h]** (bar-index 演算、週末スキップ。h: aud_jpy/eur_aud/nzd_jpy=12、eur_gbp/usd_cad=3 — strategies/hourly literal 確認済み)
- catastrophic SL = entry − 2×vol20[i]×Close[i]×√20 (base 実装式)、判定 window = bars i+1..i+h の Low
- **SL 再構成の較正**: 初期 SL が保存されている未変異 8 rows の stored SL と照合 — 本モデル (vol20[i] full-bar) median |err| = **2.5p** (AUD_JPY rows は ±2.6p 以内)、対抗モデル (vol20[i−1]) は 6.5p で AUD_JPY に −16〜−19p の系統誤差 → 前者を primary に採用
- entry 価格は両腕とも row の実 entry を共有 → **paired 差分は exit 過程のみを分離**
- bootstrap: paired ΔEV の mean を percentile 法 B=10,000、seed=20260728

### 6.3 結果: per-cell + pooled (paired N=13)

| cell | N | realized EV / WR / PF | counterfactual EV / WR / PF | paired ΔEV (cf−realized) |
|---|---|---|---|---|
| aud_jpy (h=12) | 4 | −3.07 / 75.0% / 0.46 | **+0.97 / 75.0% / 1.19** | **+4.05 p/t** [CI −0.72, +9.37] |
| eur_gbp (h=3) | 8 | −2.59 / 37.5% / 0.48 | −2.05 / 37.5% / 0.61 | +0.54 p/t [CI −1.15, +2.79] |
| nzd_jpy (h=12) | 1 | +54.0 / 100% / inf | +53.4 / 100% / inf | −0.60 p/t |
| **POOLED** | **13** | **+1.62 / 53.8% / 1.34** | **+3.15 / 53.8% / 1.65** | **+1.53 p/t [CI −0.49, +3.90]** |

- pooled cf EV +3.15 p/t [CI −5.71, +13.65] / realized EV +1.62 (full N=14 realized は EV +1.64、total +23.0p)
- 正 EV は単一 outlier (nzd_jpy +54p) 依存: **ex-NZD では realized −2.75 p/t vs cf −1.04 p/t (N=12)** — どちらの exit でも窓は負、ただし Δ の向き (+1.71 p/t) は保存
- **counterfactual の catastrophic SL 発火 = 0/13、realized の実 2×ATR stop 到達 = 0/14** — 3.5 ヶ月間、オーバーレイの保険機能は一度も効かず、クリップコストだけが発生した

### 6.4 クリップ row の分解 — §3.1 構造の直接実証

realized `sl_2atr` ラベル 5 rows (全て正の小 pnl = BE/trail クリップ、実 stop ゼロ) の counterfactual は**全て正**:

| id | cell | realized (clip) | cf (design) | foregone | 備考 |
|---|---|---|---|---|---|
| 10357 | aud_jpy | +2.1 | +7.0 | +4.9 | **exit_time = entry_time (同一秒) の即時クリップ**。クリップ後 −53.1p まで逆行 → +7.0p へ回復 (SL 距離 68.5p で非発火、AUD 較正誤差 ±2.6p に対しマージン 15.4p) |
| 10481 | eur_gbp | +2.0 | +9.6 | +7.6 | |
| 13247 | eur_gbp | +11.2 | +9.9 | −1.3 | trail が design を上回った唯一の row |
| 14108 | aud_jpy | +1.6 | +13.4 | +11.8 | 週末跨ぎ horizon (bar-index で正しく採点) |
| 14318 | aud_jpy | +2.0 | (未確定) | — | horizon 完了前のため除外 |

- クリップ 4 rows の foregone 合計 **+23.0p** = pooled Δtotal +19.9p のほぼ全て。**「勝ちがクリップされ、負けは horizon まで走る」(§3.1 / T3 診断) の row-level 直接実証**
- **§2 の 3 層に加え第 4 の逸脱経路を確認**: id=10730 は `SIGNAL_REVERSE` close (−10.1 vs cf −9.0)。code 上 SIGNAL_REVERSE 免除は weekend_gap のみで **price_shock は非免除** (`demo_trader.py` `_check_signal_reverse`) — option (b) を採る場合は免除セットに含める必要がある

### 6.5 感度分析

| variant | pooled ΔEV | 95% CI | 備考 |
|---|---|---|---|
| **primary** (exit Close[i+h]、SL vol20[i]) | **+1.53** | [−0.49, +3.90] | grid 規約 + SL 較正 best |
| S1: exit Close[i+h−1] (1 bar 早い close) | −0.67 | [−4.78, +3.64] | exit-bar 規約の ±1 bar 感度 |
| S2: SL vol20[i−1] (直前閉 bar) | −1.94 | [−9.33, +3.01] | 較正劣後モデル。id=10357 が SL 発火 (−38.2p) に反転し単独で符号を支配 |

**結論は規約に敏感 (N=13 の限界)**: primary では design 優位 (+1.53 p/t) だが、exit bar ±1 や SL モデルの選択で符号が動く。
確度をもって言えるのは (i) **クリップが勝ち trade を平均 +5.8p/row 削っている** (4 rows 一貫、13247 のみ逆)、
(ii) **保険 (catastrophic SL) の実効発火はどちらの世界でもゼロ**、(iii) **pooled ΔEV は CI が 0 を跨ぎ統計的に未確定** — の 3 点。

### 6.6 option (b) への含意 (判断材料 — 決裁は user R1)

1. **estimand 逸脱の実害規模**: 3.5 ヶ月で ~+20p foregone (pooled +1.53 p/t、n.s.)。「大惨事」ではないが方向は §3.1 / [[payoff-asymmetry-diagnosis-2026-07-07]] と一貫し、BE_LOCK A/B の PF 悪化 (§3.2: B 0.505 < A 0.635) とも整合
2. **watchdog / G-gate への影響の定量**: realized 系列は 5/14 rows (36%) がラベル汚染 (`sl_2atr`=クリップ) で、EV は design 比 −1.5 p/t 前後ずれる。六週 EV gate の判定が signal 有効性と別の量で動くリスク (§4-1) は現実の大きさとしてはこの程度
3. **(b) 採用時の追加要件**: ATR-BE/trail 免除だけでは不足 — **SIGNAL_REVERSE 免除も必要** (§6.4)。免除セットは weekend_gap 型 (BE_LOCK trig 0.0 + ATR-BE/trail 免除 + SIGNAL_REVERSE 免除) をそのまま流用するのが code 上最小
4. **(b) の Cons (系列断絶) の再評価**: 断絶する series の中身は「36% ラベル汚染 + クリップで勝ち側が削られた系列」であり、連続性の価値自体が低い。counterfactual 再採点ハーネス (`tools/price_shock_exit_counterfactual.py`、規約は §6.2) で過去系列を design 尺度に遡及換算できるため、watchdog series は折れても再構成可能
5. **別件 (要 registry)**: eur_aud / usd_cad の 2 席が 3.5 ヶ月無発火。Q5 vol 分位フィルタ × 1%-tile の同時成立が現実の発火率でどれだけ稀か、席の期待発火率を再見積もりすべき (本 § の範囲外、live 変更なし)

### 6.7 追補 (2026-07-29): id=14318 の horizon 完了 → paired N=14 確定値

§6.3〜6.5 は決裁時 (07-28、id=14318 未確定) の記録としてそのまま保持。07-28 16:00 UTC に horizon 完了し確定:

- **id=14318: cf −7.6p (horizon、SL 非発火) vs realized +2.0p (BE_LOCK clip)** — クリップが design を明確に上回った初の row (13247 の −1.3p を超える)。クリップ 5 rows の foregone は +23.0p → **正味 +13.4p** に更新
- pooled paired N=14 (primary): realized EV +1.64 (WR 57.1% / PF 1.37) vs cf EV +2.38 (WR 50.0% / PF 1.47)、**ΔEV +0.74 p/t [95% CI −1.76, +3.36]** — 方向は維持、有意性なしの度合いは強まる
- 感度 (N=14): S1 −2.11 [−6.91, +2.77] / S2 −2.49 [−9.39, +2.38]
- §6.5 の結論 3 点は不変 (実 catastrophic SL 発火は 14/14 とも 0 のまま)。**§7 執行の根拠は ΔEV の符号ではなく estimand 整合性** (昇格根拠と同じ量を測る) であり、本追補で覆らない — ただし「オーバーレイ除去で EV が改善する」という副次期待は N=14 時点でほぼニュートラルに減衰したことを明記する

---

## 7. 執行記録 (2026-07-28 — rule:R1)

**決裁根拠**: user ミッション委任 (2026-07-08「運用判断は Claude に全面委任」) + 本パケット (§5 + §6 判断材料) 提示後の user「進めて」(2026-07-28)。
§5 推奨ライン (「(a) を即時、(b) は counterfactual 定量化後に第 2 段として判断」) を §6 完了を受けて執行。

| # | 内容 | 実装 |
|---|---|---|
| (a) | price_shock_rev ×5 を BE_LOCK OFF | `MFE_BE_LOCK_STRATEGY_TRIGGERS` に 5 entry_type を 0.0 追加 (code pin — env と独立に恒久化、「KV disable は pin にならない」教訓) |
| (b) | ATR-BE / SMC-BE / ATR-trail 免除 | `_sltp_loop` の免除条件に `_is_ps_rev_sltp` 追加 (weekend_gap 型) |
| (b)+ | SIGNAL_REVERSE 免除 (§6.4 の第 4 経路) | `_check_signal_reverse` に PRICE_SHOCK_REV_TIER1_TYPES 早期 return |
| 併決 | BE_LOCK A/B 実験の正式クローズ | verdict FAIL ([[mfe-be-lock-design-2026-06-03]] §8)。執行 = **code close** (`_be_lock_enable = False` + pin テスト) — env 経路より強い不可逆化 (2026-07-29) |

**変更の判断根拠 (BT 検証要件への回答)**: 本変更は「新エッジ」ではなく **BT 検証済み estimand への復帰**。
- 昇格根拠 BT (horizon-exit で採点、12.3y MASSIVE, BH-FDR m=3744): EUR_GBP N=239 WR=72.8% / EUR_AUD N=262 WR=67.6% / USD_CAD N=247 WR=66.4% / NZD_JPY N=303 WR=64.0% / AUD_JPY N=426 WR=63.8%
- 2026-07-24 exit-free 監査: 全席 p=0.0001 (同 estimand)
- §6 counterfactual: 免除で失うもの (クリップ保険) の実発火は 3.5 ヶ月ゼロ、得るもの (foregone 解消) +23p/4 rows。paired ΔEV +1.53 p/t [CI −0.49, +3.90]
- リスク面: 全席 Sentinel 1000u 固定 + ps watchdog (R2 自動 demotion gate) 併設 — 最小リスク例外にも該当
- 逆に**オーバーレイ側**は R1 未通過 (BE_LOCK live 適用は設計自身が R1 必須と規定) + A/B 55d INCONCLUSIVE

**残存する既知の逸脱 (スコープ外として維持)**:
- `WEEKEND_CLOSE` (金曜 21:45 UTC 全ポジ強制クローズ) は price_shock にも適用され続ける。設計 BT は週末跨ぎ保有だが、週末ギャップリスクはポートフォリオ全体のリスクポリシー事項のため本執行に含めない (金曜午後 entry の horizon≤12h のみ影響、§6 の 14108 が該当例)
- テスト pin: `tests/test_mfe_be_lock.py::TestPriceShockExitEstimandPins` + trigger 0.0 pin、`test_weekend_gap_fade.py` の共有条件 pin 更新

**効果の観測**: 以後の realized 系列 = 設計 estimand (close_reason は horizon / 実 sl_2atr のみ) → ps watchdog / G-gate は昇格根拠と同じ量を測る。§6.6-4 のとおり過去系列は `tools/price_shock_exit_counterfactual.py` で遡及換算可能。

---

## 関連
- [[lesson-preserve-sltp-unboundlocal-2026-07-28]] — 本監視の対象バグ
- [[price-shock-reversion]] / [[price-shock-rev-live-activation-2026-05-18]] / [[price-shock-rev-promote-criteria-2026-05-18]]
- [[weekend-gap-stage2-execution-prereg-2026-07-24]] §2.3 — 免除の先例 (新基準)
- [[mfe-be-lock-design-2026-06-03]] — BE_LOCK 設計 + 検証計画 (期日超過)
- [[payoff-asymmetry-diagnosis-2026-07-07]] — 同型の構造診断 (v2.3 T3)
- MEMORY: `project_be_trail_inflates_python_bt_wr` / `project_preserve_bug_fixed_10cells_live_2026_07_28`
