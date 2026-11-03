# ADR0016：具名原生目标执行session与可替换推理fixture

2026-10-20，accepted（实现边界以验证记录为准）。

背景：013只有离线轨迹/静态三图；用户要求先真机回放，再用假模型验证推理端。复制遥操应用并直接调用SDK会导致两套权限/停止行为。

决定：ReplaySource和AsyncPolicySource提供同语义的native targets；ExecutionSession承担起始关节对齐、控制权代次、运行与终止，所有动作继续经过LiveGateway→已有PiperROSBackend。物理适配器只负责驱动生命周期/ROS反馈，fake设备不导入ROS或SDK。遥操已有session本轮保持兼容，共享网关执行面，不同时重写其按钮/采集生命周期。

轨迹必须saved/QC、源MCAP hash匹配、具名关节/单位和model hash/base/tip相同。源时钟重基到本次单调时钟、倍率显式；迟到停止，不重用旧ownership。起始夹爪目标需证据，不能由反馈补动作。起始对齐阶段保留当前夹爪，RUNNING才恢复片段目标。停止只尝试新鲜反馈hold，无默认home/disable/jaw-close。

推理fixture采用单在途后台worker，HTTP服务独立进程可选。输入真实fake RGB bytes/state；输出版本化policy-chunk/1、request/epoch/观测时间和显式动作语义。超时/旧结果/空队列等失效必须退出执行；mock只接fake设备。它不是ZeroWAM协议，也不等于真实相机/策略闭环。

workflow-session/1与experiment-graph/1分离：前者绑定本轮native执行子集，后者仍为逻辑图模板。不得把未绑定的相机/history/任意planner节点称为已经动态执行。预检不构建设备；物理执行同时需要明确backend、deployment和--execute。后续扩展真实策略与三图统一启动时复用source/session/gateway，不在模型adapter中增加硬件写入口。

代价：物理replay与fake推理不证明真实GPU/VLA支持；没有任意图解释器、训练writer或新相机episode。现有live-teleop/2、real-episode/1/2和只读replay命令不变；新增协议需单独记录版本。
