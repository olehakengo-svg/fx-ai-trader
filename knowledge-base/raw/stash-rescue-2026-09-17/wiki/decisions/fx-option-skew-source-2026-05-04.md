---
title: FX Option Skew (FOS-1) — dexter 第 3 ツール候補のデータ源調査
date: 2026-05-04
status: PROPOSED → SOURCE_FEASIBILITY_REQUIRED
owner: claude-司令塔
implementer: codex
trigger: ポジション偏り edge を CFTC のみで判定している (S3 literal Wave 1 完了済)
related:
  - knowledge-base/wiki/lessons/feedback_codex_mock_test_trap.md
  - knowledge-base/wiki/decisions/structural-flow-tier-2026-05-04.md
  - 記憶: project_dexter_fx_phase0_2026_05_03.md (Phase 0 cot_report/x_sentiment 常駐)
roadmap_gate: dexter Phase 1 candidate
---

# 1. Why this tool

CFTC は商業 hedger 構造で常に偏るデータ源で、W3-5 の 6-pair pool は FDR 棄却済 (本物の no-edge)。**オプション側 (Risk Reversal, 25Δ skew, BFLY)** は OTM hedger と speculator の交差で、CFTC とほぼ独立な情報を持つ。dexter Phase 1 で 3rd tool として加える価値が大きい。

ただし: **FX option 25Δ RR の信頼できる無料 API が確立していない**。Phase 0 で `oanda_audit` を Render Postgres 不在で削った経緯 (記憶) と同じく、**先に source feasibility を確認** してから実装する。

# 2. Two-phase approach

## 2.1 Phase A — Source feasibility study (本決定の唯一の実装対象)

実装ではなく **データ源生存性の E2E 検証**。複数候補を並行調査:

| Candidate | Source | Auth | 25Δ RR? | Coverage | Risk |
|---|---|---|---|---|---|
| C1 | CME FX Option settlement reports (cmegroup.com/markets) | None (public) | OI のみ、RR は計算要 | 主要 6 通貨 | スクレイピング脆弱 |
| C2 | NY Fed H.10 / FRED | None | × (spot のみ) | 主要 | RR は無い |
| C3 | Yahoo Finance currency ETF options (FXE, FXY, etc) | None | proxy | ETF 6 銘柄 | プロキシなのでズレ |
| C4 | Investing.com currency options page | None (scrape) | △ Implied vol mention | 主要 | TOS / 安定性 |
| C5 | Saxo Open API | API key | ○ 25Δ RR 直接 | 100+ pair | 個人口座必要 |
| C6 | OANDA v3 pricing/instruments | API key | × spot のみ | OANDA pair | RR 無し |
| C7 | quote.com / TradingEconomics | API key (paid) | ○ | 主要 | 有料 |
| C8 | Firecrawl で BFIX / forexlive 日次コメント | なし | △ qualitative | 主要 | 構造化困難 |

**現実的本命**: C1 (CME) + C3 (Yahoo currency ETF options proxy) の組合せ。C5 は将来候補として保留 (口座開設は別議論)。

## 2.2 Phase B — Tool implementation (Phase A PASS 後の **別タスク**)

Phase A で「日次更新で 6 ヶ月以上欠損率 < 5% を達成できる source」が 1 つでも見つかれば、それを使って `fx_option_skew` ツールを実装。本決定文書は Phase B の spec を含まない (Phase A 結果を見てから別決定で書く)。

# 3. Phase A acceptance criteria

- [ ] 上記 8 candidate のうち最低 4 つ E2E で叩いて、結果を `knowledge-base/raw/audits/fos1-source-feasibility-2026-05-04.md` に表で報告
- [ ] 各 candidate について:
  - HTTP status / response shape
  - 25Δ RR (or proxy) が抽出できるか (yes / partial / no)
  - 直近 6 ヶ月の欠損率 (実測 sample 30 日で代替可)
  - レート制限 / TOS 上の懸念
  - サンプル row を JSON で 3 行付ける
- [ ] 推奨 source 1〜2 個を選定し、Phase B 実装計画 (どの API、cache TTL、schema) を 1 ページにまとめる
- [ ] **Phase B 実装は本タスク対象外**。司令塔 Claude が feasibility report を読んで Phase B 起動の決定を出す

# 4. Risks / mitigations

- **R1 — TOS 違反**: Investing.com 等のスクレイピングは TOS 上グレー。Firecrawl 経由でも商用利用に注意。Phase A の report に TOS 状況を必ず明記。
- **R2 — Source 死亡**: 先行 Phase 0 で oanda_audit 削除した教訓。Phase A は **6 ヶ月の安定性まで実測** することが理想だが現実的ではないので、最低 「直近 30 日 + 1 年前同月 30 日」 の 2 sample で安定性チェック。
- **R3 — proxy のズレ**: ETF options (FXE/FXY) は配当・コスト調整のため spot RR と微妙にズレる。Phase A で spot vs ETF の 25Δ skew 相関を最低 30 日 sample で確認。

# 5. Dexter side scope

dexter リポジトリは別 git repo (`/Users/jg-n-012/test/dexter`)。本タスクは fx-ai-trader の `.ai/tasks/` に置かず、dexter 側の queue に置く。タスク本体は dexter の AGENTS.md に従う。

# 6. Out of scope (本決定)

- Phase B 実装 (上記)
- Saxo Open API 統合 (C5、口座開設の別議論)
- OANDA option pricing 統合 (C6 に option がある場合のみ別議論)
- 戦略結合 (`risk_reversal_extreme_filter` 等は dexter Phase B 完了後の別決定)
