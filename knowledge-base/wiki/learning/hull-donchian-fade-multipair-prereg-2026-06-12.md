# 🔒 Pre-reg LOCK: hull_donchian_fade 横展開 (4ペア一発判定) — 2026-06-12

**MEMORY:** `project_hull_donchian_multipair_prereg_queue.md`
**LOCK 規律**: 本節記載のプロトコル・gate・spread を実行前に凍結。実行後の変更・grid 探索・
パラメータ再調整は禁止 (post-hoc selection 罠)。結果は PASS/FAIL を問わず本ファイルに append。

## 凍結ルール (EUR_USD holdout confirm 済み、変更禁止)

- Hull(HMA55) trend (HULL[0] vs HULL[2]) × Donchian(20) 二重確認の fade
- entry gate: width/ATR14(SMA of TR) ≤ **そのペア自身の 2014-2022(<2022-01-01) train-q33**
  (q33 再計算はルールの一部。outcome 非参照のため全期間適用で汚染なし)
- exit (live-mechanics 忠実度): TP=entry-bar Donchian basis (static, intrabar limit) /
  SL=4×ATR14 intrabar **SL-first** / max_hold 96 bars → close 決済
- flat 時のみエントリー、pyramiding なし、TP/SL サイド sanity gate (本番実装同一)
- entry=シグナル bar close、spread は round-turn 控除

## エンジン較正 (実行前検証済み)

`hull-donchian-1m-validation/fidelity_engine.py` が LIVE 投入根拠 BT を再現:
EUR_USD holdout N=1834/1833, WR=0.780 (一致), net+1.335p (vs +1.342), PF=1.190 (vs 1.191),
q33=3.8558 (本番 `MAX_WIDTH_ATR` と一致)。

## Universe (m=4) と spread 仮定 (凍結)

| pair | data | pip | spread (round-turn) |
|---|---|---|---|
| USD_CHF | MASSIVE 15m ~12.4y (新規 fetch) | 0.0001 | 1.2p |
| AUD_USD | MASSIVE 15m ~12.4y (新規 fetch) | 0.0001 | 0.8p |
| EUR_GBP | cache 12.3y | 0.0001 | 1.2p |
| EUR_JPY | cache 12.3y | 0.01 | 1.0p |

**除外と理由**: GBP_JPY/AUD_JPY/NZD_JPY/NZD_USD/USD_CAD = cache 1.1y のみで
2014-2022 train 窓が存在せず q33 ルール適用不能 (かつ 3y 未満基準)。USD_JPY = 同上 +
sweep で gross +0.10p の既知死亡。EUR_USD/GBP_USD = ルール選定に使用済み (真 OOS でない)。

## 判定条件 (per pair, ALL required, 実行前凍結)

- C1: net EV > 0
- C2: bootstrap p (10k, seed=42, one-sided mean>0) が BH-FDR (m=4, q=0.10) 生存
- C3: walk-forward 4 等分時間 fold で ≥3/4 fold net 正
- C4: Wilson 95% lower bound (WR) > 損益分岐 WR (= avgLoss/(avgWin+avgLoss))
- C5: LONG / SHORT 両 side net EV > 0

**報告のみ (gate ではない)**: trailing-90d regime (UP/DOWN) × side 分解 / exit-reason 構成 /
保有時間 / 2022 以降サブ期間 / spread +0.3p ストレス列。

**通過ペアは LIVE 候補として user 決裁へ** (shadow-first の意図的例外は user 判断事項)。
新ペアの全期間はルールに対して genuine OOS のため train/holdout 分割なしの全期間一発判定。

## 結果 (2026-06-12 実行、verdict 確定 — 再調整禁止)

**全 4 ペア REJECT。** raw output: `hull-donchian-1m-validation/reports/prereg_multipair_fidelity.txt`

| pair | N | WR | net EV | PF | p | C1 | C2 FDR | C3 WF | C4 Wilson | C5 sides | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| USD_CHF | 4090 | .789 | **+2.117p** | 1.340 | <.0001 | ✅ | ✅ | ❌ 2/4 | ✅ | ✅ | REJECT |
| AUD_USD | 4084 | .767 | +0.591p | 1.082 | .0233 | ✅ | ✅ | ❌ 2/4 | ✅ | ❌ L-1.01 | REJECT |
| EUR_GBP | 3686 | .782 | +0.146p | 1.026 | .2909 | ✅ | ❌ | ❌ 2/4 | ❌ | ❌ L-1.22 | REJECT |
| EUR_JPY | 3533 | .752 | +0.282p | 1.025 | .2869 | ✅ | ❌ | ❌ 2/4 | ❌ | ✅ | REJECT |

### 構造所見

1. **全ペア共通の時間構造**: F1/F2 (2014-2020) 負、F3/F4 (2020-2026) 正。
2. **診断 (EUR_USD 全期間 WF、報告のみ)**: EUR_USD は 4/4 fold 正
   (F1 +0.49p / F2 +0.53p / F3 +2.27p / F4 +0.55p、全期間 N=4107 EV=+1.040p PF=1.152)。
   → 新ペアの前半負けはレジーム要因ではなく **ルールの pair-specific 非転移**。
   圧縮ゲート fade の全天候性は EUR_USD 固有。
3. **USD_CHF は「2020 以降エッジ」としては強い** (F3 +6.04p / F4 +1.67p、>=2022:
   N=1994 WR .813 EV +1.96p PF 1.33、両side正、spread+0.3p 耐性あり) が、凍結 C3 に
   より REJECT。sweep_reversion EUR_GBP と同じ「直近 5-6 年集中」型。再評価するなら
   新 pre-reg (レジーム条件を仮説として事前明文化) が必要 — 本判定の覆しは禁止。
4. **時間コホート罠の注意**: >=2022 サブ期間は 4 ペア全て見栄えが良い
   (CHF +1.96p / AUD +1.67p / EURGBP +1.69p)。直近窓の数字での昇格は
   feedback_cohort_time_check / TV-favorable selection bias の再演になるため不可。

### 帰結

- 横展開による低相関セル追加は **この凍結ルールでは不成立**。EUR_USD LIVE 単体運用を継続。
- USD_CHF post-2020 仮説は別系統の新規 pre-reg 候補としてのみ存続 (user 決裁事項)。
