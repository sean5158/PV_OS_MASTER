











#!/bin/bash


PROJECT_ROOT="/Users/liudesean/PV_OS_MASTER"

cd "$PROJECT_ROOT" || exit


CONTEXT="00_SYSTEM/PV_OS_AI_CONTEXT.md"


echo "================================"
echo " PV_OS MASTER BOOT V2"
echo "================================"


DATE=$(date "+%Y-%m-%d %H:%M:%S")


echo ""
echo "[1/6] Checking Core System"


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
echo "[2/6] Scanning Agents"


AGENTS=$(find 03_AI_AGENT/agents -name "agent.yml")


echo "$AGENTS"



echo ""
echo "[3/6] Scanning Automation"


WORKFLOWS=$(find 10_AI_AUTOMATION_ENGINE/workflows -type f)


echo "$WORKFLOWS"



echo ""
echo "[4/6] Reading Project Status"




STATUS=$(cat 00_SYSTEM/PV_OS_PROJECT_STATUS.md)




echo "$PHASE"



echo ""
echo "[5/6] Generating AI Context"



cat > "$CONTEXT" <<EOF

# PV_OS_AI_CONTEXT

更新时间:

$DATE


## 项目

PV_OS_MASTER


## 定位

光伏行业 AI 自动化运营系统




## 项目状态

$STATUS


## Agents

$AGENTS


## Automation Workflow

$WORKFLOWS


## AI执行规则

必须读取：

00_SYSTEM/PV_OS_DIRECTORY_MAP.md

00_SYSTEM/PV_OS_AI_RULES.md

00_SYSTEM/PV_OS_PROJECT_STATUS.md


禁止：

- 修改无关文件
- 偏离业务方向
- 编造数据


## 下一步

继续当前 Phase 开发。


END

EOF



echo ""
echo "[6/6] Context Generated"

echo "$CONTEXT"


echo ""
echo "================================"
echo " PV_OS READY V2"
echo "================================"



