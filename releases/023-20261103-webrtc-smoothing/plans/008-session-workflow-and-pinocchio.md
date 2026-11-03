# 遥操 session 状态机、Pinocchio 与固定 VR 画面

2026-10-16；complete（自由遥操切片，非原始episode采集）。沿用此前未提交源码，不重置用户修改。

## 用户目标与确认

命令启动→设备自检→网页/VR→STANDBY A回home→READY A开始→TELEOP侧握跟随/扳机夹爪/A结束→STANDBY；退出VR暂停。未来采集增加REVIEW A保存/X丢弃，本轮不伪造录像/episode保存。用户已确认现场可配合、两臂home均六关节全0、home不改变夹爪开口。取消人为10cm/0.6rad测试边界，保留硬件关节范围、控制权和通信有效性。此前无限幅/100%物理启动曾被自动审批拒绝，不绕过该拒绝；新的物理测试按具体home/夹爪/小幅跟随步骤另验证，驱动速度沿用20%，不启动100%。

## 实现与验收

1. 阅读架构/状态/旧代码与QuestArm参考：借鉴上一解热启动、平滑残差、反馈home到位、状态/驱动分层；不复制固定TCP/坐标、自动夹爪关闭或未检查的旧服务。
2. Pinocchio FK/雅可比/SE3；SciPy bounded least_squares（现有Pin4.0/SciPy1.18；无CasADi绑定）。每臂独立求解进程、最新目标、代次/离合token，主线程不等待求解；保留旧纯标准库模型用于原测试兼容，真实v2 session不用其IK。
3. 独立session状态机、按键上升沿、异步home插值+反馈settle、暂停/恢复/停止清理；HTTP输入、控制循环、ROS、视频/日志分开。慢/失效结果不能复活旧会话。
4. Piper边界复用现有驱动，项目包装器覆写会自动关爪的使能入口，验证源码hash；home/保持消息省略夹爪，显式扳机目标才命令夹爪。夹爪范围按已审计SDK协议/现场反馈明确配置。
5. VR在local-floor里固定大主屏，初次进入按头部位置/yaw摆屏；头动只改变观看方向，旁边腕屏与上下HUD可通过转头/抬低头看到。状态、按键说明、相机配置/实时FPS；episode数仅在实际采集实现后显示。
6. 单元/fake、Linux真实Pinocchio离线、生命周期/信号测试先通过；现场验证A流程、双侧握/扳机、退出VR暂停。报告验证范围与退出状态，不声称完整数采已完成。

## checkpoint

实现已落地：Pinocchio模型/每臂求解进程、session状态机、checked驱动包装、ROS夹爪可选目标、CLI启动器和模块化Three.js网页。Windows完整194通过/1跳过；Ubuntu初版全套196通过，最后A修复相关33通过；JS语法通过。现有Pin4.0/SciPy1.18/ROS Jazzy，未安装系统包或改供应商源码。

远端根目录 `/home/ros/robot-infra-runs/008-session-20261016`：源码source，离线测试依赖testdeps，本地设备profile和camera-profile，首轮stack-01六子进程均退出0、journal-summary已写；目前stack-02监督器元数据supervisor-02.json（启动PID15405，不能盲信PID，操作前核对/proc cmdline/cwd），ROS domain64，HTTPS8445，20分钟定时。停止用该监督器SIGINT，仅清理其子进程。

现场用户确认固定大屏/腕屏/HUD可见；首个A被先前页面transport_error暂停消耗为resume-only，已定位按钮right4实际到达。改为PAUSED按阶段执行A动作并补2项回归测试，部署session008b。用户随后确认“双臂成功回位，完美”；日志HOMING→READY4.52s，两侧q全0，无guard拒绝，home无夹爪目标，反馈开口保持原值。当前等待现场验证第二次A开始、双侧握位置/朝向、扳机开合、A结束和退出/重进暂停。未宣称这些已验收，未完成原始episode。

后续现场用户确认完整流程“一切都完美”，包括两臂位置/朝向/夹爪/松键/A结束；日志trial1结束→STANDBY、再次home→READY、退出→PAUSED。2578个IK结果中2121收敛/457best-effort，中位2.45ms/最大7.05ms，0guard拒绝（不是任务级精度基准）。用户要求反转扳机，已增加每臂gripper.trigger_pressed，当前均open=按下开/松开关，模板/HTML/HUD一致，补双极性/无侧握不写夹爪测试。

最新版部署stack-03，supervisor-03.json（启动PID16027，须核对/proc），前两轮六子进程均正常退出0。现场最后验证URL ?v=session008c 已发出，等待确认再停止stack-03。最终Windows196通过/1跳过，Ubuntu200通过；uv离线wheel/sdist构建、资源许可证/排除与wheel CLI smoke通过。设备仍source运行，不冒充wheel安装验收。

操作说明docs/teleop-session.md，ADR0011，验证报告docs/validation/2026-10-16-a4s-session.md，状态/架构/入口已更新。结束前补最终清理状态和预览hash/QC；不推送、不创建Git远程。下一步正式采集独立接episode REVIEW和原始MCAP。

最终checkpoint：用户确认新版扳机“完美符合预期”。stack-03正常退出六子进程全0，监督器/六子进程/三个求解相关后代均已无活跃残留，HTTPS8445已关闭。三轮journal finalize/summary均完整且error=null/writer_stopped=true；22028张预览全数路径/文件/hash通过。最后一轮左右夹爪目标/反馈覆盖闭合至全开，home不写夹爪。日志final-session-report.json在设备根目录，本地忽略artifact有副本。此计划验收完成；未录原始MCAP、未接策略、未发布Git远程。再次启动须现场用户授权，按新profile/CLI步骤进行。
