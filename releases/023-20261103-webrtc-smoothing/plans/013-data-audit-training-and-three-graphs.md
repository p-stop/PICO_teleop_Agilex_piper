# 013：数据审计、训练视图及三种运行图

2026-10-19，complete（调查、设计及无硬件软件切片）。用户要求按序完成连接、3集数据/日志审计、训练字段与LeRobot v3转换构思、Zero-WAM/VLA推理图、轨迹回放及统一图启动设计。模块化/通用化/配置化优先；不把设计图当已运行的物理实现。

顺序与验收：

1. SSH使用更新配置，核验同一主机身份；只读盘点`~/robot-infra/dataset/new_test`及对应session，不改源数据/日志或运行服务。
2. 逐集核对manifest/QC/索引/MCAP/视频，检查RTT/输入、相机、IK/写盘时间关联，区分已证实的断流与未证实根因；输出可复用离线审计工具及研究报告。
3. 训练数据报告：三RGB、可选三depth、关节/夹爪state、最终发布command action与原始输入意图区分；因果对齐、起始目标/稀疏目标保持、单位/顺序/有效掩码及深度缺失处理；确定LeRobot v3适配边界，先实现不依赖训练框架的可审计训练视图/转换预检最小切片。
4. 核查Zero-WAM论文/官方代码的观测、动作、缓存、时序、上下文、算力与部署接口，设计VLA/WAM graph及改动清单，不能承诺预训练权重直接兼容双Piper。
5. 比较观测回放与命令回放；提供不连接硬件的轨迹检查/调度验证，再设计经共同网关的物理回放。不直接重放ROS/SDK字节或旧lease。
6. 形成采集/回放/推理三图模板和共同端口/执行面，新增版本独立于M1 fake graph及已有物理session；完成配置验证/fake测试及文档状态更新。真机动作与GPU模型运行不在本轮默认执行范围。

范围控制：不一次实现完整图引擎、完整LeRobot导出和完整Zero-WAM部署；但所有明确要求的调查、报告、图及下一步可运行的无运动验证必须交付。若审计定位到可证实的软件bug，先小范围修复并回归；网络因果不足不盲目调超时。

checkpoint：已读AGENTS、onboarding、架构/状态、计划001/012及CLI/session/数据实现。新IP为192.168.87.126；StrictHostKeyChecking初次因无该IP记录拒绝，用旧IP已信任的HostKeyAlias=192.168.87.130核验成功，未放宽密钥校验。current仍012；8445/8446关闭。new_test含已保存episode0/1与.incomplete的episode2，三集均有3个MP4。待审计。

审计/用户澄清完成：两集saved、QC/deep过；第三review、固定RGB最大197.477ms失败，deep过，无queue drop/writer error。第二集RTT557.7ms，第三结束后client_event836.4ms/stale ticket；不将其归为相机QC直接原因。gap期间metadata9440…9444连续，不能仅据此归因Wi-Fi或相机停机。无depth；4pose流约180Hz，全部原生/转换来源清楚。用户确认未换相机、当前角色正确（022422072252左、342522071110右、254922307547固定）；历史身份差异不猜。三集任务仅手感/质量工程测试，任务/成功失败待人工标注。ZeroWAM在独立服务器，GPU型号尚未提供。

四份报告：research/2026-10-19-new-test-audit.md、training-data-format-report.md、three-workflow-graphs.md、research/2026-10-19-zerowam-deployment.md。ZeroWAM固定提交08e2c4ae41e2b63573a299825cebe6753481407c，API公共限流后改用官方codeload文本研究，未安装模型。其16维EEF/初始参考、缓存与lerobot0.3.3不等于本框架joint14/v3出口，需独立adapter。

实现：共享real reader、另目录audit、training-view/1确认目标/causal state/image refs/未知掩码、离线trajectory-check/TimelineSource、三图typed compiler。真实视图ep0 1858/740有效、ep1 1724/1722有效，原始时间线10509/8687条；未执行。episode0早段夹爪目标证据缺失，未以实测补目标。新context.initial_targets只记publish返回后的目标，支持以后初始标签。

修复：旧诊断总512MiB上限已接近，改默认128MiB追加分段、可配总限/磁盘保留、不删除历史；同capture/record FPS不再门控丢帧，显式降FPS才RateGate；新增callback seq/writer计数和ACK input_ms。未证明旧197ms空洞/RTT根因已解决，待现场并发验收。

验证：Windows261通过/10skip，Ubuntu274通过（ROS localhost，无设备），Node2通过。源码树0b366dade00cbfbb6048dd85c979ac86d5a423daf4ec429b29e9dec8cc43cf91；软件测试zip c275023538a4bac2dbaf23987fdaa0d46ad65176757ca4f5d14de19a86f5f345。隔离测试releases/013-20261019-software-test；源数据sidecar不变，派生审计runs/013-audit-20261019、视图runs/013-training-views。没有物理实验。

最终checkpoint：含文档快照`artifacts/preflight/013-validated.zip`，184文件，SHA256 `590a3724194cdad1895ff812e6eb7a8a95e2e06d527f425b19cc349d55d3cf78`；源码树与被测试版本一致。离线wheel/sdist构建成功，检查新模块/报告/三图已入包、参考仓库/数据/日志/密钥未入包，收据`artifacts/preflight/013-package-validation.json`。

机器人`current`已切到`/home/ros/robot-infra/releases/013-20261019-workflows-validated`；旧012版本保留，配置/manifest分别备份`profiles/robot.session.pre-013.json`、`release-manifest.pre-013.json`。配置仅补默认diagnostics分段参数；相机/驱动/控制参数未变。raw_mcap与mp4的collect --check-only、三图experiment-plan全部通过；入口脚本hash未变；8445/8446保持关闭。远端`offline-deployment-013.json`、`offline-tests-013.json`已取回本地`artifacts/preflight/`。部署没有启动任何物理服务。

验收：六项调查/设计已交付，四报告、ADR0015、配置模板、离线工具和双平台回归完成。后续任务依次为：共同执行session与source协议→轨迹shadow/现场短轨迹→mock policy/调度→ZeroWAM服务桥→graph物理启动统一；LeRobot官方v3 writer在独立数据环境另做最小导出。上述物理runner、模型桥和v3 writer均未实现，不计为本轮已验证功能。真实任务文本/成功失败需人工标注，不因capture QC通过改为成功。
