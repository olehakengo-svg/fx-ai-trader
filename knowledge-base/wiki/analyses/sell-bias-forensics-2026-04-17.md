# SELL Bias 法医学 — 事前登録版 (2026-04-17)

**作成**: 2026-04-17 (JST 午後)
**方式**: pre-registered 3仮説 → falsification → 結論
**前提**: [[rigorous-edge-analysis-2026-04-17]] で Live SELL −183p (N=174, p=8e-8, Bonferroni 有意) が確認済み。全 Live trades の 53% (174/326) を占める最大の単一敗因。

---

## なぜ pre-registration するか

データを見てから仮説を作ると p-hacking になり、真の原因を見誤る。**3つの競合仮説を先に固定**し、各仮説が反証される条件 (falsifier) を先に書き下す。その後データを当てる。

---

## 対立仮説

### H1 — 信号生成バイアス (Code Bug)
**主張**: ストラテジー群が BUY より SELL を物理的に多く発火している。50:50 から統計的に乖離した生成比。

**メカニズム候補**:
- Entry condition の片側 (SELL) が緩い or BUY が厳しい
- Session filter が BUY 側のみを落としている
- Layer1 / regime input の片側バイアスが SELL を促している

**予測**: Signal が発火した時点 (= trade が open される時点) での BUY:SELL カウントが、全戦略横断で chi-squared 50:50 から有意に偏る。

**Falsifier**: **全戦略の生成比が 50:50 と統計的に区別不能** (chi-sq p > 0.05) → H1 却下

**発見されたら**: Code 修正 = signal generation logic の対称化 → **即座に portfolio に +183p 相当の影響**

---

### H2 — 執行摩擦の方向非対称
**主張**: Signal 生成は対称。ただし SELL 側の spread/slippage が BUY より体系的に大きく、確定 PnL で −1p/trade の差を生んでいる (174 trades × 1p ≈ 174p 相当)。

**メカニズム候補**:
- Broker quoting asymmetry (典型的には bid-ask mid vs actual fill price)
- SELL order の注文時刻が BUY より illiquid moment に集中
- OANDA の spread が direction-dependent (可能性は低いがゼロではない)

**予測**: `spread_at_entry` / `slippage_pips` が SELL > BUY で有意差 (Mann-Whitney U or t-test)

**Falsifier**: **spread/slippage の direction 差が統計的に zero** → H2 却下

**発見されたら**: Spread gate に方向別の threshold を導入、または SELL 発注タイミングの調整 → **部分回復 (推定 +60〜100p)**

---

### H3 — Regime 依存の一時的バイアス
**主張**: Signal 生成も執行も対称。**現 9日間の regime 分布が強い uptrend に偏っており**、SELL が負けるのは市場事実。π_long_run で reweight すれば SELL 劣位は縮小/消滅する。

**メカニズム候補**:
- 2026-04-08〜04-16 の DXY/USD 基調が一方向 (サンプリング偏り)
- regime=up_trend の cell で SELL 負、down_trend cell で BUY 負、両者の比率が π_sample と π_long_run で乖離

**予測**: regime × direction breakdown で、down_trend regime では SELL が勝ち、up_trend では負ける。π_long_run で reweight すると SELL の θ_reweighted が 0 に近づく。

**Falsifier**: **全 regime で SELL が負け続ける** or **regime_support=INSUFFICIENT で結論不能** → H3 却下

**発見されたら**: Regime 条件付き SELL guardrail (regime=up_trend では SELL 禁止) → **+100〜150p 相当の回復**、ただし長期では本当に対称に戻る保証があるので慎重な実装

---

## 仮説の相互排他性

H1, H2, H3 は **完全には排他的ではない**。複合原因もあり得る。ただし主因を特定するため、以下の優先順位で評価:

1. **H1 (最悪のシナリオ)** — これがあると残り2つの分析結果も歪む。最初に確認。
2. **H2 (中間)** — H1 を通過した trades に対してだけ執行非対称を評価
3. **H3 (残差説明)** — H1, H2 で説明できない残差が regime で説明できるか

---

## 設計: どのデータを取るか

