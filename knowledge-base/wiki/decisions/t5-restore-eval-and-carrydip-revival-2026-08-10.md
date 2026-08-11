# T5 復帰条件の評価 (= 執行せず) と carry dip v3 の dormancy 解除 実測記録 — 2026-08-10

> **rule:R3 (記録・診断)** — live パラメータ変更ゼロ。lot・tier・env・戦略コードいずれも不変更。
> 起点: `tools/prereg_trigger_watch.py` が **🔴 TRIGGERED: t5-jpy-cap-restore-price** (D1 close=158.268 < 159.50) を出力。当該 registry エントリは **T5 の lot 復帰**と **T8 carry dip v3 の dormancy 解除**の 2 つを相乗りで見ているため、両方をここで決着させる。

## 0. 結論 (先に)

| 対象 | 判定 | 根拠 |
|---|---|---|
| **T5 lot 1.0x 復帰** | ❌ **執行しない** (0.5x 維持) | pre-reg の復帰条件は **AND**。第1要件のみ成立、第2要件 (介入/当局言及の再確認) は**未確認**。かつ lot↑ は R1 = user 決裁事項 |
| **T8 carry dip v3** | ✅ **dormant → 稼働 に状態更新** | 07-31 以降 実 fill 6 件 (LIVE 2 / shadow 4)。roadmap T8 の「dormant-by-design」記述は本日付で stale |

---

## 1. T5: 復帰条件は AND であり、成立しているのは第1要件のみ

[[jpy-cap-exit-prereg-2026-06-12]] 「復帰条件」原文:

> USD_JPY が D1 close < 159.50 に回帰 **かつ** 介入観測 or 当局の 160 防衛言及が再確認された場合、lot 1.0x へ復帰 (要 KB 記録)

### 第1要件: ✅ 成立 (2026-08-03 以降)

USD_JPY D1 close (`USDJPY=X`、watch tool と同一ソース):

| 日付 | close | 判定 |
|---|---:|---|
| 2026-07-29 | 163.864 | above |
| 2026-07-30 | 163.300 | above |
| 2026-07-31 | 160.183 | above |
| **2026-08-03** | **157.582** | **BELOW ← cross** |
| 2026-08-04 | 157.529 | BELOW |
| 2026-08-05 | 157.692 | BELOW |
| 2026-08-06 | 157.600 | BELOW |
| 2026-08-07 | 158.409 | BELOW |
| 2026-08-10 | 158.269 | BELOW |

07-29 163.864 → 08-04 157.529 = **4 営業日で −633 pips**。一過性ヒゲではなく 6 営業日連続で 159.50 を下回っている。

### 第2要件: ❌ 未確認 — かつ「価格から推定してはならない」

「介入観測 or 当局の 160 防衛言及の再確認」は KB 内に記録がない (`raw/market-analysis/2026-07-31..08-10-regime.md` に介入/財務省の言及ゼロ)。Q2-2026 の MoF 日次開示は本記録時点で未公表。

