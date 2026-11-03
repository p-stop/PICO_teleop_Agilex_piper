# A4-S graph、共享执行与多端点采集fake切片

日期：2026-10-16。状态：complete（本轮graph+单组多端点fake子集）。基线5191923及计划004/005未提交工作；不覆盖既有修改。

## 用户决策与目标

用户确认继续PICO双手柄→双Piper执行臂、双夹爪、三相机；底盘/升降固定。原负责人报告旧双臂VR效果不好、IK不佳且建议主从：这是使用经验，不是本次复现结果。当前采用本框架提供映射/IK、复用机器人ROS驱动的方向；主从保留可替换意图源。

先明确真实graph与数据/时序/打包细节，再抽象最小共性，做可运行多端点fake采集。采集/推理共用最终执行面；模型前处理、动作解码、chunk/截止期和任务效果仍需独立验证。物理模型、TCP、外参、按键配置缺项不静默猜测。

## 本切片交付与验收

1. docs/a4s-graph.md固定节点/边、四逻辑端点到两驱动批次、输入/反馈/三相机/记录、VR和策略的不同前半段及待核验项；ADR记录复用边界。
2. 独立版本的多端点fake配置/契约，不放宽M1固定图。N端点具名单位/坐标/限位、N驱动批次、执行组和具名观测；静态检查缺失/重复/资源冲突。
3. 单一fake执行入口：组授权/epoch、全批次先检查再下发、部分发送失败如实记录、迟到结果/接管/过期拒绝；teleop和stub-policy共用入口。手动clock不能作为真机watchdog。
4. 有界fake多相机与状态→流式MCAP，保留raw source、归一化意图、guard、命令批次/receipt/反馈，结束hash/计数；读回只验证文件，不创建设备。无真实IK、ROS命令或物理控制声称。
5. Windows单元/配置/集成、相关Linux隔离fake测试（若可用）及M1回归；更新状态/版本边界和checkpoint。不实现完整任意graph编排、真实策略、RTC/MPC或一次性全M2。

## checkpoint

完成[真实目标graph](../docs/a4s-graph.md)、ADR-0009、独立collection-plan/1与collection-event/1、四端点/两backend批次模板、单组lease/epoch/来源替换/全组预检及逐批次发送前复检、部分失败receipt和流式MCAP/独立读取。M1固定契约不变。只提供fake运行器，不将它误称真实graph编排、VR mapper或IK。

运行入口和审查顺序见[collection-review](../docs/collection-review.md)，证据见[验证报告](../docs/validation/2026-10-16-a4s-shared-execution.md)。Windows/Python3.11.12全套165项通过；Ubuntu24.04/Python3.12.3隔离全套165项通过，临时复制mcap1.5.0纯Python测试依赖，无安装/ROS/硬件访问；临时目录已清理。40项新增测试覆盖错误配置先于构造、单位/批次、全组拒绝、接管旧结果、超时、部分写入、记录失败、结束/完整性和单臂配置。

20步CLI产生394事件、两backend各20次fake执行、三camera共63帧，人工标签与stub-policy标签各10步；读回通过，outcome=complete。fault恢复后的episode仍aborted，独立读取器拒绝错误complete。快照缓存32；MCAP仍有索引元数据开销，不承诺任意长度/视频带宽。

构建/交付：sdist/wheel构建及排除检查通过；wheel含新模块和HTML，在源目录外通过collect-validate、collect-demo、collect-read与M1 validate。48份Markdown/214内部文件链接零问题，git diff --check通过。证据artifacts/2026-10-16-collection-release-check.json；当前源hash保存在artifacts/2026-10-16-collection-source-manifest.json。包metadata保持0.3.0，增量在CHANGELOG Unreleased，未推送/发布。

接续：持续真实观测/记录和输入质量→精确模型/joint order/TCP/双臂frame及按钮配置→框架VR映射与IK离线基准/shadow→设备本地时钟/watchdog/ROS命令代理→单臂/双臂明确范围运动与真实采集。缺失参数不猜。独立端点/重叠执行组、真实策略artifact/chunk/模型任务另验；本轮没有完成真正双臂遥操数采，未运行物理命令。
