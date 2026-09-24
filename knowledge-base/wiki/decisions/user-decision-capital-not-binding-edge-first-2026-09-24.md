---
title: user 決裁 — OANDA 固定・資金は必要時追加・優先はエッジ見極めと勝てるトレード増 (2026-09-24)
tags: [decision, user-decision, u3, mission, priority]
status: active
---

# user 決裁 (2026-09-24): OANDA 固定 / 資金は必要時追加 / 優先 = エッジ

## 1. 原文 (要旨)

> OANDA は仕様だから変えられない。足りなくなったらバジェット追加するから OK。それよりもエッジをしっかり見極めて、勝てるトレードを増やすことが重要。

会話の文脈: 09-20 [[path-to-win-decision-memo-2026-09-20]] / 09-22 [[path-to-win-reassessment-2026-09-22]] / 09-23〜24 の追加分析 (入金 feasibility 17 エージェント、レバー 6 本 12 エージェント) で Claude が「資本税 0.755% > M2 0.5% の不動点」「keeper ゼロ化 (別口座で出来高合算 / venue 変更) が最大レバー」を繰り返し提示したのに対する user の裁定。

## 2. 決裁として扱う 3 点

| # | 決裁 | 影響を受ける既存項目 |
|---|---|---|
| 1 | **OANDA は仕様で不変** — venue 変更 / 同一会員の別口座で出来高合算 (M1 レバー) / keeper ゼロ化 / U3 (ii) 縮退 は**提案しない**。keeper ¥2,080/月 は固定費として受容 | packet UD3 (会員合算の OANDA 問い合わせ) → **見送り**扱い。D3 の選択肢 (ii) 縮退 / (iv) 別口座 は候補から外す。memo Rank 8 venue feasibility (90 日側) → 不要 |
| 2 | **資金は足りなくなったら user が追加** — U3 の方向 = **(i) 入金**。額・時点は未定 (D3 の数字は別途)。floor ¥262k / F4 資金時計は「user が先回りで補充する」前提となり、kill 条件としての重みが下がる | D3 (i) 確定方向。F4 (registry `project-falsification-f4-nav-floor-clock`) は「決裁を強制する」機能を失い、期限管理はパケット側 (11-30)。⚠️ 入金は F4 推定器・M2 定義 A の読み手を汚染する — PR #295 (TRANSFER_FUNDS 調整) の着地を確認して引用 |
| 3 | **優先 = エッジをしっかり見極めて勝てるトレードを増やす** — 資本税・分母レバーの議論は打ち切り。資源配分は研究供給 (新 family 起案、shadow readout、pre-reg) と fill 変換 (live 資格セルの N 時計)、計測整合に寄せる | roadmap の資源配分 (研究 6 : 執行 4 — user 合意 2026-08-05、原本は Claude MEMORY `feedback_cell_portfolio_thesis_2026_08_05`。KB 側に単独ページは無く、[[roadmap-v2.3-payoff-friction-repair]] の配分と整合) を維持。資本ゲートで park されていた供給枝 — U4 (a) 有償 probe ((a-1) CME DataMine FX options 歴史 等)、(b) daily+ クロスセクショナル、(c) 非 FX (**OANDA 銘柄内に限る**) — は「資本が先」の前提が外れたため再評価対象 ([[supply-space-feasibility-2026-09-17]] §3〜4) |

## 3. 未決裁のまま残るもの

- **U2 (資本上限の 1 数字)**: 未決裁。月額 ¥数十万級の有償データ購読 (supply-space §1.3「U2 ≥¥1M でないと自動 NO」) は額を user に明示確認してから起案する
- **D1 (M2 会計定義 A/B)**, **D2(i) (DD lever 乗算/非乗算)**, **D5 (carry_dip disposition)**, **D8 (velocity_down の 4 原則解釈)**: 未決裁、期限 11-30 (packet)。本決裁 3 は D5/D8 を「勝てるトレードを増やす」側の最優先 user 項目にする
- **D3 の額と時点**: 方向のみ確定

## 4. Claude の運用への反映

- 「勝てる方法」を問われたら資本 / keeper の話を先に出さない。**研究供給 / shadow readout / fill 変換 / 計測整合の 4 軸**で答える
- 資本ゲートの供給枝 U4 (a)(b)(c) を scan#6 (10-18) の議題に「資本制約なし」で再上程する。(c) は OANDA JP の取扱銘柄内 (FX + 貴金属 CFD 等、要確認) に限定
- 4 原則 (攻める / デスゾーン = 動的のみ / 静的時間ブロック禁止 / 攻撃は最大の防御) との整合: 本決裁は原則 1・4 を強化する方向
- registry は **message 文言のみ本 PR で同期済み** (resolved フラグは一切変更しない — 2026-09-23 user 指示「勝手に resolved 化しない」に従い、resolved 化は user 既読確認後の follow-up): `project-falsification-f4-nav-floor-clock` (TRIGGERED 時の起票を「入金の額と時点」のみに改文、強制機能の消失を明記) / `integrated-decision-packet-d1-d12` (U3 = 入金の額と時点のみ) / `edge-supply-scan-monthly` (10-18 議題に U4 (a)(b)(c) の資本制約なし再上程を追加)。packet 本文は UD3 返答プロンプト・D3 (ii)(iii)(iv)・§3.6 UD3 一次確認・§6-5 U3 (ii) を取り消し線 + 廃止日で表記 (歴史記録として残置)

## 5. 関連

- 直前分析: 入金 feasibility (09-23、6 主張 × 2 レンズ反証、3 主張が部分 refuted) / レバー 6 本 (09-24、6 反証全てが部分 refuted) — いずれも「keeper ゼロ化が最大」を結論したが、本決裁で選択肢から外れた。数字自体 (単一セル寄与上限 0.166〜0.432%/月 は NAV 不変、G3 N≥30 が binding) は不変で、歴史記録として保持
- MEMORY: `feedback_capital_not_binding_edge_first_2026_09_24.md`
