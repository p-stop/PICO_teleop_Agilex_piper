# Robot experimentation infrastructure

2026-11-03 023（021-webrtc-r3＋022遥操平滑）：保留WebRTC输入与metrics统计；输入One-Euro滤波＋锚点平移/旋转死区、IK收敛门槛（converged或残差<5mm才跟随）、下发关节每周期限速（默认0.8rad/s）叠加一阶低通；session可选teleop_filter节调参。仅改teleop_session.py及其测试，其余文件同021-r3。

2026-10-23性能候选020：[通信/线程与QuestArm对照](docs/communication-and-performance.md)、[11次相机与网络验证](docs/validation/2026-10-23-communication-performance.md)。新增分段计时、按需内存预览、显式JPEG归档/Image QoS与独立诊断工具；正式current仍018。已确认图像接收缺失和独立网络尾延迟，尚未改ACK/媒体协议或完成双臂并发性能验收。

2026-10-22正式采集：[完整操作命令](docs/episode-collection.md)、[配置/验证](docs/validation/2026-10-22-formal-collection.md)。独立formal-018配置实现松开打开/按下闭合、三RGB MP4＋仅头部原始深度；启动/home/暂停不主动开合。相机10秒记录/deep过，无机械臂动作，完整PICO并发由首条采集验收。Windows284/Ubuntu297通过。

2026-10-20新增：[轨迹回放/假模型操作](docs/replay-and-mock-inference.md)与[验证记录](docs/validation/2026-10-20-replay-and-mock.md)。A4-S已现场通过起始对齐＋3秒native轨迹回放；独立进程HTTP假模型＋fake三RGB/设备正常及错误路径通过。新增workflow-run，保留原采集入口；不是任意图解释器，未接真实模型/真相机推理。Windows278/Ubuntu291通过。

2026-10-19新增：[三集数据与卡顿审计](docs/research/2026-10-19-new-test-audit.md)、[训练字段/夹爪目标/LeRobot v3设计](docs/training-data-format-report.md)、[采集/回放/推理三图](docs/three-workflow-graphs.md)、[ZeroWAM代码与部署研究](docs/research/2026-10-19-zerowam-deployment.md)。可运行离线audit/训练视图/轨迹检查和图预检；统一物理graph runner、LeRobot writer及模型桥接尚未实现。下面旧切片证据保留，当前状态以project-status为准。

包metadata0.3.0，含尚未发布的fake多端点和A4-S真机采集增量。2026-10-18已现场跑通双Piper+独立夹爪+PICO遥操、三相机原始RGB记录、A保存/X丢弃与QC：首个保存episode26.18秒、2.18GB，三路约30fps，deep完整性检查通过。机器人可独立命令启动，无Windows运行依赖。Windows218通过/1跳过、Ubuntu222通过、Node2通过；M1/fake契约保留，真实策略尚未完成。

优先A4-S（静态双Piper）→A1→A2，先遥操数采，再策略推理。[M2计划](plans/002-a4s-teleop-acquisition.md)仍为部分完成；一次合格RGB采集不代表长期网络可靠性、深度或跨机器人支持已验收。

新增可选 `collect --image-storage mp4`：通用图像后端保存各RGB流MP4、事件/深度MCAP与逐帧时间索引，原始模式仍默认。Windows/Ubuntu软件与离线重编码通过；实时MP4采集和完整LeRobot v3导出另验。

新增可配置末端观测：Piper原生XYZ/Euler整数保留；驱动转换Quaternion单独标记来源。字段、形状、单位、时间与读取代码见[给supervisor的数据格式报告](docs/collection-data-format-report.md)；新增流尚待现场验收。

- [带图的通俗数据流报告](docs/a4s-dataflow.md)
- [真实双臂运动、IK与日志完整性报告](docs/validation/2026-10-16-a4s-live-control.md)
- [采集操作员手册：启动命令、VR按键、保存与排错](docs/episode-collection.md)
- [采集技术说明：部署、相机配置、时间戳与QC](docs/episode-storage-and-configuration.md)
- [可选MP4存储、时间索引与LeRobot导出边界](docs/recording-storage-options.md)
- [首个真实保存episode与完整性验收](docs/validation/2026-10-18-a4s-link-and-episodes.md)
- [自由遥操 session：一条命令、A键回位/开始/结束、夹爪](docs/teleop-session.md)
- [旧版真机部署、证书与停止](docs/live-teleop.md)

