# LIVE 発火セル 124 → 3 の帰属 — 88.7% は設計通り、11.3% は現行テレメトリで帰属不能

**日付**: 2026-09-06 / **Rule**: R3 (診断 + 読み手新設、365d BT 不要)
**きっかけ**: [[m1-kpi-readout-and-mechanical-flip-2026-09-04]] §6 が M3 スループットを
独立ボトルネックへ昇格させた際、崩壊を「7-8 月の R2 降格バッチ = 設計通り」と解釈したが、
**その帰属を機械的に突き合わせた主体が存在しなかった**
**関連**: [[rnb-dead-mode-and-block-estimand-2026-09-05]] / [[roadmap-v2.3-payoff-friction-repair]] M3 行

---

## 0. 要約

| # | 事実 | 帰結 |
|---|---|---|
| **A** | anchor 窓 (2026-05-01 終端 30d) の LIVE 発火 **124 セル**のうち **95 セル (76.6%)** はコード上の停止機構 (live 停止 83 / shadow 降格 12) に載っている | 09-04 の「縮小は設計通り」は**大部分について正しい** |
| **B** | さらに **15 セル (12.1%)** は昇格集合に**一度も入っていない** = shadow のみが設計状態。**anchor 窓の LIVE 行の方が異常** | 帰属済み計 **88.7%** |
| **C** | 残 **14 セル (11.3%)** は昇格集合にあり、どの停止機構にも載らず、現在窓の LIVE がゼロ | **バグではない。現行テレメトリでは帰属できない**、が正しい記述 |

**最大の含意は損益の非対称にある**: 停止済み 83 セルは anchor 窓で **N=609 / −469.8 pips** を
出していた。つまり**止血は損失の圧倒的部分を除去しており、分母縮小の代償は主に「負け」だった**。
一方 C の 14 セルは **N=34 / −25.1 pips** と小さく、ここを開けても M3 は解けない
(下記 §4 の算術)。

---

## 1. estimand と読み手

新設した読み手 `tools/live_roster_attrition.py` が名乗る量:

> anchor 窓 (既定 2026-05-01 終端 30 日) で **clean LIVE 約定**を出していたセル
> (entry_type × instrument × direction) が、現在窓で LIVE 約定を出さなくなった理由の帰属。
> clean LIVE = `oanda_trade_id` 非空 ∧ `dedup_violation != 1` ∧ `instrument != 'XAU_USD'`

`is_shadow=0` 単独では判定しない (FLAG_DRIFT 行が混入する。MEMORY
`feedback_live_vs_shadow_strict_separation`)。窓系列は 09-04 の正準値を
**完全再現**した (124 / 24 / 26 / 11 / 4 / 3) 上で分解している。

⚠️ **本ツールは「なぜ LIVE 転送されなかったか」を測っていない。** 測るのは
「停止機構・昇格集合との突き合わせで LIVE 消滅が説明できるか」だけである。

## 2. 分類と結果

優先順位順 (先に一致したものを採る):

| class | 定義 | セル | anchor N | anchor pips |
|---|---|---:|---:|---:|
| `A_STILL_LIVE` | 現在窓でも LIVE 約定あり | 0 | — | — |
| `B_LIVE_STOPPED` | `_FORCE_DEMOTED` / `_PAIR_DEMOTED` / `HTF_MIXED_LIVE_STOP_CELLS` | **83** | 609 | **−469.8** |
| `C_SHADOW_DEMOTED` | `SHADOW_RETIRED_STRATEGIES` / `SHADOW_DEMOTED_CELLS` / `SHADOW_ALWAYS_STRATEGIES` | **12** | 54 | −52.4 |
| `D_NEVER_PROMOTED` | `_PAIR_PROMOTED` ∪ `_UNIVERSAL_SENTINEL` に無い | **15** | 28 | −26.2 |
| `E_PROMOTED_UNATTRIBUTED` | 昇格済み・停止なし・LIVE ゼロ | **14** | 34 | −25.1 |

A が 0 なのは定義どおり — 現在窓の LIVE 3 セル (`carry_dip` / `price_shock_rev` ×2) は
いずれも anchor 窓には存在しなかった**後発**のセルである。

