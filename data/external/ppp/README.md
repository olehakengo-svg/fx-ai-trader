# PPP Real FX Gap — External Data (FRED H.10 / FRED CPI / BIS CPI)

**Wave**: `ppp_real_fx_gap_reversion` (次期探索 wave)
**根拠**: `knowledge-base/raw/analysis/new-angle-adversarial-verification-2026-07-28.md` 候補 1 — GO-WITH-CONDITIONS 条件 1 (重大): 5y rolling z-score には 2009 年以前からの FX 日次データが必要。in-repo MASSIVE parquet は 2014 開始のため、pre-2014 は本ディレクトリの FRED H.10 で補う。
**取得日時**: 2026-07-29T04:11:37Z (UTC) = 2026-07-29 13:06–13:11 JST
**注意**: このディレクトリは**データ配管のみ**。シグナル×リターンの統計 (IC/EV 等) は一切計算していない (観測前凍結の規律)。実施した検証はデータ QA (カバレッジ / 欠測 / 系列同一性) のみ。

## 1. 系列 ID 対応表

### FX (FRED H.10, 日次, ニューヨーク正午 buying rate, keyless)

| ファイル | FRED series | H.10 建値 | = OANDA ペア |
|---|---|---|---|
| `fred_h10_EURUSD.csv` | DEXUSEU | USD per 1 EUR | EUR_USD |
| `fred_h10_USDJPY.csv` | DEXJPUS | JPY per 1 USD | USD_JPY |
| `fred_h10_GBPUSD.csv` | DEXUSUK | USD per 1 GBP | GBP_USD |
| `fred_h10_AUDUSD.csv` | DEXUSAL | USD per 1 AUD | AUD_USD |
| `fred_h10_NZDUSD.csv` | DEXUSNZ | USD per 1 NZD | NZD_USD |
| `fred_h10_USDCAD.csv` | DEXCAUS | CAD per 1 USD | USD_CAD |
| `fred_h10_USDCHF.csv` | DEXSZUS | CHF per 1 USD | USD_CHF |

建値方向は 7 ペアとも OANDA ペア名と一致 (変換不要)。欠測は `.` (米国祝日等、各系列 197/4843 行 = 4.1%、最大連続 2 営業日、最大カレンダーギャップ 5 日)。H.10 は週次公表 (月曜、前週分) のため、末尾は常に数営業日〜1 週間程度遅れる。

### CPI (総合, NSA = 未季調, index)

| ファイル | 国 | series | 頻度 | 季調 | ソース | 備考 |
|---|---|---|---|---|---|---|
| `fred_cpi_US_CPIAUCNS.csv` | US | CPIAUCNS | 月次 | **NSA** | BLS via FRED | CPI-U。**2025-10 が欠測 (政府閉鎖で BLS が公表スキップ、恒久欠測)** — explore 窓 (2014–2021) 外 |
| `fred_cpi_EA_CP0000EZ19M086NEST.csv` | EA | CP0000EZ19M086NEST | 月次 | **NSA** | Eurostat via FRED | HICP 総合 **EA19 (19 か国固定構成)**、1996-12 開始、2026-06 まで現行更新 |
| `fred_cpi_JP_JPNCPIALLMINMEI.csv` | JP | JPNCPIALLMINMEI | 月次 | **NSA** | OECD via FRED | **2021-06 で更新停止** (下記 §4.2)。クロスチェック用に保持 |
| `bis_cpi_JP_WS_LONG_CPI_M_JP_628.csv` | JP | BIS WS_LONG_CPI `M.JP.628` | 月次 | **NSA** (総務省ヘッドライン, BIS が 2010=100 に rebase) | **BIS (JP 主系列)** | 1946-08〜2026-04。FRED 系列と重複期間で YoY log 差 max 1e-6 = 同一系列の rebase (QA 済) |
| `fred_cpi_GB_GBRCPIALLMINMEI.csv` | GB | GBRCPIALLMINMEI | 月次 | **NSA** | OECD via FRED | 2025-03 で停滞 (§4.3) |
| `fred_cpi_AU_AUSCPIALLQINMEI.csv` | AU | AUSCPIALLQINMEI | **四半期** | **NSA** | OECD via FRED | 日付は四半期の**初月 1 日** (2025-01-01 = 2025Q1)。2025Q1 で停滞 |
| `fred_cpi_NZ_NZLCPIALLQINMEI.csv` | NZ | NZLCPIALLQINMEI | **四半期** | **NSA** | OECD via FRED | 同上。2025Q1 で停滞 |
| `fred_cpi_CA_CANCPIALLMINMEI.csv` | CA | CANCPIALLMINMEI | 月次 | **NSA** | OECD via FRED | 2025-03 で停滞 |
| `fred_cpi_CH_CHECPIALLMINMEI.csv` | CH | CHECPIALLMINMEI | 月次 | **NSA** | OECD via FRED | 2025-04 で停滞 |

