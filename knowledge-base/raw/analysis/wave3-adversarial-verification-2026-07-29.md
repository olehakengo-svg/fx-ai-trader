# wave-3 候補 敵対的検証 verdict (2026-07-29)

**検証者**: 独立 subagent (payload はファイル渡し: `wave3-candidates-2026-07-29.json`)。
一次ソース 8 系統精読照合。**生存 = W3-1 + W3-2 (いずれも GO-WITH-CONDITIONS)、W3-3 は登録
アクション (スロット外)、rejected 5/5 支持・誤棄却なし。**

## grounding facts 照合結果

- **cot_panel** ✅: `tools/build_cot_panel.py:56-61,129-135` は noncomm 列のみ抽出 (commercial 列なしは正)。
  legacy 形式の commercial 列は CFTC 仕様と整合 (検証後、orchestrator が zip ヘッダで実在確認済み:
  `Commercial Positions-Long/Short (All)` + Change 列)
- **massive_api_surface** ⚠️ load-bearing 未検証 (network probe は orchestrator の当日実測のみ)。
  W3-2 の成立可否がこれに全乗り
- **e12_status** ✅ ほぼ整合 (`market-data-ingest-2026-07-18.md:50-54`)
- **vol_state registry 占有** ✅ (`hypothesis-catalog-2026-07-24.md:82`)

## [W3-1] cot_commercial_dnet_flow_weekly — GO-WITH-CONDITIONS

**ban 照合: CLEAR (明示 carve-out)** — 「ban 範囲は『net_pct_oi レベル極値×週次』限定 — Δnet/flow・
commercial 側は新 family として可」(`hypothesis-catalog-2026-07-24.md:66`)、「起こすなら新 family +
台帳新行 + pre-2022 explore から」(`reports/cot_extreme_explore-2026-07-24.md:91`)。OOS 2022+
COT×価格ジョイント未接触も確認 (同:93)。

**LOCK 前必須 6 条件**: (1) primary 1 本凍結 (tercile onset vs continuous IC の未決 DoF をデータ
非接触 attestation 付きで解決、ホライズン 1 本 + m 明記)、(2) Δ窓 4w 単一設計点 + 変種禁止明記、
(3) cot_spec 死因 (単一イベント支配 >50% / 年次符号一貫性 / サイド split 同符号 / tercile 単調性) の
機械 kill rule 化、(4) 鏡像恒等性 comm ≈ −(noncomm+nonreportable) の開示 + 独立性主張の減額 +
corr 診断併記、(5) multi-week swap 純額込み (4w 実測 hurdle 14-26p 前例)、(6) rebuild assert +
反転マップ + release-lag +3bd + lookahead assert の無変更継承。

**score 裁定**: headroom 85・testability 90 は実測整合 (cot_spec 実測 21-115×)。composite 62 は
軽度インフレ — prior 45-50 が誠実 (兄弟 incoherence 死 + Sanders-Irwin null)。verdict 不変。

## [W3-2] fx_quote_spread_state — GO-WITH-CONDITIONS (弱い生存、ゲート厳格)

**ban 照合: CLEAR、差分節 3 本必須** — (i) session/hour バケット REJECT (`session-time-bias.md:97`)
は「毎日再帰する時計バケットの無条件ドリフト」であり同時刻 baseline 対比の異常オンセットは estimand
別。(ii) holiday ban (日次×カレンダー) の認可再挑戦経路「新モダリティ (intraday マイクロストラクチャ等)
+ 明示差分節」に該当。(iii) VIX 不使用。price_shock 5 席とは |move| 小の分離条件で差分。

**LOCK 前必須 6 条件**: (1) **headroom gate はイベント条件付き実測スプレッドで計算・baseline RT 使用は
自動 kill、かつ摩擦測定を forward return への一切の look の前に実施** (<10x なら OOS 未消費 kill)、
(2) 配備経路の構造ブロッカー解消 (デスゾーン live gate がイベント時点の執行をブロックする —
entry を「スプレッド正常化後の最初のバー」等に凍結するか PASS 時配備形を pre-reg 明記。未解決なら
PASS しても行き場がない)、(3) feed QA 観測前凍結 (土曜行除外 / 同時刻複数 sample median 化 /
異常持続 ≥2 連続サンプル / スプレッド上限 sanity — price_shock 監査 4-12.8% 汚染の前科)、
(4) DST 補正 (同 UTC 時刻 baseline は DST 遷移で擬似異常を系統生成 — ローカル時刻基準か補正付きで
凍結)、(5) probe 未検証の明示 + 取得後の年次 quote 密度 assert (密度不足年は正直に skip)、
(6) primary 1 本 (4h or 24h) + 年末・祝日 thin market 重複 share 診断。

**score 裁定**: headroom 35 / testability 45 / composite 48 は誠実。

## [W3-3] e12_cme_volume_forward_prereg — GO-WITH-CONDITIONS (登録アクション、BH 非消費)

MoF forward 型の正当な前例踏襲。条件: (1) power trigger の数値凍結 (N or 期日で機械判定)、
(2) joint look ゼロ attestation (QA look 済み・volume×価格ジョイント未接触を明記)、(3) scan-round2
S1 設計の無変更凍結 (unsigned abnormal volume primary + 価格 momentum への増分 IC 必須)、
(4) backfill=explore / go-forward=OOS の役割 split 凍結、(5) 陳腐化 review 期日、(6) first_bar
実測確定。

## rejected_at_generation — 5/5 支持

options OI (split 不能の事前回避 + Databento unlock は user 決裁) / weekend_gap 同型異所 (枯渇の
正直な記録) / E13 変種 (E12 が上位測定器。**E12 unsigned PASS 時のみ 12y 拡張の再入場余地を台帳に
残せば完全**) / FX 広域クロスセクション (古典因子全滅 + エキゾチック sub-friction) / intraday
vol-state 単独 (正 EV ホスト不在 + registry 2 件占有)。

## 実行順序 (採択)

**W3-1 を単独 wave で先行、W3-2 は W3-1 verdict 後に別の単独 wave** (wave-1 の実死因 = 並列 2 本の
多重性コスト。W3-2 の fetch は look に当たらないため W3-1 走行中バックグラウンド開始可)。
**横断警告**: W3-2 の coverage assert 不通過はそのまま data-blocked クローズ —
「取れたところまでで走る」への事後緩和を禁止。
