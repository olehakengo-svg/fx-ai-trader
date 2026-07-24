# 仮説カタログ + グローバル多重検定台帳 — 2026-07-24 (user 指示: 探索最大化)

**user 指示 (2026-07-24)**: 「探索を爆速で走らせる・複数本並列 OK・仮説は網羅的に」
**実装形**: 生成は無差別 (7 レンズ × 12+ 本 = 87 本生成)、入場は規律 (headroom≥10x / 再試行禁止 / 台帳)。
**方法**: 14-agent workflow (7 レンズ並列生成 → KB 再試行禁止チェック → triage)。
**Raw**: `knowledge-base/raw/analysis/hypothesis-catalog-2026-07-24.json` (87 本全量 + ban verdicts)
**前提**: [[edge-dev-postmortem-2026-07-24]] の処方箋 (§6) の実装。live は一切触らない。昇格は R1。

---

## 運用ルール (凍結)

- **並列アクティブ上限 3 本** (E1/E7 のロック走行 2 本とは別枠)。compute は安価だが OOS 窓と pre-reg スロットが希少資源 — ファミリ追加は全員の Bonferroni 分母を膨らませる
- **台帳 m=12**: 新規 7 ファミリ (sweep_reversion 再検証 / price_shock 監査 / gap / MoF / COT / month-end-conditional / VIX-unwind) + 既登録 5 (E1 / E7 phase-1 / E12-design / htf_fb recheck / sr_anti_hunt)。parked は昇格時のみ台帳入り
- **全 pre-reg 共通ハード条件**: exit 機構フリー固定ホライズン測定 / explore 窓で headroom≥10x 実証後に LOCK / multi-week は swap を EV に純額込み / E1・E7 ロック窓は覗かない / banned 隣接ファミリは pre-reg に明示差分節を必須

## 凍結探索プロトコル (wave-0 ファミリ、実行前凍結)

- **データ**: `data/cache/massive/` parquet (12y)。**explore = 2014-01-01〜2021-12-31 / OOS = 2022-01-01〜2026-06-30**。OOS は候補凍結後に 1 回だけ接触
- **測定**: exit-free forward MFE/MAE + 方向純移動、h ∈ {4h, 12h, 24h, 72h, 120h}
- **統計**: event-block bootstrap、BH-FDR q=0.10 (wave ファミリ横断)、headroom 判定 = MFE p50 ≥ 10× ペア RT friction (理論値 + floor 1.30p 感度)
- **例外**: MoF 介入は事象が 2022 以降に集中し temporal split 不能 → 全事象記述統計 + permutation null + **将来介入への forward pre-reg** 形式に切替 (低 N 設計)

## Wave 構成 (score = prior × headroom × testability × 独立性)

### wave-0-now (本日着手、in-repo データ)
| score | 仮説 | 骨子 |
|---|---|---|
| 72 | **sweep_reversion_eurgbp 再検証** | 12.4y Bonferroni 生存 (t=4.46)・execution 死のみの唯一資産。exit-free 固定ホライズンで 12.4y 再測定 (exit-artifact 排除確認)。gate 修復は別線 (P-S1(a) R1 決裁パケット準備中、トリガ unique N≥10 まであと 2 イベント) |
| 58 | **price_shock 5席 exit-free 監査** | 12y+Bonferroni 昇格済みだが BE/Trail artifact 暴露後に未再測定の検証負債。shock 幅なら headroom≥10x が期待できる — explore 窓で確認 |
| 47 | **weekend_gap_fill_multiday** | KB 死亡記録 54 件に不在 = 未検証。gap≥20p のみ対象 (headroom gate)。トラップされた保有者の強制解消メカニズム。バックグラウンド線 — explore IC が綺麗な場合のみ pre-reg スロット消費 |

### wave-1-fetch (公開データ取得後)
| score | 仮説 | 骨子 |
|---|---|---|
| 66 | **mof_intervention_proximity_usdjpy** | カタログ中最強メカニズム (政策的強制カウンターパーティ、300-500p vs RT 2.14p = 100x+ headroom)。S4 は data-blocked (falsified ではない) — 財務省四半期開示リストで解除。fetch 即時開始 |
| 50 | **cot_spec_positioning_extreme_weekly** | 機関投機筋 (E1 のリテールと別母集団、部分独立ペナルティ適用済)。週次・数十年ヒストリで蓄積待ちゼロ。E1 データは覗かない |
| 43 | **equity_conditional_monthend_rebalance** | 条件付き月末フロー (株指数の月中騰落に比例)。**棄却済み無条件 WMR-fix と隣接** — explore IC が無条件形を明確に上回らなければ即 kill |
| 41 | **vix_riskoff_carry_unwind_jpy_crosses** | VIX スパイク → キャリー強制解消の continuation。E20 凍結 (carry-rank/mom63) とは別 estimand だが pre-reg 時に隣接性の敵対的チェック必須 |

### wave-2-accumulating (蓄積待ち・受動)
E7 phase-1 (verdict 08-28) / E1 (first look 10-15) / E12 volume (~3ヶ月) / htf_fb recheck (受動、実測ペースでは deadline 2027-01-31 に N≈15-30 で stale クローズ公算) / sr_anti_hunt N≥30 (受動)

### parked (台帳外)
oanda_labs_h4 fade (**E1 と同一メカニズムの double-bet — E1 校正入力専用**) / fred_cpi surprise (E7 重複) / tsmom weekly (E20 隣接) / mafe exit 復活 (正 EV ホスト不在) / yield_spread 残差 (07-24 口頭評価 HOLD) / sub-friction gross 構造 / E15 型無条件イベント窓

