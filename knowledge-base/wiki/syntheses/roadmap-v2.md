# ロードマップ v2.0: A+B+C三位一体 — 月利100%→年利1,200%

**作成日**: 2026-04-14
**設計思想**: データ依存ゲートは待つ、実装はすべて並行
**前提**: v9.0 C1修正済み（サイレント消失バグ解消）、Massive API最優先、Kellyゲート実装済み

---

## 設計原則

```
A（規律）: ゲートを飛ばさない。条件未達なら進まない
B（集中）: 毒を除去し正EVのみに集中。Kelly正転を最速で実現
C（基盤）: テクノロジーで精度と安全性を底上げ
```

**核心**: 「攻撃は精鋭で、防御はゲートで、基盤はテクノロジーで」

---

## 二軸構造: ゲート軸（直列）× 実装軸（並行）

### ゲート軸（データ依存 → 直列、飛ばせない）

```
Gate 0: 基盤確認
  [ ] Massive APIプライマリ動作確認
  [ ] Kellyゲート動作確認
  [ ] 精鋭+SENTINEL+SHADOW三層化完了
  
Gate 1: Kelly正転 (推定 Week 2)
  条件: Aggregate Kelly > 0 (精鋭のみ計算)
  → DD防御 0.2x → 0.3x

Gate 2: DD緩和 (推定 Week 3-4)
  条件: Kelly>0.05 AND FX PnL>+50pip AND 破産確率<70%
  → DD防御 0.3x → 0.5x
  → ★月利100%到達（0.5x × 精鋭BT EV ≈ 117%/月）

Gate 3: 1.0x到達 (推定 Week 5-6)
  条件: PF>1.0 AND N≥100 AND 破産確率<30% AND DSR>0.80
  → DD防御 0.5x → 1.0x
  → 月利235%

Gate 4: Kelly Half (推定 Week 8+)
  条件: DSR>0.95 AND 破産確率<10% AND N≥200 AND 3ヶ月連続黒字
  → lot 3.0x解禁
  → 月利594%
```

### 実装軸（データ非依存 → 全並行、今すぐ着手）

```
Track A: シグナル品質向上
  [即時] VWAPファクターをシグナルスコアに組込み
  [即時] キャッシュTTLをMassive前提に短縮 (1m:30s, 5m:120s)
  [即時] マルチTFコンフルエンスを全TF同一ソース(Massive)で統一

Track B: リスク管理自動化
  [即時] MCゲート自動化（取引前に破産確率チェック挿入）
  [即時] Kelly動的調整基盤（per-strategy Kelly 10トレードごと再計算→lot自動反映）
  [即時] Phase Gate自動チェックAPI（Gate 1-4条件をエンドポイントで公開）
  [即時] ポートフォリオKelly設計（Thorp方式、相関考慮）

Track C: ML/統計モデル
  [即時] HMM 2状態モデル学習開始（Massive長期データでオフライン学習）
  [即時] HMM vs ルールベースのログ並走比較（本番投入はGate 2以降）
  [Gate 2後] HMM本番投入（trending/ranging動的切替）
  [Gate 3後] ポートフォリオKelly最適化ON

Track D: BT自動化
  [即時] Massive長期データ(2年+)による高精度BTパイプライン
  [即時] 新戦略候補 → BT(120日) → 評価 → 昇格をワンコマンド化
  [即時] SHADOW戦略のBT再評価（Massive品質で再テスト → 復活候補発掘）
```

---

## 戦略三層構造

### 🗡 精鋭 LIVE（OANDA転送ON）
| 戦略 | 根拠 | Lot |
|---|---|---|
| vol_momentum_scalp | WR=80% N=10 +21.6pip 唯一の実証正EV | 1.5x boost |

