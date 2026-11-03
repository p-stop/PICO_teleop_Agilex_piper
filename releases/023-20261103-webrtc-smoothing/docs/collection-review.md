# 多端点fake采集：运行、契约与审查

更新：2026-10-16。这是0.3.0之后尚未发布的源码增量；对应[真实目标graph](a4s-graph.md)、[计划006](../plans/006-a4s-graph-and-shared-execution.md)。M1命令/格式不变。

## 运行与结果

在项目根目录、安装现有开发依赖后运行：

```powershell
.venv\Scripts\python.exe -m robot_infra collect-validate configs/fake-a4s-collection.json --dry-run
.venv\Scripts\python.exe -m robot_infra collect-demo configs/fake-a4s-collection.json --output artifacts/my-collection.mcap --steps 20
.venv\Scripts\python.exe -m robot_infra collect-read artifacts/my-collection.mcap
```

Linux对应python3/项目venv入口。输出必须是新文件，第二次运行更换文件名。collect-demo构造的全部backend/camera/source均为fake，不能通过把mode改real获得物理控制。collect-read只验证文件，不创建设备。原M1的replay与新collect-read使用不同MCAP profile，不能互相混读。

20步结果：394事件；每个backend20次fake执行，共40个command/receipt/feedback；三相机每路21张2×2合成RGB（含start首次观测），共63条camera；人工标签与stub-policy标签各10步，走同一submit路径。epoch、group、单位与stream角色可由独立MCAP读取器检查。hash包含session_id，所以不同运行的最终hash不同，不以它们相等作为确定性断言。

**此结果不是20步真实遥操、不是策略部署，也没有执行IK。** 源直接生成合成具名关节目标；motion_result明确标synthetic-native-joint-identity。真实PICO/三相机/CAN反馈目前仍是计划004的独立诊断入口，尚未接入这个fake运行器。

## 配置与抽象

`collection-plan/1`当前仅支持fake/fake_monotonic、一个执行组、1–32个具名端点/批次/来源/相机。它是本切片执行配置，不是完整端口图schema，不加载任意plugin。端点数/名字不在核心写死；模板以双6关节臂+双夹爪和三相机体现A4-S形态。

| 配置项 | 用途 |
|---|---|
| endpoints | id、backend、命令kind、具名坐标顺序、unit、frame、limits、initial和每次max_step |
| backends | 一次底层发送的资源分组；同backend的坐标名不得重复 |
| group | 当前要求完整包含全部端点；组授权/epoch一次撤销，不声称双设备硬件原子执行 |
| sources | 任意具名来源与优先级；只有更高优先级且明确takeover才能抢占 |
| cameras | 具名观测角色；不由字符串猜安装位置或实际设备 |
| timing | fake period、反馈/意图年龄和lease时限；全部是合成测试数值，不可直接迁移实机 |

真实硬件serial、IP、ROS topic、TCP和外参不进入这份合成配置。模板的±1rad、0–0.08m、max_step及合成frame只用于测试，不是Piper能力声明。夹爪与关节不拼成一个全rad向量。

## 源码阅读顺序

1. [collection.py](../src/robot_infra/collection.py)：配置检查和EndpointTarget/CommandSet。先检查配置，再允许构造fake backend；保留M1独立契约。
2. [collection_runtime.py](../src/robot_infra/collection_runtime.py)：CollectionSession编排、组lease/epoch、observe、最终submit。FakeBatchBackend只做完整批次立即赋值，没有ROS/SDK。它是新执行子集，不替换M1 runtime.py。
3. [collection_demo.py](../src/robot_infra/collection_demo.py)：应用只生成来源和调用session；中途换源，执行入口相同。实际模型adapter、观测预处理、chunk队列和IK另接。
4. [collection_episode.py](../src/robot_infra/collection_episode.py)：按事件流写MCAP，有限chunk缓冲；不保留整个episode图像/事件列表。结束hash/计数及独立读取器校验CRC、schema、事件顺序、配置hash、批次guard/receipt/feedback和必需流。
5. [test_collection.py](../tests/test_collection.py)：检查错误语义、整组先验证、来源替换、超时/迟到结果、部分批次失败和错误complete标记。

## 需要重点审查的语义

- CommandSet必须完整覆盖本执行组，端点名字/关节顺序/单位/frame均精确匹配。任何目标不合法时，首次发送前全部拒绝；不默认填零或裁剪未知语义。
- 每份backend实际发送前再次检查lease/epoch、意图/反馈年龄和限步，防止前一份发送耗时使后一份越过有效期。全部预检通过不意味着后续发送一定都成功。
- 第二批次失败时，第一批次可能已执行，receipt分别为executed_fake和failed_execution_unknown；组fault/撤权并停止各fake backend，不能写成回滚成功。
- 旧IK/策略工作必须保留创建时的source/epoch/snapshot；接管后旧结果拒绝。真实异步求解和request/chunk调度尚未实现，本轮用已创建的CommandSet模拟迟到结果。
- fault之后即使reset/start，当前episode的失败历史仍锁存，最终标aborted；读取器也拒绝“出现fault/失败receipt却标complete”的文件。
- Session只保留最多32个snapshot和当前状态，不保存全量events。MCAP仍有索引/元数据开销；不据此宣称任意时长或真实视频带宽已验证。
- stop是fake调用计数，不代表真实保持/制动/失能；watchdog_tick是手动fake轮询，不是设备本地实时看门狗。实际ROS命令代理/真实时钟、部分端点控制、重叠多组、实际相机持续录制都还未实现。

## 验证证据

[本轮报告](validation/2026-10-16-a4s-shared-execution.md)分别记录Windows165项全套、Ubuntu隔离165项全套与20步fake episode。Linux使用临时pure-Python mcap测试依赖副本和机器已有pytest/jsonschema，不是完整锁环境安装；未运行ROS或任何物理命令。
