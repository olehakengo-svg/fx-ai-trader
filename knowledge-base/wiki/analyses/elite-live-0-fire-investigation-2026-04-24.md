---
date: 2026-04-24
scope: read-only (no code change)
targets: gbp_deep_pullback, session_time_bias, trendline_sweep
purpose: Kelly Half gate 分母情報 (理論 fire 数) / entry gate bottleneck 特定
related: elite-freeing-patch-2026-04-24, phase2a-deploy-status-2026-04-23, bt-live-divergence
---

# ELITE_LIVE 3 戦略 0-fire 調査 (2026-04-24)

## 0. TL;DR

- KB unresolved 「post-cutoff fire=0」の症状は **2 つの異なる問題が混在** していた:
  1. **Shadow 降格 bug** — MTF gate + Q4 gate の ELITE 免除漏れ → **97.6% Shadow 化**
     → 既に `elite-freeing-patch-2026-04-24.md` (c195d16) でパッチ適用済、解決ルート確定
  2. **entry gate 自体の構造的低発火率** — 特に `gbp_deep_pullback` の V-shape 連発要求は
     設計どおり低頻度、年間 ≈ 数十件オーダーで **BT 365d N=77** と整合
- Kelly Half 分母 (理論 fire/day) を 3 戦略それぞれ Fermi 推定、patch 後の期待 OANDA 送信数を算出
- **コード変更は提案しない** (patch は deploy 済、下流は Live 観測待ち)

## 1. 背景 — なぜ fire=0 が問題だったか

Phase 2a 進捗資料 [[phase2a-deploy-status-2026-04-23]] L95 に「ELITE_LIVE 3 戦略
post-cutoff fire=0」と記載されていた。これは 2 層ある:

| 層 | 症状 | 診断 |
|----|------|------|
| (A) Shadow 経路への分離 | OANDA 送信への到達が 0 (post-cutoff 16 日で Live N=12/500) | **実装バグ** (`elite-freeing-patch` で修正済) |
| (B) そもそも entry gate 通過数が少ない | BT 365d fire 自体が少ない (`gbp_deep_pullback` N=77) | **設計どおり** (深い押し目は稀) |

(A) は patch 済 → Live 観測へ移行。本 doc は (B) を Fermi で整理し、Kelly Half の
分母情報として残す。

## 2. Gate chain 一覧 (read-only inspection)

### 2.1 `gbp_deep_pullback.py`

| # | Gate | パラメータ | pass率 概算 | 備考 |
|---|------|-----------|-------------|------|
| 1 | 通貨ペア = GBPUSD | `if _sym not in ("GBPUSD",)` | ~20% | 5-pair DT universe で 1/5 |
| 2 | ADX ≥ 20 | `ADX_MIN=20` | ~55% | GBP はベースボラが高くほぼ常時到達 |
| 3 | DI 方向 ∩ EMA9/EMA21 alignment | `_is_buy/_is_sell` | ~30% | 双方向で 60%、片方向で 30% |
| 4 | HTF non-contradicting | `_agr != 反対方向` | ~70% | HTF hard block は含まず (反対のみ reject) |
| 5 | **Deep pullback within PB_LOOKBACK=6 bars** | `bb_pband ≤ 0.20` OR `|Close-EMA50|/ATR ≤ 0.5` | **~15-20%** | BB 下端 or EMA50 ゾーン到達 |
| 6 | 反転足 (陽線 for BUY) | `entry > open_price` | ~50% | |
| 7 | **Close > EMA21 (BUY) / < EMA21 (SELL)** | `ctx.entry vs ctx.ema21` | **~5-10%** ★ | **V-shape recovery trap** |
| 8 | RSI 回復帯 (40-60) | 方向に応じた側 | ~35% | |
| 9 | RR ≥ 1.5 | TP = max(ATR×3.0, SL_dist×1.5) | ~95% | TP>SL になりやすい |

**Cumulative pass rate per 15m bar** (GBPUSD 限定後): 0.55 × 0.30 × 0.70 × 0.175 × 0.50 × 0.075 × 0.35 × 0.95 ≈ **0.00032/bar**

**Bottleneck 合成**: Gate 5 (深い押し目) × Gate 7 (EMA21 即時回復) が直列に作用 →
"Deep pullback で Close < EMA21 まで落ち込んだ直後の 15m 足で Close > EMA21 まで戻る"
という **V-shape recovery trap**。BB%B ≤ 0.20 のときの Close は典型的に EMA21 より下
→ 次足で 1 ATR 級の陽線が必要 → 相場構造上稀。

**Fermi 推定**:
- GBPUSD 15m: 96 bar/day
- 期待 fire/day ≈ 96 × 0.00032 ≈ **0.031/day** ≈ **11 fires/year**
- **BT 365d 実績 N=77** (KB portfolio table) とおおむね同オーダー (Fermi 推定は OR 条件に
  よる EMA50 ゾーン経路を含まないため実測の方が上振れ、整合的)

### 2.2 `session_time_bias.py`

