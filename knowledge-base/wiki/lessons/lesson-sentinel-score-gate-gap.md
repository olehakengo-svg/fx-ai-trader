### [[lesson-sentinel-score-gate-gap]]
**発見日**: 2026-04-20 | **修正**: v9.x (task/priority1-sentinel-score-gate)

- **問題**: Clean Slate(2026-04-16)以降 7日経過時点で Live N=0 / Sentinel N=1（bb_squeeze_breakout のみ、62戦略中）。
  Sentinel経路が `score_gate(score<0)` で1日396件ブロックされ、**shadow データすら蓄積できない**状態だった。
- **症状**: Kelly Gate は N≥30 Live 到達が前提。OANDA転送は `_ELITE_LIVE`/`_PAIR_PROMOTED` 制約で極小
  → 唯一のデータ蓄積経路(Sentinel)が score_gate で閉塞 → 月利100%ロードマップが停滞。
- **原因**:
  1. `score_gate` (modules/demo_trader.py L2761) は「Shadow含め全トレードに適用」として実装された。
     IC=0.089(score) の統計的根拠はあるが、Sentinel は定義上「EV<0 を承知で最小ロットでデータ収集する」戦略 → score_gate の設計目的と直交
  2. spread_wide (L3483) / spike (L3522) は `_is_shadow_eligible` でバイパス済み。
     score_gate のみ同パターンが適用されておらず、Sentinel が spread/spike より厳しいゲートに晒される非対称性があった。
  3. Sentinel `is_shadow=True` は L4179 safety net (`not _is_promoted → is_shadow=True`) で確実に立ち、
     学習エンジン/統計は is_shadow=0 フィルターで遮断される → Sentinel の score<0 通過は**学習汚染リスクゼロ**。
- **修正**:
  - `score_gate` 判定に `_sentinel_score_bypass` (SCALP_SENTINEL ∪ UNIVERSAL_SENTINEL) を追加。
  - Live 昇格戦略(`_ELITE_LIVE` / `_PAIR_PROMOTED`) および FORCE_DEMOTED には従来通り score_gate を適用
    （Live 挙動は一切変更しない）。
  - バイパス発火時は `[SCORE_GATE] Sentinel bypass:` ログで観測性を担保。
- **教訓**:
  1. **Shadow経路のフィルターは「学習汚染リスク vs データ蓄積価値」で判断する** —
     is_shadow=1 強制される戦略は下方リスクゼロ、データ蓄積は上方 → バイパスがデフォルトであるべき。
  2. **フィルター追加時は既存の Sentinel バイパスパターン(L3483/3522)と対称性を取る** —
     新規ゲートだけ Sentinel 適用を忘れると、最も弱い経路にしわ寄せが来る。
  3. **"全トレードに適用"は Sentinel 定義と矛盾する** — Sentinel は「score<0 戦略に最小ロットで枠を与える」
     ための仕組み。Live フィルターを無思考に Sentinel へ拡張すると存在意義を消す。
- **根拠データ**: 1日ブロック計 396件 (score_gate) は本番 block_counts ログより。
  ただし「Sentinel バイパスで月Nいくつ増える」の定量予測は 1日ログからの推定のため、
  本修正は「Live 挙動変更ゼロ + 学習汚染ゼロ + 観測機会の回復」に限定し、lesson-reactive-changes 準拠。
- **関連**: [[lesson-clean-slate-2026-04-16]] / [[lesson-shadow-contamination]] /
  [[lesson-shadow-persistence-bug]] / [[lesson-reactive-changes]]
