# ADR0018：有界分段计时与按需预览

2026-10-23，accepted，计划020。

背景：019发现相机frame gap、控制RTT尾延迟和VR生命周期暂停是不同问题；连续JPEG归档和集中服务资源共享需要可测量的隔离，不能靠放宽QC诊断。

决定：提取无ROS依赖的CameraIngress/PreviewWorker，正式服务和相机独立probe使用相同分发；原始记录有界队列独立于每相机一个最新预览槽。预览默认按请求租约编码、只在内存发布；JPEG归档显式开启。原始采集新鲜度作为自检依据，不要求网页先打开预览。预览故障单独上报健康状态；ROS/记录错误仍按原路径失败。保留所有必要的输入/控制/反馈/停止与原始记录证据。

Performance是独立、可关闭、有固定内存上限的诊断，输出performance-snapshot/1；host耗时和源时间间隔区分，分位数标为最近窗口。图像响应附帧身份和服务端帧龄；不把不同机器时钟相减。real-episode/1、/2和输入协议不变。

Image订阅的reliability/depth显式配置，默认保留best_effort/5；其他相机消息仍使用sensor-data QoS。probe可对照RELIABLE，但不能在不确认发布端兼容与时延代价时升级正式配置；RMW/publisher QoS记录在测试结果。

兼容影响：旧配置默认不再产生连续preview JPEG归档，诊断消费者不能假设每次会话都有preview目录；需要旧侧车时显式设置archive_jpeg=true、on_demand=false。原始RGB MP4/depth MCAP与逐帧时间不变。首次预览请求可能503以启动编码，现有轮询会重试。

边界：本轮不改变输入ACK策略、控制调度、物理映射、夹爪、关节限制或QC门限；不立即拆出所有服务进程。camera_benchmark不构造机械臂，不消耗正式任务编号。后续以对照测量决定进程/共享内存、异步位姿传输和媒体协议切片；这些提案不能当已实现。
