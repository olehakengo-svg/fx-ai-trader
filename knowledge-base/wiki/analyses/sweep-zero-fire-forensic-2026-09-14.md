# P-S1(a) zero-fire forensic #2 — 2026-09-14 (rule:R3 診断のみ)

**Status**: 🔴 診断確定 / コード変更なし (verdict=WAITING のため live gate 不可触)
**Trigger**: `tools/ps1a_execution_check.py --json` → `zero_fire_forensic_alert: true`
(last_fire 2026-08-12T21:16:12Z、32.1 日 fire ゼロ = LOCK Withdrawal trigger 5)
**前回**: [[sweep-zero-fire-forensic-2026-08-12]] (gbp_asia rowless drop、PR #180 で修復)

## 1. 判定 JSON (2026-09-14)

```json
{"verdict": "WAITING", "detail": "unique N=9/10",
 "stats": {"row": {"n": 16, "ev_pips": 1.875, "wr": 0.75},
           "unique": {"n": 9, "ev_pips": 2.8, "wr": 0.7778},
           "spaced": {"n": 7, "ev_pips": 2.1286, "wr": 0.7143}},
 "last_fire": "2026-08-12T21:16:12Z", "days_since_last_fire": 32.1,
 "zero_fire_forensic_alert": true}
```

## 2. 結論 (2 行)

1. **シグナル生成は健全** — 供給枯渇ではない。08-20〜09-09 に **5 イベント**発生。
2. **5/5 が rowless hard block で消滅** — 分母が再び silent 枯渇している。
   ただし**主因は前回 (gbp_asia) と別のゲート 2 種**であり、うち 1 種は
   **保留中の Option B PR でも修復されない**。

## 3. 経路の健全性 (kill ではない — 戦略は稼働中)

| 検査 | 結果 |
|---|---|
| `daytrade_eurgbp` mode | ✅ running、engine_tick 0.3s、tick_counts 67 |
| strategy registry | ✅ `enabled: true` / `blacklisted: false` |
| 08-12 gbp_asia rescue | ✅ 作動 — `[SHADOW] GBP Asia bypass` を全イベントで観測 |
| candidate 生成 | ✅ 7d で n_buy=102 / n_selected=76 |

## 4. イベント台帳 (`/api/demo/evaluated-candidates`, 35d)

evaluation 行 253 → **distinct signal bar 5 件**。全件 `selected=1` / `confidence=65` /
選択 score 正 (3.18〜3.78)。**trade row 化は 0 件。**

| # | signal bar | 初回 block (SENTINEL_BLOCK_DIAG) | row |
|---|---|---|---|
| 1-2 | 2026-08-20 21:15 / 21:45 | (Render log 保持期限切れ — 未帰属) | ❌ |
| 3 | 2026-09-01 21:15 | `spread_wide(9.4pip>1.5)` → `spread_wide(8.2pip>1.5)` | ❌ |
| 4 | 2026-09-07 21:45 | `score_gate(misalign:BUY,-0.10 / -0.87)` + `spread_wide(5.2pip>1.5)` | ❌ |
| 5 | 2026-09-09 21:15 | `score_gate(misalign:BUY,-0.62)` | ❌ |

※ 各バーの 2 回目以降の `ORDER_BAR_DEDUP` は一次ブロックではない (dedup map 登録後の従属ログ)。
※ candidate table の `score` (3.38) と SCORE_GATE の `score` (-0.62) は**別量**
 (前者 = 戦略選択スコア / 後者 = 方向アラインメント)。取り違え注意。

## 5. 2 つの欠損経路

### 5-1. spread_wide — ✅ 保留中 Option B PR で修復済み
`origin/draft/ps1a-option-b-20260731` の AMENDMENT (`PS1A_SWEEP_SPREAD_CAP_PIPS = 10.0`,
`ps1a_sweep_spread_cap_skip`) は cap 超過を **live skip + shadow record** に変換し、
`spread_wide` hard block から本 cell を除外する。**分母保存は執行時に回復する。**

### 5-2. score_gate — ❌ 未修復 (frozen packet の穴)
`modules/demo_trader.py:4894-4903` は misalign 時に `_block()` + `return` = **rowless**。
bypass は `_SCALP_SENTINEL` / `_UNIVERSAL_SENTINEL` のみで、本 cell は**どちらにも不在**
(実測確認済み)。`git diff origin/main...origin/draft/ps1a-option-b-20260731` に
score_gate の変更は **0 件** — つまり **Option B 執行後も 5-2 は残る**。
帰属可能 3 イベント中 **2 件**が score_gate 由来。

## 6. ⚠️ より重大な発見 — spread 前提の falsification

pre-reg の反証チェック #2 は「OANDA EUR_GBP LATE 実勢 **1.5-3p**」を前提に
「3.5p でも +4.22p」で合格していた。**live 実測はこれを満たさない。**

research mean = **+6.22p (net 1.5p spread)** ⇒ gross ≈ 7.72p。
実測 spread `s` での含意 net EV = `7.72 - s`:

| 実測 spread | 含意 net EV |
|---|---|
| 5.2p | **+2.52p** |
| 8.2p | **−0.48p** |
| 9.4p | **−1.68p** |
| 平均 7.60p | **+0.12p (≒ゼロ)** |

**breakeven spread = 7.72p。** frozen AMENDMENT の live cap は **10.0p** であり、
**観測 3/3 の quote が live 送信対象に入る** — うち 2 つは含意 EV が負。

⇒ Option B を凍結文言どおり執行すると、**エッジが消えている摩擦帯で live 送信**する。
これは「ps 席の BT 由来 EV を live 期待値に使うな」(memory
`project_ps_capture_estimand_disjoint_2026_09_09`) と同型のリスク。

## 7. 本セッションで**やらなかった**こと (と理由)

- **live gate を一切触っていない** — verdict≠OPTION_B_EXECUTE 時の絶対規律。
- **score_gate の shadow rescue を実装しなかった** — 08-12 と同型の R3 修理に見えるが、
  rescue した行は 5.2-9.4p の摩擦帯で記録され、その pnl が **spaced EV トリガを動かし
  Option B (live 昇格) を引き起こす**。§6 の通りその帯の EV は負〜ゼロ。
  分母だけ機械的に回復させると**誤った live 昇格を能動的に招く**ため、
  修理より先に §8 の決裁が要る。
- **retire 期日の再繰り延べを提案しない** — 08-17 に一度 09-30→10-28 へ繰り延べ済み。
  2 度目を自動で積むと、**構造的な経済的失格を配管問題として恒久的に隠す**。

## 8. user 決裁事項 (2 件、いずれも Rule 1 相当)

1. **AMENDMENT spread cap 10.0p の再決裁** — breakeven 7.72p を上回る cap は
   負 EV 帯を live に通す。cap を breakeven 未満 (例 5.0-6.0p) に締めるか、
   Option C (retire) を選ぶか。
2. **score_gate を本 cell に適用し続けるか** — 適用継続なら分母は回復せず
   10-28 の retire(R2) は **配管由来**で発火する。除外するなら pre-reg の
   estimand (research は score_gate 非適用) と整合するが live gate 変更 = Rule 1。

**どちらも決めずに放置した場合の既定結末**: 2026-10-28 に unique N<5 → `RETIRE_R2_DEADLINE`。
ただしその retire は戦略の成績ではなく §5-2 の配管に起因する — 判定として無効。

## 9. 参照
- 手順書: [[sweep-reversion-ps1a-execution-runbook-2026-07-31]]
- パケット: [[sweep-reversion-ps1a-decision-packet-DRAFT]] §8.1
- 前回 forensic: [[sweep-zero-fire-forensic-2026-08-12]]
