---
title: r2_shadow_demoted_cell と Shadow 蓄積「構造的詰まり」診断 — analyst フラグの裁定
date: 2026-07-18
type: analysis
rule: R3
status: 確定 (診断のみ、挙動変更なし)
related: [[../lessons/lesson-shadow-always-emit-cleanup-2026-04-28]], [[../decisions/usdchf-1h-cell-demotions-2026-07-02]], [[../decisions/per-cell-shadow-cap-2026-04-30]], [[../learning/edge-factor-audit-2026-06-12-ema-trend-scalp]], [[../decisions/edge-cell-e1-e4-code-disable-2026-07-02]]
---

# r2_shadow_demoted_cell 診断 — 「Sentinel N 蓄積の構造的詰まり」は誤読、gate は設計どおり (2026-07-18)

## 0. 裁定サマリー

**結論: 現状維持 (裁定案 i)。gate の挙動は設計意図どおりで、原則 3 (Shadow データ蓄積を削らない) と無矛盾。**

- コード実態は **(b)**: `r2_shadow_demoted_cell` block は OANDA 送信だけでなく **shadow row の DB 書込みまで完全に止める**。
- ただし止まるのは **反証確定済みセルのみ** (静的 registry、全て N=59〜1,117 のクリーン監査で KILL 済み)。
- **現役 Sentinel セルの蓄積は生きている**: 直近 30d で shadow rows **3,239 件 (~108/日)、147 セル、59 戦略**。
- analyst report (2026-07-17-pre_tokyo 等) の「scalp 系全般で Sentinel N 蓄積が毎日足止め = 構造的詰まり」は **block カウントの誤読** (§4)。
- 将来 discovery の統計力への影響: **ゼロ〜正** (§5)。unblock した場合はむしろ shadow slot 侵食で現役セルの蓄積が減る。

---

## 1. コード実態 — (a) か (b) か → **(b) で確定**

### 1.1 primary 経路 (`_tick_entry`)

`modules/demo_trader.py` (origin/main c2bee9f7 時点):

- **L4227**: `if is_shadow_demoted(entry_type, instrument) and not _is_live_tier_exempt:`
- **L4236**: edge-cell pre-block bypass 判定 (`_edge_cell_eligible_at_pre_block`, L9057) — active EdgeCell に match し **lot>0** の場合のみ shadow 化して通す
- **L4247-4248**: 不成立なら `_block("r2_shadow_demoted_cell")` → **`return`**
- **L5859**: `trade_id = self._db.open_trade(..., is_shadow=_is_shadow, ...)` — **DB insert は gate の約 1,600 行後**

→ L4248 の `return` は L5859 に到達しないため、**shadow row は 1 行も書かれない**。

### 1.2 shadow_emit 経路 (SHADOW_ALWAYS 系の並行記録)

- **L3826-3831**: `if is_shadow_demoted(_se_entry_type, instrument): ... continue` — `_open_shadow_emit_trade` (L3855) に到達せず、こちらも **DB 書込みなし**。

### 1.3 bypass の現況

- edge-cell bypass は `DISABLED_CELLS = {"E1","E4","E8","E10"}` (`modules/edge_cell_promote.py` L107, 2026-07-02 code disable) により **registry セルと重なる cell は全て lot=0 → bypass 実質不活性**。
- 歴史上唯一の貫通 = 2026-07-02 watchdog DECREMENT 再武装バグ (E4 経由で bb_rsi_reversion×USD_JPY が **live 11 発**、本診断の 30d データでも当日 11 行 is_shadow=0 を確認)。同日修正済み (MEMORY `project_watchdog_decrement_rearm_bug`)。

### 1.4 block 対象 (静的 registry `modules/shadow_demote_registry.py`)

| 種別 | 対象 | 反証根拠 (クリーン N) |
|---|---|---|
| 戦略ごと全ペア (SHADOW_RETIRED_STRATEGIES) | ema_trend_scalp / bb_rsi_reversion / fib_reversal / sr_channel_reversal / sr_fib_confluence | N=1,117 / 780 / 638 / 584 / 453 — edge-factor audit #1〜#5 (2026-06-12〜18, rule:R2)、全セル PF 0.03〜0.84 で salvage 不能 |
| セルごと (SHADOW_DEMOTED_CELLS) | engulfing_bb×{USD_JPY,USD_CHF}, london_breakout×USD_CHF, three_bar_reversal×USD_CHF, vol_surge_detector×USD_CHF ほか (retired と重複分を除く実効 5 セル) | 2026-05-08 R2 Critical 12 cell (commit 0208ba85) + 2026-07-02 USD_CHF mode 監査 N=169 WR16.6% -416.3p (commit 794a4015) |

