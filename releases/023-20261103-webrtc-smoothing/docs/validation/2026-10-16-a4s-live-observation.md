# A4-S真实输入与观测验证

日期：2026-10-16。基线5191923上的计划004增量；包0.3.0，M1契约仍0.3.0-m1。环境：Windows/Python3.11.12开发；ranger-piper Ubuntu24.04.4/x86_64、Python3.12.3、ROS Jazzy、realsense2_camera4.58.1/librealsense2.58.1。SSH只部署本项目独立观测源码，不安装依赖、不修改前人工程。

## 实测结果与边界

| 链路 | 结果 | 未证明的能力 |
|---|---|---|
| PICO HTTPS/WebXR | 用户两次进入VR并操作；头部/左右手柄位姿、按键、第一轮摇杆变化可记录；两次均收到session_end | 稳定低延迟控制、丢追踪/recenter/重连故障覆盖、Quest3兼容 |
| 双腕D435+固定D455 RGB | 三路同时640×480/15FPS配置，15秒观察，各保存3帧raw+PNG及CameraInfo/原始metadata | 深度/IMU、硬同步、持续episode、D435/D435i固定相机替代分支 |
| can0左臂/can2右臂 | 用户激活接口后纯接收3秒，两侧各9423帧；各保存600原始CAN帧；六关节反馈解码有效 | 固件查询、夹爪标定、使能/运动/停止行为、完整控制backend |
| 测试 | Windows全套125通过；Ubuntu隔离切片45通过 | 完整M1 Linux、其他OS/机器人 |

本项目没有发送机械臂、夹爪、底盘或升降动作。CAN采样前后can0/can2的TX计数均为0；接收器不提供send调用，不初始化SDK。用户在机器人终端执行的接口UP配置已单独记录；can1未改动。反馈解码显式选择与已审SDK0.6.1相符的Piper-v2关节协议；三对反馈各保留收取时间与组装偏差，未假设原子状态或设备时钟。

三条链路分开运行，尚未证明一个同步多模态episode，更没有完成双臂遥操验收。当前格式是独立诊断记录；M1固定fake的MCAP契约没有扩展。

## 设备身份纠正

此前仅凭sysfs枚举判断旧相机launch的serial失配，证据不足。此次原生RealSense驱动日志将SDK身份与物理USB端口关联，证明两套serial属于不同命名空间，旧launch中的SDK serial实际对应当前设备：

| 用户确认角色 | USB descriptor serial | USB端口 | RealSense SDK serial |
|---|---|---|---|
| left_wrist / D435 | 022523021289 | 2-3.2 | 022422072252 |
| right_wrist / D435 | 342123026960 | 2-1 | 342522071110 |
| scene_fixed / D455 | 261143061977 | 2-3.1 | 254922307547 |

USB绑定profile保持USB身份；相机开流profile显式使用serial_namespace=realsense_sdk，并保存本次关联证据。不由serial外形猜命名空间，也不在代码中按型号选择第一台相机。旧launch仍有右腕默认禁用、记录器只含两相机等问题，但“全部serial失配”的结论已撤回。

计划005后续补充：上句“右腕”指旧launch的逻辑名。进一步逐项核对发现旧left_wrist_camera绑定的是当前物理右腕、旧right_wrist_camera绑定的是当前物理左腕；因此其当前默认关闭的是物理左腕。上表和本轮独立相机profile使用用户当前确认的正确角色；旧配置角色不可直接沿用，历史安装情况另待确认。详见[工作流研究的相机对照](../research/2026-10-16-existing-robot-workflow.md)。

## VR证据

浏览器UA自报PICO 4 Ultra Enterprise OS5.11.2、PicoBrowser4.0.34/Chrome125；profiles含pico-4u、oculus-touch-v2、generic-trigger-squeeze-thumbstick。此为浏览器证据，未读取头显设置或据此推断其他版本兼容。secure_context/webxr_present/immersive_vr均true；用户看到深蓝空间与左右青/橙标记。

