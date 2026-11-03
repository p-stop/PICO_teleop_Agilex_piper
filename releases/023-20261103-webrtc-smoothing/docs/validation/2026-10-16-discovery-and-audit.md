# 设备发现与远端审计验证

日期：2026-10-16。包0.2.0；M1事件契约仍0.3.0-m1，新device-discovery/1和device-bindings/1独立版本。只增加被动发现与配置校验，没有真实控制backend。

## 验证结果

| 环境/项目 | 结果 | 证据与限制 |
|---|---|---|
| Windows/Python3.11.12全套 | 105 passed | artifacts/2026-10-16-discovery-windows.xml；原86项+19项发现测试，含M1单元/集成/配置与CLI |
| ranger-piper Ubuntu24.04.4/Python3.12.3/系统pytest7.4.4 | 19 passed | artifacts/preflight/ranger-piper-discovery-validation.json；只传输发现模块/CLI/测试/模板及本地绑定profile，临时目录自动移除，无依赖安装 |
| Linux真实被动枚举及角色匹配 | exit0，74候选，5角色resolved，无diagnostics | 同一报告中的discovery stdout；用户确认左右/安装角色后，按serial精确匹配。只代表身份绑定，不代表流/机器人已就绪 |
| sdist/wheel | 构建与文件集检查通过 | artifacts/release/；wheel17项，排除参考仓库/PDF/证据/本地profile/数据与密钥，未发布远程 |
| 独立wheel环境（Windows） | validate/run/replay/discover通过 | artifacts/wheel-smoke-0.2/smoke-result.json；包metadata0.2.0，在源目录外验证安装与资源 |

37份项目Markdown、141个内部文件链接及围栏/UTF-8检查通过；见artifacts/2026-10-16-release-check.json。原始证据和本地profile不入Git。

测试覆盖重复serial、缺失设备、未确认角色、共享资源冲突、显式共享、换USB口、部分枚举/权限失败、离线报告读写、拒绝覆盖文件、配置非法字段、CLI/stdlib入口。Windows无创建符号链接权限时fixture模拟解析；Linux测试使用真实临时symlink核对sysfs父设备关联。未打开/dev设备节点。

首次Linux测试包装器未创建basetemp父目录并把pytest配置根放在/dev，造成5项setup错误/14项通过及cache警告；修正包装器后19项全通过，原失败证据保留为ranger-piper-discovery-validation-harness-failure.json。没有改机器人系统/pytest设置。

## 实际身份

用户现场确认：can0左臂、can2右臂；D435左腕022523021289、右腕342123026960，固定D455261143061977。本地profile在profiles/local/ranger-piper.device-bindings.json（gitignored），精确匹配CAN适配器serial而不是接口枚举顺序，详细来源见[远端索引](../remote-code-index.md)。CAN依旧未激活；相机开流、固件、关节状态和标定未验证。

## 未验证与接续

- 未运行完整M1 Linux测试：现有系统环境没有完整核心依赖，本轮不改其环境。Linux19项仅覆盖发现切片。
- 未安装remote Codex、注册桌面远程项目或迁移聊天；只是当前工具经SSH执行。
- 未启动旧VR/IK/数采/推理代码。存在源码、旧数据目录或旧配置不等于可运行、可训练或可复现。
- Ubuntu20.04/22.04、Windows本机设备枚举、PICO/WebXR、三相机连续帧、SDK实际连接/停止、双臂动作均未验证。
- 下一控制切片是M2具名端点/组授权fake与独立状态/记录接口，不将当前发现器当作驱动或控制入口。