### 🔬 SENTINEL（最小ロット観測）
| 戦略 | 根拠 | 昇格条件 |
|---|---|---|
| orb_trap (3ペア) | BT WR=79%, Live N=2 | Live N≥15, WR≥60%, EV>0 |
| session_time_bias (3ペア) | BT WR=69-77%, 学術★★★★★ | Live N≥15, WR≥55%, EV>0 |
| london_fix_reversal (GBP) | BT WR=75%, 学術★★★★★ | Live N≥15, WR≥60%, EV>0 |
| ema_pullback×JPY | Post-cut N=14 WR=42.9% EV=+1.09 | N≥30, WR≥45%, Kelly>0 |

### 👻 SHADOW（OANDA転送OFF、demoデータ蓄積のみ）
- 残り50+戦略全て
- 目的: 将来のKelly再計算 + レジーム変化時の復活パス
- SHADOWデータはHMM学習にも活用

---

## 週次運用プロトコル

### 毎日
- [ ] Massive API取得状況確認（ログ `[Massive/...]`）
- [ ] 精鋭戦略の発火・P/Lログ確認
- [ ] SENTINEL初回発火チェック

### 毎週金曜
- [ ] Aggregate Kelly再計算
- [ ] 破産確率MC再計算
- [ ] Gate条件チェック（自動APIで）
- [ ] SENTINEL昇格条件チェック
- [ ] SHADOW戦略のBT再評価（Massive品質で）

### Gate通過時
- [ ] KB更新（index.md, changelog）
- [ ] DD防御レベル変更
- [ ] 変更理由とデータ根拠を wiki/decisions/ に記録

---

## リスクゲート（各Gateの停止条件）

| 条件 | アクション |
|---|---|
| 1日 -3%以上の損失 | ロット1段階引下げ |
| 1週間 -5%以上の損失 | 0.2xに強制復帰 |
| Aggregate Kelly < -0.1 | OANDA全転送自動停止（実装済み） |
| Live WR < BT WR - 20pp | 該当戦略のPAIR_DEMOTED |
| 破産確率 > 50% (MC) | DD防御モード強制発動 |
| OANDA接続障害 > 5分 | Emergency Kill Switch |
| Massive API障害 | OANDA→TwelveData→yFinance自動フォールバック（実装済み） |

---

## vol_momentum 1本依存リスクへの対策

**最大リスク**: 精鋭が1戦略のみ → 壊れたら全滅

| 期間 | リスク軽減策 |
|---|---|
| Week 1-2 | SENTINEL 4戦略が保険。C1修正後の発火でN蓄積加速 |
| Week 3-4 | SENTINEL→LIVE昇格で2-3戦略に分散 |
| Week 5+ | 3-5精鋭フルポートフォリオ完成 |
| 並行 | SHADOW戦略のMassive BT再評価 → 復活候補発掘 |

---

## 実装完了済み（本セッション v9.0）

- [x] C1: confバグ修正 → シグナル消失解消
- [x] C2: API Bearer token認証
- [x] C3: XAU pip精度修正
- [x] H1: update_sl_tp ロック追加
- [x] H2: OANDA close 3回リトライ
- [x] A1: lot上限 env設定可（3.0、Kelly Half対応）
- [x] A2: DD分母 env設定可（スケーリング対応）
- [x] A3: Aggregate Kellyゲート（Kelly<0で自動ブロック）
- [x] Massive API最優先昇格（全6ペア×全TF）
- [x] Frontend Bearer token自動付与

## 次に実装するもの（Track A-D 並行）

- [ ] Track A: VWAPファクター組込み
- [ ] Track A: キャッシュTTL短縮
- [ ] Track B: MCゲート自動化（取引前チェック）
- [ ] Track B: Kelly動的調整基盤
- [ ] Track B: Phase Gate自動チェックAPI
- [ ] Track C: HMM 2状態モデル学習開始
- [ ] Track D: Massive BT自動パイプライン
- [ ] 精鋭+SENTINEL+SHADOW三層化の設定変更

---

## Related
- [[roadmap-to-100pct]] — 旧ロードマップ（v1、WARNING付き）
- [[changelog]] — バージョン別変更タイムライン
- [[independent-audit-2026-04-10]] — リスク管理勧告
- [[friction-analysis]] — ペア別摩擦
