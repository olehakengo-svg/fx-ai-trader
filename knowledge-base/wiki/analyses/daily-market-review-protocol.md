# Daily Market Review Protocol — 日次市場レビュー + 観測採集 (S0 intake 層)

**Created**: 2026-09-14
**Author**: Claude (quant analyst mode)
**Status**: ⚠️ **60d レビュー 2026-11-12 = (i) 不成立 → §6 (a) 発動・廃止提案 (user 決裁、既定 = (b) 縮退継続) / (ii) 不成立 → rollup 層廃止 (同 PR で執行)** (§9、registry `daily-market-review-60d-effectiveness` resolved → user 決裁 entry `daily-market-review-abolition-user-decision` 2026-11-26)。30d レビュー 2026-10-14 = 条件付き継続 (§8)
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

**(d) 週次 rollup (月曜) — ⬛ 廃止 (2026-11-12、§9 (ii) 字義 1/4 < 3/4)**
- 旧手順 (先週分の family 集計を観測ファイル末尾の rollup 節に追記、卒業条件到達 family を列挙) は 60d 窓で月曜定刻 1/4 (10-19 → 10-20 / 10-26 → 10-29 / 11-02 定刻 / 11-09 → 11-11 の代行) に留まり、読み手は依然 自分自身のみ (§9 表「外部の読み手」) = 30d §8 の事前規定どおり rollup 層のみ廃止
- family の累計は各 O エントリの「family 候補」行と registry の当該 frame が保持する。≥3 独立観測の到達は (c) 執行 QA の registry 検索 (既存 frame への回付) で扱い、集計層は置かない。既存の rollup 節 (2026-10 / 2026-11) は歴史記録として残置

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
| ~~週次 (月曜)~~ | ~~rollup 節~~ | ⬛ 2026-11-12 廃止 (§9 (ii)、字義 1/4) — 既存 rollup 節は残置、新規追記なし |
| 月次 | external-hypothesis-scan S0 queue | 卒業 family を次回スキャンの S0 候補へ供給 |
| 30d | registry `daily-market-review-30d-effectiveness` (期日 2026-10-14) | 観測数 / 卒業 family 数 / 執行 QA 発見数 — 判定基準は §6 (稼働率 <50% または「執行 QA 発見 0 かつ 卒業 family 0」で廃止提案) |
| 60d | registry `daily-market-review-60d-effectiveness` (期日 2026-11-13) | ✅ 2026-11-12 執行 (§9): (i) 11/22 = 50% < 60% 不成立 / (ii) 字義 1/4 不成立 / (iii) 観測 19・執行 QA 発見 17・卒業 0 |
| 決裁 | registry `daily-market-review-abolition-user-decision` (期日 2026-11-26) | §6 (a) 廃止提案 (a) 全廃止 / (b) 縮退継続 (推奨・既定) / (c) 現状維持 — 無回答 = (b) |

## 6. 廃止条件 (自己反証)

30d レビューで (a) 観測記録が習慣として途絶 (稼働率 <50%)、または (b) 執行 QA 発見 0 かつ 卒業 family 0、のいずれかなら、本プロトコルは維持コストに見合わないと認定し廃止提案を出す。「仕組みを作った」こと自体は成果ではない ([[process-meta-audit-2026-09-07|meta-audit]] enforcement 不在の教訓)。

## 7. 明示的な非スコープ

- **Tier B-daily (`scripts/daily_hypothesis_scan.py`) の Phase 3 有効化は本プロトコルに含まない** — dry-run 解除は α 予算消費を伴う別決裁 (render.yaml コメント参照)
- 日次での BT 実行・パラメータ変更・tier 変更は一切しない (それぞれ既存 Rule 1/2/3 の管轄)

## 8. 30d 有効性レビュー (2026-10-14、autopilot、rule:R3 記録のみ) — 条件付き継続

**窓**: 2026-09-14〜10-13 (30 日、営業日 22)。**SSOT**: `raw/trade-logs/YYYY-MM-DD.md` (wiki-daily 本体 run) の『執行 QA』節、`research/daily-observations-2026-09.md` / `-10.md`。
⚠️ 10-06 / 10-07 / 10-13 の run 成果物はローカル `main` に座礁しており origin に無かった (10-13 run の観測ファイル `daily-observations-2026-10.md` 自体が未 push) — 本レビューの PR で救出。**観測層の write-only は「書いたが誰も読まない」だけでなく「書いたが repo に届かない」形でも起きる**。

