#!/usr/bin/env bash
# PostToolUse Hook — 戦略関連ファイル編集時の検証リマインダ
# 戦略スコア/PROMOTE/DEMOTED/QUALIFIED変更を検知し、BT検証を強制
set -uo pipefail

# stdin から tool_input を読む
INPUT=$(cat 2>/dev/null || true)
FILE=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null || true)

# 戦略関連ファイルかどうか判定
IS_STRATEGY=0
if echo "$FILE" | grep -qE 'strategies/|demo_trader\.py'; then
    # 変更内容に戦略キーワードが含まれるか
    NEW_STR=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('new_string',''))" 2>/dev/null || true)
    if echo "$NEW_STR" | grep -qiE 'score|PROMOTE|DEMOTE|QUALIFIED|FORCE_DEMOTED|SENTINEL|LOT_BOOST'; then
        IS_STRATEGY=1
    fi
fi

if [[ "$IS_STRATEGY" == "1" ]]; then
    cat <<ENDJSON
{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"🚨 STRATEGY CHANGE DETECTED in $FILE\\n\\n検証必須 (lesson-tool-verification-gap + lesson-bt-before-deploy):\\n1. preprocess_bt_divergence() を実データで実行し、該当戦略×ペアのBT WR/EVを引用すること\\n2. 変更の根拠となるN/WR/EV/Kellyを明示すること\\n3. BT未検証の変更は原則禁止（Sentinel lotでの最小リスク化は例外）\\n4. 空結果が返った場合はパーサーバグを疑うこと"}}
ENDJSON
else
    echo '{}'
fi