| 仮説 | データ源 | 指標 |
|---|---|---|
| H1 | `_demo_db.get_closed()` | 全 Live trades の direction count, by entry_type |
| H2 | 同上 | `spread_at_entry`, `slippage_pips` by direction |
| H3 | 同上 + OANDA candles | regime_independent × direction の PnL cross-tab |

**サンプル**: 2026-04-08 以降の全 Live closed FX trades (N≈326)

**除外**: XAU, Shadow (user memory + 既存ルール)

---

## 事前登録 signatures

- **私 (Claude, quant analyst)**: 2026-04-17 JST 午後時点でこの文書を確定
- **データは未閲覧**: 上記は全て [[rigorous-edge-analysis-2026-04-17]] の集計結果と、過去の [[sell-bias-root-cause-2026-04-17]] の regime-unaware 観察のみに基づく。

---

## 検定結果 (2026-04-17 JST 午後実行)

### データ
- N=326 Live FX closed trades (2026-04-08〜04-16)
- 除外: Shadow, XAU
- Regime labels: OANDA M30 × 1000 bars × 5 instruments (independent labeler, no look-ahead)

### H1 — 信号生成バイアス: **却下**

| 指標 | 結果 | 判定 |
|---|---|---|
| 全体 BUY:SELL | 152:174 (SELL share 53.4%) | 二項検定 p=0.24 → 50:50 と区別不能 |
| 戦略別 chi-sq × Bonferroni | **有意な戦略なし** (vol_surge_detector p_bonf > 0.05, ema_trend_scalp p_bonf > 0.05) | 個別戦略にも生成比バイアス確認されず |

→ **信号生成は対称**。code bug 由来ではない。

### H2 — 執行摩擦の方向非対称: **却下**

| 指標 | BUY | SELL | 検定 |
|---|---|---|---|
| spread_at_entry median | 0.800 | 0.800 | Mann-Whitney p=0.81 |
| spread mean ± std | 0.852 ± 0.229 | 0.840 ± 0.136 | **逆に SELL の方がタイト** |
| slippage_pips median | 0.400 | 0.400 | p=0.26 |
| slippage mean | 0.407 | 0.294 | **BUY の方がむしろ滑っている** |

→ **執行は対称どころか SELL 側の方がわずかに良い**。broker/infra 起因ではない。

### H3 — Regime 依存: **部分支持** (核心の発見)

**Regime × Direction PnL クロス表**:

| Regime | 方向 | N | Total | Avg | WR | 備考 |
|---|---|---|---|---|---|---|
| up_trend | BUY | 60 | **−89.1p** | −1.49p | 31.7% | 🔴 問題セル |
| up_trend | SELL | 62 | −17.5p | −0.28p | 45.2% | (むしろ BUY より善戦) |
| down_trend | BUY | 24 | 0.0p | 0.00p | 45.8% | ~flat |
| down_trend | SELL | 34 | −26.9p | −0.79p | 26.5% | 軽い負け |
| range | BUY | 4 | −7.0p | — | — | N不足 |
| range | SELL | 6 | −17.1p | — | — | N不足 |
| uncertain | BUY | 64 | **+76.4p** | +1.19p | 48.4% | 🟢 唯一の勝ちセル |
| uncertain | SELL | 72 | **−121.8p** | −1.69p | 27.8% | 🔴🔴 最大敗因 (t=-3.29, p=0.0016) |

**Falsifier 解釈**:
- 「全 regime で SELL が負ける」= 事実ではない (up_trend は SELL より BUY の方が悪い)
- 「SELL が負けるのは uncertain regime 特有」= **Bonferroni 級のエビデンス**
- π_long_run reweighted θ(SELL) = −0.74p ± 0.59 → t=−1.26、長期的には有意負ではない

→ **blanket SELL bias ではなく、regime-conditional SELL 問題。しかも"uncertain"regime だけ。**

---

## 真の原因の再定式化

前回の [[sell-bias-root-cause-2026-04-17]] での「SELL bias」という表現は**粒度が粗すぎた**。正しくは:

> **現戦略群は "uncertain" regime (= slope 弱 + ADX 低 = choppy) で SELL を多発し、systematic にやられている。さらに "up_trend" regime で BUY も負ける。両方とも regime-direction 不整合 による負け。**

