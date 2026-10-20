# 外部仮説スキャン第6次 — U4 (a)(b)(c) の「資本制約なし」再評価 + #29 step 1 承認 + 四半期モダリティ棚卸し (2026-10-20)

**位置づけ**: [[../syntheses/edge-development-pipeline-2026-07-18|edge パイプライン]] §4 月次 cadence の第6回 (registry `edge-supply-scan-monthly`、期日 2026-10-18 → 10-19 00:20Z TRIGGERED、実行 10-19〜20、2 日遅延)。
**前回**: [[external-hypothesis-scan-round5-2026-09-17]] (E29-E31 全棄却、WIP 会計訂正) / 臨時 [[adhoc-scan-29-step0-2026-09-22]] (#29 step 0)。
**四半期モダリティ棚卸し**: 本次に同乗 (§7)。
**実施方法**: 調査 6 面 (台帳・枠 / 有償データ / daily+ クロスセクション / 中銀テキスト #29 / cross-asset / 非 FX) を独立に読み、3 レンズ (ban・estimand・P-10 / 費用・feasibility・決裁 / 手続き・規則) の敵対的反証を通した。反証はいずれも「核は生存、細部を訂正」で、訂正は本文に反映済み (§8 に一覧)。

**live への影響: ゼロ。** live/tier/lot/Kelly/shadow 構成を一切変更しない。E1 skew×outcome / ECG gate×outcome / E12 volume×価格 / LOCK 中 shadow セルの outcome は一切計算していない。

**本スキャンの成果 (先出し)**:
1. **新規採用 (能動 explore LOCK) = 0 本 (3 周連続、第4〜6次)**。着手可能 family は 0 のまま。**#29 S1 step 1 census (診断枠、価格非接触、$0) を承認** — ただし診断枠は WIP 下限「着手可能 ≥1」に数えない (pipeline §3 / 台帳 #23 先例)。
2. 🔴 **KB の有償データ記述に事実誤り 2 点を発見** — E22 §9 の「真正 OTC 面 = Databento 等有償」は不正確 (Databento は CME **上場** options)。字義を満たす経路は CME DataMine 経由の **TFS-ICAP FX Options** (OTC indicative 面、2003-09〜、52 ペア) だが、**価格・個人の契約資格・tick→EOD 構築工程の 3 点が未確認**。「数百 $ 一回性」は一次情報ゼロで**未確認に格下げ**。
3. **U4 (b) daily+ クロスセクション (weekly-xs-reversal 等) は「DRAFT 起案可」ではなく research-only 🅿️ 予約に格下げ** — 価格/OHLCV 内部モダリティは第3次で閉鎖済み (daily carve-out の明示宣言が要る)、正 EV ホスト不在 (C4、帳簿外保有)、F2 教訓 (OOS PASS → live 変換未実証の計画的再生産)。「資本が先」で止まっていたのは live 変換の論拠のみで、研究は元から $0 だった ([[../analyses/supply-space-feasibility-2026-09-17|supply-space]] §2.3)。
4. **U4 (c) 非 FX は OANDA 制約下で空集合** — v20 API 口座は FX 68 ペアのみ、金・銀は CFD (MT4/MT5 別口座 = 対象外、user 決裁 09-24)。S1 クローズ。残余は「追加 FX ペアの shadow 蓄積」のみ (市場を変えない)。
5. **データ入手性 re-check で未処置の欠陥 1 件を継続確認**: MASSIVE 1h cache が 13 ペア全て 2026-05-15 終端のまま refresh ジョブ不在 (5 ヶ月)。15m→1h resample は bit-exact (EUR_JPY 2025-03、499/499 bar) で R3 構築可 (§5)。
6. **explore 枠の現在値は規則依存で 0/3〜2/3 の不定** — 3 読みを記録し、案 A (FAIL/park = 解放、explore-LOCK 中のみ占有、現在 0/3) を**作業上の読み**とする。正式採択は cadence と同じ user ack 項目 (§6)。

---

## 1. データ入手性 re-check (2026-10-19〜20 本番 GET / worktree 実読)

| 系統 | 状態 | 出所 |
|---|---|---|
| E1 positioning ingest (13 ペア) | ✅ 13/13 fresh (verified 09:27Z、stale 771s)、Myfxbook logged_in、auth_failure_streak 0。first look #1 = POSTPONE (coverage 88.56%/88.32% < 90%) → cutoff 11-05 / verdict 11-12。残 budget は算術で ≈2.4pp (≈1.6 営業日分の停止余地) | `/api/positioning/status` 2026-10-19T09:40Z、registry `e1-first-look-postponed-freeze-due` |
| E12 CME bars (7 契約) | ✅ 7/7 fresh (06:12Z)、rows 15,162〜15,166。判定 harness は未実装 (11-30 陳腐化 review が接点) | `/api/marketdata/status` 09:42Z |
| ECG #22 forward 窓 | 蓄積センサス (件数のみ): session_time_bias GBP_USD 122 / EUR_USD 99、xs_momentum GBP_USD 13 (08-07 で系列停止)、vol_momentum_scalp GBP_USD 0 → 11-06 は全セル N<150 の公算 = UNDERPOWERED 見込み (second look 2027-01-31) | `/api/demo/trades` 09:43Z、outcome 非計算 |
| MASSIVE 1h cache | 🔴 13 ペア全て end = 2026-05-15T13:00Z (3 ペア 14:00Z)、refresh workflow 不在 (`.github/workflows` に massive 参照 0、repo secret に MASSIVE_API_KEY 無し)。ws3-round4 の FX 脚到達経路なし (§5) | `data/cache/massive/*_1h.audit.json`、`gh secret list` |
| ZN 脚 (ws3-round4) | ✅ 2026-10-16T21Z まで延伸 (15,238 行)、evaluator strict `>` で TRIGGERED は 11-16 以降 | `data/cache/yield/ZN_F_1h.parquet`、registry `ws3-round4-eur-divergence-conditional` |
| mof-statements daily | ✅ 09-25〜10-17 で 13 commit (第5次修復の運用継続) | git log |
| OANDA 口座銘柄 | FX 68 ペア (公式スプレッド頁「取引通貨ペア 68通貨ペア」)、貴金属なし。決定的確認 = 既存 G0 ツール出力を PAIRS フィルタなしで 1 回保存 (次アクション) | OANDA JP 公式、`raw/bt-results/cc-g0-rt/2026-08-10.json` |

## 2. 供給ライン会計 (WIP、2026-10-20 現在)

| 区分 | 本数 | 内訳 |
|---|---|---|
| 着手可能 (能動 explore family) | **0** | — (第4次〜第6次で新規採用 0、3 周連続 (第4〜6次)) |
| 診断枠 (供給ライン非算入、F1 分子分母外、explore 枠非消費) | 1 | #29 step 1 census (本次承認、§3-(i)) |
| 時限ロック | 3 | E1 (verdict 11-12、元 10-15) / ECG #22 (11-06) / E12 (2027-02-05) |
| 条件付き | 2 | MoF #4 reverdict (11-14、Q3 開示待ち) / ws3-round4 EUR divergence (ZN ≥11-16 ∧ FX 脚未到達) |
| park | 2 | E23 #25 (UNDERPOWERED、Gate B N 40) / family B |
| research-only 予約 (本次新設、枠非消費) | 3 | idx 19 guidance-shock / catalog[55] weekly-xs-reversal / catalog[70] tail-day-aftermath (§4-(b)、§5-(b)) |

**WIP 下限「着手可能 ≥1」は本次後も未充足**。第5次の訂正どおり、診断枠を能動ラインに数えない (adhoc-scan-29 §6「census を着手可能に数えると承認範囲外の作業を能動ラインとして執行しうる」)。**臨時スキャンの発動規則は pipeline §3 / registry `edge-supply-scan-monthly` の現行どおり維持する** (着手可能 0 なら期日を待たず R3 臨時スキャン) — 本文書はこの規則を変更しない。常時成立による再演 (adhoc-scan-29 と同型) の抑制は、§7 の cadence 決裁に「イベント駆動化 + meta-audit R5 (能動枠 0 継続の機械トリガ) の registry 起票」を提案として載せるに留め、採択・実装されるまでは現行トリガが有効。

## 3. 裁定 7 件

| # | 裁定 | 結論 | Rule | user |
|---|---|---|---|---|
| (i) | #29 S1 step 1 census の実行可否 | **承認**。範囲 = ABGH-2019 辞書の逐語転記モジュール (WP 381 Appendix 出典、sha256 pin、語彙編集を test で封鎖) + 価格非接触ペア列挙器 (`load_corpus()`→`census()` 生存 CB fed/ecb/boe、staleness >120d・Fed/ECB 同日 void) + 出力 = 適格連続同一 CB ペアの \|ΔNH\|>0 割合 (primary)。閾値・ホライズン・ペア写像の探索禁止。**WCB pooled は optional secondary** (user が gated 同意 + E23 §0-4 解釈を確認した場合のみ)、primary 単独で R3・$0 完結。クローズ条件は step 0 §7-3 文言不改変、参照値に「監査後 ABG-2012 40/228 = 17.5% (生存 3 CB、pass-1 10-01)」を併記 (旧 56/323 併記)。Gate A 引用は「EUR_USD/GBP_USD 2/2 通過、USD_JPY は判定外 (E23 §12.2)」 | R3 | ABGH-2019 再利用根拠 = Riksbank open-data 条件 (出所・日付表記、法 2022:818 = EU 指令 2019/1024) の読みを採用してよいか — **user の明示承認 (#29-L) が辞書転記の gate**。無回答 = 転記しない (法的判断は user 専権、adhoc-scan-29 §4.2「再利用許諾の根拠確認前にモジュールを作らない」)。census は辞書なしでは着手できないため、承認までは step 1 は「承認済み・着手待ち」 |
| (ii) | #29 台帳登録 | **登録** (step 1 承認と同時)。形式 = #23 型「S1 intake (診断枠、供給ライン非算入、F1 分子分母外、m 非加算、explore 枠非消費)」。dense PASS (>50% 厳密、τ=0) 時のみ新 pre-reg DRAFT (R1) へ進み、explore 枠 1 消費の裁定を別途行う | R3 | — |
| (iii) | explore 枠の現在値と解放規則 | 3 読み (案 A 0/3 / 案 B 1/3 / 案 C 2/3) を §6 に記録。**作業上の読み = 案 A** (09-10 E23 LOCK 時の会計「現在 0/3」が #26 FAIL を解放済みと数えた先例と整合)。規則本文は台帳の凍結節に挿入せず「第6次 追補」節に置く。正式採択 (解放規則 + verdict 行の「枠 x/3 → y/3」書式要件) は cadence と同じ user ack + PR レビュー。実務上どの読みでも空き ≥1 で、次の凍結 (dense PASS → R1 DRAFT) までに確定すれば足りる | R3 (記録) / user ack (採択) | 案 A の採択 (一言) |
| (iv) | Picault–Renault (2017) 再取得 | **不可 (C1 到達不能、09-22 / 10-19 の 2 回連続) でクローズ**。以後の月次スキャンで保留を持ち越さない。例外 = user がブラウザで SSRN 2980777 を手動取得し辞書が全掲と確認できた場合のみ ECB 単独 secondary として census に追記 | R3 | 手動取得するか (任意、不要なら不可クローズ確定) |
| (v) | U4 (a)(b)(c) の「資本制約なし」再上程 | §4 に詳細。(a-1) = DRAFT 骨子 + user 決裁 4 件 / (a-2) CLS = user 法人照会のみ / (a-3) = 2027-02 保留維持 / (b) = research-only 予約に格下げ / (c) = OANDA 制約下クローズ、残余 shadow ペア拡張は RT 実測 (R3) まで | R1 (起案は user 決裁後) | U4-1〜U4-6 (§4) |
| (vi) | cross-asset 生存 2 本 + overlay R3 ablation | §5。ws3-round4 = pre-reg DRAFT 起草可 (データ非接触、LOCK は両脚 TRIGGERED 後に user 通知) + R3 infra (15m→1h resample、条件付き) / idx 19 = research-only 予約 (#30) / overlay readout = P-10 除外 assert を先に固定 (LOCK 中 shadow セルの outcome を層別で計算しない) | R3 / R1 | repo secret `MASSIVE_API_KEY` の登録 (1 回) |
| (vii) | 四半期モダリティ棚卸し + cadence | §7。巻き戻し 0 / text に FAIL 1 (#27) + park 1 (#25) / OOS 確定 PASS = weekend_gap 1 本 (live N=0)。cadence 月次→四半期は **user 決裁** (三択)、R5 機械トリガ起票を前提条件に | user 決裁 | 月次維持 / 四半期+イベント駆動 / 折衷 の三択 |

## 4. U4 (a)(b)(c) — 「資本は必要時に追加 / OANDA 固定」の下での再評価

### 4.1 (a) 有償データ

**(a-1) FX オプション面 (RR25Δ / BF25Δ) 新 vol family**
- **字義訂正 (R3、KB 更新)**: E22 §9 復活経路の「真正 OTC 面 = Databento 等有償」は不正確。Databento GLBX は CME **上場** options on futures (2010〜) で OTC ではない。字義を満たす経路 = **CME DataMine 経由 TFS-ICAP FX Options** (OTC ブローカー indicative 面: ATM straddle + 10/25Δ RR/BF、ON〜1Y、52 ペア (EUR/USD・USD/JPY・GBP/USD 等)、**2003-09〜**)。KB 既存記述「DataMine = 取引所上場分のみ」(round4 §4 / supply-space §1.2) は訂正対象。E22 §9 本文は凍結のため不改変、supply-space §1.2 に訂正を追記。
- **ただし TFS-ICAP は 3 点未確認**: (1) **価格** — DataMine 製品別価格は一次情報で取得不能 (cmegroup.com / datamine は非ブラウザに 403 / TLS 拒否、FAQ は「Pricing varies based upon data type and duration」のみ)。ファイルは**ティック級 indicative 気配の日次ファイル** (`TFSICAP_FXOptions_tick_yyyymmdd.csv`、~2MB/日) で 2014–2026 なら ~6–9GB 級 → 「数百 $ 一回性」で explore 窓 12 年が買える保証はない。(2) **個人購買の契約資格・第三者データのライセンス** — wiki に記載なし。(3) **tick→EOD スナップショット構築** (時刻・stale 上限) を自前で凍結する工程が要る。
- **Databento 上場経路**: Standard $199/月 / Plus $1,750/月 / Unlimited $4,500/月 (年契約)、新規 $125 クレジット (6 ヶ月失効)、historical 「$0.50/GB〜」は全 schema の最安値で statistics 単価ではない。StatType Volatility=14 / Delta=15 の GLBX 配信は未確認 (無ければ Black-76 で settlement premium から surface 構築 = 工数大)。字義不充足のため選ぶなら **E22 §9 と手順書 §8 (vendor を「CME DataMine」と固定) の 2 文書改定が user 決裁**。
- **差分節 (必須 8 項目)**: ① E22 クローズ範囲 (通貨 VRP: IV−RV 差分・レベル・比率 × G10 × 日次〜月次 + 無料 proxy) の字義外であること ② E24 ban (3 ヶ月超 horizon) ③ E25 ban (価格由来 synthetic RR/BF) ④ round2 E10 所見「RR は防御ゲートで方向エッジではない、**単独供給ラインにならず E9 採択時の secondary のみ**」を覆す理由 (ΔRR 時系列 IC を primary とする新 estimand、secondary ホスト E9/E22 の消滅) ⑤ multi-week hold の swap 支配 (E22 / family C) ⑥ E14 は options OI のみ・先物 volume 不接触 (P-10) ⑦ E1 `skew` との名称衝突回避 (`rr25` 命名) ⑧ **#7 vix_carry_unwind (FAIL knife-edge、「再挑戦は新データ必須」ban) と同一機構文献 (Brunnermeier 2009) であることの明示差分**。
- **起案条件**: 手順書 [[../decisions/e1-first-look-runbook-2026-09-22|e1-first-look-runbook]] §8 = E1 verdict ∈ {UNDERPOWERED, REJECT, REJECT-F} ∧ U1 継続 ∧ 一回性 probe ∧ 新 family pre-reg とセット。E1 は POSTPONE (verdict 11-12) で**第 1 項不成立**。11-12 の分岐は PASS / 非 PASS 3 種 / **DEFERRED (2 回目の品質 gate 不達)** の 5 つで、DEFERRED は §8 の集合に含まれない。
- **user 決裁 (4 件)**: **U4-1** (A) §8 どおり 11-12 を待つ [無回答既定] / (B) decouple = §8 の E1 条項を外し「U1 継続 ∧ 一回性 probe (上限 U4-2) ∧ pre-reg + 敵対的検証とセット ∧ explore 枠に空き」へ改定 — Claude 推奨 (B)、根拠は E1 と供給圧の独立性のみ (確率の数字は添えない)。**U4-2** probe 上限額 (円、1 数字)。**U4-3** vendor = TFS-ICAP (字義充足、価格未取得) か Databento 上場 (字義不充足 → U4-6) — D4 (資本上限、11-30) の後、または「D4 < ¥1M なら一回性のみ / ≥¥1M なら月額型も候補」の条件付き。**U4-6** Databento 選択時に E22 §9 + 手順書 §8 の字義改定可否。付随: アカウント作成・SSO・決済は user 操作 (Claude は行わない)。
- 購買は「family 起案 + 敵対的検証 GO-WITH-CONDITIONS」とセットでのみ (単体購買 = 読み手のいない write の再生産)。DRAFT 上で可能な敵対的検証項目 (差分節・P-10・estimand) を購買前に先行する。

**(a-2) CLS FX Outstanding**: 2021-09-02 開始の日次 EOD (forward/swap 残高)、価格・契約資格は非公開、問い合わせは Business email + Organization 必須 (B2B)。個人口座主の資格は一次情報で確認不能 → **照会は user 操作でのみ可、(a-1) の後、U2 決裁後まで起案しない**。研究価値 (母集団独立性) は記録として保存。

**(a-3) Databento CME 先物 (E12 歴史 / E13)**: **2027-02 まで保留維持** (E12 LOCK §6/§8 前倒し禁止)。(a-1) で Databento を使う場合もクレジット消費に E12 unlock を含めない。

### 4.2 (b) daily+ クロスセクション — research-only 予約に格下げ

- 対象 = catalog[55] weekly-xs-reversal (7 USD ペア、週次 Fama-MacBeth IC + skip-1-day) / catalog[70] tail-day-aftermath-continuation / idx 19 guidance-shock-yield-proxy。いずれも data_status in-repo / public-fetch で**研究は元から $0**。packet U4 表「資本が先」が止めていたのは live 変換 (最小ロット粒度) であって起案ではない (supply-space §2.3 L53 は「$0 で可能だが、weekend_gap F2 教訓の計画的再生産」と反対論まで既に書いている)。
- **DRAFT 起案に進めない理由 (反証で確定)**: (α) 価格/OHLCV 内部モダリティは第3次 §3 棚卸しで「3 周 FAIL + Mesfin 2026 → 閉鎖」、E28 / E31 は同理由で C2 棄却 — daily carve-out を起案するなら「base rate 4% は intraday 空間の測定値」を根拠に**閉鎖モダリティからの carve-out 宣言**が差分節に要る。(β) 帳簿外保有 (週次 / D1–5d、swing DISABLED、MAX_HOLD_SEC) で**正 EV ホスト不在 (C4)** — idx 19 を research-only にしたのと同じ理由を [55]/[70] にも適用する。(γ) F2 教訓。(δ) 入力定義が禁止データ — catalog の data 欄は 1d parquet 前提だが、E22 §7 L30 は `EUR_USD_1d_2014_2026.parquet` を使用禁止 (週末行 714)、cc-mr §2 は固定 UTC 境界禁止。使うなら 15m 凍結複製 (実体コピー + sha256・行数 manifest) から NY17:00 境界で週次/D1 close を再構築する 1 本のみ。
- **[70] の ban 列は CLEAR → ADJACENT-CAUTION**: #18 level_failed_break_d1 (D1 極値 → multi-day 継続、p≈0.30 n.s.、事後符号反転主張禁止) と #15 holiday レグ c (D1-D2 継続 −7.61p) に隣接。
- **昇格条件** (idx 19 と同一): (α) daily+ 執行レーン (週次/D1 hold、swing 再有効化 or 新 lane) の pre-reg が成立、または (β) 信頼できる net+ live セル ≥1 (E29 C4 解除)。**user 上程の実体は「daily+ 執行レーンの pre-reg 起案可否」**であり「(55) DRAFT 承認」ではない。U2 (資本上限) と連動。
- 台帳登録: #30 idx 19 / #31 [55] / #32 [70] を 🅿️ 予約行 (#20 形式、枠非消費、測定非起動) で追加。[55] と [70] は同一モダリティのため、起動時も同時 LOCK しない (pipeline §3 モダリティ分散)。

### 4.3 (c) 非 FX — OANDA 制約下でクローズ

- OANDA JP の v20 API 口座 (NY サーバー / fxTrade / プロコース) で取引できるのは **FX 68 ペアのみ**。金 (XAUUSD)・銀 (XAGUSD) は商品 CFD = **MT4/MT5 の別口座** (2026-05-12 実測: v20 REST は CFD を 400 で返す) → user 決裁 09-24「別口座は提案しない」により対象外。supply-space §2.2 の (c-1) equity index / (c-2) 個別株 / (c-3) crypto は全て OANDA 外 = 不成立。§2.4「母集団が変わる」利点も消える。
- **残余 = 追加 FX ペア (68−13=55、取引制限中ペアの除外要確認) の shadow 蓄積**。これは市場を変えない (base rate 4% prior 不変、クロスの RT 3.70–3.90p は majors より悪い、ZAR_JPY 等 EM は intraday 不成立、TRY 系は証拠金 25%)。起案するなら順序固定: ① 既存 G0 ツール出力を PAIRS フィルタなしで保存し instrument 全集合 (XAU/XAG 不在・displayPrecision・marginRate・取引制限) を KB 凍結 → ② G0 型 RT 実測 (read-only、stressed_RT = p75(spread)+1.0p ≤ 5.0p で PASS) → ③ PASS ペアのみ MASSIVE backfill + friction 表追記 → ④ MODE_CONFIG `shadow_only=True` 追加は rnb 前例の付帯条件 (forward pre-reg first look + R2 auto-demote gate 読み手 + `_UNIVERSAL_SENTINEL` 非追加 + test pin + KB 同 commit) + **Render disk/engine tick 容量の実測** (08-21 disk 満杯の再発防止) + user 一言承認。①〜③ は R3 単独実行可。live 化は常に Rule 1。
- **KB 訂正候補**: `friction-analysis.md` XAU 行 / xau-stop-rationale に「OANDA JP fxTrade に XAU/USD は無く、数値は demo 推計・OANDA 約定 0」を注記。MODE_CONFIG の XAU_USD 2 モード (auto_start=False) は死に銘柄 → 除去は code PR 別建て。

## 5. cross-asset 生存 2 本 + overlay

- **(a) ws3-round4 EUR divergence**: pre-reg DRAFT 起草可 (データ非接触; m=2 セル事前登録 / 新 OOS 窓 2026-05-16〜11-15 固定 / EUR_USD 6 ヶ月窓 N≈19<30 の UNDERPOWERED 分岐事前固定 / §2c L64 訂正 / gap 処置)。LOCK は ZN ∧ FX 両脚 TRIGGERED 後に user 通知。**FX 脚の到達経路 (R3 infra、条件付き)**: 15m→1h resample (EUR_JPY 2025-03 で vendor 1h と O/H/L/C/V 完全一致、vwap 1e-6) + 欠落 (EUR_JPY fresh 窓 ≈593 本 ≈6d04h) は OANDA mid 補填複製 + 週次 workflow。**条件**: (i) commit は 1h resample のみ (15m バイナリ 9.1MB/6.8MB を毎週再 commit しない)、(ii) commit 先は render buildFilter ignoredPaths 内の専用 dir (例 `data/cache/ws3_round4/`、harness 側 path を引数化) — `data/cache/massive` は意図的に ignoredPaths 外で**週次 commit ごとに本番 deploy が走る** (reassessment は ZN commit を夜間 deploy 源として既に列挙)、(iii) merge_never_shorten (keep="first") 経路のみ許可し `bt_data_cache refresh` (keep="last" = 消費済 OOS 窓を上書き) を test pin で禁止、(iv) registry 兄弟 entry で両脚化。user 作業 = repo secret `MASSIVE_API_KEY` の登録 (1 回、値は Claude が扱わない)。初回 scheduled run の green を実ログで確認するまで「修復完了」と言わない。費用 = GH Actions $0 (public repo)、Massive 増分 $0 は「既存 key の範囲なら」の条件付き。
- **(b) catalog idx 19 guidance-shock-yield-proxy**: ban 非該当 (E7 §13 carve-out / E20 ban 文言と非同型) だが D1–D20 帳簿外 + C4 + U2 未決裁 → **research-only 🅿️ 予約 (#30)**。再入条件 = §4.2 と同一。差分節 (E20 Q2 hollow / fold3、E7 §13、E23 §6、family C、BOE 2y 不在 → 5y ZC 代用、BOE 声明 2015-09 開始) を台帳行に置く。
- **(c) app.py cross-asset overlay の R3 ablation readout**: shadow 行に届くチャネルは 5 本 (scalp 閾値前乗算 ×1.15/×0.50/×0.80 / daytrade ×1.15/×0.55/×0.80 = 符号不変で emission 非影響 / dual-scenario `_fund_total` boost / hourly fund_sc×0.3 → THRESHOLD)。10-09 synthesis §5 の 2 点を訂正 (compute_signal の係数は shadow 行に非該当 / scalp は ×0.50)。readout は層 1+2 (record-only) で起案可だが、**層 1 (iii)「layer1_dir 層別の shadow net EV/WR/Wilson」は P-10 抵触** — LOCK 中 shadow セル (rnb_support_bounce×USD_JPY×BUY / sr_anti_hunt_bounce×EUR_JPY×BUY / 同 ×USD_JPY×BUY / ECG forward 窓の 4 cells) の outcome を層内で計算することになる。**観測前に registry の active LOCK を機械列挙して除外する assert を固定するか、層 1 を layer1_dir 分布・件数・fetch 失敗率のみ (outcome 非接触) に縮める**。層 3 (reasons marker) は live 共有コードのため別 PR・別裁定。

## 6. explore 枠 (並列上限 3) — 追補 (正式採択は user ack)

**消費・解放の台帳 (原文由来)**: 07-24 wave-0 #1/#2 = 2 (同日 verdict) → 07-28 wave-1 #6/#7 = 2/3 → #13 1/3 → 08-05 #21 FAIL「解放 → 0/3」(明示) → 08-17 #24 E22 1/3 → 同日 FAIL「解放 → 0/3」(明示) → 08-19 #26 family C 1/3 → 同日 FAIL (解放文言なし) → 09-10 #25 E23 LOCK「1/3 消費 (現在 0/3)」(= #26 を解放済みと計上) → 09-15 #25 park (解放文言なし) → 09-18 #27 family A 凍結「1 消費」→ 同日 FAIL (解放文言なし)。LOCKED 受動 (MoF 等) は非占有 (wave1-tv L6)。ws3-round4 LOCK は pre-reg スロットを使うが台帳に行がない (会計に入らない理由を次回明記)。

| 読み | 規則 | 現在値 |
|---|---|---|
| **案 A (作業上の読み)** | FAIL = 即解放 / park = 解放 / explore-LOCK 中のみ占有 | **0/3** |
| 案 B | park は占有 (サンセット条項、例 90 日) | 1/3 |
| 案 C | 明示解放行がなければ占有 | 2/3 |

いずれの読みでも空き ≥1。本次は LOCK を起案しないため実務影響なし。**正式採択 (案 A + verdict 行に「枠 x/3 → y/3」を必ず書く書式要件) は user ack 項目 (§9) とし、台帳の凍結節 (運用ルール) には挿入しない** — 台帳末尾の「第6次 追補」節に置く。

## 7. 四半期モダリティ棚卸し + cadence (裁定 vii)

| モダリティ | 第3次 (08-14) 以降の verdict | 前提の巻き戻し |
|---|---|---|
| 価格/OHLCV 内部 | #28 range_fade FAIL (09-14)、E28/E31 棄却 (閉鎖済み理由) | なし (閉鎖維持) |
| vol | #24 E22 FAIL (08-17)、(a-1) は未起案 | なし |
| event | E7 phase-1 FAIL、#15/#13 は維持 | なし |
| positioning | E1 LOCK (POSTPONE → 11-12) | なし |
| flow | E30 CLS = C1 (有償・B2B) | なし |
| text | **新規 FAIL 1 (#27 family A、J=0.2978 p=0.1074、検出力 caveat) + park 1 (#25 E23 UNDERPOWERED)** = 「測定可能性の未達」であり falsified ではない | なし |
| cross-asset | round-4 条件付き (ZN ≥11-16)、10-09 クエリで素直な 4 構成は全て既 FAIL/BAN | なし |
| cross-sectional (daily+) | 未起案 (research-only 予約へ) | なし |
| OOS 確定 PASS | weekend_gap 1 本 (live N=0、F2 12-31) | — |

**cadence (user 決裁、三択)**: 月次維持 / 四半期 + イベント駆動 (臨時スキャンの発動を「新規 E 候補 / 入手性変化 / lock verdict 到達」のイベントに限定し、常時成立の再演を R5 機械トリガで代替する提案を含む — 採択まで現行 WIP トリガは有効) / 折衷 (文献四半期・運用月次)。賛成材料 = 第4〜6次で新規採用 0 が 3 周連続、棄却理由が C1/C2/C4 の 3 分類に収束。反対材料 = WIP 下限が現に未充足で臨時トリガが常時成立し四半期化しても削減にならない / 月次 §1 の入手性 re-check が 3 周連続 (第4〜6次)で実欠陥を検出 (ZN cache / rate-anchor / mof-statements / MASSIVE 1h) / R5 機械トリガが未実装。**どの選択でも R5 (能動枠 0 が X 日継続の機械トリガ) の registry 起票 (R3) を前提条件にする**。

## 8. 反証記録 (3 レンズ、全て「核は生存・細部訂正」)

| レンズ | 崩れた点 → 訂正 (本文反映済み) |
|---|---|
| ban・estimand・P-10 | [55]/[70] は閉鎖モダリティからの daily carve-out 宣言と C4 を欠く → research-only 予約へ格下げ / [70] ban CLEAR → ADJACENT-CAUTION (#18, #15c) / 「元から $0」は supply-space §2.3 の転記で F2 反対論を併記 / 1d parquet 代替案は E22 L30 違反で削除 / overlay 層 1 (iii) は LOCK 中 shadow セルの outcome 計算 = P-10 抵触 → 除外 assert 必須 / 週次 workflow は deploy 副作用・15m 再 commit・keep="last" 上書きを費用に計上 |
| 費用・feasibility・決裁 | TFS-ICAP は日次 EOD ではなくティック級日次ファイル (6–9GB 級) で価格・契約資格・EOD 構築が未確認 / Databento 「$0.50/GB〜」は statistics 単価ではない / E1 分岐に DEFERRED を数え落とし、4% は base rate の流用 → 推奨 (B) の論拠から確率を外す / 手順書 §8 は vendor を CME DataMine と固定 (Databento なら 2 文書改定) / 差分節に #7 vix_carry_unwind と E10「単独供給ラインにならず」を追加 / U4-3 は D4 の後 / (c): list_instruments は G0 ツールで実行済み (XAU 不在の決定的確認のみ未了)、取引制限中ペアの除外確認、Render 書込み容量を費用欄に |
| 手続き・規則 | #29 診断枠を「着手可能 1」に数える自己矛盾 → WIP 0 のまま / 解放規則を台帳凍結節に挿入する提案 → 追補節 + user ack / 前日規則の不適用 → registry deadline = 意図日 −1 (11-18 → 11-17、census gate 11-08 → 11-07) / §7-3 文言は不改変で 40/228 併記のみ / Gate A 引用は 2/2 (USD_JPY 判定外) / WCB は optional secondary / pipeline §3 C5 追記の PR は pr_review_gate 経由 |

## 9. user 決裁項目 (本次で新設、11-30 のパケット返答と同じ機会で可)

| id | 問い | 選択肢 | 無回答既定 |
|---|---|---|---|
| U4-1 | (a-1) 起案条件を E1 verdict (11-12) まで待つか decouple するか | (A) 待つ / (B) decouple (推奨) | (A) |
| U4-2 | 一回性 probe の上限額 | 円 1 数字 | 起案なし |
| U4-3 | vendor | TFS-ICAP (字義充足、価格未取得) / Databento 上場 (字義不充足、U4-6 連動) | D4 後に再上程 |
| U4-6 | Databento 選択時の E22 §9 + 手順書 §8 字義改定 | 可 / 不可 | 不可 |
| U4-(c) | 残余 shadow ペア拡張 | RT 実測 (R3) まで進める / 起案しない | RT 実測のみ |
| #29-L | ABGH-2019 再利用根拠 (Riksbank open-data 条件) の読み — **辞書転記の gate** | 採用 (転記開始) / 異論 | **転記しない (step 1 は承認待ちで保留、census gate 11-07 は催促のみ)** |
| (iv) | Picault–Renault SSRN 手動取得 | する / しない | しない (不可クローズ) |
| (iii) | explore 枠規則 案 A の正式採択 | 採択 / 保留 | 保留 (作業上の読みのまま) |
| (vii) | cadence | 月次 / 四半期+イベント / 折衷 | 月次維持 |

## 10. 次アクション (Claude、執行は本 PR 外)

1. **registry (別 PR、デプロイを伴うため open live trade 0 の窓でバッチ)**: `edge-supply-scan-monthly` deadline 2026-10-18 → **2026-11-17** (意図実行日 11-18 の前日、message に第6次実績を追記) / 新規 `adhoc-scan-29-step1-census-gate` (deadline **2026-11-07**、意図日 11-08) / R5 機械トリガの起票は cadence 決裁の前提として同 PR で検討。
2. **#29 step 1 census (R3、別 PR、#29-L の user 明示承認後)**: ABGH-2019 辞書転記モジュール (WP 381 Appendix、sha256 pin) + 価格非接触ペア列挙器 + 出力 (件数・割合のみ)。参照値 40/228 併記。承認前に着手できるのは列挙器の骨格 (辞書非依存部分) と転記 PR の雛形まで。
3. **(a-1) DRAFT**: 差分節 8 項目 + P-10 節 + 購買前に可能な敵対的検証を DRAFT 上で先行 (購買は U4-1/2/3 後)。
4. **ws3-round4 DRAFT + R3 infra 条件付き起案** (§5-(a))。
5. **(c) 残余**: G0 ツール出力の instrument 全集合凍結 → RT 実測 (read-only)。
6. **KB 訂正 (docs)**: supply-space §1.2 (a-1) 訂正 + §2 (c) 取り消し線 (本 PR) / friction-analysis XAU 注記 / 10-09 synthesis §5 訂正。
7. **E1 11-05 再凍結の防衛** (0 時台 deploy 回避、deploy 後 verified 前進確認) は autopilot 継続項目。

## 関連
- [[external-hypothesis-scan-round5-2026-09-17]] / [[adhoc-scan-29-step0-2026-09-22]] / [[../syntheses/hypothesis-catalog-2026-07-24]] (台帳: #29 登録、#30–#32 予約、第6次 追補)
- [[../analyses/supply-space-feasibility-2026-09-17]] (§1.2 訂正、§2 (c) クローズ) / [[../decisions/user-decision-capital-not-binding-edge-first-2026-09-24]] / [[../decisions/integrated-decision-packet-d1-d12-2026-09-22]] (U4 行)
- [[../decisions/e22-vrp-explore-prereg-2026-08-17]] §9 (凍結、字義は本次で訂正を追記のみ) / [[../decisions/e1-first-look-runbook-2026-09-22]] §8
- [[../analyses/path-to-win-reassessment-2026-09-22]] §9 (未検証項目の消化: #8 MASSIVE 1h、#9 explore 枠規則)
