# M2：A4-S双Piper遥操采集验证切片

日期：2026-10-16，更新2026-10-18。状态：in_progress（完整M2）；计划008/009已完成当前双Piper的VR/Pinocchio IK/物理执行和首个原始三RGB保存episode，QC/deep通过。任务级重复采集、外部标定、训练导出和真实策略仍待完成；证据见[2026-10-18验收](../docs/validation/2026-10-18-a4s-link-and-episodes.md)。下表历史计划能力按实际实现边界更新。

## 用户目标与当前事实

优先A4的静态子集A4-S：两台Piper+夹爪、两台D435腕部、固定D435/D435i/D455之一、PICO优先/Quest3备用、Ubuntu24.04。用户报告两臂已可分别控制，PICO浏览器UA报告4 Ultra Enterprise，当前固定相机确认为D455；设备设置与标定仍待核对。先完成遥操数采，再策略推理；随后移植复用能力到A1 FR3/Ubuntu22.04及A2 Piper+CamBot/Ubuntu20.04。

成功结果不是启动上游launch，而是在同一可追踪session中获得双臂/夹爪意图、guard、实际下发及反馈、三相机、VR输入、标定/时间证据；可接管、受控停止、读取/检查episode。更换固定相机以同一接口/独立profile表达，未实测型号不标通过。

## 起点与边界

- 先读AGENTS、project-status、架构§3–5/§8/§12–13、ADR-0005/0006、参考仓库索引和A4-S/A1/A2现场手册。
- M1仅2关节、1相机、固定7角色图、手动时钟和内存日志；不能改mode绕过validator直接接SDK。
- 现有驱动/固件/ROS/SDK先冻结，优先复用已工作的台架路径。新SDK/ROS仅在独立环境比较，不顺带升级固件、系统或控制栈。
- user应用只调用session/mapper，SDK持有者有设备本地唯一写入入口、lease/epoch和最终guard；上层topic中转不自动阻止其他publisher旁路。
- 不在此切片实现底盘、全身控制、GUI节点编辑器、通用训练平台、RTC/MPC或任意图编排。
- 仿真/无硬件前置保留，但不要求先完成整个A3。物理测试须用户明确安排并现场执行。

## 里程碑与可验证交付

| 阶段 | 最小交付 | 验收门槛 | 本轮状态 |
|---|---|---|---|
| M2.0 | 型号/基线/版本/USB/CAN盘点；PICO输入路线决策 | 已有驱动和实际设备身份可追溯；缺项列unknown；不改变现有控制 | 远端审计/被动发现/身份绑定已完成；PICO设置及标定等仍待补 |
| M2.1 | 具名执行端与观测源契约、最小DeviceBackend接口；双6关节/双夹爪/三相机fake配置 | 左右隔离、单位/关节顺序、状态/时间/provenance明确；M1旧配置继续通过或明确迁移 | fake契约及当前Piper ROS backend已实现；真机live/real-episode独立版本，不冒充完整通用M2契约 |
| M2.2 | per-endpoint lease/epoch + 双臂ControlGroup、设备本地时钟/后台超时、受限事件/图schema | 组申请失败回滚；一成员失联按组策略撤销；关闭客户端/SSH不恢复旧动作；不能以手动tick作为实机watchdog | fake与独立live网关/设备时钟/后台watchdog已实现；通用独立端点/多组仍待补 |
| M2.3 | 三相机/双臂反馈的采集与有界记录管线；无运动的输入录制 | serial绑定角色；帧时间域与收取时间、掉帧/队列、内外参、depth scale；长录不积累全部RGB-D到内存 | 真实三RGB原始MCAP/有界writer/接收时间对齐已验；深度、外参和长时间负载未验 |
| M2.4 | PICO输入归一化→clutch/增量映射→IK/FK/最小sim或严格shadow | 跟踪丢失、原点重置、左右手交换、deadman释放、IK失败/跳解/碰撞/过期均拒绝；shadow无运动写入 | Pinocchio/FK/相对6D映射和当前限位内IK已实测；外部标定、完整碰撞与通用shadow验收待补 |
| M2.5 | 一个实际Piper backend的passive/read-only→单臂受控→双臂 | 先证明无意外enable/回零/夹爪写入；之后各阶段需现场准入和明确物理请求 | 当前审计ROS驱动/双臂/独立夹爪和完整用户session已现场确认 |
| M2.6 | 固定任务episode、QC与训练导出交接 | 正常/中止/接管均留证；先20个完整episode为候选验收量，用户固定任务与阈值；独立读取和导出消费方检查 | 首个26.179s原始RGBepisode保存与QC/deep通过，另有中断/丢弃证据；20任务episode及训练导出待补 |