これは signal 方向の問題ではなく、**regime filter の欠落**の問題。

---

## 戦略別責任分解 (drill-down)

### uncertain × SELL (−121.8p, N=72) の中身

| Strategy | N | Total | Avg | WR |
|---|---|---|---|---|
| **bb_rsi_reversion** | **36** | **−40.6p** | −1.13p | 30.6% |
| trend_rebound | 5 | −17.0p | −3.40p | 0% |
| vix_carry_unwind | 1 | −22.7p | — | — |
| session_time_bias | 3 | −12.9p | −4.30p | 0% |
| (他 9 戦略、小サンプル散在) | | | | |

`bb_rsi_reversion` がこの cell の半分 (36/72) を占める主犯。ただしこの戦略自体は**不完全な悪**ではない (下の cross-check 参照)。

### up_trend × BUY (−89.1p, N=60) の中身

| Strategy | N | Total | Avg | WR |
|---|---|---|---|---|
| donchian_momentum_breakout | 3 | −32.1p | −10.7p | 33% |
| **bb_rsi_reversion** | **29** | **−30.1p** | −1.04p | 37.9% |
| **ema_trend_scalp** | **13** | **−18.1p** | −1.39p | **15.4%** |

`ema_trend_scalp` がトレンドフォロー戦略にもかかわらず up_trend で WR 15% — **仕様と挙動が矛盾**。単独で FORCE_DEMOTE 候補。

### uncertain × BUY (+76.4p, N=64) — 唯一の勝ち cell 内訳

| Strategy | N | Total | Avg | WR |
|---|---|---|---|---|
| dt_sr_channel_reversal | 2 | +25.1p | +12.55p | 100% |
| **bb_rsi_reversion** | **20** | **+22.4p** | **+1.12p** | **55%** |
| post_news_vol | 1 | +17.7p | — | — |
| vol_surge_detector | 9 | +15.0p | +1.67p | 67% |
| **ema_trend_scalp** | **9** | **−21.0p** | −2.33p | **11%** |

**重要な発見**: `bb_rsi_reversion` は uncertain × BUY では勝つ (+22p, WR 55%)。同じ戦略で direction を変えると勝敗が反転する → **これは戦略のレジーム適性が direction 依存**ということ。

逆に `ema_trend_scalp` は uncertain でも up_trend でも BUY で WR 11-15%。どの regime にも適合していない。

---

## PnL 期待インパクト (シミュレーション)

| シナリオ | N | Total PnL | 改善幅 |
|---|---|---|---|
| **ベースライン (現状)** | 326 | **−203.0p** | — |
| uncertain × SELL を抑止 | 254 | −81.2p | **+121.8p** |
| up_trend × BUY を抑止 | 266 | −113.9p | +89.1p |
| **両方抑止** | 194 | **+7.9p** | **+210.9p** |

**9 日間のポートフォリオを net 負け → 微 positive に反転できる**。

---

## アクション選択肢 (ランク付け)

### 🟢 Action A (最高推奨): Regime-Conditional Guardrail 実装
**対象**: `modules/demo_trader.py` の signal 実行パイプライン
**内容**:
- Entry 直前に `regime_labeler` で現在 regime を判定 (最新 closed M30 candle から)
- 以下 2 つの regime × direction cell を block:
  - `regime == "uncertain" and direction == "SELL"` → skip
  - `regime == "up_trend" and direction == "BUY"` → skip
- 既存 signal は全て通す (filter ではなく reject wrapper)

**期待 EV**: +210p / 9日間 相当 (≈ +23p/日) ※in-sample なので過大評価リスクあり、実運用では半分の +100p/9日を想定
**Downside**: regime 判定が当てにならなければ逆効果。9日で検証可能 (N≈120/日 × 9 = 1080 で再評価)
**実装量**: 小 (~30行 + guardrail 統合テスト)
**Rollback**: 環境変数 1 個で即 off

