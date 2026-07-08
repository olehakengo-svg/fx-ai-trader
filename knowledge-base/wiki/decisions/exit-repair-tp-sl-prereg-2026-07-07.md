# Pre-registration LOCK: Exit-Repair — TP/SL 実走距離整合 grid (rule:R1)

**登録日**: 2026-07-07 (BT 実行前に設計固定 — カーブフィッティング禁止の遵守)
**Status**: 🔒 **LOCKED** — 本文書の変更はレビュー必須 PR のみ。BT 結果を見た後のエンドポイント/グリッド/対象セルの変更は禁止
**起点**: [[payoff-asymmetry-diagnosis-2026-07-07]] (T3 診断確定) / [[roadmap-v2.3-payoff-friction-repair]] WS-Diag T2
**承認**: user 2026-07-07「進めていいよ」= R1 パイプライン始動の承認。**実装 (live パラメータ変更) は verdict PASS 後の user 最終承認が別途必要**

## 1. 仮説 (H1)

設計 TP が実走距離 (winners MFE 帯 4–6p) の約5倍遠いことが payoff 0.274 の主因である (T3 確定)。
**H1: 設計 TP を短縮し (SL も R:R 維持方向で調整)、BE/Trail を無効化した exit 構成は、現行設計比で摩擦調整後 EV を改善し、少なくとも 1 構成でポートフォリオ摩擦調整 EV > 0 を達成する。**

帰無仮説 H0: どの構成も摩擦調整後 EV ≤ 0 (= exit 再設計では黒字化せず、シグナル張り替え (WS3) が唯一の経路)。

## 2. Grid (a priori 固定、9 構成)

| パラメータ | 値 | 根拠 |
|---|---|---|
| TP_mult | {0.4, 0.6, 0.8} × 現行設計 TP | T3: 実走 MFE/設計TP ≈ 0.20 (中央値ベース)。0.4 が MFE 帯近傍、0.8 が保守側 |
| SL_mult | {0.6, 0.8, 1.0} × 現行設計 SL | T3: SL ~9p vs MFE 天井 ~5p の R:R ミスマッチ。負け側は設計どおり執行されるため SL 距離が直接 avgL を決める |
| BE/Trail | **OFF 固定 (ablation)** | MEMORY `project_be_trail_inflates_python_bt_wr` (+20pp 水増し) + T3 (trail は解でない)。BT/live 乖離の既知源を遮断 |

TP_mult/SL_mult は**比率レバー** (絶対 pips ではない) — entry_type 毎の ATR ベース設計を保存し、fit 対象を 2 自由度に制限する。

## 3. 評価プロトコル

- **エンジン**: 本番 signal 関数 (`backtest_mode=True`)。BT/本番ロジック統一原則。
- **期間**: 365d。**ただし診断窓 2026-06-07〜2026-07-08 は in-sample (grid の動機データ) のため評価から除外**。
- **対象セル**: 診断窓 clean live N≥7 の 7 entry_type (trendline_sweep / wick_imbalance_reversion / zz_pivot_v60_sr / vix_carry_unwind / dt_sr_channel_reversal / vsg_jpy_reversal / bb_rsi_reversion) × 該当 pair。**例外**: bb_rsi_reversion は T10 KILL (再試行禁止) のため除外 → 実対象 6 entry_type。demote 済みセル (wick×GBP_USD 等) も BT には含む (研究であり live 復帰ではない)。
- **摩擦**: per-pair 理論値 ([[friction-analysis]]: USD_JPY 2.14 / EUR_USD 2.00 / GBP_USD 4.53 / EUR_JPY 2.50) を往復控除。感度分析として実測フロア 1.30/t も併記 (判定には理論値を使用 = 保守側)。
- **Walk-forward**: 3-fold (約 120d ×3、診断窓除外後)。fold 毎の摩擦調整 EV 符号を記録。

## 4. エンドポイント (固定)

