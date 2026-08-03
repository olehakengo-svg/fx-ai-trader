# level-family (wave-4) 候補 敵対的検証 verdict (2026-07-31)

**検証者**: 独立 subagent (payload はファイル渡し: `level-family-candidates-2026-07-31.json`)。
一次ソース精読照合: postmortem 2026-07-24 / hypothesis-catalog md+JSON (ny-cut 他 7 エントリ精読) /
wave3・new-angle 敵対的検証 2 本 / 3 corpse memory + 3 falsification decision 全文 /
ws3-asymmetry-oos-prereg §8 / e12-volume-forward-prereg §2,§7,§10 / rnb-usdjpy カード /
weekend-gap-oos-prereg 全文 (§2/§4/§9/§11) / wave1-tv-explore-protocol-freeze /
external-hypothesis-scan round1 (E2) + round2 (E13) / tier-master (trendline_sweep) /
prereg-trigger-registry (#11 recheck) / `data/cache/massive/` `data/external/` `tools/e20_rates_ingest.py` 実在確認。

**サマリ: 生存 = L-a + L-b (いずれも GO-WITH-CONDITIONS、単独 wave 直列)。L-c / L-d / L-e は KILL (triage、
BANNED ではない — 各再入場経路を明記)。並行線 (parallel) 側は健全な候補が残らなかった — 全滅を正直に記録する。**

---

## 1. grounding facts 照合結果 (Task A)

| # | payload claim | 照合 |
|---|---|---|
| 1 | E12 P-10 ban scope = CME volume × spot price 限定 | ✅ 正 — `e12-volume-forward-prereg-2026-07-29.md` §7「cme volume × spot price のジョイント量」。**⚠️ MEMORY 側 (`project_e12_volume_forward_prereg_locked`) の「volume×価格ジョイント計算は全面禁止」は CME 限定句を落とした過大表現** — payload の方が一次ソースに忠実。E13 ban 継続 (E12 unsigned PASS 時のみ再入場) も §10 で確認 |
| 2 | rnb_usdjpy shadow 実在 + ny-cut 前例の reconciliation 要求 | ✅ 正 — カードは SHADOW data-collection / USD_JPY / BT データなし。catalog ny-cut エントリの ban_reason に 3 corpse 差分 + rnb reconciliation 要求が明記 |
| 3 | ny-cut: honest headroom 3-6x、direction が弱点、未 wave | ✅ 正 (catalog JSON 実文確認、+1h/+4h horizon での headroom fail) |
| 4 | trendline_sweep 12y 崩壊 (WR73-81→41-44%、p=0.88-1.0、gross +0.94p) + 06-25 memory の「斜め固有」は今や弱い | ✅ 正 — postmortem TL;DR-1/§1/訂正 a。tier-master 実確認: trendline_sweep は **PAIR_DEMOTED (EUR_GBP/EUR_USD/GBP_USD 全席)** = live-demoted、falsified family ではない |
| 5 | TV OANDA D1 は majors で 2014 以前から | ⚠️ **load-bearing 未検証** (W3-2 の massive_api と同型)。per-pair coverage assert を測定前必須とし、不通過 = data-blocked クローズ (事後緩和禁止) — payload 自身の宣言どおりだが、本検証時点で確認された事実ではないことを明記 |
| 6 | identity ban 4 系統 (i)-(iv) | (i)(ii)(iii) ✅ memory + decision 全文と一致。**(iv)「15m 連続足スキャン一般」は registered ban ではない** — postmortem §3.3 の経験的生存形状 (「15m 連続足スキャン系は全滅」) であり、identity-ban 表に載せるのは過大。strong prior として扱う (verdict への影響なし) |

**meta 監査**:
- **ledger 状態** ✅: 台帳 #1-#17 使用済み → 次 #18。並列 cap 3 / active non-locked 0 (wave-3 2/2 FAIL クローズ、E1/E7/E12/MoF/#11/#12 は locked/passive、weekend_gap は R1 stage-2 執行トラック) — 整合。
- **frozen protocol の RT 表** ✅: wave1-tv-explore-protocol-freeze の凍結値と 8 ペア全一致 (floor 1.30p 感度も postmortem §4b と一致)。
- **worktree parquet 部分版** ✅: 実 ls で確認 (worktree に 1d ほぼ不在、15m も部分)。**追加事実: main checkout にも AUD_JPY_1d parquet は不在** (AUD_USD/EUR_JPY/EUR_USD/GBP_USD/NZD_USD/USD_CAD/USD_CHF/USD_JPY のみ)。AUD_JPY のローカル cross-check は `AUD_JPY_1h_12y_audit.parquet` の D1 resample で代替すること。
- **survival_prior の overstatement (訂正要)**: 「htf_false_breakout×AUD_JPY is the only 2-stage-screen survivor」— ws3 §8.1 では **2 セルが PASS** (london_fix_reversal×EUR_USD も)。lfr は stage-2 で 9/9 負クローズ、htf_fb も stage-2 は **8/9 負で UNDERPOWERED** (+1.15 の 1 構成は p=0.594)。正確には「explore→OOS 2 段スクリーンを通過し**今も生きている唯一のセル (recheck registry、未収益化)**」。この prior が L-a に移転するのは **stage-1 型 (exit-free net-move/asymmetry) の estimand に対してのみ** — L-a の設計はまさにそれなので prior 引用自体は有効、ただし「EV 変換の証拠はゼロ」を pre-reg に明記すること。
- **orchestrator_position_on_capability_claim** ✅ 支持: 3 反証は N=10k-15k (H4) / 48k-59k (channel) / 6,456 イベント+6 ペア (sweep) の massive-N・Bonferroni 級であり「アナリスト力量」では説明不能。同時に「未検証の差分軸 (D1 レベル・非 swing 生成・低頻度イベント条件付け) は実在」も正 — weekend_gap arm B (D1 スケール・低頻度・price-only) の OOS PASS (stressed-net +9.04p) がこの差分空間の存在証明。

---

## 2. verdict サマリ

| 候補 | verdict | ban 照合 | 一言 |
|---|---|---|---|
| L-a htf_level_failed_break_d1w1 | **GO-WITH-CONDITIONS** (12 条件) | ADJACENT (差分成立) | 生存機構の直系一般化、set 中最良 |
| L-b round_number_major_level_behavior | **GO-WITH-CONDITIONS** (12 条件) | ADJACENT (差分成立) | 唯一の非 swing レベル生成、Osler 実注文データ根拠 |
| L-c anchored_vwap_deviation_reversion | **KILL (triage)** | ADJACENT (E2/E13 隣接) | 機構が FX spot に存在しないデータを要求 — proxy で退化 |
| L-d d1_regression_channel_reversion | **KILL (triage)** | **ADJACENT (BANNED ではない — §5 で scope 裁定)** | 差分は合法だが prior 最弱 + 死型既知 |
| L-e d1_diagonal_trendline_sweep | **KILL (triage)** | CLEAR (corpse 非該当) | 機構の唯一の支持が 12y で崩壊 + DoF 最大 |

---

## 3. [L-a] htf_level_failed_break_d1w1 — GO-WITH-CONDITIONS

### ban 照合: ADJACENT (差分節成立を確認)

- **corpse (i) H4 swing×touch ×15m**: 差分 3 本とも実文と整合 — (1) レベル生成 = 決定的 55d 極値 (swing pivot × touch-count ではない)、(2) hold = 1-10 D1 bars (15m ではない)、(3) D1 close 確定イベント (連続 bar スキャンではない)。h4 決定文の再発防止条項は「別の水準定義を試すなら方向性 IC を先に確認」を**恒常要求**としており、これは条件 11 で履行する。
- **corpse (iii) 水平 sweep&reclaim ×15m**: あちらは「wick 貫通→close 戻し」の intraday SL 狩り。本件は **D1 close でのブレイク→D1 close での失敗確認**で wick イベントではなく、horizon も日単位 — estimand 別。
- **corpse (ii)**: 非該当 (水平、チャネルではない)。

### prior 裁定

「medium-high (set 中最高)」は**条件付きで妥当**。htf_fb×AUD_JPY (1H SR false-break fade) は stage-1 (exit-free 非対称) の生き残りであり、L-a は同機構を 1-2 段上の TF に一般化した stage-1 型測定 — prior の移転先として正しい。ただし §1 のとおり **stage-2 EV 変換は 8/9 負 UNDERPOWERED** であり、「機構が方向を持つ」ことまでしか裏書きしない。postmortem 成功形状 3/3 (低頻度・レベルアンカー・長ホールド) も確認。

### power / headroom (Task C)

- 頻度 4-10 events/pair/年 は 55d Donchian close-break + ≤3d 失敗確認としてオーダー妥当。pooled explore 期待 N ≈ 256-640 — 検定力は足りる。**ただし payload の「pooled <40 で underpowered」床は緩すぎる** — weekend_gap §4(e) の Poisson 導出方式で床を再導出・凍結すること (条件 5)。
- headroom 名目 10-30x は D1 5d ホールドとして妥当なオーダー。**イベント条件付き MFE p50 の fwd-return 非接触実測が先** (W3-2 前例) — 条件 4。

### DoF 監査 (Task D) → LOCK-前 必須 12 条件

1. **定義 DoF 全凍結**: level = max(prior 55 D1 highs) / min(prior 55 D1 lows) (当該 bar 除外)、break = **D1 close** が level 超え、failure = ≤**3** D1 bars 以内の close 復帰、event bar = 復帰 bar、entry proxy = event bar close。55d / 3bar / dedup 10d の **grid 探索禁止** (単一宣言値)。**名称の「w1」は未テストと明記するか名称から落とす** — W1 レベル変種は「declared non-tested」であって scan 対象ではない。
2. **primary 1 本凍結**: pooled 8-pair・h=5d・fade 方向 net move (pips)、両サイド合算。per-pair / 他 horizon / サイド split は diagnostic (選択に使わない)。
3. **bootstrap 構造**: **calendar-week event-block** (同週クロスペアイベントの USD 共通因子相関をブロック化 — weekend_gap weekend-block + ppp 検証「USD 因子で実効独立 ~1-2」の同型対策)。5-10d horizon の forward 窓重複イベントの blocking 規則を凍結。実効独立 N の診断併記。
4. **headroom gate を forward-look 前に**: イベント条件付き MFE(5d) p50 ≥ 10× per-pair RT (凍結表 + floor 1.30p 感度) を **forward return への一切の look の前に**実測 (W3-2 条件 (1) の文言継承)。不通過ペアは**候補凍結時点で除外** — OOS 後の事後除外は禁止。
5. **N floor の Poisson 導出**: explore pooled 床 (≥150 目安) と OOS 床を発生率から導出して凍結、不足時は **UNDERPOWERED verdict** 経路 (PASS/FAIL にしない) を併設。payload の「<40」を置換。
6. **swap 会計**: OANDA 現行 snapshot の一律適用は**不可** (§7 Q4 裁定 — explore 窓 2014-2021 は低金利差 regime で snapshot 適用は系統誤差)。**e20_rates_ingest 残置パネル (BIS CBPOL 政策金利差、日次 ffill) をイベント日付で適用**する歴史 proxy + 凍結 broker markup、markup ±50% 感度。
7. **機械 kill rules**: 単一イベント/単一週の pooled effect 支配 ≤50% (SNB 型ガード) / explore 年次符号一致 ≥6/8 / LOYO / knife-edge 3 点 (55d±20%、確認窓 3→{2,4}、close-break→wick-break) を verdict 時必須で凍結。
8. **TV coverage assert**: per-pair D1 first bar ≤ 2014-01-01 を測定前 assert。不通過ペア = data-blocked (「取れたところまでで走る」への事後緩和は W3-2 横断警告どおり禁止)。土曜 bar 除外等 feed QA は wave-1 凍結事項を無変更継承。
9. **ローカル cross-check**: main checkout の 1d parquet (AUD_JPY のみ `AUD_JPY_1h_12y_audit.parquet` の D1 resample) でイベント数 + pooled 符号を照合、乖離時は測定停止して原因究明。worktree parquet は部分版につき使用禁止。
10. **台帳 #11 との関係宣言**: 別 family (cross-reference 必須)。#11 は LOCKED 一回限り再判定でありその grid/分母は不変。**htf_fb×AUD_JPY の shadow live データを L-a の explore/OOS に一切使用しない**。
11. **h4-memory IC-first 条項の履行**: explore = 測定のみとし、strategy 実装 (Pine strategy()/engine 登録) は explore gates 通過後に限る — これで「新レベル定義は方向性チェックを先に」の恒常条項を discharge する。
12. **接触規律**: explore verdict (§5.1 型追記) 後に OOS 単一接触。live パラメータ・shadow 構成変更ゼロ。PASS ≠ live (R1 全段 + user 承認は別途)。

---

## 4. [L-b] round_number_major_level_behavior — GO-WITH-CONDITIONS

### ban 照合: ADJACENT (3-corpse lineage — 差分成立を確認)

- ラウンドナンバーは水平レベルであり「ページのライン→エッジ」3/3 死亡系譜の警告 (catalog ny-cut ban_reason) が適用される。差分 3 本を確認: (1) **レベル生成が完全に外生** (swing/price-action 幾何を一切使わない — corpse (i)/(iii) は swing/直近極値)、(2) D1 イベント + multi-day hold (corpses は ×15m)、(3) 低頻度 fresh-approach 条件付け (連続スキャンではない)。set 中で corpse との構造距離が最も大きい。
- **ny-cut 前例との差分** ✅: expiry clock なし / D1 horizon / multi-day で headroom 算術が変わる (あちらは +1h/+4h で 3-6x fail)。ただし ny-cut の「direction is the weak part」の弱点は**継承リスク**であり、reversal 片側 primary 1 本に凍結することで多重化を防ぐ (条件 3)。
- **rnb_usdjpy との reconciliation**: 要求どおり成立可能 — あちらは live-forward shadow 収集 (歴史主張なし)、こちらは歴史測定のみ。条件 8 で拘束。
- **in-repo 未テスト確認** ✅: decisions/lessons/learning に round-number レベルの過去検証なし (grep 実施)。
- 補強: Osler (2003, J. Finance) は**実注文データ**での TP=at / SL=beyond クラスタリング — 本 set で唯一、機構の一次証拠が価格系列の外にある。ただし証拠は intraday であり D1 multi-day への外挿は untested (prior "medium" は妥当、むしろ上限)。

### power / headroom

頻度 6-15/pair/年 は妥当なオーダー (pooled explore 期待 ≈ 288-720)。headroom 名目 10-25x — **GBP_USD (RT 4.53p) は 3d MFE p50 ≥45.3p 要求で境界的** — per-pair headroom gate が正直に刈る設計で良い。

### DoF 監査 → LOCK-前 必須 12 条件

1. **level grid 凍結 per pair**: JPY クロス = 整数 00 (EUR_JPY/AUD_JPY 含む)、USD-quoted = 0.0100 grid。**50-levels は declared non-tested (variant scan 禁止) を維持**。
2. **touch / approach / 方向の定義凍結**: touch = D1 high ≥ L (下から接近) or low ≤ L (上から接近)、接近方向 = 直前 D1 close の側で決定。**同日複数 level 交差時の規則** (直前 close に最近接の 1 level のみ、1 pair 1 日 1 event) を凍結。
3. **primary 1 本凍結**: pooled 6-pair・h=3d・reversal 片側 (level から離れる方向)。breach-acceleration (Osler 予測 2) は**本 family で検定しない**と明記 (別 family 候補として台帳注記のみ)。
4. **bootstrap**: calendar-week event-block (L-a 条件 3 と同一設計)。
5. **headroom gate を forward-look 前に** (L-a 条件 4 と同一、per-pair 除外は凍結時のみ)。
6. **N floor Poisson 導出 + UNDERPOWERED 経路** (L-a 条件 5 と同一)。
7. **介入汚染の機械ガード**: `data/external/mof_interventions.csv` (在庫確認済み) で OOS イベントの介入週重複 share を診断出力し、**単一週支配 ≤50% ガードに介入週を含める** + LOYO (2022/2024 除外で符号維持)。explore 窓 2014-2021 が USD_JPY 介入ゼロであることの assert (payload 主張は正 — 直近の JPY 介入は 2011 以前)。
8. **rnb_usdjpy reconciliation 節**: 歴史測定のみ / live 収集トラックと重複なし / rnb shadow データ非使用 / PASS 時は rnb トラック設計への入力として扱う — を pre-reg に明記。
9. **swap 会計** (L-a 条件 6 と同一の歴史 proxy 方式)。
10. **TV coverage assert + feed QA** (L-a 条件 8 と同一)。
11. **L-a とのイベント重複診断**: 55d 極値の failed break がラウンドナンバー近傍で起きるケースの pair-week 重複 share を報告。>30% なら台帳に部分依存を注記 (BH 分母は変えないが「独立 2 家系」と誇張しない)。
12. **接触規律** (L-a 条件 12 と同一)。

---

## 5. [L-c] anchored_vwap_deviation_reversion — KILL (triage 却下、ban ではない)

- **ban 照合: ADJACENT** — E12 P-10 の**文言**は CME volume 限定で非該当 (payload の読みは正)。しかし E2 verdict「OHLCV/tick volume は弱 proxy」(scan round1 実文) と E13 棄却「E2 を覆す新証拠なし、E12 が上位互換、再入場 = E12 unsigned PASS 時のみ」(round2 実文 + e12 prereg §10) の**射程内に実質的に入る**: TV の FX volume = feed tick count であり、tick-volume 加重 AVWAP は「tick volume × 価格のジョイント構成量」そのもの。
- **kill 理由 (3 本)**:
  1. **機構がデータ的に成立しない**: institutional benchmark 機構は実約定 volume を要求するが FX spot に存在しない。tick 加重では AVWAP が anchored average price に退化し、estimand は「quarter アンカー平均からの 3ATR 乖離→回帰」= **slow D1 mean-reversion** — ppp FAIL (「方向は合うが弱い」IC +0.113 p=0.129) / quote-spread FAIL (−0.24σ p=0.32) / nominal-5y-band (ppp の弱い兄弟、catalog prior low) と同じ死型の再訪。orchestrator 自身が KILL 期待を明記しており、その読みは正しい。
  2. **power 最弱**: 2-4 events/pair/年 × 4 pairs → explore 64-128 / OOS 36-72、かつ quarter アンカーでカレンダークラスタ。低ボラ四半期はイベントゼロ。
  3. **E12 LOCK との規律衝突リスク**: 文言外とはいえ、E12 first look (2027-02-05) 前に volume×価格ジョイントを別経路で走らせるのは P-10 の趣旨 (volume モダリティの verdict を先に) を骨抜きにする。
- **再入場経路**: E12 unsigned primary PASS 後に、**実約定 volume (CME 先物) アンカーの AVWAP** として新 family / R1 でのみ。tick-volume 版の再提案は E2/E13 ban の実質的再着せ替えとして棄却対象。

---

## 6. [L-d] d1_regression_channel_reversion — KILL (triage 却下) + ban scope 裁定

### ban scope 裁定 (on-record、Task B の明示要求)

**裁定: TF/estimand-scoped であり definition-global ではない → BANNED ではなく ADJACENT。**根拠 (実文):
- `channel-edge-falsification-2026-06-25.md` の判定ヘッダは「**再試行禁止（この特徴量セット・チャネル定義では）**」と自己 scope している。測定は 15m bars / horizon 1h/3h/12h / 連続スキャン / 6 ペア N≈48-59k。
- 同決定の再発防止条項は「**別チャネル定義 (Donchian中心線・Keltner・別lookback) を試すなら実装前に IC ハーネスで方向性 IC を先に確認**」と、**別 lookback を明示的に許容される再挑戦形として列挙**している。memory 側の「回帰±2σ・swing平行 定義は null 確定・再試行禁止」は、この決定文の縮約であり、決定文の許容条項を消すものではない。
- したがって「60 D1-bar 回帰±2σ + 初回 close-outside イベント + multi-day hold」は falsified estimand (15m 連続スキャン × 1-12h) の**外**にあり、identity-BANNED ではない。再挑戦する場合は IC-first 条項 + 明示差分節が必須となる。

### それでも KILL (triage) — 理由

1. **prior が set 中最弱で、期待される死型が既知**: 同一幾何構造が 15m で meanIC −0.005〜−0.02 (閾値の 1/3 以下、★0/6 ペア) の**決定的 null**。D1 化の最近傍前例 (ppp / holiday / quote-spread) は 3/3 が「方向は合うが弱い」型で死亡。トレンドライン系の TF-lift 救済も 12y で崩壊した前歴 (365d→12y 反転)。
2. **estimand の独立性が低い**: 「60d 回帰から 2σ 外に D1 close」≈「60d トレンド対比の大幅な逸脱」であり、price_shock family (H1 shock reversion、live 稼働) および nominal-band 極値と条件が重なる — 新差分空間としての価値が L-a/L-b より明確に薄い。
3. **希少資源**: OOS 窓と pre-reg スロットは有限 (catalog 運用ルール)。power は足りる (explore 128-256 見込み — **power 不足は kill 理由ではない**と正直に記録) が、同じスロットで L-a/L-b の方が期待値が高い。
- **再入場経路**: なし (同構造)。並行線側の将来提案は「回帰±2σ/swing平行以外のチャネル定義 + IC-first + 明示差分節」の決定文条項に従うこと。**user 委任 (平行線を『ちゃんと調べる』) への正直な回答 = 平行線・チャネルの方向性エッジは 15m で massive-N null 確定済みであり、D1 版は最近傍死型 3/3 の空間 — 測定リソースを投じない判断がデータに忠実**。

---

## 7. [L-e] d1_diagonal_trendline_sweep — KILL (triage 却下、ban ではない)

- **ban 照合: CLEAR** — corpse (i)/(iii) は水平、(ii) は回帰/swing 平行チャネルであり、単一斜め TL sweep はどの corpse とも identity しない。trendline_sweep は live-demoted (tier-master: PAIR_DEMOTED ×3) であって falsified family ではない — payload の整理は正確。
- **kill 理由 (3 本)**:
  1. **機構の唯一の支持が崩壊済み**: 「斜め TL 固有の流動性狩り」(06-25 memory) の根拠は trendline_sweep の live WR80% だったが、12y 検証で WR41-44% / p=0.88-1.0 / gross +0.94p sub-friction に反転。payload 自身「mechanism's only support is now weak」と認めるとおり、これは**新差分空間の探索ではなく、死んだ戦略の TF 変え再訴訟**に近い。L-a と差分軸 (D1 化・multi-day・低頻度) が同一なので、その軸の検定は L-a が上位互換で担う。
  2. **DoF 面が set 中最大**: fractal 3/3 の確定タイミング (+3 bar) の因果性、直近 2 swing の選択、≥15d span、線の失効条件、slope 制約、Pine 実装の repaint — payload 自身「verifier may KILL on DoF grounds alone」。凍結可能ではあるが、凍結コスト・監査コストが最も高い候補に希少スロットを割く合理性がない。
  3. **希少資源** (L-d と同じスロット論)。
- **再入場経路**: L-a explore gates 通過 (= D1 レベルイベント modality に信号が存在する実証) 後に限り、**線構築の参照実装 + 全 DoF 凍結 + 敵対的再検証**を伴う新提案として可。L-a explore FAIL の場合は D1 diagonal 変種の再提案も不可 (同 modality の供給死)。

---

## 8. verifier_questions への回答 (Task E)

1. **Family/BH 構造**: **singles を直列 (m=1 × 2 wave) — wave-3 採択と同型**。wave-1 の実死因裁定 (並列 2 本の多重性コスト) と、OOS 窓が希少資源である運用ルールに従う。within-family は各 pre-reg の primary 1 本、cross-family は weekend_gap §9 の階層宣言どおり台帳スロット制 + 全 verdict 追記式記録で統制 (family 横断 p 補正はしない)。L-a = 台帳 #18、L-b = #19。両者のイベント重複診断 (L-b 条件 11) で部分依存を可視化する。
2. **L-a と台帳 #11 (htf_fb recheck) の関係**: **separate family + cross-reference**。#11 は「同一 grid・同一検定の 1 回限り再判定 (新探索自由度なし)」で LOCKED 済みであり、その Bonferroni 分母は事後変更不能かつすべきでない。L-a の PASS/FAIL は #11 の判定に影響しない旨を双方向に明記し、htf_fb shadow live データを L-a に流用しない (L-a 条件 10)。
3. **8-pair pooled primary の可否**: **可、ただし 3 条件付き** — (a) calendar-week event-block bootstrap (weekend_gap の weekend-block の D1 版。8 ペアは USD 共通因子で実効独立数が名目より遥かに小さい — ppp 検証の「実効独立 ~1-2」指摘の同型処理)、(b) ペア除外は候補凍結時のみ (weekend_gap の GBP 除外は explore 段階の凍結だった — OOS 後の除外は禁止)、(c) per-pair headroom gate 併走。ペア数削減は必須としないが、pooled N を検定力として過大解釈しない (実効 N 診断併記)。なお arm-B 前例は 3 ペアであり「8 ペアの直接前例」ではないことを pre-reg に正直に書くこと。
4. **swap netting のソース**: **OANDA 現行 financing snapshot の一律適用は不可**。explore 窓 (2014-2021) はゼロ金利差 regime、OOS 窓 (2022+) は大金利差 regime であり、snapshot 一律は explore/OOS 間に系統誤差を作る (USD_JPY 2023-24 は ~2p/日 = 5d で ~10p と material)。**採択案: e20_rates_ingest 残置パネル (BIS CBPOL 政策金利差、日次 ffill — in-repo 実在確認済み) をイベント日付で参照する歴史 proxy** + 凍結 broker markup、markup ±50% 感度。カバレッジ欠損ペアは保守側バウンド (proxy と snapshot の悪い方) で凍結。
5. **TV D1 単独計測の妥当性**: **可 — wave-1 前例 (TV = 測定カノン、統計はローカル post-processing) の直接踏襲であり、Live > TV > Python BT の序列 (feedback_tv_edge_discovery_loop) では TV はローカル BT より上位**。条件: (a) per-pair D1 coverage assert を測定前に (不通過 = data-blocked、事後緩和禁止)、(b) wave-1 の土曜 bar 除外・feed QA を無変更継承、(c) main checkout parquet での cross-check はイベント数 + pooled 符号の整合確認に限定 (AUD_JPY は 1h_12y resample で代替、worktree parquet 使用禁止)。

---

## 9. 実行順序 (Task F、採択)

1. **L-a を単独 wave で先行** (台帳 #18)。pre-reg DRAFT → 敵対的レビュー → LOCK → explore (TV per-event export) → gates → OOS 単一接触。条件 1-12 の解決を LOCK 前提とする。
2. **L-b は L-a の explore verdict 後に単独 wave** (台帳 #19)。準備作業 (level grid 定義、TV coverage assert、mof_interventions 重複下ごしらえ) は forward return への look に当たらないため L-a 走行中に開始可 (W3-2 fetch 前例)。
3. L-c / L-d / L-e は台帳に KILL + 再入場経路を記録 (pre_fomc / move_bondvol の triage KILL 様式)。
4. 枠整合: 現 active non-locked 0 → 本採択で最大 1-2 (cap 3 内)。E7 verdict (08-28) / E15/E7 refreeze (08-21 前 `--verify-only`) / weekend_gap stage-2 執行と資源競合なし。
5. **横断警告 (W3-2 と同文)**: TV D1 coverage assert 不通過はそのまま data-blocked クローズ — 「取れたところまでで走る」への事後緩和を禁止。

## 10. score honesty 監査

- L-a「medium-high」: **条件付き妥当** — stage-1 型 estimand への prior 移転として正しいが、htf_fb の stage-2 (EV 変換) は 8/9 負 UNDERPOWERED であり「機構は方向を持つ、が金になった実績はゼロ」を pre-reg に明記のこと。
- L-b「medium」: 妥当 (上限)。Osler 証拠は intraday — D1 multi-day への外挿は untested、McLean-Pontiff 減衰も正しく自己申告済み。
- L-c「low-medium」: **インフレ — 誠実には low**。機構が要求するデータ (実約定 volume) が FX spot に存在しない時点で「practitioner-popular」は prior に算入できない。
- L-d「weakest in set」/ L-e「HONESTLY DEGRADED」: 自己申告は誠実。orchestrator の「L-c は KILL 期待」「L-d は生存を主張しない」「L-e は DoF だけで KILL され得る」の 3 自己申告はいずれも本検証の結論と一致 — payload の正直さは wave-3 水準。
- 頻度・headroom 見積り: 全候補オーダー妥当 (L-c の 2-4/年のみ「thin」の自己申告どおり過小 power)。唯一の実質修正 = L-a の explore N 床「<40」→ Poisson 導出床へ置換 (条件 5)。

---

**総括**: 水平線側は「genuinely untested な差分空間 + 正直な機構 + 十分な power」を満たす 2 本 (L-a/L-b) が条件付きで生存。並行線側は 3 本とも評価したが、(回帰チャネル) 15m massive-N null の TF 変えで最近傍死型 3/3、(AVWAP) データ不在で機構退化、(斜め TL) 支持崩壊 + DoF 過大 — により全滅。これは検定回避ではなく、user 委任「ちゃんと調べる」への最もデータに忠実な回答である。charter の凍結解釈 (「健全な候補が残らなければ全滅と正直に記録」) に従い記録する。
