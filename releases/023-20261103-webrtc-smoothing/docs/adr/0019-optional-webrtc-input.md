# ADR0019：复用采集状态机的可选WebRTC输入

2026-10-24，accepted for candidate implementation；S0/S2获批，正式默认保持018。

原WSS逐包等待业务回复，吞吐受RTT限制。用户要求先验证完整采集与WebRTC，暂缓未证明必要的“共同输入语义”和新命令体系。

决定：输入边界增加可选WebRTC适配器，沿用 `webxr-input/1`、`app.input` 校验、`TeleopSession`、gateway、IK与原始记录。一个可靠有序通道承载完整快照，避免首切片拆分按键/姿态引入跨通道顺序问题；发送不等单包回复，回复仅用于计时和失联。

配置为 `webxr_transport.input = "webrtc"`，可选Python依赖单独安装。HTTPS同源交换连接信息，无外部STUN/TURN；保留原HTTP/WSS实现，不自动回退。HUD/事件记录实际候选协议，不能仅凭WebRTC名称宣称UDP已验证。发送积压和接收队列均有界，关闭释放连接/线程并请求原session暂停。不改变坐标、速度、QC或失联阈值。

不新增流程状态、消息schema或命令总线。可靠通道仍有重传等待；允许位姿丢帧将来按实测必要性讨论。UDP输入不改变HTTPS JPEG视频，不修复相机Image空档；跨网段/TURN未验证。见[计划021](../../plans/021-transport-semantics-and-live-validation.md)与[流程说明](../webxr-workflow-and-transport.md)。
