# E15/E7 event calendar build log

**generated**: 2026-07-21T10:44:07Z / **window**: 2014-01-01 .. 2026-06-30
**pre-reg**: [[e15-e7-event-modality-prereg-2026-07-18]] §3.2 + §3.2b AMENDMENT (2026-07-21)
**builder**: `tools/event_calendar_build.py` (politeness 2s/req)

## Counts

| event | N in window | per-year |
|---|---|---|
| FOMC | 99 | 2014:8, 2015:8, 2016:8, 2017:8, 2018:8, 2019:8, 2020:7, 2021:8, 2022:8, 2023:8, 2024:8, 2025:8, 2026:4 |
| NFP | 149 | 2014:12, 2015:12, 2016:12, 2017:12, 2018:12, 2019:12, 2020:12, 2021:12, 2022:12, 2023:12, 2024:12, 2025:11, 2026:6 |
| CPI | 149 | 2014:12, 2015:12, 2016:12, 2017:12, 2018:12, 2019:12, 2020:12, 2021:12, 2022:12, 2023:12, 2024:12, 2025:11, 2026:6 |

## Validation

```json
{
  "NFP": {
    "n_in_window": 149,
    "per_year": {
      "2014": 12,
      "2015": 12,
      "2016": 12,
      "2017": 12,
      "2018": 12,
      "2019": 12,
      "2020": 12,
      "2021": 12,
      "2022": 12,
      "2023": 12,
      "2024": 12,
      "2025": 11,
      "2026": 6
    },
    "non_standard_weekday": [
      "2014-07-03",
      "2015-07-02",
      "2020-07-02",
      "2025-07-03",
      "2025-11-20",
      "2025-12-16",
      "2026-02-11"
    ],
    "first_friday_share": 0.8188,
    "oos_flags": [
      "OOS NFP non-Friday release 2025-11-20 (weekday=3)",
      "OOS NFP non-Friday release 2025-12-16 (weekday=1)",
      "OOS NFP non-Friday release 2026-02-11 (weekday=2)",
      "OOS NFP reference-month gap: (2025, 9) -> (2025, 11) (expected (2025, 10))"
    ]
  },
  "CPI": {
    "n_in_window": 149,
    "per_year": {
      "2014": 12,
      "2015": 12,
      "2016": 12,
      "2017": 12,
      "2018": 12,
      "2019": 12,
      "2020": 12,
      "2021": 12,
      "2022": 12,
      "2023": 12,
      "2024": 12,
      "2025": 11,
      "2026": 6
    },
    "non_standard_weekday": null,
    "first_friday_share": null,
    "oos_flags": [
      "OOS CPI reference-month gap: (2025, 9) -> (2025, 11) (expected (2025, 10))"
    ]
  },
  "FOMC": {
    "n_in_window": 99,
    "per_year": {
      "2014": 8,
      "2015": 8,
      "2016": 8,
      "2017": 8,
      "2018": 8,
      "2019": 8,
      "2020": 7,
      "2021": 8,
      "2022": 8,
      "2023": 8,
      "2024": 8,
      "2025": 8,
      "2026": 4
    },
    "cancelled_per_year": {
      "2020": 1
    },
    "excluded_n": 9,
    "excluded": [
      {
        "row": "March 4 (unscheduled) - 2014",
        "reason": "unscheduled",
        "statement_date": null
      },
      {
        "row": "October 4 (unscheduled) - 2019",
        "reason": "unscheduled",
        "statement_date": "2019-10-11"
      },
      {
        "row": "March 2 (unscheduled) Meeting - 2020",
        "reason": "unscheduled",
        "statement_date": "2020-03-03"
      },
      {
        "row": "March 15 (unscheduled) Meeting - 2020",
        "reason": "unscheduled",
        "statement_date": "2020-03-15"
      },
      {
        "row": "March 17-18 (cancelled) Meeting - 2020",
        "reason": "cancelled",
        "statement_date": null
      },
      {
        "row": "March 19 (notation vote) - 2020",
        "reason": "notation vote",
        "statement_date": null
      },
      {
        "row": "March 23 (notation vote) - 2020",
        "reason": "notation vote",
        "statement_date": "2020-03-23"
      },
      {
        "row": "March 31 (notation vote) - 2020",
        "reason": "notation vote",
        "statement_date": "2020-03-31"
      },
      {
        "row": "August 27 (notation vote) - 2020",
        "reason": "notation vote",
        "statement_date": "2020-08-27"
      }
    ]
  }
}
```

