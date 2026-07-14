#!/bin/bash

# =====================================
# PV_OS Restore Engine V1.3
# =====================================


PROJECT_DIR="$HOME/PV_OS_MASTER"

echo ""
echo "================================="
echo "        PV_OS RESTORE REPORT"
echo "================================="
echo ""


echo "【最新备份版本】"

LATEST_BACKUP=$(ls -td "$PROJECT_DIR/backup/history/"* | head -1)

echo "$LATEST_BACKUP"


echo ""
echo "---------------------------------"


echo "【当前项目状态】"

if [ -f "$PROJECT_DIR/backup/PV_OS_STATUS.md" ]; then

cat "$PROJECT_DIR/backup/PV_OS_STATUS.md"

else

echo "未找到 PV_OS_STATUS.md"

fi


echo ""
echo "---------------------------------"


echo "【最近开发日志】"


LATEST_LOG=$(find "$PROJECT_DIR/99_BACKUP_ENGINE/chat_history" \
-name "PV_OS_DEV_LOG.md" \
| sort \
| tail -1)


if [ -f "$LATEST_LOG" ]; then

echo "$LATEST_LOG"

echo ""

cat "$LATEST_LOG"

else

echo "暂无开发日志"

fi


echo ""
echo "================================="
echo "       PV_OS RESTORE COMPLETE"
echo "================================="
