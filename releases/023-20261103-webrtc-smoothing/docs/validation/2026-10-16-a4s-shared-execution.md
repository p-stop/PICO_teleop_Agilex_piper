# A4-S graph与共享fake执行验证

日期：2026-10-16。基线5191923上的未发布增量；包metadata仍0.3.0，M1契约仍0.3.0-m1。新collection-plan/1、collection-event/1仅表示多端点fake子集，不发布完整M2硬件协议。实施[计划006](../../plans/006-a4s-graph-and-shared-execution.md)、[graph](../a4s-graph.md)、[审查说明](../collection-review.md)、ADR-0009。

## 结果

| 验证 | 环境与结果 | 证据 |
|---|---|---|
| 单元/配置/集成全套 | Windows/Python3.11.12，165 passed，含原125与新增40 | artifacts/2026-10-16-collection-windows.xml |
| 同一源码全套隔离测试 | ranger-piper Ubuntu24.04.4/Python3.12.3，165 passed | artifacts/preflight/collection-linux-tests.json，含JUnit与传输源码包SHA256 |
| 20步采集CLI/独立读回 | 四逻辑端点、两fake backend、三fake camera；人工标签→stub-policy标签 | artifacts/2026-10-16-a4s-fake-collection.mcap |
| 完整episode结构 | 394事件；40次backend调用/command/receipt/feedback；63个camera事件；没有缺失backend/camera | collect-demo返回结果及collect-read再验证 |
| 构建/独立wheel | sdist/wheel构建与排除检查；源目录外collect-validate/demo/read及M1 validate通过 | artifacts/2026-10-16-collection-release-check.json |
| 文档与代码差异 | 48份Markdown/214内部链接检查零问题，git diff --check通过 | 同上；当前源文件hash另保存在artifacts/2026-10-16-collection-source-manifest.json |

Linux没有安装mcap；因此仅把开发环境的mcap1.5.0纯Python包、metadata和许可复制到临时测试目录，通过PYTHONPATH运行，使用现有系统pytest/jsonschema。没有复制Windows原生扩展，不使用LZ4/ZSTD压缩，没有pip/uv安装或修改供应商环境。临时源码/依赖/测试输出目录自动删除，本地保存结果。此结果现在包含M1 Linux源码测试，但不是锁文件对应的正式Linux安装/wheel部署验证，更不是任何物理控制验证。

## 关键证据

- 配置在backend构造前检查：模式/版本、精确字段、单位/关节顺序、限位/初姿、端点/相机重名、驱动内坐标冲突、完整组成员、纳秒整数和有限数值。
- 右侧目标不合法时两侧调用计数0；目标不完整/重复、不合语义、过大增量、NaN、陈旧反馈等均不写backend。
- 策略标签不能抢占更高优先级人工标签；人工明确takeover可撤销旧epoch，旧CommandSet不能因迟到恢复执行。
- 第二backend失败：左侧1次fake执行、右侧0次；保存分开的executed_fake/failed_execution_unknown，停止并撤销组。异常episode独立读回为aborted。
- 第一个发送耗时跨越lease期限，第二个发送前检查拒绝，避免只在一帧开头检查一次。
- 写command前记录失败，backend0调用且撤权。CRC损坏、缺footer/未finalize、缺必需相机以及fault后伪标complete均被独立读回拒绝。
- fault/reset/start不能把同一episode改标正常完成。snapshot缓存上限32，核心不硬编码双臂或三相机数量；另测一臂/夹爪/自定义相机配置。
- 原M1固定graph拒绝collection-plan/1；M1原有全部测试继续通过。

20步参考文件的events_hash为a2d42d1144966591cc3b315737fac3852c2a3a899753f78dd12d5619cb7f2d13；它是finalize之前按规范JSON逐行计算的SHA256，含本次session_id，换一次运行应不同。该值不是整个MCAP文件hash。

## 未验证范围

没有运行ROS驱动、物理命令、真实VR→TCP映射、真实IK/FK/碰撞、模型服务、GPU、chunk调度或真实视频持续录制。图中PICO输入、三相机和CAN之前已有独立诊断证据，但本轮新运行器只接受fake配置，不能据此宣称把真实输入/相机接成了同一个episode。背景watchdog和真实命令代理未完成；Windows/Linux手动fake时钟通过不代表实时停止能力。

用户对旧负责人经验的转述已写入graph和研究接续：旧双臂VR/IK体验欠佳不改变当前双臂VR目标；本框架负责新映射/IK与执行协调，现场现有驱动作为可复用边界。现阶段缺真实模型/TCP/安装标定和输入按键/运动阈值，未以默认旋转矩阵或旧ready姿态代填。
