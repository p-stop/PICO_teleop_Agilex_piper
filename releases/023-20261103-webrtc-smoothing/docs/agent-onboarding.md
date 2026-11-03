# Agent入口

更新：2026-10-24。遵循AGENTS，以架构和project-status为实现边界。

**021最新授权：S0、S2已批准，S1暂缓。** 见[计划021](../plans/021-transport-semantics-and-live-validation.md)。复用现有输入包和机器人端状态机，不新增命令体系，不先重写WSS。先完整020采集基线与可选WebRTC单通道输入，再按证据判断。下文“待审核”是10月23日历史提案。

**021检查点：** [10月24日验证](validation/2026-10-24-state-machine-and-webrtc.md)、[流程说明](webxr-workflow-and-transport.md)、ADR0019。S0真机保存37.276秒，用户确认跟手且无自动中断，左腕RGB235.98ms空档QC失败，6帧元数据存在/图像缺失；writer无drop，三MP4完整。S2 v2在 `releases/021-20261024-webrtc-v2`，独立 `profiles/021-webrtc-20261024/deployment-v2.json`、`python-deps-webrtc-021`；Windows293/Ubuntu306/Node3通过，check-only通过。无机械臂诊断300秒收到0个头显输入，不能宣称Quest/UDP通过。测试栈已全部结束；下次先开v2无机械臂诊断，等头显确认UDP路径后再真机A/B，不直接启用S2物理控制。current018不动；S1不做，正式部署仍不能继承候选质量结论。

**待审核021：** [协议/证据/必要性审核稿](transport-review.md)、[计划](../plans/021-transport-semantics-and-live-validation.md)。用户明确要求审核后才能执行；S0–S2只是建议范围，尚未批准。后续“可以继续真机”不自动批准新方案。当前仅文档和只读状态检查，未实现异步WSS/WebRTC或开始新真机测试；先落实审核意见再推进。

**最新候选020（2026-10-23）：** [通信/QuestArm对照与操作](communication-and-performance.md)、[现场证据](validation/2026-10-23-communication-performance.md)、[计划](../plans/020-communication-profiling-and-isolation.md)、ADR0018。共享CameraIngress/PreviewWorker；预览默认按需、无连续JPEG归档；分段计时有界；Image QoS显式配置默认仍best_effort/5。11次相机诊断共19分钟，无机械臂；原始RGB gap内存在连续设备元数据，范围缩至驱动观测后Image发布/DDS/接收；RELIABLE候选通过但未改正式配置。Quest3仍报告网络尾延迟/断链；回环WSS p95<1ms，图像同进程负载p95约2ms，Windows无线约109ms，ICMP也有尾延迟。省电只是候选，未修改网络。部署current仍018，候选v2在releases/020-20261023-profiling-v2，测试服务已清理。下一步异步最新位姿与离散按键分离、无线条件对照与完整并发验证；不能声称性能问题全解决。

**最新现场诊断019（未改运行时）：** [帧间隔/VR延迟报告](research/2026-10-22-collection-latency-audit.md)、[计划](../plans/019-live-collection-bottleneck-audit.md)。018正式采集十次已结束尝试中六次有frame gap，writer无drop/error；源时间也有空档，USB/驱动/DDS/回调原因未定。RTT尾延迟、输入逐包等ACK、预览8→2fps降级与摘头显visible-blurred暂停应分别处理。只读审计，没有发送控制、启停服务或改配置；性能改造未实施，部署仍018。后面的018相机短测/首轮未验描述保留其当时边界，正式尝试证据以019为新补充。

**最新运行时018：** [正式采集手册](episode-collection.md)、[验证](validation/2026-10-22-formal-collection.md)、[计划](../plans/018-formal-collection-head-depth.md)、ADR0017。用户指定fill_pen_holder，dataset根~/robot-infra/dataset、起始0/skip；独立formal-018 deployment选择两臂按扳机闭合/松开打开、teleop_start=follow_trigger，三RGB MP4与仅scene_fixed原始depth640×480×30。旧deployment保留旧设置，不能误选。无按钮数据不猜松开；启动/home/暂停不主动开合。Windows284/Ubuntu297通过，相机独立10秒记录/deep过，未启动机械臂或正式episode；CAN原为DOWN，用户启动前需按手册激活。新IP192.168.87.138，旧可信HostKeyAlias沿用130。部署/source hash见计划018和receipt；首条完整新配置PICO双臂采集未验。

