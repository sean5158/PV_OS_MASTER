#!/bin/bash

echo "================================"
echo "PV OS AI CONTEXT BOOT"
echo "================================"

echo ""

FILES=(
"00_SYSTEM/PV_OS_MASTER_CONTEXT.md"
"00_SYSTEM/PV_OS_AI_RULES.md"
"00_SYSTEM/PV_OS_GOVERNANCE_RULES.md"
"00_SYSTEM/PV_OS_CODEX_RULES.md"
"PV_OS_CURRENT_STATE.md"
)

echo "Loading Context:"

for file in "${FILES[@]}"
do
    if [ -f "$file" ]; then
        echo "✓ $file"
    else
        echo "✗ Missing $file"
    fi
done


echo ""

echo "Business Boundary:"
echo "✓ 中国城市家庭光伏"
echo "✓ 别墅/叠拼/高价值住宅"
echo "✓ 国内视频平台"
echo "✗ 农村光伏"
echo "✗ 大型工商业"


echo ""

echo "Generating Context Report..."

./00_SYSTEM/ai_context_boot/generate_context_report.sh



echo "PV OS AI CONTEXT READY"
