# A4-S 双臂真实位置遥操与三相机显示验证

日期：2026-10-16。范围：计划007的实验性真机切片；完整M2采集验收未完成。用户明确请求实际运动，在现场操作PICO、观察机械臂并可使用实体急停。本轮未对底盘、升降或夹爪发送目标。

## 结果

- **已跑通两条真实链路**：PICO左右手柄 → 框架相对映射/IK → 设备本地控制权/guard → 现有Piper ROS驱动 → CAN → 对应机械臂实际反馈。不是SDK运动demo，也没有让网页绕过网关。
- 用户确认两臂可运动，“上下左右好像是对的，松键后就是不动，符合预期”。这属于初步现场方向/操作验证；前后方向、外部TCP精度和双臂安装标定仍未验收。
- PICO确认中央大固定相机画面、两侧小腕部画面正常；桌面与immersive均实现。三路RGB真实提供预览。
- 本轮临时服务、相机与两臂驱动全部停止；8个已知项目PID经独立/proc检查均不存在。控制日志含operator_stop及撤权。未回零、未失能，不把进程退出等同于机械臂断电。

## 环境与身份

设备端ranger-piper：Ubuntu24.04.4、Python3.12.3、ROS Jazzy，既有piper_sdk0.6.1及Piper ROS驱动。两臂can0左/can2右；隔离ROS_DOMAIN_ID=64，命令/使能均重映射至本项目话题。驱动auto_enable=false、gripper_exist=false；旧enable_srv不调用。

相机角色沿用用户已确认的物理安装：左腕D435、右腕D435、固定D455。ROS640×480/15FPS配置；预览约每路8FPS上限，JPEG质量75。序列号及两种命名空间关联保存在本地忽略profile和原始manifest。PICO前轮UA自报4 Ultra Enterprise；当前profiles包括pico-4u/oculus-touch-v2/generic-trigger-squeeze-thumbstick，button1实测用于侧握离合。

项目源码独立放置于 `/home/ros/robot-infra-runs/007-probe-20261016T142159Z/checkout`。未覆盖供应商代码、安装系统包、创建Git远程或发布仓库。运行使用已存在Pillow；发现OpenCV/NumPy ABI冲突后改为Pillow预览，未更改原环境。

## 模型与不发命令的验证

显式URDF为设备既有 `piper_description/urdf/piper_description.urdf`，hash：

```text
22c15f95e50003b01713bae158638f7d19cdb71b1bd1095289865b835067002b
```

base_link→gripper_base，关节顺序joint1…joint6。第三方模型未纳入项目发布包。gripper_base不是经外部测量标定的指尖TCP。

框架FK与独立Pinocchio位置差约1e-16m，旋转差约5e-16rad；与SDK末端反馈位置差左0.039mm/右0.045mm、旋转差左0.000203rad/右0.000166rad。这验证模型/计算/消息一致性，不代表外部绝对定位精度。当前折叠姿态下±5/20mm位置目标的影子测试有多方向拒绝，向上小位移两侧可解；没有将局部DLS称为全工作空间规划器。

## 真机三轮与修复

live-01：三相机/驱动已通，头显旧页面取得控制权后约26ms即请求停止，没有输入帧，不算遥操成功。

live-02：浏览器保留旧页面，用新URL版本参数强制载入，并延后到可见跟踪稳定帧申请控制权。记录589个原始输入帧，左臂真实运动。右侧按握键退出控制的原因明确为 `IK seed outside explicit limits`：近零位测量有微小越限，异常被当作传输失败。新增显式0.005rad测量容差，只投影近限位种子，记录投影幅度，命令范围仍保持原模型限位；初始严重越限拒绝使能。原始反馈不被改写。正常hidden/visible-blurred单独记录，不再误标为clientError。

live-03：修复后两臂均运动，用户确认方向和松键表现。记录1813个原始输入帧、123092条反馈事件、2826条command（含保持）、2804条receipt、7188张预览索引、10次离合锚定。会话seq0…2550，实际收到1813帧，缺口738；采用单在途/最新帧替换，有意跳过部分帧，不能据此声称完整WebXR逐帧记录。运动约106.4秒的输入窗口外，日志仍持续记录观测。

