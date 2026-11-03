# ADR-0002：推理时序与运动执行分层

日期：2026-10-11。状态：设计决定，接口仍为草案。

## 背景

策略频率、推理延迟与设备伺服频率不同；RTC、TE、IK、MPC 解决不同问题。统一“后处理列表”会掩盖动作空间、时域和控制权限。

## 决定

- 定义拟议的 PolicyArtifact、ObservationSnapshot、ActionChunk、MotionProfile；各自版本化。
- PolicyAdapter 输出原生动作与时间语义；ActionScheduler 做时间对齐、队列与过期处理；Mapper/Planner 做显式语义转换；MotionExecutor/Controller 跟踪；最终 guard 是唯一硬件命令入口。
- native 模式也必须经所有权和安全检查。TE/RTC 的兼容由 adapter 能力声明与测试决定，默认不叠加；RTC 不只是队列 smoothing。
- 每次 session/reset/接管/故障更换 epoch，撤销旧 lease、清除 chunk/规划/控制器状态并拒绝旧结果。重连不自动恢复运动。
- 调度前缀必须跟踪承诺目标与执行 receipt；guard 修改/拒绝或跟踪偏差显著时使前缀失效并重规划/停止。
- 可选 IK、轨迹生成、路径规划、MPC 不替代最终 guard。重规划器输出同样带 provenance、有效期和授权 epoch。
- 全链保存 raw policy output → fused/scheduled → mapped/planned → guarded → driver receipt → feedback；训练导出显式选动作标签，不混为一个 action。

## 后果与替代方案

更多可测试边界和 metadata；部署 profile 需兼容检查。拒绝策略直接调用 SDK、自动串联所有优化、遇到超时永久保持最后动作。先做 stub 与同步/native，后做异步/IK，RTC/MPC 按需求推进。

验证：乱序、重复、超时、队列欠载、接管旧结果、IK 失败、MPC deadline miss 与 guard 改写；首版全部 fake/sim。参见[调研](../research/2026-10-11-teleop-inference.md)。
