---
title: 指値execution × 構造イベント × 予測選別 — Codex引き継ぎレポート
date: 2026-06-25
status: in-progress (探索完了, 実運用検証は未)
author: Claude (session handoff to Codex)
branch: research/h4-level-edge
tags: [handoff, edge-discovery, limit-order, execution, sweep, prediction, friction, codex]
related:
  - "[[mtf-regime-switch-eurusd-falsified-2026-06-25]]"
  - "[[tv-pine-edge-discovery-framework]]"
  - "[[friction-analysis]]"
---

# 指値execution × 構造イベント × 予測選別 — Codex引き継ぎレポート

> **このレポートの目的**: 2026-06-25 セッションの探索成果を Codex が cold-start で継続できる形で引き継ぐ。
> 会話文脈ゼロでも動けるよう、結論・成果物・数値根拠・次タスク・再現コマンドを自己完結で記す。

---

## 0. TL;DR (30秒で全体像)

ユーザー要望「RSI/MACD/EMA/ZIGZAG でインジ最強ツールを作る」から出発し、5段階の探索で次を**定量的に確定**した:

1. **オシレーター/価格パターン単体の方向エッジは EUR_USD 15m で非定常 or ゼロ** (IC≈0、年で出入り)。
2. **生エッジの上限 ≈ +0.8〜1.3pip < リテール成行 friction 2pip。** これが「インジで勝てない/BTで勝ってもLiveで負ける」の根本。エッジが無いのでなく **エッジ < コスト**。
3. **friction壁を超えた唯一の方法は「指値execution」。** 指値の正体 = **価格改善(+5.2pip)が唯一の源泉**、見送り効果は**逆**(−4.9pip、トレンドを逃す)。ネット +0.28pip(定常)。
4. **予測スコア** (`reclaim_frac高 × sweep_depth低 × atr_regime低`) で約定後トレードを選別 → EV +0.28→**+0.45pip** (holdout)、**train/holdout安定・EUR/GBP 2ペア再現・現実friction1.0で薄く正**。
5. ただし **EVは +0.1〜0.16pip と薄い** → 単体でなく **「複数弱エッジ × 低friction × 分散 → Kelly Half」(roadmap)の1ピース**。

**結論の骨格**: 勝ち筋は「構造イベント(sweep) × 指値execution × 予測選別 × 分散」。インジは方向トリガーでなくフィルタ/特徴量。

---

## 1. 探索フロー (なぜこの結論に至ったか)

| # | 探索 | ツール | 結論 |
|---|---|---|---|
| 1 | mtf_regime_switch (RSI+MACD+EMA+ATR統合, レジーム切替) | `tools/mtf_regime_switch_explore.py`, pine 2本 | **falsified**。複数年×friction2.0で全レジーム負。TVのPF1.39はfriction0+10ヶ月方向バイアスの誇張。詳細: [[mtf-regime-switch-eurusd-falsified-2026-06-25]] |
| 2 | MACDダイバージェンス (本物のpivot版) | `mtf_regime_switch_explore.py --div pivot` | **反証**。div有 fwd12 −3.7pip ⇔ div無 +0.9pip。ダイバは遅行でエッジ破壊。 |
| 3 | ZIGZAG swing構造の方向IC | `tools/zigzag_swing_ic_explore.py` | **方向予測力ゼロ** (|IC|<0.02)。swing_amp×abs=0.05はボラのクラスタリング(方向でない)。 |
| 4 | session_time_bias (実需フロー時間構造, Breedon-Ranaldo) | `tools/session_bias_explore.py` | 生エッジ実在 (USD_JPY+0.83, GBP+1.28) **だが friction(2.14/4.53)に届かず**。「BT79%→Live負け」の正体=friction過小+窓過適合。年次も不安定。 |
| 5 | sweep & reclaim (水平流動性狩り, trendline_sweepの水平版) | `tools/sweep_reclaim_explore.py` | 生エッジ +0.32 (大口介入確認, holdout+0.70)。成行friction2.0では負、**指値friction0.5でholdout+0.85**。ただし年次分解で**非定常** (2025年単独の山、2026負)。 |
| 6 | 指値約定の予測器 + 見送り効果解明 | `tools/limit_fill_predictor.py` | 指値の正体完全解明 + 予測スコアでEV向上を実証 (§3, §4)。 |

---

## 2. 核心の数値根拠

