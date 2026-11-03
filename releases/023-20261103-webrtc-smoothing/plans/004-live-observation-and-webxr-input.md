# A4-S真机观测与独立WebXR输入

日期：2026-10-16。状态：complete（本切片范围）。基线5191923 / 包0.2.0。

用户要求开始接真机与VR，且可现场操作PICO。本轮最小可用终点：独立VR输入服务可访问、保留原始输入与时间/追踪状态；三相机可按已确认serial读取图像；双臂反馈接入路径与CAN状态明确。首次数据接入不启动旧整机launch/控制/推理程序，不发送机械臂运动、夹爪、底盘或升降命令。控制映射与动作执行接续M2端点/组授权及模型验证。

## 验收与实施顺序

1. 核对远端当前SSH、设备/端口、ROS依赖及现有进程，不覆盖旧工程。
2. 优先准备无机器人依赖的WebXR浏览器输入→服务端记录/状态链路；坐标保持WebXR原始参考空间，头/左右手柄及按钮分开，显示tracking/recenter/session事件，不默认转换到机器人坐标。
3. 使用单独观测adapter接入实际相机（serial来自本地profile）；先单帧/短录再三路同时，保存设备/收取时间、frame序号和流参数；明确实测分支。
4. 双臂反馈只用已审查的接收路径；CAN激活与查询/使能/运动区分。不得以SDK默认connect或auto_enable=false代替纯接收。未就绪则报告实际缺项，不伪造零状态。
5. 新格式独立版本、不改M1事件契约；fake输入/配置/断开/超时/无写入测试，Windows相关全套与目标机实际证据。
6. 写运行/停止/接续文档及状态。用户操作头显期间持续回收连接和左右手柄数据证据；完成度分别标server_ready、headset_connected、controllers_observed、camera_frames、arm_feedback。

## checkpoint

完成：独立WebXR服务、原始输入/时间/参考空间与事件记录；用户两次PICO实测；三路真实RGB及双臂纯CAN接收反馈；USB/SDK serial命名空间纠正；运行文档、ADR-0008与逐项[实测证据](../docs/validation/2026-10-16-a4s-live-observation.md)。包0.3.0，M1契约不变。

Windows125项全套通过，Ubuntu隔离切片45项通过；九帧raw图像hash复核并查看三路首帧。PICO首轮840帧/第二轮472帧，seq缺口170/37；第一轮有摇杆变化，两轮均有按键/位姿。三相机640×480 RGB，15秒各观察214/212/211帧、保存3帧；双CAN3秒各9423帧，TX前后0。每项均有独立证据，不代表同步episode、完整Linux M1或物理控制通过。

实际观察没有覆盖用户遮挡追踪丢失、recenter或故障重连，不据fake测试宣称头显已通过这些验收。HTTP/1.1复用后仍有37个客户端队列跳帧（send_errors=0）；画面偏青/过曝、时钟对齐、持续数据与输入质量留给下一切片。用户只激活can0/can2，本项目未写机器人命令、未改can1/旧工程/服务。

接续：M2.1–M2.2多端点/执行组与真实时钟fake故障测试→持续观测/输入时序→显式模型/joint order/TCP、VR映射/离合与IK shadow→明确范围的物理运动验收。现场profile在profiles/local，数据在artifacts/live-004及报告列出的远端独立run目录；不要从USB serial直接推SDK serial。两轮临时WebXR服务已按PID/cwd核验后停止，8445需下次重新启动；CAN接口保持用户配置。仓库未设remote/未发布。

交付检查：0.3.0 sdist/wheel构建、排除和HTML资源检查通过，源目录外wheel观测模块/服务构造通过；41份Markdown/169内部链接零问题。服务停止后确认PID已不存在、8445不监听。
