#!/bin/bash

# =====================================
# PV_OS Backup Engine V1.0
# 自动备份系统
# =====================================


PROJECT_DIR="$HOME/PV_OS_MASTER"

DATE=$(date +"%Y-%m-%d_%H-%M-%S")


BACKUP_DIR="$PROJECT_DIR/backup/history/PV_OS_BACKUP_$DATE"

SNAPSHOT_FILE="$PROJECT_DIR/snapshots/PV_OS_SNAPSHOT_$DATE.tar.gz"


echo "================================="
echo "PV_OS Backup Start"
echo "Time: $DATE"
echo "================================="


mkdir -p "$BACKUP_DIR"


echo "1. Backup PV_OS 三件套"


cp "$PROJECT_DIR/backup/PV_OS_BACKUP_MAP_V1.0.md" \
"$BACKUP_DIR/"


cp "$PROJECT_DIR/backup/PV_OS_RULE_INDEX.md" \
"$BACKUP_DIR/"


cp "$PROJECT_DIR/backup/PV_OS_BUSINESS_TREE.md" \
"$BACKUP_DIR/"
cp "$PROJECT_DIR/backup/PV_OS_STATUS.md" \
"$BACKUP_DIR/"

if [ -f "$PROJECT_DIR/backup/PV_OS_CODEX_STATUS.md" ]; then

cp "$PROJECT_DIR/backup/PV_OS_CODEX_STATUS.md" \
"$BACKUP_DIR/"

fi


echo "2. Create Project Snapshot"


tar -czf "$SNAPSHOT_FILE" \
--exclude="snapshots" \
"$PROJECT_DIR"

echo "3. Backup chat history"

cp -r "$PROJECT_DIR/99_BACKUP_ENGINE/chat_history" \
"$BACKUP_DIR/"


echo "4. Update latest backup"


rm -rf "$PROJECT_DIR/backup/latest/*"


cp -r "$BACKUP_DIR/"* \
"$PROJECT_DIR/backup/latest/"


echo ""
echo "================================="
echo "PV_OS Backup Complete"
echo "Snapshot:"
echo "$SNAPSHOT_FILE"
echo "================================="
