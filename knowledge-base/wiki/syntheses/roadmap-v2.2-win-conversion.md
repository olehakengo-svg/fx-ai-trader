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
| T2 | **live_tier_exempt リーク監査** | R3 | ✅ **完了 2026-06-12** (Codex 9b16ebb5): バグ確定 → PAIR_DEMOTED/FORCE_DEMOTED を exempt 経路から除外 + 送信直前 gate + 検知器盲点 (q5) 修正 + 回帰テスト | — |
| T3 | **wick_imbalance slippage -40p×2 forensic** | R3 | ✅ **完了 2026-06-12** (Codex af41f52a): **記録バグ確定** (stale signal_price 基準、実約定正常・PnL影響なし) → E10 停止不要。修正+backfillスクリプト済、**本番 backfill 適用が残作業** | 全期間 \|slip\|>10p は76件、live×wick は当該2件のみ |
| T4 | **LDN朝 (UTC07-09) counter-USD MR の SIZE lever 0.5x** — 対象 E5/E7/E10 | R2 | ✅ user 承認 2026-06-12 → Codex queue `20260612-1715-ldn-morning-size-lever` (P1) | env kill switch 付き。USD一方向レジーム終了で解除 |
| T5 | **JPYレジーム撤退 pre-reg** — D1 close > 160.8 or BOJ利上げ → JPY系4戦略 lot 0.5x | R1 pre-reg | 🔴 **発動 2026-06-18 (D1 161.295) → 執行 2026-07-06** (18日ギャップ、監視機構不在)。code lever `_resolve_jpy_cap_exit_size_lever` + 回帰テスト: [[jpy-cap-exit-prereg-2026-06-12]] 発動記録 | 復帰 = 復帰条件 KB 記録 + テスト変更 PR のみ |

## WS2: 勝ち集中・N蓄積 (Rule 1 正順)

| # | 項目 | 統計条件 | 状態 |
|---|---|---|---|
| T6 | **orb_trap GBP_USD SELL (E9) N蓄積** | clean N≥30 → H1 ∧ WF 3-fold ∧ Bonferroni(m=116) 再評価。N 以外は通過済 (WR.783/PF13.6/Wilson.581/Kelly.725/WF3-3) | E9 継続稼働。触らない |
| T7 | **Carry Dip v3 発火 E2E 検証** | ✅ **CLOSED 2026-07-06** — 0-fire 根因 = ceiling 159.50 のレジーム前提崩壊 (06-03 以降 RSI クロス 28 中 22 が ceiling block、**dormant-by-design**)。QUALBAR print telemetry 本番稼働 (07-06 deploy)。ceiling 再パラメータ化は R1 要件のため起案せず。残リスク: env gate render.yaml 未宣言 + live 側 dedup/cooldown 無効 (engine 再構築問題)。詳細: [[zero-fire-diagnosis-carrydip-vix-2026-07-02]] §6 | 159.50 割れで自動再稼働 |
| T8 | **本日 LIVE 投入 2 戦略の初週監視 pre-reg** — sweep_reversion_eurgbp_late (12y survivor, N=543/+6.22p/t=4.46) + hull_donchian_fade (C1-C4 通過, net+0.66p/PF1.07) | 発火頻度乖離 >3× or sweep 実測 spread >3.5p (検証時仮定 1.5p) で R2 停止。EUR_GBP エッジの 2021-2026 集中 caveat 監視 | Claude 次タスク (pre-reg を decisions/ に) |
| T9 | **Kalman D7 pre-reg を qualifying-bar 基準に書換え** | ✅ **CLOSED 2026-07-06** — QUALBAR print telemetry (class 属性 dedup、engine 再構築耐性) + pre-reg 追補 (分母付き判定表: dormant / filter落ち / 経路ブロックの3値判定)。分子は registry `t9-kalman-d7-fire-info` で毎日監視 | [[pre-reg-kalman-d7-shadow-fire-recovery-2026-05-28]] 追補参照 |

## WS3: エッジ要因解析シリーズ継続 (司令塔直轄)

- T10: ✅ **CLOSED 2026-07-02 = KILL** — 清浄shadow N=495 因子分解+敵対検証で生存セルゼロ、friction>edge 構造 (楽観上限=BE天井)。再試行禁止。SCALP_SENTINEL は shadow 収集のみ継続 (LIVE候補ゼロ固定)。詳細: [[bb-rsi-t10-kill-2026-07-02]]
- T11: ❌ **CLOSED 2026-07-06 = REJECT (R1)** — 「LDN朝×counter-USD MR」クラス禁止仮説は 12y MASSIVE grid で Codex 初回 PASS (aggregate Bonferroni p=0.0497) → **同日敵対的検証で棄却**: ①唯一の pass cell EUR_JPY は USD ネットエクスポージャ 0 で「counter-USD」メカニズム不成立 (USD 3ペア pooled gap -0.23p p=0.33)、②48-bar 重複ホールドの擬似反復 (lag-1 ρ=0.76) を日次クラスタ補正すると aggregate p≈0.15 で raw でも非有意、③TREND 閾値が in-sample median リーク (walk-forward で ×16=0.089 FAIL)。2026 YTD は効果逆転 (+12.6p)。**30d 実測はレジーム一過性と結論** — 戦略横断 lever は起案せず、T4 既存 lever の解除条件監視のみ継続。詳細: [[t11-ldn-morning-counter-usd-mr-12y-2026-07-06]]

## WS4: 目標再キャリブレーション

- T12: ✅ **決裁済 2026-06-12** — 目標を月利21.6% (数学的上限) 基準に再設定。CLAUDE.md / index.md 反映済み。Gate 1 (aggregate Kelly>0) は KPI M1 とほぼ等価なので存置

## 棄却済み (このロードマップで追わない)

- E6 rsk dedup 修正 — **2026-05-01 caec0e88 で修正済みと実コード検証** (MEMORY が stale だった、修正済み)
- counter-USD MR の SKIP フィルタ追加 — SIZE lever 優先原則 (2026-05-28 実証) に反する
- 低friction高TF risk-premia 再訪 — TSMOM NULL 確定済み (2026-06-08 rethink)

## ボトルネック

**クリーン N の蓄積速度** (全昇格候補 N<30)。原則3 (Shadow は削らない) と原則4 (攻撃は最大の防御) に従い、shadow 発火は止めない。LIVE 側だけ winning-location フィルタ + SIZE lever で守る。
