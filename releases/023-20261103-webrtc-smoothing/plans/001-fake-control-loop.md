# M1：硬件无关的控制、采集、回放与策略接管切片

更新：2026-10-15。状态：complete（Windows fake范围）。用户已明确请求实施M1；授权范围为无硬件首切片，不包含真机命令。

## 目标

在Windows开发机上，用户可以验证一份小图配置，运行fake遥操/策略到fake执行器的控制链，查看反馈及拒绝事件，生成MCAP记录，并在无设备写入的回放模式中核对事件。人工接管、旧策略结果与停止是这条链的验收部分，不是留给硬件阶段的附加功能。

fake为软件生成的输入、状态和观测，不连接真实设备。stub policy为可预测输出并可注入延迟的假策略，不下载模型。epoch为授权代次，接管/reset/故障后旧代次动作失效；lease是某个源对执行端的控制许可。

## 实施前基线与本次范围

- 仓库只有设计文档，无源码、打包配置、CLI、测试或CI；架构v0.5。Git无commit，实际进入时再次检查。
- 先读AGENTS、agent-onboarding、project-status、architecture§3–5/§12，ADR-0001/0002。
- 本次只用fake机器人、fake相机、fake遥操、stub策略；核心不导入ROS/厂商SDK，不做网络部署、真机probe、MuJoCo、真实模型、IK、RTC、MPC、GUI或LeRobot导出。
- §15的任务/QC/报告仅保留必要标识与证据引用，不同时实现完整评测/数据管理平台。
- 开发验证目标为当前Windows；Linux同commit验证作为后续环境证据。未执行的Ubuntu版本一律not_run。

## 实施时先确定的少量决策

实现agent选择并记录包名、核心Python基线、最小schema/序列化方式、MCAP依赖及测试工具。验证其所选环境能安装/运行，不修改Ubuntu系统Python。架构Python协议例子是草案，不要求照搬类名/继承树。

只实现拟议v0.3契约所需最小子集，schema显式版本化；记录相对历史v0.2示例的差异，未知版本/不支持功能明确拒绝。不创建所有未来模块空目录，不引入多套中间件。可逆实现选择直接推进，影响长期契约/兼容/安全边界时写简短ADR。

计划中的命令名称不是已存在命令；实现后必须将真实安装、运行、验证和回放命令写入本计划/README，并证明能复现。

## 最小场景与契约

- 执行端为明确命名的2关节fake资产（示例joint_a/joint_b），关节位置用rad、顺序固定；限位与周期在fake profile声明。不将它标为FR3/Piper，也不推断真实frame。
- 一路合成RGB观测带相机角色、序号、原始时间戳和clock domain；一份明确标注fake的资产/标定元数据。
- 遥操源与策略源共用一个所有权入口，最终guard独占fake驱动写入。图可以有多个候选源，但不能有多个绕过仲裁的命令写入者。
- 版本化消息包含session/source/seq、动作或观测schema、单位/顺序、时间域/有效期；动作含lease/epoch。request/chunk与真正下发receipt、反馈可关联。
- 先用进程内组件与可注入时钟；不把一个统一hz或收到消息的时间当所有阶段原始时间。
- MCAP保存原始意图、stub输出、映射/调度结果、guard事件、实际下发/receipt、反馈及相机观测，并保存配置/schema/资产版本。若尚无执行确认，不能标成executed。

## 里程碑与依赖

| 里程碑 | 可运行结果 | 完成条件 |
|---|---|---|
| M1.1 | 最小包、版本化契约、图validator、合法/非法配置 | 安装与测试命令成立；合法fake图通过，坏图在启动前明确失败 |
| M1.2 | fake遥操→映射→所有权/guard→fake执行→反馈，最小session | 同一入口可运行/停止；无lease、越界、非有限数和过期动作拒绝，驱动没有收到它们 |
| M1.3 | 该链路生成MCAP，并只读回放 | 独立读取器打开日志；验证完整事件关联和配置/时间元数据；回放不申请lease、不发命令 |
| M1.4 | stub policy走相同链路，支持受控延迟及人工接管 | 策略/人两种源切换；旧epoch/迟到结果拒绝；reset/故障使旧结果无效 |
| M1.5 | 可复现演示、故障验证和交接 | unit、integration、配置验证通过，README/计划/status符合真实状态 |

