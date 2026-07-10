# Pre-registration DRAFT: WS3 探索2周目 — 方向性非対称の新軸探索 (rule:R1 stage-1 型、純研究)

**起案日**: 2026-07-10。**Status**: 📝 **DRAFT — 候補セル未確定 (§2 の診断実行後に列挙・固定して self-LOCK)**
**位置づけ**: [[shortest-path-decision-memo-2026-07-10]] トラックB (供給ライン)。stage-2 ([[ws3-stage2-barrier-ev-prereg-2026-07-09]]) の結果に依存せず常時運転する。**純研究 — live/shadow 変更なし**。self-LOCK 根拠 = stage-1 前例 ([[ws3-asymmetry-oos-prereg-2026-07-09]] の承認欄) + user 通知済み・異議なし (2026-07-09 提案 → 07-10「進めて」)
**タスク票**: `.ai/tasks/queue/20260710-ws3-round2-explore.md` (排他 claim)

## 1. 仮説

round-1 で探索した軸 (entry_type×pair プール方向、h24 主表) の補集合に、OOS 再現可能な方向性非対称 (MFE/MAE ratio) セルが存在する。

## 2. 候補生成手続き (a priori 固定 — 診断は探索窓のみ、OOS 窓に接触しない)

- **探索窓**: round-1 と同一 (365d baseline 2025-07-08〜2026-06-07、診断窓除外)。`tools/ws3_mfe_scan.py` 系を流用
- **新軸 (round-1 の補集合のみ)**:
  - (a) **方向分割** (BUY/SELL 別セル) — round-1 は方向プールだった。未判定セルのみ対象
  - (b) **未走査ペア** — round-1 h24 表に現れなかった production shadow 母集団のペア (機械的に列挙し診断 md に記録)
  - (c) **h96 主軸の持続型** — round-1 で h24 主表から漏れた持続型増幅セル
- **除外 (再試行禁止)**: stage-1 判定済み 8 セル**とその方向分割サブセル** (多重性ロンダリング防止) / falsified 6 系統 (H4 level / channel / 水平sweep&reclaim / mtf SELL / bb_rsi / T11 counter-USD) / trendline_sweep×EUR_USD (stage-1 §8.3(c) により live N 蓄積経路限定)
- **選抜規則 (2026-07-10 改訂 — stage-2 verdict 反映、round-2 スキャン結果の観測前)**:
  - (i) 探索窓 ratio≥1.3 (h24) ∪ 持続型 (h96 で増幅) ∧ 探索窓 N≥30 — round-1 と同一の1次スクリーン
  - (ii) **【新設】探索窓 first-touch EV スクリーン**: 1次通過セルに対し、探索窓で first-touch barrier sim (`tools/ws3_stage2_barrier_sim.py` 流用、TP/SL = 当該セル探索窓 MFE/MAE 分位点アンカー 3×3 grid、SL 優先 tie-break、per-pair 摩擦控除) を実行し、**best 構成の摩擦調整 EV > 0 ∧ 隣接構成の過半が EV > 0** (孤立格子点除外) を要求。根拠 = stage-2 verdict ([[ws3-stage2-barrier-ev-prereg-2026-07-09]] §8): 「MFE/MAE 非対称 ≠ 固定 barrier で EV 化可能」— sequencing (SL 先着) で ratio survivor が全滅した failure mode を探索段で先に落とす。**本改訂は round-2 スキャン結果・OOS の観測前 (2026-07-10) に行った a priori 変更である**
  - **上限 m=10** (超過時は探索窓 EV 降順で切る — 今宣言)
- 診断結果 (候補列挙 + 各候補の探索窓 EV) を本文書 §2b に追記して **self-LOCK (Status 🔒)** → 以後の候補変更禁止
- **注意**: 探索窓 EV は選抜にのみ使用 (探索標本の消費)。OOS 判定 (§3) では ratio と **OOS first-touch EV の両方**を評価し、確認的根拠は OOS 側のみ

## 3. OOS 検証 (LOCK 後)

- **OOS 窓**: 2024-07-07〜2025-07-07 — 候補は全て未判定セルなので本窓は per-cell 未使用 = 有効な OOS。窓の再利用回数を verdict に明記 (3周目以降の独立窓枯渇管理)
- **判定 (2レグ、両方充足で PASS — 2026-07-10 改訂、スキャン結果観測前)**:
  - **(A) ratio レグ** (round-1 と同一): median-ratio 日次ブロックブートストラップ (B=10,000、seed 固定) → BH-FDR q=0.10 (m=候補数) ∧ point ratio≥1.2 ∧ OOS N≥30、型別 primary horizon 固定
  - **(B) EV レグ (新設)**: §2(ii) で **LOCK 時に凍結した grid** (探索窓分位点アンカー — OOS で再アンカーしない) の OOS first-touch 摩擦調整 EV について、**best 構成の 3×3 近傍平均 EV ≥ +0.5 p/t ∧ 隣接構成の過半が EV > 0** (stage-2 §4(b)/§5.3 と同基準)。lfr 型の「ratio は再現するが EV 化不能」を OOS 段で機械的に落とす
  - ナイフエッジ3点検査 (擬似反復 / 孤立格子点 / fold 集中 — stage-2 §5 準拠、LOFO 含む)
- **分岐 (事前固定)**: PASS≥1 → stage-2 型 barrier/EV pre-reg 起案 (**その段から user LOCK 承認**) / PASS=0 → 本番 shadow 母集団内の軸は枯渇と判定し、**外部仮説 (新シグナル系統 — 学術/TV 由来、falsified 6 系統除外) の探索へ転進** — survivor 確率は保証しない (round-1 の 25%/セルは上澄み候補での値、round-2 はそれ以下が自然)

## 4. 期日・監視

- 診断 + 候補固定 + self-LOCK: **2026-07-14** / OOS verdict: **2026-07-17**
- LOCK 時に `prereg-trigger-registry.json` へ verdict 期日エントリを追加
- 出力: `raw/bt-results/ws3_round2_scan_2026_07.{json,md}` (診断) / `ws3_round2_oos_2026_07.{json,md}` (verdict)

## 5. 除外・注意

- stage-2 実行 (zen-mahavira 排他領域) の成果物・結果には接触しない。本 pre-reg の設計は stage-2 の結果を一切参照していない (2026-07-10 時点で未読)
- 探索窓・OOS 窓の消費履歴: round-1 で explore=2025-26 / OOS-1=2024-25 を候補選抜に消費済み (stage-2 grid 設計にも使用)。本 round-2 は**未判定セルに限る**ことで OOS-1 窓の有効性を保つ
- BE/Trail は MFE/MAE 計測に関与しない (forward scan) — round-1 と同一エンジン
