#!/bin/bash

# =====================================
# PV_OS MASTER BOOT V3
# AI Context Recovery System
# =====================================


PROJECT_ROOT="$HOME/PV_OS_MASTER"

cd "$PROJECT_ROOT" || exit


CONTEXT="00_SYSTEM/PV_OS_AI_CONTEXT.md"


DATE=$(date "+%Y-%m-%d %H:%M:%S")


echo ""
echo "================================"
echo " PV_OS MASTER BOOT V3"
echo "================================"


echo ""
echo "[1/7] Checking Core System"


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
echo "[2/7] Loading Design Decisions"


DESIGN_LOG=$(find 00_SYSTEM/PROJECT_MEMORY \
-name "PV_OS_DESIGN_DECISION_LOG*.md" \
| sort \
| tail -1)


if [ -f "$DESIGN_LOG" ]; then

echo "✓ $DESIGN_LOG"

else

echo "No Design Decision Log"

fi




echo ""
echo "[3/7] Scanning Agents"


AGENTS=$(find 03_AI_AGENT/agents \
-name "agent.yml")


echo "$AGENTS"



echo ""
echo "[4/7] Scanning Workflow"


WORKFLOWS=$(find 10_AI_AUTOMATION_ENGINE/workflows \
-type f)



echo "$WORKFLOWS"




echo ""
echo "[5/7] Reading Project Status"


STATUS=$(cat 00_SYSTEM/PV_OS_PROJECT_STATUS.md)




echo ""
echo "[6/7] Generating AI Context"



cat > "$CONTEXT" <<EOF


# PV_OS_AI_CONTEXT


更新时间:

$DATE



# 项目

PV_OS_MASTER



# 当前定位

光伏行业 AI 自动化运营系统。



# 当前系统状态


$STATUS




# PV_OS V2.0战略决策


设计文件:

$DESIGN_LOG




# 当前 Agents


$AGENTS




# 当前 Workflow


$WORKFLOWS




# AI执行规则


进入项目必须读取:


00_SYSTEM/PV_OS_DIRECTORY_MAP.md


00_SYSTEM/PV_OS_AI_RULES.md


00_SYSTEM/PV_OS_PROJECT_STATUS.md


00_SYSTEM/PROJECT_MEMORY/PV_OS_DESIGN_DECISION_LOG*.md




禁止:


- 修改无关文件

- 偏离业务方向

- 编造数据

- 创建未定义目录



# 下一步


继续当前 Phase 开发。


EOF




echo ""
echo "[7/7] Context Generated"


echo "$CONTEXT"



echo ""
echo "================================"
echo " PV_OS READY V3"
echo "================================"

