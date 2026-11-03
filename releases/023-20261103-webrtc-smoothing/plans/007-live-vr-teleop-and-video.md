# 双臂真机WebXR遥操、三相机显示与数据流说明

日期：2026-10-16。状态：complete（有界首版位置遥操与图解范围；完整M2未完成）。用户明确请求部署、真机运动及手柄遥操，并确认在现场可观察/急停；涉及当前静态双Piper，不涉及底盘/升降或其他机器。后续要求完全放开限制的启动被自动审批拒绝；改为明确有界的10cm/0.6rad/0.4rad/s/20%速度配置完成验证。

## 交付与顺序

1. 核对在线主机、现有进程/CAN、模型/依赖和驱动初始化/停止；不覆盖旧工程。
2. 图形化graph与通俗数据流报告，明确当前实现/待验、视频与控制/记录的不同路径。
3. 框架侧模型/FK/IK、输入映射/离合、组所有权/时效与最终检查，配置化ROS设备边界；fake/离线/shadow先验证。
4. 独立部署三路相机及HTTPS/WebXR。固定D455作为用户所称头部/主视角，居中放大；双腕小画面左右摆放，桌面与immersive VR均显示；记录并显示输入/反馈/视频新鲜度。
5. 现场配合下先小幅关节测试/停止验证，再手柄位置跟随；坐标/按钮映射先展示并确认，不猜缺失变换。逐项保存命令/反馈/输入证据，不能用“已发送”冒充真实执行。
6. 回归测试、更新状态/运行与停止文档；只停止本项目创建的进程，保留用户数据与现有环境。未测能力保持未验证。

## checkpoint

- 已完成：现场身份/源码/依赖复核、框架FK与Pinocchio/SDK对比、局部IK影子验证、所有权/guard/watchdog、Piper ROS适配器、三相机HTTPS/immersive显示、graph SVG与通俗报告。未另发固定关节demo；以经网关的左侧小位移VR跟随作为首个小幅运动测试，然后扩大到双臂。
- 用户指定scale=1，自行小幅核验候选坐标；button1侧握离合、位置跟随、朝向保持。用户最终确认两个臂可动、上下左右初步正确、松键符合预期。实际记录与FK独立证明双臂变化；不能仅以published receipt称已执行。
- 修复部署OpenCV/NumPy ABI冲突（改现成Pillow）、PICO旧页面/进入VR稳定时机、右侧近零位种子微小越限、可见性误标错误、日志失败仍尝试保持、ROS退出context先关闭导致日志摘要缺失。
- Windows/Python3.11与Ubuntu/Python3.12隔离全套各182通过；含17新增项。ROS域65、不启动硬件驱动，定时/SIGINT退出均exit0，summary/finalize正常且零命令。物理三轮原件摘要缺失，保持诊断不完整状态，不补造complete。完整启动器加入但未另跑整栈物理验收。
- 现场原件 `/home/ros/robot-infra-runs/007-probe-20261016T142159Z`；三轮JSONL与30746张预览原件保留。全部JPEG存在/hash检查通过；21.5MB抽样图+全日志封存包已下载本地ignored artifacts。source/episode hash与表格见[现场报告](../docs/validation/2026-10-16-a4s-live-control.md)。所有8个临时项目PID已不存在，撤权/保持后停止，无自动失能或回零。
- 报告：[graph与通俗数据流](../docs/a4s-dataflow.md)、[部署与停止](../docs/live-teleop.md)、[ADR-0010](../docs/adr/0010-live-gateway-and-position-teleop.md)。Git baseline5191923未变，新增源码未提交，无远程发布，无厂商目录/系统依赖修改。

## 接续

最终带文档的源码快照已在机器人端独立解包至 `/home/ros/robot-infra-runs/007-probe-20261016T142159Z/final-source/robot_infra-0.3.0`；`profiles/local/robot.live.json`与`robot.realsense.json`已准备，离线模型/profile校验通过。启动器参数按部署手册，证书仍使用该轮根目录下tls文件，不复制私钥。源码包hash、端口关闭及无服务启动证据在本地 `artifacts/preflight/007-final-deployment.json`；8445/18445均关闭。Windows sdist/wheel构建、模块独立导入、两种fake配置wheel验证、无关文件排除均通过；52份Markdown/241个内部链接无缺失，SVG XML与网页JS语法通过。复现需新的输出目录和现场设备复核，不自动启动。

优先改善IK/可操作起始姿态、标准化三轴方向/安装/TCP与连续轨迹基准，再独立接夹爪/姿态遥操、真实原始MCAP episode/QC。live-03的1353次IK中285次到预算，部分松键片段有约0.022rad收敛；不能宣称解决旧IK质量、无延迟或瞬时硬停。随后接策略解码/调度；A1/A2、避碰、硬件崩溃watchdog、正式wheel/Linux锁定部署均未验。下一次物理测试先复核身份/源码hash/进程与当前profile，不自动重启或恢复上次owner。