### 2-1. 生エッジ < friction (全探索共通の壁)
| 手法 | 生エッジ (friction0) |
|---|---:|
| ZIGZAG方向 | ≈0 |
| sweep緩い定義 | +0.20 |
| session_bias USD_JPY | +0.83 |
| sweep+大口介入+指値 (holdout) | +0.85 |
| session_bias GBP | +1.28 |

→ いずれも EUR/USD/JPY のリテール成行 RT friction (2.0〜4.5pip) 未満。

### 2-2. 指値の正体 (`limit_fill_predictor.py`, EUR_USD, friction limit=0.7)
| 効果 | train | holdout |
|---|---:|---:|
| E[market \| 約定群] | −4.9 | −4.6 |
| E[market \| 不約定群] | +4.7 | +4.9 |
| **見送り効果** (E[m\|filled]−E[m\|notfilled]) | **−9.6** | −9.6 |
| 良い価格効果 (E[limit\|f]−E[market\|f]) | +5.2 | +4.9 |
| **ネット E[limit \| filled]** | **+0.28** | **+0.31** |

**解釈**: 指値は「トレンド継続(成行なら勝てた)場面を見送り、戻って負ける場面だけ約定」する。優位は価格改善(+5.2)のみ。これが定常。

### 2-3. 予測スコア選別 (EUR_USD, friction limit=0.7)
`score = z(reclaim_frac) − z(sweep_depth_atr) − z(atr_regime)`
| 群 | TRAIN EV | HOLDOUT EV |
|---|---:|---:|
| 全約定 | +0.278 | +0.306 |
| 上位30% | +0.372 | +0.363 |
| 上位20% | +0.366 | **+0.446** |
| 上位10% | +0.152 (過剰適合境界) | +0.375 |

### 2-4. 現実friction(1.0) × 他ペア再現
| ペア | 全約定(t/h) | 上位30%(t/h) | 判定 |
|---|---|---|---|
| EUR_USD | −0.02/+0.01 | +0.07/+0.06 | 薄く正・安定 |
| GBP_USD | +0.15/+0.11 | **+0.16/+0.16** | 最良・安定 |
| USD_JPY | +0.45/−1.02 | +0.64/−0.79 | **不安定(15mデータが2025-04〜と短く分割が脆い)** |

---

## 3. 成果物 (全て branch `research/h4-level-edge` に**未コミット**)

| ファイル | 役割 | 主要CLI |
|---|---|---|
| `bt-results/tv-overlays/mtf_regime_switch-EURUSD-15m.pine` | TV版A (1m/5m補助あり) | TVに手動Add to chart |
| `bt-results/tv-overlays/mtf_regime_switch-EURUSD-15m-fullhist.pine` | TV版B (1m/5mなし) | 同上 |
| `tools/mtf_regime_switch_explore.py` | レジーム切替BT + 診断 | `--friction --div {proxy,pivot,none} --exit {fixed,trail} --diagnose` |
| `tools/zigzag_swing_ic_explore.py` | ZIGZAG swing構造の方向IC | `--pair --horizon 12,48` |
| `tools/sweep_reclaim_explore.py` | sweep&reclaim BT (成行/指値, 厳格化, TF切替) | `--entry {market,limit} --strict-bar --tf {15m,1h} --friction` |
| `tools/session_bias_explore.py` | session_time_bias 複数年定常性 (1h) | `--pair --no-confirm` |
| `tools/limit_fill_predictor.py` | **指値約定予測器 + 見送り効果 + 予測選別** (本命) | `--pair --fric-limit --fric-market` |
| `knowledge-base/wiki/learning/mtf-regime-switch-eurusd-falsified-2026-06-25.md` | mtf falsification記録 | — |

共通基盤: データは `data/cache/massive/{PAIR}_{15m,1h,4h}.parquet` (BTDataCache)。共通窓 2022-01〜2026-05 (1h/4h深度制約)。train/holdout=60/40 chronological。EUR_USD_15m は12年あるが MTF(1h/4h)が4.4年。

---

## 4. 未解決事項・既知の限界 (Codexが必ず認識すべき)

