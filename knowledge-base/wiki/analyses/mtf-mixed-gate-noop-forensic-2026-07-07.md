# MTF Gate mixed = no-op Forensic — 「シグナル抑制中」タグ付き LIVE 発注の経路特定 (2026-07-07)

## TL;DR
close_analysis タグ **「⚖️ 4H+1D 不一致 → シグナル抑制中」は診断タグのみで、mixed 状態は DTE 候補経路に一切の抑制を持たない**。v9.1 HTF Hard Block は `htf_agreement in ("bull", "bear")` の時しか候補を除外せず、mixed は no-op。trendline_sweep は self-contained HTF guard を持たないため、mixed 状態の候補が無抑制で ELITE_LIVE 経路から OANDA へ転送されていた。

**対処 (同コミット)**: (R2) `HTF_MIXED_LIVE_STOP_CELLS = {(trendline_sweep, GBP_USD)}` セルの live 転送停止 + shadow 退避 / (R3) 診断タグ文言の実状態化。

## 発端 (T1 forensic §7)
trendline_sweep × GBP_USD の 30d 大負け4発 (−53.6pip) 全てに「⚖️ 4H+1D 不一致 → シグナル抑制中」タグが付いたまま LIVE (OANDA) 発注されていた。

本番スナップショット (2026-07-07, `tools/render_trades_snapshot.py`, clean live = `oanda_trade_id != '' AND dedup_violation != 1`) で再現確認:
- 30d LIVE 大負け上位4発: −20.0 / −15.4 / −10.9 / −7.3 = **−53.6p ぴったり一致** (全て mixed タグ)
- タグの二重絵文字「⚖️ ⚖️ …」= `app.py` reasons[0] (`f"⚖️ {htf_dt['label']} → シグナル抑制"`) 由来と確定

## 経路特定 (コード)
1. **タグ生成**: `get_htf_bias_daytrade()` (app.py) — 4H/1D EMA アライメントから `agreement ∈ {bull, bear, mixed}` + label を返す。ステートレス (TTL キャッシュのみ)
2. **タグ転写**: `compute_daytrade_signal` ⓪ で reasons[0] に append → trade record `reasons` → 決済時 `_generate_close_analysis` が `_clean[:2-3]` を close_analysis に転写。**タグは entry 時の gate 判定を正しく記録している** (gate 状態喪失ではない)
3. **mixed の実効果 (修正前)**:
   - legacy score path: `score *= 0.70` の soft 減衰のみ (完全ブロックは bull×SELL / bear×BUY のみ)
   - **v9.1 HTF Hard Block (候補リスト除外): `if htf_agreement in ("bull", "bear")` — mixed は分岐ごと素通り**
   - DTE 採用時は `signal = _dt_best.signal` で legacy score 減衰も実質無関係
4. **trendline_sweep 戦略自体**: HTF 参照ゼロ (self-contained guard 欠如 — lesson「セーフティネットは単一レイヤーに依存してはならない」の再現形)
5. **demo_trader 側の第2層も不在**: v9.3 MTF Regime gate (別物、strategy_aware_alignment ベース) は `_is_live_tier_exempt` で **ELITE_LIVE を免除** + A/B hash 半数のみ gated → trendline_sweep は二重に素通り

## 仮説判定
| 仮説 | 判定 | 根拠 |
|---|---|---|
| (a) MTF ゲートは診断タグ付与のみで転送 block しない | **CONFIRMED** | Hard Block の bull/bear 限定分岐 + mixed=score減衰のみ。タグ文言「抑制中」が実装と乖離 |
| (b) engine 再構築で gate 状態喪失 | **棄却** | gate はステートレス毎回計算。タグ自体が「entry 時に mixed と正しく判定していた」証拠 |
| (c) ELITE_LIVE が gate bypass を持つ | 部分的 (副因) | 当該タグの gate (4H+1D) には bypass 概念自体が無い。v9.3 regime gate の ELITE 免除は「第2層の不在」として寄与 |