**最新研究017（不改变运行时）：** [业界/学界质量证据](research/2026-10-22-data-quality-quantification.md)、[量化标准草案](data-quality-standard.md)、[指标JSON](assets/data-quality/metrics-proposal.json)、[计划017](../plans/017-data-quality-standards.md)。覆盖七家公司及相关学术工作，七维20项指标；区分可信性、片段用途和闭环收益。JSON仅为文档，不能传给采集入口。现有QC通过不代表曝光同步/任务成功；恢复片段、未知夹爪目标与无深度不能机械过滤或补造。Windows文档检查通过、源码hash与014/016相同，未连接设备。下一实施建议离线I02/T01/T02/S02；先输出未知与异常区间，再校准阈值。

**最新研究016（不改变运行时）：** [统一数学模型](research/2026-10-22-pipeline-mathematical-model.md)、[八课教程](pipeline-learning.md)、[离线学习阅读器](pipeline-model.html)、[计划016](../plans/016-pipeline-mathematical-model.md)。覆盖混合状态、时钟/信息年龄、映射/异步IK、执行器未知动力学、记录/训练视图和推理队列；特别区分按更新次数的IK正则与物理时间、旧队列覆盖与新chunk首动作未来性。教学数字不是Piper辨识参数。当前源码hash与014相同，未连接设备、未改运行参数；下一实施优先Timing QC/传输基准，不能把研究建议当已实现功能。

**最新研究015（不改变运行时）：** [信号/采样/学习报告](research/2026-10-20-signal-timing-and-learning.md)、[离线交互版](signal-timing-report.html)、[计划015](../plans/015-signal-timing-and-policy-research.md)。解释手柄→异步IK→发布目标→反馈→多速率记录及训练时序。plan014已有日志重分析得到约60Hz目标发布/169Hz反馈，不能据此推断原生伺服频率或精确复现。后续优先Timing QC、传输基准、回放精度评估；未修改控制参数或启动设备。

**最新计划014：** [回放/假模型操作](replay-and-mock-inference.md)、[验证](validation/2026-10-20-replay-and-mock.md)、[计划](../plans/014-physical-replay-and-mock-inference.md)、ADR0016。ExecutionSession连接ReplaySource/AsyncPolicySource并共用LiveGateway；不改旧采集session。workflow-run是native绑定子集，不是任意图解释器。用户现场确认双臂起始对齐＋第二集前3秒回放正常；反馈与日志验证，驱动已退出，无持续物理会话。假模型独立进程HTTP/fake三RGB通过正常/错误链，不代表GPU或真相机推理。Windows278/Ubuntu291过，current=014，旧013保留。以下013/012为历史状态；后续动作需依据新任务授权，不能因为本次验证过就自动继续真机。

**最新：计划013数据审计/训练视图/三图设计。** 先读[本次数据审计](research/2026-10-19-new-test-audit.md)、[训练报告](training-data-format-report.md)、[三图](three-workflow-graphs.md)、[ZeroWAM代码研究](research/2026-10-19-zerowam-deployment.md)、[计划013](../plans/013-data-audit-training-and-three-graphs.md)和[验证](validation/2026-10-19-data-and-workflows.md)。new_test两集saved+QC/deep过，一集review固定相机帧间隔失败，全部无depth；四路末端/真实MP4已实采。任务仅工程测试，成功失败待标注。用户确认当前相机角色且未更换设备，序列号按本次配置，历史差异不猜原因。