registry 外のセルはこの gate に**一切触れない** (`is_shadow_demoted()` は set lookup のみ)。

---

## 2. 定量実測 — 蓄積は死んでいるか

データ: 本番 API `/api/demo/trades` closed 2026-06-17〜07-18 (N=3,297、うち shadow 3,239) + Render app logs。

### 2.1 全体: Shadow 蓄積は継続している

- **3,239 shadow rows / 30d ≈ 108 行/日、147 セル、59 戦略** — 蓄積面は広く生きている。
- 週次推移 (W24→W28、ISO 週) も全体で枯れていない: 上位セル例 `engulfing_bb×EUR_USD` 14/48/31/33/31=157、`ma_regime_switch×USD_JPY` 6/19/53/24/13=115、`session_time_bias×GBP_USD` 117 など。

### 2.2 SCALP_SENTINEL メンバーのセル粒度 30d 蓄積

| 戦略 | 30d shadow N | 内訳 | 停滞原因 |
|---|---:|---|---|
| vol_surge_detector | 90 | EUR_USD 38 / USD_JPY 23 / GBP_USD 21 / USD_CHF 8(→07-02 以降 0) | **蓄積中**。USD_CHF セルのみ registry (意図的) |
| ma_regime_switch | 115 | USD_JPY 115 | **蓄積中** |
| mtf_trend_follow_scalp | 21 | USD_JPY 12 / EUR_USD 9 | 蓄積中 |
| mtf_counter_trend_scalp | 4 | USD_JPY 4 | 発火率低 (シグナル条件) |
| bb_rsi_reversion | **0** | — | **registry (T10 KILL、意図的)** |
| ma_trend_perfect / mtf_regime_*_cascade | 0 | — | **registry 外** — シグナル不成立が原因で gate は無関係 |

→ 「scalp 系全般で Sentinel N 蓄積が足止め」は**データで否定**。gate 起因のゼロは bb_rsi_reversion (KILL 済) のみ。

### 2.3 registry セルの遮断は正確に効いている (leak なし)

entry_time ベースで registry 各セルの最終流入日を確認:

| セル | 30d 内の rows | 最終 entry | demotion commit |
|---|---:|---|---|
| ema_trend_scalp × 全ペア | 0 | — | 4d1ac133 (06-12) |
| fib_reversal / sr_channel_reversal | 0 | — | 2582279e ほか (06-12) |
| sr_fib_confluence | 13 (shadow) | **2026-06-17** | 61ef87ad (**06-18**) — 遮断前日まで、以降 0 |
| london_breakout × USD_CHF | 28 | **2026-07-02** | 794a4015 (**07-02**) — 当日まで、以降 0 |
| vol_surge_detector / engulfing_bb / three_bar_reversal × USD_CHF | 8 / 4 / 2 | 2026-07-02 | 同上 |
| engulfing_bb × USD_JPY | 0 | — | 0208ba85 (05-08) |

同時に **per-cell 粒度が機能している証拠**: `engulfing_bb×EUR_USD` は同期間 157 行 (30d 最多蓄積セル)、`vol_surge_detector` は USD_CHF 以外の 3 ペアで 82 行。戦略ファミリー巻き添えは起きていない。

### 2.4 block 件数の実測 — 「件数」は tick 再発火ノイズ

- Render app logs 実測: **2026-07-17 21:22:11〜21:59:33Z の 37.4 分で `[R2_SHADOW_DEMOTE] blocked ... ema_trend_scalp x GBP_USD` が 100 件** (≈2.7 件/分、この 1 セルのみで ≈160 件/h)。同夜 `bb_rsi_reversion x USD_JPY` も 20:30〜20:49Z に複数件。最終発生は 07-17 21:59Z (週末クローズ) で、週末中はゼロ。
- 機構: block されたシグナルは trade 化されず recent_emit にも乗らないため、**同一の物理シグナルが 10〜30 秒毎の tick で何度でも再カウント**される。engine 毎 tick 再構築 (MEMORY `project_engine_reconstruction_live_dedup_dead`) の帰結。
- さらに `_block_counts` は in-memory で **deploy/再起動毎にリセット** (2026-07-18 08:11Z 実測: 再起動直後 total=0)。analyst report の「60 件超/日」「295 件」等はスナップショット時刻と deploy 間隔に依存する不安定な値。
- **含意: block 件数は「失われた N」の推定量として使えない。** 1 日数百〜数千件の block ≠ 数百件の逸失 trade。実際の逸失は「registry セルが slot/dedup 制約下で書けたはずの row 数」であり、歴史実測では ema_trend_scalp 全セル合計 ≈18 行/日、fib_reversal ≈8 行/日のオーダー (retirement 前 30d N=251)。