## Source snapshot ledger

| source | url | bytes | sha256 (12) | fetched |
|---|---|---|---|---|
| NFP | http://web.archive.org/web/20260713072607id_/https://www.bls.gov/bls/news-release/empsit.htm | 132521 | 2e55df17109b | 2026-07-21T10:43:46Z |
| CPI | http://web.archive.org/web/20260612180753id_/https://www.bls.gov/bls/news-release/cpi.htm | 128002 | 45f8f0d293e0 | 2026-07-21T10:43:48Z |
| FOMC_CURRENT | https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm | 164095 | 39374768ddbb | 2026-07-21T10:43:51Z |
| FOMC_HIST_2014 | https://www.federalreserve.gov/monetarypolicy/fomchistorical2014.htm | 96026 | ef65de7561c8 | 2026-07-21T10:43:53Z |
| FOMC_HIST_2015 | https://www.federalreserve.gov/monetarypolicy/fomchistorical2015.htm | 95178 | de2fe3ad8341 | 2026-07-21T10:43:56Z |
| FOMC_HIST_2016 | https://www.federalreserve.gov/monetarypolicy/fomchistorical2016.htm | 95766 | 9f5f8cec801d | 2026-07-21T10:43:58Z |
| FOMC_HIST_2017 | https://www.federalreserve.gov/monetarypolicy/fomchistorical2017.htm | 95137 | 6ea5566ccd6f | 2026-07-21T10:44:00Z |
| FOMC_HIST_2018 | https://www.federalreserve.gov/monetarypolicy/fomchistorical2018.htm | 95642 | e753b113b232 | 2026-07-21T10:44:02Z |
| FOMC_HIST_2019 | https://www.federalreserve.gov/monetarypolicy/fomchistorical2019.htm | 97281 | 9c4576f7df2d | 2026-07-21T10:44:05Z |
| FOMC_HIST_2020 | https://www.federalreserve.gov/monetarypolicy/fomchistorical2020.htm | 98492 | 5ae9f6863918 | 2026-07-21T10:44:07Z |

## Sanity (§3.2 range detector)

