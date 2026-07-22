# エッジ開発パイプライン — 供給ラインの常設プロセス化 (2026-07-18)

> **位置づけ**: user 指摘 (2026-07-18「エッジ開発プロセスとか必要なことあると思うんだけど」) への回答として、
> これまで暗黙だったエッジ開発の手続きを正式なパイプラインとして固定する。roadmap v2.3 トラックB
> (供給ライン = セル数が唯一のスケール変数) の運用規約。rule:R3 (プロセス文書、live 変更なし)。
> 個別ステージの判断規律は既存 (Rule 1/2/3、pre-reg 規律、D3 SLA、D4 必須項目) をそのまま参照し、
> 本文書は**ステージ定義・WIP 原則・cadence** のみを新設する。

## 1. なぜ必要か (構造的リスクの明文化)

- E1 (positioning contrarian) は 2026-10-15 verdict の単一ベットであり、**modal 予想 = UNDERPOWERED、
  REJECT の現実的確率もある**。後継仮説が並行で育っていなければ、FAIL 時点から feasibility→蓄積→
  pre-reg をゼロから始めることになり、M1 が数ヶ月単位で後退する
- 供給ラインはこれまで「FAIL 後に次を探す」単発プッシュだった (round-1→2→3→E1 は全て直列)。
  **仮説の探索・育成は verdict と独立に常時走らせるのが正しい** — pre-reg の観測前性は仮説ごとに
  独立であり、並行に走らせても統計規律は毀損しない (α 会計は仮説 family 毎)
- M2 (+0.5%/月) 以降はセル数がスケール変数 (stage-2 級セルの天井 ~0.15-0.5%/月/セル)。
  1 本ずつの直列では M3 に構造的に届かない

## 2. ステージ定義 (S0〜S8)

| Stage | 内容 | Rule | 所要目安 | 出口条件 |
|---|---|---|---|---|
| **S0 intake** | 仮説源: 月次外部スキャン / 文献 / live・shadow 異常の観察 / 落選候補の条件付き復活 (registry) | — | 常時 | 一言仮説 + 経済機構の仮説 |
| **S1 feasibility** | hard constraints C1-C6 (データ実在 2y+ or 今から蓄積可 / 摩擦 2.0-4.5p 超え見込み / falsified 6 系統 + 価格 3 周との明確な区別 / 複雑性禁止) | R3 | 1-3 日 | 裁定表 (research/) |
| **S2 R3 診断** | 探索窓のみで IC/MFE/発火頻度の予備計測。OOS 窓に接触しない | R3 | 数日 | 診断 doc (analyses/) |
| **S3 pre-reg LOCK** | 型 A: 観測前 pre-reg 直行 (データが今から発生する場合 — E1 型、最速) / 型 B: discovery→凍結→OOS (歴史データがある場合)。self-LOCK は純研究のみ・user 通知後 | R1 手続き | 起案 1-2 日 | 🔒 LOCKED + registry 期日 |
| **S4 verdict** | 判定器で一発実行 (ハーネスは LOCK 後・verdict 前に実装し test pin) | — | 期日固定 | PASS / UNDERPOWERED / REJECT (+固定分岐) |
| **S5 実装 pre-reg** | D4 必須 4 項目 (carve-out / R2 自動降格 / セル単位判定 / parity)。テンプレ = [[d4-implementation-prereg-template-2026-07-16]] | R1 + **user 承認** (D3 SLA 48h) | 1-2 日 | user 承認 |
| **S6 shadow parity** | fill/spread/slippage vs 検証前提の突合 (最低 N=10) | R3 | 発火頻度依存 | parity OK |
| **S7 live pilot** | minlot 1000u carve-out。R2 復帰条件を対で常設 | — | N 蓄積 | セル live N≥30 ∧ Wilson 下限 EV>0 |
| **S8 scale** | 防御解除ラダー 2 段目 (5000u)。以後 Kelly 学習へ | R1 | — | — |

**既存規律への参照**: 各ステージの統計要件 (BH-FDR q / block bootstrap / ナイフエッジ /
UNDERPOWERED 分岐) は各 pre-reg が定義。falsified 再試行禁止・カーブフィッティング禁止・
Shadow は UTC 固定で削らない (原則 3) は全ステージ共通。

