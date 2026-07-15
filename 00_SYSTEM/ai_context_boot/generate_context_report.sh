#!/bin/bash

OUTPUT="PV_OS_AI_CONTEXT_REPORT.md"

echo "# PV OS AI CONTEXT REPORT" > $OUTPUT

echo "" >> $OUTPUT

echo "更新时间:" >> $OUTPUT
date >> $OUTPUT

echo "" >> $OUTPUT

echo "## 项目目标" >> $OUTPUT

echo "中国城市家庭光伏 AI 主动获客系统" >> $OUTPUT


echo "" >> $OUTPUT

echo "## 业务边界" >> $OUTPUT

echo "" >> $OUTPUT

echo "目标客户:" >> $OUTPUT

echo "- 城市家庭光伏" >> $OUTPUT
echo "- 别墅" >> $OUTPUT
echo "- 叠拼" >> $OUTPUT
echo "- 花园洋房" >> $OUTPUT
echo "- 高价值住宅" >> $OUTPUT
echo "- 小商业" >> $OUTPUT


echo "" >> $OUTPUT

echo "禁止方向:" >> $OUTPUT

echo "- 农村光伏" >> $OUTPUT
echo "- 大型工商业光伏" >> $OUTPUT
echo "- 地面电站" >> $OUTPUT
echo "- 供应链客户" >> $OUTPUT


echo "" >> $OUTPUT

echo "## 数据平台" >> $OUTPUT

echo "- 抖音" >> $OUTPUT
echo "- 快手" >> $OUTPUT
echo "- 小红书" >> $OUTPUT
echo "- 视频号" >> $OUTPUT


echo "" >> $OUTPUT

echo "## 系统规则" >> $OUTPUT

echo "开发前必须读取 00_SYSTEM 规则文件" >> $OUTPUT

echo "不重复创建已有模块" >> $OUTPUT

echo "优先读取已有设计文件" >> $OUTPUT


echo "" >> $OUTPUT

echo "## 当前状态" >> $OUTPUT

cat PV_OS_CURRENT_STATE.md >> $OUTPUT


echo ""

echo "Generated:"
echo $OUTPUT
