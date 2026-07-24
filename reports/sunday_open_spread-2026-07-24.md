# Sunday open 実スプレッド実測 — weekend_gap family #3 R1 step (i) (2026-07-24)

**目的**: OOS confirm gate (c) の stressed friction 仮定 (通常 RT x3) を OANDA live feed の歴史 BA candle 実測で検証・置換する ([[weekend-gap-oos-prereg-2026-07-24]] §9 R1 手続き 1)。
**測定**: 直近 12 週末 (2026-05-03 〜 2026-07-19、全て US 夏時間期) x EUR_USD/USD_JPY/AUD_USD、M1 price=BA、spread = ask.o − bid.o、RT = spread + slippage 0.5p (KB friction table 準拠)。
**read-only**: GET `/v3/instruments/:i/candles` のみ。live 変更・注文送信ゼロ。pre-reg 文書は不変更。
**ツール / raw**: `tools/sunday_open_spread_measure.py` / `bt-results/sunday_open_spread-2026-07-24.json`
**データ品質**: 36/36 pair-weekend 全取得、skip 0。全週末で最初の complete M1 バー = **21:04 UTC** (OANDA の実開場プリントは 21:00 open の約 4 分後で一定)。

## 1. サマリ表 (spread は pips、p50/p90 = 週末横断)

| pair | 通常RT(凍結) | 火曜実測 spread p50 | 実測通常RT | 3xRT仮定 | 初バー spread p50/p90 | +15m | +30m | +1h | +2h | +4h |
|---|---|---|---|---|---|---|---|---|---|---|
| EUR_USD | 2.0p | 1.6p | 2.1p | 6.0p | 4.45/9.89 | 5.80/7.58 | 5.20/7.00 | 1.80/2.95 | 1.60/1.69 | 1.60/1.70 |
| USD_JPY | 2.14p | 1.55p | 2.05p | 6.42p | 7.05/10.00 | 6.85/10.00 | 6.70/10.00 | 2.05/2.79 | 1.65/1.89 | 1.45/1.60 |
| AUD_USD | 2.5p | 1.3p | 1.8p | 7.5p | 6.45/15.00 | 5.40/11.60 | 4.20/6.93 | 1.60/2.29 | 1.40/1.40 | 1.30/1.30 |

- **通常 RT テーブルの検証**: 火曜 12:00 UTC 実測 + 0.5p slip = EUR 2.1p / JPY 2.05p / AUD 1.8p ≒ 凍結値 (2.0/2.14/2.5)。**AUD_USD の理論仮置き 2.5p は保守的 (実測 1.8p)** — qualify 閾値 (10xRT、凍結) の再計算は pre-reg §2 で禁止のため不変。
- **quoted spread は schedule cap に張り付く**: 初 1h の観測値は JPY 10.0p / AUD 15.0p / EUR 10.0p の上限に繰り返し到達 — OANDA は週明け初 1h に固定の wide スプレッドスケジュールを敷いている挙動。

## 2. 正規化タイミング — 減衰ではなく 22:00 UTC の段差

sustained normalization (open からの分数、[t, t+15m) median が閾値以下になる最初の t、p50/p90 across 12 weekends):

| pair | spread ≤ 3xRT−slip 閾値 | ≤ 1.5x通常 | ≤ 2x通常 | ≤ 3x通常 |
|---|---|---|---|---|
| EUR_USD | 4m/35m | 51m/67m (max 78m) | 50m/53m | 25m/49m |
| USD_JPY | 29m/50m | 54m/81m (max 85m) | 50m/57m | 47m/50m |
| AUD_USD | 0m/25m | 50m/59m (max 68m) | 48m/52m | 16m/49m |

分足の直接検査 (複数週末) で確認: **spread は初 1h 全体で高原状 (4〜8p、decay ほぼ無し) を維持し、22:00〜22:01 UTC (Sydney 流動性開始) に 1.5〜2p へ一段で崩落する**。つまり「X 分待って spread が下がる」型ではなく、**21:04〜22:00 は何分待ってもほぼ節約ゼロ、22:01 以降は即・通常圏**という二値構造。

- **X ≈ 57 分 (= 22:01 UTC)、Y ≈ 1.1〜1.3x 通常** — これが「entry を open 直後 X 分遅らせれば spread が通常 xY に収まる」の実測解。
- 全ペア・全 12 週末で 4h 以内に全閾値到達 (never=0)。+2h/+4h (= arm B の exit 時刻) は完全に通常スプレッド。

## 3. 検証対象の判定: stressed 3x 仮定は保守的だったか

**時間軸では YES、entry バーの水準では NO (特に USD_JPY)**:

