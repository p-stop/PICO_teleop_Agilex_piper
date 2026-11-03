# 原生末端 / 转换姿态记录：软件验证

2026-10-18。用户要求原生Euler可保留，所有转换标明来源。数据字典见[报告](../collection-data-format-report.md)，实现边界见[ADR0014](../adr/0014-native-pose-observations-and-provenance.md)。

## 源码核对

机器人端只读读取SDK0.6.1及ROS驱动：SDK原生XYZ（0.001mm）/Euler（0.001degree）整数；driver转换为米/xyzw四元数。四元数算法为SciPy from_euler('xyz')，不是SDK原生四元数；PoseStamped frame_id为空。驱动/SDK文件hash记录在计划012和报告。没有初始化SDK、启驱动、相机或机械臂。

新增wrapper只复制已经连接的SDK缓存并发布native-pose/1；测试SDK替身仅提供GetArmEndPoseMsgs，无ConnectPort/Enable/JointCtrl等API，确认新发布不需要任何硬件写接口。原生整数、单位、SDK秒stamp保持；通用ROS订阅器用来源配置而非左右臂硬编码。Quaternion流有显式converted/conversion，原生流native/null，保留未知frame。

## 测试及环境

- Windows Python3.11.12：全套250通过、10跳过；8个Linux Bash用例、1个Pinocchio、1个ROS回环在此环境不可用。
- Ubuntu24.04 Python3.12.3 / ROS Jazzy：全套263通过，包括Pinocchio、真实MP4编解码、真实PoseStamped/String本机回环。ROS测试使用独立Context/executor、domain191、localhost，不构造物理设备。
- 新增测试覆盖通用sourceID、来源与转换配置、空/未知frame、原始整数/单位、非归一化四元数原样保留、invalid观测事件、raw/MP4末端记录/索引/对齐/deep、缺失/冻结/零源stamp，以及原生发布只读SDK缓存。
- 初次隔离测试未创建pytest basetemp父目录，ROS回环将独立Context交给默认executor而失败；修正harness和显式executor后重跑263通过。失败日志保留，不作为设备故障处理。

测试源码树SHA256 `391d5adb0e802e1ac4dcc7a4de517537fdddac8a4c40aacbb7d862270ee12b35`。Ubuntu测试目录`~/robot-infra/releases/012-20261018-pose-test`，完整日志`~/robot-infra/offline-tests-012.json`；初次失败日志`offline-tests-012-initial.json`保留。

## 部署静态检查

已切换`current`至`releases/012-20261018-pose-validated`，归档SHA256 `af5d8c1ecc9450ec0636047388bbde285333b31e652bd032458b5d8361dc6847`。profile仅增加原生发布topic与原生/converted各臂来源，旧配置备份`profiles/robot.session.pre-012.json`。raw_mcap/mp4的正式collect入口`--check-only`均通过且不构建设备，结果包含四个来源；默认raw不改。8445/8446未启动。收据`~/robot-infra/offline-deployment-012.json`。

## 证据限制

旧原始episode2只读抽查用于核对字典，没有回填新流或修改旧集。此次没有实时原生末端记录证据；真实源流率、左右身份/方向、工具点/外参、CAN多分量原子性、硬件时钟同步与VR/相机并发负载留待现场验证。部署后仍须对新一集实际存在的原生/转换来源、时间更新及QC进行验收；不把loopback通过等同于硬件已验。