仓库根目录PowerShell，需uv和可用Python3.11：

```powershell
uv --cache-dir .uv-cache sync --locked --extra dev --python 3.11
.venv\Scripts\python.exe -m robot_infra validate configs/fake-control.json --dry-run
.venv\Scripts\python.exe -m robot_infra run configs/fake-control.json --output artifacts/my-demo.mcap --steps 500
.venv\Scripts\python.exe -m robot_infra replay artifacts/my-demo.mcap
.venv\Scripts\python.exe -m pytest -q
```

输出文件须不存在，重复运行更换文件名。500步产生5053事件、502次fake执行及四类预期拒绝；run自动验证MCAP与live时间线。所有时间是fake逻辑时间，没有真实采集或运动。

- [当前双臂VR graph、采集/推理共享边界](docs/a4s-graph.md)
- [多端点fake采集运行与审查](docs/collection-review.md)
- [共享执行Windows/Linux验证](docs/validation/2026-10-16-a4s-shared-execution.md)
- [为什么先做M1、如何运行和审查](docs/m1-review.md)
- [本机验证证据与限制](docs/validation/2026-10-15-m1-windows.md)
- [真实输入/观测的运行方法](docs/live-input.md)
- [A4-S真机与PICO本轮证据、限制和接续](docs/validation/2026-10-16-a4s-live-observation.md)
- [设备发现、配置模板与退出码](docs/device-discovery.md)
- [远端已有遥操/采集/推理代码位置](docs/remote-code-index.md)
- [旧机器人工作流是否闭环：代码用途、使用方式、数据流与历史证据](docs/research/2026-10-16-existing-robot-workflow.md)
- [本轮Windows/Linux发现验证](docs/validation/2026-10-16-discovery-and-audit.md)
- [Git基线、发布排除与独立部署](docs/release-and-deployment.md)

- [项目约束](AGENTS.md)
- [Agent入口与按任务阅读导航](docs/agent-onboarding.md)
- [AI对话组织、任务分工与交接建议](docs/ai-development-workflow.md)
- [首个fake控制/采集/回放切片计划](plans/001-fake-control-loop.md)
- [项目定位、闭环边界与快速入门验证目标](docs/positioning.md)
- [架构 v0.14、A4-S与原六项验收场景](docs/architecture.md)
- [本地14份参考仓库、代码入口与补充建议](docs/reference-repositories.md)
- [实现状态与下一切片](docs/project-status.md)
- [GELLO、手机/WebXR数采与推理/运动控制调研](docs/research/2026-10-11-teleop-inference.md)
- [跨机器开发、Codex远程项目与验证流程](docs/development-and-validation.md)
- [真机工作流、已有方案与定位调研](docs/research/2026-10-11-workflow-positioning.md)
- [架构调研计划](plans/2026-10-11-architecture-research.md)
- [定位核验计划](plans/2026-10-11-workflow-positioning.md)

后续任务可从[任务计划模板](plans/templates/task-template.md)和[验证报告模板](plans/templates/validation-report-template.md)开始；小任务按需删减。

M1控制/记录仍限于契约`0.3.0-m1`与固定fake拓扑；新`collect-*`命令只接受独立`collection-plan/1`的单组多端点fake，记录为`collection-event/1`，不接受真实模式或任意graph；发现报告与绑定配置使用独立的`device-discovery/1`、`device-bindings/1`。独立观测adapter使用各自诊断格式，未扩展M1拓扑；实验性live-teleop入口独立提供双臂真实backend；高级推理/GUI仍为设计。[M1兼容边界](docs/adr/0005-m1-fake-contract-and-evidence.md)、[发现设计](docs/adr/0007-discovery-and-explicit-device-binding.md)。真实机器人测试必须由用户明确请求。

Linux源码检查可先运行`python3 tools/discover_devices.py --output artifacts/discovery.json`，不需要安装SDK。复制`configs/device-bindings.example.json`至gitignored的`profiles/local/`后填写身份；Windows目前可处理离线报告，本机枚举会明确返回collector不可用。`relevant-repo/`和`artifacts/`为可选本地资料/证据，不随仓库发布。
