# MoF Communication Modality — External Data (介入 ground-truth / 会見 transcript / GDELT)

**背景**: user 介入主張のスコーピング (wf_32d378df、2026-08-18) — 「当局発言ラダー lexicon × 公式介入ラベル」を主軸とする通信モダリティの収集基盤。
**設計 doc**: `knowledge-base/wiki/analyses/mof-communication-data-infrastructure.md`
**取得開始**: 2026-08-18 (backfill) + daily cron (`.github/workflows/mof-statements-daily.yml`)

⚠️ **このディレクトリはデータ配管のみ。発言×介入×価格のジョイント測定 (IC/EV/オーバーラップ等) は一切計算していない** (観測前凍結の規律 + MoF #4 pre-reg cross-LOCK — `knowledge-base/wiki/decisions/mof-intervention-forward-prereg-2026-07-24.md`)。測定は別 pre-reg (hypothesis-catalog 登録 + 観測前凍結) まで禁止。

## 1. ファイル構成

| パス | 内容 | 更新 |
|---|---|---|
| `interventions_daily.csv` | 外国為替平衡操作 日次明細 (1991-04〜最新開示四半期)。公式 CSV を正規化 | daily cron (四半期開示で増分) |
| `interventions_monthly_pending.csv` | 四半期日次開示が未着地の月次総額窓 (額のみ、日付/ペア無し) | daily cron (月末公表) |
| `conferences/{YYYYMM}.jsonl` | 財務大臣記者会見 transcript (1 行 = 1 会見、role タグ付き全文 blocks) | daily cron (追記) |
| `lexicon_scores.csv` | 会見ごとの発言ラダースコア (L0-L5)。corpus から決定的に再生成 | daily cron (全再生成) |
| `rss_items.csv` | MoF news.rss の為替関連新着 (link dedup 追記) | daily cron |
| `gdelt/*.csv` | GDELT DOC timelinevol (介入報道強度、2017〜) | daily cron (全再取得・上書き) |

## 2. ソースと再現

| ソース | URL | ラグ | 備考 |
|---|---|---|---|
| 介入日次 CSV | `https://www.mof.go.jp/policy/international_policy/reference/feio/foreign_exchange_intervention_operations.csv` | **四半期** (例: Q2-2026 分は 2026-08-07 公表) | CP932。四半期計行との合計クロスチェックを ingest が強制 |
| 介入月次総額 | `…/feio/data/monthly/index.html` | 約 1 ヶ月 | 額のみ。日次明細の先行指標 |
| 会見 transcript (現行) | `…/public_relations/conference/{YYYYMM}.html` → `my{YYYYMMDD}.html` | 数日 (転記) | オンライン保持は 2023-04 以降。robots.txt なし (404)、UA 明示 + ≥1.2s/req |
| 会見 transcript (2022-01〜2023-03) | 国立国会図書館 WARP (pywb)。`https://warp.ndl.go.jp/{collection}/{capture}id_/www.mof.go.jp/...` (`id_` = 原本 HTML) | — | MoF は旧ページを purge → WARP が唯一の一次アーカイブ。月次クロール (毎月 1 日前後) を lag+2〜4 ヶ月で解決 |
| MoF 新着 RSS | `https://www.mof.go.jp/news.rss` | 当日 | 為替関連 title のみ保存 |
| GDELT DOC 2.0 | `https://api.gdeltproject.org/api/v2/doc/doc?...&mode=timelinevol` | 15 分 | 2017-01-01 が被覆下限。レート制限 1 req / 5s (ingest は 6s sleep) |

再現コマンド:

```bash
# backfill 一式 (介入 + 会見 online/WARP + スコア + GDELT + 目視チェック表)
python3 tools/mof_statements_ingest.py --all

# forward daily (cron が実行するもの)
python3 tools/mof_statements_daily.py
```

## 3. lexicon ladder (v1、`tools/mof_statements_lexicon.py`)

Gnabo 系 talk/act 離散化 + 実務 escalation ladder のコード化。**大臣側発言 (冒頭発言/答) のみスコア対象** — 記者の質問中のラダー語引用は除外 (テストで固定)。答弁の為替文脈は直前の質問から継承。

| Level | 名前 | 代表パターン |
|---|---|---|
| 1 | watch | 注視 / 動向を見守る |
| 2 | concern | 過度な変動 / 急速な変動 / 一方的な動き / 憂慮 / 緊張感 |
| 3 | readiness | あらゆる選択肢 / 排除しない / 適切な対応 / 万全な対応 / 投機 |
| 4 | resolute | 断固 / 毅然 |
| 5 | action | 介入を実施 / 平衡操作 / レートチェック (明示言及) |

補助フラグ `no_comment` (コメント差し控え) はレベルではなく別列 — 介入実施期の「ノーコメント」急増自体が情報になるため。

## 4. 既知の限界 (v1)

- **大臣会見のみ**。財務官 (神田/三村) の ad-hoc ぶら下がり発言は MoF サイトに transcript がなく、GDELT 報道強度が補助線。2022 年の発言主体は鈴木大臣 + 神田財務官、2025 秋以降は片山大臣。
- **X (Twitter) は不使用** — ToS がスクレイピング明示禁止 + 公式 API の歴史取得は有償。片山大臣在任 <1 年で N も不足 (wf_32d378df data 調査)。forward で必要になれば公式 API pay-per-use を user 決裁で。
- 会見は週 2 回程度 (閣議後)。イベント日 (介入当日) に会見が無いことがある — 目視チェック表は「会見なし」行を明示。
- lexicon v1 の phrase 網羅性は 2022/2024 窓の目視チェックで較正済みだが、新表現 (新大臣の言い回し) は forward で追補が必要。追補時は `lexicon_scores.csv` を全再生成する (決定的)。

## 5. 整合確認 (2026-08-18 backfill 時)

`data/external/mof_interventions.csv` (383 events、2026-07-24 取得、MoF #4 W1-F1 凍結) との突合: backfill レポート `reports/mof_statements_backfill-2026-08-18.md` と ingest ログ参照。既存ファイルは #4 pre-reg の参照物のため**本ディレクトリからは変更しない**。