全系列 NSA を確保 (FRED series ページで "Not Seasonally Adjusted" を確認済)。NSA は改定がほぼゼロのため vintage/look-ahead 問題を回避できる — これが SA より NSA を優先した理由。

## 2. 再現コマンド

```bash
# FX (H.10 日次, 2008-01-01〜)
for s in DEXUSEU DEXJPUS DEXUSUK DEXUSAL DEXUSNZ DEXCAUS DEXSZUS; do
  curl -s "https://fred.stlouisfed.org/graph/fredgraph.csv?id=${s}&cosd=2008-01-01" -o "fred_h10_<pair>.csv"
done

# CPI (FRED, 全履歴)
curl -s "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCNS" -o fred_cpi_US_CPIAUCNS.csv
# (他系列も同様: id を上表の series に置換)

# CPI JP 主系列 (BIS, keyless)
curl -s "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_LONG_CPI/1.0/M.JP.628?format=csv" \
  -o bis_cpi_JP_WS_LONG_CPI_M_JP_628.csv
# BIS refresh 経路 (FRED OECD feed 停滞時の代替、検証済 key):
#   M.US.628 / M.XM.628(EA) / M.GB.628 / M.CA.628 / M.CH.628 → 2026-05 まで確認
#   M.AU.628 / M.NZ.628 → 四半期値を 3 か月繰り返す step 系列 (2026-03 まで確認)。Q.AU.628 等の Q key は存在しない
```

QA スクリプト (カバレッジ/欠測/z 有効開始日の再計算): `check_coverage.py` (同ディレクトリ) — 本 README §1/§3 の数値を生成したもの。統計計算なし。

## 3. カバレッジ表 (ペア × z 有効開始日)

前提: gap 系列開始 = max(FX 初日, 各 CPI 脚の初観測期間末 + 公表凍結 45d)。全 CPI 脚は 1996-12 以前開始のため、拘束条件は FX 初日 2008-01-02。z 有効開始 = gap 開始 + 5 年 (次の FX 営業日にスナップ)。

| ペア | FX 有効開始 | FX 最終 | CPI 脚 (base/quote) | CPI 開始 (拘束側) | 5y z 有効開始 | explore 2014-01-01 比 |
|---|---|---|---|---|---|---|
| EUR_USD | 2008-01-02 | 2026-07-24 | EA / US | EA 1996-12 | **2013-01-02** | +364d 余裕 ✅ |
| USD_JPY | 2008-01-02 | 2026-07-24 | US / JP(BIS) | JP 1946-08 | **2013-01-02** | +364d 余裕 ✅ |
| GBP_USD | 2008-01-02 | 2026-07-24 | GB / US | GB 1955-01 | **2013-01-02** | +364d 余裕 ✅ |
| AUD_USD | 2008-01-02 | 2026-07-24 | AU / US | AU 1948-Q3 | **2013-01-02** | +364d 余裕 ✅ |
| NZD_USD | 2008-01-02 | 2026-07-24 | NZ / US | NZ 1914-Q2 | **2013-01-02** | +364d 余裕 ✅ |
| USD_CAD | 2008-01-02 | 2026-07-24 | US / CA | CA 1914-01 | **2013-01-02** | +364d 余裕 ✅ |
| USD_CHF | 2008-01-02 | 2026-07-24 | US / CH | CH 1955-01 | **2013-01-02** | +364d 余裕 ✅ |

**結論: 7 ペア全てで explore 窓 (2014-01 開始) が成立する** (条件 1 クリア)。CPI 側の period_holes は全系列ゼロ (US 2025-10 の 1 点欠測のみ、窓外)。

## 4. 設計論点 (探索設計者への引き継ぎ — 本ディレクトリでは未解決のまま)

### 4.1 AU/NZ は CPI が四半期 (確認済み事実)
- ABS (豪) / Stats NZ は全品目 CPI を**四半期のみ**公表 (explore 窓全期間)。FRED に月次系列は存在しない (`AUSCPIALLMINMEI` 等は 404)。ABS の月次 CPI indicator (2022-10〜, 部分バスケット) は FRED 未収載で、窓内カバレッジもない。
- **月次補間はしていない** (指示どおり)。設計論点: (a) 四半期値を quarter 内 flat hold (BIS step 系列と同型) するか、(b) AU/NZ を z 定義から外すか、(c) 補間するか — 補間は将来情報混入リスクがあるため、pre-reg で明示的に決めること。
- **凍結アンカーの罠**: FRED の四半期日付スタンプは四半期**初月** (2025-01-01 = 2025Q1)。「観測日付 + 45d」で凍結すると 2025Q1 (公表 ~4 月末) が 2 月に使用可能扱いになり **look-ahead**。凍結は必ず**期間末** (quarter end) 基準で実装すること。

