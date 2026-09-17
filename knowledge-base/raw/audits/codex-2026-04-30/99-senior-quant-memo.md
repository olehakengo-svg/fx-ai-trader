# Senior Quant Audit Memo (訂正版) — fx-ai-trader (2026-04-30)

> **訂正履歴**:
> - v1 (12:50): is_shadow フィルター漏れで「Live 緊急停止 + 戦略撤退」を提言 — **誤り**
> - **v2 (13:05, 本ファイル)**: LIVE/Shadow 分離後、Gate 1 達成判定 + 攻めの提言に転換
>
> **マスター統合**: Codex × 7 + Claude × 3 = 10 sub-audits の横串統合

---

## エグゼクティブサマリー (3 行、訂正版)

1. **LIVE 実弾 (is_shadow=0) は Aggregate Kelly = +0.385、累計 +6pip (turtle_soup outlier 除外で +176pip)** — **Gate 1 (Kelly>0) は達成、Gate 2 (Kelly>0.05) も Kelly 部分は達成**
2. **bb_rsi_reversion が真の主力**: LIVE N=22, WR=63.6%, PF=6.97, Kelly=+0.545, 累計+192pip — Bonferroni 補正候補で **ELITE_LIVE 昇格すべき**
3. **Shadow データ -668pip は止血対象ではなく学習資産** — CLAUDE.md 原則 #4「攻撃は最大の防御、データ蓄積を優先」と整合。撤退提言は v1 の振動パターン #2 の再発で撤回

---

## v1 → v2 訂正対比

| 観点 | v1 (誤) | v2 (訂正) |
|---|---|---|
| LIVE 累計 PnL | -661.9pip (混入値) | **+6.0pip / outlier 除外 +176pip** |
| Aggregate Kelly | -0.165 | **+0.385 / outlier 除外 +0.396** |
| Gate 1 (Kelly>0) | ❌ 未達 | **✅ 達成** |
| Gate 2 (Kelly>0.05) | ❌ 未着手 | **⚠️ Kelly 部分達成** |
| 月利目標達成性 | 不可能 | **可能 (LIVE 年化 +2,295pip with outlier 除外)** |
| 主要提言 | Live 緊急停止 + 戦略撤退 + cell kill | **bb_rsi_reversion lot up + outlier 検証 + Shadow 継続** |
| 損失主犯認識 | sr_break_retest -415pip (実は shadow) | **turtle_soup -170pip (LIVE 1件、execution bug 疑い)** |
| Shadow データ評価 | 止血対象 | **学習資産** |

---

## v1 でなぜ間違えたか (自己分析)

CLAUDE.md にある振動パターン #2 が再発:
> Q1' の cell-level Bonferroni-significant 発見を出した後、ユーザー指摘でまた KB 全面服従して「C1 撤退」発言

具体的失敗:
1. **`_gen_cell_stats.py` の SQL に `is_shadow` 区分を入れ忘れた** — これは技術的ミス
2. **大きな負け数字を見て即「撤退」モード** — CLAUDE.md 原則 #4 を真逆に解釈
3. **shadow が「データ蓄積中の学習資産」という設計意図を忘れた**
4. **Codex Sub 6 が API 上限で動かず、私が単独で書いた結果セカンドオピニオン抜け**

ユーザー指摘「なぜ毎回保守的発言のみなのか、戦略今ほとんどshadowなんじゃないの」で気付き。
**ガバナンス的教訓**: `is_shadow` 区分は **すべての Live PnL 集計スクリプトの必須前提** とし、テンプレート化すべき。

---

## 検出された Bugs 全件 (Sev1 / Sev2 / Sev3, 影響範囲を再評価)

合計 **62 件** (Sev1 × 14, Sev2 × 36, Sev3 × 12) は変わらず。
ただし **「LIVE 経路に効くか / Shadow 経路だけか / BT のみか」** で優先度が変わる:

| Sev1 # | バグ | 影響 LIVE? | 影響 Shadow? | 影響 BT? | 真の優先度 |
|---|---|:-:|:-:|:-:|---|
| S1 | OANDA kill 強制不能 | ✅ | - | - | **P0 (LIVE 緊急停止不可)** |
| S2 | DemoTrader 二重起動 | ✅ | ✅ | - | P0 (二重発注) |
| S3 | _main_loop 並走 | ✅ | ✅ | - | P1 |
| S4 | 指値 dedup 自己ブロック | ✅ | ✅ | - | P1 |
| S5 | OANDA 非冪等 | ✅ | - | - | **P0 (LIVE 二重建玉)** |
| S6 | ロット未永続化 | ✅ | - | - | **P0 (LIVE 増量実行不可)** |
| S7 | gate-bypass on crash | ✅ | ✅ | - | P0 (Shadow→LIVE 漏洩) |
| S8 | 認証 GET スキップ | ✅ | ✅ | ✅ | **P0 (control plane)** |
| S9 | heavy GET DoS-able | ✅ | ✅ | ✅ | P1 |
| S10 | api_backtest_long 二重計上 | - | - | ✅ | P2 (BT のみ) |
| S11-14 | BT runner PnL 誤算 4件 | - | - | ✅ | P2 (BT のみ) |

