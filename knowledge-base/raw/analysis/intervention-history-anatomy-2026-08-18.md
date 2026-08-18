# 介入全史解剖 (2026-08-18) — 09-18 スキャン family A/B 裁定用 dossier

**出所**: 並行セッション (zz-pivot→E21 ライン) の user 要請ワークフロー (wf_3134bcbd、3 agents、
213k tokens)。scratchpad 揮発前に当レーンが回収 (raw JSON =
`intervention-history-anatomy-2026-08-18.json`、result = taxonomy / anatomy / precursors の 3 部)。
**測定規律**: 2026 データ非接触 (2025-01-01 clamp)、介入ラベルは MoF 公式 CSV のみ (価格からの推定なし)。

## family A/B 裁定に効く要点 (起草セッションの要約、原本 = raw JSON)

1. **base rate**: 円買い介入は **39 日/35 年**、金額の 83% が 2022-24 に集中 — family B
   (介入イベント→執行) は**超低頻度イベント設計 (weekend_gap 型)** が前提
2. **dip 買いは「エピソード初撃のみ成立」** — MoF #4 verdict の E-C (2026-05 初撃 +188p リトレース)
   と整合。2022-10 / 2024-07 の**後半介入はトレンド転換と重なり dip 買い即死** →
   **family B の設計本体 = 初撃/追撃の区別**
3. **追撃は初撃後 48h 帯に無条件集中** → 回避ルールの最単純形 (48h flat 化)
4. **初撃の事前条件 4 点** (20bd +480-790p / ライン突破 +200p 以内 / 薄商い窓 / 発言ラダー先行) は
   **N=4 の記述** — false positive 率の測定が family A の仕事 (152 円到達で 13 営業日放置の反例あり)
5. 副産物 lesson 候補: **yfinance JPY=X 日足は UTC 日付が +1 日ずれる (実測)** — JPY 日足を
   yfinance から使う全ハーネスで要注意

## 裁定時の注意 (当レーン付記)

- 上記 1-4 は**記述統計 + N≤4 の事前条件**であり、エッジ主張ではない。family A/B の pre-reg では
  MoF #4 の E-C 符号逆 (介入後 SELL は 2026 で死亡) を必須の負 prior として扱い、
  「回避 (flat 化)」と「ショート」を別 estimand として分離すること
- E-A 実証済みの real-time 検知器 (rule (X,Y)=(2.0, 0.25%)) は family B の入力候補
  (再校正禁止、as-is 流用のみ)
