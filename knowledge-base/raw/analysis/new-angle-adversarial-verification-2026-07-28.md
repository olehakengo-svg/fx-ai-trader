# 敵対的検証 verdict — new-angle-candidates-2026-07-28 (再ラン、正式 payload 全量照合済み)

**検証者**: 独立 subagent (2026-07-28)。初回検証は orchestrator 補間バグで payload 未達のため無効 —
本レポートが正式。payload: `knowledge-base/raw/analysis/new-angle-candidates-2026-07-28.json`。

**照合済み一次ソース**: payload JSON (6 候補 + rejected 3 系統) / hypothesis-catalog md+JSON (87 本、
該当 18 エントリ精読) / wave-1 verdict / postmortem §2-§6 / session-time-bias.md / gotobi-fix.md /
`data/calendar/structural_events.parquet` (実測検証) / `data/cache/massive/` (worktree 実態確認)。

**データ検証で確定した横断事実**: (i) structural_events.parquet 実在 (4,503 行、2014-01-01→2026-04-30、
jp_holiday=224 日、要 3 ヶ月 refresh)。(ii) **worktree の parquet は 15m だけでなく 1h も部分版**
(USD_JPY 1h 実測: 2021-12-24 開始) — 「main checkout 必須」は全 explore に適用。

## verdict サマリ

| 候補 | verdict | 核心 |
|---|---|---|
| ppp_real_fx_gap_reversion | **GO-WITH-CONDITIONS** | 条件1 (重大): 5y rolling z × FX 2014 開始 → 実効 explore が ~2.5y に崩壊。pre-2014 FX ソース確保 or 窓再設計を凍結前に解決。条件2: スワップ会計の自己矛盾解消 (純額 vs キャリー整合フィルタ、どちらか一方)。条件3: \|z\|>2 極値レグは secondary へ降格。条件4: USD 因子で実効独立 ~1-2、同時ブロック bootstrap。条件5: CPI は NSA or ALFRED vintage。**単独 wave** |
| holiday_liquidity_state_family | **GO-WITH-CONDITIONS (2 レグ縮約 + 背景線格下げ)** | レグ (d) はイベント数 5-8 倍過大の実測反証 (1h 実データで \|z\|>2 = 3.8% → 12y ≈9 件/pair、power 死確定)。レグ (b) も underpowered。検定可能は (a) 祝日前日 + (c) 米休場翌日反転のみ。祝日カレンダー定義検証 (Good Friday 等) + parquet refresh 前提。**背景 explore、BH 分母を他 family と共有しない** |
| gotobi_tokyo_fix_usdjpy | **GO-WITH-CONDITIONS (本セット中最も健全)** | 「較正プライマリ + 単一テール cell」フレーミング妥当 (postmortem 測定器故障史への解毒剤、較正は昇格 look 非消費)。条件: wave-1 の EOM D1 ≈0 実測を制約として明記 (テール cell 死亡が既定路線)、繰り越し規約の in-repo 3 文書矛盾を Ito-Yamada 定義で一本化・凍結、kill 13p の根拠明示 + sub-13p 再解釈禁止誓約、tokyo_nakane_momentum/gotobi_fix カードと台帳統合。session_time_bias REJECT との差分 (同一時計窓 diff-in-means = 直交コントラスト) は定量成立を確認 |
| pre_fomc_fx_transcription | **KILL (triage 却下、ban ではない)** | honest headroom 4-12x < 入場ゲート 10x。減衰後効果 5-10p vs 3d sd 60-80p、N≈80 → 検出不能。E7 verdict (08-28) 前に同一イベント供給源へ挑戦する理由なし。再入場経路: E7 PASS 後、C4 摩擦会計 + D0 前 exit 明示の新 pre-reg のみ |
| move_bondvol_shock_jpy_unwind | **KILL (triage 却下)** | explore 窓の MOVE ショック ≈ killed-VIX 23 イベントと同一集合 (bond 固有は全部 OOS 側)。post-2022 反転で符号一致ガード不通過が既定。cluster 後 N~12-25 で H2 同型 power 死。**現行 split では原理的に検証不能** — 再入場は 2022+ を explore に含む将来の split 再設計 or MoF 型 forward のみ |
| vol_state_gates | **GO (registry 登録のみ、wave 非該当)** | ban CLEAR、prior 本物。だが正 EV ホスト不在の構造ブロッカー未解消。登録: (a) htf_fb N≥100 recheck への split (look 追加なし)、(b) weekend_gap 将来 recheck への RV5/RV21 forward split (live 非接触の観測的 pre-reg)。単独 estimand 再確認にスロットを使わない |

payload の rejected_as_banned 3 系統 (MSCI/FTSE 指数リバランス、equity-stress JPY re-dress ×4、
GPIF quarter-end) は照合の結果**すべて支持**。

## 推奨実行順序 (採択)

1. **gotobi 較正** — 即日 (単独 family、m=1 テール cell) → [[gotobi-calibration-explore-prereg-2026-07-28]]
2. **ppp** — 条件 1-5 解消後、単独 wave
3. **holiday 縮約版 (a+c)** — 背景 explore (スロット非消費)
4. **vol_state_gates** — registry 登録
5. **pre_fomc / move_bondvol** — KILL、再入場経路のみ台帳記録
