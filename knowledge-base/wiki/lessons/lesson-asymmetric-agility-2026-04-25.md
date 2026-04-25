# [[lesson-asymmetric-agility-2026-04-25]] — Asymmetric Agility 規律

**発見日**: 2026-04-25 | **改定対象**: [[lesson-reactive-changes]] / [[lesson-reactive-changes-repeat]]
**発令者**: シニアPM兼クオンツ・リスクオフィサー監査
**ステータス**: ★ 規律改定 (effective immediately)

---

## 1. 病理監査 — 「対称的な遅さ」の構造リスク

[[lesson-reactive-changes]] と [[lesson-reactive-changes-repeat]] は HARKing と感情的反応を抑止する基礎規律として有効に機能してきた。
しかし運用 17 日後、この**「すべての変更に一律 N≥30 / 365日BT を要求する対称ルール」**が以下の致命的副作用を生じている:

| 病理 | 具体例 (今セッションまで観察) |
|---|---|
| **止血遅延** | `vwap_mean_reversion` の Live 占有率 80% × 負 EV 状態が、Patch C (OANDA TRIP) 適用まで複数日継続。Bonferroni 有意の cell が出るまで停止できない構造になっていた |
| **算数破綻の温存** | `bb_rsi_reversion` の WR=32.3% × RR=1.17 → BEV=48.1% 必要 vs 実測 32.3% という**統計検定不要の純粋な算数破綻**に対し、RR 救済 BT を 365日走らせる pre-reg を起案 ([[bb-rsi-rr15-rescue-2026-04-25]]) してしまった |
| **構造バグ放置** | MTF gate の ELITE 免除漏れ・SL 計算と TP 計算の独立 (整合性チェック欠如) など、**コード上明らかなバグ**にも統計検定を要求 |
| **ポートフォリオ硬直化** | 数値的に明白な負 EV 戦略を「N≥30 まで shadow 観察」として保持、defensive lot 0.2x 状態を不必要に長期化 |

**結論**: HARKing 抑止の重みを「促進判定」と「停止/構造修正」に **対称的** に課すのは過誤. 統計的厳格さは**新規エッジの主張**に対してのみ必要であり、**算数 evidence と構造バグ**には別ルールを設けるべき.

→ [[lesson-user-challenge-as-signal]] (ユーザー challenge は診断信号) と整合: 規律自身も **non-symmetric** に進化すべき.

---

## 2. Asymmetric Agility — 3層ルール (effective 2026-04-25)

### Rule 1: Slow & Strict (極遅) — エッジ主張系
**対象**: 新戦略追加 / 新フィルタ導入 / Shadow→Live 昇格 / 新 entry_type 追加 / pair promotion / lot 拡大

**要件 (現行 [[lesson-reactive-changes]] 規定どおり)**:
- 365 日 BT 必須 (N≥30 cell-level)
- Bonferroni 補正 (M = cell 数)
- Pre-registration LOCK (data look 前)
- Wilson 95% / Welch t-test / WF 同符号
- → 詳細: [[claude-harness-design]] §4-5

**根拠**: 偽の聖杯 (curve fitting / HARKing / selection effect) 排除は本質的に統計問題.

### Rule 2: Fast & Reactive (即断) — 損失停止系
**対象**: 既稼働戦略の **OANDA 送信停止** / **Shadow 降格** / **lot ↓** / **pair demotion**

**要件 (緩和)**:
- 数トレード〜N=10 程度の異常値で **Kill-switch 即時発動可**
- 統計有意性は不要、**判断基準は EV / Kelly / 占有率の警報閾値**:
  - Aggregate Kelly < -0.05 (edge severely negative)
  - Live 占有率 > 50% で負 EV
  - Wilson_lo (WR) < BEV_WR by 5pp 以上 (N≥10)
  - Mean loss > 2× mean win (RR 構造破綻)
  - DD 寄与 > +5pp/週
- 停止後の復旧は **Rule 1 経路 (Holdout + 365日 BT)** で再判断

**根拠**: 損失方向のリスク/リワード非対称. 誤って正エッジを停止しても shadow に降格するだけで、**最悪 = エッジ蓄積 1 週遅延**. 一方、負 EV を放置すれば DD 直撃で資本が削れる. **停止は安価、放置は致命的**.

→ [[lesson-vwap-inverse-calibration-2026-04-23]] / [[lesson-confounding-in-pooled-metrics-2026-04-23]] と整合: aggregate 負 EV が cell-level 分解で確証されたら shadow 降格は即時.