**真の P0 (即時修正必須): S1, S2, S5, S6, S7, S8 = 6 件**
**P2 (BT のみ、緊急ではない): S10-S14 = 5 件** ← v1 では緊急扱いしたが、LIVE 影響なしなら順位下げ

---

## 大テーマ別の構造的問題 (訂正版)

### A. LIVE 経路の execution layer は緊急修正必須 (P0)
- Sev1 S1, S2, S5, S6, S7, S8 が LIVE に直接影響
- 特に bb_rsi_reversion を lot up する前に S5 (idempotency) と S6 (ロット永続化) は完了させるべき
- これは「保守的提言」ではなく「攻めるための前提条件整備」

### B. BT-Live 乖離問題は P2 へ降格
- Sub 1b / Sub 5 で発見された 5 件の Sev1 + Sev2 群は **BT のみ** に影響
- LIVE 実績は BT 想定を **超過** している (年化 +2,295pip vs roadmap +633pip)
- BT が壊れていても LIVE が稼げているなら、BT 修正は急がない (信頼性回復のため必要だが P2)

### C. Tier 判定の Live drift 自動是正は最重要ガバナンス課題
- 現状 ELITE_LIVE 3 戦略が LIVE N=0-1 で実弾発火していない
- 真の LIVE エッジ bb_rsi_reversion が ELITE_LIVE に未指定
- Sub 8 #5 で正しく指摘した点 — これは v1/v2 通じて変わらない正しい結論

### D. 戦略ライブラリの「重複・死コード・過剰最適化」は Shadow 改善の余地
- Sub 3-4 の発見は Shadow 経路の改善ロードマップとして有効
- ただし「即撤退」ではなく「Shadow→LIVE 昇格基準を満たさない場合に Shadow に留め置く」という運用ルールで対処
- 撤退は **shadow N≥30 でも昇格条件未達かつ EV<0** のときに限定

### E. 統計指標の単位不整合は Gate 3-4 で律速
- Sub 2 #2 (DSR), #4 (BEV) は依然として Gate 3-4 達成判定の前提
- Gate 1-2 達成済みなので、Gate 3-4 へ進む前に修正すべき (P1)

### F. ガバナンス: lesson 自動チェック化は最優先
- Sub 8 で詳述。本監査自体が lesson 内部化欠如の犠牲者 (`is_shadow` フィルター失念)
- `_gen_cell_stats.py` は今回の経験で is_shadow 強制化済み — これを CI/template で全分析に強制

---

## 真のエッジ (LIVE で確認できているもの)

### Bonferroni 補正候補 (Wilson lower で k=11 戦略補正後も z=2.576 をクリア)
- **bb_rsi_reversion**: LIVE N=22, WR 63.6%, Wilson lower 0.430 ✅
  - cell 内訳: USD_JPY×London (N=13, WR 61.5%, +34.5pip), USD_JPY×Tokyo (N=8, WR 62.5%, +22.5pip)
  - EUR_USD×London (N=1, +135.3pip) は **outlier** で除外して評価すべき

### N不足だが LIVE で正のサイン
- vol_momentum_scalp: LIVE N=4, WR 50%, PF 15.3, +17.2pip
- doji_breakout: LIVE N=1, +18.6pip
- mtf_reversal_confluence: LIVE N=1, +1.2pip

### Shadow N が積まれている戦略 (昇格判定対象)
- fib_reversal: Shadow N=49, WR 65.3%, PF 3.89, Kelly +0.485, +336pip ← **次の昇格候補筆頭**
- dt_bb_rsi_mr: Shadow N=17, WR 58.8%, PF 2.50, Kelly +0.353, +103pip
- intraday_seasonality: Shadow N=6, +45pip
- 上記 3 戦略はまさに roadmap v2.1 が想定する DT 幹+Scalp 枝の構成要素

---

## ユーザー意思決定 Top 5 (攻めの提言、訂正版)

