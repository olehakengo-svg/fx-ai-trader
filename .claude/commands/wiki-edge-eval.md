# Wiki Edge Eval — エッジ仮説の定量評価

knowledge-base/wiki/edges/ にあるエッジ仮説を定量的に評価し、実装するかどうかを判定する。

## 引数
$ARGUMENTS — エッジ仮説名（例: "dealer-inventory-rebalance"）またはALLで全仮説を一括評価

## 手順

### Phase 1: 仮説の読み込み
- `knowledge-base/wiki/edges/$ARGUMENTS.md` を読む（またはedges/*.md全ファイル）
- エッジのStageを確認

### Phase 2: Gate Check（Stage昇格判定）

**DISCOVERED → FORMULATED Gate:**
- [ ] エントリー条件が疑似コードで定義されている
- [ ] SL/TP計算ロジックが明確
- [ ] レジームフィルターが設計されている

**FORMULATED → BACKTESTED Gate:**
- [ ] 摩擦耐性: BEV_WR + 10pp マージン確保
- [ ] 既存戦略との相関 |r| < 0.5
- [ ] 15m以上のTF

**BACKTESTED → SENTINEL Gate:**
- [ ] BT N>=30
- [ ] BT WR > BEV_WR + 5pp
- [ ] WFO(Walk-Forward Optimization) PASS
- [ ] Monte Carlo検定 p < 0.10

**SENTINEL → VALIDATED Gate:**
- [ ] Live N>=50
- [ ] Live Kelly > 0
- [ ] Live PF > 1.0
- [ ] BT/Live乖離 < 15pp

### Phase 3: 判定出力
各エッジ仮説について:
- PROMOTE: 次のStageに昇格 → edge-pipeline.md更新
- HOLD: 現Stageで継続 → 理由を記録
- REJECT: 棄却 → 理由を記録（学術的根拠なし/摩擦超過/冗長）

### Phase 4: wiki更新
- edge-pipeline.md のテーブル更新
- 該当エッジページのStageフィールド更新
- log.mdに評価結果を記録

## 判定基準の厳格さ
- 独立監査勧告: "唯一の正エッジ(bb_rsi×JPY)の保護が最優先"
- 新エッジ追加は「既存エッジを希釈しない」ことが必須条件
- 破産確率85%のシステムに追加するリスク/ベネフィットを明示
