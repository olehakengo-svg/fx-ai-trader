# ロードマップ v2.2: Win Conversion — LIVE負け→勝ち転換

**作成日**: 2026-06-12
**旧版**: [[roadmap-v2.1]] (2026-04-14, DT幹+Scalp枝)
**根拠**: 2026-06-12 LIVE負け要因監査 (30d clean live N=84 / -37.9pip、MEMORY `project_live_loss_factor_audit_2026_06_12.md`) + [[audit-index]] 系列

---

## v2.1 からの前提変更 (なぜ v2.2 が必要か)

1. **v2.1 の「DT幹」は消滅** — session_time_bias は 12y MASSIVE BT で全 pair REJECT ([[audit-index]] 2026-06-11)、edge cell E2/E8 停止済み。幹の年間+433pip 推定は無効。
2. **月利100%は数学的に不可能と確定** — TP-HIT 12-cell 検証 (2026-06-05, commit 0688b333): 証拠金4×NAV+ruin 63%。Bonferroni 補正後の現実上限 ~21.6%/月。
3. **dedup 汚染除去後、昇格資格セルはゼロ** — TF-aware dedup (2026-06-08) で全 promote 候補 N<30。クリーン N 蓄積が唯一の昇格経路。
4. **負けの構造が特定済み** — 30d 損失の核は (a) EUR_USD SELL -49.7p (ECB前底固め×LDN朝MR、セル停止済み)、(b) USD全面高への counter-USD MR -28p、(c) NY 午後薄商い MR。勝ちは JPY 系 +44p (160介入キャップ整合)。

## コンセプト: 「負け経路を閉じ、勝ちレジームに資本と N を集中する」

```
負け側: 設計破綻確定セルの停止 (済) + 残存リーク経路の封鎖 + 負け時間帯の SIZE lever
勝ち側: JPY系MR (介入キャップ) + 12y survivor 2戦略 (本日LIVE) + orb_trap N≥30 待ち
横断:  エッジ要因解析シリーズ継続 (N降順) で kill/redesign を回し続ける
```

**KPI (30d rolling, clean live is_shadow=0, dedup除外, XAU除外)**
- M1: clean live PnL > 0 (現在 -37.9p) — 最初のマイルストーン
- M2: 負けクラスタ (counter-USD MR + 薄商い時間帯) 寄与 > -10p/30d (現在 ~-50p)
- M3: clean N≥30 セルを 3 個 (現在 0) → equal-risk weighting 適用開始条件
- M4: Gate 再キャリブレーション後の月利目標への軌道復帰 (T12 で再定義)

---

## WS1: 止血 (Rule 2/3, 今週)

| # | 項目 | Rule | 状態 | 採用/棄却条件 |
|---|---|---|---|---|
| T1 | **E12 sr_anti_hunt_bounce EUR_JPY stage=0** | R2 | ✅ **実行済 2026-06-12 07:36 UTC** (stage 1→0) | 根拠: 20260608 forensic「設計が誤」確定 + Live N=4 WR25% -7.0p。復帰条件: TP/hold 再設計 + 12y BT 通過のみ (R1) |
| T2 | **live_tier_exempt リーク監査** — PAIR_DEMOTED の xs_momentum が `mtf_gate_action=live_tier_exempt` で live 発火 (30d N=3 -1.4p)。demoted 戦略に exempt 経路が開く設計意図の code derivation → 封鎖 or 明示 allowlist | R3 | Codex queue 投入 (P1) | exempt 経路の demoted 通過が設計なら allowlist 文書化、バグなら封鎖 + 回帰テスト |
| T3 | **wick_imbalance slippage -40p×2 forensic** (6/10 17:46/18:41 GBP_USD、記録バグ疑い) | R3 | Codex queue 投入 (P2) | oanda_audit×demo_trades 突合。実損なら E10 即停止判定 (R2)、記録バグなら修正+backfill |
| T4 | **LDN朝 (UTC07-09) counter-USD MR の SIZE lever 0.5x** — 対象 E5/E7/E10。30d 実測: 当該時間帯 -71.8p | R2 | 🔶 **user 決裁待ち** | SKIP でなく SIZE (lesson: SIZE lever > SKIP filter 2026-05-28)。USD一方向レジーム終了 (DXY 反転 or Fed pivot) で解除 |
| T5 | **JPYレジーム撤退 pre-reg** — JPY系勝ち (+44p) は 160 介入キャップ依存。キャップ消滅 (D1 close > 160.8 or BOJ利上げ実施) で vsg/dt_sr_channel/vix_carry/ema200 lot 0.5x | R1 pre-reg | 🔶 **user 決裁待ち** | pre-reg LOCK をこの文書でなく decisions/ に切って commit |

