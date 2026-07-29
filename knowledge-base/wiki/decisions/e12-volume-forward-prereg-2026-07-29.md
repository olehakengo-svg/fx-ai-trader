# 🔒 Pre-registration LOCK: E12 CME 先物 volume flow — 観測前 forward pre-reg (W3-3 登録アクション、rule:R1 stage-1)

**🔒 LOCKED 2026-07-29 — 以降、estimand・gates・役割 split・trigger の変更禁止。本コミットは登録アクションのみで測定ゼロ (BH/wave スロット非消費)。執行 = first look trigger 発火時 (2027-02-05、registry 機械監視)。**

**起案日**: 2026-07-29 (wave-3 W3-3、台帳 #10 の前倒し登録)
**起点**: [[external-hypothesis-scan-round2-2026-07-18]] E12 行 (採用 — 第2モダリティ) / [[market-data-ingest-2026-07-18]] §5/§7 (蓄積インフラ、PR #102) / `raw/analysis/wave3-adversarial-verification-2026-07-29.md` [W3-3] 節 (GO-WITH-CONDITIONS、6 条件)
**様式踏襲**: [[mof-intervention-forward-prereg-2026-07-24]] (forward 型) / [[cot-commercial-flow-explore-prereg-2026-07-29]] (W3-1、pooled IC 規約)
**承認**: user ミッション委任 (2026-07-08) + 探索最大化指示 (2026-07-24) に基づく純研究。**live パラメータ・コード・shadow 構成の変更ゼロ**。tradeable 化は verdict PASS 後に stage-2 別 pre-reg + user 最終承認。

---

## 0. 敵対的検証 [W3-3] 6 条件の解決マップ

| # | 条件 | 解決箇所 |
|---|---|---|
| (1) | power trigger の数値凍結 (N or 期日で機械判定) | §6 — first look **期日 2027-02-05** (データ cutoff 2027-01-31) + validity gate N (registry `e12-volume-first-look-deadline`) |
| (2) | joint look ゼロ attestation | §7 — 既発生 QA look の全列挙 + volume×価格ジョイント未計算の宣言 + 執行までの計算禁止 (MoF P-10 型) |
| (3) | scan-round2 の S1 設計無変更凍結 | §3 — unsigned abnormal volume primary + 価格 momentum への**増分 IC 必須検定**、BVC-signed は secondary (非 claimable) |
| (4) | backfill=explore / go-forward=OOS の役割 split 凍結 | §2 — 境界 **2026-07-30T00:00Z** で凍結 (OOS バーは本 LOCK 時点で未生成 = genuine OOS) |
| (5) | 陳腐化 review 期日 | §8 — **2026-11-30** (registry `e12-volume-prereg-staleness-review`、設計変更・データ look 禁止) |
| (6) | first_bar 実日付の DB 実測確定 | §2.1 — 本番 `/api/marketdata/status` 実測 (2026-07-29): 全 7 契約 **first_bar = 2024-02-27T05:00:00Z** |

## 1. 背景と機会 (なぜ観測前に登録するのか)

- E12 (台帳 #10) は scan-round2 採択の**第2モダリティ** (取引所実約定 volume = falsified 6系統+price 3周が未使用)。データは yfinance 60m の **730d rolling 窓** — 歴史左端は 2024-02-27 で固定され (これ以上左に伸びない)、検証歴史は go-forward 蓄積 (2026-07-18 開始、PR #102) でのみ延伸する。
- **前倒し登録の狙い**: volume×価格のジョイント量を一切見ずに estimand / gates / 役割 split / trigger を凍結する。蓄積が検定力に到達した時点で**機械執行** — 「データが貯まってから設計する」ことで生じる file-drawer / 事後裁量の窓を、MoF forward 型 (期限 12 日前倒し LOCK の前例) と同じ理由で今日閉じる。
- explore/OOS の temporal split は従来型 (2014-2021 / 2022+) が**原理的に不能** (2024-02 以前の歴史が存在しない) — 代わりに「LOCK 時点で存在するバー = explore / LOCK 後に生成されるバー = OOS」という forward split が唯一の genuine OOS 構成である (§2)。

## 2. データと役割 split (凍結)

### 2.1 DB 実測 (2026-07-29、本番 `/api/marketdata/status` — 条件 (6))

counts/timestamps のみの QA look (volume 値・価格に非接触)。running=true、last_cycle 2026-07-29T14:02Z。

| 契約 | first_bar | latest_bar | rows |
|---|---|---|---|
| 6E=F | 2024-02-27T05:00:00Z | 2026-07-29T10:00:00Z | 13,861 |
| 6J=F | 2024-02-27T05:00:00Z | 2026-07-29T10:00:00Z | 13,863 |
| 6B=F | 2024-02-27T05:00:00Z | 2026-07-29T10:00:00Z | 13,864 |
| 6A=F | 2024-02-27T05:00:00Z | 2026-07-29T10:00:00Z | 13,863 |
| 6C=F | 2024-02-27T05:00:00Z | 2026-07-29T10:00:00Z | 13,866 |
| 6S=F | 2024-02-27T05:00:00Z | 2026-07-29T10:00:00Z | 13,862 |
| 6N=F | 2024-02-27T05:00:00Z | 2026-07-29T10:00:00Z | 13,864 |

### 2.2 役割 split (条件 (4) — 凍結)

| セグメント | bar_time_utc | 役割 | provenance |
|---|---|---|---|
| **explore** | [2024-02-27T05:00Z, **2026-07-30T00:00Z**) | discovery + 校正 + candidate 凍結 | 2026-07-21 一括 `period=730d` backfill (95,069 行) + 2026-07-18〜 go-forward 日次 capture。**INSERT OR IGNORE first-capture 凍結**で以後不動 |
| **OOS** | ≥ **2026-07-30T00:00Z** | 単一接触 confirm | 本 LOCK 時点で**未生成** (latest_bar 2026-07-29T10:00Z) = genuine OOS。go-forward 日次 job が蓄積 |

- **provenance 非対称の開示**: explore セグメントは 2026-07-21 の一括 fetch vintage であり、go-forward セグメントとはベンダー側事後補正への露出が異なる。first-capture 凍結 (本番 SQLite) で双方とも取得後は不動。**執行時に explore/OOS extract を `/api/marketdata/export?table=cme_bars` で取得し sha256 を verdict 追記に凍結** (E15/E7 refreeze 型 — MASSIVE drift 教訓 `project_massive_vendor_gap_backfill_2026_07_29`)。
- **spot 側** (forward return 用): `data/cache/massive/{pair}_15m*.parquet` mid。土曜行除去 + 不良プリント (spike-revert) 除去は **price_shock 監査 (台帳 #2、2026-07-24) のクリーニングルールを無変更継承**。spot parquet は drift しうるため執行時 extract sha256 を同様に記録。
- **universe (凍結)**: 6E=F→EUR_USD / 6J=F→USD_JPY / 6B=F→GBP_USD / 6A=F→AUD_USD / 6C=F→USD_CAD / 6S=F→USD_CHF / 6N=F→NZD_USD。先物は対 USD base 通貨建て — unsigned primary には無関係、BVC secondary の符号写像のみ **spot 方向 = BVC 符号 × (spot が USD_XXX 型なら −1、XXX_USD 型なら +1)** で凍結。
- 歴史 unlock (Databento 有料、CME 実 volume 12y) は **user 決裁事項として記録のみ** — 本 pre-reg の執行はこれに依存しない。

## 3. 仮説と estimand — scan-round2 S1 設計の無変更凍結 (条件 (3))

### 3.1 仮説

- **H1**: 異常出来高 (unsigned abnormal volume) は情報到達・強制フローの proxy であり、その onset は直近価格 momentum の forward 継続/反転構造を条件付ける (方向は explore で凍結する — §4)。
- **H0**: 異常出来高 bar 上の momentum→forward 関係は、無条件 baseline と区別不能 (**volume の増分情報ゼロ**)。
- **増分 IC が必須である理由 (scan-round2 条項の凍結)**: BVC 符号は価格変化そのものから導出されるため、「volume シグナルが効く」という主張は**価格 momentum 単体に対する増分**を示して初めて成立する。増分を示さない結果は price-modality 3 周 FAIL の再着せ替えであり、いかなる形でも claim しない。

### 3.2 Estimand (凍結)

| 項目 | 定義 (凍結) |
|---|---|
| volume 系列 | 契約 c の closed 1h bar (bar_time_utc = バー開始)。**v = log(1+volume)**。volume=0 bar は baseline・event の両方から除外 |
| 季節性 baseline | **hour-of-week キーは America/Chicago 現地時刻** (取引所ローカル — UTC 固定だと US DST 遷移で diurnal パターンが 1h ずれ擬似異常を系統生成する。W3-2 条件 (4) と同根の構造対策)。trailing 同 hour-of-week **8 週** (K=8 サンプル) の median / MAD |
| 異常スコア | z(t) = (v(t) − median) / (1.4826 × MAD)。MAD=0 または baseline サンプル <6/8 の bar は無効 |
| onset event | z(t) ≥ z\* ∧ 直近 24h 以内に同契約の既 event なし (first-onset dedup)。z\* は §4 の機械規則で explore から凍結 (唯一の校正 DoF その1) |
| シグナル時刻 τ | **bar close = bar_time_utc + 1h** (volume はバー完成まで未知 — lookahead assert: forward 窓は τ 以降のみ。ingest は `filter_closed_bars` で形成中バー非保存) |
| momentum s(τ) | spot mid log-return、[τ−24h, τ] (spot 15m の τ 以前直近バー close 使用) |
| forward f(τ) | spot mid log-return、(τ, τ+24h]。**primary horizon h = 24h 固定** (explore 選択させない)。4h / 72h は secondary 記述のみ |
| **primary 統計量** | **pooled ΔIC = IC_evt − IC_all** — IC = Spearman(s, f)、per-pair rank 変換後 pooled (W3-1 と同一の pooled IC 規約)。IC_evt = event bar 上、IC_all = 同一窓の全有効 bar 上。ΔIC ≠ 0 が「momentum→forward 関係を volume が条件付ける」の直接測定 = 増分 IC 検定 |
| 帰無 | matched pseudo-event permutation — 契約毎に event 数・hour-of-week 構成を一致させた擬似 event 集合を有効 bar から非復元抽出 (24h dedup 同一適用)、ΔIC_perm を同一手続きで計算。**N=10,000、seed=20260729**。explore は両側 p、OOS は explore 凍結符号への片側 p。p 床は 1/(N+1) 表記 |
| swap | 全 horizon ≤72h のため multi-week swap 純額規定は非適用 (ハウスルールどおり multi-week のみ)。h=72h secondary に carry 概算を記述併記 |

### 3.3 Secondary (記述のみ、判定・claim 不使用)

- **BVC-signed flow**: BVC (Bulk Volume Classification) buy fraction = volume × Φ(Δp/σ_Δp) による符号付きフロー、§2.2 の符号写像で spot 方向へ変換。**BVC 符号は価格由来 — 本 secondary は verdict にいかなる寄与もせず、単独で claim 可能な結果を構成しない** (E13/E2 grey の射程を明示的に尊重)。
- per-contract ΔIC 分解、h ∈ {4h, 72h}、event 強度 (z の大きさ) との dose-response。

## 4. Explore プロトコル (trigger 発火時に実行 — OOS 非接触)

執行は §6 trigger 発火時に explore → (gates 通過時のみ) candidate 凍結追記 → OOS 単一接触を**同一手続き内**で行う。中間 peeking 禁止。

- **校正 DoF は 2 つのみ** (他の全パラメータは §3.2 で凍結済み):
  1. **z\*** ∈ {2.0, 3.0} — 機械選択: z\*=3.0 で explore pooled event 数 ≥700 (≈100/契約 ≈0.8/週) なら 3.0、未満なら 2.0。比較 1 回、grid 拡張禁止。
  2. **方向** = explore pooled ΔIC の符号 (継続増幅 ΔIC>0 / 反転 ΔIC<0 の両側スクリーン → 符号を凍結し OOS は片側)。
- **Explore gates (全て機械、いずれか不成立 → family FAIL クローズ、OOS 未接触保存)**:
  - (i) pooled |ΔIC| permutation 両側 **p < 0.05**
  - (ii) headroom: event bar の凍結方向 MFE(24h) p50 ≥ **10× per-pair RT friction** ([[friction-analysis]] 理論値 + floor 1.30p 感度、weekend_gap prereg と同一規約) を **≥4/7 契約**で充足
  - (iii) 単一 event または単一 UTC 週が pooled effect の **≥50%** を占めない (SNB 型支配ガード — W3-1 条件 (3) の同型継承)
  - (iv) 年次セグメント (2024 / 2025 / 2026、explore 内) の ΔIC 符号一致 **≥2/3** (incoherence 死型の機械 kill)
- Explore 完了時、本文書 §5.1 に凍結値 (z\*、符号、per-contract event 数、pooled ΔIC、gates 判定) を追記してから OOS に接触する。

## 5. OOS プロトコル + verdict 固定分岐

- **OOS 窓**: 2026-07-30T00:00Z 〜 **2027-01-31** (データ cutoff、約 26 週)。
- **validity gate (執行時)**: OOS 非ゼロ volume bar **≥2,500/契約** を **≥6/7 契約**で充足 (26 週 ≈ 2,990 bar 期待の 84%) ∧ `r3-market-data-ingest-freshness` が green。不成立 → **DATA-BLOCKED** (設計変更禁止の stale review — 「取れたところまでで走る」への事後緩和は W3-2 横断警告と同じく禁止)。
- **Primary**: pooled ΔIC、explore 凍結符号への片側 permutation **p ≤ 0.05 (m=1、単独 wave — W3-1 型)** ∧ 単一 event/週 支配 ≤50%。
- **ナイフエッジ 3 点 (T11 lesson、verdict 時必須)**: (1) z\* を {2.0↔3.0} で入替えて符号・有意性が flip しないか、(2) 単一 event 除外での再計算、(3) 隣接 horizon (4h/72h) の符号整合。
- **verdict 固定分岐**:

| verdict | 条件 | 帰結 |
|---|---|---|
| **PASS** | explore gates 全通過 ∧ OOS primary 成立 ∧ ナイフエッジ通過 | stage-2 (執行設計 pre-reg + user 最終承認) へ。**PASS ≠ edge claim ≠ live 昇格**。**E13 再入場資格が開く (§10)** |
| **FAIL (explore)** | §4 gates いずれか不成立 | family クローズ、**OOS 未接触保存**、同型再試行禁止を台帳記録 |
| **FAIL (OOS)** | explore 通過 ∧ OOS primary 不成立 | family クローズ、同型再試行禁止 (unsigned abnormal volume × 時間 baseline × momentum 増分 IC の全変種) |
| **UNDERPOWERED** | OOS pooled event **<100** | second look **1 回限り** (cutoff 2027-04-30 / verdict 2027-05-07、新自由度ゼロ) |
| **DATA-BLOCKED** | validity gate 不成立 | stale review — データ回復時の再開 or 正直クローズ。設計変更禁止 |

### 5.1 Explore 実行記録 (執行時に追記 — 本 LOCK 時点では空欄であること自体が観測前性の証明)

*(未執行 — trigger 発火まで記入禁止)*

## 6. Power trigger の数値凍結 (条件 (1))

- **first look = データ cutoff 2027-01-31 / verdict 期日 2027-02-05** — registry `e12-volume-first-look-deadline` (type=deadline_info) で機械監視。
- **数値根拠**: z\* 設計フロア ~0.8〜1 event/週/契約 → OOS 26 週で pooled ≥180 event 期待。IC の se ≈ 1/√N ≈ 0.07 — 片側 α=0.05 の confirm に最低限の検定力。**wave-2 の目安「~3ヶ月」(2026-07-24 台帳) はここで置換する**: 13 週では pooled ~90 event / se ~0.10 となり、confirm が構造的に underpowered。登録は無料であり待機コストはゼロ (他ラインが並走)。
- 期日前の執行 (前倒し) は**禁止** — 「良さそうだから早く見る」は peeking。DATA-BLOCKED/陳腐化 review (§8) だけが期日前の分岐。

## 7. Joint look ゼロ attestation (条件 (2))

既発生の QA look を全列挙する。**いずれも counts / timestamps / volume 単独の健全性確認であり、cme volume × spot price のジョイント量 (event-conditional return、IC、相関、条件付き分布) はいかなる主体も未計算**:

| 日付 | look | 内容 |
|---|---|---|
| 2026-07-18 | smoke (PR #102) | 2 symbol × 155 bars 保存成功、6E=F 非ゼロ volume 96% — volume 単独 QA |
| 2026-07-18 | scan-round2 実測 | 6E=F/6J=F 1h 13,733–13,735 bars、非ゼロ 96.5%、**日足 volume 列は壊 (1h 必須)** — volume 単独 QA |
| 2026-07-21 | backfill (§2.2) | 新規 95,069 行 / dedup 1,008 / first_bar 2024-02-27T05:00Z — 行数・timestamps のみ |
| 2026-07-29 | 本 LOCK 起草 | `/api/marketdata/status` の rows/first_bar/latest_bar (§2.1) — counts/timestamps のみ |

- **禁止宣言 (MoF P-10 型)**: trigger 発火による §4 explore 実行まで、いかなる主体 (main セッション・subagent・autopilot・Codex) も volume×価格ジョイント量を計算してはならない。日常の ingest 鮮度監視 (`r3-market-data-ingest-freshness`) は counts/timestamps 系のみで本 attestation と両立。

## 8. 陳腐化 review (条件 (5))

- **期日 2026-11-30** — registry `e12-volume-prereg-staleness-review`。review 内容: (a) ingest 健全性 (yfinance 経路の生存、7 契約 capture 継続)、(b) 設計前提の戦略的地位 (E12 を supersede する上位データ/決裁の有無)。
- **許容 outcome = 継続 or クローズ (data-blocked / superseded) のみ**。設計変更・データ look・トリガー前倒しは禁止。

## 9. 多重検定 (グローバル台帳 family #10)

- 本登録アクションは**測定ゼロ = BH/wave スロット非消費** (敵対的検証 [W3-3] の裁定どおり)。
- 執行時は**単独 wave m=1** (W3-1 と同型)。within-family: 検定エンドポイントは pooled ΔIC 1 本 (explore 両側 → OOS 片側)。BVC secondary / per-contract / 隣接 horizon / dose-response は記述のみで検定に数えない。
- cross-family: PASS は「第2モダリティの stage-1 実証」であり edge 主張ではない。live 経路は Rule 1 全段 (365d 相当 or Live N≥30 + Bonferroni + stage-2 pre-reg + user 承認) の責務。

## 10. E13 の再入場余地 (敵対的検証注記の恒久化)

- **E12 unsigned primary PASS 時のみ**: E13 (MASSIVE tick volume、12y) を「同一 estimand の歴史拡張」として**新 family / R1 手続きで再入場可** — 12y なら従来型 explore 2014-2021 / OOS 2022+ split が構成可能になり、E12 が実証した測定器を深い歴史で再検定できる。
- **E12 FAIL 時**: E13 ban 継続 (E2「tick volume は弱 proxy」verdict の射程内、scan-round2 棄却裁定どおり)。
- Databento 有料 unlock (CME 実 volume 歴史) は user 決裁事項として記録のみ (§2.2)。

## 11. 除外・注意

- **live パラメータ・コード・shadow 構成・Kelly・tier の変更ゼロ**。本コミットの変更は KB 文書 + registry JSON のみ。
- LOCK 後の設計変更禁止。verdict を見た後のいかなる再計算・grid 拡張・horizon 追加も禁止 (exit-repair pre-reg §7 と同じ拘束)。
- 執行時にデータ問題が発覚した場合は DATA-BLOCKED の正直クローズ経路のみ — 窓・universe・gate の事後縮小/緩和は禁止。
- 本文書は volume×価格ジョイントから導出された数値を一切含まない (§7 attestation の自己適用)。
