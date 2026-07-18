#!/bin/bash

# =====================================
# PV_OS MASTER BOOT V3
# Context Recovery System
# =====================================


PROJECT_ROOT="/Users/liudesean/PV_OS_MASTER"

cd "$PROJECT_ROOT" || exit


CONTEXT="00_SYSTEM/PV_OS_AI_CONTEXT.md"


DATE=$(date "+%Y-%m-%d %H:%M:%S")


echo "================================"
echo " PV_OS MASTER BOOT V3"
echo "================================"



echo ""
echo "[1/6] Checking Core Rules"



CORE_FILES=(

"PV_OS_MASTER_CONTEXT.md"

"PV_OS_ARCHITECTURE.md"

"PV_OS_AI_RULES.md"

"PV_OS_DIRECTORY_MAP.md"

"PV_OS_PROJECT_STATUS.md"

)



for f in "${CORE_FILES[@]}"
do

if [ -f "00_SYSTEM/$f" ]; then

echo "✓ $f"

else

echo "✗ Missing $f"

fi

done



echo ""
echo "[2/6] Loading Design Decision"



DECISION_FILE="00_SYSTEM/PROJECT_MEMORY/PV_OS_DESIGN_DECISION_LOG_2026-07-15.md"


if [ -f "$DECISION_FILE" ]; then

echo "✓ PV_OS V2.0 Decision Loaded"

else

echo "✗ Missing Design Decision"

fi



echo ""
echo "[3/6] Scanning Agents"



AGENTS=$(find 03_AI_AGENT/agents -name "agent.yml")


echo "$AGENTS"



echo ""
echo "[4/6] Scanning Workflow"



WORKFLOWS=$(find 10_AI_AUTOMATION_ENGINE/workflows -type f)


echo "$WORKFLOWS"



echo ""
echo "[5/6] Generating Full AI Context"



STATUS=$(cat 00_SYSTEM/PV_OS_PROJECT_STATUS.md)


DECISION=$(cat "$DECISION_FILE" 2>/dev/null)



cat > "$CONTEXT" <<EOF


# PV_OS_AI_CONTEXT V3


更新时间:

$DATE



# 项目

PV_OS_MASTER



# 当前定位

光伏行业 AI 自动化运营系统



# 系统规则

必须遵守：

00_SYSTEM/PV_OS_AI_RULES.md

00_SYSTEM/PV_OS_DIRECTORY_MAP.md

00_SYSTEM/PV_OS_ARCHITECTURE.md



# PV_OS V2.0 战略决策


$DECISION



# 当前项目状态


$STATUS



# Agents


$AGENTS



# Workflow


$WORKFLOWS



# AI执行要求


禁止：

- 修改无关文件
- 偏离PV_OS业务方向
- 编造不存在的数据


继续当前开发阶段。


EOF



echo ""
echo "[6/6] Context Generated"


echo "$CONTEXT"



echo ""
echo "================================"
echo " PV_OS READY V3"
echo "================================"
