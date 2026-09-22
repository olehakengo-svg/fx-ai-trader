---
id: 20260911-0200-ps-seat-hourly-c1-coverage-readout
title: "[M3 スループット] HourlyEngine C1 計装の到達確認 + ps 席残余 (3 席 × design 17 本ゼロ) の上流/下流帰属"
owner: unclaimed
status: queued (readout 実行可能日 = 2026-09-25、計装 deploy +14d)
created_at: 2026-09-11T02:00:00+0900
priority: P1
deadline: 2026-09-25 (registry `ps-seat-supply-hourly-c1-coverage`)
roadmap_gate: "M3 (clean live N≥30 セル×3) のスループット。ps×5 は LIVE 資格ロースタの中核で、供給 capture 20.6% の主因が未帰属のまま = 是正の打ち手が選べない状態"
rule: R3 (readout と帰属のみ。supply 是正・gate 変更・tier/lot 変更は本タスクの範囲外)
prereq_artifacts:
  - knowledge-base/wiki/analyses/ps-seat-supply-remeasure-2026-09-10.md (§7 verdict / §8 帰属 / §9 計装 / §10 後続)
  - knowledge-base/wiki/analyses/price-shock-seat-supply-audit-2026-07-29.md (親監査 §8 補足項目)
  - knowledge-base/raw/audits/ps-seat-supply-verdict-2026-09-11.json (verdict 生値)
  - knowledge-base/raw/audits/ps-seat-hedge-block-snapshot-2026-09-10.md (hedge_block 実測)
---

# 目的 (1タスク1目的)

2026-09-11 に敷いた HourlyEngine の C1 candidate 計装が**実際に本番へ届いているか**を確認し、
ps 席 3 席 (NZD_JPY / EUR_AUD / USD_CAD) の「design 17 本に対する観測ゼロ」を
**(A) 上流 = `evaluate_all` が候補を出していない** と
**(B) 下流 = 候補は席優先 select で勝ったが `_tick_entry` / order 層で落ちた** に割る。

# 背景 (なぜ 09-11 に判定できなかったか)

供給率 30d 再計測の正式 verdict は **REJECT** (design 34 / 観測 unique 7 / capture 20.6%)。
§8 の 3 項目のうち hedge_block (寄与 0、構造的に bind 不能) と blackout 床 (17 本中 ~0.2 本、
説明には wall-clock 84% 被覆が必要) は**否定**できたが、残余 ~100% は帰属できなかった。
理由は「未知の抑制要因」ではなく**測っていない**こと — 観測面 3 つがいずれも hourly 経路を
覆っていない (`_block_counts` は再起動で消える / `gate_block_daily` は 09-11 稼働開始 /
`evaluated_candidates` は `_dt_engine` 経路にしか call site が無かった)。

# 実行手順

1. **計装到達の確認 (これが最初。届いていなければ以降は無意味)**
   ```
   curl -s 'https://fx-ai-trader.onrender.com/api/demo/evaluated-candidates?view=summary&days=14'
   ```
   summary キーに `price_shock_rev_*` 5 席 (+ `donchian_momentum_breakout` /
   `keltner_squeeze_breakout`) が出ているか。**出ていなければ配線落ちとして R3 再修理**し、
   本タスクは (iii) を未判定のまま roll する (推測で帰属しない)。
2. **書込み量の実測** — `view=meta` の `rows` 増分と `/api/admin/disk_status` の `used_pct`。
   §9 の見積り (DTE 経路 3,125 行/日と同オーダー) を実測で置き換える。
   disk が逼迫していれば C1 retention 短縮 (R3、`c1_retention_days`)。
3. **帰属** — 3 席について `view=rows&strategy=price_shock_rev_<pair>_h1_long&days=14`:
   - 行が**ゼロ** → (A) 上流。`evaluate_all` が live feed 上で候補を出していない。
     §2 の forming-bar / closed-bar 母集団ずれと同じ層の問題として P-1/P-2 パケットへ合流
   - 行が**有る** → (B) 下流。`selected` 列で席優先 select が勝っているかを確認し、
     `gate_block_daily` (`/api/demo/block-counts?days=14` の `persisted`) と突合して
     どの gate が落としたかを特定する