### 4.2 JP は FRED 全系列が 2021-06 で死亡 → BIS を主系列に
- FRED 上の日本 CPI (JPNCPIALLMINMEI / JPNCPALTT01IXNBM / CPALTT01JPM657N/659N/661S / JPNCPICORMINMEI 全て) は **2021-06 で更新停止** (OECD 経由の再配布停止)。FRED のみでは explore 窓の最後の約 6 か月 + OOS 全体が欠落する。
- 対処: **BIS WS_LONG_CPI `M.JP.628` を JP 主系列に採用** (keyless、1946-08〜2026-04)。重複期間 2000-01〜2021-06 (N=246) で FRED 系列との YoY log 差 max 1e-6 → 同一の総務省ヘッドライン CPI を BIS が 2010=100 に rebase したものと確認済み。

### 4.3 FRED の OECD 経由系列は「フィード停滞」している (explore は無傷、live は不可)
- GB 2025-03 / CA 2025-03 / CH 2025-04 / AU・NZ 2025Q1 で末尾停滞。新フォーマット系列 (`{CC}CPALTT01IXNBM`) はさらに古い (2023 年末)。
- explore 窓 (2014–2021) には無影響。OOS 検証や将来の live 化で 2025 年以降が必要になったら **BIS refresh 経路 (§2 の検証済 key) を使う** (BIS は 2026-05 まで確認済、ただし BIS 自体も約 2–3 か月ラグ)。
- 米国のみ BLS 直系列 (CPIAUCNS) なので現行更新 (2026-06 まで)。

### 4.4 EA HICP の系列選定
- 採用: **CP0000EZ19M086NEST (EA19 固定構成, NSA, 2015=100)**。理由: FRED で現行更新 (2026-06) されている唯一の EA 総合 HICP index。EA20 版 (クロアチア加盟後構成) は FRED に存在しない (404 確認)。OECD 版 `CPHPTT01EZM661N` は 2023-01 で discontinued。
- 含意: 2023-01 以降の EA19 は「現在のユーロ圏 (EA20)」と構成が 1 か国分ずれるが、ウェイト影響は微小 (クロアチア ~0.7%)。5y z の分母スケールにはほぼ効かない。pre-reg に系列 ID を固定 (EA19) と明記すること。
- HICP は flash (月末 ~0–3d) → final (~17d) の 2 段階公表だが、本系列は final。45d 凍結なら flash/final の差は問題にならない。

### 4.5 CPI 公表ラグの実勢 (45d 凍結の妥当性材料)
| 国 | 公表機関 | 参照期間末からの公表ラグ (実勢) |
|---|---|---|
| US | BLS | ~10–14d (月中旬) |
| EA | Eurostat | flash ~0–3d / final ~17d |
| JP | 総務省統計局 | ~19–25d (翌月第 3 金曜前後、全国) |
| GB | ONS | ~14–20d |
| CA | StatCan | ~15–20d |
| CH | FSO/BFS | ~1–5d (最速) |
| AU | ABS | **四半期**末から ~25–30d |
| NZ | Stats NZ | **四半期**末から ~15–20d |

- **月次 7 か国は全て ≤25d → 「期間末 + 45d」凍結は全国で保守的かつ安全** (national release 基準)。
- ただし「FRED でいつ見えたか」は national release より遅い (OECD 経由は月単位のラグ、§4.3)。NSA 系列は改定ほぼゼロなので、explore では **national release calendar を可用性モデルとし 45d はその上限として妥当** — FRED 到着時刻を再現する必要はない。厳密な vintage が必要になったら ALFRED (US のみ実用的)。
- 例外イベント: US 2025-10 は公表自体が存在しない (政府閉鎖)。凍結ロジックは「最後に公表された月を hold」で自然に処理されるが、2025-10〜11 の US 脚は 1 か月余分に stale になる (窓外、記録のみ)。

### 4.6 スコープ外 (明示)
- スワップ/キャリー会計は本 wave の対象外 (敵対的検証の整理どおり)。
- シグナル定義・z 窓の営業日換算 (5y = カレンダー 5 年 vs 1260 営業日)・リバランス頻度は観測前凍結ドキュメント側で決定する。本ディレクトリは入力データの提供のみ。

## 5. ファイル一覧 (2026-07-29 取得)

FX 7 ファイル: `fred_h10_{EURUSD,USDJPY,GBPUSD,AUDUSD,NZDUSD,USDCAD,USDCHF}.csv` — 各 4,843 行 (2008-01-02〜2026-07-24, 欠測 197)
CPI 9 ファイル: `fred_cpi_{US,EA,JP,GB,AU,NZ,CA,CH}_*.csv` + `bis_cpi_JP_WS_LONG_CPI_M_JP_628.csv`
