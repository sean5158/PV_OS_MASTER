# PV_OS_COMMAND_REFERENCE

版本:
V1.1

项目:
PV_OS_MASTER


用途:
PV_OS 系统操作命令统一说明。


---

# 一、AI上下文加载

命令:

./00_SYSTEM/ai_context_boot/load_context.sh


用途:

- AI跑偏校准
- 开始开发前
- 更换AI工具


---

# 二、一键备份

官方命令:

./PV_OS_BACKUP.sh


用途:

修改重要内容前：

- Agent
- Workflow
- 系统结构


---

# 三、备份引擎

命令:

./99_BACKUP_ENGINE/pvbackup.sh


用途:

- 历史备份
- 快照
- chat_history保存


---

# 四、恢复检查

命令:

./99_BACKUP_ENGINE/pvrestore.sh


用途:

查看：

- 最新备份
- 当前状态
- 开发日志


---

# 五、系统启动检查

命令:

./99_BACKUP_ENGINE/pv_bootstrap.sh


用途:

- 核心文件检查
- Agent扫描
- Workflow扫描


---

# 六、快速判断


AI跑偏:

使用:

./00_SYSTEM/ai_context_boot/load_context.sh


修改前:

使用:

./PV_OS_BACKUP.sh


系统异常:

使用:

./99_BACKUP_ENGINE/pvrestore.sh


检查系统:

使用:

./99_BACKUP_ENGINE/pv_bootstrap.sh


---

END