---

## 3. 設計意図との突合 — 現挙動は意図どおりか → **意図どおり**

設計チェーン:

1. **[[../lessons/lesson-shadow-always-emit-cleanup-2026-04-28|lesson 2026-04-28]]**: SHADOW_ALWAYS の無条件 emit が EV<0 戦略を自動的にデータ汚染源化 (4 日で -746.5p、Wilson/Bonferroni/Kelly の N に直接混入)。教訓 = **「SHADOW_ALWAYS 等の bypass 機構には必ず R2 自動 demotion gate を併設する」**。→ 本 gate はこの教訓の実装そのもの。「emit は継続し DB にも書く」設計はここで既に否定されている (書いた row が学習系に N として乗るのが汚染の定義だったため)。
2. **2026-05-08 commit 0208ba85**: `shadow_demote_registry` (R2 Critical 12 cell) + **6h alert cron `tools/shadow_promote_r2_alert.py`** (`--apply-demote` は **suggestion JSON のみ、auto-edit なし**)。ELITE/PAIR_PROMOTED live tier は exempt。→ 「自動 demotion gate + 人間 (Claude) の R2 判断で registry 追記」という半自動設計。
3. **2026-06-12〜18 edge-factor audit #1〜#5**: 戦略レベル retirement 5 件。各エントリに N・PF・learning 参照がコード内コメントで残る。
4. **2026-07-02 [[../decisions/usdchf-1h-cell-demotions-2026-07-02|USD_CHF mode 監査]]**: registry 追記時に**原則 3 を明示的に検討済み** — 「mode slot は生かす。per-cell stop であり、USD_CHF 上の他戦略の Shadow 蓄積は続く (principle 3)。再昇格は R1-only」。

**原則 3 との整合の論理**: 原則 3 が守るのは「未解決仮説の検定力」(静的*時間*ブロックで無差別に蓄積を削らないこと)。registry は時間軸でも無差別でもなく、**十分な N で解決済み (反証済み) の個別仮説の再蓄積停止**。解決済み仮説に N を積んでも検定力は増えない (§5)。よって緊張は設計時点で裁定済みであり、本診断はそれを追認する。

analyst の「毎日足止め」認識との差分は §4。

---

## 4. analyst フラグの誤読ポイント (analyst-memory 向け)

1. **block カウントの対象取り違え**: `r2_shadow_demoted_cell` で止まっているのは KILL 済みセルの墓標再発火 (tombstone re-fire) であって、現役 Sentinel のシグナルではない。現役 scalp Sentinel (vol_surge_detector 90、ma_regime_switch 115 ほか) は同じ 30d に蓄積継続。
2. **「Sentinel N=3/30 が進まない」の帰属誤り**: あれは **live 昇格用の OANDA live N** であり、その停滞原因は OANDA 転送側 (shadow_tracking 100% skip / hedge_block / direction_filter)。`r2_shadow_demoted_cell` は live 候補セルを 1 つも止めていない (registry セルはいずれも live 候補ではない)。
3. **SENTINEL_BLOCK_DIAG ラベルの罠**: bb_rsi_reversion が `_SCALP_SENTINEL` に残存しているため、その block が `[SENTINEL_BLOCK_DIAG]` として記録され「Sentinel が堰き止められている」ように見える。実体は T10 KILL 済み戦略。
4. **件数の非定常性**: §2.4 のとおり in-memory カウンタは deploy 毎リセット + tick 再発火の積であり、日次比較に使えない。

---

## 5. 統計力への定量評価 — unblock した場合の期待効果

**(A) 解決済み仮説への追加 N の情報価値 ≈ 0**
ema_trend_scalp: N=1,117、WR≈20% 帯での Wilson 95%CI 半幅 ≈ ±2.4pp。全 8 セル PF 0.03〜0.77 で、判定反転には WR が持続的に +10pp 以上シフトする必要がある — それは「別のレジームの別仮説」であり、正規手順 (R1: 365d BT + Bonferroni + pre-reg) で再提案すべきもの。受動的 shadow 再蓄積では検出設計にならない (look 無管理の事後観察になる)。