> ⚠️ **cross-LOCK ハザード (本セッションで新規に特定)**
> 第2要件を「−633p の急落という価格シグネチャから介入日を推定する」形で満たすことは **禁止**。それは [[mof-intervention-forward-prereg-2026-07-24]] (台帳 family #4、🔒 LOCKED 2026-07-24) が §2.2 で凍結した識別 rule — `candidate(d)=1 ⟺ close/open−1 ≤ −Y% ∧ range(d) ≥ X × trailing-20d median range` — **そのもの**であり、**2026-04〜05 窓および現行 2026 窓の「どの日が介入日か」というラベルは同 pre-reg の genuine OOS** だからである。価格推論で T5 の第2要件を認定すれば、#4 の OOS を burn する。
>
> **運用規約 (本記録で明文化)**: T5 第2要件の認定ソースは **MoF 公式開示 / 当局の公式言及 (外部一次情報) のみ**。価格ベースの介入推定は使用不可。#4 の verdict (Q2-2026 開示着地 +10 日以内、backstop 2026-09-30) が出れば、その開示自体が第2要件の適格ソースになる。

### したがって

- **lot 1.0x 復帰は執行しない。** `JPY_CAP_EXIT_SIZE_LEVER_ACTIVE = True` (0.5x, floor 1000u) を維持。
- そもそも lot↑ は **Rule 1** であり、registry メッセージも「user 判断」と明記している。autopilot の権限外 (roadmap v2.3: R1 は個別 Rule 1 手続き + user 最終承認)。
- **user 決裁材料としての要点**: 価格は戻ったが、戻り方が「キャップが再建された」ではなく「**円高方向へ 633p 走った**」である。T5 lever が守っている 4 戦略 (`vsg_jpy_reversal` / `dt_sr_channel_reversal` / `vix_carry_unwind` / `ema200_trend_reversal`) は 160 キャップが作る人工レンジ天井に依存する MR 系であり、レンジ天井ではなくトレンドで下に抜けた現局面は**復帰の根拠にならない**。第2要件が AND で置かれていたのは、まさにこの取り違えを防ぐためである = pre-reg が設計どおり機能した事例。

### 再発防止 (アラート運用)

`t5-jpy-cap-restore-price` は type=`price_below` の単一条件しか見ないため、第1要件成立中は**毎日 🔴 TRIGGERED を出し続ける** (08-03 以降そうなっている)。本記録がその dated resolution である。以後この赤は「第2要件の外部ソース確認待ち」を意味し、価格が 159.50 を上抜けるか #4 verdict が出るまで状態は変わらない。alert fatigue で本物のトリガーを見落とす経路 ([[jpy-cap-exit-prereg-2026-06-12]] の 18 日執行ギャップと同型) を避けるため、registry の message を「第2要件は外部一次情報のみ / 価格推定は #4 LOCK 抵触」に更新した。

---

## 2. T8 carry dip v3: dormancy は解除済み、live で稼働中

roadmap v2.3 WS2 T8 は「ceiling 159.50 レジーム前提崩壊の dormant-by-design」「復帰 = D1 close<159.50」としていた。**この記述は本日付で stale** — 実測で復帰済み。

### 解除タイミングは D1 cross より早い

`strategies/hourly/usdjpy_carry_dip_accumulator.py` の天井フィルタは **H1 closed close < CEILING(159.50)** (D1 ではない)。07-31 の急落は日中に起きたため、D1 close が 159.50 を割った 08-03 より前、**07-31 の intraday** に H1 ベースで解除されている。実際、初回発火は 2026-07-31 14:03 UTC (entry 159.246)。

### 実測 fill (production API `/api/demo/trades?limit=2000`、窓 07-20 →)

| entry (UTC) | 経路 | entry | exit | pnl | close_reason | outcome | dedup_violation |
|---|---|---:|---:|---:|---|---|---|
| 2026-07-31 14:03:45 | shadow | 159.246 | 159.396 | +15.0 | SL_HIT | **WIN** | 0 |
| 2026-07-31 14:16:03 | shadow | 159.400 | 159.481 | +8.1 | SL_HIT | **WIN** | **1** |
| 2026-08-05 04:17:51 | **LIVE** (`549260`) | 157.386 | 157.676 | **+29.0** | OANDA_SL_TP | WIN | 0 |
| 2026-08-07 13:03:39 | shadow | 157.436 | 157.245 | −19.1 | SL_HIT | LOSS | 0 |
| 2026-08-07 13:04:21 | shadow | 157.488 | 157.290 | −19.8 | SL_HIT | LOSS | **1** |
| 2026-08-09 22:03:55 | **LIVE** (`573986`) | 157.842 | — | **建玉中** | — | — | 0 |

**dedup 後 (標準フィルタ `dedup_violation != 1`)**: LIVE closed **N=1 / +29.0p**、shadow closed **N=2 / −4.1p**、LIVE 建玉 1。

- 重複 2 ペア (07-31 の 13 分差、08-07 の 42 秒差) は **システムが既に `dedup_violation=1` で検出済み**であり、R2 alert 等の標準集計は最初から除外している。`COOLDOWN_BARS=12` が live で効かない既知構造 (MEMORY `project_engine_reconstruction_live_dedup_dead`) の再現ではあるが、**計測系は汚染されていない**。
- 07-31 の 2 件は `close_reason="SL_HIT"` かつ `outcome=WIN` — MEMORY `project_sl_hit_label_collision_2026_08_07` の実例 (BE/トレール利確が SL_HIT ラベルを付ける)。**本セルの評価で `close_reason` 起点の集計を使ってはならない。**

### 復帰先レジームは thesis に逆風 (開示、行動は取らない)

`raw/market-analysis/2026-08-10-regime.md`: USD_JPY = **VOLATILE**、ATR%ile(20d) **91%**、SMA20 slope **−0.0068**。EUR_JPY / GBP_JPY も VOLATILE + slope 負 = **円高方向のトレンド局面**。

carry dip v3 は **long-only の押し目買い**で、thesis は「ドリフトは上 (キャリー + コストプッシュ)」。その retreat 条件 (2) は「オイル完全沈静化で**円高転換**」。つまり本戦略は、自身の retreat 条件が示す方向のレジームへ復帰した — 下降トレンドで押し目を拾う構図であり、SL は 1.5 円 (150 pips) のテールキャップ。

**しかし pre-emptive な停止はしない**:
- 復帰後の deduped live N=1 (+29.0p)。**判断に足るデータが存在しない**。N=1 で止めるのは R2 (損失停止) の要件を満たさず、原則1 (マーケットが開いている間は攻める) / 原則4 に反する。
- 「レジームが逆風に見えるから止める」は感情/物語駆動であり、[[lesson-reactive-changes]] が禁じた型そのもの。
- → **事前規定トリガを置いて監視する**のが正しい。下記。

### 事前規定 R2 トリガ (registry `carry-dip-v3-revival-watch`、本記録で凍結)

| 条件 | アクション | Rule |
|---|---|---|
| deduped **LIVE N≥10** かつ EV<0 | lot↓ or LIVE 停止 (shadow は継続 = 原則3) | R2 (即断可) |
| deduped LIVE+shadow で **単一トレード損失 ≤ −150p** (SL 全張り付き) が 2 件 | テールキャップ実効性の R3 監査 | R3 |
| USD_JPY D1 close が **159.50 を上抜けて回帰** | 天井フィルタが再び dormant 化 — 状態を戻すだけ (アクション不要) | — |
| backstop **2026-11-30** | N<10 なら「低頻度は構造的」の再確認として state 更新のみ | — |

**判定時の必須規律 (凍結)**: (a) `dedup_violation != 1` で dedup、(b) `close_reason` ではなく `outcome` / `pnl_pips` で勝敗を取る、(c) LIVE (`oanda_trade_id != ''`) と shadow を混ぜない。

---

## 3. 変更したもの

- `knowledge-base/wiki/decisions/prereg-trigger-registry.json` — `t5-jpy-cap-restore-price` の message を第2要件の認定ソース規約込みに更新 / `carry-dip-v3-revival-watch` を新規追加
- `knowledge-base/wiki/syntheses/roadmap-v2.3-payoff-friction-repair.md` — WS2 T8 行を「dormant 監視」から「復帰済み・稼働中」へ更新
- **コード・lot・env・tier は一切変更していない**

## 4. 関連

- [[jpy-cap-exit-prereg-2026-06-12]] (T5 pre-reg 本体、復帰条件の AND)
- [[mof-intervention-forward-prereg-2026-07-24]] (#4、価格ベース介入推定の LOCK 元)
- [[roadmap-v2.3-payoff-friction-repair]] WS2 T8
- [[vix-carry-grail-removal-overlap-1000u-2026-06-15]] (T5 lever の floor 1000u 契約)
- MEMORY `project_engine_reconstruction_live_dedup_dead` / `project_sl_hit_label_collision_2026_08_07`
