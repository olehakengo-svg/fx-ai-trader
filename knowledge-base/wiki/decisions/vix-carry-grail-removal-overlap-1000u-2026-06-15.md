# vix_carry_unwind: GRAIL London 経路撤去 + Overlap pilot 1000u 固定 (2026-06-15)

- **Rule**: R2 (lot↓ / cell demote — fast & reactive)
- **判定**: user 決裁 (2 質問とも推奨を選択)
- **commit**: (この doc を含むコミット)
- **動機**: データ駆動 (Live 実測 + 5/13 pilot の自己矛盾検出)

## 背景 — user 質問「LIVE の lot は全部 5000 では？ でも vix は 1000」

実コード + Render 本番 `/api/oanda/live` / `/api/oanda/audit` で確認した結果、
`vix_carry_unwind` は **session ごとに 2 経路・異サイズ**で LIVE 発火していた:

| 経路 | 発火条件 | 昇格ソース | サイズ (現状) |
|---|---|---|---|
| **Overlap pilot** (公式, 5/13) | UTC 12–16 | `_PAIR_PROMOTED` + `_PAIR_SESSION_FILTER={"Overlap"}`, 5/21 1.0x 例外 | **5000u** (cascade→FLAT) |
| **GRAIL** (旧, 4/25) | UTC 7–11 London × range_tight × squeeze | `_GRAIL_CANDIDATES` | **1000u** (forced, FLAT の後段で上書き) |

user が見た 1000u は **GRAIL 経路 (London)**。2026-06-15 の London fills は
hour=8 で +1.3p / +1.6p / **−9.0p** / open。

## 核心の発見 — GRAIL が pilot の demote 判断を黙って延命

5/13 Overlap pilot (`vix-overlap-pilot-prereg-2026-05-13.md`) は **London を
負けセルとして明示 demote** し (`London 0/2 + Asia 5 が aggregate demote 駆動`)、
vix を **Overlap-only に制限**した。

しかし旧 GRAIL 経路 (4/25) は `_PAIR_SESSION_FILTER={"Overlap"}` を bypass して
**London×squeeze (hour 7-11) で発火し続けていた**。= pilot 自身の session 制限を
構造的に無効化。2026-06-15 の London 損 (−9.0p SL 含む) は pilot の負けセル仮説と整合。

加えて、5/21 の「1.0x 意図的例外」は **FLAT (6/2) 導入前**の判断であり、
"1.0x" が 5000u を意図していたわけではない。FLAT が Overlap を黙って 5000u に
膨らませていた (Live 累計 N=5、Rule1 N≥30 に遠く未達)。

## 決定 (2 点)

1. **`vix_carry_unwind` を `_GRAIL_CANDIDATES` から除外** — London×squeeze 発火を
   完全停止。`_check_grail_filter` の Grail #2 ブロックも撤去 (到達不能化 + 誤読防止)。
   vix は **Overlap pilot のみ**で発火。
2. **Overlap pilot を 1000u 固定** — `modules/demo_trader.py` に明示 fixed-lot
   ブロック (`VIX_CARRY_MIN_LOT`, carry_dip / sweep と同型) を追加し、FLAT bypass
   リストにも `vix_carry_unwind` を追加。cascade / FLAT に関係なく 1000u。

## 実測根拠 (Live 全履歴 — oanda_audit `sent` × OANDA 約定突合)

vix LIVE fill は全期間 **N=5、全て 1000u**:

| 日時 (UTC) | session | 経路 | 結果 |
|---|---|---|---|
| 05-20 15:08 | Overlap | (FLAT 前, pilot) | TP +30.2p |
| 06-15 08:19 | London | GRAIL | SL +1.3p |
| 06-15 08:21 | London | GRAIL | SL +1.6p |
| 06-15 08:22 | London | GRAIL | SL −9.0p |
| 06-15 08:33 | London | GRAIL | OPEN |

5/21「1.0x 昇格」は実は **一度も 5000u で発効していない** (FLAT 導入後の Overlap
fill が未発生、London は全て GRAIL で 1000u)。よって「未テストの 5000u」を避け、
観測済みの 1000u に固定するのが保守的かつ Rule1 整合。

## 撤回 / 昇格条件 (pre-reg)

- **5000u 昇格**: Overlap pilot で Live N≥30 ∧ EV>0 を確認 → 別途 Rule1 pre-reg
- **完全 demote**: Overlap Live N≥10 ∧ (EV<0 ∨ Wilson_lo<34.4%) → `_PAIR_PROMOTED`
  から除外 (既存 watchdog `volume_live_promotion_watchdog.py` と整合)
- watchdog は既存のまま (Live N≥10 EV<0 で自動 demote)

## 横展開メモ (別件)

GRAIL は他に `ema200_trend_reversal` / `vol_surge_detector` / `ny_close_reversal`
を保持。いずれも `_PAIR_PROMOTED` 非所属のため今回の session-filter 矛盾は無いが、
将来これらが pair promote された場合は GRAIL が同様にサイズ/session を上書きしうる。
hardening (GRAIL が already-promoted を上書きしないガード) は未実装 — follow-up 候補。