## 3. WIP 原則 (新設、本文書の核心)

- **常時 ≥2 仮説が S1〜S4 のどこかに存在すること。** 1 本になったら次の月次スキャンを待たず
  臨時スキャンを起動する (autopilot / セッションどちらでも可、R3)
- 並行仮説は**モダリティを分散**させる (同一モダリティ 2 本は片方 FAIL で両方死ぬ相関を持つ)
- S5 以降 (実装系) は直列で良い — 並行すべきは探索・検証段であって live 配管ではない
- 「今から蓄積しないと間に合わない」型のデータ (E1 の Myfxbook が典型) は、
  **S1 通過の時点で ingest を先行起動する** (蓄積は無料、待ちは不可逆)

## 4. Cadence (新設)

| 周期 | 内容 | 監視 |
|---|---|---|
| **月次** | 外部仮説スキャン (文献 18 ヶ月 + データ入手性の再確認 — 入手性は時間で変わる: round-4 の cache 延伸、新 API、無料化等) | registry `edge-supply-scan-monthly` (deadline_info、完了時に翌月へ更新) |
| 四半期 | モダリティ棚卸し (falsified 一覧の再確認・「閉鎖」判定の前提が崩れていないか) | 月次スキャンに同乗 (3 回に 1 回) |
| verdict 毎 | §固定分岐の執行 + パイプライン状態表 (下記 §5) の更新 | 各 pre-reg registry |

## 5. パイプライン状態表 (2026-07-18 時点 — verdict 毎に更新)

| 仮説 | Stage | 期日/条件 | 備考 |
|---|---|---|---|
| **E1 positioning contrarian** | S4 待ち | first look **2026-10-15** / second look 2027-01-06 | 🔒 LOCKED、13 ペア蓄積中、判定器完備 |
| **E15+E7 イベントモダリティ** | **phase-0 (E15): S4 完了 → ❌ FAIL 0/6 (2026-07-22、C5×6)。phase-1 (E7): S3 継続** | phase-1: FF gap+データ付録凍結 08-14 / discovery 08-21 / **verdict 08-28** | [[e15-e7-event-modality-prereg-2026-07-18]] §12 — E15 無条件イベント窓は棄却 (BH q=0.05 m=6 通過ゼロ、min p 0.214)。§8 固定分岐で phase-1 は予定続行。registry phase0 = resolved、`e15-e7-event-prereg-phase1-verdict` 監視継続 |
| **E12 CME 先物 volume flow** | S1 通過 → インフラ先行 | **yfinance 1h は 730d rolling — capture 開始が 1 週遅れる毎に歴史が 1 週消える** | 第 2 モダリティ。週次 1h バー capture job が前提 |
| E9 通貨 VRP | S1 条件付き | EVZCLS×EURUSD 無料 probe 先行 → 正なら Databento (クレジット 6 ヶ月失効、probe 後にサインアップ) | 第 3 線 |
| round-4 EUR divergence | S0 (条件付き) | cache 2026-11-15+ 延伸で発火 | registry `ws3-round4-eur-divergence-conditional` |
| htf_fb×AUD_JPY recheck | S4 待ち (non-load-bearing) | shadow N≥100 or 2027-01-31 stale | projected N 14-41 — 計画に算入しない |
| shadow 蓄積詰まり診断 | S2 実行中 | 2026-07-18 起動 | 内部母集団の将来 discovery power に影響 — [[shadow-accumulation-blockage-diagnosis-2026-07-18]] |

**WIP 原則の充足状態**: S1-S4 に E1 + イベントモダリティ + E12 の 3 系統 (モダリティ分散: 非価格 sentiment / イベント / 実約定フロー) — 原則充足 ✅

## 6. 責務

- **autopilot / 任意セッション**: S0〜S2 (R3)、S3 の純研究 self-LOCK (通知後)、S4 の期日執行、月次スキャン
- **user**: S3 の live 影響型 LOCK、S5 実装 pre-reg 承認 (D3 SLA 48h)、防御解除ラダー段上げ
- 本文書の変更は PR レビュー必須 (プロセス変更 = 全仮説に波及するため)