单组fake与当前专用live路径均已有实测，不等于通用graph编译器/独立多组完成。底层驱动、映射/IK、会话和录制分层，M1/fake契约保留；外部TCP/相机安装变换仍需标定，不猜测缺失转换。

契约升级拟为独立的0.4草案，需实施前固定schema和M1消费方兼容策略；本计划不发布0.4格式或可运行M2配置。不得将二维fake向量扩为含糊的14维关节/夹爪向量。

## 双臂/三相机的关键设计

- 端点：left.arm、left.gripper、right.arm、right.gripper；每臂6关节，夹爪开口/力/状态按SDK明确单位。状态流与命令族分离。
- 相机角色：left_wrist、right_wrist、scene_fixed。arm_link→camera_optical安装关系有版本；固定相机是scene/world安装，不使用VR头位姿代替外参。
- 双臂安装外参、桌面、夹爪、相机支架/线缆碰撞范围纳入检查；单臂关节限位不等于双臂防碰撞。
- 输入先保留原始pose/buttons、追踪状态、handedness、input session与原始/接收时间；头显位姿在A4-S不直接控制手臂。断追踪/浏览器刷新/参考原点改变撤销映射及授权，重新校准/离合。
- SDK或ROS已经拥有CAN时不得再开第二个写入连接；选择现有ROS边界或独立SDK backend中的一条路径。
- stop按实机模式验证，不能把disable、电机掉电、保持最后目标或自动回零统一当作安全停止；进程死亡后的行为需要设备/独立保护证据。
- 三路视频独立有界队列，慢消费者/磁盘/网络不拖累控制loop；可在MCAP内记录帧或保留外部视频的逐帧索引/原始时间/hash。MP4帧号不足以替代时间证据。
- fixed=D435/D435i/D455为三个profile，角色/接口统一，内参/畸变/流能力/固件独立。IMU/depth等能力不能用假字段补齐；只测到一种时另两种not_validated。

## 必须通过的故障测试

1. 左右CAN/端点串接、交换关节顺序或camera serial，预检失败或身份变更触发重新准入。
2. 一臂lease/group获取失败、反馈陈旧、VR deadman释放/追踪丢失，两侧按配置进入已验证停止状态。
3. 同组旧epoch的排队动作、在途IK/策略结果全部拒绝；重连不自动使能。
4. 观测时钟域不明、时间倒退、IK不可达/碰撞/超deadline，清楚拒绝并记录，不能复用上次解。
5. 视频堵塞/磁盘满/进程异常，记录完整性与停止行为按声明验证；不能把不完整episode标完整。
6. 模拟/影子时实际命令写入计数为0；真实receipt区分submitted/sent/acknowledged/executed，不能沿用fake同步executed假设。

## 验收与交接

具体实验顺序、用户需要提供的资料和三台主机命令见[现场手册](../docs/validation/a4s-a1-a2-playbook.md)。每个阶段固定源代码/依赖/资产/标定，使用现有验证报告模板；候选时间/频率/阈值经基线后冻结，本计划不给未经测试的控制Hz或停止毫秒承诺。