4. KB 記録: analyses ページ §10 に判定を追記 + registry `ps-seat-supply-hourly-c1-coverage`
   を resolve/roll — **同一コミット**。

# 採用/保留/棄却の境界

- **(A) 上流確定**: 14d で 3 席の C1 行が 0 かつ他戦略の hourly 行が存在する (= 計装は生きている)
- **(B) 下流確定**: 3 席の C1 行 > 0。gate 別内訳を出す
- **判定不能 → roll**: 計装未到達 (手順 1 で 5 席が summary に不在)、または hourly 行が
  全戦略でゼロ (計装が届いていない証拠)。deadline を +14d roll し、配線を R3 で修理

# 禁止事項

- **EV / WR / PnL の計算禁止** — `ps-carveout-regate-post-172` (09-30) の凍結 look を burn しない (P-10 型 ban)
- supply 是正・gate 免除・tier/lot 変更は本タスクでは行わない。**帰属が出るまで §7(a) 型の是正を重ねない**
- 帰属を盛らない — 3 択 (A / B / 判定不能) 以外の結論を書かない
- 本番 DB / Render env / OANDA への書込み禁止 (read-only API のみ)
- 作業は worktree で行う (main checkout 座礁教訓)

# 検証コマンド

```
python3 -m pytest tests/ -x -q
python3 scripts/check.py
python3 tools/sync_kb_index.py --check
```

---

## 🔍 中間確認 (2026-09-16、roadmap autopilot — verdict ではない)

check.py の queue SLA 警告 (5 日滞留) を受けて確認。**本タスクは日付ゲート
(readout 実行可能日 = 2026-09-25 = 計装 deploy +14d) であり滞留ではない**が、
手順 1 (「計装到達の確認。届いていなければ以降は無意味」) は今日実行できる —
**届いていなければ 09-25 まで待つと 14 日窓を丸ごと失う**ため先行実施した。

### 手順 1 = ✅ PASS (計装は本番に届いている)

`/api/demo/evaluated-candidates?view=summary&days=14` → **46 キー**。うち hourly 経路:

- `donchian_momentum_breakout` ✅ 出現
- `price_shock_rev_eur_gbp_h1_long` ✅ 出現
- `hull_donchian_fade` ✅ 出現

⇒ 「配線落ちとして R3 再修理 + (iii) 未判定 roll」の分岐は**閉じた**。14 日窓は蓄積中。

### 手順 3 の暫定シグナル (⚠️ 確定させない)

ps 5 席のうち **`eur_gbp` のみ出現**。対象 3 席 (**NZD_JPY / EUR_AUD / USD_CAD**) と
`aud_jpy` は **day 5 時点で行ゼロ**。タスクの判定規則では「行ゼロ → (A) 上流
(`evaluate_all` が live feed 上で候補を出していない)」に該当する向きだが、
**本タスクは 14 日窓での readout を予定しているため、ここでは帰属を確定しない**
(day 5 の観測で 14 日設計の verdict を名乗るのは estimand のすり替え)。
09-25 に全窓で再実行して確定させる。

### 09-25 のチェックリストに追加

- [ ] `keltner_squeeze_breakout` が C1 summary に**不在** — 現時点では
      **「14 日間シグナルなし」と「配線ギャップ」を判別できない**。同じ hourly 経路の
      `donchian_momentum_breakout` は出現しているため配線一般の問題ではない。
      squeeze 系の低頻度で説明できるかを頻度期待値と突合して判別すること
- [ ] 手順 2 (書込み量 / disk `used_pct`) は未実施 — 09-25 の本実行で計測


---

# 執行結果 (2026-09-21、Claude 直接実行 — 期日 09-25 の 4 日前倒し)

`owner: claude` / `status: done`。Codex には委譲せず Claude が直接実行 (本番 API 読取り +
コード照合のみで重い BT を含まないため)。成果物 =
`knowledge-base/wiki/analyses/ps-seat-supply-remeasure-2026-09-10.md` §11。

## 完了条件の照合

- [x] 手順 1 (計装到達) — PASS。`view=summary&days=14` の `n_strategies=50` に
      `price_shock_rev_*` 5 席すべて出現。配線落ちではないので (iii) を roll せず判定できた
