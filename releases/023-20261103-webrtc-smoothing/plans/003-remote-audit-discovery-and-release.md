# M2准备：远端代码审计、设备发现与发布基线

日期：2026-10-16。状态：complete（本轮审计、发现切片、文档和本地发布基线；M2真实控制未实施）。

## 范围和验收

用户授权浏览ranger-piper的机器人相关文件/代码，审查SDK、环境和启动项，完善通用设备发现、后续验证与发布/部署计划，并自主推进。重点功能完整性与复用，不扩张与当前切片无关的安全工程；已有所有权/guard边界保留，不执行真实控制、CAN激活、相机开流或供应商demo。

1. 有范围/截断信息的远端工程索引，保留绝对目录、用途、版本和可复查代码位置；不将前人代码/数据/凭证打包发布。
2. 已安装SDK/虚拟环境/ROS/启动项的只读证据；初始化与停止代码审查、左右臂/相机绑定的证据与未决项分开。
3. 实现一个可用的最小设备发现切片：被动OS枚举→版本化候选设备/证据→配置驱动角色绑定/冲突报告。不猜左右/标定，不把传输适配器当成已识别机器人。不做任意串口主动探测。
4. fake/配置测试、Windows全套与目标Ubuntu无硬件验证。实际验证范围单独报告。
5. 发布排除规则、部署/回退/版本说明与检查清单完整；准备可审查的发布文件集/基线。远程Git地址尚未提供则不发布；不得将参考仓库、交付PDF、数据/权重/私钥混入。

## 顺序

- A：SSH分阶段只读扫描（home机器人工程及明确扩展路径，剪枝虚拟环境/数据/缓存/凭证），再针对候选源码阅读；输出到本地ignored artifacts。
- B：根据真实发现明确自动发现契约、插件边界、角色profile及下一切片；写ADR，保留M1兼容。
- C：实现被动发现及绑定校验，使用fixture覆盖无设备/权限/重复serial/歧义/换口/多端点资源；Linux执行仅无硬件代码。
- D：补全README、审计索引、部署/发布文档、ignore/打包规则，执行相关测试与文件集检查；更新状态、计划checkpoint。

## 起点

M1固定fake，Windows86项通过。ranger-piper已可SSH，只读inventory可见Ubuntu24.04.4/Python3.12.3，系统metadata piper_sdk0.6.1，三CAN均DOWN，双D435+一D455。主项目无commit/remote。用户已被询问Git目标地址；发布不阻塞本地工作。

## checkpoint

已完成A–C及主要D文档：远端代码/安装副本/ROS/venv/启动项审计；确认用户提供的左右臂/三相机角色并保存gitignored profile；独立版本的stdlib被动发现、Collector与绑定CLI实现，Windows105项/目标Ubuntu发现19项通过。新schema不扩张M1控制契约。

用户确认本轮先准备本地基线、尚无Git远程；不创建/推送仓库。临时传输的是无硬件发现测试，目录已移除；未改供应商工程/系统环境/设备状态。

最终验证：Windows105项通过，目标Ubuntu发现19项通过（首次包装器目录问题修正后重跑，原失败证据保留）；真实被动发现74候选/五角色resolved。sdist/wheel构建和排除检查通过，wheel17项；独立wheel环境validate/run/replay/discover通过。37份Markdown/141内部链接零问题。证据见docs/validation/2026-10-16-discovery-and-audit.md和artifacts/2026-10-16-release-check.json。

交接：本地初始Git基线分支codex/m2-discovery-baseline；不将relevant-repo、artifacts、profiles/local或环境/数据纳入。下一任务从计划002的M2.1–M2.2开始，先通用N端点+组授权fake，然后三相机/VR/反馈采集；真实backend另阶段。PICO准确型号/浏览器、模型/TCP/安装标定、任务与设备动态行为仍需验证。