| 計数 | 値 | 内訳 |
|---|---|---|
| wiki-daily run (本体 `YYYY-MM-DD.md`) | **17/22 = 77%** | 欠落 5: 09-15 / 09-23 / 10-08 / 10-09 / 10-12 (うち 10-08〜10-12 は 3 営業日連続、10-13 に 6 日一括 run) |
| 執行 QA 節あり run (Phase 2.5 実行の痕跡) | **13/22 = 59%** | 09-14 / 09-16 / 09-17 / 09-22 は run あり・節なし (導入直後の 3 run は未適用) |
| 観測 entry / 独立 event | **8 / 7** | 09-11 CPI / 09-13 WG (2 entry = 1 event) / 09-18 learner / 09-18 gate 到達 / 09-27 WG basis / 10-08 storm / 10-12 learner |
| 執行 QA 発見 | **6 entry / 5 event** | O-09-14-1 (WG drift → G0' 回付 → packet §6 発動 = 既存 frame が実際に動いた唯一の例) / O-09-18-1・O-10-13-2 (learner write-only ×2) / O-09-18-2 (gate 到達非対称) / O-09-28-1 (WG basis → packet v1) / O-10-13-1 (storm → `storm-guard-enforce-decision` 回付) |
| 卒業 family (≥3 独立観測) | **0** | 最多 = learner write-only 2/3 (制御系、S1 対象外) |
| 週次 rollup (月曜) | **0/4** | 09-21 / 09-28 / 10-05 / 10-12 全て未実施 (09-21 / 09-28 / 10-05 は run 自体はあった) → 本 PR で遡及記載 |
| 外部の読み手 | 2 doc | weekend_gap packet v1 (09-28) / redraft が O-09-14-1・O-09-28-1 を引用。他 family の観測は未引用 |

**§6 判定**: (a) 稼働率 <50% — **不成立** (run 77% / 執行 QA 59%)。(b) 執行 QA 発見 0 ∧ 卒業 0 — **不成立** (発見 6)。⇒ 廃止条件は成立しない。

**ただし素直に「有効」とは言わない**:
1. 価値の実体は**執行 QA** (6 発見、うち WG drift は packet §6 の事前コミット経路を実際に発動させた) であり、**観測採集→family 卒業→S1 の経路は 30d で 1 件も動いていない** (base rate 4% の下で 30d に卒業を期待する数理は元々無い — §1)。卒業 0 を廃止理由にしない代わりに、卒業を成果として数えもしない
2. **rollup 層は write-only** (0/4、読み手 = 自分自身の月曜 run だったが実行されなかった)。family 集計は 30d レビュー時に一括で足りる可能性が高い
3. 稼働率は knife-edge (執行 QA 59%) で、10-08〜10-12 の連続欠落 + 一括 run は習慣途絶の前兆。閾値 50% を「通過」と読むより「次の 30d で下回れば廃止」と読む

**決定 = 条件付き継続** (registry `daily-market-review-60d-effectiveness`、期日 2026-11-13、窓 10-14〜11-12):
- (i) 執行 QA 節あり run / 営業日 **≥ 60%** — 不成立なら §6 (a) 発動で廃止提案
- (ii) 月曜 rollup **≥ 3/4** (10-19 / 10-26 / 11-02 / 11-09) — 不成立なら rollup 層のみ廃止 (観測→30d 集計へ一本化、§3(d) 削除)
- (iii) 3 計数 (観測 / 執行 QA 発見 / 卒業) を再集計。卒業 0 は単独では廃止理由にしない
- 判定は本節と同形式で追補し、registry entry の resolution に転記する

## 9. 60d 有効性レビュー (2026-11-12、autopilot、rule:R3 記録のみ) — (i) 不成立 → §6 (a) 発動・廃止提案 / (ii) 不成立 → rollup 層廃止

**窓**: 2026-10-14〜11-12 (営業日 22)。**SSOT**: §8 と同じ — `raw/trade-logs/YYYY-MM-DD.md` (wiki-daily 本体 run。cloud cron の `-pre_tokyo` / `-monitor` 等は run に数えない) の『執行 QA』節、`research/daily-observations-2026-10.md` / `-11.md`。
**評価時刻 = 2026-11-12 04:10Z (期日 11-13 の 1 日前)**: 11-12 の wiki-daily run はローカル `main` 上で進行中 (scheduler 記録 11-11 23:44Z 開始、`raw/trade-logs/2026-11-12.md` に「Phase 2.5 市場レビュー + 観測 + 執行 QA」節あり) → run あり・節ありとして計上 (origin 未着 = 座礁 11 例目候補)。**11-12 の帰結は (i)(ii) の成否を変えない** (計上して 11/22 = 50%、不計上で 10/22 = 45%、いずれも < 60%; (ii) の 4 月曜は全て経過済み) — 「前倒しは窓を変える」(11-11 session) の条件に抵触しないため本日執行。
**scheduler 記録 (desktop app `wiki-daily-update`、cron `47 20 * * 1-5` ローカル + jitter 767 s)** を欠落日の帰属に用いた (30d は未参照)。

| 計数 | 値 | 内訳 |
|---|---|---|
| wiki-daily run (本体 `YYYY-MM-DD.md`) | **11/22 = 50%** | 10-15 / 10-16 / 10-20 (×2 run) / 10-22 / 10-29 (×2 run) / 11-02 / 11-04 / 11-05 / 11-06 / 11-11 / 11-12 (進行中)。欠落 11: 10-14 / 10-19 / 10-21 / 10-23 / 10-26 / 10-27 / 10-28 / 10-30 / 11-03 / 11-09 / 11-10 |
| 執行 QA 節あり run (Phase 2.5 実行の痕跡) | **11/22 = 50%** | run あり 11 日の**全て**に節あり (30d の「run あり・節なし」4 本は消滅 = 手順は定着、欠落 = run 不在のみ) |
| 欠落 11 日の帰属 | 未発火 8 / 失敗 3 / skill 不履行 **0** | 未発火 (発火記録なし) = 10-14 / 10-19 / 10-26 / 10-27 / 10-28 / 11-03 / 11-09 / 11-10。失敗 = 10-21 13:23Z / 10-23 23:57Z / 10-31 04:58Z (全て定刻 11:47Z±13 min 外の遅延発火 → `API Error … ENOTFOUND` で KB 書込み前に終了)。成功 run の開始時刻も 05:46Z / 23:44Z 等の定刻外が 5 本 = ホスト復帰時の catch-up 発火。**[[sprint-1022-process-fixed-cost-upsubmit-2026-11-05]] (i) の 10 月所見 (未発火 5 + 失敗 4 = 41%) と同型、11 月前半で悪化 (7 営業日中 4 日欠落)** |
| 観測 entry / 独立 event | **19 / 19** | 10-15 ×2 / 10-16 / 10-20 ×3 / 10-22 / 10-29 ×3 / 10-30 / 11-02 ×2 / 11-04 ×2 / 11-05 / 11-06 / 11-11 ×2 (各 entry が別 trigger)。11-12 run 進行中の O-2026-11-12-1 (storm_guard totals + learner blacklist 同時消失、状態消失 9 例目) は評価時刻後 = 数えない |
| 執行 QA 発見 | **17 entry** | 19 − 制御系/learner のみの 2 (O-11-04-1 / O-11-11-1)。既存 frame への回付・実装に至った例: O-10-20-1 → `storm-guard-enforce-decision` ENABLE (10-19) / **O-11-02-1 → R3 修理 PR #363 (max_open live cap)** / **O-11-04-2 → R3 修理 PR #365 (DD 台帳 writer 一本化)** / O-11-02-2 → kalman R2 code pin の latency 記録 / O-11-05-1・O-11-11-2 → `storm-guard-enforce-first-storm-readout` resolve (喪失 0 ×2)。**live 経路に触る修理 2 本が観測 → R3 の経路で着地 (30d は回付 1・着地 0)** |
| 卒業 family (エッジ = S1 対象) | **0** | 制御系 family の ≥3 到達 = storm_guard 系 (≥11) / learner in-memory 反映 (6) / 決済後レース (5、実害 0) / `render_deploy_trigger` (3–4) / deploy 直後 LIVE 送信 (3) — いずれも S1 対象外、経路は R3 (着地済 2) or user 未決 (5 / 12 / sprint-1022 (iii)) |
| 週次 rollup (月曜 10-19 / 10-26 / 11-02 / 11-09) | **字義 1/4** (11-02 のみ定刻) / 代行込み 4/4 | 10-19 → 10-20 (1 日遅れ) / 10-26 → 10-29 (3 日遅れ) / 11-02 定刻 / 11-09 → 11-11 (2 日遅れ)。遅れの原因は全て月曜 run 不在 (ホスト) = 手順の省略ではない |
| 外部の読み手 | R3 derivation 2 本 + registry note 4 entry | [[max-open-live-cap-counts-shadow-r3-2026-11-03]] / [[dd-ledger-broker-close-booking-r3-2026-11-04]] が O-11-02-1 / O-11-04-2 を起点に引用; registry `storm-guard-enforce-first-storm-readout` / `sl-persist-root-fix-first-live-trail-readout` / `max-open-live-cap-counts-shadow-r3` / `dd-ledger-broker-close-first-booking-readout` の note が観測を参照。**rollup 節の読み手は index の「代行」記述のみ = 自分自身** (30d と不変) |

**判定** (§8 の事前規定どおり):
- **(i) 執行 QA 節あり run 11/22 = 50% < 60% → 不成立** (§6 (a) の 30d 閾値 <50% にも接している)。⇒ **§6 (a) 発動 = 廃止提案** (下記、user 決裁)
- **(ii) 月曜 rollup 字義 1/4 < 3/4 → 不成立** ⇒ **rollup 層のみ廃止 — 本 PR で執行** (§3(d) を廃止表記、`.claude/commands/wiki-daily.md` Phase 2.5 の月曜行を削除、§5 表更新)。代行込み 4/4 は併記するが判定に使わない (pre-reg は月曜の日付 4 つを列挙しており、30d で遡及記載を 0/4 と数えた前例と整合)
- (iii) 卒業 0 は単独では廃止理由にしない (§8)。執行 QA 発見 17 / R3 着地 2 は 30d (発見 6 / 着地 0) から増加

**廃止提案 (§6 (a)、user 決裁 — registry `daily-market-review-abolition-user-decision` 期日 2026-11-26、無回答 = (b))**:
- **(a) 全廃止**: wiki-daily Phase 2.5 を停止 (前営業日レビュー・観測記録・執行 QA すべて)。`~/.claude/scheduled-tasks/wiki-daily-update/SKILL.md` は user 領域のため autopilot は執行しない (11-11 と同じ権限判定)
- **(b) 縮退継続 (推奨・既定)**: (a) 前営業日レビュー + (b) 観測記録 + (c) 執行 QA は維持、(d) rollup は廃止済み。「観測 → family 卒業 → S1 供給」は**非目標化** (60d で 0、base rate 4% の下で期待できない — §1 の「S0 intake 層」という位置づけを「執行 QA の受け皿 + 制御系欠陥の観測台帳」に改める)。定期有効性レビュー (30d/60d) は打ち切り — 稼働率はホスト可用性の計測であって本プロトコルの計測ではなく、同じ量は sprint-1022 (i)/(ii) (C 案 = クラウド routine 化) で追う
- **(c) 現状維持** (rollup 含む) — (ii) の pre-reg 帰結に反するため推奨しない
- **推奨 (b) の根拠**: 不成立の (i) は skill 不履行 0 / run 不在 11 = ホスト可用性の計測 (表「帰属」)。一方 60d の執行 QA は live 経路の R3 修理 2 本 (PR #363 / #365) と enforce readout 2 本を供給した = 30d の「回付 1」から実収益化した唯一の S0 層。全廃止 (a) は観測 → R3 の供給線を切る
- **自己反証 (pre-reg)**: (b) は「成果が出たから続ける」の事後正当化と読める。反証条件 = **次 120 日 (〜2027-01-12 を期日とする後継 entry `daily-market-review-exec-qa-yield-120d`、(b) 採択時に起票) で執行 QA 発見からの R2/R3 着地 (PR マージ) が 0 なら (a) へ移行**。着地の定義 = 観測 entry を起点に引用する derivation doc 付きの merged PR (今窓の #363 / #365 型)。本 run では後継 entry を起票しない (決裁前の frame 増殖回避)