| pair | 初バー実測 RT mean/p50/p90 | 3xRT 仮定 | 仮定超過 | per-pair EV: gross@4h − 実測meanRT (vs 仮定net) |
|---|---|---|---|---|
| EUR_USD | 6.19 / 4.95 / 10.39p | 6.0p | **4/12 週末** | 13.22 − 6.19 = **+7.03p** (仮定 +7.22p) |
| USD_JPY | 8.06 / 7.55 / 10.50p | 6.42p | **10/12 週末** | 14.55 − 8.06 = **+6.49p** (仮定 +8.13p) |
| AUD_USD | 8.40 / 6.95 / 15.50p | 7.5p | **5/12 週末** | 18.29 − 8.40 = **+9.89p** (仮定 +10.79p) |

- **USD_JPY は中央値でも仮定超過** (7.55p > 6.42p、12 週中 10 週で超過) — 3x 仮定は entry バーに関して underestimate。
- 一方、**exit 脚 (+4h) は通常スプレッド**のため、round-trip 全体に stressed RT を課した gate (c) の会計は exit 側で過大 — 半スプレッド分解 (0.5x open spread + 0.5x exit spread + slip) では実効 RT はさらに ~1.5〜3p 軽い。上記は task 規定の保守形 (full open spread + 0.5p) で統一。

### EV 再計算 (arm B pooled、OOS N 構成 46/65/66 加重)

| RT 置換 | pooled RT | stressed-net 再計算 (gross +15.60p) |
|---|---|---|
| 凍結仮定 (verdict) | 6.56p | +9.04p |
| **実測 mean (初バー)** | **7.70p** | **+7.90p** |
| 実測 p50 | 6.65p | +8.95p |
| 実測 p90 (tail 週末) | 12.34p | **+3.26p** |

**結論: 実測置換後も arm B の正 EV は保存される (mean +7.90p、tail p90 でも +3.26p > 0)。gate (c) の PASS 方向は実測で覆らない。** ただし仮定より ~1.1p 重く、tail では ~6p 重い。

### 留保 (stage-2 で扱う)

1. **slippage 0.5p は通常市場の仮定** — 21:04 の薄い板での成行 slippage は candle からは測定不能で、実際は 0.5p を上回る可能性が高い (実測 RT は下方バイアス)。
2. 12 週末は全て「平穏な週末」(2026-05〜07)。gap qualify (≥10xRT) する news-weekend の open spread は cap 側 (10/15p) に寄る可能性 — p90 行 (+3.26p) をそのケースの参照とする。
3. 測定は OANDA quoted spread であり、他社流動性とは独立 (live 執行が OANDA である以上これが正しい母集団)。

## 4. 執行設計への示唆 (stage-2 pre-reg の入力)

BT の estimand は「Sunday open 初バー Open からの 4h 固定ホライズン」で凍結済み・OOS 再接触は禁止 (§9) のため、entry 遅延変種を OOS で再検証することはできない。選択肢:

- **(a) 成行 @ 初バー + spread ゲート (推奨 primary)**: estimand に忠実。EV は実測 RT で +7.90p。執行ルールとして「発注時 quoted spread > cap (例: 10p = 実測 p90 水準) なら当該週末 skip」を stage-2 で凍結 — forward ルールであり OOS mining ではない。AUD_USD の 15p cap 張り付き週末を自動排除できる。
- **(b) 指値 @ BT 参照価格 (Sunday open)**: spread crossing を払わず estimand と同一価格 — ただし fill 率が未知 (fade 方向ゆえ gap 続伸時のみ fill する adverse selection もあり)。前向き shadow で fill 率実測が必要。
- **(c) entry を 22:01 UTC へ遅延 (X=57m)**: friction は通常圏 (Y≈1.2x、RT≈2.2p) になるが **estimand が変わる** — explore の fill dynamics は t-half 中央値 1〜2h であり、初動 1h の放棄は gross +15.6p の相当部分を放棄しうる。OOS 再走は禁止のため、採用するなら前向き検証 (shadow) が必須。
- 中間遅延 (15/30/45m) は **無意味** — spread 高原のため節約ほぼゼロで初動だけ失う。設計空間から除外してよい。
- exit (+4h = 01:04 UTC) は通常スプレッドで執行可能 — exit 側の stress 会計は不要。

**stage-2 への推奨**: primary = (a) 成行 + spread cap 凍結。並行して (b) の fill 率を前向き計測 (発注せず板気配の記録のみでも近似可)。(c) は shadow 検証枠が取れる場合のみ。

## 5. R1 step (i) の充足

- 要求 ≥8 週末 → **12 週末 x 3 ペア実測完了** (遡及取得が可能だったため前向き蓄積は不要)。
- 3x 仮定の実測置換 → §3 の EV 再計算で完了。**正 EV 保存を確認 (mean +7.90p / p90 +3.26p)**。
- 次段 = R1 step (ii) 執行設計 pre-reg (stage-2) → §4 を入力とする。step (iii) user 最終承認は据え置き。
