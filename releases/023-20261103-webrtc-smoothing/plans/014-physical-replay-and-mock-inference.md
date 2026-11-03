# 014：真机轨迹回放与假模型推理端

2026-10-20，complete（native短轨迹真机＋fake HTTP推理切片）。用户明确要求真机轨迹回放，已确认在现场可配合；假模型先用fake设备验证。新SSH配置已连通，初始机器人current=013，8445/8446无服务。

范围与顺序：

1. 提取共同的具名关节/夹爪候选动作执行session，复用LiveGateway和PiperROSBackend唯一写路径。不改遥操采集行为、不直接调用SDK。
2. 轨迹源读取saved+QC通过的episode，只用确认发布目标；配置选择片段、初始目标来源、时间倍率。先平滑对齐起始关节，夹爪目标明确，未知不猜，过迟停止而非突发补发。
3. 推理源采用异步单请求worker和具名chunk协议；mock观察状态与三路fake RGB，输出joint_absolute；检查请求/epoch、观测年龄、时序、超时、队列耗尽、取消与异常。模型不持有设备capability。
4. 配置/CLI、fake端到端及故障测试→双平台测试→机器人隔离部署/只读预检→现场确认短轨迹→反馈与日志验收。
5. 更新操作手册、ADR、状态和可恢复checkpoint；保留旧数据/部署与日志。没有完整模型/ZeroWAM、任意图引擎、LeRobot writer或新训练任务。

验收：轨迹来源/hash/片段/目标语义可审查，起始对齐和正常完成/停止有日志与实际反馈证据；假模型正常chunk执行、慢结果拒绝/异常/耗尽停机、旧epoch不得执行，后台线程不阻塞本地watchdog，退出清理。报告Windows/fake与Ubuntu/物理的证据级别，不能互相代替。

设计决策：部署/设备配置与workflow source配置分离；本轮固定native joint_absolute执行面，无坐标变换/IK。物理回放需要当前机器与源model的URDF hash/base/tip/joint顺序一致，不以14维相同作为兼容依据。原生夹爪目标以m，不把反馈作为未知初始action。现场首测只取已保存第二集的短片段，具体动作范围先只读统计再告知操作者。

最终checkpoint：已实现workflow.py具名source/共同session、workflow_runner.py原生绑定、mock_policy_server.py独立HTTP服务；新增workflow-session/1配置和mock joint图，旧采集不变。fake与物理均通过唯一网关，native回放不需要VR/IK/相机，model worker无硬件写权限。物理CLI需要deployment和--execute，check-only不构建设备。

测试：Windows278过/10skip、Ubuntu291过（localhost ROS，无设备）；新增17项测试。Ubuntu首轮fixture环境缺artifacts父目录，已更正并保存失败收据。独立进程HTTP：正常COMPLETED，注入模型HTTP422为FAULT/退出码3，均清理无错；日志`runs/014-20261020-offline`。

物理验收：用户再次确认具体“4秒全零对齐＋第二集前3秒回放，播放恢复闭合夹爪”已准备好，随后确认“双臂正常运动并停住，无异常”。实际对齐4.501秒、播放3.000911秒、450命令集合、两侧各508条反馈、零guard拒绝/清理错误、双驱动退出0；源hash不变。20%原生速度未改，截点最大跟踪差左.098176/right.051588rad，不能声称精度复现。首3秒夹爪一直闭合，不覆盖开合变化。证据`physical-replay-validation-014.json`及`runs/replay-014-physical-01`。

部署current=`releases/014-20261020-native-validated`，保留旧013与release-manifest.pre-014.json；机器session/deployment未改，新增profiles/replay.validation014.json可复现本次片段。源码树`380ee1788a47160a48382610fc8826ebc6996ef4b89ec25d64eed7ef80014248`；被测试归档`014-validated.zip` SHA256 `6b36bd5ac92e817aff9e13b842a32ab728bcb408446865efea931e410fdbb88d`。最终文档归档/包收据另存artifacts/preflight/014-final-package.json和机器人release-manifest，源码树不变。物理会话与假模型服务已退出；后续动作不自动继续。

已更新操作手册、ADR0016、architecture v0.16、project-status及验证记录。后续：较慢倍率/更长片段的跟踪测量与终点稳定语义、真实观测源与策略adapter、GPU/ZeroWAM协议；不是本轮已完成内容。整体图解释器、LeRobot writer仍未实现。