| 实测片段 | 编码器/FK证据 | 边界 |
|---|---|---|
| live-02左臂首段 | 最大末端位移13.63mm，主要+Z；松键后前0.5s该段无关节变化 | 初始有界配置 |
| live-03右臂首段 | 最大末端位移63.77mm，其中+Z约62.90mm | 不是外部测量；不是全空间误差评测 |
| live-03左臂片段 | 一段最大位移62.46mm，其中+X约61.49mm | 操作者完整三轴动作未做标准化标定 |
| live-03松键 | 用户观察符合预期；多数片段前0.5s无变化，部分左臂片段有最高0.0222rad短暂收敛 | 不承诺瞬时硬停或已标定制动距离 |

live-03中IK共1353次，1068次收敛、285次到计算deadline，平均14.45ms、最大36.71ms。35ms是检查预算，不是硬实时截止保证。guard拒绝399次测试关节范围、7次速度和6次跟踪偏差。不可达/近奇异/姿态保持约束、局部迭代超时与调试范围共同影响操作体验；本轮没有证明IK质量优于旧系统。

## 实际开放范围与审批

初轮scale=1、保持朝向、夹爪禁写；4cm位移/0.12rad关节偏移、0.1rad/s、驱动5%。用户随后明确要求完全放开。无限幅/100%驱动速度的服务启动被自动审批拒绝，理由为超出窄范围约束的高风险实体运动能力；没有绕过该拒绝。

随后改为有界现场配置并获准启动：每次接合10cm、相对启动关节偏移0.6rad、速度0.4rad/s、跟踪偏差0.08rad、驱动20%，输入超时0.6s/反馈超时0.25s。仍保留模型关节限位、ownership/epoch、失联停止。最终物理证据来自此有界配置，完全无限幅/100%配置从未启动。

## 记录完整性与退出bug

三轮原始记录共保留30746张JPEG预览，逐张文件存在/hash校验全部通过；原始JSONL均可解析。真实格式为live-teleop-event/1 JSONL+有损JPEG sidecar，不是原始RGB/统一MCAP采集episode。

三轮退出时ROS信号处理提前关闭context，再次rclpy.shutdown报错，导致journal-summary/finalize缺失。原始日志保留，没有补造complete标签；QC标为diagnostic_incomplete_shutdown_bug。已修复为应用持有信号处理、先停线程后关闭ROS、独立finally关闭journal。修复后在ROS_DOMAIN_ID=65无设备驱动的隔离环境，定时结束及SIGINT两种退出都为exit0、finalize/summary存在、writer_stopped=true/error=null、stderr为空，且零使能/命令记录。**修复后的退出路径尚未再跑一轮物理采集**。

## 测试、版本与证据

- Windows/Python3.11.12全套182通过；Ubuntu/Python3.12.3隔离源码全套182通过。后者临时解包带许可/metadata的纯PythonMCAP，复用既有pytest/jsonschema，无安装、不启设备。新增17项覆盖运动学、网关、故障、测量容差、HTTP与异步日志。
- 本地baseline仍为5191923，实际新增源码尚未提交。最终无硬件验证源包hash：`bd7dfa8325da7db8e5d7f0bb7a3ea16815b2252f4bdc6d738d42577a69f1d7cb`。
- 物理运动用r5服务；收尾信号修复在物理服务停止后加入并完成隔离ROS验证，不能将两者混成同一次全栈验收。完整启动器已加入并静态检查，现场实际使用分阶段等价启动脚本，启动器本身尚未重跑整栈。

本地忽略证据：`artifacts/preflight/007-shadow-results.json`、`007-motion-final.json`、`007-shutdown-and-qc.json`、`007-shutdown-regression.json`、`007-full-linux.json`。封存包 `artifacts/live-007/evidence-007-v2.tar.gz`（约21.5MB）保留三轮全部JSONL、驱动日志和每角色/每轮3张抽样预览，其余预览原件仍在设备端对应live目录；封存包hash：

```text
34de1c1836a2ff4400c57dd66f20ae57d2fac948a22bf9d202fbd33ea9083a5f
```

最终live-03 events.jsonl hash：`7eaf0da7cee5978b00f3be8e4baa16aa451206abb5b92bae5e3d1259f3f8527a`。复现见[部署手册](../live-teleop.md)。

## 后续优先级

先规范可操作起始姿态、核验前后方向/TCP/双臂安装，建立连续目标/不可达/近限位IK基准并降低失败率；然后独立接入夹爪与六自由度遥操。随后把真实输入/命令/反馈/原始相机接入统一MCAP/episode/QC，实际完成训练数据采集，再接策略动作解码/调度/评测。夹爪、碰撞规划、进程崩溃后的独立硬件watchdog、策略推理、A1/A2/其他OS与机器人均未在本轮验证。