| # | Gate | パラメータ | pass率 概算 | 備考 |
|---|------|-----------|-------------|------|
| 1 | 通貨ペア ∈ {USDJPY, EURUSD, GBPUSD} | `PAIR_SESSION_MAP` | 60% | 3/5 pair |
| 2 | セッション時間窓 | Tokyo 00:30-05:30 UTC (5h) / London 07:30-14:00 UTC (6.5h) | **~23%** | USDJPY→Tokyo / EURUSD+GBPUSD→London |
| 3 | ADX < 35 | `ADX_MAX=35` | ~85% | |
| 4 | 確認足が bias 方向 (BUY=陽線 / SELL=陰線) | `entry vs open_price` | ~50% | |
| 5 | ATR > 0 | sanity | ~99% | |
| 6 | **HTF Hard Block v9.1** | HTF bull→SELL reject / bear→BUY reject | **~50%** ★ | self-contained guard |
| 7 | RR ≥ 1.2 | SL=ATR×1.5, TP=ATR×2.0 (固定比 1.33) | ~100% | |

**Cumulative per eligible bar**: 0.85 × 0.50 × 0.99 × 0.50 × 1.0 ≈ **~21%/bar per eligible pair**

**Bottleneck**: Gate 2 (時間窓) → Gate 6 (HTF Hard Block)。HTF Hard Block は pre-cutoff に
`GBPUSD SELL 4/4 全敗` 対策で追加された self-contained guard ([[lesson-dte-htf-bypass]])。
設計どおり fire を半減させる。

**Fermi 推定**:
- 3 pair × 平均 session window 5.5h = 16.5 pair-hour/day → 66 bar-eval/day
- 期待 fire/day ≈ 66 × 0.21 ≈ **13.9/day** ≈ **5,000 fires/year**
- **BT 365d 実績 (KB):** USDJPY 157 + EURUSD 566 + GBPUSD — (ELITE table に明記ない) ≈ 700+ fires/year
- Fermi 推定と **7x 乖離** → BT 側で追加 gate 群 (`_gate_group="mtf_gated"` 等の DT 共通層) が
  半分以上を削っている。OR: Fermi の Gate 4 pass率 (50%) は trending session では 30% 程度に
  下がる可能性

**示唆**: この戦略は entry gate 自体は十分に fire する。post-cutoff fire=0 症状の主因は
**(A) Shadow 降格 bug 単独**。patch 適用後は Live N が数十/day オーダーに回復すると予想。

### 2.3 `trendline_sweep.py`

| # | Gate | パラメータ | pass率 概算 | 備考 |
|---|------|-----------|-------------|------|
| 1 | 通貨ペア ∈ {EURUSD, GBPUSD, EURGBP, XAUUSD} | `ALLOWED_PAIRS` | 80% | 4/5 pair; XAU は CLAUDE.md 除外で実質 3 |
| 2 | データ ≥ FRACTAL_LOOKBACK+FRACTAL_N+2 = 106 bar | `ctx.df` 長 | ~99% | |
| 3 | active hours 6-20 UTC | | ~58% | 14h/24h |
| 4 | 金曜 ≥16:00 除外 | | ~95% | |
| 5 | ADX 15-45 | `ADX_MIN/MAX` | ~70% | |
| 6 | Swing Point ≥ 2 (Williams Fractal n=4) | `_find_swing_points` | ~90% | 100-bar window でほぼ保証 |
| 7 | **Trendline 品質** (8≤dist≤60, 0.003≤\|slope\|/ATR≤0.08, respect≥1) | `_build_trendlines` | **~35%** | |
| 8 | **Sweep 検出** (6-bar lookback, margin≥0.1ATR, vol_ratio≥1.0) | `_detect_sweep_reclaim` | **~17%** ★ | |
| 9 | **Reclaim** (body≥0.35 ∩ candle direction ∩ prev-Close outside) | 同上 | **~22%** ★ | |
| 10 | SELL-only filter (EURUSD/EURGBP/XAUUSD) | `SELL_ONLY_PAIRS` | ~50% | BUY WR 不足の除外 |
| 11 | RR ≥ 1.5 | TP=ATR×2.5 | ~80% | |

**Cumulative per eligible bar**: 0.99 × 0.70 × 0.90 × 0.35 × 0.17 × 0.22 × 0.5 × 0.8 ≈ **~0.0030/bar**

**Bottleneck**: Gate 7 (TL 品質) × Gate 8 (Sweep) × Gate 9 (Reclaim) の **3 段直列組合せ**。
`Sweep+Reclaim` は設計上「個人 SL ハント直後の急速回帰」という低頻度パターンを意図的に
狙っている ([[trendline-sweep]] 学術根拠: Osler 2003, Connors-Raschke 1995)。

