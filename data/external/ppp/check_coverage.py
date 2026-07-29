"""PPP data pipeline coverage verification (data QA only — no signal/return statistics)."""
import pandas as pd
from pathlib import Path

D = Path("/Users/jg-n-012/test/fx-ai-trader/.claude/worktrees/hopeful-kapitsa-417e40/data/external/ppp")

FX = {
    "EURUSD": "DEXUSEU", "USDJPY": "DEXJPUS", "GBPUSD": "DEXUSUK",
    "AUDUSD": "DEXUSAL", "NZDUSD": "DEXUSNZ", "USDCAD": "DEXCAUS", "USDCHF": "DEXSZUS",
}

print("=" * 100)
print("FX (FRED H.10 daily)")
print("=" * 100)
fx_first_valid = {}
fx_last_valid = {}
for pair, sid in FX.items():
    df = pd.read_csv(D / f"fred_h10_{pair}.csv")
    assert df.columns.tolist() == ["observation_date", sid], f"{pair}: header mismatch {df.columns.tolist()}"
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    v = pd.to_numeric(df[sid], errors="coerce")
    n = len(df)
    miss = int(v.isna().sum())
    valid = df.loc[v.notna(), "observation_date"]
    fx_first_valid[pair] = valid.iloc[0]
    fx_last_valid[pair] = valid.iloc[-1]
    # max consecutive missing rows (holidays etc.)
    runs = (v.isna().astype(int).groupby(v.notna().cumsum()).sum())
    max_run = int(runs.max())
    # max calendar-day gap between consecutive valid observations
    gaps = valid.diff().dt.days
    max_gap = int(gaps.max())
    max_gap_at = valid[gaps.idxmax()] if gaps.notna().any() else None
    print(f"{pair} ({sid}): rows={n} missing='.'={miss} ({miss/n:.1%}) "
          f"first_valid={valid.iloc[0].date()} last_valid={valid.iloc[-1].date()} "
          f"max_missing_run={max_run} max_calendar_gap={max_gap}d (ending {max_gap_at.date()})")

CPI = {
    "US": ("fred_cpi_US_CPIAUCNS.csv", "CPIAUCNS", "M"),
    "EA": ("fred_cpi_EA_CP0000EZ19M086NEST.csv", "CP0000EZ19M086NEST", "M"),
    "JP_fred": ("fred_cpi_JP_JPNCPIALLMINMEI.csv", "JPNCPIALLMINMEI", "M"),
    "GB": ("fred_cpi_GB_GBRCPIALLMINMEI.csv", "GBRCPIALLMINMEI", "M"),
    "AU": ("fred_cpi_AU_AUSCPIALLQINMEI.csv", "AUSCPIALLQINMEI", "Q"),
    "NZ": ("fred_cpi_NZ_NZLCPIALLQINMEI.csv", "NZLCPIALLQINMEI", "Q"),
    "CA": ("fred_cpi_CA_CANCPIALLMINMEI.csv", "CANCPIALLMINMEI", "M"),
    "CH": ("fred_cpi_CH_CHECPIALLMINMEI.csv", "CHECPIALLMINMEI", "M"),
}

print()
print("=" * 100)
print("CPI (FRED)")
print("=" * 100)
cpi_first = {}
cpi_last = {}
for cc, (fn, sid, freq) in CPI.items():
    df = pd.read_csv(D / fn)
    assert df.columns.tolist() == ["observation_date", sid], f"{cc}: header mismatch"
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    v = pd.to_numeric(df[sid], errors="coerce")
    miss = int(v.isna().sum())
    step = 3 if freq == "Q" else 1
    d = df["observation_date"]
    month_diffs = (d.dt.year.diff() * 12 + d.dt.month.diff()).dropna()
    holes = int((month_diffs != step).sum())
    cpi_first[cc] = d.iloc[0]
    cpi_last[cc] = d.iloc[-1]
    print(f"{cc} ({sid}, {freq}): rows={len(df)} internal_missing={miss} period_holes={holes} "
          f"first={d.iloc[0].date()} last={d.iloc[-1].date()}")

