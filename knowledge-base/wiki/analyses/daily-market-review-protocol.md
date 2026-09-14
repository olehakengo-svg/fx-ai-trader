# Daily Market Review Protocol — 日次市場レビュー + 観測採集 (S0 intake 層)

**Created**: 2026-09-14
**Author**: Claude (quant analyst mode)
**Status**: ACTIVE (30d 有効性レビュー 2026-10-14、registry `daily-market-review-30d-effectiveness`)
**Related**: [[daily-tierB-protocol]], [[edge-development-pipeline-2026-07-18]], [[hypothesis-catalog-2026-07-24|hypothesis-catalog]], `.claude/commands/wiki-daily.md` Phase 2.5
**Adversarial review**: 2026-09-14 初稿は 3 レンズレビューで P1×3 棄却 → 本版で修正 (シード観測自身が §2 違反を 2 種踏んだ — 定義の緩さは初日に悪用される実証)

---

## 1. 目的と位置づけ

**「毎日エッジを完成させる」のではなく「毎日観測を採集し、検証は既存の束 (pre-reg バッチ) で行う」。**

本プロトコルは edge-development-pipeline の **S0 intake の上流に置く観測層**である。台帳 (#N) の下ではなく前段:

```
日次観測 (本プロトコル、記述級のみ)
  → family 集計 (週次 rollup、月曜)
    → 卒業 (同一 family ≥3 独立観測 or user 指名)
      → ban/estimand 監査 (必須、feedback_audit_past_verdicts)
        → S1 feasibility → 既存経路 (敵対的検証 → freeze → 台帳 #N → pre-reg LOCK → verdict)
```

**根拠となる数理 (正直な期待値)**: 実測 base rate ≈ 4.0% (家族級 verdict ~25 件中 OOS PASS 1、Wilson 95% CI 0.7–19.5%、[[process-meta-audit-2026-09-07|process-meta-audit]] §1)。日次観測は**エッジではなく供給レートの乗数**であり、月利目標 (M1→M2→M3) への寄与は「次の live 有望セルまでの期待 family 数 (~53 — ⚠️ 未検証モデル、funnel-5 confidence medium)」を消化する速度を上げることに限られる。毎日「勝てるエッジ」が出る装置は base rate 4% の下では数学的に存在しない。

## 2. 統計規律 (絶対遵守 — 破ると本プロトコル自体が α 漏洩装置になる)

1. **記述級 (descriptive) のみ** — 観測エントリで p 値・検定・Wilson 下限を計算しない。採否判断に統計量を使わない。α 予算 ([[daily-tierB-protocol]] §3) の消費はゼロ
2. **凍結 look 保有 family の事前確認 (P-10 一般則)** — 固定リストではなく規則で運用する: **エントリを書く前に `prereg-trigger-registry.json` を当該 family 名で検索**し、活性の凍結 look / 事前登録 forward frame があれば、その family の **outcome 量 (PnL/WR/EV/fill 率/回帰率/埋め速度) をエントリに記載してはならない**。未登録の新 split の事後シードも禁止 (split を検証したければ蓄積前に registry へ conditional_info を事前宣言する)。2026-09-14 時点の該当例: E1 / ECG / E12 / family A / weekend_gap (volstate split + G0' + F2 + G1/G2) / ps (ps-carveout-regate-post-172) / sr_anti_hunt (forward 枠 fresh N≥40)
3. **counts の定義** — 許されるのは **marginal count のみ** (event 単発の件数、gate 単独の件数)。outcome 条件付きの count・rate (「gate X 内の WIN 数」「30 分内回帰率」等) は語形が counts でも gate×outcome であり禁止
4. **保存 OOS 非接触** — 2022+ split、「2013–2025 非接触保存」条項の窓に触れない。観測は直近データ (live/shadow/直近数日の bar) のみから記述する
5. **トリガ日の記録と卒業時除外 (選択バイアス遮断)** — 観測採集は将来の OOS/forward 母集団に対するデータスヌーピングである。各エントリは**トリガ日**を必ず記録し、卒業した family の確認評価は (a) トリガ日を OOS 窓から機械的に除外する、または (b) 卒業時点から strictly forward で判定する (family A 前例:「クリーン判定は forward OOS のみ」) のいずれかを pre-reg に明記する
6. **台帳番号は既存経路のみ** — 観測は台帳 # を持たない。番号付与は敵対的検証 → freeze の既存手続きに限る (Bonferroni/BH 分母の膨張は卒業時点で初めて発生する — ただし §2.5 の通り、採集自体のスヌーピングはトリガ日除外で別途遮断する)
7. **卒業前の ban/estimand 監査必須** — 隣接する closed family の ban 条項との差分節を観測エントリ時点で仮記載し (原本 decision doc を実読すること — 記憶からの family 特徴づけは 2026-09-14 初稿で実際に誤った)、卒業時に正式監査

## 3. 日次手順 (wiki-daily Phase 2.5 として実行)

**(a) 前営業日レビュー (data-first、~10分)**
- 主要ペア (最低 USD_JPY) の日足 OHLC / セッション分解 (東京/ロンドン/NY) / 最大 15m バー (時刻・値幅・出来高) を算出
- **データ供給**: `data/cache/massive/*_15m.parquet` を使う場合は `tools/fetch_massive_data.py` で当日分まで更新してから読む (⚠️ sha256 凍結済み BT キャッシュ (E15/E7 系) は日次更新で触らない — 凍結対象は `tools/e15_e7_data_refreeze.py --verify-only` で確認)。ローカル parquet が無い環境では本番 API (`/api/demo/*`) または Massive MCP を fallback とする
- 材料付合せ: 指標時刻 (12:30/14:00 UTC 等) との一致、`raw/market-analysis/{date}-regime.md` と整合確認。外部報道由来の材料ラベルは**未確認と明記** (一次 econ calendar での確認は卒業時監査)
- **物語の禁止**: 「なぜ動いたか」は材料の時刻一致まで。N=1 の物語からの直接エッジ設計はしない

**(b) 観測記録**
- `knowledge-base/wiki/research/daily-observations-YYYY-MM.md` (月次ファイル) に §4 形式で追記
- 0 件の日は「観測なし」を記録しない (ノイズ防止)。無理に絞り出さない

**(c) 執行 QA (毎日必須 — 観測より優先)**
- 前営業日〜当日に **当時点の live-eligible セル (tier-master 参照)** の発火条件が成立していたか確認: 想定発火 vs `/api/demo/trades` 実績 + block/abandon 理由
- 乖離 (発火すべきが不発 / 想定外の abandon) は必ず観測として記録。**escalation 前に registry を当該 family で検索**: 事前コミット済みの再審条件 (例: WG packet §6 の「fill 不成立 2 連続」) や監査 frame (例: G0') が既に存在する場合は**その経路へ回付し、独自の R1 再決裁候補マークで前倒ししない**。コード欠陥なら R2/R3、凍結パラメータの前提破れで既存 frame が無い場合のみ R1 再決裁候補として `wiki/decisions/` 行きをマーク
- 執行 QA は仮説数を増やさず純粋に正 EV (2026-09-14 の WG_EXEC_B drift 境界の前提破れ発見が初例、O-2026-09-14-1 → G0' 回付)

**(d) 週次 rollup (月曜、alpha-scan 日)**
- 先週分の観測を family 単位で集計し、観測ファイル末尾の rollup 節に追記
- 卒業条件到達 family を列挙 → user 報告 or S1 起票

## 4. 観測エントリ形式

```markdown
### O-YYYY-MM-DD-n: <一行タイトル>
- **現象**: <数字付きの記述。時刻は UTC、値幅は pips。凍結 look 保有 family は outcome 量を書かない>
- **トリガ日**: <観測の元になった市場日付 — 卒業時の OOS 窓除外に使う>
- **想定メカニズム**: <1-2 文。物語ではなく検証可能な機構>
- **family 候補**: <snake_case> (新規 or 既存 family への付記かを明示)
- **反証可能な予測**: <次に同条件が来た時に何が観測されるはずか — 凍結 look 対象の量は定式化しない>
- **隣接 ban / 凍結 frame**: <closed family の原本 verdict 実読に基づく差分節仮記載 + 当該 family の活性 frame 列挙。なければ「なし (監査は卒業時)」>
- **経路**: S1候補 / 既存family付記 / 執行QA→既存frame回付 or decisions行き / 記録のみ
```

**卒業条件の「≥3 独立観測」の定義**: 独立 = **異なる日付の異なる市場 event**。同一 event の別側面 (例: O-2026-09-14-1/-2) は合わせて 1 と数える。同一 event 内の複数ペアも 1 event と数える。

## 5. 読み手宣言 (write-only 防止 — 検知器も write-only になりうる、2026-08-28 教訓)

| 頻度 | 読み手 | 何を読むか |
|---|---|---|
| 日次 | wiki-daily Phase 2.5 実行者 | 前日エントリとの重複確認 + 執行 QA |
| 週次 (月曜) | rollup 節 | family 出現回数、卒業条件到達 |
| 月次 | external-hypothesis-scan S0 queue | 卒業 family を次回スキャンの S0 候補へ供給 |
| 30d | registry `daily-market-review-30d-effectiveness` (期日 2026-10-14) | 観測数 / 卒業 family 数 / 執行 QA 発見数 — 判定基準は §6 (稼働率 <50% または「執行 QA 発見 0 かつ 卒業 family 0」で廃止提案) |

## 6. 廃止条件 (自己反証)

30d レビューで (a) 観測記録が習慣として途絶 (稼働率 <50%)、または (b) 執行 QA 発見 0 かつ 卒業 family 0、のいずれかなら、本プロトコルは維持コストに見合わないと認定し廃止提案を出す。「仕組みを作った」こと自体は成果ではない ([[process-meta-audit-2026-09-07|meta-audit]] enforcement 不在の教訓)。

## 7. 明示的な非スコープ

- **Tier B-daily (`scripts/daily_hypothesis_scan.py`) の Phase 3 有効化は本プロトコルに含まない** — dry-run 解除は α 予算消費を伴う別決裁 (render.yaml コメント参照)
- 日次での BT 実行・パラメータ変更・tier 変更は一切しない (それぞれ既存 Rule 1/2/3 の管轄)