- **Primary**: 構成毎の**ポートフォリオ集計** (対象セル pooled) 摩擦調整 EV。多重性 m=9 (grid 構成数)、**BH-FDR q=0.10**。トレード非独立性はブロックブートストラップ (日次ブロック) で SE 推定。
- **Secondary (記述のみ、判定に不使用)**: セル別摩擦調整 EV / payoff / WR、fold 別符号。
- **PASS 条件**: 少なくとも 1 構成で (a) FDR 通過 (b) WF 3-fold pos_ratio ≥ 2/3 (c) 摩擦調整 EV > 0。
- **FAIL 条件**: 全構成が (a)-(c) のいずれかを満たさない → H0 採択、**WS3 (シグナル張り替え) へ全振り**を v2.3 に反映。

## 5. ナイフエッジ3点検査 (verdict 時必須 — T11 lesson)

1. **メカニズム整合**: PASS 構成の改善が「TP 到達率上昇 × 実現 R:R」の機構どおりか分解確認 (別要因のまぐれ PASS を排除)
2. **擬似反復**: 保有時間の重複による自己相関を lag-1 ρ で確認、日次クラスタ補正後も有意か
3. **閾値リーク**: TP_mult/SL_mult の PASS が格子点固有 (knife-edge) でないか隣接構成との整合を確認

## 6. 執行と監視

- **BT 実行**: Codex queue タスク `20260707-1640-exit-repair-tp-sl-grid` (本 pre-reg を仕様として参照)
- **監視**: registry `exit-repair-bt-deadline` — **2026-07-21 までに verdict 未着なら stale アラート** (T5 の 18 日執行ギャップ再発防止)
- **verdict 記録**: 本文書に追記 + `raw/bt-results/` 保存 + session log。PASS 時は user 最終承認を経て実装 PR (回帰テスト + 段階ロールアウト条件を含む)

## 7. 除外・注意 (LOCK 時点で明示)