### 2.1 D クラスの意味 — anchor 側が異常

D の 15 セルは昇格集合に**一度も**入っていない。にもかかわらず 2026-04〜05 に
LIVE 約定を出していた。これは既知の 2 バグ期
(MEMORY `project_watchdog_decrement_rearm_bug` の stage 0→1 昇格 /
`project_preserve_bug_fixed_10cells_live`) と時期が整合する。
**つまり D は「失われた発火機会」ではなく「本来出てはいけなかった発火」**であり、
M3 の分子に数えてはならない。

## 3. E クラス — 昇格済みだが LIVE ゼロ (未帰属)

| cell | anchor N | 現在窓 行数 | subclass |
|---|---:|---:|---|
| `session_time_bias × GBP_USD × SELL` | 7 | **37** | E1_SUPPLY_PRESENT |
| `dt_sr_channel_reversal × USD_JPY × SELL` | 2 | 23 | E1 |
| `dt_bb_rsi_mr × USD_JPY × SELL` | 5 | 10 | E1 |
| `dt_sr_channel_reversal × EUR_JPY × BUY` | 1 | 10 | E1 |
| `dt_bb_rsi_mr × USD_JPY × BUY` | 2 | 9 | E1 |
| `dt_sr_channel_reversal × USD_JPY × BUY` | 2 | 5 | E1 |
| `dt_sr_channel_reversal × GBP_USD × SELL` | 2 | 4 | E1 |
| `doji_breakout × GBP_USD × BUY` | 1 | 4 | E1 |
| `doji_breakout × EUR_USD × SELL` | 1 | 2 | E1 |
| `doji_breakout × USD_JPY × BUY` | 2 | 1 | E1 |
| `bb_squeeze_breakout × EUR_USD × BUY` | 5 | **0** | E2_SILENT |
| `bb_squeeze_breakout × EUR_USD × SELL` | 2 | **0** | E2_SILENT |
| `ema200_trend_reversal × USD_JPY × SELL` | 1 | **0** | E2_SILENT |
| `squeeze_release_momentum × GBP_USD × BUY` | 1 | **0** | E2_SILENT |

### 3.1 これを「バグ」と呼んではいけない理由

CLAUDE.md **原則 3** は明文で「LIVE OANDA 転送側は『勝てる場所で勝つ条件だけ転送』が
正しい設計 — session_pair / gbp_asia_flash_crash / alpha_scan 等の winning-location
フィルタは LIVE 側で意図的に維持する」と定めている。したがって
**昇格済みセルが LIVE ゼロであること自体は正常でありうる。**

E が「未帰属」に留まるのは、**セル単位で「昇格候補が LIVE 約定に至らなかった理由」を
永続化している系列がプロジェクトに存在しない**ためである。`block_counts` は
モード × block family 粒度で、かつ**市場オープン時間しか積み上がらない**
([[rnb-dead-mode-and-block-estimand-2026-09-05]] §1.6)。
これは新種の欠陥ではなく、**読み手の粒度不足**である。

### 3.2 E2_SILENT の 4 セルは rnb 型シグネチャだが、断定はしない

`bb_squeeze_breakout × EUR_USD` は `_PAIR_PROMOTED` 登録かつ
`wiki/index.md` の Current Portfolio に PAIR_PROMOTED として現役掲載されているが、
**あらゆる行 (LIVE / shadow) の最終出力が 2026-05-06 = 123 日前**である。
rnb (153 日) と同じ「現役掲載だが無出力」のシグネチャに見える。

ただし **scalp 側の当該経路は env フラグ依存**である
(`strategies/scalp/__init__.py`: `SQUEEZE_REDESIGN_V2` ∧ `SQUEEZE_REDESIGN_V2_SHADOW_PROMOTE`)。
本番 env の実値を確認するまでは「意図的に無効」と「配線落ち」を区別できない。
**この区別は `/api/demo/live-enable-flags` の実測で付く** (MEMORY
`project_bb_rsi_redesign_v2_lever_blocked`)。registry に監視エントリを起票した。

## 4. M3 への寄与 — E を全部開けても解けない