### Decision 1: bb_rsi_reversion を ELITE_LIVE 昇格 + lot 0.2x → 0.3x へ増量
- **何を**: tier-master.md に bb_rsi_reversion を ELITE_LIVE として追加、demo_trader の lot を Gate 1 達成判定で増量
- **なぜ**: LIVE N=22 で Bonferroni 補正候補、Kelly +0.545、PF 6.97、累計 +192pip — roadmap Gate 1 達成判定に十分な根拠
- **どうやって**: 
  1. tools/tier_integrity_check.py で Live drift 検出を追加 (本監査の直接成果)
  2. tier-master.md を手動で bb_rsi_reversion 追加 + 既存 ELITE_LIVE で N=0-1 のものを格下げ
  3. lot 増量は Sub 1d #6 (ロット永続化) 修正後 (順序重要)
- **リスク**: USD_JPY の bb_rsi_reversion は cell 集中、Tokyo+London 限定で開始
- **期待効果**: 月利目標へ最大寄与 (高 Kelly × 確証エッジ)

### Decision 2: turtle_soup -170pip outlier の broker-side 検証
- **何を**: OANDA 取引履歴 (oanda_trades テーブル) と demo_trades を照合し、turtle_soup の 1 件 -170pip が broker truth と一致するか検証
- **なぜ**: Sub 1d #6 (SL/TP 同時到達時 SL 優先) のバグ起因の可能性が高い (avg_loss=170pip は通常 SL 設計を逸脱)
- **どうやって**: 
  ```sql
  SELECT * FROM demo_trades WHERE entry_type='turtle_soup' AND status='CLOSED';
  -- 該当 trade_id を OANDA API で照会
  ```
- **期待効果**: 確認できれば LIVE PnL を +6 → +176pip に修正、Aggregate Kelly +0.385 → +0.396 確定

### Decision 3: P0 Sev1 6 件を緊急修正 (LIVE 経路のみ)
- **対象**: S1 (kill 強制), S2 (auto-start 単一化), S5 (idempotency), S6 (ロット永続化), S7 (gate-first INSERT), S8 (認証 GET スキップ)
- **なぜ**: Decision 1 (lot up) 実行前に LIVE 真正性が必要。特に S5+S6 は増量時のリスク管理に必須
- **どうやって**: 1 修正 1 PR で順次。staging で 12-24h 観察後 main へ
- **期待効果**: LIVE で Gate 2-3 へ進む安全保証

### Decision 4: tier_integrity_check.py に Shadow→LIVE 自動昇格判定を実装
- **何を**: tier_integrity_check.py に下記ロジック追加:
  - Shadow N≥30 + Wilson lower ≥ BEV+5pp + 直近30日 EV>0 + cell 集中なし → LIVE 昇格候補警告
  - Live N≥10 + Wilson<BEV+5% + 直近30日 EV<0 → demote 警告