- 本 pre-reg は **live パラメータを一切変更しない** (純研究)。
- MFE/MAE はバー粒度記録 (T3 caveat #2) — BT も同粒度のため内部整合するが、tick 粒度の実行差は残存リスクとして verdict に明記。
- 診断窓の MFE 統計から grid を導出しているため、**診断窓を評価に含めることは全構成で禁止** (in-sample リーク)。
- slippage_pips/spread_at_exit 列の本番輸出 (task_d932525c、別セッション進行中) が完了したら、感度分析の実測フロアを更新してよい (エンドポイントは不変)。

---

## 8. VERDICT (2026-07-08): ❌ **FAIL — H0 採択** (機械判定 + ナイフエッジ3点検査済)

**執行記録**: executor は §6 の Codex queue から **claude (Fable5) 直接実行に変更** (2026-07-08、user 運用委任「codex 使うのが正しいのか改めて考えて…運用はまかせるよ」に基づく。§2-§4 の LOCK 内容は不変 — 実行者は運用事項。期日 07-21 に対し 13 日前倒しで verdict 到達)。実装 = `tools/exit_repair_tp_sl_grid_bt.py` + `app.py` BT 専用 env hook (`BT_TP_MULT`/`BT_SL_MULT`、RR check 直後適用でエントリー母集団を構成間固定、env 未設定で完全 no-op、pytest 1990 green)。

### 8.1 機械判定 (§4 エンドポイント)

**全 9 構成が PASS 3条件を全て不通過** — (a) BH-FDR q=0.10: 全構成 p=1.0 で不通過 (b) WF 3-fold pos_ratio: 全構成 0/3 (c) 摩擦調整 EV>0: 全構成負。

| config | N | WR% | EV_theory (p/t) | EV_floor | TP-hit |
|---|---|---|---|---|---|
| **tp0.4_sl0.6 (最良)** | 628 | 48.4 | **−2.96** | −1.36 | 0.401 |
| tp0.4_sl0.8 | 614 | 50.5 | −3.89 | −2.29 | 0.417 |
| tp0.4_sl1.0 | 598 | 53.3 | −4.13 | −2.54 | 0.441 |
| tp0.6_sl0.6 | 609 | 41.5 | −4.22 | −2.62 | 0.276 |
| tp0.8_sl1.0 (最悪) | 559 | 43.5 | −6.06 | −4.48 | 0.250 |
| baseline 1.0/1.0 (記述) | 549 | 40.6 | −6.64 | −5.05 | 0.215 |

- 日次ブロックブートストラップ (B=10,000, seed 固定, 208 取引日): 最良構成でも resample 平均の **100% が負** (p=1.0, SE 0.594)。WF fold 別 EV = −3.71/−2.37/−2.55 (全期間一様に負 — 特定レジーム依存ではない)
- データ: 365d 15m (診断窓 2026-06-07〜 は除外、除外 48 trades/構成)、本番 signal 関数 `backtest_mode=True`、BE/Trail OFF、V2 parity (WICK/DT_SR_CHANNEL/VSG =1)

### 8.2 ナイフエッジ3点検査 (§5)

1. **メカニズム整合 ✅ (レバーは設計通り作動)**: TP-hit 率 0.215 (baseline) → 0.401-0.441 (TP_mult 0.4) と約2倍、EV は TP 短縮・SL 短縮方向に**厳密単調に改善** (baseline −6.64 → 最良 −2.96、+3.67 p/t)。T3 診断のメカニズム (capture-TP距離逆相関) は grid でも再現。**FAIL は「レバーが効かなかった」のではなく「効いても黒字に届かない」** — 診断の counterfactual 上限 (両レバー完璧でも −77.6p) と整合。
2. **擬似反復 ✅**: lag-1 ρ = −0.058 (trade-level) / +0.055 (daily-mean)。自己相関は無視可能で、判定は日次ブロックで既にクラスタ補正済み。p=1.0 は如何なる補正でも符号反転しない。
3. **閾値リーク ✅ (該当なし)**: PASS 構成ゼロのため leak の余地なし。EV 曲面は両軸で厳密単調 (最良 = grid 角 0.4/0.6) で孤立格子点なし。※角が最良 = 最適点が grid 外 (更なる短縮側) にある可能性はあるが、事後の grid 拡張は本 LOCK が禁止 — 仮に外挿しても EV_floor −1.36 からの残距離と TP-hit 頭打ち傾向から黒字転換は見込み薄。

### 8.3 感度・頑健性

- **感度 run (pre-PR#58 コード、mixed 込み trendline_sweep)**: 同一結論 FAIL 0/9 (最良 −3.11)。**2つの独立コード状態で verdict 一致** (`exit_repair_tp_sl_grid_2026_07_sensitivity_pre58.json`)。
- **実測フロア摩擦 (1.30p/t) でも全構成 pooled 負** (最良 −1.36)。セル単位の唯一の例外 = dt_sr_channel_reversal×EUR_JPY (N=176, EV_floor **+0.41**, EV_theory −0.79, TP-hit 0.55) — Secondary (判定外・事後選択) であり、次期 pre-reg の探索仮説としてのみ記録。
- **摩擦の扱い (caveat)**: BT 内部摩擦 (spread/2+slip×entry/exit) を算術足し戻し→gross 化→理論 RT 控除。entry 摩擦のバリア幾何 path 効果は残存 = **控除は保守側 (二重計上方向)**。ただし実測フロア側 (控除過小方向) でも全構成負のため verdict は摩擦モデルに対して頑健。
- **Time-decay SL tightening** (BE 類似機構、MAX_HOLD×50% 後) は BE/Trail ablation の対象外で残置 (本番にも存在 = parity)。
- エントリー母集団の構成間ドリフト (cooldown の exit 依存) は N=549〜628 の範囲で軽微。

### 8.4 帰結 (§4 の固定分岐)

**H0 採択: 「exit 再設計では黒字化せず、シグナル張り替え (WS3) が唯一の経路」** — roadmap v2.3 の T2 を FAIL クローズし、**WS3 (20p 走る場所への entry 再設計) へ全振り**を正式反映する。WS3 の優先母集団は [[friction-adjusted-ev-map-2026-07-07]] §5-3 の「高 gross WR × 深 net−」群 (trendline_sweep / gbp_deep_pullback / sr_anti_hunt_bounce) + 本 grid の近接セル dt_sr_channel_reversal×EUR_JPY。

**成果物**: `raw/bt-results/exit_repair_tp_sl_grid_2026_07.{json,md}` (primary) / `…_sensitivity_pre58.{json,md,_trades.json}` (感度) / registry `exit-repair-bt-deadline` inactive 化済み。
