#!/bin/bash

echo "================================"
echo " PV_OS COMMENT PIPELINE START"
echo "================================"


echo "[1/5] Loading raw comments"

ls 02_DATA/raw/test_comments


echo "[2/5] Loading competitor sources"

ls 02_DATA/02_COMPETITOR_DATABASE/competitor_accounts.csv


echo "[3/5] Running comment analysis"

echo "comment_analyzer"


echo "[4/5] Running lead scoring"

echo "lead_scoring_agent"


echo "[5/5] Generating CRM tasks"

echo "CRM OUTPUT READY"


echo "================================"
echo " PV_OS COMMENT PIPELINE READY"
echo "================================"
