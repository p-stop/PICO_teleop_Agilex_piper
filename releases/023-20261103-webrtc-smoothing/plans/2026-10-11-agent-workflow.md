# AI开发协作与交接准备

日期：2026-10-11。状态：已完成文档准备；范围为协作建议、agent入口、任务/验证模板和首切片实施计划。本轮不开始runtime实现，不创建新聊天或worktree，不连接设备。

## 已检查的基线

- AGENTS.md、architecture.md v0.5、project-status.md、现有ADR与跨机开发说明。
- 仓库只有14份Markdown文档，无实现、依赖清单、测试或CI；Git尚无提交，现有文件未跟踪。
- 已核对官方OpenAI的Codex提示、长任务计划及精简仓库指令建议；协作分工是针对本项目的建议，不是产品强制规则。

## 交付步骤

1. 为新agent提供短入口和按任务阅读的文档路由，保持架构/状态唯一事实来源。
2. 定义对话粒度、共享接口修改、独立checkout、跨机验证及交接方式。
3. 创建任务计划和验证报告模板，明确证据级别与未执行状态。
4. 把首个fake控制/记录/回放/stub切片写成可接续实施的计划，保留少量实施时决策。
5. 更新AGENTS.md导航、README和项目状态；检查文档链接与一致性。

## 完成标准

新对话可以仅凭仓库入口和指定计划识别当前状态、开始范围内实现、运行所需验证并留下可审计交接。文件中的示例命令不得被误读为已经存在的CLI；没有机器人运动授权被隐含赋予。

## 完成记录

- 新增agent-onboarding、ai-development-workflow、任务和验证报告模板及M1首切片计划；根AGENTS/README/status同步。
- M1计划仍为proposed，所有实现与功能测试未执行；本计划完成只代表协作文档准备完成。
- 静态检查：20份Markdown、49个内部链接、代码围栏、UTF-8替换字符、architecture/status版本一致性，0问题。
- 未运行unit/integration/config测试：仓库仍无实现和测试。未创建聊天/agent/worktree/commit，未连接远端或机器人。
