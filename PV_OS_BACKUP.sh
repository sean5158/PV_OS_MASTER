#!/bin/bash

# ==================================
# PV_OS ONE COMMAND BACKUP
# ==================================

PROJECT_ROOT=$(pwd)

DATE=$(date +"%Y-%m-%d_%H-%M-%S")

SNAPSHOT_NAME="PV_OS_SNAPSHOT_${DATE}.tar.gz"

echo "================================"
echo " PV_OS BACKUP START"
echo "================================"


# 1. 创建快照目录

mkdir -p snapshots


# 2. 创建完整快照

echo "[1/4] Creating snapshot..."

tar -czf snapshots/$SNAPSHOT_NAME \
00_SYSTEM \
01_PROJECT_MANAGEMENT \
02_DATA \
03_AI_AGENT \
04_CONTENT \
05_CUSTOMER_CRM \
05_CUSTOMER_LEADS \
09_AI_OPERATION \
10_AI_AUTOMATION_ENGINE \
PV_OS_*.md


echo "Snapshot created:"
echo $SNAPSHOT_NAME


# 3. 更新 latest

echo "[2/4] Updating backup/latest..."

mkdir -p backup/latest

cp -r 00_SYSTEM/PV_OS_* backup/latest/ 2>/dev/null


# 4. Git checkpoint

echo "[3/4] Git checkpoint..."

git add .

git commit -m "PV_OS auto backup $DATE"


echo "[4/4] Backup complete"


echo ""
echo "================================"
echo " PV_OS BACKUP COMPLETE"
echo "================================"

echo "Snapshot:"
echo $SNAPSHOT_NAME

echo "Git:"
git rev-parse --short HEAD

echo "================================"