```json
{
  "status": "FAIL",
  "scope": "explore window only (\u00a73.2b-7)",
  "rule": "event-bar range < 2x median(same-ET-time bar range, prior 20 business days); majority vote over primary pairs",
  "results": {
    "NFP": {
      "checked": 118,
      "flagged": 8,
      "rate": 0.0678,
      "flagged_events": [
        "2018-08-03T12:30:00+00:00",
        "2020-03-06T13:30:00+00:00",
        "2020-04-03T12:30:00+00:00",
        "2020-07-02T12:30:00+00:00",
        "2020-10-02T12:30:00+00:00",
        "2020-11-06T13:30:00+00:00",
        "2020-12-04T13:30:00+00:00",
        "2021-02-05T13:30:00+00:00"
      ]
    },
    "CPI": {
      "checked": 117,
      "flagged": 51,
      "rate": 0.4359,
      "flagged_events": [
        "2014-01-16T13:30:00+00:00",
        "2014-02-20T13:30:00+00:00",
        "2014-03-18T12:30:00+00:00",
        "2014-04-15T12:30:00+00:00",
        "2014-08-19T12:30:00+00:00",
        "2014-10-22T12:30:00+00:00",
        "2014-11-20T13:30:00+00:00",
        "2014-12-17T13:30:00+00:00",
        "2015-01-16T13:30:00+00:00",
        "2015-06-18T12:30:00+00:00",
        "2015-07-17T12:30:00+00:00",
        "2015-09-16T12:30:00+00:00",
        "2015-11-17T13:30:00+00:00",
        "2015-12-15T13:30:00+00:00",
        "2016-02-19T13:30:00+00:00",
        "2016-03-16T12:30:00+00:00",
        "2016-05-17T12:30:00+00:00",
        "2016-06-16T12:30:00+00:00",
        "2016-07-15T12:30:00+00:00",
        "2016-10-18T12:30:00+00:00",
        "2016-12-15T13:30:00+00:00",
        "2017-01-18T13:30:00+00:00",
        "2017-03-15T12:30:00+00:00",
        "2017-04-14T12:30:00+00:00",
        "2018-04-11T12:30:00+00:00",
        "2018-06-12T12:30:00+00:00",
        "2018-08-10T12:30:00+00:00",
        "2018-11-14T13:30:00+00:00",
        "2018-12-12T13:30:00+00:00",
        "2019-01-11T13:30:00+00:00",
        "2019-02-13T13:30:00+00:00",
        "2019-03-12T12:30:00+00:00",
        "2019-04-10T12:30:00+00:00",
        "2019-06-12T12:30:00+00:00",
        "2019-08-13T12:30:00+00:00",
        "2019-10-10T12:30:00+00:00",
        "2019-11-13T13:30:00+00:00",
        "2019-12-11T13:30:00+00:00",
        "2020-01-14T13:30:00+00:00",
        "2020-02-13T13:30:00+00:00",
        "2020-03-11T12:30:00+00:00",
        "2020-04-10T12:30:00+00:00",
        "2020-05-12T12:30:00+00:00",
        "2020-06-10T12:30:00+00:00",
        "2020-07-14T12:30:00+00:00",
        "2020-09-11T12:30:00+00:00",
        "2020-10-13T12:30:00+00:00",
        "2020-11-12T13:30:00+00:00",
        "2020-12-10T13:30:00+00:00",
        "2021-02-10T13:30:00+00:00",
        "2022-03-10T13:30:00+00:00"
      ]
    },
    "FOMC": {
      "checked": 79,
      "flagged": 2,
      "rate": 0.0253,
      "flagged_events": [
        "2020-11-05T19:00:00+00:00",
        "2020-12-16T19:00:00+00:00"
      ]
    }
  },
  "reverification": {
    "method": "offset-peak test: mean(event-bar range / baseline median) at M15 offsets -4..+8 vs t_e; explore window only; range-only (no returns/directions \u2014 \u00a710-1 non-contact)",
    "verdict": "CALENDAR_TIMES_CORRECT (all event types peak at offset +0; zero broken rows -> no retroactive fixes per \u00a73.2)",
    "results": {
      "NFP": {
        "peak_offset_bars": 0,
        "ratio_profile": {
          "-4": 0.635,
          "-3": 0.667,
          "-2": 0.763,
          "-1": 1.24,
          "0": 3.938,
          "1": 1.855,
          "2": 1.502,
          "3": 1.264,
          "4": 1.323,
          "5": 1.273,
          "6": 1.459,
          "7": 1.255,
          "8": 1.172
        }
      },
      "CPI": {
        "peak_offset_bars": 0,
        "ratio_profile": {
          "-4": 0.72,
          "-3": 0.771,
          "-2": 0.813,
          "-1": 1.019,
          "0": 2.917,
          "1": 1.451,
          "2": 1.307,
          "3": 1.184,
          "4": 1.273,
          "5": 1.172,
          "6": 1.365,
          "7": 1.15,
          "8": 1.123
        }
      },
      "FOMC": {
        "peak_offset_bars": 0,
        "ratio_profile": {
          "-4": 1.167,
          "-3": 1.07,
          "-2": 1.2,
          "-1": 2.116,
          "0": 7.953,
          "1": 3.197,
          "2": 4.932,
          "3": 3.741,
          "4": 3.347,
          "5": 2.686,
          "6": 2.151,
          "7": 1.77,
          "8": 1.619
        }
      }
    }
  }
}
```

## ⚠️ §8 DEFERRED trigger

sanity フラグ率 > 5% → pre-reg §8「カレンダー sanity >5% — **user 裁定 (勝手に解釈しない)**」が発動。**discovery は user 裁定まで実行しない。**
再検証 (verify-times、上記 reverification) の結論と、フラグの年次分布 (低インフレ期 CPI / COVID 期の高ベースライン集中 = イベント低インパクト由来) を 裁定材料としてここに凍結する。時刻破損行はゼロ → §3.2 の後付け修正は不実施。

## 役割分離 (vs `tools/ff_calendar_import.py`, PR #102)

本カレンダー = **歴史イベントカレンダー** (BLS/Fed 一次ソース、2014-01〜2026-06、E15/E7 の BT 判定用、Wayback snapshot で凍結・再現可能)。
PR #102 の FF calendar capture = **go-forward ingest** (ForexFactory、E7 Actual 補完・live 蓄積、`modules/market_data_ingest.py`)。ファイル・役割とも非重複。
