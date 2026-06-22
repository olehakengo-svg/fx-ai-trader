# H4 水平線エッジ探索 — 設計ドキュメント

- **日付**: 2026-06-22
- **作成**: Claude (クオンツアナリスト) + user (goto)
- **ステータス**: DRAFT — user レビュー待ち
- **関連**: roadmap-v2.2-win-conversion / friction-analysis / power_analysis.py
- **動機**: data-driven なエッジ探索。直前に TV "Hull-Donchian FADE" v241 が摩擦控除後マイナス + 241改訂のカーブフィットで失格 (本セッション)。その反面教師として「探索→凍結→単発確認」の規律を最初から組み込む。

---

## 1. エッジ仮説（falsifiable に明文化）

H4(4時間足) のタッチ回数が多い水平線（heavy wall）は、15m スケールで意味のある意思決定点になる、という仮説。2つの**逆方向**エッジを**独立**に検証する。

- **H1 (Reversal / 逆張り)**: 15m 価格が heavy wall に接近し reject されたとき、wall を背にした fade エントリーは、摩擦控除後 EV > 0 を、null(ランダムエントリー) baseline を有意に上回って生む。
- **H2 (Breakout / 順張り)**: 15m が heavy wall を実体で明確に終値ブレイクしたとき、ブレイク方向への continuation は摩擦控除後 EV > 0 を null を有意に上回って生む。

**反証条件（どちらか1つでも該当でそのセルは棄却）**:
- 摩擦控除後 EV ≤ 0
- Wilson lower bound(WR) < n-scaled gate
- null bootstrap p ≥ Bonferroni 補正後 α
- walk-forward 3-fold で正 fold < 2/3
- N < 30

> H1 と H2 は逆方向なので、同一 wall で両方シグナルが出ることは設計上ありうる。混入を防ぐため**別戦略・別統計ファミリー**として扱う（Bonferroni 汚染回避）。

---

## 2. スコープ

- **ペア (6)**: EUR_USD, GBP_USD, USD_JPY, EUR_JPY, AUD_USD, USD_CHF（XAU は KB ルールで除外）。MASSIVE cache にデータが無いペアは Stage 0 で落とす。
- **エントリー TF**: 15m。**水準 TF**: H4。
- **戦略数**: 2（reversal, breakout）。水準検出コアは共有。
- **統計ファミリー**: 最大 6 pairs × 2 strategies = **12 cell**。family size は Stage 2 実行**前**に pre-reg doc で確定（後から増やさない）。
- **Out of scope (YAGNI)**: retest エントリー版 / ラウンドナンバー confluence / volume 確認（FX volume は信頼性低）/ live 昇格（shadow で N 蓄積後の別 task）/ 多パラメータグリッド探索。

---

## 3. 水準検出コア（reversal/breakout 共有）

`detect_h4_heavy_walls(h4_df, params) -> list[(price, weight)]`（純関数, unit-test 可）

1. 入力は **closed H4 bar のみ**（`modules/htf_data_source.fetch_htf_candles` の complete=True、look-ahead protection 済み）。
2. Williams Fractal `n=fractal_n` で swing high/low を検出（lookback = `lookback_h4` 本）。
3. swing 群を価格近接でクラスタ化（tolerance = `kde_tol × ATR14_H4`）。1D KDE でクラスタ中心を求め、level price = クラスタ centroid、weight = クラスタ内 swing 数（タッチ回数）。
4. **heavy wall** = weight ≥ `min_touches`。
5. 各 15m bar 評価時点で、その bar より**厳密に過去**の H4 bar からのみ wall を構成する（causal 保証、テストで検証）。

既存 `tools/sr_weight_gate_audit_v2.py` の KDE weight ロジックを流用候補。

---

## 4. 15m エントリートリガー

closed 15m bar でシグナル判定 → **次 bar の open でエントリー**（intrabar look-ahead 排除）。

- **Reversal**:
  - resistance wall: 15m high が wall ± `entry_tol × ATR14_15m` 帯に侵入 かつ 15m が wall 下側で終値（rejection wick）→ 次 bar SHORT。
  - support wall: 対称で LONG。
- **Breakout**:
  - 15m が wall を `brk_buffer × ATR14_15m` 超で終値ブレイク かつ ブレイク bar の実体率 (|close-open|/(high-low)) ≥ `body_frac` → ブレイク方向に次 bar エントリー。

---

## 5. SL / TP（pip ベース、摩擦はペア別 friction table で控除）

- **Reversal**: SL = wall を `sl_buf × ATR` 超えた先。TP = 利益方向の次 heavy wall（無ければ `tp_cap × R`）。
- **Breakout**: SL = wall の内側へ `sl_buf × ATR` 戻った位置。TP = measured move もしくは次 wall、`tp_cap × R` で上限。
- exit はSL/TP 到達 or `max_hold` 本 (15m) 経過のいずれか早い方。

---

## 6. 凍結パラメータ（pre-registered。Stage 2 確認では再調整しない）

