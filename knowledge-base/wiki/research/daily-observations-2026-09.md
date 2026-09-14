# Daily Observations — 2026-09 (S0 intake 層、記述級のみ)

**Protocol**: [[daily-market-review-protocol]] — p 値計算禁止 / α 消費ゼロ / 台帳番号なし / 卒業には ban/estimand 監査必須 / 凍結 look 保有 family の outcome 量は記載禁止 (registry 事前確認)

---

### O-2026-09-11-1: US CPI 日の初動フラッシュ → 反発 (USD_JPY)
- **現象**: 2026-09-11 (金) 12:30 UTC の 15m バーが値幅 87.5p (当日最大、出来高 5,397)。153.9 台 → 13:00 UTC に日中安値 153.220 → 安値からクローズまで 40.0p 反発 (瞬間最大 55.6p)、153.6–153.7 で週末クローズ。日足は O 154.457 / C 153.620 (−83.7p)
- **材料 (外部報道ベース、repo 内一次資料なし = 未確認)**: 12:30 UTC = 8:30 ET の米指標時刻に一致。FXStreet 2026-09-11 報道では US CPI 発表日、直前週に米 PPI 5.4% y/y、BoJ 9/17–18 25bp 利上げ織り込みとされる — **econ calendar 一次ソースでの確認は卒業時監査に委ねる**
- **トリガ日**: 2026-09-11 (卒業時、確認評価の窓からこの日付を除外すること)
- **想定メカニズム**: 高インパクト指標の初動オーバーシュートが流動性回復後に部分回帰する (announcement overshoot / liquidity withdrawal)
- **family 候補**: `event_flush_reversion` (新規)
- **反証可能な予測**: 次回 CPI/NFP 級イベントで、発表後 15–30 分の初動極値から 60 分以内に初動の 40%+ が回帰する頻度が方向無差別で観測されるはず
- **隣接 ban**: 🔴 **E15-H1 phase-0 CPI-fade が直接の先行 ban** — 同一 pre-reg (e15-e7-event-modality-prereg-2026-07-18) で発表後初動 fade (CPI/fade/30m/h12, CPI/fade/60m/h12, CPI/fade/30m/h24) を検証済み、**全て OOS C5 FAIL**。verdict はイベントモダリティ (カレンダー/サプライズ × M15) 枯渇を宣言、fade 再挑戦には新規 pre-reg + 敵対的検証 + CPI-fade C5 負 prior の継承が必須 (catalog #9 / prereg SIGN-FLIP 条項)。本観測との残余差分は (a) entry anchor = 発表後極値 vs 固定 30/60m オフセット、(b) horizon = 60m vs h12/h24 のみ — **この差分で ban を超えられるかは卒業時監査の判定事項で、現時点では否定的 prior が優勢**。なお E7 phase-1 (発表後 surprise-z 順方向 drift、FAIL 0/24) は方向逆の隣接 family (事前ポジショニング系は E8 で round-2 棄却済み)
- **経路**: 記録のみ (≥3 独立イベントまで S1 不可、E15 負 prior により卒業ハードル高)

### O-2026-09-14-1: weekend gap −50p が OANDA tradeable 前に消費 — WG_EXEC_B drift 境界の前提破れ (執行 QA)
- **現象**: 2026-09-13 日曜オープン USD_JPY gap −50.0p (Fri close 153.620 → Sun open 153.120、qualify 21.4p 超) で weekend_gap_fade が 21:05:03 UTC に仕様通り発火 (shadow row id 17602 記録)。live 送信は `ABANDONED_DRIFT`: OANDA tradeable 確認時点 (quote_age 7.5s) で drift +41.0p > 凍結境界 +8.0p。ギャップの ~47p が最初の 15m バー内 (大半は約定不能の halt 窓 ~4 分) で消費された。**価格系の記述のみ — 本 event の shadow outcome は意図的に記載しない** (G0'/G2/G3 凍結 look の汚染防止)
- **トリガ日**: 2026-09-13/14 weekend
- **想定メカニズム**: 大ギャップほど回帰が速く、リオープン halt 窓内で消費される → 境界導出時の実測 drift (mean +3.15p [qualifying N=8] / p90 6.7p [全 48 pair-weekend]) を、境界 +8.0p 比 ~5 倍 / p90 比 ~6 倍で超過。**qualify する最大級 event ほど live 送信が構造的に不可能になる選択バイアス**の疑い
- **family 候補**: なし (新規エッジではない) — 既存 `weekend_gap_fade` の執行契約観測
- **反証可能な予測**: 今後の qualify event でも |gap| と tradeable 時点 drift は正相関し、|gap|≥40p では drift>8p が常態のはず (shadow row の send_mid 記録 = 価格系のみで毎回検証可能)
- **隣接 ban / 凍結 frame**: weekend_gap は活性凍結 frame を 5 本保有 — volstate-split-weekend-gap-recheck (観測前 forward split 宣言 2026-07-29、唯一の事前登録 split) / weekend-gap-execution-amendment-g0prime (期日 2026-09-28、**本 event がその第 1 検証 event**) / F2 project-falsification-f2-wg-live-conversion / 凍結 G1/G2。outcome 量・追加 split の中間計算は全て禁止
- **経路**: **G0' 証拠として registry `weekend-gap-execution-amendment-g0prime` の週次監査へ回付** (drift +41.0p は price-only で §4.6 観測データとして適法)。+8.0p 境界の R1 再起案は **packet §6 の事前コミット (fill 不成立 2 連続 event 到達) まで保留** — 本 event は不成立 #1。meta-audit 集計基準 (live send 経路到達 event) では live fill 0/4 連続。user が独立に R1 再決裁を指示する場合はこの限りでない

### O-2026-09-14-2: CB 会合前週フラグ (weekend_gap_fade qualify event への marginal 記録のみ)
- **現象**: 2026-09-13 の qualify event (O-2026-09-14-1) は BoJ 会合 (9/17–18) 前週の週末に発生した — **CB 会合前週 = yes の marginal フラグとして記録** (event 単位の calendar count のみ)
- **トリガ日**: 2026-09-13/14 weekend
- **想定メカニズム**: 大イベント前週は週末ポジション軽量化でギャップの需給が薄い可能性 — ただし検証は G2/G3 凍結 look 後まで不可能
- **family 候補**: なし — 既存 `weekend_gap_fade` への calendar flag 併記のみ
- **反証可能な予測**: (凍結 look 前は定式化しない — 埋め速度・回帰率など outcome/条件付き量の計算は volstate 以外の split が事前登録されていないため禁止。CB-week split を検証したければ、蓄積前に registry へ conditional_info として事前宣言するのが唯一の適法経路)
- **隣接 ban / 凍結 frame**: O-2026-09-14-1 と同一 (weekend_gap の 5 frame)。**初稿はここで「30 分内回帰率の CB 週比較」を提案し敵対的レビューで P1 棄却された** — 未登録 split の事後シード = 観測前宣言手続きの正面違反 (教訓として残す)
- **経路**: 記録のみ (marginal flag)

---

## 週次 rollup

(初回 rollup は 2026-09-21 月曜)
