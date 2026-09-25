---
id: 20260925-0300-kalman-d7-live-constrained-bt
title: "[M1 clean live] kalman_d7_po_dn_flip — live exit スタック (C1〜C5 + C6 近似) 付き BT による診断: overlay 別の edge 減衰と winner/loser 別 hold 分布 (user 決裁 packet 用)"
owner: unclaimed
status: queued
created_at: 2026-09-25T03:00:00+0900
priority: P1
deadline: 2026-10-08 (registry `kalman-d7-live-exit-spec-mismatch-disposition`)
roadmap_gate: "M1 (clean live 月次符号転換)。今月唯一 LIVE 約定している戦略の live 仕様が BT と決定論的に不一致 = live は BT に無い戦略を走らせている状態。本タスクは診断のみ — 分解 (どの overlay が edge を削るか) と winner/loser 別分布を user 決裁 packet (10-08) に供給する。keep / demote はこの数字から機械的に決めない"
rule: R3 (計測のみ。tier / lot / live 配線の変更は本タスク範囲外。宣言通り保持 (max hold = 市場 bar 数 480 本 / 市場オープン時間ベース、wall-clock 120h ではない + 週末保持 + C0〜C6 免除) の live 導入は Rule 1 = user 決裁)
prereq_artifacts:
  - knowledge-base/wiki/strategies/kalman-d7-po-dn-flip.md (Overview / BT Performance / Exit Logic / 09-24 節「2026-09-25 確定」)
  - knowledge-base/wiki/decisions/kalman-d7-carveout-postfill-packet-2026-09-17.md (6. + 2026-09-25 追記)
  - bt-results/tv-overlays/kalman_d7_v18e_usdjpy_live_BACKUP.pine (live 版 Pine の参照。po_dn_flip v17 の canonical Pine は TV 側 — strategy card の Signal Logic / Exit Logic を仕様とする)
  - modules/demo_trader.py L3129-3173 (MAX_HOLD_SEC / _ENTRY_TYPE_MAX_HOLD) / L3135 (_is_pre_weekend) / L3702-3728 (適用箇所) / L3328-3372 (ATR BE 0.8 / trail 1.5→0.5) / L3732-3766 (TIME_DECAY_EXIT 半分時点) / L8439-8572 (_check_signal_reverse)
---

# 目的 (1タスク1目的)

`kalman_d7_po_dn_flip` の **BT (TV Pine、hold 無制限、480 bars ≈ 120h) と live (`daytrade` mode 8h cap
+ 金曜 21:45Z 全建玉クローズ) の仕様不一致**を、**live 制約を BT に入れて**同期間で再計測し、
**overlay 別に分解して診断する** (走 0〜5、下記)。出力は (1) どの overlay が BT edge をどれだけ削るか (2) winner / loser 別の
hold・exit 分布 (3) 8h 以内に完結する winner の割合 — で、これを registry entry の **user 決裁 packet (10-08)** に供給する。
**本タスクの数字から keep / demote を決めない** (C6 は再現不能、C1〜C5 も intrabar 順序は近似 — 「判定の扱い」参照)。
旧版の「EV ≤ 0 → R2 降格 / EV > 0 → 維持」は撤回済み。

# 背景

- 宣言 max hold 480 bars (~120h)、BT edge は winner を ~458 bars (~115h) 保持することに依存 (WR 23.91% / PF 3.866 /
  W/L 12.3×、N=46、2025-07-01→2026-05-19 USDJPY uptrend)。
- live は `MAX_HOLD_SEC["daytrade"]=28800` に override 無し → 8h で `MAX_HOLD_TIME` 強制決済。負け側 (SL 1.5×ATR) は
  8h 内に決着する保証は無く、C5 (4h 含み損 TIME_DECAY) は負け側も打ち切る — **どちら側がどれだけ削られるかは本 BT の winner / loser 別分布で初めて分かる**。さらに金曜 21:45Z の全クローズで週末を跨げない。