| 项 | 首轮 | HTTP/1.1连接复用后第二轮 |
|---|---|---|
| 所有事件 / frame | 852 / 840 | 482 / 472 |
| 头部无追踪帧 | 0 | 0 |
| 左/右有效grip | 839 / 839 | 472 / 472 |
| 相邻记录seq缺口合计 | 170 | 37 |
| 原始JSONL SHA256 | 9df32f7579781f2c48797016cd3adfceb33187d3e56e6d0ad1c37dd5f2533382 | 84194a386f9e28676810e16c99436e51048b295e1d44bece2d74651ada130efc |

两轮长度、可见状态和操作不同，不是受控性能对比。首轮末帧客户端累计skipped=166/send_errors=0；seq在入队前生成，有界队列满会跳帧，因此缺口不能直接称为网络丢包。第二轮缺口37均出现在frame之间，末帧客户端累计skipped=37/send_errors=0，与缺口一致；仍需优化客户端队列与浏览器调度，测量新鲜度和延迟分布，不能宣称零丢帧或控制就绪。WebXR、设备metadata、ROS header及host收取时间原值保留，跨时钟关系unmeasured。

## 相机证据与图像质量

左腕观察214帧、右腕212帧、固定211帧，各保存3帧，均有CameraInfo且采集器errors为空。metadata分别214/213/212条到达，按有界策略保留样本；原始JSON含frame_counter、frame_timestamp、hw_timestamp、sensor_timestamp、time_of_arrival及clock_domain，不猜单位或强制对齐。9个raw文件均在开发端重新计算SHA256并与索引一致。

已逐路查看首帧PNG：左腕主要看到桌面及夹爪边缘，右腕可见桌面物体，固定相机俯视桌面。腕部整体偏青、固定画面高亮区域过曝；未调整驱动默认曝光/白平衡，正式任务前需在选定摆位和照明下调整并保存参数。身份角色来自用户确认与物理端口关联，不能仅凭画面推断左右。

## 可接续证据位置

以下本地路径均gitignored，不进入发布；保留报告让第三方按[运行说明](../live-input.md)复测：

- artifacts/preflight/live-input-linux-tests.json：45项、隔离源码包hash、JUnit；临时目录自动清理，无依赖安装。
- artifacts/2026-10-16-live-input-windows.xml：125项全套。
- artifacts/2026-10-16-live-release-check.json：41份Markdown/169个内部链接零问题；0.3.0 sdist/wheel排除检查、打包HTML与源目录外wheel模块/服务构造检查通过。
- artifacts/preflight/live-vr-validation.json、live-vr-validation-keepalive.json：逐轮汇总；artifacts/live-004/xr-input*.jsonl为原始输入。
- artifacts/preflight/live-rgb-observation-sdk-identities.json、live-canrx-observation.json：实际命令/结果、TX对照及运行路径。
- artifacts/live-004/：三路raw/PNG、camera-config/summary/observations、CAN raw/summary及原始日志；图像不进Git。
- profiles/local/ranger-piper.device-bindings.json与ranger-piper.realsense.json：现场绑定与独立SDK开流配置。

远端独立运行目录：/home/ros/robot-infra-runs/004-webxr-20261016T093114Z（首轮）、004-webxr-20261016T094313Z（第二轮）、004-rgb-20261016T093835Z（三相机成功轮）、004-canrx-20261016T094104Z（CAN）。首次相机轮004-rgb-20261016T093547Z因serial命名空间错误失败，证据保留；不计为通过。相机/CAN采样已退出；两轮WebXR服务均在确认各自PID/cwd后由本次任务SIGINT停止。页面8445当前已关闭；下次按运行说明新建输出并启动，接续时检查进程/端口。证书私钥留在对应远端运行目录，不读取、复制或提交。

## 下一验收门槛

接续M2.1–M2.2具名端点/执行组、真实时钟/独立超时与fake故障测试；并行顺序推进M2.3的有界持续记录与输入质量度量。随后确认真实机器人模型、joint order/TCP与VR映射/离合，离线FK/IK及shadow验证通过后，再进行明确范围的单臂低幅运动测试，最后双臂遥操/三相机episode。策略推理仍在遥操数采之后。
