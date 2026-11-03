# A4-S、A1、A2：从已有实验台到项目验收

更新：2026-10-16。状态：操作准备与验收设计；现场测试not_run。先遥操数采，再策略推理。当前CLI只有M1 fake和主机inventory，尚无可执行的真实双Piper采集/遥操命令。

## 1. 新优先级与复用范围

| 优先级 | 场景 | 当前已知 | 首轮终点 |
|---|---|---|---|
| 1 | A4-S：A4静态双臂子集 | Ubuntu24.04、双Piper+夹爪已可分别控制（用户报告）；双D435腕部；fixed=D435/D435i/D455之一；PICO型号待补、Quest3备用且可能占用 | 双臂遥操、三相机采集、停止/接管、QC与只读回放 |
| 2 | A1 | FR3、D405腕部、D435第三视角、GELLO/手机WebXR、Ubuntu22.04 | 先GELLO采集与相同数据管线，手机另验 |
| 3 | A2 | Piper、CamBot、CamBot上D435i、Quest3 WebXR、Ubuntu20.04 | 复用单Piper/VR/相机接口，加独立头控视觉臂与动态外参 |

剩余完整A3/A4/A5/A6保留ID；A4-S通过不覆盖轮式底盘、全身碰撞、头部相机或移动补偿。A4-S不必等待A1/A2全部环境通过后才推进。基础fake、最小模型/IK/仿真验证仍是真机命令前置条件，完整A3不提前扩张为必需大工程。

## 2. 你现在需要准备的材料

不要求先装新SDK、升级ROS或整理全部硬件。先保留已有能工作的环境，上传以下可得材料即可，缺项明确标unknown。

| 材料 | 用来确认什么 |
|---|---|
| PICO设置中的准确型号、系统版本、浏览器/App版本；使用控制器还是裸手 | WebXR与原生XRoboToolkit/televuer路线是否适用。Quest3当前不可用不阻塞PICO能力检查 |
| 双Piper照片/型号/固件、夹爪规格，已有控制仓库路径/commit或源码快照、实际启动命令 | 锁定已工作的SDK/ROS/固件和接口；命令只作审计，不在本轮执行 |
| 左右CAN名称/USB适配器身份、夹爪反馈/开口单位、已有停止方式与现场保护 | 防左右串接、模式误配；不能将disable或最后目标保持默认视作安全停 |
| 两臂基座安装关系、桌面/夹爪/腕部相机支架、TCP与已知标定 | 双臂共同坐标、FK/IK、工具与碰撞范围。历史快照的0.13m TCP/外参不直接复用 |
| 三台相机型号/serial/USB连接；实际固定相机先是哪一种 | 绑定left_wrist、right_wrist、scene_fixed；当前型号先验收，另外两种保留未验证分支 |
| 首个简单任务、希望记录RGB还是RGB-D、是否需要视频回传头显 | 固定相机流规格、任务验收与吞吐要求。先桌面可直视遥操可降低视频回传依赖 |

PICO头显透视摄像头权限与机器人RealSense回传是两件事；不因为某原生客户端需要企业/VST权限，就推断普通controller姿态读取必需相同权限。

## 3. 三台主机的第一步：只盘点环境

已收到的7页交付资料见[手册审阅与SSH检查](2026-10-16-a4s-manual-review.md)：提供venv_piper/旧piper_sdk、Ranger Air和升降线索，但CAN文图不一致、左右臂身份未知。A4-S固定底盘与升降，记录安装状态；不照抄整机启动、CAN激活或末端ctrl示例。

工具：[collect_host_inventory.py](../../tools/collect_host_inventory.py)。它只用Python标准库读取系统/包metadata、USB sysfs和固定的只读命令，不加载机器人/RealSense SDK、不启动ROS节点、不启用CAN、不采图、不发设备命令。无sudo，不修改控制环境。Python3.8+是兼容意图，目前仅本机3.11验证。

将此脚本放到对应Ubuntu主机，在普通开发账号执行：

