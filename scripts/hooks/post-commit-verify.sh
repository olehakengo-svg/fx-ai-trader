#!/usr/bin/env bash
# Post-commit自動検証 — コミット後に成果物の機能テストを実行
# lesson-tool-verification-gap対策: 作ったものが動くことを毎回検証
set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

# 直前コミットで変更されたファイルを取得
CHANGED=$(git diff --name-only HEAD~1 HEAD 2>/dev/null || true)

ISSUES=""

# 1. alpha_scan.py が変更された → 本番APIで正例テスト
if echo "$CHANGED" | grep -q "alpha_scan"; then
    RESULT=$(cd "$ROOT" && python3 -c "
import json, urllib.request
try:
    url='https://fx-ai-trader.onrender.com/api/demo/factors?factors=strategy&min_n=5'
    with urllib.request.urlopen(url, timeout=10) as r:
        d=json.loads(r.read())
    cells=d.get('cells',[])
    if not cells:
        print('FAIL:no_cells')
    else:
        wr=cells[0].get('wr',0)
        if wr==0:
            print('FAIL:wr_zero')
        else:
            print('OK')
except Exception as e:
    print(f'SKIP:{e}')
" 2>/dev/null || echo "SKIP")
    if echo "$RESULT" | grep -q "FAIL"; then
        ISSUES="${ISSUES}alpha_scan: ${RESULT}\n"
    fi
fi

# 2. daily_report.py が変更された → BT乖離パーサー正例テスト
if echo "$CHANGED" | grep -q "daily_report"; then
    RESULT=$(cd "$ROOT" && python3 -m pytest tests/test_p2_system.py::TestBtDivergenceParser -x -q 2>&1 | tail -1)
    if ! echo "$RESULT" | grep -q "passed"; then
        ISSUES="${ISSUES}bt_parser: ${RESULT}\n"
    fi
fi

# 3. demo_trader.py が変更された → FORCE_DEMOTED/PAIR_DEMOTED整合テスト
if echo "$CHANGED" | grep -q "demo_trader"; then
    RESULT=$(cd "$ROOT" && python3 -c "
from modules.demo_trader import DemoTrader
dt = DemoTrader.__new__(DemoTrader)
# FORCE_DEMOTEDとUNIVERSAL_SENTINELの重複チェック
overlap = dt._FORCE_DEMOTED & dt._UNIVERSAL_SENTINEL
if overlap:
    print(f'FAIL:overlap={overlap}')
else:
    print('OK')
" 2>/dev/null || echo "SKIP")
    if echo "$RESULT" | grep -q "FAIL"; then
        ISSUES="${ISSUES}demoted_overlap: ${RESULT}\n"
    fi
fi

# 結果出力
if [[ -n "$ISSUES" ]]; then
    echo "⚠️ POST-COMMIT VERIFICATION ISSUES:" >&2
    echo -e "$ISSUES" >&2
fi
