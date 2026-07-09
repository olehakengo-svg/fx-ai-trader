#!/usr/bin/env bash
# Post-commit自動検証 — コミット後に成果物の機能テストを実行
# lesson-tool-verification-gap対策: 作ったものが動くことを毎回検証
#
# NOTE (2026-07-09, rule:R3): python コードは必ず quoted heredoc (<<'PYEOF') で渡す。
# `python3 -c "..."` (bash double quote) は python コード内の `"` が bash 文字列を
# 途中終端し、截断コードの SyntaxError が `|| echo SKIP` に吸収されて check が
# silent 不発になる (check #3 がこのパターンで一度も実行完了していなかった)。
# inline `python3 -c "..."` への書き戻し禁止。
set -uo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"

# 直前コミットで変更されたファイルを取得
# POST_COMMIT_VERIFY_CHANGED: テスト用シーム — hook を commit なしで red→green 検証する
CHANGED="${POST_COMMIT_VERIFY_CHANGED:-$(git diff --name-only HEAD~1 HEAD 2>/dev/null || true)}"

ISSUES=""

# 1. alpha_scan.py が変更された → 本番APIで正例テスト
if echo "$CHANGED" | grep -q "alpha_scan"; then
    RESULT=$(cd "$ROOT" && python3 - 2>/dev/null <<'PYEOF'
import json, urllib.request
try:
    url = 'https://fx-ai-trader.onrender.com/api/demo/factors?factors=strategy&min_n=5'
    with urllib.request.urlopen(url, timeout=10) as r:
        d = json.loads(r.read())
    cells = d.get('cells', [])
    if not cells:
        print('FAIL:no_cells')
    elif cells[0].get('wr', 0) == 0:
        print('FAIL:wr_zero')
    else:
        print('OK')
except Exception as e:
    # network/API 障害は環境要因 — SKIP (理由付き)
    print('SKIP:' + repr(e))
PYEOF
)
    RESULT="${RESULT:-FAIL:verify_no_output}"
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

# 3. demo_trader.py が変更された → tier set 整合テスト
# この check に正当な SKIP 経路はない (network 非依存) — import 失敗も FAIL で可視化する
#
# assertion 張替え (2026-07-09, rule:R3): 旧 assertion (FORCE_DEMOTED∩SENTINEL /
# PAIR_PROMOTED-strategy∩SENTINEL) は sentinel 優先時代 (2026-04-14) の遺物。
# 現行設計では両者は意図的共存 — demote = live 遮断 + sentinel shadow 蓄積継続、
# PAIR_PROMOTED は _is_promoted_ex/_resolve_tier の両方で SENTINEL より先に評価
# (demo_trader.py 2026-07-02 コメント「PAIR_PROMOTED overrides _UNIVERSAL_SENTINEL
# shadow eligibility / Shadow accumulation continues (principle 3)」参照)。
# 現行設計で実害のある overlap は以下の 2 つ:
#   a) PAIR_PROMOTED∩PAIR_DEMOTED (同一セル) — _is_promoted_ex は PAIR_DEMOTED を
#      先に評価するため、昇格セルが silent に shadow 化され死ぬ
#   b) ELITE_LIVE∩FORCE_DEMOTED — live gate はブロック vs _resolve_tier は
#      ELITE_LIVE を先に返す = gate と write-path の矛盾 (v9.0 trendline_sweep 前例)
if echo "$CHANGED" | grep -q "demo_trader"; then
    RESULT=$(cd "$ROOT" && python3 - 2>/dev/null <<'PYEOF'
try:
    from modules.demo_trader import DemoTrader
    dt = DemoTrader.__new__(DemoTrader)
    pp_pd = dt._PAIR_PROMOTED & dt._PAIR_DEMOTED
    elite_fd = dt._ELITE_LIVE & dt._FORCE_DEMOTED
    msg = []
    if pp_pd:
        msg.append('PAIR_PROMOTED&PAIR_DEMOTED=' + repr(sorted(pp_pd)))
    if elite_fd:
        msg.append('ELITE_LIVE&FORCE_DEMOTED=' + repr(sorted(elite_fd)))
    if msg:
        print('FAIL:' + '; '.join(msg))
    else:
        print('OK')
except Exception as e:
    print('FAIL:verify_error:' + repr(e))
PYEOF
)
    RESULT="${RESULT:-FAIL:verify_no_output}"
    if echo "$RESULT" | grep -q "FAIL"; then
        ISSUES="${ISSUES}demoted_overlap: ${RESULT}\n"
    fi
fi

# 結果出力
if [[ -n "$ISSUES" ]]; then
    echo "⚠️ POST-COMMIT VERIFICATION ISSUES:" >&2
    echo -e "$ISSUES" >&2
fi
