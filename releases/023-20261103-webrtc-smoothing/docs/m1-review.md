# M1如何运行、为什么先做、审查什么

日期：2026-10-15。实现版本0.1.0，契约0.3.0-m1；只在Windows/Python3.11.12验证fake。此演示没有真实机器人、相机、模型或GUI。

## 为什么先做

M1先让架构中的关键约束变成可以失败的程序：配置错误不能启动，未授权动作不能到达驱动，人工接管后旧策略不能复活，日志必须区分原始意图和实际执行。若直接接FR3/Quest/真实模型，这些错误会与驱动、网络、坐标和依赖问题混在一起，难以归因。

fake提供可复现输入和可控时间，可以精确构造过期、乱序、接管与故障，无需等待机器人或GPU。MCAP和只读回放同时建立证据链，后续设备适配器可以复用同一组行为检查。它验证基础设施，不验证学习能力、真实运动质量或真机安全。

## 最短操作路径（仓库根目录，PowerShell）

前提：已安装uv，可使用Python3.11。当前机器3.11.12位于uv管理目录，系统`python`是不可运行的WindowsApps占位，故命令显式使用虚拟环境。

```powershell
uv --cache-dir .uv-cache sync --locked --extra dev --python 3.11
.venv\Scripts\python.exe -m robot_infra validate configs/fake-control.json --dry-run
.venv\Scripts\python.exe -m robot_infra run configs/fake-control.json --output artifacts/my-review.mcap --steps 500
.venv\Scripts\python.exe -m robot_infra replay artifacts/my-review.mcap
.venv\Scripts\python.exe -m robot_infra replay artifacts/my-review.mcap --jsonl
.venv\Scripts\python.exe -m pytest -q
```

输出文件必须不存在；重复演示更换文件名，避免覆盖证据。pytest的临时目录为仓库内`artifacts/pytest`，由pytest管理，勿存用户文件。500步为10秒fake时间，实际运行无需等待10秒；不是实测采集帧率或快速入门时间。

默认`--steps 12`演示应产生173事件、14次fake写入；500步应产生5053事件、502次fake写入。`run`会自动只读回放并比较live/recorded时间线。每次session ID和全局hash可以不同；同一个文件的run/replay报告应一致。

## 重点审查行为

| 审查点 | 操作/源码与测试 | 应看到的结果 |
|---|---|---|
| 配置是否真的约束执行 | [合法图](../configs/fake-control.json)、[绕过guard的坏图](../configs/invalid/bypass.json)；运行validate坏图 | 错误指明必须mapper→guard→robot；退出码2，无设备构造，无录制文件 |
| 谁能写入 | [Session._dispatch](../src/robot_infra/runtime.py)、[FakeRobot](../src/robot_infra/fake.py)、[边界测试](../tests/test_runtime.py) | 无lease、错误源、非有限数、越限、过期、重复命令不增加driver_calls |
| 接管后旧策略怎么办 | runtime中的acquire/_invalidate/complete_policy/tick；`test_late_policy_after_takeover_cannot_revive_and_human_can_write` | pending/queue清空、epoch改变，迟到结果old_epoch；人工合法命令能继续执行 |
| 停止、故障和恢复 | stop/fault/reset、lease过期测试 | 清空待执行项、撤销授权；fault后须reset/start，新lease才可执行 |
| 日志是否能解释执行 | [MCAP与回放](../src/robot_infra/recording.py)、[集成测试](../tests/test_integration.py) | intent→mapped→guard→command→receipt→feedback可关联；camera/state→snapshot→request→chunk可追踪 |
| 回放会不会重新运动 | replay的导入/调用路径，`test_replay_does_not_construct_or_write_devices` | 不构造Session/FakeRobot，不申请lease，不调用execute |
| 错误是否被掩盖 | 集成测试中的截断、CRC、schema/hash和关联损坏 | 回放失败；`--jsonl`也不会先输出部分“成功”事件 |

查看少量关键事件而不阅读整份日志：

```powershell
.venv\Scripts\python.exe -m robot_infra replay artifacts/my-review.mcap --jsonl |
    Select-String 'human_takeover|old_epoch|joint_limit|not_due_or_expired|no_valid_lease'
.venv\Scripts\python.exe -m robot_infra validate configs/invalid/bypass.json
$LASTEXITCODE
```

本次500步演示有四个刻意拒绝：旧epoch、越限、过期、无有效lease，各1次。guard共506事件，其中502次批准对应502条命令/receipt/反馈；没有把拒绝动作算成执行成功。

## 再看结构与边界

建议按[contracts](../src/robot_infra/contracts.py)→[图校验](../src/robot_infra/graph.py)→[runtime](../src/robot_infra/runtime.py)→[recording](../src/robot_infra/recording.py)→[app](../src/robot_infra/app.py)的顺序阅读。优先确认数据语义和错误行为，再看类名或代码风格。

需要你判断的设计点：固定fake资产与端口语义是否足以成为第一组契约；接管/停止/故障后的恢复是否符合预期；日志是否包含你将来排查真机问题所需的事实；CLI是否能清楚区分执行与只读回放。实际硬件单位、坐标和停止方式留到对应适配器明确确认。

M1没有通用插件发现、任意图执行、真实训练数据导出、真实策略/异步网络或物理安全机制。具体选择与限制见[ADR-0005](adr/0005-m1-fake-contract-and-evidence.md)，本机证据见[验证报告](validation/2026-10-15-m1-windows.md)。Linux和A1–A6仍未验证。