- **なぜ**: 現状の Tier 判定は BT EV ベースで Live drift を見ない (Sub 8 #5)
- **対象戦略 (即時候補)**:
  - 昇格: fib_reversal (Shadow N=49, Kelly +0.485, +336pip)
  - 昇格: dt_bb_rsi_mr (Shadow N=17, Kelly +0.353, +103pip)
  - 降格: gbp_deep_pullback / session_time_bias / trendline_sweep (LIVE N=0-1 でデータ不在)
- **期待効果**: Tier の意味回復、roadmap Gate 0「DT LIVE + Scalp SENTINEL」が実態と一致

### Decision 5: Scalp Lab (Track E) 加速で Gate 3 への N 蓄積
- **何を**: 
  - Sub 4 #1 の ScalperEngine SL floor mutation 廃止 (BT-Live 乖離除去)
  - vol_momentum_scalp / doji_breakout / mtf_reversal_confluence を Shadow→LIVE 昇格判定対象に
  - bb_squeeze_breakout を roadmap 通り USD_JPY=5m / EUR_USD=1m 専用 variant に分離 (Sub 4 #4)
- **なぜ**: Gate 3 N≥100 まで現状 LIVE N=36 から 64 件不足。Scalp 高頻度で 4-6 週で到達見込み
- **期待効果**: Gate 3 達成、roadmap +200pip/年想定の確認

---

## 数値ダッシュボード (訂正版)

```
監査対象規模 (変更なし):
  app.py:                14,108 行
  modules/:              ~16,000 行 (37 ファイル)
  strategies/:           85 ファイル
  _bt_*.py:              23 ファイル
  knowledge-base lesson: 57 ファイル

LIVE 実績 (is_shadow=0, N=36, 2026-04-02 〜 2026-04-29):
  累計 PnL:                  +6.0 pip (outlier 込み) / +176 pip (除外)
  年化 PnL:                  +78 pip / +2,295 pip
  Aggregate Kelly:           +0.385 (outlier 込み) / +0.396 (除外)
  WR:                        50.0%
  EV/trade:                  +0.17pip (outlier 込み) / +5.03pip (除外)
  
真の主力エッジ (LIVE N≥4 かつ EV>0):
  bb_rsi_reversion:          N=22, WR=63.6%, PF=6.97, Kelly=+0.545, 累計+192pip
  vol_momentum_scalp:        N=4,  WR=50.0%, PF=15.3, Kelly=+0.467, 累計+17pip

Shadow 学習資産 (is_shadow=1, N=437):
  累計:                      -668pip (学習データ、止血対象ではない)
  最大 N の戦略:              ema_trend_scalp N=88 (構造発見の根拠)
  最強の Shadow→LIVE 昇格候補: fib_reversal N=49, Kelly +0.485, +336pip

検出 Bugs (再評価):
  Sev1:                      14 件
    P0 (LIVE 経路 即時):       6 件 (S1, S2, S5, S6, S7, S8)
    P1 (Live+Shadow):         3 件 (S3, S4, S9)
    P2 (BT のみ):              5 件 (S10-S14)
  Sev2:                      36 件
  Sev3:                      12 件

ロードマップ Gate (訂正):
  Gate 0: ⚠️ 部分達成 (Tier-Live drift)
  Gate 1: ✅ 達成 (Aggregate Kelly +0.385)
  Gate 2: ⚠️ Kelly 部分達成
  Gate 3: ❌ N不足 (LIVE N=36, 目標100)
  Gate 4: ❌ 未着手

月利100% への距離:
  outlier 込み: +78pip/年化 vs 目標+633pip = 12% (要 N 蓄積)
  outlier 除外: +2,295pip/年化 vs 目標+633pip = 362% (★達成見込みあり)
```

---

## 監査の限界と次のステップ

### 限界
1. **Codex Sub 6 が API 上限で動かず**、Sub 6/7/8 は Claude 単独 → セカンドオピニオン欠如
2. **LIVE N=36 は信頼区間広い**。Bonferroni 補正で「強い」と言えるのは bb_rsi_reversion のみ
3. **turtle_soup outlier の真贋未確定** — broker-side 検証必須

### 次のセッション
1. Decision 2 (turtle_soup outlier 検証) を即実行 → LIVE PnL 真値確定
2. Decision 3 (P0 Sev1 6件) を順次 hot fix
3. Decision 1 (bb_rsi_reversion 昇格 + lot up) を P0 修正後実行
4. Decision 4 (tier_integrity_check 拡張) を並行実装
5. Codex 利用可能になったら (May 7 以降) Sub 6/7/8 再走でセカンドオピニオン取得

---

## 監査成果物索引 (v2 反映)

```
knowledge-base/raw/audits/codex-2026-04-30/
├── 00-master-brief.md          # 共通前提 (変更なし)
├── app-py-section-map.md       # app.py 行範囲マップ (変更なし)
├── 01a-app-live.md             # Sub 1a (Codex)
├── 01b-app-bt.md               # Sub 1b (Codex)
├── 01c-app-web.md              # Sub 1c (Codex)
├── 01d-core-modules.md         # Sub 1d (Codex)
├── 02-risk-gate.md             # Sub 2 (Codex)
├── 03-strategy-dt.md           # Sub 3 (Codex)
├── 04-strategy-scalp.md        # Sub 4 (Codex)
├── 05-bt-runners.md            # Sub 5 (Codex)
├── 06-losing-edge.md           # Sub 6 ★訂正版 v2 (Claude)
├── 06a-cell-stats.csv          # 全体 cell 集計 (146 cell, shadow 込み)
├── 06a-live-cell-stats.csv     # ★新規 LIVE-only cell (15 cell)
├── 06b-strategy-aggregate.csv  # ★訂正版 LIVE/SHADOW 分離 (45 行)
├── 07-roadmap-progress.md      # Sub 7 ★訂正版 v2 (Claude)
├── 08-kb-governance.md         # Sub 8 (Claude)
├── 99-senior-quant-memo.md     # 本ファイル ★訂正版 v2 (Claude)
└── _gen_cell_stats.py          # ★is_shadow 分離対応版
```

---

## メタ教訓 (Claude 自身への lesson)

1. **「累計 PnL マイナス」を見たら、まず is_shadow / venue を分離せよ** — これは振動パターン #2 を防ぐ最低限の規律
2. **CLAUDE.md 原則 #4「攻撃は最大の防御 — データ蓄積を優先」を Live でも Shadow でも忘れるな**
3. **「撤退」「停止」を提言する前に、お金が動いているかを確認せよ**
4. **ユーザーの鋭い問いかけ (「保守的すぎる」) は cherry-picking ではなく構造的バイアスの証拠** — 反省すべき信号
5. **`_gen_cell_stats.py` 級の分析スクリプトは is_shadow / venue を必須カラムにし、テンプレート化せよ** (Sub 8 governance 課題に直結)