**(B) 現役仮説の検定力への影響: unblock は負**
shadow slot は per mode×pair 共有 (scalp=4、[[../decisions/per-cell-shadow-cap-2026-04-30]])。実測 2.7 シグナル/分の ema_trend_scalp×GBP_USD を再開放すると GBP_USD scalp pool (現在 8 現役戦略が 30d で engulfing_bb 78 / london_breakout 70 / vol_momentum_scalp 63 行等を蓄積) の slot を dead セルが恒常占有し、**現役セルの N 蓄積レートを直接下げる**。fib_reversal 単独で retirement 前 30d -321.7p の bleed も再開する。
→ 原則 3 の目的 (discovery の statistical power) に対して、**現行 gate は保護、unblock は毀損**。

**(C) 「emit 継続 + is_shadow=1 + 学習除外フラグ」分離案 (裁定案 ii) の評価 → 却下**
- 除外を保証するには全 consumer (cell_edge_audit / Wilson / Bonferroni n_test_eff / Kelly / R2 alert cron / BT 突合) にフラグ対応が必要 — lesson 2026-04-28 が「汚染源」と定義した経路の再導入で、フラグ漏れ 1 箇所が即汚染。
- slot 侵食 (B) はフラグでは解決しない (別枠 slot を作ればメモリ・DB 容量・監査ノイズが増えるだけ)。
- 得られるのは (A) で価値 ≈0 の N。**コスト > 便益 が数量的に明白。**

**残余スコープ (既知として明文化)**: SHADOW_RETIRED_STRATEGIES は将来追加ペアも全遮断する。よって例えば ema_trend_scalp×新ペアの仮説は永久に受動蓄積されないが、これは leak 封鎖 (daytrade_1h_usdchf Phase B-1 slot 経由の漏れ) の意図的コスト。scalp 幾何そのものが摩擦算数で死んでいる (gross EV +0.5〜0.6p vs friction 1.2〜1.7p) ため、ペアを変えても仮説は復活しない。再挑戦は R1 手続きで registry から外すのが正規経路。

---

## 6. 裁定と提案 (実装は本コミットに含めない)

**裁定: (i) 現状維持。** gate は lesson 2026-04-28 の要求どおりに機能し、原則 3 と矛盾しない。「構造的詰まり」は存在しない。

観測性の改善提案 (別タスク、いずれも挙動非変更の R3 候補):

1. **analyst report 生成側の注記**: `r2_shadow_demoted_cell` を「resolved-cell tombstone re-fire (期待値: 高頻度・無害)」として別枠表示し、Sentinel 蓄積の議論から機械的に除外する。analyst-memory に §4 の 4 点を恒久記載 → 毎日の誤警報ループを止める。
2. **`_SCALP_SENTINEL` から bb_rsi_reversion を除去** (cosmetic): SENTINEL_BLOCK_DIAG の誤ラベル根絶。`_sentinel_score_bypass` / `_is_shadow_eligible_full` の参照があるため tests (`test_edge_cell_pre_block_bypass.py` 等) の green 確認つきで別コミット。
3. (任意) `[R2_SHADOW_DEMOTE] blocked` ログの per-cell rate-limit (例: 15 分に 1 回) — Render ログ量削減のみが目的。

再昇格の正規経路 (現行どおり): registry からの削除は **R1** (365d BT + Bonferroni + pre-reg LOCK)。エビデンス: registry 各エントリのコメント + `wiki/learning/edge-factor-audit-2026-06-12-*.md`。

## 7. 検証ログ

- コード参照: `modules/demo_trader.py` L3826/L4227-4248/L5859、`modules/shadow_demote_registry.py`、`modules/edge_cell_promote.py` L107、`app.py` L13456 (`/api/demo/block-counts`)
- データ: `/api/demo/trades` closed 30d N=3,297 (2026-07-18 08:0x UTC 取得)、Render logs (srv-d6va1of5r7bs73en10vg) text-filter `R2_SHADOW_DEMOTE`
- git 考古学: 0208ba85 (05-08 registry 導入) / 4d1ac133・3f5ac941・2582279e (06-12) / 61ef87ad (06-18) / 794a4015 (07-02)