新增episode-audit（另存报告）、training-view（确认目标/因果观测/未知夹爪mask，不是LeRobot）、trajectory-check（离线，不执行）和experiment-plan（三图静态，不是真机runner）。诊断分段不删历史、同FPS保留每帧、初始发布目标快照和ACK处理计时已软件测试，Windows261/Ubuntu274通过，Node2过。ZeroWAM在独立服务器，未安装模型；其EEF16/cache和lerobot0.3.3需要独立adapter。当前代码/部署checkpoint以计划013为准；不要启动物理回放/策略。连接ranger-piper新IP为192.168.87.126，严格校验可用旧可信HostKeyAlias=192.168.87.130，未改用户SSH文件。

以下计划012/011的未验描述为当时历史状态，最新实采证据见上方计划013。

**最新切片：计划012末端观测和supervisor数据报告。** 用户要求原生Euler可直接记录，转换必须标明来源。Piper wrapper只复制现有SDK缓存，原生XYZ/RX_RY_RZ整数、单位和秒stamp单独流；ROS驱动转换Quaternion另流、显式conversion。不推断未知frame/TCP，不改命令链路，不回填旧集。先读[数据报告](collection-data-format-report.md)、[ADR0014](adr/0014-native-pose-observations-and-provenance.md)、[计划012](../plans/012-cartesian-feedback-and-data-dictionary.md)。Windows250通过/10跳过、Ubuntu263通过（含真实ROS本机序列化、无设备）；软件部署/静态预检见计划checkpoint，**新增末端流和实时MP4仍待现场验收**。

**此前软件切片：计划011的可替换MP4存储。** raw_mcap默认保留；collect --image-storage mp4选择每RGB流MP4＋事件/深度MCAP＋逐帧时间索引，real-episode/2与旧raw v1分开。实现/测试/部署状态先读[计划011](../plans/011-pluggable-image-storage.md)、[ADR0013](adr/0013-pluggable-image-storage-and-mp4.md)和[验证](validation/2026-10-18-mp4-storage.md)。Windows236通过/9跳过、Ubuntu248通过；旧真实26秒样本离线重编码2.18GB→20.45MB，帧数一致、QC/deep通过。**尚未做实时MP4物理采集，也没有完整LeRobot v3导出。**

操作员读[简明采集手册](episode-collection.md)，实现/配置读[技术说明](episode-storage-and-configuration.md)与[布局说明](recording-storage-options.md)。计划010已修复显式deployment被默认值覆盖的问题，继续保持ROS/Python环境与所选配置一致。

此前计划009已验收原始RGB真机闭环：episode2保存26.179秒、三相机约30fps、独立夹爪，QC/deep通过。当前无活动实验；历史失败/incomplete/discarded保留。没有授权时不要启动物理命令；新功能不能继承旧raw真机结论。新会话优先核对计划012最终checkpoint和实际部署。

## 首次进入

1. 遵循根目录[AGENTS.md](../AGENTS.md)。
2. 检查实际cwd、Git状态、文件清单和当前任务计划；保护已有未提交修改。
3. 从[项目状态](project-status.md)获取完成度。实质改动按AGENTS.md读取[架构](architecture.md)，然后只读相关ADR、源码与测试。
4. 用任务的可观察结果、范围和验收条件驱动实现；不要把完整架构一次实现出来。

**历史快照（v0.10，不代表当前实现）**：架构v0.10、包metadata0.3.0+未发布增量。Windows/Ubuntu隔离全套各182通过；fake-only collection保留。PICO→框架位置映射/FK/IK→本地网关→现有ROS驱动→双臂真实运动已由用户/反馈确认，三相机中央大/两侧小布局已确认。夹爪禁写、朝向保持，10cm/0.6rad偏移/0.4rad/s/20%速度有界测试；无限幅/100%实际启动被自动审批拒绝。所有临时物理进程已停止。三轮诊断JSONL/JPEG可读/hash通过，但退出摘要缺失，不能算完整episode；收尾修复通过隔离ROS定时/SIGINT测试，尚未再做物理采集。先读[数据流](a4s-dataflow.md)、[现场报告](validation/2026-10-16-a4s-live-control.md)、[运行手册](live-teleop.md)和[计划007](../plans/007-live-vr-teleop-and-video.md)。近期改善IK/标定，接夹爪/原始MCAP采集，再策略；A1/A2未验。用户要求本地基线，无远程发布。

