# 2026-10-24：采集基线与可选WebRTC输入

用户批准S0/S2、暂缓S1。操作者在机器人旁，使用Quest 3。Ubuntu机器人SSH别名 `ranger-piper` 当前地址192.168.87.110；CAN can0/can2 UP/1Mbps。未修改网卡/AP/内核设置，未改变坐标、控制速度、QC或失联阈值。正式 `current` 始终保留018。

## S0：020完整真机采集已执行，质量仍有问题

使用已测020清洁候选 `releases/020-20261023-profiled`，独立配置 `profiles/021-s0-20261024/deployment.json`，独立任务 `a4s-021-s0-validation`，存于 `validation-data`。配置从formal-018复制：双臂、三路640×480×30 RGB MP4、头部同分辨率/FPS原始深度；WSS输入；Image订阅默认best_effort/5。测试证书单独生成，没有覆盖正式配置/证书。

用户执行回位、遥操、A结束与A保存。现场反馈“挺跟手”，HUD常见RTT约50–60ms、看到峰值约90ms，没有自动中断；保存后QC提示frame gap。记录数据与实际统计如下，HUD的间歇观察不能替代完整时序统计。

| 流 | 保存帧数 | 实收FPS | 最大接收间隔 |
|---|---:|---:|---:|
| 左腕RGB | 1106 | 29.66 | **235.98ms** |
| 右腕RGB | 1111 | 29.79 | 71.66ms |
| 固定RGB | 1117 | 29.96 | 66.27ms |
| 固定深度 | 1117 | 29.96 | 66.60ms |

episode_000000持续37.276秒，已保存。QC只因左腕RGB gap失败；对齐1117行中4行无效。深度完整性复查执行完成，三MP4全部解码帧数与索引一致；**文件完整不等于时序QC通过**。writer dropped=0、无错误；左腕 received_by_writer=written=1106，rate_filtered=0。

左腕gap前后设备frame_counter为5293→5300，中间6帧元数据连续存在；原始图像时间也跨过该间隔。故驱动曾观测中间帧元数据，但缺相应Image记录。范围落在图像处理/发布、DDS或接收路径，不能进一步断言一定是DDS，也不能把它归因于VR网络。尚未把RELIABLE配置升级为正式默认。

录制阶段900个已接收输入，平均24.16Hz；接收间隔p50=31.51ms、p95=107.92ms、最大310.42ms。浏览器随下一包上报的**前一次成功回复RTT**：p50=10.9ms、p95=91ms、最大280.5ms；这是有选择的成功回复统计，不是动作端到端延迟。IK结果耗时p50=1.29ms、p95=2.94ms、最大8.45ms，不含所有机械响应时间。

状态记录出现HOMING→READY→PREPARING→TELEOP→FINALIZING→REVIEW→COMMITTING→STANDBY，证明原机器人端状态机完成了采集/保存流程。随后操作者又回位一次并退出/失去VR可见性，系统暂停；不能把这次可见性暂停记为网络自行中断。关闭测试栈后六子进程退出码全0，无自动home/夹爪收尾动作。

证据：机器人 `runs/021-s0-20261024/{status-after-trial.json,camera-gap-audit.json,summary.json,deep-qc.log}`；实际栈 `runs/20261024T072844Z_57e8a1ef`；已保存集 `validation-data/a4s-021-s0-validation/episodes/episode_000000`。小型收据复制到本地 `artifacts/validation/021-data`，未下载大体积原始数据。

## S2：软件完成，头显与真机对照尚未验收

只新增可选输入适配器，复用原包、原校验、原状态机和执行入口。一个可靠有序通道连续发送；不逐包等回复。未实施原S1的新消息体系或异步WSS改造，未改JPEG视频协议。具体说明见[流程与连接](../webxr-workflow-and-transport.md)、[ADR0019](../adr/0019-optional-webrtc-input.md)。

- Windows最终293 passed / 10 skipped（Linux/ROS/Pinocchio专属），Node 3 passed。
- Ubuntu最终306 passed，含ROS localhost、Pinocchio与实际aiortc本机UDP/DTLS/SCTP往返；不涉及机械臂运动。
- 新增验证：原包顺序保留、连续发送无需等待回复、非法输入/SDP、连接占用、断开期间输入处理后的暂停顺序、线程清理；浏览器测试还验证最大未回复数和一次性停止。
- v2候选 `releases/021-20261024-webrtc-v2`；运行时tree SHA256 `95f7688009279ff527902349be1a1c53a5a861e44f5c57838efbf4d8abf2b31e`。来源包 `artifacts/preflight/021-candidate-v2.zip`，SHA256 `2ec57d6f29c0e383a957d44e289c9bdcc7f1bce550eb2cd62281864bc7b32b34`，248个文件，逐文件校验后解包；包后文档补记不冒充新运行时。
- 独立依赖 `python-deps-webrtc-021`：aiortc1.15.0、av16.1.0；未覆盖018依赖。项目extra和uv.lock可复现安装。
- 独立配置 `profiles/021-webrtc-20261024/deployment-v2.json`，`collect --check-only`退出0，验证可选依赖和配置但不构造设备。TLS本轮独立证书仅7天有效、含本轮IP，不能长期沿用。

已开放初版候选的300秒“仅相机/WebRTC回显”页面，**没有机械臂驱动**。相机记录/deep QC通过、三相机退出码[0,0,0]，无线程或错误残留；但窗口内输入数为0，没有收到头显路径事件，故**不能称作Quest 3 WebRTC验证通过**。不自动重启无人参与的重复诊断，也未运行S2物理遥操。该初版随后补强了断开期间输入与暂停的线程顺序，最终v2重新通过上述软件测试；未在运行时热替换源码。

截至本检查点，诊断服务均结束，机器人无本项目机械臂/相机进程。下一步在操作者准备好时用v2重新开放无机械臂页面，确认HUD/事件实际UDP候选、输入频率和延迟，再做同条件完整真机A/B及丢弃测试。切到WebRTC同时改变了发送是否等待业务回复，因此后续改善也不能单独归功于UDP；若需要单独分离两因素，再讨论一个小范围WSS发送对照，不捆绑新架构。
