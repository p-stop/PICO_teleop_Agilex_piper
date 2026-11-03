# ADR-0011：遥操会话与独立 Pinocchio 求解

日期：2026-10-16。决定已实现，物理验收分阶段进行。取代 v1 现场路径的直接入 VR 使能流程，不改变 M1 / collection-plan/1 契约。

用户要求同一命令启动、自检、A回位/A开始/A结束、双侧握离合、扳机夹爪和退出VR暂停。此前同步本地 DLS 的时间预算拒绝较多，不能让数值求解阻塞输入和会话管理；现有驱动的 enable 会隐式发送夹爪0，违背“home保持夹爪”要求。

决定增加显式 `live-teleop/2` profile 和独立 `TeleopSession`。HTTP负责接收，单独控制线程推进状态；每臂一个 spawn 求解进程，只保留最新目标，结果受 epoch/离合token/年龄约束。Pinocchio负责运动学及解析雅可比，SciPy负责有界最小二乘；复用设备现有包。不是自己另写 FK/数值求解器，也不为了复用 QuestArm 强装当前缺失的 Pinocchio-CasADi。旧 stdlib 模型留作 v1 兼容和独立 FK 对照。

Pinocchio SE(3)残差/Jlog6依据[官方 IK 示例](https://raw.githubusercontent.com/stack-of-tasks/pinocchio/master/examples/inverse-kinematics.py)，边界优化用[SciPy least_squares](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html)。借鉴本地 QuestArm 的上一解热启动、平滑项和反馈回位确认；不复制其固定 TCP/夹爪关闭/驱动自动使能。目标不可达时可配置接受 best-effort，记录真实误差；这不是轨迹规划或碰撞避免。

最终命令仍经过设备网关的 owner/epoch/单位/坐标/限位检查。取消 commissioning 特有限幅，不取消通信失效和语义校验。带 hash 的窄包装器复用已审计 Piper 驱动，覆写使能副作用和线程退出；home/hold省略夹爪字段，明确的遥操扳机才命令夹爪。此消息语义依赖特定驱动源码 hash，换版先审计。

暂停后要求先看到中立按键，再按 A 执行 HUD 提示的下一步：原待机/回位阶段重新回位，原准备/遥操阶段进入遥操。第一轮现场发现“只恢复状态、不执行动作”的额外 A 看似无响应，因此去掉不可见的中间步骤并补回归测试；不自动恢复运动。

后果：增加可部署依赖和子进程，但单臂求解阻塞不会阻塞 A/暂停；进程卡死仍会导致故障，需要重启 session。Thread/Python/ROS 非硬实时，SIGKILL/断电时软件不能保证保持。硬件与输入绑定继续在具体适配层，未实现任意 graph 编译。录像/episode REVIEW及策略后续复用执行面，单独验收。