每阶段完成可运行结果后再扩展，不另开任务让共享契约并行漂移。M1.3可使用简单同步循环；M1.4用受控待处理结果验证时间/epoch边界，不要求先部署异步GPU服务。

## 必要验证场景

| 类型 | 输入/条件 | 必须观察到 |
|---|---|---|
| 配置 | 未知schema、缺端口、类型/单位/joint order不匹配、没有guard、直接多写入者 | 预检失败并给具体节点/边及原因；任何驱动未启动 |
| 正常链路 | 合法源获lease并发有限、限位内目标 | guard批准→唯一驱动调用→receipt/反馈，序号与来源可对应 |
| 授权边界 | 无lease、已撤销lease、旧epoch、重复seq | 拒绝且驱动调用计数不增加；拒绝事件可读 |
| 数值/时间边界 | NaN/Inf、越限、显式过期、所需状态过期 | 不执行；原因和原始输入保留，停止规则与状态一致 |
| 接管 | 发出策略请求，人工接管后才返回策略结果 | 旧结果拒绝；合法人工动作可执行；没有短暂策略复活 |
| reset/故障/stop | 队列中已有动作或请求未返回 | 授权代次失效、队列清理，后续迟到动作不执行；不自动恢复 |
| 记录/回放 | 正常与拒绝事件混合的固定输入 | 独立MCAP读取校验；保留全部来源、时间域、seq和receipt关联；只读回放产生同一规范化事件序列 |
| 文件损坏/版本变化 | 截断记录或不支持schema | 清楚报告失败/不完整，不静默视为完整成功episode |

过期/延迟使用可注入时钟或可控完成队列，避免依赖真实sleep而形成偶发测试。确定性比较针对规范化事件内容与顺序，不要求包含运行标识的MCAP字节完全相同。fake guard规则通过不代表真实设备停止或碰撞安全已通过。

测试包含最小unit、消费方/端到端integration及独立配置验证；记录读取需用MCAP库读取输出，避免只用写入函数自己的内存对象证明正确。关键行为需有断言，例如接管后故意放行旧结果应导致对应测试失败。

## 交付与报告

- 可安装包、最小合法图及坏配置fixtures、运行/验证/回放命令、短演示说明；明确fake模式。
- 必要测试与实际命令、退出码/结果；按[验证报告模板](templates/validation-report-template.md)记录环境。
- 相关契约决定与schema差异；project-status更新为实际完成的fake能力，不标记A1–A6通过。
- 证据中不保存私钥或真实连接凭证；大文件只引用/hash。
- Git基线状态如实记录；若未来要并行或远程接续，先建立双方可识别的源码基线。

## 当前checkpoint

M1.1–M1.5全部完成：robot-infra0.1.0，契约0.3.0-m1，JSON图/事件schema、7角色fake固定拓扑、session/lease/epoch/final guard、camera/stub、MCAP/replay、CLI与测试。实际用uv已安装Python3.11.12建立本仓库venv，没有修改系统Python。

真实复现命令、结果和未验证项见[审查指南](../docs/m1-review.md)与[验证报告](../docs/validation/2026-10-15-m1-windows.md)。选型和历史草案差异见ADR-0005。

- 验证：80项unit/integration/config测试通过，Junit为artifacts/pytest-results.xml。
- CLI：`python -m robot_infra validate <config> --dry-run`、`run <config> --output <new-file> --steps 500`、`replay <file> [--jsonl]`，均须使用venv Python。
- 演示：artifacts/m1-demo.mcap，5053事件、502次fake写入；四类预期拒绝各1次，回放与live一致。
- 独立wheel构建/安装及离开源码目录的validate/run/replay通过；移除限位检查的临时副本被回归测试识别。
- 未做：Linux、MuJoCo、真实SDK/传感器/模型/网络和所有A1–A6；未创建Git提交或连接远端。
- 下一步：先由用户按指南审查语义与故障行为；后续任务建立可追踪Git基线，运行目标Ubuntu无硬件契约测试，再进入固定MuJoCo/输入只读验证。不是自动授权真机工作。