```bash
# Ubuntu 24.04双Piper主机，先做这一台
python3 tools/collect_host_inventory.py --bench A4-S --output artifacts/preflight/a4s-host.json

# FR3的Ubuntu 22.04主机
python3 tools/collect_host_inventory.py --bench A1 --output artifacts/preflight/a1-host.json

# Piper/CamBot的Ubuntu 20.04主机
python3 tools/collect_host_inventory.py --bench A2 --output artifacts/preflight/a2-host.json
```

这些是在各自主机运行的命令，不是在Windows一次运行后代表三台结果。如果只拷贝脚本，调整脚本路径即可，输出文件须尚不存在。

知道实际源码目录后，可附加`--repo-root /absolute/path/to/robot-scratch`及重复的`--reference piper=/absolute/path/to/working-driver`等参数。Git只读查询记录HEAD和tracked改动，**不检查untracked文件**；dirty内容还需patch/hash。包版本只代表运行脚本的这个Python环境，必要时在现有驱动/相机环境各跑一次，用不同输出文件名。

没有ip/lsusb/lspci或权限不足会写not_available/failed，不要求为盘点修改系统；退出成功只表示报告生成，不是硬件准入。脚本不会自动识别PICO型号、Piper固件或相机流规格，这些另靠资料/后续已审计设备探测获取。

## 4. 固定源码与环境，不替换现有可用路径

主项目还没有commit，跨机前建立一个可识别基线或小型源码包与hash；不要执行`git add .`把14个参考仓库、视频和环境一起纳入。Windows与各Ubuntu用独立checkout，保留现有机器人工作区。

核心Python3.11环境与Ubuntu20.04的ROS/Foxy/Python环境分开；通过已定义接口交换数据，不把rclpy或厂商包强装进一个统一venv。A4-S实际已用何种ROS/SDK仍待盘点，Jazzy是候选而非升级要求。

原有供应商demo能动只证明已有路径可工作；我们需要接入guard、时间/标定、数据和接管并留下项目证据。参考：[仓库索引](../reference-repositories.md)、[M2实施计划](../../plans/002-a4s-teleop-acquisition.md)。

## 5. A4-S分阶段操作与放行条件

### G0：输入与观测分开确认

**PICO先行**：确认准确型号、系统和输入方式；先录左右controller的6DoF pose、buttons/trigger/grip、追踪有效性、来源时间/接收时间与参考空间。不连Piper。测试静置、只移动头、左右手分别移动、释放deadman、控制器遮挡、浏览器退出/重进和重置参考原点。

优先审计现有QuestArm/CamBot的独立WebXR客户端；浏览器必须实际具备所需immersive/session/controller能力。若这条路径在该PICO型号不可用，再选择对应原生XRoboToolkit客户端+PC服务。两者统一为输入适配器，不把Quest3设为必须可用的前提。当前项目尚无独立VR录制CLI，不要运行完整上游双臂launch来“试一下输入”。

**相机先行**：确认serial与物理角色，枚举实际支持流，再逐台开流→三台同时开流。首版可先三路RGB（例如640×480/30FPS作为待验证候选），RGB-D和头显显示分别增加。D435i的IMU、D455内参/视场/固件不能当作D435的同值替代；重启/换口后角色仍按serial绑定。

逐帧保留原始时间、时间域、frame seq、host receive time、内参/畸变/对齐方式；depth启用时加depth scale和原始深度引用。跨相机软件对齐先测偏差，不默认具有硬件同步。先短录、再10分钟无运动连续采集作为候选稳定性检查，报告FPS/掉帧/延迟/内存/磁盘；这是现场计划，未执行。

三路640×480×30的应用层RGB+16-bit depth约138MB/s，未计编码和其他开销；它是数据量估算，不是实际USB总线带宽结论。需要看USB控制器拓扑并实测，不能只数USB3插孔。

**双臂反馈**：先从已经运行且确认无写副作用的反馈路径读取，两侧joint order、关节/TCP单位、夹爪、状态/错误和时间戳各自保存。主动固件查询、SDK connect和驱动launch不是默认被动读：先审计TX/初始化，不能把`auto_enable=false`等价为零写入。当前inventory不执行这些探测。