### Rule 3: Immediate (即時) — 算数/構造バグ修正系
**対象**: 統計検定不要の自明な破綻
- **純粋な算数破綻**: BEV_WR 計算で観測 WR が必要 RR を構造的に満たさないケース (例: WR=32% × RR=1.17, BEV=48.1%)
- **構造的バグ**: ゲート免除漏れ / SL と TP の独立計算によるリスクリワード不整合 / ペアフィルター抜け / silent except による不発 cell / DB 書込み順序ミス
- **コード演繹で確証可能な誤り**: 単体テスト・式展開・型チェックで検証可能なもの

**要件**:
- 365 日 BT を **スキップ**
- KB lesson + コード差分を **同一コミット** で記録
- Mathematics または code derivation を `analyses/` に文書化
- 修正後の挙動は **Rule 2 監視** (異常値で即停止可) に格下げして観察

**根拠**: 「WR=32% × RR=1.17 が +EV である」可能性は**数学的にゼロ**. これを統計検定で確認するのは「2+2=5 ではないことを 365 日かけて検証する」と同じ. データを待つ必要はない.

→ [[lesson-preregistration-gate-mechanism-mismatch]] と整合: pre-reg gate も「機構と整合した軸」を選ぶべき = **算数妥当性は前提条件**.

---

## 3. 適用判定フローチャート

```
変更提案
   │
   ├─ Q1: 統計的エッジの新規主張か？  ── YES → Rule 1 (BT/Pre-reg/Bonferroni)
   │
   ├─ Q2: 既稼働の損失停止 / 降格 / lot↓ か？ ── YES → Rule 2 (即断, N=10程度の警報閾値)
   │
   └─ Q3: 算数破綻 / 構造バグ修正か？ ── YES → Rule 3 (即時, BTスキップ)
```

**判定の優先順位**: Q3 > Q2 > Q1 (より自明な根拠が勝つ)

**逸脱時の処理**:
- Q3 経路で修正後、結果が悪化 → **Rule 2 で即停止** + lesson 追記
- Q2 経路で停止後、再投入 → **Rule 1 経路で 365 日 BT 必須**
- Q1 経路で BT NULL → **Rule 2 (継続観察) or REJECT**

---

## 4. 既存 lesson との関係

| Lesson | 関係 |
|---|---|
| [[lesson-reactive-changes]] | **継続有効** (Rule 1 領域に限定) |
| [[lesson-reactive-changes-repeat]] | **継続有効** (Rule 1 で N=4日 / N=628 in-sample で BT スキップは禁止) |
| [[lesson-bt-before-deploy]] | **継続有効** (Rule 1 デプロイ系) |
| [[lesson-preregistration-gate-mechanism-mismatch]] | **強化** — Rule 3 で「機構整合」が事前要件 |
| [[lesson-survivor-bias-mae-breaker-2026-04-25]] | **継続有効** (Rule 1 で生存者バイアス対策) |

---

## 5. 監査記録 (本日 2026-04-25 適用例)

### Case 1: bb_rsi_reversion RR 拡張 (Rule 3 適用)
- 観測: WR=32.3% × RR=1.17 → BEV_WR=48.1% 必要
- 数学: BEV_WR = 1/(1+RR) で RR ≥ 2.10 が WR=32% で BEV 越え
- アクション: 365日 BT pre-reg ([[bb-rsi-rr15-rescue-2026-04-25]]) **撤回**, RR=2.5 を **即時** 本番コード適用
- 監視: OANDA TRIP は維持 ([[bb-rsi-fix-rr-2.5-2026-04-25]] 参照), Rule 2 の警報閾値で観察

### Case 2: vwap_mean_reversion Patch C (Rule 2 後付け justification)
- 観測: Live 占有率 80%, post-cutoff EV<0
- アクション: OANDA TRIP 即時発動 (実施済 c195d16)
- 本ルールへの遡及登録: ★ Rule 2 経路の正規化

### Case 3: ELITE_LIVE 3 戦略 0-fire (Rule 3 → Rule 2)
- 観測: c195d16 で MTF gate 免除漏れ (構造バグ)
- アクション: コード即時修正 (実施済), 監視は Rule 2

---

## 6. 適用責任

- **Claude (実装者)**: Q1/Q2/Q3 のいずれに該当するか **判断時にコミットメッセージで明示**
- **ユーザー (PM)**: ルール選択が誤った場合は challenge → 該当 lesson 追記
- **CI/Pre-commit (将来)**: コミットメッセージに `rule:R[1|2|3]` タグ強制 (TODO)

---

## 7. 関連

- [[lesson-reactive-changes]] (Rule 1 詳細)
- [[lesson-reactive-changes-repeat]] (Rule 1 違反パターン)
- [[bb-rsi-fix-rr-2.5-2026-04-25]] (Rule 3 第1適用)
- [[bb-rsi-rr15-rescue-2026-04-25]] (撤回 pre-reg, 参考保管)
- [[claude-harness-design]] (全体規律フレームワーク)
- [[roadmap-v2.1]] (Gate 進捗との接続)