之后先做A1、A2各自同版本核心无硬件测试，分别接入FR3/GELLO和单Piper/CamBot，复用采集/VR/评测工具而不继承物理通过状态。策略推理是后续切片：选一个明确模型、动作/观测、GPU和checkpoint，先offline/shadow，再单臂/双臂；不以服务器启动当作部署完成。

## 当前checkpoint

已完成：参考源码审计、M2计划、主机inventory工具及现场步骤设计。
2026-10-16补充：已阅读交付手册全部7页，见[手册审阅](../docs/validation/2026-10-16-a4s-manual-review.md)。文档提供Ubuntu24.04、ROS“Jazy”、venv_piper/旧piper_sdk、双CAN、Ranger Air及升降线索；不是现场验证。正文与截图的CAN命名、遥控开关标注有差异，SSH后只读核对。相机/VR及左右对应仍未明确；尚未SSH。
等待资料：PICO型号/OS、现有驱动实际路径/版本/启动方式、固件、serial/端口、安装尺寸/外参、固定相机实际型号与任务。
用户补充：PICO外形疑似PICO 4 Ultra；准确型号、消费/企业版本与系统版本尚未从设备设置确认，不作为已验证兼容证据。SSH目标地址/认证尚待提供，尚未配置连接。
后续checkpoint：用户已配置ranger-piper；SSH无需交互连接及只读inventory成功，见[现场盘点报告](../docs/validation/2026-10-16-ranger-piper-ssh-inventory.md)。实际Ubuntu24.04.4/Python3.12.3，系统包metadata piper_sdk0.6.1，三CAN均DOWN，USB见双D435+一D455。上述旧SSH待办已解除；左右身份、实际源码/venv/ROS、相机安装/流和PICO仍待核对。M2.0仅部分完成，M2.1–2.6不变；无设备控制。
本轮新增：plans/003完成远端代码索引和独立版本的被动发现/角色绑定。用户确认can0左臂/can2右臂、左腕022523021289/右腕342123026960/固定D455261143061977，当前profile匹配成功。纠正：旧相机launch使用SDK serial，后来已通过USB端口关联证明有效，不能用USB descriptor serial判定失配；旧记录/推理多为左臂+底盘+两相机，不能直接标为本轮双臂链路。SDK0.6.1源码与安装接口hash已核对，保留原环境。
下一代码任务范围固定为M2.1–M2.2：N个具名端点（A4-S模板双6关节+双夹爪）、明确单位/关节顺序、per-endpoint与ControlGroup、系统时钟/后台超时fake；契约迁移独立评审，原M1不松绑。随后M2.3先三相机/反馈/VR独立记录和有界管线，再M2.4映射/模型/IK，最后设备backend与遥操数据验收。主机SDK/ROS目录通过配置选择，不复制旧绝对路径/坐标/serial。
硬件结果：not_run；本轮没有连接任何机器人、相机或头显。

计划004后续checkpoint：已实测独立PICO输入、三路640×480 RGB与双臂纯接收六关节反馈，见[真实观测报告](../docs/validation/2026-10-16-a4s-live-observation.md)。此前not_run是历史状态。Windows125项/Ubuntu隔离切片45项通过；多端点/执行组runtime、持续同步episode、映射/模型/IK与物理命令尚未完成。下一实现优先M2.1–M2.2，随后持续观测/时序与M2.4；不把输入连接当作M2全量验收。

计划006 checkpoint：用户再次确认双臂VR，旧负责人认为旧IK效果不好；当前方向是框架提供新映射/IK、复用现有ROS驱动，主从仅作替代意图源。已固定[graph](../docs/a4s-graph.md)，实现独立collection-plan/1、collection-event/1的单组N端点/驱动批次fake采集（M2.1部分、M2.2组授权/epoch/fake超时部分、M2.3流式fake记录部分）；不发布完整0.4硬件契约。Windows/Ubuntu隔离源码各165项通过；真实IK、连续观测episode、本地watchdog和ROS命令backend仍未实现。上表已按本次增量更新，以checkpoint及project-status和对应验证证据为准。