| param | 初期値（Stage1 で確定） | 備考 |
|---|---|---|
| fractal_n | 2 | swing 感度 |
| lookback_h4 | 180 本 (≈30 営業日) | wall 構成窓 |
| kde_tol | 0.5 × ATR14_H4 | クラスタ許容 |
| min_touches | 3 | heavy wall 閾値 |
| entry_tol | 0.25 × ATR14_15m | 接近帯 |
| brk_buffer | 0.5 × ATR14_15m | ブレイク確定 |
| body_frac | 0.6 | ブレイク bar 実体率 |
| sl_buf | 0.5 × ATR | SL バッファ |
| tp_cap | 2.0 R | TP 上限 |
| max_hold | 48 本 (12h) | 強制 exit |

> 初期値は既存コード慣習 + Stage1 IC 分析で確定する。**確定後は触らない**のが本設計の肝（v241 の逆）。

---

## 7. 方法論 A: 探索 → 凍結 → 単発確認

データを時系列で **train 60% / holdout 40%** に分割（chronological、post-cutoff 起点）。

- **Stage 1 — 探索 (train slice のみ)**: H4-level 相互作用イベントを全ログ化。特徴量 = {touch_count, wick_ratio, close_position, approach_velocity, h4_bias_alignment, session, dist_to_next_wall, atr_regime}。各特徴量の forward-return **IC を計測**（カーブフィットせず相関だけ見る）。結果から §6 の凍結スペックを**1セットに確定**し pre-reg doc に記載。
- **Stage 2 — 確認 (holdout、未見)**: 凍結スペックで reversal/breakout × 6ペアを**一発 BT**。holdout 内で walk-forward 3-fold。
  - セル別統計: N / WR / Wilson lower (n-scaled gate) / 摩擦控除 EV / PF / null bootstrap p / walk-forward fold consistency。
  - Bonferroni: family size (=確定 cell 数) で α 補正。
- **昇格ゲート（全通過のみ）**: N≥30 ∧ Wilson_lo ≥ n-scaled gate ∧ 摩擦控除 EV>0 ∧ null bootstrap p < Bonferroni α ∧ walk-forward ≥2/3 正。
  - 生存セル → **shadow 投入が先**（直 live 禁止、KB ルール）。

---

## 8. アーキテクチャ / コンポーネント

**新規**:
- `strategies/daytrade/h4_level_core.py` — `detect_h4_heavy_walls()`（純関数）
- `strategies/daytrade/h4_level_reversal.py` — `H4LevelReversal(StrategyBase).evaluate(ctx)`
- `strategies/daytrade/h4_level_breakout.py` — `H4LevelBreakout(StrategyBase).evaluate(ctx)`
- `tools/h4_level_edge_explore.py` — Stage1 IC 分析（train slice）→ feature-IC テーブル出力
- `tools/h4_level_shadow_bt.py` — Stage2 凍結スペック BT（2戦略×6ペア）→ セル別統計テーブル
- `knowledge-base/wiki/decisions/h4-level-edge-pre-reg-2026-06-22.md` — family size / 凍結スペック / ゲートを **Stage2 実行前に LOCK**

**再利用**:
- `modules/htf_data_source.fetch_htf_candles`（native H4, causal）
- `app.py get_htf_bias()`（H4 バイアス特徴量）
- `research/edge_discovery/power_analysis.py`（wilson_lower, n_scaled_wilson_gate, bonferroni_per_family）
- `research/edge_discovery/walk_forward_scanner.py`（walk_forward_3fold）
- `tools/empirical_validator.py bootstrap_ci`
- friction table（friction-analysis.md）

**登録（Stage2 で生存した場合のみ、別 task で deploy エージェントに委譲）**: `strategies/daytrade/__init__.py` / `DT_QUALIFIED` (app.py) / 必要なら `_UNIVERSAL_SENTINEL`。

---

## 9. テスト

- `detect_h4_heavy_walls`: 合成データ（既知 swing 配置）→ 期待 level/weight。
- 因果性テスト: 評価時点より未来の H4/15m bar を一切参照しないことを assert。
- `evaluate()`: 有効な Candidate（entry/sl/tp/entry_type）を返す。heavy wall 無し → WAIT。
- 摩擦控除が EV 計算に入っていることの確認。
- silent except 禁止（KB lesson）: skip は理由付きで log。

---

## 10. エラーハンドリング

- H4 履歴不足 → no signal（crash しない）
- heavy wall 無し → WAIT
- ATR が NaN → skip（理由 log）
- `except Exception: pass` 禁止 — 「不発」と「ゼロ件」を区別可能に保つ。

---

## 11. 成功基準

- Stage2 で **1セル以上**が全昇格ゲートを通過 → shadow 投入候補 → エッジ探索成功。
- 全セル棄却でも「H4 heavy wall に 15m トレード可能なエッジは(この凍結スペックでは)無い」という**クリーンな反証**が得られれば、それも成功（v241 のような汚染データを残さない）。
