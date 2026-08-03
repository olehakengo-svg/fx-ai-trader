# level_failed_break_d1 (台帳 #18) explore report — ❌ FAIL (2026-07-31)

**pre-reg**: [[level-failed-break-d1-explore-prereg-2026-07-31]] (🔒 commit 5ea2d4dc で凍結後に測定)
**データ**: TV OANDA D1 per-event export、8 ペア、explore 2014-01-01〜2021-12-31、290 イベント
**raw**: `knowledge-base/raw/bt-results/level-fb-d1-pass{1,2}-2026-07-31.json` / 測定器 `bt-results/tv-overlays/level_fb_d1_export.pine` / 統計 `tools/level_fb_d1_explore_stats.py`

## verdict: ❌ FAIL クローズ (OOS 2022+ 非接触保存)

| Gate | 結果 | 判定 |
|---|---|---|
| A headroom (per-pair MFE5d p50 ≥ 10×RT) | **8/8 PASS** — p50 51.3〜91.9p (要求の 2.4〜4.3 倍) | ✅ |
| B power floor (pooled N ≥ 200) | N=290 (実効週数 200) | ✅ |
| C primary (pooled fade 5d 純移動 > 0, 週 block perm p<0.05) | **−4.91p、p=0.702** — 符号が仮説と逆 | ❌ |
| D net EV (RT+swap 控除) | −8.81p (markup ±50%: −8.30/−9.32、RT floor: −7.25) | ❌ |
| E 集中 (単一週寄与 ≤50%) | 52.6% (2014-W38) — ただし総効果自体が負 | ❌ |
| F 一貫性 (年次符号 ≥6/8 + LOYO 全正) | 3/8、LOYO 7/8 負 | ❌ |

knife-edge 検査は Gate C が p=0.702 の完全 null のため非該当 (ナイフエッジ判定圏外)。

## 診断 (non-binding)

- **horizon 減衰**: net1 +1.06 → net3 −0.57 → net5 −4.91 → net10 −6.52p。fade は初日のみ微小に効き、以後は**継続方向に負ける**
- **サイド split**: L (下抜け失敗の買い) −12.17p / S (上抜け失敗の売り) +2.45p — 非対称だが S 側も RT 未満
- **per-pair**: 正は AUDJPY +8.8 / USDCAD +6.6 / GBPUSD +3.0、負は USDJPY −25.6 / EURJPY −20.4 等 — ペア間再現性なし
- **⚠️ 事後符号反転の禁止**: fade FAIL は「継続がエッジ」を意味しない — 継続方向の片側 p ≈ 0.30 で**継続も n.s.**。
  継続仮説を立てるなら新 family + 新 pre-reg (holiday レグ c の前例に従い、事後反転主張はしない)

## 測定 QA 記録 (凍結 assert が 2 回作動 — 設計どおり)

1. **OANDA D1 の Monday bar UTC 誤ラベル**: wknd=1257 検出 → trading-day ラベル (bar close 日、NY tz) に修正。
   fwd-return look ゼロ時点。修正後 wknd=0 / bars/week≈4.97 / 全ペア coverage 2002〜2004 開始
2. **cross-check 初回乖離は照合側の実装ミス**: 短窓 `_1d.parquet` (2016-04 開始) + 日曜バー混入で比較が無効だった。
   **正しい照合** (1h フル版 → NY17:00 境界 D1 再構築、7 ペア、EUR_JPY は 1h フル版不在で照合不能と開示):
   イベント日一致 ±2d = 27〜38/ペア、pooled 平均 parquet −2.93p vs TV −4.68p = **符号・量級一致、測定器妥当**。
   ペア別符号揺れ 2 件 (AUD_USD/AUD_JPY) は平均≈0・SE 12-16p 圏内のノイズ

## 帰結

- **同型再試行禁止**: 長 lookback 極値 (Donchian 型) の D1 close 確定失敗ブレイク × fade × multi-day exit-free
  全変種 (lookback/確認窓/dedup の摂動を含む)。knife-edge 摂動を試すまでもなく符号逆
- **prior への含意**: htf_fb×AUD_JPY (1H レベル、h24) の機構は D1/55d スケールへ**外挿不能**と実証。
  #11 recheck の判定には影響しない (別 family 宣言どおり)
- **正の副産物**: Gate A 全通過 = **D1 イベント系の headroom (MFE p50 ≥ 10×RT) は 8 ペアで実在**。
  「摩擦が殺す」のではなく「方向シグナルが無い」ことが死因 — 供給ラインの制約は headroom ではなく signal
- 次: 台帳 #19 round_number_major_level (敵対的検証 GO 済み) を単独 wave で凍結・測定
