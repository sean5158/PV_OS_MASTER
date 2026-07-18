#!/bin/bash

echo "========== PV_OS CONTEXT =========="
cat PV_OS_MASTER_CONTEXT.md

echo ""
echo "========== PV_OS STATUS =========="
cat PV_OS_STATUS.md

echo ""
echo "========== PV_OS RECOVERY =========="
cat PV_OS_RECOVERY.md

echo ""
echo "========== PV_OS DEVELOPMENT LOG =========="
cat PV_OS_DEV_LOG.md

echo ""
echo "========== PROJECT STRUCTURE =========="
tree -L 2

echo ""
echo "========== GIT STATUS =========="
git status

echo ""
echo "========== GIT TAG =========="
git tag | tail -20

echo ""
echo "========== RECENT COMMITS =========="
git log --oneline -10