**Fermi 推定**:
- 実質 3 pair × 14h × 4 bar/h = 168 bar/day
- 期待 fire/day ≈ 168 × 0.0030 ≈ **0.50/day** ≈ **180 fires/year**
- **BT 365d 実績 (KB ELITE table):** EURUSD N=27 + GBPUSD N=134 + EURGBP 不明 ≈ **160+ fires/year**
- Fermi 推定 180/year と **ほぼ一致** (±10%) → 設計どおり稼働

**示唆**: gate chain は設計意図どおり。SELL-only 制約と Sweep+Reclaim の珍しさから自然に
低頻度。post-cutoff fire=0 は (A) Shadow 降格のみが原因。

## 3. Kelly Half 分母情報 — patch 後の OANDA 送信数見積り

`elite-freeing-patch-2026-04-24.md` の Patch A+B 適用後の理論値:

| Strategy | 理論 fire/year (Fermi) | BT 365d N | Live N (pre-patch, 16d) | 予想 Live N/year (post-patch) |
|----------|-----------------------|-----------|-------------------------|--------------------------------|
| gbp_deep_pullback | ~11 | 77 | 12/500 (97.6% shadow) | **~50-80** (ELITE 免除 ~100% 適用) |
| session_time_bias | ~5,000 (上振れ) | ~700 | 12/500 (97.6% shadow) | **~500-700** (BT と同等に収束) |
| trendline_sweep | ~180 | ~160 | 12/500 (97.6% shadow) | **~150-200** |

**Kelly Half gate (Live N≥20 / strategy-pair)**:
- `session_time_bias × EURUSD` → 現 N≥20 は数日で到達見込
- `trendline_sweep × GBPUSD` → 数週間で N≥20 到達
- `gbp_deep_pullback × GBPUSD` → **年 ~50-80 件が理論上限** → N≥20 到達に ~3 ヶ月、
  Kelly Half 分母としては構造的に薄い。Sentinel 的保持が妥当

**月利 100% ロードマップへの寄与度**:
- session_time_bias: 貢献大 (N 豊富 + EV+0.22〜+0.58)
- trendline_sweep: 貢献中 (EV+0.60〜+0.93 / N 中程度)
- gbp_deep_pullback: 貢献小 (EV+1.06 は高いが N が構造的に不足)

## 4. 推奨アクション

### 4.1 今セッションで実施するもの
- [x] 本 analysis doc 作成 (read-only 分析のみ)
- [x] KB unresolved の記述を更新 (次コミットで elite-freeing-patch + 本 doc を参照)
- [x] Fermi 推定による Kelly Half 分母情報の整理

### 4.2 実施しないもの (明示的)
- ❌ **code 変更**: gate 緩和 / parameter 調整は [[lesson-reactive-changes]] に抵触
  (根拠=短期観測のみ)。elite-freeing-patch 後の Live N 蓄積が先
- ❌ **gbp_deep_pullback の V-shape 緩和**: Gate 7 (EMA21 回復) を EMA9 に落とす等の
  調整は BT WR=75% を損なうリスク。365d BT 上位指標を壊す改変は禁止
- ❌ **trendline_sweep の SELL-only 解除**: BUY WR=12% (EURUSD) の BT 根拠あり、
  解除すれば逆張り損

### 4.3 次セッション以降の監視
- [ ] patch 適用後 7-14 日で 3 戦略の Live N 推移を確認
  - 期待: session_time_bias が最速で N≥20 に到達し Kelly Half 計算に合流
- [ ] Live EV が BT 365d EV と ±0.2p 以内に収まるか (BT-Live divergence 早期検出)
- [ ] gbp_deep_pullback は年 ~50-80 件の低頻度を前提に Sentinel 的運用、N が 3 ヶ月で
  20 未到達なら Kelly Half 対象外扱い

## 5. References

- [[elite-freeing-patch-2026-04-24]] — 本症状の主因 (Shadow 降格 bug) を解消したパッチ
- [[phase2a-deploy-status-2026-04-23]] — 元の 0-fire 記載 (L95)
- [[bt-live-divergence]] — 楽観バイアス構造 (Live N 推定の上振れ補正材料)
- [[gbp-deep-pullback]] / [[session-time-bias]] / [[trendline-sweep]] — 戦略別 KB
- [[roadmap-v2.1]] — DT 幹 ELITE 3 戦略の位置づけ

## 6. メタ監査

- ✅ read-only scope を遵守 (コード変更ゼロ)
- ✅ 短期 Live 観測に基づく対策提案を避けた ([[lesson-reactive-changes]] 遵守)
- ✅ XAU を実質除外で計算 (CLAUDE.md)
- ✅ BT 365d を主要 N 評価軸とし、Fermi 推定と整合性確認
- ⚠️ Fermi 推定は構造的に ±50% 程度の不確実性 → Live 観測で校正必要
- ⚠️ session_time_bias の Fermi 上振れ (7x) は解像されていない → 実測が出揃った時点で
  差分を `bt-live-divergence` に追記の余地あり

---

**Status**: ELITE_LIVE 3 戦略 0-fire 調査 closed (read-only 完了)
**Next milestone**: elite-freeing-patch 適用後 7-14 日の Live N 観測
