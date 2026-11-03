# 018：正式采集夹爪默认打开、头部深度与MP4

2026-10-22，complete（软件/部署＋无机械臂相机验证）。用户要求双侧扳机按下闭合/松开打开、默认打开，仅头部固定相机录深度，三RGB用MP4；交付机器人完整采集命令，由用户启动。本轮不启动机械臂或修改已有数据。

范围与验收：

1. 已读AGENTS、onboarding、architecture/status及M1完成状态；保留014运行时和015–017研究文档/所有未提交修改。
2. 增加可选gripper.teleop_start=follow_trigger；默认preserve兼容旧配置。只在遥操阶段有效手柄输入出现时启用，配合trigger_pressed=close实现松开全开；home/暂停/启动不自动开合。
3. 复用已存在的RGB MP4＋原始depth MCAP路径，配置scene_fixed capture/record.depth=640×480×30，腕部不启用depth；不猜深度尺度或默认RGB对齐。
4. 追加无设备配置准备入口：从机器现有deployment/身份生成独立的正式采集deployment、session和camera文件，保留原文件；角色、方向、存储、分辨率均显式参数。
5. fake/原始深度字节/视频存储/配置检查与相关回归；机器人若连通则部署代码、备份并执行check-only，无运动。更新手册/ADR/状态、给出完整任务/目录/编号/MP4启动命令。

初始连接ranger-piper仍为192.168.87.133，SSH超时；已向用户询问在线状态和IP，本地开发继续。不能将离线通过报告为头部RGB-D真机录制通过。

最终checkpoint：用户更新为192.168.87.138后连接成功。任务fill_pen_holder，根~/robot-infra/dataset，起始0/skip。新增可选teleop_start、有效按钮准入和collect-configure；原模式默认preserve保持兼容。CLI生成profiles/formal-018下独立session/cameras/deployment，原机器身份和原deployment不改。

Windows284过/10skip，Ubuntu297过；新6项配置/行为/原始depth字节＋3MP4用例通过。最终代码hash `d0fe3be2c2e3d29db89f45adf63dc851bf20caa0405c11383b5c0186c0739590`。最终测试快照018-validated.zip SHA256 `19fe2bef5bc3ac76280d8f9a3f2f4144e21661b4fba52e9ae4debf1596acb6dd`；初版相机probe代码身份和最终按钮校验改动在验证报告中区分。

相机独立真机检查：10秒三RGB分别300帧MP4、scene_fixed 295帧原始16UC1 MCAP，约30fps，capture QC/deep通过，最大帧间隔<36ms；三相机进程退出0。未启动任何双臂驱动、未创建正式任务episode。诊断在runs/018-camera-only；无深度单位/像素对齐额外承诺。完整PICO＋双臂＋RGB-D并发、新默认夹爪物理行为仍需首条正式短episode验收。

current已切releases/018-20261022-formal-collection，旧014与release-manifest.pre-018.json保留。collect --check-only如预期仅因can0 DOWN返回2；其余配置/MP4编码校验此前已执行，通过模型构造后才检查CAN。用户启动前运行两条sudo激活can0/can2，再使用正式deployment。没有代用户启动正式采集或更改CAN。

部署/测试收据offline-deployment-018.json、offline-tests-018-final.json、collection-settings-018.json、camera-probe-018.json；本地artifacts/preflight/保存副本。操作手册给出fill_pen_holder完整命令/URL/A流程；ADR0017、architecture v0.17和status同步。最终文档/包归档hash以artifacts/preflight/018-final-package.json及机器人release-manifest为准，不改动测试源码身份。
