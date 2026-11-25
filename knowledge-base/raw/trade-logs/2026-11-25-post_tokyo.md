# Post-Tokyo Report: 2026-11-25

## Analyst Report
# Post-Tokyo Report — 2026-11-25 06:52 UTC（JST 15:52）

---

## 1. 東京セッション結果

**東京セッション: トレードなし**

| 項目 | 値 |
|---|---|
| セッション内トレード数 | 0 |
| PnL | ¥0 |
| WR | N/A |
| アクティブモード数 | 25/27（daytrade_xau・scalp_xau・scalp_eurjpy OFF） |

東京UTC 00:00–06:00における約定ゼロ。ブロック集計は累積値のため本セッション起因の内訳は分離不可だが、主因は後述のBlock分析に吸収される。

---

## 2. What Worked

**該当なし**（トレード約定ゼロのため）

---

## 3. What Didn't Work

**該当なし**（約定ゼロのため損失も発生していない）

ただし「約定されなかった理由」として以下を記録：

| ブロック主因 | Count | 判断 |
|---|---|---|
| `rnb_usdjpy:no_signal` | 455 | シグナルそのものが発生せず（レジーム=RANGING 43%ile、エントリー条件を満たさず） |
| `scalp:r2_shadow_demoted_cell` | 278 | Shadow評価でセル降格、スキャルがアウト |
| `daytrade_gbpjpy:gbp_asia_flash_crash` | 190 | GBP_JPY VOLATILE判定によるフラッシュクラッシュガード発動 |
| `scalp_eur:r2_shadow_demoted_cell` | 160 | 同上、EUR系スキャルも降格セルでブロック |
| `daytrade:order_bar_dedup` | 81 | バー重複排除（同バー多重シグナル除去） |

**主因はr2_shadow_demoted_cell（合計556件）が全体の最大ブロック群を形成。** Shadow降格セルが広範囲に存在し、スキャル系の実質的な不活性化が継続中。

---

## 4. 戦略調整判断

**NO — パラメータ変更不要**

根拠：
- Fidelity Cutoff後のセッション内N=0。統計判断の基礎となるサンプルが存在しない
- DD防御0.2x (defensive mode)が継続稼働中。DD=10.01%、Lot Mult=0.2x。現時点でシステムは正しくリスク抑制を行っている
- Shadow降格セルによるブロックはr2評価の正常動作であり、介入する根拠がない
- OANDA転送率0%（SENT 0/50）はShadowブロックが主因（`shadow_tracking` 17件、`pair_demoted` 2件、`agg_kelly=-0.223<0` 1件）。構造的に意図通り動作している

---

## 5. ロンドンセッション準備

### ATR・レジーム変化予測

| ペア | 現レジーム | ATR%ile | ロンドン開幕予測 |
|---|---|---|---|
| GBP_JPY | VOLATILE | 67% | GBP系はロンドン開幕で更にボラ拡大リスク。フラッシュクラッシュガードは引き続き有効と想定 |
| GBP_USD | VOLATILE | 69% | 同上。高ボラ継続、スキャル系は不利 |
| EUR_USD | TRENDING_DOWN | 67% | トレンド方向性あり。DT系に相対的に有利なレジームだが、VOLATILE化の警戒必要 |
| EUR_JPY | RANGING | 55% | RANGING継続見込み。DT系のエントリー確率は低め |
| USD_JPY | RANGING | 43% | rnb_usdjpy向けシグナル発生確率は引き続き低い |

### 推奨戦略配分

**NO ACTION推奨**

| 推奨根拠 | 詳細 |
|---|---|
| **DD防御発動中** | 10.01% DD、Lot Mult 0.2x。システムが既に自律的にリスク抑制。上位レイヤーからの追加介入は不要 |
| **GBP系VOLATILE** | ロンドン開幕でGBP_JPY・GBP_USDのボラティリティ拡大が見込まれる。`gbp_asia_flash_crash`ガードが190件発動した実績があり、ロンドン序盤も同等以上のガード発動を想定 |
| **Shadow降格広域** | スキャル系の実質不活性状態が継続。ロンドンでもr2_shadow_demoted_cellが主要ブロック要因として継続する可能性が高い |
| **agg_kelly<0** | Kelly基準がマイナス（−0.223）。期待値的にポジション取得を推奨しない水準 |

ロンドン序盤でEUR_USDのTRENDING_DOWN継続を確認できた場合、daytrade_eur系がシグナルを生成する可能性があるが、DD防御とShadow評価に委ねる。システム外からの誘導は行わない。

---

## 6. クオンツ見解

### 最重要シグナル：**Shadow降格の広域固着とagg_kelly<0の継続が「構造的不活性」を示している**

現在のシステムは「正しく動作して何も約定させていない」状態にある。これは欠陥ではなくリスク管理の正常動作だが、**2点の構造的観察を記録しておく必要がある。**

**①Shadow降格セルの固着深度**：r2_shadow_demoted_cellによるブロックがscalp・scalp_eur・scalp_5m・scalp_5m_gbp・scalp_5m_eurに渡って合計656件（TOP15の約38%）を占める。これはShadow評価が広範囲のペア×時間帯セルに降格判定を与えており、スキャル系が実質的に「活動可能セル枯渇」状態にある可能性を示す。M3目標（+2〜3%/月複利）への貢献源としてスキャル系を期待する場合、このShadow固着の解消が先決条件となる。ただしShadow評価はデータ蓄積に依存するため、外部介入ではなく実績蓄積による自然回復を待つのが適切。

**②carry_dip蓄積N=35・EV+5.34**：KB記録によればusdjpy_carry_dip_accumulatorはN=35・EV+5.34・WR54.3%と唯一の有望候補だが、agg_kelly=−0.223がOANDA転送を阻止し続けている。このKellyマイナスはポートフォリオ全体のEVが負（realized N=624・EV−0.97）に引きずられているためであり、carry_dip単体の優位性がポートフォリオ評価に反映されない構造問題が存在する。**推奨アクション：DD=10.01%が防御閾値を下回るまで（またはagg_kellyが転換するまで）現状維持。現時点でOANDA昇格の手動介入は行わない。** N=35は形式的にはカットオフを超えているが、carry_dipの実績がKelly抑制を解除するには全体ポートフォリオの回復が必要条件であり、単策での判断は時期尚早。

## SL replacement storm guard（決定的出力 — LLM 非経由、読み方: storm-guard-design-2026-09-22 §3）
### SL replacement storm guard
| enforce | max_tx/h | max_tx/day | deadband | evaluated | sent | failed | breaker_trips | detected (brk/idem/mono/dead/ser) | skipped (brk/idem/mono/dead/ser) |
|---|---|---|---|---|---|---|---|---|---|
| ON | 50 | 200 | 1.0p | 0 | 0 | 0 | 0 | 0/0/0/0/0 | 0/0/0/0/0 |

(guard 登録建玉なし)

