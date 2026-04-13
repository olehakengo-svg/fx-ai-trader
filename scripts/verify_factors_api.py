#!/usr/bin/env python3
"""Factor Decomposition API 検証スクリプト
Renderデプロイ後に実行し、/api/demo/factors が正しく動作することを検証する。

Usage: python3 scripts/verify_factors_api.py

検証項目:
1. 各単因子で非空レスポンスが返ること
2. 2因子交差で正EVセルが検出されること
3. EVの値が妥当な範囲(-50 ~ +50 pip)であること
4. 既知のアルファ源（H14×JPY等）が再現されること
5. 既知の毒性源（EUR_USD SELL等）が再現されること
"""
import json
import urllib.request
import sys

BASE = "https://fx-ai-trader.onrender.com"
ERRORS = []
PASSES = []

def fetch(path):
    try:
        req = urllib.request.Request(f"{BASE}{path}")
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

def check(name, condition, detail=""):
    if condition:
        PASSES.append(name)
        print(f"  ✅ {name}")
    else:
        ERRORS.append(f"{name}: {detail}")
        print(f"  ❌ {name}: {detail}")

print("=== Factor Decomposition API Verification ===\n")

# 1. 単因子スキャン
print("--- Step 1: Single-factor scan ---")
SINGLE_FACTORS = ["strategy", "instrument", "direction", "hour", "regime",
                   "confidence", "close_reason", "holding_time", "spread_tier"]
for f in SINGLE_FACTORS:
    d = fetch(f"/api/demo/factors?factors={f}&min_n=3")
    if "error" in d:
        check(f"single/{f}", False, d["error"])
        continue
    cells = d.get("cells", [])
    check(f"single/{f} non-empty", len(cells) > 0, f"got {len(cells)} cells")
    # EV妥当性
    for c in cells:
        ev = c.get("ev", 0)
        check(f"single/{f} EV range", -50 < ev < 50,
              f"{c.get(f, '?')} EV={ev}")
        break  # 最初の1セルだけチェック

# 2. 2因子交差
print("\n--- Step 2: 2-factor cross ---")
CROSS = [("hour", "instrument"), ("strategy", "instrument"),
         ("direction", "instrument"), ("direction", "regime")]
for f1, f2 in CROSS:
    d = fetch(f"/api/demo/factors?factors={f1},{f2}&min_n=5")
    if "error" in d:
        check(f"cross/{f1}×{f2}", False, d["error"])
        continue
    cells = d.get("cells", [])
    check(f"cross/{f1}×{f2} non-empty", len(cells) > 0, f"got {len(cells)} cells")
    positive = [c for c in cells if c.get("ev", 0) > 0]
    check(f"cross/{f1}×{f2} has positive EV", len(positive) > 0,
          f"{len(positive)}/{len(cells)} positive")

# 3. 既知アルファ源の再現
print("\n--- Step 3: Known alpha source verification ---")
d = fetch("/api/demo/factors?factors=hour,instrument&min_n=5")
if "error" not in d:
    cells = d.get("cells", [])
    h14_jpy = [c for c in cells if c.get("hour") == "14" and c.get("instrument") == "USD_JPY"]
    if h14_jpy:
        check("H14×JPY detected", True)
        check("H14×JPY EV positive", h14_jpy[0].get("ev", 0) > 0,
              f"EV={h14_jpy[0].get('ev')}")
    else:
        check("H14×JPY detected", False, "cell not found (may need more data)")

# 4. 既知毒性源の検出
print("\n--- Step 4: Known toxic source detection ---")
d = fetch("/api/demo/factors?factors=direction,instrument&min_n=5")
if "error" not in d:
    cells = d.get("cells", [])
    eur_sell = [c for c in cells if c.get("direction") == "SELL" and c.get("instrument") == "EUR_USD"]
    if eur_sell:
        check("EUR_USD SELL detected", True)
        check("EUR_USD SELL EV negative", eur_sell[0].get("ev", 0) < 0,
              f"EV={eur_sell[0].get('ev')}")
    else:
        check("EUR_USD SELL detected", False, "cell not found")

# Summary
print(f"\n=== Results: {len(PASSES)} passed, {len(ERRORS)} failed ===")
if ERRORS:
    print("\nFAILURES:")
    for e in ERRORS:
        print(f"  ❌ {e}")
    sys.exit(1)
else:
    print("\n✅ All checks passed. Factor decomposition engine is functional.")
    sys.exit(0)