### G1：在设备外验证组合

实现并跑M2双6关节/夹爪/三相机fake；固定URDF、TCP及双臂安装外参。先FK对齐真实反馈，再把VR增量目标交给IK/最小仿真或离线录制流验证。保持所有真实命令出口禁用，shadow记录proposal及拒绝理由，命令写入计数必须为0。

关节限位、速度/加速度/单步变化、IK残差/超时、桌面/两臂/夹爪/腕相机碰撞与状态新鲜度分别验证。原点改变后重新clutch/对齐，不能沿用旧参考。不能以截图里“看起来方向一致”替代数值与动作语义核验。

### G2：现场明确安排后的受控真机验证

现场人员准备既有保护与停止手段，按固定操作协议推进：

1. 一臂动作、另一臂保持既定安全状态；先小范围关节/夹爪，再TCP映射，不自动回零。
2. 另一臂重复同样验收，确认左右不串。
3. 两臂分隔工作区动作，通过后才测试共同工作区。
4. 演练deadman、追踪丢失、超时、组故障、接管及重连；优先在fake/shadow注入，物理故障按已验证停止协议受控测试，不直接建议带载拔CAN或掉电。
5. 明确SDK/控制器对停止、失联、进程死亡的实际行为；保证最终guard在设备侧且所有命令出口受约束，不能只有上层topic过滤。

阈值由现场基线和设备模式固定后写入profile，不能沿用M1的20ms/100ms/5s测试值。无明确物理请求、未通过G1、停止行为未知、碰撞模型/工具或左右身份未核验时不开放命令入口。

### G3：遥操采集验收

固定一个简单任务，候选至少20个完整episode，另留中止/故障/接管样例。记录任务、操作者、左右端点/夹爪、VR原始输入、映射/IK、guard、实际下发/receipt、反馈、三相机、标定/资产和环境版本。

检查文件完整性、camera serial角色、时间对齐误差/丢帧、动作/反馈关联、拒绝与接管标注；回放只能检查数据，不自动重放到机器人。若需要训练出口，再用固定LeRobot版本验证导出可读取；采集链通过不保证数据量足够训练任务。

**阶段通过条件**：按既定profile独立复现G0–G3，实际停止/接管有证据，正常与中止数据可区分，未测试分支清楚标记。记录表使用[验证模板](../../plans/templates/validation-report-template.md)，A4-S结果不自动授予A4完整场景支持。

## 6. A1与A2怎样接着做

**A1**：复用相机/记录/QC及端点契约；FR3设备侧仍用匹配Robot System/FCI/libfranka/franka_ros2的实时Linux环境。先Ubuntu22.04核心测试、只读反馈、GELLO原始输入与零位/关节顺序，再模型/FK/受控映射，最后记录D405+D435的任务episode。GELLO启动自动位置同步必须改成明确交接；手机WebXR为独立分支，PICO通过不替代手机证据。

**A2**：复用已验单Piper、输入与RealSense接口，保留Ubuntu20.04控制域；本地QuestArm快照已有CamBot/RealSense与旧环境经验，先比对其dirty SDK/驱动版本。先固定CamBot不动完成手柄→单Piper采集，再独立验证头显→CamBot，最后组合两条控制链。移动相机必须关联每帧CamBot反馈/时间和动态安装变换，不能使用单个固定外参。请求仍为Quest3 WebXR，暂用PICO实验不能写成A2完整验收通过；设备占用时继续无设备/单链验证。

## 7. 之后才进入策略推理

在采集链稳定后选一个明确模型/权重、观测/动作语义、norm/预处理与GPU环境；使用对应数据版本。先离线输入输出检查与shadow，再按单臂→双臂闭环评测及人工接管。模型返回意图不拥有SDK权限，队列在设备侧，epoch沿用；实际延迟/动作年龄及任务成功率另测。

当前资料不够确定选ACT还是VLA，也不应因示例仓库包含某模型就默认兼容本台架。首轮不启用RTC/MPC来掩盖动作语义/时延问题。
