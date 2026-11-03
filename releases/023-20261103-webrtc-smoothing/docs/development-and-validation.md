# 跨机器开发与验证工作流

日期：2026-10-11。设计与操作说明，尚未配置远程连接或执行 Linux 验证。

2026-10-16接续：本地系统SSH已连接ranger-piper，完成只读源码/环境审计和临时目录中的19项发现测试；尚未配置桌面远程项目/迁移聊天，完整M1 Linux及真实控制未验。当前发布/独立部署以[发布文档](release-and-deployment.md)、[远端工程索引](remote-code-index.md)和[当前状态](project-status.md)为准，以下“本轮未连接”等描述对应原10-11方案阶段。

## 1. 区分三种连续性

代码连续性用 Git commit/patch，实验连续性用配置、依赖、校准与验证报告，聊天连续性由 Codex 的 host/会话功能提供。登录同一个账号或同步聊天，并不自动把 Windows 的工作目录变成 Ubuntu 文件系统。[官方项目与聊天说明](https://learn.chatgpt.com/docs/projects)明确区分聊天同步与文件访问。

推荐从 Windows 桌面通过 **SSH 连接实验室主机上的远程项目**。Codex 在远端读写源码、构建和测试，用户仍在桌面交互；机器人实时 runtime 由设备本机独立管理。此连接只解决开发执行位置，不承担遥操链或实时通信。

## 2. 在当前桌面继续使用 Codex、远端执行开发

依据[官方 Remote connections / SSH 与 handoff 文档](https://learn.chatgpt.com/docs/remote-connections)：

1. 给目标机配置具体的 SSH host alias，确认桌面能以开发账号 SSH 登录。
2. 目标机安装并认证 Codex，登录 shell 能找到 `codex`；配置该机自己的编译/测试环境、项目指令和所需插件。
3. 桌面 Settings → Connections 添加 SSH host，选择远端仓库目录，保存为远程项目。
4. 要移动已有聊天，先在目标机保存同一 Git 仓库的项目，再从聊天底部运行位置选择 handoff。该功能有版本/账号/组织条件，以实际 UI 为准。

SSH alias 模板（示意，不包含实际地址；本轮未写入用户配置）：

```sshconfig
Host lab-fr3
    HostName <FR3开发主机地址>
    User <开发账号>
    IdentityFile <本机SSH私钥路径>
```

当前聊天工具只列出了 `Local` 作为可用 host，没有已连接的实验室目标机；因此现在不能直接把此聊天移过去。仓库尚无 Git 提交，handoff 的仓库识别与状态转移也还未具备可验证基线。后续先将选定内容纳入 Git、建立双方一致的仓库身份，再连接目标机。本轮不替用户创建远程仓库、上传代码或修改 SSH/认证设置。

## 3. 在实验室电脑直接工作

若桌面 SSH 功能不可用，最稳妥的备用路径是 SSH 到目标机，在同一仓库运行 **Codex CLI**；[官方 CLI 文档](https://learn.chatgpt.com/docs/codex/cli)给出 Linux 安装/登录入口。可用 `tmux` 保持开发会话。目标机已保存的 CLI 会话可用 `codex resume` 续接；它不保证能直接打开本 Windows 桌面聊天。通过版本化文档交接需求和状态，不手工复制认证文件或内部聊天数据库。

2026-10-11 查阅的[Linux 桌面预览说明](https://learn.chatgpt.com/docs/linux/linux-app)列 Ubuntu24.04/26.04 为支持发行版，未列20.04/22.04。因此不能建议为装桌面 app 而升级现有 FR3/Piper 控制系统；这些机器优先用 SSH host/CLI，并先验证 CLI 的系统依赖。无需为此自建 Agents API 或 app-server 前端。

## 4. 一次开发—验证循环

1. **确定源码基线**：共享一个 Git 仓库，固定 commit；未提交开发内容另保存 patch 与 hash，禁止同时改同一 checkout。Windows 本地和 Linux 远程可使用独立分支/worktree。
2. **Windows 核心测试**：图校验、序列化、fake session、录制回放和 stub policy；不导入厂商 SDK、不配置真实 CAN/FCI。
3. **Ubuntu 无硬件测试**：在目标机相同 commit 上运行核心、网络边界和设备 adapter 契约测试。20.04、22.04、24.04 分别报告；CI 容器只能覆盖用户空间构建，不能证明宿主实时内核/USB/CAN 可用。
4. **MuJoCo 验证**：锁定引擎、MJCF、TCP/关节/相机资产，先单臂；测试输入映射、推理调度和故障，无任何真实驱动入口。
5. **只读 probe**：对设备、相机、主臂与资源盘点；先检查 SDK 初始化是否产生写操作，未知时不用其默认连接流程。
6. **真机测试**：必须由用户明确请求，并由现场人员准备设备、急停、使能与安全区；开发/无硬件 CI 的通过不能自动授予运动权限。
7. **回收证据**：远端生成 `environment.json`、`plan.lock`、测试结果、延迟统计、日志/MCAP 与 hash。仅同步诊断所需材料；本地状态文档记录证据路径与结果。

本轮只提出上述流程；没有连接任何远程机器，也没有安装软件或验证硬件。

## 5. 每台主机的 profile 与测试报告

推荐目录（拟议，尚未创建可运行配置）：

```text
profiles/hosts/              OS、CPU架构、Python、内核、GPU/CUDA、传输
profiles/devices/            固件/SDK、端口、总线、能力、停止行为
profiles/calibrations/       frame、joint order、TCP、相机、有效期与hash
configs/scenarios/           用户任务图
artifacts/validation/        本地输出，不把大日志/私钥纳入Git
```

报告至少包含：场景 ID、测试级别（static/fake/sim/read-only/physical）、代码与依赖版本、实际 OS/内核/权限、设备身份、校准、运行参数、执行命令清单、期望与实际结果、拒绝/失败原因、复现步骤、日志 hash。无硬件、缺依赖和未执行分别标 `not_run`、`unsupported`、`blocked`，不能写为 `pass`。

开发账号用于构建、日志读取和无硬件测试；设备 runtime 负责厂商访问和最终 guard。使用现有账号权限策略完成边界验证，不在 Codex 安装时顺带赋予 sudo 或总线写权限。现场停止不依赖 SSH、Codex 或 Windows 在线。

## 6. 环境差异的处理

- 核心为传输无关契约；驱动、运动库与模型分别隔离环境。Python 基线在首个 fake 切片时决定，不强迫 Ubuntu20.04 的系统 Python 跟随 GPU 模型升级。
- FR3 Ubuntu22.04 的 Humble 是候选路径，仍按机器人系统版本锁定依赖；双 Piper Ubuntu24.04 的 Jazzy 为候选。ROS 发行版支持矩阵参见[REP-2000](https://github.com/ros-infrastructure/rep/blob/master/rep-2000.rst)。
- Piper Ubuntu20.04 优先审计原生 SDK/已有驱动，ROS1 桥接仅局部保留；Foxy/Noetic 不作为新核心的跨机基础。不同 ROS distro 不依赖直接 DDS 互通来保证兼容，边界显式转换并测试。
- CamBot 上游 Python3.12+/Ubuntu24.04 与现有 Piper Ubuntu20.04 不一致：先测独立环境或旁机服务，若同主机移植失败就清楚报告，不能改变用户的20.04验收目标后宣称完成。
- GPU 推理环境可独立放在其他 Linux 主机，模型升级不强迫设备 OS/SDK 升级；网络断开由设备端停止策略处理。
