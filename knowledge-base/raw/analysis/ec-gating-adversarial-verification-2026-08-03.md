# 敵対的検証: equity_curve_shadow_gating forward pre-reg DRAFT (2026-08-03)

> **status: 非規範 (archival)** — 検証対象の DRAFT は SUPERSEDED-NEVER-LOCKED (並行セッションの v2 forward LOCK が PR #155 で main 先着)。#22 の SSOT = [[equity-curve-shadow-gating-explore-prereg-2026-08-03]]。race 記録: `raw/analysis/ec-gating-race-cross-audit-2026-08-03.md` (本検証が見落とした K1 型攻撃の記録含む)。
> 検証者: 独立 subagent (ファイル渡し、main セッションと独立にソース精読 + cutoff/eligibility 独自検算)。
> 対象: `raw/analysis/equity-curve-shadow-gating-prereg-draft-2026-08-03.json` (LOCK 前 DRAFT)
> 帰結: REQUIRED #1-#8 は DRAFT に全反映されたが、LOCK は撤回。REQUIRED #1-#8 の論点 (cutoff 算数一致・null 再連結仕様・censoring 保守性・P-10 whitelist 設計) は SSOT v2 の first look 執行時にも参照価値あり。

## verdict: SURVIVES-WITH-REQUIRED-AMENDMENTS

統計コア (K grid / 閾値 0 / uplift 定義 / Bonferroni×3 が §4.2 で**内部データ非接触のまま 2026-07-31 に凍結済み**、eligibility は機械評価、実行は registry 監視の期日執行) は健全で、forward 化の判断自体は正しい。ただし **cutoff 導出規則の算数が壊れている** (自称「機械規則」が自身の期日を再生産しない)、**s6 の censoring 独立性主張が解析的に誤り**、**P-10 ban の文言が既存本番モニタと初日から衝突する広さ**、**null の block 長頑健性の欠如**という 4 つの実質欠陥があり、LOCK 前修正必須。いずれも修復可能なため KILL ではない。

---

## 攻撃観点別判定

### A. 凍結違反 — **判定: 概ね「仕様化」で違反なし。ただし 1 件の内部矛盾 (cutoff 導出) と 2 件の運用ルール衝突が未処理**

- **real-time gate 定義 (`exit_time(j) < entry_time(i)`)**: 仕様化と認定。§4.2 の「直近 K closed trades」は closed の基準時点が未定義であり、DRAFT は実装可能かつ**より厳しい** (オーバーラップ排除) 読みを採用し、sequence 版を secondary 感度として保持。緩和ではない。
- **day-block permutation**: §4.2 は「block-bootstrap null」を概念レベルで凍結。bootstrap→permutation の置換は s4 が正しく自認する通り推論上の改善 (bootstrap は null 分布でなく標本分布を近似) であり、検定思想の変更ではない。**ただしアルゴリズムの「再連結」が未特定** (置換ブロックが元カレンダーの日スロットに載るのか端点連結なのか、block 境界を跨ぐ保有の扱い) — C で REQUIRED。
- **measurement window 548d / span≥365d**: §4.2 の「12-18 ヶ月」レンジの端点をそのまま使用 (365d=12mo 床、548d=18mo 上限) で仕様化と認定。注意点: 「window=上限 18mo」の選択は在庫メタデータを見た**後**に行われた permissive 側の選択だが、両端点とも 07-31 凍結レンジ内であり、メタデータのみの影響なので許容。
- **eligibility の window 内評価**: N≥300 を window 内で数えるのは全歴史カウントよりやや厳しい方向 — 仕様化。
- **cutoff 導出の内部矛盾 (実質欠陥)**: s5 は「epoch (2026-04-08) から 4 週間以内 (〜2026-05-15)」と書くが、**2026-04-08 + 28d = 2026-05-06 であって 05-15 ではない** (在庫の実 epoch 2026-04-02 からなら 04-30)。「恣意的な前倒し・後ろ倒しの余地を排除」と主張する機械規則が、自身の宣言期日を再生産しない。これは事後裁量の余地そのもの → REQUIRED #1。
- **台帳 #22 の凍結条件との整合**: hypothesis-catalog「全 pre-reg 共通ハード条件」のうち **(a) exit 機構フリー固定ホライズン測定、(b) explore 窓 headroom≥10x 実証後 LOCK** の 2 つを本 DRAFT は満たさず、かつ**適用除外を明文化していない**。estimand が「実 book の配分 counterfactual」なので実 exit 込み pnl_net が正しく、新規トレード・新規摩擦ゼロなので headroom も非適用 — 論理は立つが、凍結ハード条件からの逸脱は on-record の差分節が必須 → REQUIRED #6。

### B. 観測前性 — **判定: 骨格は守られているが、attestation が E12 水準に達していない + 「純 forward」の過大主張**

- 分析パラメータ (K/閾値/統計量/Bonferroni 式) は EA sweep 時点 (07-31、内部データ非接触を sweep 自身が attestation) で凍結済み — **候補選択の自由度が構造的に存在しない**ため、本日の N/span メタデータ look は E12 §2.1 の counts/timestamps look と同格で汚染にならない。在庫 artifact も実査で P&L 非含有を確認 (メタデータのみ)。
- **穴 1 — attestation の列挙不足**: E12 は既発生 look を**全**列挙した。本 DRAFT は 2026-08-03 の R2 alert 1 回分のみ記載。R2 alert は cron の反復実行であり (ファイル名 `-0236` が示す)、**過去の全実行歴 + 開始日 + 統計量定義の code path** をクラスとして列挙すべき。2026-07-31 の quant-eval 全数監査 (live 出血分解、shadow 集計にも接触) も不掲載 → REQUIRED #5。
- **穴 2 — scratchpad の生 P&L**: 在庫調査は `/api/demo/trades` 全量 (15,008 行、**per-trade pnl_pips 込み**) をダウンロードしており、E12 の「status API の counts のみ」より接触が深い。「trailing-K 未計算」は自己申告のみで、生データが scratchpad に残置される限り事後計算の物理的障壁がない → LOCK 時に削除を義務化 → REQUIRED #5。
- **穴 3 — 「E12/MoF 同型」は過大主張**: E12 の OOS は LOCK 時点で**未生成バーのみ** (純 forward)。本件の first look window は **~4 ヶ月分 (~30%) の既実現データを含む** forward-completing 設計であり、その既実現部分は R2 alert の 30d EV として反復観測済み・demote 判断にも使用済み。候補選択 DoF ゼロ + パラメータ事前凍結により許容できるが、同型主張のまま LOCK するのは不正直 → REQUIRED #7。
- R2 alert (30d EV/WR/PF) の継続は「系列順序に条件付けない aggregate」carve-out で両立可とする論理自体は妥当。ただし E の ban 文言問題 (下記) と表裏。

### C. 統計設計 — **判定: intraday セルには概ね正しい null。multi-day 保有と低周波 drift に対して anti-conservative な穴が 2 つ**

- **day-block null の照準**: 破壊されるのは日跨ぎ依存 = 検定対象そのもの、日内構造は保存 — 概念は正しい。real-time gate 定義が gate 入力と被 gate トレードの保有期間オーバーラップを**定義レベルで排除**している点は優秀 (機械的相関の主経路を断つ)。
- **穴 1 — multi-day 保有の cross-day オーバーラップ**: gate 入力トレード同士 (j1 が月曜 close、j2 が月曜→火曜跨ぎ) の P&L 相関は block 境界を跨ぐため、シャッフルで破壊される。null 側の gate 和の分散が実データより縮む → **p 値が anti-conservative**。scalp セルでは無視できるが、daytrade/swing モードのセルでは実質的。1 日 block は「保有 ≪ 1 日」の暗黙仮定に立っており、その仮定が eligibility に書かれていない → REQUIRED #2。
- **穴 2 — 低周波 EV drift の混入**: 置換 null は日 block の交換可能性を仮定するが、セル EV の緩慢な単調劣化 (戦略 decay) があるだけで gate_on が好調期にクラスタし uplift>0 が機械的に出る。仮説は「短期 (K=5-20 trades) 持続性」なのに、検定は**任意の非定常性**を signal として拾う。knife-edge (3)「両半分が両方負でない」は「片方が強負でも通る」ほど弱く、この交絡を殺せない → REQUIRED #2 (block 長頑健性) + OPTIONAL (時間半割の強化)。
- **再連結アルゴリズム未特定**: 上記 A 参照 → REQUIRED #2。
- **Bonferroni m**: eligible セル数×3、機械評価、degenerate 組を m から除外しない (保守) — 事後裁量なし。5000 permutations の p 床 1/5001≈0.0002 < 想定 α_bonf (m≤36 で 0.0014) — 分解能 OK。微小残余: entry_type 文字列の改名/分割 (例: vol_momentum_scalp の env 2 本併存) がセル定義を動かしうる → OPTIONAL。

### D. 交絡 (R2 demote) — **判定: 遮断論理は方向として機能するが、s6 の独立性主張は解析的に誤り (幸い保守方向)**

- demote → eligibility 縮小のみ、という主張は正しい (emission 停止セルは span 凍結で規則的に不適格)。
- **s6 の誤り**: 「停止時刻は過去情報のみの関数 = H0 下で gate と次トレード pnl の独立性を破らない」は**偽**。R2 stop のトリガー変数 (trailing 30d EV) は gate 変数 (trailing-K 和) と同族であり、「365d 生き残った」= **path 汎関数 (走行 trailing EV が demote 域に落ちなかった) への条件付け**。i.i.d. 系列でもこの条件付けの下では gate_off 直後の pnl が上方に歪む (生存に必要だったから)。ただし歪みの向きは **uplift を押し下げる = H1 に対して保守的** — type-I は守られ、power が削られる。「妥当性は保たれる」でなく「バイアス方向が保守的」と書き直すべき → REQUIRED #3。
- demote 執行者と pre-reg 起案者が同一という利益相反は、demote 基準が cron 機械判定 + user 決裁である点、staleness review が demote registry 影響をメタデータで監査する設計で bounded。可。
- **副次発見 (F にも波及)**: R2 alert の demote 手段は「戦略単位 env var 除去」と「セル単位 registry 追加」の**二重系**で、env 除去を選ぶと CRITICAL でない同戦略他セル (xs_momentum×GBP_USD/USD_JPY、sr_break_retest×USD_JPY/GBP_JPY) まで emission が死に、DRAFT の eligible 予測を直撃する。staleness review でどちらの機構が使われたか記録必須 → REQUIRED #8。

### E. banned/LOCKED 隣接 — **判定: 衝突なし。二重ゲート問題の残余は stage-2 送りで正当。ただし P-10 ban 文言が自傷的に広い**

- 19 banned family はすべてシグナル族、本件は配分層で estimand 非重複 — EA sweep の実査判定を追認。FAIL 時 retry-ban のスコープ (「自己 shadow P&L trailing-window gating 全変種」) も適切。
- LOCKED 4 本: shadow book 内部 P&L のみ使用で E1 (positioning) / E7 (サプライズ) / E12 (volume×価格) / MoF (介入 forward) のロック窓・ジョイント量のいずれにも非接触。並列枠も #21+#22=2/3、登録アクションのスロット非消費は E12 [W3-3] 裁定と同型 (その裁定に相当するのが本検証)。
- 既存 R2/watchdog との二重ゲート: 測定は「emission された shadow 系列内の counterfactual 対比」で live 実状態から独立 — 遮断は設計自体で成立。live gate 化時の相互作用は stage-2 R1 の責務として明示的に切り出し済み — 正当。
- **問題 — ban 文言の過剰包摂**: s7 の「equity-curve 由来の系列条件付き量**全般**」は、cumulative P&L 曲線・drawdown (系列順序の汎関数!) を含む読みになる。本番 `/api/risk/dashboard` は DD/MC を常時計算しており、これが shadow セルに触れるなら **ban は LOCK 当日から恒常違反**。carve-out は「30d 集計」「メタデータ」しか挙げていない → 禁止対象を「セル別 trailing-window **gate 条件付き**統計 + uplift 型対比」に精密化し、既存本番モニタを名指しで whitelist する必要 → REQUIRED #4。

### F. 実行可能性 — **判定: eligible ≥2 は堅い。ただし DRAFT の 6-12 予測は demote シナリオ下で楽観、実質 3-7**

在庫生データからの独自検算 (蓄積レート線形外挿、cutoff 2027-05-15、必要 span 365d + window 内 N≥300):

| セル | N (rate/mo) | cutoff 時予測 N | span | demote 露出 |
|---|---|---|---|---|
| session_time_bias×GBP_USD | 328 (93.7) | ~1,209 | 13.0mo ✓ | promote alert 対象**外** (65 戦略リストに不在) |
| session_time_bias×EUR_USD | 276 (79.3) | ~1,021 | 13.0mo ✓ | 同上 |
| dual_sr_bounce×EUR_JPY | 128 (35.4) | ~461 | 13.0mo ✓ | 同上 |
| sr_break_retest×USD_JPY / GBP_JPY | 159/147 (41) | ~545/~536 | ✓ | **env 除去なら死** (同戦略 2 セルが CRITICAL) |
| xs_momentum×GBP_USD / USD_JPY | 200/141 (56/39) | ~722/~508 | ✓ | **env 除去なら死** (EUR_USD が CRITICAL) |

最悪ケース (9 demote 全て戦略単位 env 除去で執行) でも **3 セル (m=9)** が残り、UNDERPOWERED 分岐 (eligible<2) には届かない見込み。re-arm 1 回 + 正直クローズの分岐構造も E12 型で妥当。cutoff 恣意性は A で指摘の通り算数破綻が REQUIRED #1。eligible<2 という UNDERPOWERED 閾値自体は新規自由度だが、今凍結する分には可 (根拠一文の追記が望ましい — OPTIONAL)。

### G. 機会費用/設計妥当性 — **判定: forward 化が三択中最善。棄却理由 4 点は全て妥当**

- **(a) 事後緩和の信頼性毀損** — 妥当 (span 床を今日 4mo に緩めれば「K/閾値凍結」の規律主張全体が死ぬ)。**(b) censored 循環性** — 妥当かつ本検証の D 分析で裏付けられる (5 セル中 3 つは運用者が equity 劣化を見て止めた系列であり、その上で equity gating を測るのは条件付けの自己言及。しかも 4mo 版は生存条件付けの歪みが span 比で最大化する)。**(c) 単一レジーム** — 妥当 (regime 持続性仮説は regime 遷移を跨がないと識別できない)。**(d) 単一クリーンショットの焼却** — 妥当 (family self-LOCK 下で underpowered 実行は E15 phase-0 の C5 教訓の再演)。
- 「不成立クローズ」との比較: 登録コスト ~0 (スロット非消費・測定ゼロ)、待機は他ライン (E7 08-28 / E1 10-15 / E12 2027-02) と並走 — クローズより優位。**唯一の隠れコスト = P-10 ban が 9.5 ヶ月間、運用・研究の equity-curve 系診断を縛ること**。これは E で指摘の ban 精密化 (REQUIRED #4) で許容水準に落ちる。
- 結論: forward 化は正しい。ただし「観測前」の看板は REQUIRED #7 の誠実化とセットでのみ成立。

---

## REQUIRED amendments (LOCK 前必須)

1. **s5 cutoff 導出の算数修復**: 「epoch 2026-04-08 から 4 週間 = 〜2026-05-15」は偽 (04-08+28d=05-06)。(i) 規則を「series start ≤ epoch+4wk=2026-05-06 → cutoff = 2027-05-06」に直して期日をずらす、または (ii) cutoff 2027-05-15 を維持し「epoch+365d+5週間 buffer の凍結カレンダー日 (機械導出でなく本 LOCK で固定)」と正直に書き換え、「恣意性排除」の主張を削除する。どちらでもよいが**宣言規則と宣言期日は一致していなければならない**。
2. **null の仕様確定 + block 長頑健性**: (i) 再連結アルゴリズムを 1 文で凍結 (「置換された日 block は元カレンダーの active 日スロットへ順に割当、block 内相対時刻・保有時間保存」等)。(ii) knife-edge (4) を追加: **7 日 (暦週) block permutation で p < 2×α_bonf を維持** — multi-day 保有の cross-day 相関と低周波 drift の双方に対する頑健性を 1 本で担保。(iii) primary の暗黙仮定を明文化: p95 hold > 24h のセルは primary から除外し secondary 記述に落とす (または block 長をセル別 `max(1d, ceil(p95_hold)+1d)` で機械設定)。
3. **s6 operator_stop_censoring の主張修正**: 「H0 下で独立性を破らない」を削除。正しくは「R2 stop は gate と同族の trailing P&L 変数でトリガーされるため生存条件付けは交換可能性を破る — ただしバイアス方向は gate_off 側 pnl の上方歪み = uplift 押し下げ = **H1 に対し保守的**。type-I は保たれ power が犠牲になる」。verdict 解釈節にも同旨を固定文言で。
4. **P-10 ban の精密化**: 禁止対象を「セル別 trailing-K (または <90d 窓) の **gate 条件付き** P&L 統計・uplift 型対比・gate 状態系列」に限定列挙し、既存本番モニタ (R2 alert 30d 集計 / watchdog / risk dashboard の DD・MC / quant-eval) を**名指しで** whitelist。risk dashboard の DD が shadow セル粒度に触れないこと (live book のみ) を確認の上 1 行明記。
5. **attestation の完全化 + 生データ処分**: (i) R2 alert cron を「反復モニタのクラス」として開始日・統計量定義の code path 込みで列挙、(ii) 2026-07-31 quant-eval 全数監査を追加、(iii) **scratchpad の生トレード抽出 (P&L 込み 15,008 行) を LOCK 時に削除し、削除を attestation に記載**。first look 時は fresh 抽出 + sha256 凍結 (s2 既定) のみを正とする。
6. **台帳ハード条件の適用除外節**: 「exit 機構フリー固定ホライズン」「headroom≥10x 実証後 LOCK」の 2 条件について、estimand が配分 counterfactual (実 book の実 exit が測定対象そのもの / 新規トレード・新規摩擦ゼロ) であるための非適用を明示差分節として追加。live 転送時の摩擦は stage-2 R1 の責務と再掲。
7. **「観測前 forward」主張の誠実化**: first look window の ~4 ヶ月が LOCK 時点で既実現であり E12 の純 forward OOS と非同型であることを明記。許容根拠 (分析パラメータは 2026-07-31 に内部データ非接触で凍結済み・候補選択 DoF ゼロ・既実現部への look は 30d aggregate とメタデータのみ) を同節に固定。
8. **registry エントリの完全形 + demote 機構の記録義務**: LOCK 時の 2 エントリに doc/message フィールドを registry 既存形式どおり付与。staleness review (2027-01-15) の scope に「R2 demote が env 除去 (戦略単位) か registry (セル単位) かの別と、eligible 予測への影響」をメタデータ項目として追加。

## OPTIONAL notes (非必須)

- knife-edge (3) の強化: 「両方負でない」→「両半分の符号一致 (両方 ≥0)」で decay 混入への防御が実質化する (E12 の年次符号一致 ≥2/3 と同型)。追加は保守方向なので凍結違反にならない。
- UNDERPOWERED 閾値 eligible<2 の根拠一文 (単一セルでは family 主張として脆弱、等) を追記。
- セル定義の改名耐性: entry_type は抽出時の生文字列で固定、改名・分割された系列の合成禁止を 1 行凍結 (m 操作の芽を摘む)。
- s3 の eligible 予測 6-12 は demote 執行シナリオ次第で 3-7 が現実的 — 予測帯を下方修正しておくと staleness review の基準線が正直になる。
- 検定力の記述的見積 (N~460-1,200・m~9-21 での検出可能 uplift 規模) を verdict 解釈節向けに事前併記しておくと、FAIL 時の「power 不足 vs 効果不在」の切り分けが速い。

## 総括

DRAFT の骨格 — §4.2 でデータ非接触のまま凍結された分析パラメータを一切動かさず、物理的に充足不能な eligibility を forward 執行に転換する — は E12/MoF 系譜の正当な適用であり、span 緩和即日実行の棄却理由 4 点 (特に censored 循環性) はすべて妥当。KILL 相当の欠陥はない。ただし「機械規則」を自称する cutoff 導出が自身の期日を再生産しない算数破綻、multi-day 保有と EV drift に対して anti-conservative になりうる 1 日 block null、解析的に誤った censoring 独立性主張、初日から本番モニタと衝突する広さの P-10 ban 文言の 4 点は、この pre-reg の存在意義 (事後裁量ゼロの証明) を直接毀損するため LOCK 前修正必須。REQUIRED #1-#8 反映を条件に LOCK 可。