# BIS JP
bis = pd.read_csv(D / "bis_cpi_JP_WS_LONG_CPI_M_JP_628.csv")
bis["date"] = pd.to_datetime(bis["TIME_PERIOD"], format="%Y-%m")
md = (bis["date"].dt.year.diff() * 12 + bis["date"].dt.month.diff()).dropna()
holes = int((md != 1).sum())
print(f"JP_bis (WS_LONG_CPI M.JP.628, M): rows={len(bis)} period_holes={holes} "
      f"first={bis['date'].iloc[0].date()} last={bis['date'].iloc[-1].date()}")
cpi_first["JP_bis"] = bis["date"].iloc[0]
cpi_last["JP_bis"] = bis["date"].iloc[-1]

# QA: BIS vs FRED JP overlap — same underlying series up to rebasing?
print()
print("=" * 100)
print("QA: BIS JP vs FRED JP overlap (rebasing consistency, YoY log-diff comparison)")
print("=" * 100)
fjp = pd.read_csv(D / "fred_cpi_JP_JPNCPIALLMINMEI.csv")
fjp["date"] = pd.to_datetime(fjp["observation_date"])
m = pd.merge(fjp.rename(columns={"JPNCPIALLMINMEI": "fred"})[["date", "fred"]],
             bis.rename(columns={"OBS_VALUE": "bis"})[["date", "bis"]], on="date").dropna()
m = m[m["date"] >= "2000-01-01"].set_index("date")
import numpy as np
ly_f = np.log(m["fred"]).diff(12)
ly_b = np.log(m["bis"]).diff(12)
diff = (ly_f - ly_b).abs().dropna()
print(f"overlap 2000-01..{m.index[-1].date()}: N={len(diff)} max|YoY_log_diff|={diff.max():.6f} "
      f"mean={diff.mean():.6f}  (should be ~0 if same underlying series, rebased)")

# QA: AU/NZ quarter stamping convention
au = pd.read_csv(D / "fred_cpi_AU_AUSCPIALLQINMEI.csv")
print(f"\nAU quarterly date stamps (last 4): {au['observation_date'].tail(4).tolist()}  "
      f"(months {sorted(set(pd.to_datetime(au['observation_date']).dt.month))} => first month of quarter)")

# z-score first-valid-day computation
print()
print("=" * 100)
print("5y rolling z first valid day per pair (FX ∩ CPI intersection; input-availability basis)")
print("=" * 100)
PAIR_CPI = {
    "EURUSD": ("EA", "US"), "USDJPY": ("US", "JP_bis"), "GBPUSD": ("GB", "US"),
    "AUDUSD": ("AU", "US"), "NZDUSD": ("NZ", "US"), "USDCAD": ("US", "CA"), "USDCHF": ("US", "CH"),
}
PUB_LAG_DAYS = 45  # design freeze assumption
rows = []
for pair, (a, b) in PAIR_CPI.items():
    fx0 = fx_first_valid[pair]
    # CPI usable from: first observation period start + one period + 45d publication freeze
    def usable(cc):
        per_end = cpi_first[cc] + (pd.DateOffset(months=3) if cc in ("AU", "NZ") else pd.DateOffset(months=1))
        return per_end + pd.Timedelta(days=PUB_LAG_DAYS)
    gap_start = max(fx0, usable(a), usable(b))
    z_start = gap_start + pd.DateOffset(years=5)
    # snap to first available FX business day >= z_start
    fxdf = pd.read_csv(D / f"fred_h10_{pair}.csv")
    fxdf["observation_date"] = pd.to_datetime(fxdf["observation_date"])
    v = pd.to_numeric(fxdf[FX[pair]], errors="coerce")
    valid_dates = fxdf.loc[v.notna(), "observation_date"]
    snapped = valid_dates[valid_dates >= z_start].iloc[0]
    margin = (pd.Timestamp("2014-01-01") - snapped).days
    ok = "OK" if snapped < pd.Timestamp("2014-01-01") else "LATE"
    print(f"{pair}: gap_series_start={gap_start.date()} z_first_valid={snapped.date()} "
          f"margin_vs_2014-01-01={margin:+d}d [{ok}]  (CPI legs: {a}/{b})")