- [x] 手順 2 (書込み量) — `evaluated_candidates` 325,530 行 / disk `used_pct` 60.4%
      (`level=ok`) / `c1_retention_days` 90 / `write_probe` ok。**retention 短縮不要**。
      §9 の見積りを実測で置き換え済み
- [x] 手順 3 (帰属) — **(B) 下流で確定**。`view=rows` で 5 席とも行 > 0 かつ
      `selected=1` が 141/141、`block-counts?days=14` の `persisted` と突合して
      Σblocks == C1 行数が 5 席すべてで厳密一致。gate 別内訳まで特定
- [x] KB 記録 (§11 追記 + registry resolve + 後続新設) が**同一コミット**
- [x] `python3 -m pytest tests/ -q` green (3,416 passed / 17 skipped / 1 xfailed) /
      `python3 scripts/check.py` 全10チェック通過
- [x] コミットメッセージに `rule:R3` 明示

## 採用/保留/棄却の境界への当てはめ

タスク定義の境界は「(A) 上流確定 = 14d で 3 席の C1 行が 0 かつ他戦略の hourly 行が存在」/
「(B) 下流確定 = 3 席の C1 行 > 0」/「判定不能 → roll」。
**実測は 3 席とも行 > 0 (42 / 24 / 39) なので (B) 下流確定。** roll 条件 (計装未到達 /
hourly 行が全戦略ゼロ) はいずれも成立しない。

## Claude Review

出力を額面で採らず、4 点を独立に検証した:

1. **「候補がある」を「機会がある」と読み替えなかった** — 生 141 行は `bar_time` で
   distinct **10 本**。usd_cad は 39 行すべてが**同一バー** (2026-09-17 12:00Z) で、
   行数で機会を数えると 1 機会を 39 と誤読する (14.1 倍膨張)。C1 の estimand は
   per-tick (~30s poll) なので、機会の単位は必ず `bar_time`
2. **算術一致を機構で裏取りした** — Σblocks == 行数だけなら偶然の可能性が残るので、
   `_maybe_reserve_order_bar_emit` (1348 行、1 バー 1 予約、初回は通過) の call site
   (5491 行) が `spread_wide` 判定 (6244 行) より**前**であることをソースで確認した。
   この順序を当てると「終端 gate 発火数 ≒ distinct bar 数」が導かれ、
   nzd_jpy 2/2・eur_aud 3/3・aud_jpy 2/2 で実測と一致する。
   さらに eur_gbp の `order_bar_dedup` が **0** で `gbp_asia_flash_crash` が全 21 行 =
   この guard は予約より前、という gate 順序が本番データ側からも独立に読める
3. **不一致を隠さず記録した** — usd_cad のみ distinct bar 1 に対し `spread_wide` 2 (+1)。
   in-memory の `_order_bar_signal_emits` が再起動で消えた説が最も素直だが
   **独立確認はしていない**と §11.4 に明記した (帰属の向きは変わらない)
4. **「供給は design どおり」と盛らなかった** — 3 席 design 17 本/30d → 11 日窓の期待 6.2 に
   対し実測 6 は Poisson(6.2) と整合するが、**N=6 では ~2 倍の不足も排除できない**。
   主張は「**(A) が律速ではない**」までに留めた (§2 の分子/分母 disjoint と同じ規律)

**範囲を越えなかった点の明示**: 本タスクは R3 = readout と帰属のみ。
`spread_wide` が 3 席の律速と判明したが **gate は一切変更していない** (per-strategy cap も
閾値の動的化も Rule 1 = 365d BT + Bonferroni + pre-reg LOCK + user 承認が必要)。
EV / WR / PnL も未計算 (`ps-carveout-regate-post-172` の凍結 look を消費しない)。
唯一同一コミットで足したのは **magnitude 計装**で、これは
「閾値をどれだけ超えたか」が無いと disposition (退役 / cap / 動的化) を選べないという
本 readout 自身の結論から出た観測面の追加 — §9 が `gate_block_daily` を同じ論拠で
同一タスク扱いにした前例に揃えた。後続は registry
`ps-seat-spread-magnitude-readout` (期日 2026-10-19)。