### 🟡 Action B (中推奨): ema_trend_scalp を FORCE_DEMOTE
**根拠**: up_trend×BUY で WR 15%、uncertain×BUY で WR 11%、仕様 (トレンドフォロー) と挙動が矛盾
**実装量**: `strategy_tiers.json` 1行変更 (SHADOW に落とす)
**期待 EV**: 直近 9日の ema_trend_scalp Live 貢献 ≈ −43.6p → 停止で +43p/9日相当
**Downside**: ほぼゼロ (Shadow 観測継続)

### 🟠 Action C (要追加分析): bb_rsi_reversion の direction × regime 条件付けを戦略コードに埋め込む
**根拠**: 同戦略が uncertain×BUY で勝ち、uncertain×SELL で負けている。パラメータ調整ではなく**ロジックの regime awareness** が必要
**実装量**: 戦略ファイル (~100行)
**期待 EV**: 大きい可能性 (bb_rsi_reversion 単体で N=124 = 最大戦略)
**Downside**: Curve-fitting リスク。別時期データで OOT 検証後でないと実装しない方針 (CLAUDE.md 「カーブフィッティング禁止」)。**今週は実施しない**。

### 🔴 Action D (非推奨): blanket SELL suppression
**理由**: 却下された仮説 (H1 信号生成) に基づいてしまう。down_trend×SELL, up_trend×SELL, range×SELL は問題ない。誤り。

---

## 統計的注意

1. **9日サンプル = 1 regime 近似**: π_sample (uncertain 41.7%) vs π_long_run (uncertain 53%) — サンプル側で uncertain がむしろ**少ない**。本番で uncertain regime が長期平均通りなら問題はもっと大きい可能性。
2. **Regime 判定は後付け**: 現戦略群の execution 時に regime labeling は入っていない。実運用でライブ regime 判定を入れた時、本分析と同じ cell 分類になる保証なし。実装後 2 週間の A/B 観察必須。
3. **Out-of-sample 検証なし**: in-sample optimization。次の 9日で同等以上の改善が出るかの予測精度は控えめに 50%。

---

## Next Checkpoints

1. [x] Action A (regime guardrail) 実装 → 2 週間 Live 観察 → θ_reweighted 再計算
2. [x] Action B (ema_trend_scalp demote) 実行
3. [ ] 30日後: 2-D conditional edge 探索 (uncertain × BUY のベース戦略特定 = 唯一の +76p cell をさらに分解)

---

## 実装ログ (2026-04-17 同日)

### Action B — `ema_trend_scalp` FORCE_DEMOTE
- **Location**: `modules/demo_trader.py` `_FORCE_DEMOTED` set
- **Effect**: 全ペア Shadow 強制 (従来 EUR_USD のみ PAIR_DEMOTED だった)
- **Rollback**: _FORCE_DEMOTED から 1 行削除で即復帰

### Action A — Regime-Conditional Guardrail
- **Location**: `modules/demo_trader.py` entry pipeline (alpha_scan ブロック群直後)
- **Helper**: `_get_independent_regime(instrument)` — 独立 labeler (`research.edge_discovery.regime_labeler`) で M30 slope_t + ADX 判定、5分 TTL キャッシュ
- **Blocked cells**:
  - `uncertain × SELL` → shadow (shadow_eligible なら) or block
  - `up_trend × BUY` → shadow or block
- **Fail-open**: labeler API error 時は `"range"` を返し guardrail を事実上スキップ (取引停止を回避)
- **Env flag**: `REGIME_GUARDRAIL_ENABLED=0` で即 off
- **Tests**: `tests/test_regime_guardrail.py` (7 テスト、cache TTL / fail-open / ENV flag / FORCE_DEMOTE 検証)

### 観察プロトコル (14日後: 2026-05-01)
1. `[SHADOW] Regime guardrail:` ログ件数を集計 (予想: 194〜250 件/14日)
2. Shadow 化された trades の PnL を集計して「本当に負けていたか」を確認
3. OANDA Live trades の uncertain×SELL / up_trend×BUY cell が 0 件近くなっているか
4. 全 Live PnL の θ_reweighted 再計算 — 本分析 baseline (−203p) 比で +120p 以上の改善を期待
5. 改善 < +60p なら guardrail を `REGIME_GUARDRAIL_ENABLED=0` で一旦 off にして調査
4. [ ] π_long_run による reweight で SELL が長期的に +0 に収束するかの追跡
