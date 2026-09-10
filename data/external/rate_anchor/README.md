# rate_anchor — family C (金利観測アンカー) 材料の日次蓄積

**目的**: 日米金利差フェアバリュー帯の**材料**の日次蓄積 (family C、pre-reg 前)。
**材料のみ — シグナル/乖離/フェアバリュー帯の計算はここでは行わない** (signal×outcome 接触の予防)。
設計: `knowledge-base/wiki/analyses/family-c-anchor-automation-2026-08-18.md`

## ファイル

| file | 内容 | ソース |
|---|---|---|
| `jgb_yields.csv` | JGB 15 テナー (1y..40y) 日次利回り、2013-01-04〜 | MoF jgbcm_all.csv (歴史、Shift-JIS+和暦) + 英語版 jgbcme.csv (当月、日次) |
| `us_treasury_yields.csv` | DGS1/DGS2/DGS5/DGS10、2013-01-01〜 | FRED fredgraph.csv (keyless) |
| `zn_f_daily.csv` | ZN=F (10Y T-Note futures) UTC-day OHLCV | `data/cache/yield/ZN_F_1h.parquet` の集計 (yfinance 1h、union-merge cache) |
| `manifest.json` | 行数/被覆/sha256 (タイムスタンプなし = 決定的) | `tools/rate_anchor_ingest.py` が毎回再生成 |

## 再現コマンド

```bash
python3 tools/rate_anchor_ingest.py fetch --refresh-zn   # 日次ジョブと同一 (network)
python3 tools/rate_anchor_ingest.py build-only           # ZN 日足 + manifest のみ再生成
```

更新: `.github/workflows/rate-anchor-daily.yml` (平日 21:15 UTC、union-merge で自動 commit)。

## 規約・注意

- **union-merge 蓄積** (重複日は fresh 採用): 行数単調非減少 / 既存日付欠落なし / 左端保持を assert。
  修復が必要なら CSV を削除して再シード (歴史ソースが再取得可能なため安全)。
- MoF 歴史ファイルは月次ラグ (~2-4 週)。当月分は英語版で日次補完し、穴は歴史ファイルの
  次回更新で自己修復する。シード時 (2026-08-18) の切れ目 07-31→08-03 は土日のみで穴なし。
- JGB の '-' (未発行テナー) は NaN。日付は各ソースの営業日ラベルそのまま
  (JGB=JST 営業日 / FRED=US 営業日 / ZN=UTC-day) — **クロスソース join は利用側の責務**
  (family C pre-reg で日付規約を凍結すること)。
- yfinance **日足**の UTC ずれ lesson ([[lesson-yfinance-jpy-daily-utc-shift-2026-08-18]]) に注意 —
  zn_f_daily は 1h バーからの自前 UTC-day 集計でありずれの対象外。