M3 = clean live N≥30 のセルを 3 個。E1 の 10 セルが**候補行の 100% を LIVE 転換**したと
仮定した上限計算 (現在窓 30d の行数をそのまま LIVE 約定に読み替える):

| cell | 30d 候補行 | N=30 到達 (上限、転換率 100% 仮定) |
|---|---:|---:|
| `session_time_bias × GBP_USD × SELL` | 37 | **~0.8 ヶ月** |
| `dt_sr_channel_reversal × USD_JPY × SELL` | 23 | ~1.3 ヶ月 |
| `dt_bb_rsi_mr × USD_JPY × SELL` | 10 | ~3.0 ヶ月 |

**これは上限であって予測ではない。** 転換率 100% は原則 3 の winning-location
フィルタを全部外すことと同義で、v2.3 の M6 ゲート (摩擦調整 EV>0 を LIVE 転送の
必要条件とする) に正面から反する。**E1 の候補行は摩擦調整 EV が未評価**であり、
[[friction-adjusted-ev-map-2026-07-07]] は現行母集団に live viable な正セルが
不在であることを既に確定している。

⇒ **結論: E は M3 の律速ではない。** M3 の律速は依然として
「摩擦調整後に正 EV のセルが存在しないこと」(v2.3 のボトルネック定義) であり、
09-04 が新設した「発火機会不足」は**その帰結**であって独立原因ではない。
本分析は 09-04 §6 の含意 3 (「エッジが無い問題ではなく発火機会が無い問題」) を
**部分的に否定する** — 発火機会の 88.7% は「負けていたので意図的に止めた」ためであり、
機会と EV は独立でない。

## 5. KB 更新提案 (user 決裁事項 — 本コミットでは執行しない)

- roadmap v2.3 の M3 行は「発火機会不足」を**独立ボトルネック**と記述しているが、
  §4 の通り独立ではない。**「摩擦調整 EV 不在の帰結」への格下げ**を提案する。
  09-04 の ~14 ヶ月 ETA 自体は不変 (分子の実測に依存しないため)。

## 6. 実装 (本コミット)

| 種別 | パス | 役割 |
|---|---|---|
| 読み手 | `tools/live_roster_attrition.py` | 帰属を再計算 (`--json` / markdown) |
| pin | `tests/test_live_roster_attrition.py` | 分類優先順位 / 分母 / estimand / fetch 非畳み込み (20 tests) |
| 監視 | `decisions/prereg-trigger-registry.json` `roster-e2-silent-promoted-cells` | E2_SILENT 4 セルの処分 |

### counterfactual 検証 (3/3 落ちることを確認)

| # | 破壊 | 落ちたテスト |
|---|---|---|
| 1 | `classify` が `force_demoted` を読まない | `test_classification_precedence[ema_cross...]` + `test_counterfactual_removing_a_stop_set...` |
| 2 | `load_stop_sets` が `shadow_retired` に空集合を返す | `test_load_stop_sets_reaches_real_non_empty_sets` |
| 3 | `fetch_trades` が失敗を `[]` に畳む | `test_fetch_rejects_non_https_instead_of_returning_empty` |

## 7. 未解決 / 次アクション

- [ ] **E2_SILENT 4 セルの処分** — registry `roster-e2-silent-promoted-cells`。
      まず `/api/demo/live-enable-flags` で env 実値を確認し「意図的に無効」と
      「配線落ち」を分離する。配線落ちなら R3、無効化解除は R1 (user 決裁)
- [ ] **E1 の帰属を閉じるには per-cell の LIVE 転送 block 理由の永続化が要る** —
      現行 `block_counts` はモード × family 粒度で不足。設計は別件
- [ ] **M3 行の格下げ提案** (§5) — user 決裁

---

## 教訓

**「設計通りに止めた」という説明は、止めた機構と実際に消えた母集団を突き合わせるまで
仮説である。** 本件では突き合わせの結果 88.7% が支持されたが、内訳を見て初めて
**12.1% が「止めた」ではなく「そもそも出てはいけなかった」(過去のバグの残響)** と分かり、
M3 の分子の意味が変わった。**分母の崩壊を語るときは「意図的に止めた」「異常が止まった」
「原因不明」を必ず分けよ — 混ぜると止血の成功が原因不明の欠損に見える。**
