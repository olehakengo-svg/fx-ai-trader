---
title: OANDA v20 口座の取引可能銘柄 全集合 (凍結 snapshot 2026-10-22)
tags: [oanda, instruments, supply-space, u4c, r3]
status: record
---

# OANDA v20 口座の銘柄全集合 — 第6次 §4.3 (c) の決定的確認

**Rule**: R3 (read-only 計測、live/tier/lot 変更なし)。tool = `tools/oanda_instrument_universe.py`、raw = `knowledge-base/raw/bt-results/oanda-instrument-universe/2026-10-22.json` (token / account id は記録しない)。

## 結果 (2026-10-22T06:04Z)

| 項目 | 値 |
|---|---|
| 取引可能銘柄数 | **68** |
| type 別 | CURRENCY 68 (METAL / CFD / INDEX は **0**) |
| 貴金属 (XAU/XAG/XPT/XPD) | **なし** |
| JPY quote | 11 (AUD/CAD/CHF/EUR/GBP/HKD/NZD/SGD/TRY/USD/ZAR _JPY) |
| 現 MODE_CONFIG の銘柄 | 14 (XAU_USD 2 モードは**この口座に存在しない銘柄** = 死に銘柄) |

全 68: AUD_CAD AUD_CHF AUD_HKD AUD_JPY AUD_NZD AUD_SGD AUD_USD CAD_CHF CAD_HKD CAD_JPY CAD_SGD CHF_HKD CHF_JPY CHF_ZAR EUR_AUD EUR_CAD EUR_CHF EUR_CZK EUR_DKK EUR_GBP EUR_HKD EUR_HUF EUR_JPY EUR_NOK EUR_NZD EUR_PLN EUR_SEK EUR_SGD EUR_TRY EUR_USD EUR_ZAR GBP_AUD GBP_CAD GBP_CHF GBP_HKD GBP_JPY GBP_NZD GBP_PLN GBP_SGD GBP_USD GBP_ZAR HKD_JPY NZD_CAD NZD_CHF NZD_HKD NZD_JPY NZD_SGD NZD_USD SGD_CHF SGD_JPY TRY_JPY USD_CAD USD_CHF USD_CNH USD_CZK USD_DKK USD_HKD USD_HUF USD_JPY USD_MXN USD_NOK USD_PLN USD_SEK USD_SGD USD_THB USD_TRY USD_ZAR ZAR_JPY

## 帰結

- [[../research/external-hypothesis-scan-round6-2026-10-20]] §4.3 の判定「(c) 非 FX は OANDA 制約下で空集合」は **API 一次情報で確定** (公式ページ計数 68 と一致、貴金属は v20 口座に無い)。
- 残余 (c) = 追加 FX ペアの shadow 蓄積の母集団 = 68 − 現 13 (XAU 除く) = **55 本**。displayPrecision / pipLocation / marginRate / financing は raw に凍結済み — RT 実測 (G0 型、read-only) の入力にそのまま使う。取引制限中ペアの除外は OANDA 公式の制限一覧 (user 画面) と突き合わせが要る。
- `friction-analysis.md` の XAU 行と MODE_CONFIG の XAU_USD 2 モードは「口座に存在しない銘柄」として扱う (KB 注記は本 PR、MODE_CONFIG 除去は code PR 別建て)。

## 限界
- snapshot は 1 回 (06:04Z)。銘柄集合・marginRate は OANDA 側で変わりうるので、引用時は run_utc を併記する。
- 取引制限フラグは API 応答に無い (公式ページの「取引制限中の通貨ペア」で確認)。
