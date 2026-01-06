#!/bin/bash
# 日志分析脚本 - 快速过滤错误和关键事件
# 使用方法: ./scripts/filter_logs.sh [error|critical|module:xxx|agent:yyy]

LOG_FILE="${LOG_FILE:-./logs/app.log}"

case "$1" in
  "error")
    jq 'select(.level=="ERROR" or .level=="CRITICAL")' "$LOG_FILE"
    ;;
  "critical")
    jq 'select(.level=="CRITICAL")' "$LOG_FILE"
    ;;
  module:*)
    MODULE="${1#module:}"
    jq "select(.module==\"$MODULE\")" "$LOG_FILE"
    ;;
  agent:*)
    AGENT="${1#agent:}"
    jq 'select(.extra.agent_id == "'"$AGENT"'")' "$LOG_FILE"
    ;;
  "exception")
    jq 'select(has("exception"))' "$LOG_FILE"
    ;;
  "today")
    TODAY=$(date -I)
    jq 'select(.timestamp | startswith("'$TODAY'"))' "$LOG_FILE"
    ;;
  *)
    echo "用法: $0 [error|critical|module:xxx|agent:yyy|exception|today]"
    echo "示例:"
    echo "  $0 error          # 只看错误和严重错误"
    echo "  $0 critical       # 只看严重错误"
    echo "  $0 module:asyncio # 按模块过滤"
    echo "  $0 agent:agent-123 # 按 Agent ID 过滤"
    echo "  $0 exception      # 只看包含异常的日志"
    echo "  $0 today          # 只看今天的日志"
    exit 1
    ;;
esac
