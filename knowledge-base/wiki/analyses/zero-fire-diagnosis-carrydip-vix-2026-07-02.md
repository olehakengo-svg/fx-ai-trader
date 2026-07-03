# Zero-Fire 診断: usdjpy_carry_dip_accumulator + vix_carry_unwind Overlap pilot (2026-07-02)

**Status**: 診断完了 (rule:R3 — 構造診断、tier/lot 変更なし)
**Scope**: roadmap v2.2 T7 + 2026-07-02 派生タスク。M1 (clean live PnL>0) の前提となる 2 つの LIVE 候補が発火ゼロである原因の特定。
**成果物**: 本レポート + qualifying-bar logging 実装 (T7) + fix 提案 (提案のみ、実施は user 決裁)

---

## TL;DR

| 対象 | 根本原因 | バグか? |
|---|---|---|
| carry_dip live fill 0 (06-12〜) | **CEILING=159.5 静的壁が市場に取り残された** (USDJPY は 06-01 以降 159.5 上抜け、現在 161-162.8)。06-03 以降の RSI dip cross **22 回全てが ceiling block** → emit 自体ゼロ | バグではない。**レジーム前提の失効** |
| vix Overlap pilot live fill 0 (06-18〜) | **Overlap 窓 (UTC12-16) にシグナル自体が来ていない**。50 日間で Overlap シグナル 4/54 件 (7.4%)、06-18 以降は 0 件 (期待値 ~1.1 件、Poisson 整合 P≈0.33) | バグではない。**設計上の starvation** |
| (副次) `_promotion_allows_live` 未実装疑い | **解消**。その名の関数は存在せず (コメント内の呼称のみ)、実体は `_is_promoted` 内 (demo_trader.py:8561-8578) で**実行時に評価されている**。本番挙動でも確認済み | 疑い晴れ |
| (副次・新発見 P1) Aggregate Kelly Gate | `kelly_criterion` が `full_kelly=max(0,·)` でクリップ (stats_utils.py:206) するため、gate 条件 `_agg_kelly < 0` (demo_trader.py:6203) は**構造的に発火不可能な死にゲート**。現在 aggregate edge=-0.36 でも素通し | **バグ (eligible vs effective 型)** |
| sweep_reversion_eurgbp_late 発火 0 (全期間) — §3 (2026-07-02 午後追加) | 戦略は本番同一フィードで **4 回 emit していた**が、**v9.1 HTF Hard Block (htf=bear→BUY 全排除) が記録経路より前に削除**。逆張り BUY は発火瞬間が構造的に bear = kill 率 ~100% | **構造バグ (BT/本番統一違反 + 4原則#3 違反)** |

---

## 1. usdjpy_carry_dip_accumulator

### 1.1 観測事実 (一次データ)

- 本番 DB (`/api/demo/trades?mode=daytrade_1h&date_from=2026-06-08`): daytrade_1h 全体で 4 trades (全て donchian_momentum_breakout)。**carry_dip は shadow 含め 0 行** → OANDA 送信段以前、strategy evaluate 段で emit ゼロ。
- 配管の無罪確認: daytrade_1h thread は稼働中 (donchian が記録されている)。`USDJPY_CARRY_DIP_LIVE_ENABLE=1` 済 (user 確認)。live routing (`_usdjpy_carry_dip_live_eligible` → shadow gate bypass + MIN lot 1000u) はコード上無傷 — ただし**一度も production で通っていない未実証経路**。

### 1.2 qualifying-bar 独立計算 (yfinance USDJPY=X 1h, 2026-05-25〜07-02, 677 bars)

戦略と同一の Wilder RSI(14) で再計算:

| 指標 | 値 |
|---|---|
| RSI cross-below-45 イベント | **28 回** |
| うち qualifying (close < 159.5) | **6 回 — 全て 05-28/05-29** (LIVE enable 前) |
| うち ceiling block (close ≥ 159.5) | **22 回 — 06-03 以降の cross は全滅** |
| close < 159.5 だったバー比率 | 18% (全て 05 月末) |
| 価格レンジ | min 158.84 (05月末) → max 162.79、現値 161.19 |

**結論: 発火期待値は市場条件と整合してゼロ。** トリガー (RSI dip) は月 20 回超のペースで発生しているが、CEILING=159.5 が 100% 遮断している。

### 1.3 クオンツ的含意 — レジーム前提の失効

戦略 thesis は「155-160.7 高位レンジ、160 = MOF/BOJ 介入壁、壁直下 (159.5+) では買わない」。現実は **06-22 以降 161 台、07-01 以降 162 台 = 旧介入壁 160.7 を上抜けて定着**。つまり:

1. 「壁に撃たれるのを避ける」という ceiling の防御意図は、壁自体が破られた今、**防御ではなく全遮断**として作用している。
2. 一方で「ceiling を 162.5 に上げる」等の単純追随は、**介入壁がどこに再設定されたか不明なまま撃たれる位置に入る**ことを意味し、thesis の再検証なしにはカーブフィッティング (数字の追認) になる。
3. up-drift 因果 2 本 (キャリー金利差 / コストプッシュ円売り) 自体は価格上昇と整合しており、retreat 条件 (BOJ タカ派転換 / オイル沈静化 / 累積 DD) には**未該当**。壊れたのは「レンジ上限の位置」の仮定のみ。

### 1.4 実装済み (roadmap T7): QUALBAR logging

`strategies/hourly/usdjpy_carry_dip_accumulator.py` に qualifying-bar telemetry を実装 (本コミット):

- RSI cross 成立バー (=発火期待値の分母) ごとに 1 行、`QUALBAR` マーカーで ceiling/blackout/dedup/cooldown の pass/fail と最終 emit 判定を INFO log。
- 同一 closed bar への 60s polling 再入では重複 log しない。トリガー無しバーは log しない (スパム防止、頻度 ≲1 行/日)。
- Render ログで `grep QUALBAR` すれば「7d 0-fire が市場由来か filter 由来か」を以後は即答できる。
- テスト: `tests/test_carry_dip_qualbar_logging.py` (4 cases, TDD RED→GREEN)。

### 1.5 Fix 提案 (提案のみ — tier/lot/param 変更は行っていない)

| # | 提案 | Rule | 備考 |
|---|---|---|---|
| P-C1 | **thesis 再検証タスク**: 現水準での介入壁仮説・up-drift 因果の再評価。結論に応じて (a) ceiling 再設定 + pre-reg、(b) 戦略 retire、のいずれかを user 決裁。**→ 決裁用データ整備済み (2026-07-02): [[carry-dip-ceiling-reeval-2026-07-02]] (推奨: hold + MOF/BOJ 証拠待ちで pre-reg)** | R1 (新パラメータ = 実質新戦略) | ceiling は「介入壁の位置」という**外生変数**であり、BT フィットでなく政策情報で決めるべき |
| P-C2 | 静的価格レベル参照 param (CEILING 型) に **staleness monitor** を追加: 直近 N 日 close が全て level 超過ならアラート | R3 | 教訓「固定値はマルチTF/レジームで必ず壊れる」の一般化。lesson 化候補 |
| P-C3 | HourlyEngine `_shadow_always` に carry_dip を追加し、score 競合時の silent drop を防ぐ | R3 | 現状 `select_best` に負けると記録ゼロ (carry_dip score ≤5.0 vs 他戦略)。原則 3 (Shadow 蓄積) と整合 |

---

## 2. vix_carry_unwind × USD_JPY Overlap pilot

### 2.1 filter 実行時評価の検証 (タスクの主質問)

- `_promotion_allows_live` は**関数として存在しない** (grep 一致は demo_trader.py:7867 のコメント 1 箇所のみ)。pre-reg 文書 (vix-overlap-pilot-prereg-2026-05-13.md) がこの名前で仕様を書いたが、実装は `_is_promoted` 内にインライン化された (demo_trader.py:8561-8578)。**「定義のみで runtime 未評価」の疑いは晴れ** — `_PAIR_PROMOTED` 分岐内で `_PAIR_SESSION_FILTER` を `datetime.now(timezone.utc).hour` に対して毎回評価している。
- 本番挙動での裏取り: 07-02 の London シグナル 19 件 / 06-26 Asia 1 件は全て `is_shadow=1`、oanda_audit `block_reason=shadow_tracking` — **窓外→shadow が正しく機能**。06-18 GRAIL 撤去以降、窓外 live リークは 0 件 (30d の live fill 10 件が全て UTC08-09 リークだったという個票検証とも一致 — それらは 06-12/06-17 の GRAIL 経路)。
- ⚠️ 注意 (evaluation order): `_is_promoted` は bridge mode が `live`/`sentinel` だと session filter **より前に** return True する (demo_trader.py:8553-8554)。現在 vix は `auto` なので実害なしだが、手動で mode=live を立てると pilot の session 制約が黙って外れる構造。

### 2.2 発火ゼロの根本原因: シグナル分布と Overlap 窓のミスマッチ

本番 DB、05-13 (pilot 開始)〜07-02、vix_carry_unwind × USD_JPY 全 54 シグナル (shadow 含む) の UTC hour 分布:

| Session | Hours | N | 比率 |
|---|---|---|---|
| Asia | 03-04 | 2 | 3.7% |
| **London** | 06-09 | **34** | **63.0%** |
| **Overlap (pilot 窓)** | 14-15 | **4** | **7.4%** |
| NY | 17-21 | 14 | 25.9% |

- ATR(5/20) 比という vol-spike プロキシは **London オープンと NY 後半に構造的にクラスタ**し、Overlap (UTC12-16) はシグナル砂漠。
- 06-18 以降 14 日間の Overlap シグナル期待値 = 4/50d × 14d ≈ **1.1 件**。観測 0 件は Poisson P(0)≈0.33 で**異常なし**。
- pre-reg の期待レート (BT Overlap cell N=22/365d ≈ 月 1.8 件) とも観測レート (月 ~2.4 件) は整合。**「その月 2 件が live になるか」が未実証**なだけ。

### 2.3 ⚠️ 未解決の残留疑義: pilot 経路の live 実証は N=1 のまま

Overlap 窓内シグナル 4 件の帰結:

| 時刻 (UTC) | 帰結 | 説明 |
|---|---|---|
| 05-20 15:08 | **LIVE** (+30.1p) | pilot 経路の唯一の live 実証 |
| 05-28 14:22 | shadow | 直前 14:20 に同一 instrument (xs_momentum_rsi) が open → recent_emit/mode-limit 系で説明可能 |
| 05-28 14:31 | shadow | 9 分前の vix 自身が open、`dedup_violation=1` → dedup で説明可能 |
| 05-29 15:02 | **shadow (原因未特定)** | audit は `shadow_tracking` のみ。当時 open position なし。GRAIL 撤去前の旧コード下の事象であり深追いは費用対効果低 |

**含意**: GRAIL 撤去後の現行コードで「Overlap 窓内シグナル → live fill」を通した実績はゼロ。session filter の「窓外を止める」側は本番実証済みだが、**「窓内を通す」側は 05-20 の 1 件 (旧コード) のみ**。次の Overlap シグナル発生時が事実上の本番テストになる。

### 2.4 (副次・P1) Aggregate Kelly Gate は死にゲート

- v9.0 SHIELD (demo_trader.py:6198-6216) は `_get_aggregate_kelly() < 0` で非 sentinel の OANDA 転送を全ブロックする設計。
- しかし `_get_aggregate_kelly` は `stats_utils.kelly_criterion` の `full_kelly` を返し、そこで **`max(0, full_kelly)` にクリップ済み** (stats_utils.py:206) → 戻り値は負になり得ず、**gate は一度も発火できない**。
- 現在の aggregate: edge=-0.3617, WR=48.2% (`/api/risk/dashboard`) — 設計意図どおりなら**今まさにブロックすべき状態**だが素通し。
- 教訓ページ既存パターン: 「資格 (eligible) と実状態 (effective) を区別する」の再発事例。
- **interplay 警告**: これを単純修正すると、vix Overlap pilot は非 sentinel (`_is_pair_boosted=True` で `_is_sentinel=False`) なので **aggregate edge<0 の間 pilot の live fill も全ブロック**される。「pilot を活かすなら edge-cell 型 bypass を pilot にも与えるか」を修正と同時に決裁する必要がある。単独 fix は pilot を静かに殺す。

### 2.5 Fix 提案 (提案のみ)

| # | 提案 | Rule | 備考 |
|---|---|---|---|
| P-V1 | **pilot 判定タイムラインの明文化**: 期待レート月 ~2 件 → demote gate (Cell-Live N≥10) 到達に **~5 ヶ月**。この速度を許容するか、pre-reg 修正 (窓拡張 or 判定 N 引下げ) を出すかの user 決裁 | R2 判断は user | 窓拡張は「負けセル London を再導入しない」制約付き (06-15 決裁と矛盾しないこと) |
| P-V2 | Kelly gate クリップバグ修正 (`kelly_criterion` に raw 値を追加 or gate 側で raw 計算) + **pilot との interplay を同一 pre-reg で決裁** | R3 (バグ) + R2 (interplay) | §2.4。単独 fix 禁止 |
| P-V3 | `_is_promoted` の mode=live/sentinel 早期 return が session filter を bypass する構造に guard + 回帰テスト。**→ 実装済み (2026-07-02, rule:R3)**: `_promotion_allows_live()` を method として抽出 (pre-reg 文書の呼称をそのまま実装) し、手動昇格経路にも適用。filter 未登録戦略の手動昇格は従来どおり無条件。現本番は mode=auto のため当日挙動デルタなし | R3 | §2.1 ⚠️。tests/test_session_filter_promotion_guard.py 17 cases (誤帰属防止 _is_promoted_ex 4 cases 含む) |
| P-V4 | session filter 窓外 block の観測性。**→ 実装済み (2026-07-02, rule:R3)**: audit `block_reason="shadow_tracking(session_filter_out)"` (prefix 互換) + `_block_counts` に `{mode}:session_filter_live_block` 増分 + drift guard を startswith 対応 | R3 | 05-29 型の「窓内 shadow 原因不明」を今後は即答可能に |

---

## 3. sweep_reversion_eurgbp_late (スコープ追加 2026-07-02 午後、cross-session 依頼)

### 3.1 観測事実

- 本番 DB: **全期間 (06-12 登録以降) で shadow 含め 0 行**。daytrade_eurgbp thread は稼働中 (mode 内 06-01 以降 110 trades、eurgbp_daily_mr 35 / trendline_sweep 34 ほか)。
- 本番データフィードは **Massive 15m** (Render ログ `[Massive/15m] EURGBP=X 4174本取得` 毎tick) — research と同源で、LATE 窓 (21-24 UTC) のバーも forming bar 込みで供給されている。

### 3.2 再現実験 (本番同一コード + 本番同一フィード)

**(a) strategy 単体**: `fetch_ohlcv_massive("EURGBP=X","15m",60)` + 本番 `SweepReversionEurgbpLate.evaluate()` のバー毎リプレイ (closed_idx=-2 semantics) → **06-12 以降 4 回 emit**: 06-15 21:15 / 06-25 21:00 / 06-30 21:00 / 07-01 21:00 (score 3.48-5.00)。**戦略は無罪** (research 期待 3-4回/月とも整合)。

**(b) pipeline 全体**: 同スナップショットで `compute_daytrade_signal()` を直接実行 →

```
[DaytradeEngine] 1候補: sweep_reversion_eurgbp_late    ← engine は正しく候補化
[DTE] HTF Hard Block: 1 candidates blocked (htf=bear)  ← ここで消滅
live_promote_emits: []                                  ← side-channel にも入らない
```

### 3.3 根本原因: v9.1 HTF Hard Block が逆張り BUY を構造的に全滅させる

- app.py:2609-2633 の HTF Hard Block は htf_agreement=bear のとき **BUY 候補を候補リスト段階で除外**する。除外は select_best・`split_live_promote_emits`・shadow_emit **全ての記録経路より前** → trade row も counter も残らない完全 silent drop。
- 本戦略は「96 bar 安値の sweep を買う」**逆張り**なので、**発火する瞬間はほぼ定義上 HTF が bear** — kill 率は構造的に ~100%。
- 裏取り: H4/D1 EMA9-21 は 06-25 / 06-30 / 07-01 の 3 時点で**両方 BEAR** (block 確実)。06-15 のみ H4 BULL / D1 BEAR (mixed — 歴史時点の htf_agreement は再現不能のため断定せず)。
- **観測不能だった理由**: HTF Hard Block のログは `logging.info` で、Render に届くのは print 系のみ → 20 日間誰にも見えなかった。**本コミットで print 化 + blocked entry_type 明示** (`grep HTF_HARD_BLOCK` で追跡可能に)。

### 3.4 クオンツ的含意 (3 つの原則違反)

1. **BT/本番統一違反**: 12y grid pre-reg (m=1,728 唯一の Bonferroni 生存 cell、z_bonf=4.02, N=543) は **HTF gate なし**で検証された。本番だけが追加 filter を適用 = 検証済みエッジと別物を運用し、production N を 0 に固定。
2. **4原則#3 違反**: HTF Hard Block は shadow 記録より前で殺すため、**Shadow データ蓄積まで遮断** — 「静的時間ブロックは Shadow に適用しない」思想の HTF 版逸脱。
3. **「中央 gate が登録済み LIVE 例外を黙って無効化」の 7 例目** (select_best bottleneck ×6 → HTF hard block)。06-02 対策 (`_COUNT_GATE_BYPASS_LIVE_EXCEPTIONS`) は当時の戦略のみで、06-12 世代 (sweep/hull/carry_dip) は `_SILENT_DROP_DIAG_TYPES` にも未登録 = silent drop 診断の網からも漏れていた (今回は count-gate 無罪だったが同族の網羅漏れ)。

補足: carry_dip (hourly 経路) には HTF hard block 相当は**存在しない** (compute_hourly_signal 確認済み) — ceiling が唯一の遮断で確定。hull_donchian_fade は shadow 5 件発火あり = HTF block を通過するバーが存在 (EUR_USD fade は bear 限定でない)、live 0 は env 未設定説 (cross-session 情報) と整合。

### 3.5 Fix 提案 (提案のみ — live 挙動変更は user 決裁)

| # | 提案 | Rule | 備考 |
|---|---|---|---|
| P-S1 | (b) **shadow 退避 → 実装済み (2026-07-03, rule:R3)**: `HTF_BLOCK_SHADOW_RESCUE` 登録戦略 (sweep のみ) の blocked 候補を `shadow_emit_signals` (is_shadow=1) へ退避、`[HTF_BLOCK_SHADOW_RESCUE]` タグでセグメント分離。E2E 検証: 07-01 21:16 スナップショットで shadow emit 復元を確認。**(a) live exemption は引き続き user 決裁待ち** — 蓄積される shadow N がその判断材料になる | (b)=R3 実装済 / (a)=R2 未決 | (a) は「bear 局面で逆張り BUY を実弾発火」の是非 = リスク判断。pre-reg (12y 検証は HTF なし) は (a) を支持するが、MIN lot 1000u でも user 決裁必須 |
| P-S2 | HTF Hard Block の観測性: **print 化 + blocked entry_type 明示 (本コミット実装済み)**。counter (_block_counts 相当) / evaluated_candidates への記録は別途 | R3 | 実装済み分は挙動変更なし (ログのみ) |
| P-S3 | **診断側実装済み (2026-07-03, rule:R3)**: `_COUNT_GATE_BYPASS_LIVE_EXCEPTIONS` を診断セットからの派生をやめ user 決裁済み 6 戦略の明示列挙に分離 (メンバーシップ不変、pin テストで固定)。`_SILENT_DROP_DIAG_TYPES` に 06-12 世代 3 戦略を追加 (SENTINEL_BLOCK_DIAG ログのみ、live gate 挙動不変)。count-gate bypass への追加は user 決裁 + pre-reg 必須のまま | R3 | 06-02 対策の網羅漏れ是正。新 LIVE 例外登録時のチェックリスト化は別途 |

## 4. 検証手段 (再現用)

- 本番 trades: `GET /api/demo/trades?mode={daytrade,daytrade_1h}&date_from=...&status=all` → entry_type filter
- 本番 audit: `GET /api/oanda/audit?limit=12000` → `block_reason`
- 本番 risk: `GET /api/risk/dashboard` → kelly.edge / monte_carlo.ruin_probability
- carry_dip 発火期待値: yfinance USDJPY=X 1h + 戦略同一の `_wilder_rsi` (本レポート §1.2 のスクリプト、以後は QUALBAR log で代替可)

## 5. 関連

- [[vix-overlap-pilot-prereg-2026-05-13]] / [[vix-carry-grail-removal-overlap-1000u-2026-06-15]] / [[vix-1x-intentional-exception-2026-05-21]]
- [[usdjpy_carry_dip_accumulator]] / [[vix-carry-unwind]] (strategy cards — 本診断へのポインタ追記済み)
- [[roadmap-v2.2-win-conversion]] T7
- 教訓: [[lesson-asymmetric-agility-2026-04-25]] (Rule 判定) / eligible vs effective (Kelly gate)