## 文档路由

| 任务 | 额外阅读 |
|---|---|
| 当前双臂VR graph与共享执行代码 | [graph](a4s-graph.md)、[多端点fake运行/审查](collection-review.md)、[计划006](../plans/006-a4s-graph-and-shared-execution.md)、ADR-0009；采集/推理共用执行面不等于真实推理已通过 |
| 旧机器人工作流是否闭环、代码用途与复用 | [既有遥操/数采/推理研究](research/2026-10-16-existing-robot-workflow.md)、[计划005](../plans/005-existing-robot-workflow-research.md)；主从单执行臂与A4-S双执行臂区分、历史数据完整性和相机角色差异优先核对 |
| 远端旧代码、设备发现与发布部署 | [远端索引](remote-code-index.md)、[发现格式/模块](device-discovery.md)、[发布部署](release-and-deployment.md)、[本轮验证](validation/2026-10-16-discovery-and-audit.md)，[计划003](../plans/003-remote-audit-discovery-and-release.md)、ADR-0007 |
| 真实输入/相机/CAN观测与身份命名空间 | [实测报告](validation/2026-10-16-a4s-live-observation.md)、[运行说明](live-input.md)、[计划004](../plans/004-live-observation-and-webxr-input.md)，ADR-0008 |
| 下一切片、A4-S/A1/A2现场准备 | [M2计划](../plans/002-a4s-teleop-acquisition.md)、[现场手册](validation/a4s-a1-a2-playbook.md)、[参考仓库索引](reference-repositories.md)，ADR-0006 |
| 接续/审查fake纵向切片 | [首切片计划](../plans/001-fake-control-loop.md)、[审查指南](m1-review.md)、[验证报告](validation/2026-10-15-m1-windows.md)，架构§3–5、§12，ADR-0001/0002/0005 |
| 控制权、停止、重连、动作时序 | 架构§5、§12，ADR-0002；相关故障测试 |
| 数据、训练交接、评测 | 架构§4、§15，[定位协议](positioning.md)；相关格式/导出实现 |
| 驱动、Linux环境、远程验证 | 架构§8、§13，[跨机开发](development-and-validation.md)，ADR-0001 |
| 推理、IK、RTC等选型 | 架构§12，[专题研究](research/2026-10-11-teleop-inference.md)，ADR-0002 |
| GUI | 架构§14，ADR-0003；已实现schema/session接口 |
| 范围、定位、时间承诺 | [定位协议](positioning.md)，ADR-0004；需要证据时读工作流研究 |
| 对话组织、任务交接 | [AI开发工作流](ai-development-workflow.md)，[任务模板](../plans/templates/task-template.md) |

不要为一个小改动反复加载所有研究材料。设计页中的完整Python/YAML/CLI示例仍为草案；实际可运行入口以README和M1审查指南为准。

## 必须保持的边界

- 核心不依赖ROS/厂商SDK；应用不直接写硬件。每条物理命令经所有权和最终安全检查。
- 意图、映射、调度/规划、最终命令、反馈与安全事件分开记录；时间域、单位、frame和joint order明确。
- Windows fake通过不能证明Ubuntu设备支持；构建、fake、仿真、只读、物理证据分别报告。
- 本文、任务模板和历史计划不授予机器人运动权限。未明确请求真机测试时，只推进文档、无硬件实现及相应验证。
- 不因软件接口统一而宣称跨形态权重/任务能力复用，也不宣称10分钟目标已经达到。

## 接续与交付

接续先阅读当前计划的checkpoint和验证证据，核验代码基线、环境和未提交修改；只重跑与变化或不确定性有关的检查。任务完成后更新计划和project-status，说明已做、未做、实际验证及下一步。共享接口/安全路径变化写相关ADR和兼容影响。

交接以仓库文件与代码版本为依据；聊天总结可以辅助定位，但不能代替实际代码、测试和实验报告。全局状态由当前集成任务维护，独立任务先在自身计划报告结果，再于集成时更新全局状态。
