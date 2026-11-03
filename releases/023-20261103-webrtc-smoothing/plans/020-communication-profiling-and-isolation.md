# 020：通信/线程对照、分段性能定位与预览隔离

2026-10-23，completed（首轮定位、组件隔离与无人值守实验；后续传输/媒体改造另切片）。

用户要求梳理当前实现并与本地QuestArm源码对照，实施性能定位与隔离；用户报告Quest3能正常操作，稍后可配合只看画面的测试。SSH .139已通，current018，无采集服务运行。先读019证据及架构/status/onboarding、001完成边界与相关源码。既有未提交文件保留。

本轮范围：

1. 对照本地QuestArm WebXR主路径及旧APK路径，按进程/线程/消息队列/存储/视频说明区别，不以源码推断实测性能。
2. 增加有界、可配置的分段耗时统计；ROS源时间与host monotonic分开，不把跨时钟差当延迟。记录器排队/写入、相机回调、预览排队/编码与HTTP帧身份可追踪。
3. 预览默认内存最新帧、归档显式可选；支持按订阅需求停止编码，保留无预览时原始采集和preflight能力。线程资源回收、工作区错误语义与既有真实数据兼容。
4. 提供相机独立、不会构造机械臂的对照入口，固定配置长时记录，比较preview off/on/archive；真实服务使用改进后的同一组件。独立输出目录，不占正式任务编号，不改QC阈值。
5. Windows单元/集成/配置检查，再部署独立候选版本至机器人，Ubuntu测试及相机验证；不自动切换current或启动机械臂。头显无运动预览测试以相机独立服务为入口，现场配合时不按运动按钮。

验收：可复现的命令/配置与JSON结果、原始时间/记录完整性保留、无订阅/无归档无JPEG磁盘副作用、性能统计有固定内存上限、退出清理；报告包含未测端到端时延和未定位USB/DDS原因。是否进一步拆进程或改输入协议以本次对照为依据，避免同时更改控制语义、视频协议和录制后端。

checkpoint：已连接.139、确认无服务；开始对照与实现。尚未启动设备/修改部署current。

无人值守续查（用户明确离开并授权继续）：七组相机对照、Quest3五分钟相机/回显与WSS回环/Windows网络对照已完成。用户反馈关闭预览仍100–200ms、峰值600–700ms，开启预览有断连。回环WSS p950.763ms，Windows无线p95109ms/max297ms；两端websockets源码已经设置TCP_NODELAY，不把延迟归因于遗漏该选项。接下来只做限时延长Image QoS对照、ICMP到网关/端点分层与只读无线省电信息检查；不操作VR、不启动Piper驱动、不改网络设置或正式采集配置。所有诊断输出另存，结束核对进程。

最终结果：[通信/线程对照与配置](../docs/communication-and-performance.md)、[11次物理相机及网络证据](../docs/validation/2026-10-23-communication-performance.md)。新增CameraIngress/PreviewWorker/Performance与两种独立诊断入口，Image QoS可配置；保留输入ACK/控制/映射/夹爪/QC。metadata工具已自动复现失败段中4张Image缺失但设备帧号存在的证据。11次总计19分钟；最后同进程图像录制负载回环p951.962ms/max9.528ms，180秒两种QoS均通过。不能将网络尾延迟归咎于相机编码，也未完全排除真实反馈并发/GIL影响。

范围内验收已完成：原始帧字节/队列计数兼容、预览按需/可选归档/有界最新槽、退出清理、性能窗口与时钟边界、可复现测试/错误样本均保留。原型完整进程拆分和异步输入/WebRTC未实施；没有实际执行或回归机械臂控制。

checkpoint：current=018、formal-018未改；候选v2 core/文件清单见验证报告与artifacts/preflight，所有相机/回显进程退出，8445/8446关闭，未留下物理session。测试数据在runs/020-*诊断任务，不是fill_pen_holder示范；源数据未覆盖，参考仓库未改。源代码Windows290/Ubuntu303及Node2通过；最终新增离线工具测试、清洁发布包身份/文档检查收据另补。

最终收据：Windows完整291/10skip，修订后的无可选压缩依赖审计夹具单项复验通过；Ubuntu清洁候选304全部通过，Node2通过。清洁runtime SHA256 `66f6fa10659d3e08306d25462f7cdd28e8a64e85a8843cb34432e854ef2a54d9`，源码Python/web逐文件等于实测v2，去掉了生成egg-info。最终包含文档的020-final.zip及020-final-identity.json、offline-tests-020-clean-final.json、验证JSON在artifacts/preflight或artifacts/validation/020-data；候选目录releases/020-20261023-profiled，未切current。链接、配置示例、原始统计/四张缺失图像元数据和包排除规则检查通过；git diff --check通过。无线省电/ASPM/内核buffer只读，未改变系统设置，既有正式自签证书过期单独记录；无须头显配合的范围已完成，后续现场完整并发与传输改造不在本轮完成声明内。
