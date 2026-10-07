# kalman_d7_po_dn_flip — live exit 仕様非同期の disposition packet (2026-10-07、user 決裁、順位のみ)

> **種別**: rule:R1 user 決裁パケット (Claude は起票・順位・既定挙動の明示まで。(a)/(b)/(c) の選択は user 専権)
> **Status: 起票 (2026-10-07、autopilot) — registry `kalman-d7-live-exit-spec-mismatch-disposition` (期日 10-08) の成果物。user 返答期限 = 2026-11-30 ([[integrated-decision-packet-d1-d12-2026-09-22]] D7 と同時に返す — §8-8)**
> **記述規律**: 制約付き BT ([[kalman-d7-live-constrained-bt-2026-09-27]]) は **harness FAIL (TV canon を ±10% で再現しない)** のため、**走 0′〜5 の数値 (EV / WR / PF / N) は本稿に載せない**。載せるのは分解の **順位・向き・exit 種別の構造** のみ。live fill の outcome は R2 `t9-kalman-d7-live-n10-ev-check` (N=10) の estimand 凍結が D7 承認待ちのため **件数と exit 種別のみ**。Live = `oanda_trade_id != ''`。

## §0 何が起きているか (確定している事実)

1. **宣言仕様 (BT canon) と live 実装は決定論的に非同期** ([[kalman-d7-po-dn-flip]] 09-24/09-25 節、PR #299): live は `MAX_HOLD_SEC["daytrade"]=8h` (override なし) + 金曜 21:45Z 全クローズ + BE (ATR×0.8) / trail (ATR×1.5→0.5 幅) / 4h 含み損 `TIME_DECAY_EXIT` / `SIGNAL_REVERSE` の overlay 4 + **entry 時点の SL/TP 置換 (C0: SL は SR or ATR×1.0、TP は ×0.85 短縮、MTF strong で ×1.3)**。BT の exit は TP 5×ATR / SL 1.5×ATR (宣言) のみ。
2. **宣言 TP 5×ATR が canon の exit である保証もない** (analyses §0): BT aggregate payoff (PF × (1−WR)/WR) は固定 TP/SL の上限を大きく超え、canon exit = **PO-DN flip (長期保持)** を強く示唆する — **確定ではない** (ATR 異質性・480 bar cap の早期クローズで上限は超え得る、Codex P1)。確定の唯一の経路 = **TV で v17 canon 再走** (Codex queue `20260927-0300-kalman-d7-v17-canon-tv-harness`、user の TV desktop 起動が前提 = 10-07 時点で未着手)。
3. **harness FAIL**: Python port は tp5 変種・flip 変種・flip 定義 5 候補のいずれも canon を ±10% で再現しない (要因: v17 Pine 不在 / Massive vs OANDA feed / EMA・percentile 初期化 / 週末 fill)。
4. **live 実測 (件数のみ)**: 3 variant 合算 LIVE fill **6 本** (po_dn_flip 5 / ema75_break 1、2026-09-10〜10-05、clean)。exit 種別は SL_HIT (ON_FILL SL ≈ 20p 帯) / SIGNAL_REVERSE / 週末 `MARKET_HALTED` 経由の日曜 SL (#957198、demo は WEEKEND_CLOSE で符号反転 = 既知 halted-exit 族) — **winner ride (hold 65〜168h) 形状の fill は 0** (8h cap で構造的に不可能)。`[SLTP_CONSTRUCT]` marker (PR #300、09-26 デプロイ後) 付き fill で C0 の分岐率を次回以降差し替える。
5. **この間の fill は BT 検証の N に数えない** (estimand が違う、card 09-24 節) — R2 (realized N ベースの損失停止) だけが autopilot の権限。

## §1 分解の順位 (harness 未検証 — 向きと順位のみ、全 what-if (SR 優先 / MTF ×1.3 / lowliq 無し / rn 無し / broker TP 0.85 無し) で不変)

```
edge 削減の大きさ:  C3/C4 (BE + trail)  ≫  C0 (entry 時 SL/TP 置換)  >  C6 近似 (SIGNAL_REVERSE)  >  C5 ≈ C2 (小、符号は順序仮定依存)
C1 (8h cap) は tp5 変種上では正 (loser の早期打ち切り) — flip 形状では winner を 100% 殺す (hold 65–168h、8h 内完結 0%)
```

- **C3/C4 BE+trail が最大の削減要因** で、どの順序仮定・what-if でも 1 位。宣言 BT に無い overlay。
- **C0** は 2 位。SR 優先 / MTF ×1.3 / broker TP 無しで走 0′〜2 の符号が変わる = **C0 免除の効果は「符号を変える」規模** (大きさは引用禁止)。
- **C6 (SIGNAL_REVERSE)** は同 mode 全戦略の signal stream 依存で BT 再現不能 — 近似参考値、順位 3 位。
- **C5 (4h TIME_DECAY) / C2 (金曜クローズ)** は小さく、符号は intrabar 順序仮定と境界 bar の扱いで反転する — **符号を引用しない**。C2 の帰属 2 件は週末ギャップ運を含み性質ではない。
- **C1 (8h cap)** は exit 形状に依存: canon が flip なら winner を全滅させる (致命)、tp5 なら loser 打ち切りで正。**canon exit の確定が (a) の定義に先行する理由**。

## §2 決裁肢 (card 09-24 節 3 巡目改訂を継承)

| 肢 | 内容 | 要件 | 既知のリスク |
|---|---|---|---|
| **(a)** live exit を宣言仕様に合わせる | max hold を **市場 bar 数 480 本 (市場オープンの 15m bar のみ数える — 週末・祝日の休場は bar 数に含めない。wall-clock 秒だと休場 ~48h を消費して 480 本に届かない)** + 週末保持 + C3〜C6 免除 (BE / trail / TIME_DECAY / SIGNAL_REVERSE) + C0 免除 (`_1H_PRESERVE_SLTP` / `_QUICK_HARVEST_EXEMPT` 登録 + 下流 SL 調整 [lowliq +0.2×ATR / fast-SL / rn nudge] の免除フラグ新設 + MTF TP ×1.3 対象外化) | **Rule 1** (user 決裁) + **canon exit の確定が先**: flip なら (a) = flip exit (PO-DN、定義は TV canon) + SL 1.5×ATR + 480 市場 bar / tp5 なら宣言 TP 5×ATR のまま。**TV 再走前に (a) を定義すると、どちらの exit を復元するか決まらない** | 週末ギャップ露出 (480 bar = 5 営業日で大半が週末を跨ぐ) / storm guard 未 enforce 下での長期建玉 (trail を外せば replacement storm は消える) / 1000u 固定なので資金時計への影響は ¥200〜300/敗 規模 |
| **(b)** 現状維持 | BT の無い戦略と認識して執行 QA 継続 (fill ごとに hold・exit 種別・demo↔broker 差を card に追記)。R2 (N=10 EV<0、broker realized net) で損失停止 | 決裁のみ (code 変更なし)。**D7 の estimand 凍結 (broker realized net) 承認が前提** — 承認前に N=10 到達なら判定保留 | 「測っているのは宣言と別の戦略」の状態が続く = fill を BT 検証に使えない。carry_dip と同型の契約破棄セルが 2 本並走 |
| **(c)** shadow 降格 | live carve-out 停止 (env `KALMAN_D7_LIVE_ENABLE=0`)、shadow 継続 | Rule 2 相当だが **実現損失の根拠 (R2 predicate) が未成立 (6/10)** なので「損失停止」ではなく「仕様非同期を理由にした降格」= user 決裁 | 原則 1 (攻める) に反する側。shadow 行も同じ exit スタックで走るので非同期は解消しない (測定は続くが同じ estimand) |

**autopilot 単独で取れるのは (b) の既定挙動と Rule 2 (R2 predicate 成立時の損失停止) のみ。** 前版「full stack EV≤0 → R2 降格」は撤回済み (BT 単独で keep/demote を決めない)。

## §3 Claude 推奨 (決裁の代替ではない)

- **推奨 = (b) を既定に、(a) は TV canon 再走が閉じた後に「exit 種別を確定した (a′)」として再起案**。理由: (1) (a) は今定義できない (§1 C1 の向きが canon exit に依存)、(2) (c) は実現損失の根拠が無い (6/10) のに原則 1 を破る、(3) (b) は決裁のみで estimand (broker realized net) を凍結でき、R2 の読み手 (registry 12-09) が既にある。
- **TV 再走の実行は user 操作 (TV desktop 起動 + slot 再構築)** — 対話セッションで依頼する。再走が 11-30 までに無ければ (a′) は 12-09 R2 判定の後へ繰り延べ (期日は registry で管理)。
- **(b) 下での追加義務 (R3、Claude 自走可)**: `[SLTP_CONSTRUCT]` marker 付き fill が N≥5 になった時点で C0 分岐率 (SR 採用 / lowliq / MTF ×1.3) を `tools/sltp_construct_readout.py --since 2026-09-26` で読み、analyses §3 の what-if 列を live 実測率に差し替える (件数・距離のみ、outcome 非読)。**読み手 = REG `kalman-d7-sltp-marker-c0-readout`** (live_count_decision、entry_type prefix `kalman_d7` × USD_JPY × `reasons_marker=[SLTP_CONSTRUCT]`、since 2026-09-26、n_decide 5、期日 2026-12-09 = R2 と同日; 10-07 時点 marker 付き kalman live fill **3 本** [po_dn_flip 2 / ema75_break 1] — Codex P2 4202640529)。

## §4 無回答時の既定挙動

- (b) 現状維持。R2 `t9-kalman-d7-live-n10-ev-check` (期日 2026-12-09、n_decide 10) は **D7 未承認なら N=10 到達時に判定保留 → user 再決裁** (postfill packet §3)。連続 3 SL (3 variant 合算) は即時 user review (不変)。
- 損失停止以外の変更 (hold / exit / SL / TP / lot / variant / pair) は行わない。storm 拡張凍結 (postfill packet §3) は guard 4 点セットの main 着地まで継続。

## §5 返答書式

```
D7: 承認 + disposition (b)            ← 推奨。(a) は TV canon 確定後に (a′) として再起案
D7: 承認 + disposition (a) [flip|tp5]  ← exit 種別を指定 (TV 再走前は指定不能 = 実装不能)
D7: 承認 + disposition (c)
```

## §6 監視読み手

| 層 | 読み手 | 内容 |
|---|---|---|
| binding | registry `t9-kalman-d7-live-n10-ev-check` (live_count_decision、12-09) | R2。estimand = broker realized net (D7 承認で凍結) |
| disposition | registry `kalman-d7-live-exit-disposition-user-decision` (新設、期日 2026-11-29 = 返答期限 11-30 の前日規則) | user 返答の有無。無回答 = (b) |
| C0 実測率 | registry `kalman-d7-sltp-marker-c0-readout` (live_count_decision、marker `[SLTP_CONSTRUCT]`、n_decide 5、12-09) → 発火時に `tools/sltp_construct_readout.py --since 2026-09-26` | marker 付き kalman fill の分岐率 (件数・距離のみ)。10-07: 3/5 |
| harness | Codex queue `20260927-0300-kalman-d7-v17-canon-tv-harness` | TV 再走 (user 操作待ち) |

## 関連
[[kalman-d7-po-dn-flip]] / [[kalman-d7-live-constrained-bt-2026-09-27]] / [[kalman-d7-carveout-postfill-packet-2026-09-17]] / [[kalman-d7-minlot-carveout-prereg-2026-09-01]] / [[integrated-decision-packet-d1-d12-2026-09-22]] §8-8 / [[sltp-construct-marker-2026-09-26]] / MEMORY `project_kalman_constrained_bt_harness_unverified_2026_09_27` / `project_kalman_live_exit_stack_mismatch_2026_09_25`
