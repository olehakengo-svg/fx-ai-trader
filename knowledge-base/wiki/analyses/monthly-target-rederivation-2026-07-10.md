# 月利目標の再導出: 21.6% の考古学と段階目標化 (rule:R3 算数再導出、2026-07-10)

**結論**: 月利 21.6% は「検証を通ったポートフォリオの期待値」ではなく「既に消滅した 12-cell 集合の、二重の楽観バイアス込み shadow 推定の上限値」。現行制約下の現候補集合 (stage-2 対象 2 セル) の数学的天井は **+0.15〜2.4%/月** であり、21.6% は到達目標として機能しない。**user 承認 (2026-07-10) により段階目標 M1→M2→M3 へ移行し、21.6% は aspirational anchor に格下げ**。
**根拠決裁**: [[shortest-path-decision-memo-2026-07-10]] D5 / **数値出典**: 2026-07-09/10 の本番 API・コード・bt-results 実測 (8-agent workflow、敵対的レビュー3レンズ済)

---

## 1. 21.6% の導出考古学

| 項目 | 事実 |
|---|---|
| 一次出典 | TP-HIT 12-cell 検証 (2026-06-05, commit 0688b333, `tools/tp_hit_12cell_portfolio_validation.py`)。リポジトリ直下 `bt-results/tp-hit-12cell-portfolio-2026-06-05.json` の `portfolio.dd20_sizing_monthly_return_expectancy`: raw **44.36 pips/月** → Bonferroni 保守係数 0.5 で **22.18 pips/月** |
| pips→% 変換 | 当時の MEMORY (現在は統合で消失) にのみ存在し、**KB 内に導出式が残っていない**。KB 初出は [[strategy-rethink-2026-06-08]] の「現実上限 ~21.6% (Bonferroni 後)」 |
| 検証自体の結論 | **promote_recommended = 0** — 12 cell 全てが H1 Gate ∧ WF 3-fold ∧ Bonferroni(m=116) を同時充足せず。つまり 21.6% は「どのセルも昇格基準を通らなかった」検証から出た数字 |
| 楽観バイアス① | 母体は shadow 実測 N=470 — 後に BE/Trail 水増し (WR +20pp、MEMORY `project_be_trail_inflates_python_bt_wr`) が判明した経路の数値 |
| 楽観バイアス② | DD20% 動的サイジング前提 — 現行コードの lot 制約 (下記 §3) を反映していない |
| 母体の現在 | 12 cell 中 live 経路残存は **1〜2/12** (trendline_sweep×EUR_USD のみ確実、dt_bb_rsi_mr×GBP_USD が観測事実ベースで残存)。orb_trap は FORCE_DEMOTED、sr_anti_hunt は E12 stage=0、wick_imbalance×GBP_USD / dt_bb_rsi_mr×EUR_USD は PAIR_DEMOTED、他は UNIVERSAL_SENTINEL/Phase0 |

## 2. 現行制約 (2026-07-09/10 実測)

