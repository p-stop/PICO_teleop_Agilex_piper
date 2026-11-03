# ADR-0015：训练目标、只读审计和三类工作流计划

2026-10-19，accepted。用户要求检查三集数据、构思LeRobot v3与ZeroWAM接入，并以采集/回放/推理三图共享基础设施。

决定：引入ROS/模型无关的真实episode reader，audit将QC/对齐结果写到独立派生目录；原文件不重写。训练语义在training-view/1配置中声明端点顺序/单位、视觉来源、深度scale、因果采样和准入策略。action使用确认已发布的绝对目标，不以受物体阻挡的夹爪反馈替代；普通command匹配receipt，post-send hold单独注明。初始目标从历史journal或新context.initial_targets取证，无法确定时null/mask，禁止补成实测开口。

视图是带来源hash/sequence/行号的JSONL，不冒充LeRobot v3。官方writer与模型专用adapter隔离，LeRobot/PyTorch不进入设备核心。RGB-D缺失或深度scale未知应明确拒绝，不伪造深度。任务成功与capture QC分离；new_test工程样本标注待定。

实验图使用独立experiment-graph/1，不改变M1 fake schema。固定节点目录声明类型端口，反馈/history为显式跨tick边，驱动只能由共同gateway写；动作encoding和坐标/夹爪映射须声明。三模板目前只做静态编译，不声称已有统一物理runner。轨迹计划复用确认目标和原始时间，剥离旧lease/epoch；TimelineSource只供无硬件调度验证。

执行面后续按NativeExecutionSession提取→轨迹shadow/短物理回放→mock策略→ZeroWAM桥接推进；所有路径仍过LiveGateway/PiperROSBackend，不开SDK旁路。ZeroWAM为有状态chunk/cache协议，模型预测动作与真实发布历史不能混淆；公开16维EEF与我们的14维joint不自动兼容。

审计发现独立问题：旧诊断日志512MiB总上限可在短会话内触发；改为独立可配置追加分段，默认128MiB、不删历史，保留磁盘余量检查。capture=record FPS时不再按收到时间二次限流，并新增writer帧计数/callback序号；这消除一个确定丢帧点，但不宣称已唯一解释原197ms空洞。ACK增加服务器输入处理计时，便于后续区分处理与端到端延迟，不冒充单向网络测量。

兼容：保留episode v1/v2、原事件版本、旧单文件journal读取；新增context.initial_targets、图像capture_sequence、manifest.frame_capture_stats、ACK可选计时及分段summary为加法扩展。会话journal读者须跟随segments，不只读首文件。旧数据/旧QC不改写。物理graph runner、LeRobot exporter、模型桥接尚未实现。

详见[训练报告](../training-data-format-report.md)、[三图](../three-workflow-graphs.md)、[数据审计](../research/2026-10-19-new-test-audit.md)、[ZeroWAM研究](../research/2026-10-19-zerowam-deployment.md)和计划013。