### BANNED (生成 87 本中 2 本除去)
london-4pm-fix-conditional-reversal (= london_fix_reversal の再着せ替え) / copper-china-demand-aud (= E4 lead-lag 同型)

## 実行順序 (triage 決定)

1. 本日: sweep_reversion 再検証 + price_shock 監査 起動 (アクティブ 2 本)
2. 本日: MoF fetch 発火 → 着地次第 3 本目のアクティブ線に
3. gap はバックグラウンド explore (スロット消費なし)
4. COT / month-end / VIX-unwind は今週 fetch まで、wave-0 解決に応じて順次昇格
5. 各 wave-0 線は explore verdict まで ~1 日

## 台帳 (verdict 追記式 — 全結果 PASS/FAIL 問わず記録)

| # | family | 状態 | verdict |
|---|---|---|---|
| 1 | sweep_reversion 再検証 | **explore 完了 2026-07-24** | ✅ **exit-free で生存** — 12h net med +5.10p/mean +7.72p (p<1e-4)、RT3.0p 控除後 +4.72p、11/13 年正。exit-artifact 説を棄却。同一標本の限界 (max-t 選択効果は新データでのみ解消可) → P-S1(a) 決裁パケットへ供給 |
| 2 | price_shock 監査 | **監査完了 2026-07-24** | ✅ demotion flag 0/5 (クリーニング後も全席 p=0.0001、headroom 6.5-35x)。⚠️ **feed artifact 発見**: 土曜行 + spike-revert 不良プリントが各席トレードの 4-12.8% を汚染、grid ev_pip は過大 (USD_CAD 97.9→42.4p)。⚠️ EUR_AUD/USD_CAD/AUD_JPY は pre-2021 OOS が 0 と分離不能 → regime watch (tier action なし) |
| 3 | weekend_gap | **explore 完了 → OOS pre-reg 起案中** | ⚠️ **PARTIAL** — multiday 棄却。狭い候補凍結: ≤12h fade、Bonferroni 生存 = EUR_USD 4h/12h (p<1e-4) + pooled 4h (p=2e-4)。GBP_USD は逆符号 (continuation)。モノトニシティなし。OOS 判定は stressed friction (3×RT) 主ゲート |
| 4 | mof_intervention | **fetch 完了 → forward pre-reg 起案中** | N=383 (1991-2024)、現代円買い 7 日/3 エピソード。**2026 エピソード ¥11.73 兆 (04-28..05-27) の日次内訳が Q2 開示 (~2026-08) まで非公開 = 開示前 LOCK で genuine OOS。LOCK 期限 2026-08-05** |
| 5 | cot_spec_extreme | **panel 完成、分析 queue** | 5,178 行 × 6 通貨 (2010-2026-07)、検証済 (JPY 2024-04 記録的 net short 再現)。release-lag (+3-4 日) 規律を分析時に必須 |
| 6 | equity_monthend_conditional | fetch queue (隣接注意) | — |
| 7 | vix_carry_unwind_continuation | fetch queue (隣接注意) | — |
| 8 | E1 positioning | LOCKED 走行中 | first look 2026-10-15 |
| 9 | E7 surprise phase-1 | LOCKED 走行中 | verdict 2026-08-28 |
| 10 | E12 volume design | 蓄積待ち | — |
| 11 | htf_fb recheck | 受動 registry | deadline 2027-01-31 |
| 12 | sr_anti_hunt N≥30 | 受動 | — |

## wave-0 実行記録 (2026-07-24、全線敵対的レビュー通過 — INVALID ゼロ)

- **成果物**: `tools/{sweep_reversion_exitfree_reverify,price_shock_exitfree_audit,weekend_gap_fill_explore,mof_interventions_fetch,build_cot_panel}.py` / `bt-results/*-2026-07-24.json` ×5 / `reports/*-2026-07-24.md` ×5 / `data/external/{mof_interventions.csv,cot_fx_panel.parquet}`
- **sweep_reversion**: 凍結トリガの完全再現 (N=543/t=4.46 一致) の上で exit-free 生存を確認。エッジは **~12h 平均回帰** (MFE/MAE 非対称は 4h/12h のみ、≥24h で反転 — 長ホールドへ外挿禁止)。レビュー指摘: bar-time≠wall-clock (週末跨ぎ ~11%)、72h/120h bootstrap は窓重複で過小分散
- **price_shock**: トリガ忠実度 1.003-1.020 で 5 席再現。**横断発見 = MASSIVE feed の土曜行 + 不良プリント汚染** (BT 全般に影響しうる infra 課題 → chip 化)。pre-2021 pure-OOS が有意なのは EUR_GBP (+6.1p p=4e-4) と NZD_JPY (+9.4p p=1e-3) のみ
- **weekend_gap**: fill は速く短命 (t-half 中央値 1-2h、full-fill 9-15h、120h fill 率 82-84%)。「爆速で走らせつつ FP を作らない」原則どおり、狭候補のみ OOS へ
- **MoF**: 開示ラグを利用した観測前 pre-reg 機会は**時限付き** — Q2 開示 (~2026-08) 前に LOCK 必須
- **横断規律メモ**: 週末境界の DST 問題 (21:00 UTC 固定 vs 実クローズ 22:00 冬時間) は pre-reg で定義凍結必須。bootstrap p の床 (1/(N+1)) は「p<1e-4」表記に統一