## 定量根拠 (clean live, 2026-06-03..07-03 全期間スナップショット)
trendline_sweep × GBP_USD, HTF 状態は entry 時 reasons JSON から分類:

| bucket | HTF状態 | N | PnL | EV | WR |
|---|---|---|---|---|---|
| clean_live | **mixed** | **15** | **−50.7p** | **−3.38** | 53.3% |
| clean_live | aligned (bull+bear) | 4 | +6.0p | +1.50 | 100% |
| shadow | mixed | 7 | −50.4p | −7.20 | 28.6% |
| shadow | aligned | 5 | +0.5p | +0.10 | 80.0% |

- mixed セルは live/shadow 両系列で一貫して負 (合算 N=22, −101.1p) → regime 偶然ではなく構造的
- GBP_USD RT friction 4.53p (friction table) に対し mixed セルは gross でも大幅負 — friction 調整の余地なし
- 30d 窓では trendline_sweep clean live は GBP_USD のみ発火 (EUR_USD は 0 件) → 停止セルは GBP_USD 単独で十分

## 判断 (rule:R2 + R3)
- **R2 (損失停止, N=15 ≥ 即断基準 N=10)**: `DaytradeEngine.HTF_MIXED_LIVE_STOP_CELLS = {("trendline_sweep", "GBP_USD")}` — mixed 時に候補リストから除外し live 転送停止。**shadow 退避 (is_shadow=1, `[HTF_MIXED_LIVE_STOP]` タグ) で N 蓄積は継続** (4原則#3: Shadow は削らない / LIVE は勝てる場所だけ転送)
- **R3 (診断整合)**: reasons の mixed 文言を「⚖️ 4H+1D 不一致 (mixed) — legacy score減衰のみ、DTE候補は cell stop 登録分を除き非抑制」へ是正。「4H+1D 不一致」substring は forensic query 互換のため維持
- **BT⇄本番 同期**: cell stop は `compute_daytrade_signal` 内 select_best 前に適用 → `backtest_mode=True` でも同一挙動 (htf_cache 注入経由で agreement 判定)
- **再 live 化は R1 のみ** (365d BT or clean live N≥30 + Bonferroni + Pre-reg LOCK)

## 残課題 (スコープ外、記録のみ)
1. **他 DTE 戦略の mixed セル**: 本 forensic は trendline_sweep×GBP_USD に限定 (T1 forensic 由来)。mixed × 他戦略×ペアの cell-level 集計は別タスク (同じ `split_htf_mixed_live_stop` にセル追加するだけで拡張可)
2. **UI ラベル**: `get_htf_bias_daytrade` / BT 複製 (app.py) の label 文字列「→ シグナル抑制中」自体はダッシュボード表示互換のため未変更。scalp 側 (1H+4H) の同型ラベルも同様
3. **v9.3 MTF regime gate の ELITE 免除**: 第2層不在の構造は残置 (免除は 2026-04-24 の意図的設計)。ELITE_LIVE 向け安全網は本 cell stop 方式 (evidence-based per-cell) で個別に張る方針

## 教訓との接続 (新規 lesson は作らない — 既存の再確認)
- 「セーフティネットは単一レイヤーに依存してはならない。戦略自身が HTF を知っているべき」(lesson-htf-bypass) — trendline_sweep は中央フィルターすら無い状態だった
- 「資格 (eligible) と実状態 (effective) を区別する」— タグは『抑制中』という資格を主張したが、実状態は無抑制だった。**診断タグは実状態を記述せよ**

## 関連
- [[trendline-sweep]] — 戦略カード (cell stop 追記済み)
- [[roadmap-v2.3-payoff-friction-repair]] — 負エッジ・摩擦是正の文脈 (T1 forensic の親)
- tests/test_htf_mixed_live_stop.py — 回帰 pin (6 cases)
- 前例パターン: P-S1(b) HTF_BLOCK_SHADOW_RESCUE ([[zero-fire-diagnosis-carrydip-vix-2026-07-02]] §3)
