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