1. **約定選択バイアスの実約定未検証** ★最重要。`limit_fill_predictor.py` の「約定=価格がlevelに戻る」はBT仮定。実際の指値が同条件で約定するか (板・スリッページ) は**実Live/tick約定データで未検証**。+0.45pipの一部はBTの約定仮定に依存。
2. **friction現実性**: KB friction-analysis では EUR_USD spread=0.7pip(片道)。指値makerでRT 0.7-1.0pip が現実線。**friction0.5は楽観**。現実1.0で選別後EVは +0.06〜0.16pip と非常に薄い。
3. **`htf_align` 特徴量が n/a** (IC算出不可)。`limit_fill_predictor.py` build() の htf_align 計算が分散不足 (ほぼ全シグナル同値)。要デバッグ/再設計。
4. **EVが薄い** (+0.1〜0.16pip)。単体promote不可。分散ポートフォリオ前提。
5. **sweep&reclaim自体は非定常** (sweep_reclaim_explore の年次分解: 2025年単独の山)。指値+予測選別で安定化したが、母体イベントの非定常性は残る。
6. **USD_JPY 15mデータ不足** (2025-04〜)。USD_JPY検証は1h主体にすべき。
7. **TVは15m BTを~10ヶ月(20k bars)で打ち切る** — 複数年検証はPython(parquet)必須。

---

## 5. Codexへの推奨次タスク (優先順)

**P1 — 約定選択バイアスの実証** (限界1の解消):
`limit_fill_predictor.py` に「limit_wait を変えて約定率とEVの関係」を追加。厳しい指値(wait短/level厳格)で約定率↓だがEV↑なら選択効果が本物。さらに可能なら OANDA tick/L1 データで実約定シミュレート。

**P2 — 分散ポートフォリオ合成**:
EUR_USD + GBP_USD × 予測ルール(上位30%選別, friction1.0)のトレードを時系列マージし、合成エクイティの DD/Sharpe/月次を算出。単一の薄エッジ(+0.16)が分散で実用Sharpeになるか。roadmap「分散→Kelly Half」直結。新ツール `tools/limit_edge_portfolio.py` 想定。

**P3 — htf_align バグ修正 + 特徴量拡充** (限界3):
htf_align のn/aを修正。spread推定・直近ボラ拡大・session ダミー・sweep後の経過時間等を特徴量に追加し、約定後EVの予測ICを上げる。

**P4 — shadow実装** (P1-P2クリア後のみ):
予測ルールを本番戦略としてshadow登録 (`strategies/daytrade/`)。is_shadow=1強制でLive約定・EVをクリーン蓄積。BT指値仮定 vs 実約定の最終検証。**P1未解決のままLive投入は禁止** (curve-fitting/約定バイアスリスク)。

---

## 6. 再現コマンド

```bash
# 1. mtf falsification (レジーム切替の反証)
python3 tools/mtf_regime_switch_explore.py --pair EUR_USD --friction 2.0 --div pivot --diagnose

# 2. ZIGZAG方向IC (ゼロ確認)
python3 tools/zigzag_swing_ic_explore.py --pair EUR_USD --horizon 12,48

# 3. session_time_bias 複数年 (friction壁確認)
python3 tools/session_bias_explore.py --pair USD_JPY,GBP_USD,EUR_GBP

# 4. sweep&reclaim 指値 (friction突破)
python3 tools/sweep_reclaim_explore.py --pair EUR_USD --tf 15m --entry limit --friction 0.7 --strict-bar 1.0

# 5. 指値予測器 + 見送り効果 + 予測選別 (本命)
python3 tools/limit_fill_predictor.py --pair EUR_USD --fric-limit 0.7 --fric-market 2.0
python3 tools/limit_fill_predictor.py --pair GBP_USD --fric-limit 1.0 --fric-market 2.0   # 他ペア・現実friction
```

---

## 7. 規律メモ (CLAUDE.md / KB教訓の遵守事項)

- **curve-fitting禁止フェーズ**。閾値は train で決め holdout で検証。in-sample最適化(grid最良選び)は過剰適合。
- **friction現実値で判定** (EUR 2.0成行/0.7-1.0指値, GBP 4.53成行)。friction0は再現確認のみ。
- **train/holdout符号反転・年次バラつきは非定常の赤信号** → promote不可 (今回USD_JPYで確認)。
- **集計値は分解** (direction/session/year)。aggregate WRは嘘をつく。
- **生エッジ(forward-return) < friction なら exit/フィルタを変えても勝てない** — まずエントリーの生予測力を測る。
- コードとKBは同一commit (CLAUDE.md)。本ハンドオフは全ハーネス + KB doc を1 commit に含めること。