- **NAV 278,905 JPY** (累積 −22%)。21.6%/月 = **60,244 JPY/月**
- **lot chain**: DD 防御 0.2x × OANDA_FORCE_FLAT_UNITS 5000 → 実効 1000u (07-07 live fill #549086 で観測)。絶対上限 `_OANDA_LOT_CAP` = 10,000u (L8869、lot_ratio cascade 後に再適用 — ratio 3.0x でも 30,000u は執行されない)。10,000u の証拠金 ≈ 74,000 JPY = NAV の ~27%
- **DD 防御の解除**: `DD_LOT_TIERS` (risk_analytics.py): DD≥8%→0.20 / ≥6%→0.40 / ≥4%→0.60 / ≥2%→0.80 / <2%→1.0。dd_pct 分母 = OANDA_EQ_BASE_PIPS (実効 1000 pips)、eq_peak +16.9 / eq_current −991.1 → **0.4x 復帰に +928.1p、1.0x に +988.2p の回復が必要**。eq_peak は非減衰 (ラチェット) — 現行 EV では取引による解除は不可能。解除 = 再基準化のコード変更 (user 決裁)
- **agg-Kelly gate**: 固定 cutoff 2026-04-16 累積で −0.2758 — carve-out なしに新セルは live 発火しない ([[shortest-path-decision-memo-2026-07-10]] §1a)
- **pip 価値 (概算、USD/JPY≈162)**: EUR_USD 1000u≈16.2 / 5000u≈81 / 10000u≈162 JPY/pip。AUD_JPY 1000u=10 / 10000u=100 JPY/pip
- **発火頻度 (実測)**: london_fix_reversal×EUR_USD ≈ 3.4件/月 (OOS N=41/年、shadow 実測 ~4.9件/月 日次dedup)。htf_false_breakout×AUD_JPY ≈ 2.5〜3.3件/月 (探索窓 27/11ヶ月〜OOS 39/12ヶ月)

## 3. 天井の再計算 (段階別月利)

| 段 | 状態 | 月利 (実数) | 前提 |
|---|---|---|---|
| S1 | 正EVセル1個 @1000u | **+0.01〜0.04%** (実質ゼロ) | carve-out 済み。価値は金額でなく「Kelly>0 学習データの供給」 |
| S2 | 2セル @5000u | **+0.1〜0.4%** | 防御解除ラダー (再基準化 user 決裁) 通過後 |
| S3/S4 | 2セル @LOT_CAP 10,000u | **+0.15〜0.5%** (PASS床 EV +0.5〜1p/t) 〜 **+0.7〜2.4%** (楽観 +3p/t) | EV 実現値は stage-2 verdict の近傍平均 EV で置換する (点推定は勝者の呪いで上振れ) |
| S5 | 21.6% (60,244 JPY/月) | hard cap 下で +1.5p/t なら **~310 t/月 = stage-2 級セル ~90 個相当**。margin 限界 (25x) まで解放しても **15〜20 セル × +2p/t** | セル数が唯一のスケール変数 — 探索パイプラインの常時運転が必要条件 |

## 4. 段階目標 (user 承認 2026-07-10)

| 目標 | 定義 | 必要条件 |
|---|---|---|
| **M1** | clean live (`oanda_trade_id != ''`) 30d PnL の統計確認済み符号転換 (セル単位 live N≥30 の正EVセル ≥1 ∧ book 全体 Wilson 下限 > 0 相当) | stage-2 PASS or 供給ライン survivor + carve-out + shadow parity 通過 |
| **M2** | **+0.5%/月** (NAV 実現、30d rolling) | M1 + 防御解除ラダー (0.2x→1000u→5000u、各段 R2 復帰条件付き) + 2 セル以上 |
| **M3** | **+2〜3%/月** | 正EVセル **5 個以上** + Kelly Half 稼働 + FLAT units 再スコープ |
| anchor | 21.6% は aspirational anchor (優先順位判断の分母には使わない) | M3 到達後にポートフォリオ実測で上限を再導出 |

**KPI 3層** (誤診防止): L1 = セル別摩擦調整 EV p/t (昇格 gate) / L2 = 予測月利 Σ(EV×N×pip価値)/NAV (ブリッジ) / L3 = NAV 実現月利 (mission)。DD 表示% (分母 1000p アーティファクト) は KPI から除外済み (roadmap v2.3 と整合)。

## 5. 注意 (この文書の限界)

- 発火頻度・EV レンジは BT/OOS/shadow 由来 — live 実測で毎月更新すること (特に D2 の 15m AUD_JPY モード稼働後)
- 本文書は目標の「測り方」を変えるものであり、4原則 (攻める) は不変。段階化 = 守りへの傾斜ではなく、探索供給 (トラックB) を常時運転する構造的理由の明文化
