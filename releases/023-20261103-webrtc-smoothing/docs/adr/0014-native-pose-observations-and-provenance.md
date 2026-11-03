# ADR-0014：原生末端观测及转换来源

2026-10-18，accepted；新增采集流的软件决定，不代表真机流已验证。

用户要求核查Piper原生末端反馈，明确允许原生欧拉角，要求转换不得伪装成原生。当前SDK返回XYZ整数（0.001mm）、RX/RY/RZ整数（0.001degree）；已安装ROS节点仅发布米/四元数PoseStamped，四元数由SciPy Euler xyz转换，且frame_id为空。

决定：保留两类独立可配置观测。现有Piper wrapper增加只读SDK缓存序列化，发布`native-pose/1` JSON（原整数、单位、轴名、原SDK秒时间及派生ns）。不增加SDK连接、查询或硬件命令、不更改厂商源码。原生Euler不转换。已有PoseStamped可同时录制为另一来源，`orientation_provenance=converted`且明确conversion；框架不再归一化/换序/补frame。原生流orientation_provenance=native、conversion=null。

通用`pose_feedback`来源map与`pose-feedback/1` payload不绑定左右臂数量；ROS适配器支持PoseStamped和native_pose_json，只读订阅。Piper特定轴与单位序列化留在Piper适配器。来源、frame、单位、conversion是必填显式声明（未知frame为null）。已部署v2 WebXR控制器仍有left/right限制，此项不宣称整条应用已任意臂数通用。

统一存储到`/pose_feedback/<source_id>`，index保留源和接收时间，加入expected_streams/最近邻对齐/QC。缺失、零/整段冻结stamp、非单位四元数或观测错误均报告；不因新观测错误直接增加另一硬件控制路径。保存/丢弃与raw/MP4生命周期完全共用。实时负载须单独验收。

兼容：新payload有独立版本；episode raw v1/MP4 v2和real-episode-event/1维持，属增加可选流/字段。无pose_feedback配置时行为不变；reader应按topic及payload representation解析，不能强假设所有末端都是[xyz,xyzw]。不回填、重写旧episode，不把FK当作原生测量。

边界：原生SDK缓存由多CAN帧更新，driver重复读取非原子；原生与四元数流不保证同一瞬间。frame/TCP/时间域缺失如实保留，不默认等于URDF gripper_base、实验室world或控制器硬件时间。仅凭姿态数值不能跨臂/跨机器人比较几何坐标。详见[数据报告](../collection-data-format-report.md)和[计划012](../../plans/012-cartesian-feedback-and-data-dictionary.md)。