## WS2: 勝ち集中・N蓄積 (Rule 1 正順)

| # | 項目 | 統計条件 | 状態 |
|---|---|---|---|
| T6 | **orb_trap GBP_USD SELL (E9) N蓄積** | clean N≥30 → H1 ∧ WF 3-fold ∧ Bonferroni(m=116) 再評価。N 以外は通過済 (WR.783/PF13.6/Wilson.581/Kelly.725/WF3-3) | E9 継続稼働。触らない |
| T7 | **Carry Dip v3 発火 E2E 検証** — `USDJPY_CARRY_DIP_LIVE_ENABLE=1` 確認済みだが live fill 0 | qualifying-bar (全 filter PASS) ベースの発火期待値 logging。7d 0-fire なら filter 診断 | Claude 次タスク |
| T8 | **本日 LIVE 投入 2 戦略の初週監視 pre-reg** — sweep_reversion_eurgbp_late (12y survivor, N=543/+6.22p/t=4.46) + hull_donchian_fade (C1-C4 通過, net+0.66p/PF1.07) | 発火頻度乖離 >3× or sweep 実測 spread >3.5p (検証時仮定 1.5p) で R2 停止。EUR_GBP エッジの 2021-2026 集中 caveat 監視 | Claude 次タスク (pre-reg を decisions/ に) |
| T9 | **Kalman D7 pre-reg を qualifying-bar 基準に書換え** (0 fire が設計通りか判定可能に) | qualifying bar 数 vs 発火数の整合 | Claude (低優先) |

## WS3: エッジ要因解析シリーズ継続 (司令塔直轄)

- T10: **#2 bb_rsi_reversion N=780** (シリーズ次番、キュー済) → kill/redesign 判定。SCALP_SENTINEL 残置の妥当性も判定
- T11: **新仮説「LDN朝×counter-USD MR」クラス禁止** — 30d 実測 (UTC07-09 -71.8p) から一般化できるか 12y MASSIVE grid で検証 (R1)。通過すれば戦略横断の構造フィルタ (SIZE lever) に昇格

## WS4: 目標再キャリブレーション

- T12: 🔶 **user 決裁待ち** — v2.1 Gate 2 の「月利100%」を数学的上限 (~21.6%/月、Bonferroni 後) ベースに再設定。Gate 1 (aggregate Kelly>0) は KPI M1 とほぼ等価なので存置

## 棄却済み (このロードマップで追わない)

- E6 rsk dedup 修正 — **2026-05-01 caec0e88 で修正済みと実コード検証** (MEMORY が stale だった、修正済み)
- counter-USD MR の SKIP フィルタ追加 — SIZE lever 優先原則 (2026-05-28 実証) に反する
- 低friction高TF risk-premia 再訪 — TSMOM NULL 確定済み (2026-06-08 rethink)

## ボトルネック

**クリーン N の蓄積速度** (全昇格候補 N<30)。原則3 (Shadow は削らない) と原則4 (攻撃は最大の防御) に従い、shadow 発火は止めない。LIVE 側だけ winning-location フィルタ + SIZE lever で守る。