- 実走 3 fill (hold 4h04m / 54m / 58m、1W-2L) はこの上限に触れていないが、N=10 監視では上限の効果は測れない
  (エンジンが産めない結果を測る計画だった — PR #299 review P1)。

# live exit スタック (全部入れる — PR #299 review P1 2 巡目 4100301156)

live の `daytrade` 建玉に掛かる exit は 8h cap と金曜クローズだけではない。**以下 6 経路すべて**を BT に
入れないと「live 制約付き」を名乗れない (`modules/demo_trader.py` の行番号は 2026-09-25 origin/main):

| # | 経路 | 仕様 (live 実装) | 出典 |
|---|---|---|---|
| C0a | entry 時 SL 書き換え | `kalman_d7_po_dn_flip` は `_1H_PRESERVE_SLTP` に**無い** → 宣言 SL 1.5×ATR は捨てられ、**nearest_support − margin (SR ベース、RR≥1.0 の場合)** か **ATR × 1.0** (daytrade fallback) に置換、その後 **SL 距離を daytrade JPY で 5pip 以上 / 20pip 以下に clamp** (`MIN_SL_DIST` 0.050 / `MAX_SL_DIST` 0.200、L6910-6944)。session / recent-fast-SL buffer でさらに変わる | L6746 / L6867-6944 |
| C0c | 下流 SL 調整 (共有経路、`_1H_PRESERVE_SLTP` でも**スキップされない**) | UTC {0,1,18,19,20,21} で SL に **+0.2×ATR** バッファ / 直近 5 分に同ペアで fast SL (<120s) があれば SL 拡幅 / ラウンドナンバー (50pip 刻み) 近傍で **2.5pip 外側へ nudge** | L6947-7026 |
| C0b | broker TP 85% | `_QUICK_HARVEST_EXEMPT` に**無い** → OANDA へ送る TP は `signal_price + (tp − signal_price) × 0.85` (demo 側 TP は宣言のまま = demo⇄broker で TP が違う) | L10648 / L8179-8186 |
| C0d | MTF TP 拡張 (**C0b の前**に掛かる) | `_15m_tactical_bias` が strong で entry 方向と一致すると **TP 距離 ×1.3** (`_mtf_tp_bonus`)。その後 C0b の ×0.85 ⇒ broker TP は宣言 5×ATR に対し **一致時 ≈5.525×ATR / 不一致時 ≈4.25×ATR** の 2 値 | L6703-6731 / L6774-6781 |
| C1 | MAX_HOLD | entry から **28,800s (8h)** 超で成行決済 `MAX_HOLD_TIME` | L3130 / L3705-3728 |
| C2 | 金曜クローズ | 金曜 **21:45Z 以降**の最初の tick で全建玉成行決済 | L3135 / L3702 |
| C3 | ATR BE | MFE が **entry ATR × 0.8** 到達で SL → 建値 (+spread) | L3328-3340 (共通建値ガード) |
| C4 | ATR trail | MFE が **entry ATR × 1.5** 到達後、SL = price − **ATR × 0.5** で追随 (BUY) | L3358-3372 |
| C5 | TIME_DECAY_EXIT (C1 半分時点損切り) | hold > **14,400s (4h = 8h × 0.5)** かつ含み損なら成行決済 | L3732-3766 (kalman は免除リストに無い) |
| C6 | SIGNAL_REVERSE | hold ≥ **600s** 後、反対方向シグナルが confidence ≥ `confidence_threshold + 10` (下限 50) で成行決済 | L8439-8572 `_check_signal_reverse` |

- ATR の定義は live と同じもの (entry 時点の `_entry_atr`、14 期間 15m を確認して記載)。
- **C6 は BT で忠実に再現できない** (PR #299 review P1 3 巡目 4100391371)。live の `_check_signal_reverse` (L8439-8572) は
  (i) hold ≥ 600s、(ii) **同 mode で評価される全戦略**の反対方向候補が `confidence ≥ confidence_threshold+10` (下限 50)、
  (iii) score 閾値 (USD_JPY 固有)、(iv) **ADX > 20**、(v) **含み益 > ATR×0.3 の建玉は保護** (切らない) — の全部を要求する。
  PO 崩れ等の単一指標サロゲートは (ii)〜(v) を持たず、**早期の合成 exit は EV を上げも下げもする**ので下限にも上限にもならない。
  ⇒ 走 5 は「C6 を PO 崩れで近似した参考値」として**必ず「近似」ラベル付きで別掲**し、判定には使わない (下記)。
  忠実な再現には同期間の同 mode 全戦略 signal stream の replay が必要 — 本タスクの範囲外 (必要なら別タスクで起案)。
- ⚠️ 前版の「Python fallback では BE/Trail を無効化」は**撤回** — 無効化すると live と別の exit 分布になる。

# 実行手順

1. **eval canon = TV Pine** (MEMORY feedback_tv_edge_discovery_loop: Live > TV > Python BT)。strategy card の Signal Logic / Exit Logic
   (TP 5.0×ATR / SL 1.5×ATR) を実装した Pine に C1〜C6 を**累積**で足し、同期間 (2025-07-01→2026-05-19、USDJPY M15) で走らせる:
   - 走 0: 制約なし (現行 BT の再現 — N=46 / WR 23.91% / PF 3.866 に一致することを先に確認 = harness 検証)
   - 走 0′: +C0a+C0b+C0d (entry 時の SL/TP 変換。C0d は MTF strong 一致の有無で TP が 2 値になるので、一致判定は BT で再現しないので**両方の TP で走らせて併記** (近似)。一致率の live 実測は `_15m_tactical_bias` snapshot が fill 行に永続化されていないため出せない — follow-up 計装 — **これが「実走 R:R 2.5–3.3 vs 宣言 3.33」のズレの正体**。C0a の SR ベース SL は歴史的 `sr_entry_map` が無いと再現できない。**実行可能な近似は 2 択**: (A) `app.py` の `find_sr_levels_weighted` を Python port し、各 entry bar 時点の直近 N 本から SR map を再構築して live と同じ選択規則 (SR 優先 / RR≥1.0 / clamp) を掛ける (Python 走のみ、TV では不可) / (B) port が困難なら ATR×1.0 のみで走り、**SR 採用は「未再現」と明記**して what-if (ii) は省く。どちらを採ったかを結果表に書く。SR 採用率の live 実測は分岐が永続化されていないため出せない)
   - 走 1: 走 0′+C1 ／ 走 2: +C2 ／ 走 3: +C3+C4 ／ 走 4: +C5 ／ 走 5: +C6 近似 (以降の走は全て 走 0′ を土台にする) (**参考値。C6 は PO 崩れサロゲートで conf/score/ADX/含み益保護/他戦略シグナルを持たない — 「full live stack」と呼ばない**)
   - 累積にする理由: どの overlay が EV を削るかを分解する (処置 (b) Rule 1 packet を書く場合の根拠になる)
2. TV が使えない場合は Python port で同じ 6 走 (⚠️ Python BT は容疑者。走 0 が TV の N / WR / PF を ±10% で再現できなければ
   結果を採用しない。BE/Trail は **無効化せず C3/C4 として実装**)。
3. **摩擦調整**: USD_JPY RT friction 2.14pip (wiki/analyses/friction-analysis.md) を 1 トレード当たり差し引く。
4. 出力: 走 0〜5 の N / WR / PF / EV (pips、摩擦調整後) / Wilson 95% lower / exit 種別比率 (TP / SL / MAX_HOLD_TIME / 金曜 /
   BE / trail / TIME_DECAY / SIGNAL_REVERSE)。走 0 の **winner hold 分布 (bars in trade) と 8h 以内に完結した winner の割合**を明記
   (「制約 EV が正に残る余地」の直接指標)。
5. KB: `knowledge-base/wiki/analyses/kalman-d7-live-constrained-bt-2026-10.md` に結果 + 分岐判定。strategy card 09-24 節 /
   registry entry に結果リンク。**本タスクは判定を書かない** (packet 用の所見のみ)。

# 判定の扱い (凍結、3 巡目改訂)

- **走 0′〜4 は「C0 近似」** (PR #299 review 8 巡目): C0a は `sr_entry_map` が有効なら live は SR ベース SL を採る (RR≥1.0) が BT では ATR×1.0 で代用、C0c (低流動性時間 / fast-SL / ラウンドナンバーの SL 調整) と C0d (MTF strong 一致時の TP ×1.3、一致判定は再現不能で 2 値併記) も近似。どちらも「どの fill が SL に達するか」を変え得るので、**走 0′〜4 の分布を「live ルール忠実」と呼ばない**。感度は **BT 側の what-if** (完了条件参照) で出す — live ログには SR/ATR の選択枝も C0c 発動も永続化されていないため live 実測率は導出できない (計装は follow-up)
- **走 0〜4 (C1〜C5) はルールは決定論的だが、intrabar 順序は近似**: live の C3/C4 (BE / trail) と SL/TP は `_sltp_loop` が bid/ask を
  0.5s ごとに評価するのに対し、M15 OHLC では同一 bar 内で BE/trail 発動と SL/TP 到達のどちらが先かを決められない
  (PR #299 review P2 4 巡目)。⇒ 走 0〜4 も「**ルール忠実・順序近似**」とラベルし、**bar 内順序の仮定を明示** (既定 = 逆行先行 =
  保守側: 同一 bar で BE/trail 発動と SL 到達が両方あり得る場合は SL 到達を先に処理) し、**逆の仮定 (順行先行) での感度走を併記**する。
  両仮定の差が結論 (分解の順位 / winner 比率) を変えるなら packet にそう書く。tick / bid-ask replay は本タスクの範囲外。
  走 5 (C6 近似) は参考値
- **本 BT 単独では keep / demote を決めない**: live の exit 分布は C6 を含む 6 経路の合成で、C6 が再現できない以上、
  走 4 の EV の符号がどちらでも full stack の符号は確定しない (早期合成 exit は EV を上げも下げもする)。
  前版の「走 5 EV ≤ 0 → R2 降格」「不完全な走は保守側のみ正当化」は**撤回** — 不完全なシミュレーションは**どちらの側も**正当化しない
- 本 BT の役割 = **診断**: (1) 走 0 → 走 4 の分解で、どの overlay が BT edge をどれだけ削るか (2) winner / loser 別の hold・exit 分布
  (どちら側が打ち切られるか) (3) 8h 以内に完結する winner の割合 — を registry `kalman-d7-live-exit-spec-mismatch-disposition` の
  **user 決裁 packet** (10-08) に載せる。決裁肢 = (a) live exit を宣言仕様に合わせる (max hold を **市場 bar 数 480 本 (M15) / 市場オープン時間ベース**で実装 — 現行 L3708-3724 は wall-clock 秒なので「120h」だと週末の ~48h 休場を消費し 480 bars に届かない、休場・祝日込みで数える + 週末保持 + C3〜C6 免除 (BE / trail も宣言 BT に無い overlay なので外す) + **C0 免除 = `_1H_PRESERVE_SLTP` と `_QUICK_HARVEST_EXEMPT` への登録 + 下流 SL 調整 (C0c: 低流動性時間バッファ / fast-SL 拡幅 / ラウンドナンバー nudge、L6947-7026 の共有経路 — カウンタートレンド +0.25×ATR は `_mean_rev_types` 5 戦略限定で本戦略には掛からない) の免除フラグ新設 + C0d (MTF TP ×1.3) の対象外化** (宣言 SL 1.5×ATR / TP 5×ATR をそのまま送る — 現状この共有経路は exempt 集合でスキップされないので新フラグが要る) = Rule 1)
  (b) 現状維持 (live は BT の無い戦略と認識した上で執行 QA として継続) (c) shadow 降格
- autopilot が単独で取れる処置は**通常の live 損失停止規律 (Rule 2、live realized N ベース) のみ**。BT の数字を降格根拠に使わない

# 禁止事項

- 制約付き BT の EV が負でも**制約を外す方向の live 変更 (市場 bar 数ベース override / 週末保持 / exempt 登録) を提案・実装しない** (Rule 1、user 決裁)
- パラメータ (TP 5.0×ATR / SL 1.5×ATR / filters) の再最適化禁止 (カーブフィッティング禁止。足すのは live exit スタック **C0〜C6** (entry 時 SL/TP 変換 C0a/C0b/C0c/C0d + 保持・overlay C1〜C6) だけで、それ以外のパラメータ (entry filters / ATR 期間 / 宣言 TP 5×ATR・SL 1.5×ATR の**基準値**) は BT 宣言値のまま — 「8h + 金曜の 2 制約だけ」の旧実装は不可。C0 は禁止対象ではなく**必須の土台** (走 0′))
- 走 0 が現行 BT を再現できないまま制約付きの数字を出さない (harness 未検証の数字は引用禁止)
- 走 0〜5 のいずれの EV も、単独で keep / demote の根拠にしない (上記 判定の扱い)。特に走 5 (C6 近似) の数字を「full stack」と呼ばない

# 完了条件

- 走 0〜5 の表 (**走 0′〜4 は「C0 近似」ラベル** — SR ベース SL を ATR×1.0 で代用し下流 SL 調整 (C0c) も未再現、+ bar 内順序仮定の両方向、走 5 は「C6 近似」) + **C0 感度 = BT 側の what-if** (live ログは SL 選択枝 (SR / ATR) と C0c 発動を**永続化していない** — L6895-6908 / L6951-7026 にマーカー無し、ON_FILL の SL 距離だけでは分岐を復元できない — ので live 実測率は要求しない): (i) C0a を ATR×1.0 のみ / (ii) C0a の SR-stop — 上記 (A) の port ができた場合のみ「SR 優先」走を併記、できなければ省いて「未再現」と明記 / (iii) 5–20pip clamp 有 / 無 / (iv) C0c の低流動性時間バッファ有 / 無 / (vi) **C0c のラウンドナンバー nudge** (USD_JPY で SL が .000/.500 の ±2pip 以内なら 2.5pip 外側へ — 決定論的なので **base の C0 replay に含める**、有 / 無の感度も併記、L7008-7017) / (v) C0d の MTF ×1.3 有 / 無 — の各 what-if で走 0′〜4 を再集計し、**分解の順位と winner 比率がどの what-if で変わるか**を packet に書く。live 実測率は follow-up 計装 (SL 選択枝 / C0c 発動 / MTF bonus を `reasons` marker に記録、別タスク) の後に差し替える + winner/loser 別 hold 分布 + exit 種別比率 + packet 用の所見が analyses/ に保存され、done ファイルに '## Claude Review' が付く
