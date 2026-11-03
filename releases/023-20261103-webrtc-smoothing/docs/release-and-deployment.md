# 本地基线、仓库发布与机器人端部署

更新：2026-10-18。用户确认尚无Git远程，本轮先准备本地基线，不创建仓库或对外推送。M1/fake collection保留，独立live/real-episode已现场完成首个三RGB保存episode与deep QC。机器人稳定本地入口、源码快照、profile和独立依赖布局见[采集与部署手册](episode-collection.md)，验收见[当日报告](validation/2026-10-18-a4s-link-and-episodes.md)。

## 何时推送

完成本轮源码/文档、Windows测试、目标Ubuntu的发现测试、发布文件集检查后，即适合建立首个可复查的Git提交；不必等待真机遥操全部完成。之后创建用户指定的远程仓库并推送同一基线，再在机器人端独立checkout。当前license未指定，公开发布前明确项目许可与第三方组件许可；本轮不代用户选择开源许可证或发布前人代码。

必须入库：src、tests、tools、通用configs、docs、plans、AGENTS.md、README、pyproject.toml、uv.lock、打包排除规则和变更说明。排除relevant-repo（含交付PDF/第三方嵌套仓库）、artifacts、tmp、venv/cache、datasets、视频/录制、模型权重、私钥/证书、.env与profiles/local。设备身份和网络地址只在本地profile/证据中维护；审计文档可以记录已授权的工程位置和对应证据，禁止复制登录口令。

文档中的本地relevant-repo链接是可选参考目录，干净clone可能不存在，参考索引同时提供上游身份；artifacts证据由验证者本地保留，公开仓库不包含原始日志。不要用无差别git add .创建首个提交。

## 两种部署级别

**源码检查/无硬件验证**：用明确first-party文件清单构造包，在目标机新建独立临时目录执行测试或discover，不覆盖~/piper_sdk、~/ros2_ws、~/venv_piper、驱动或配置。不启动ROS/SDK、CAN或相机；销毁临时测试目录后保留本地证据。这不等于已安装真实设备运行服务。

**正式开发checkout**：远程仓库创建后在设备端使用新路径，例如~/robot-infra（路径由用户选择），固定commit，创建项目独立venv。系统Python3.12可用于Ubuntu24.04；核心要求>=3.11，不能强行替换Ubuntu20.04系统Python。SDK/ROS现有环境单独保留，backend按进程/协议边界接入。

```bash
# 示意：替换地址、commit和目录；不是当前已执行的部署
git clone <user-repository-url> ~/robot-infra
cd ~/robot-infra
git checkout <reviewed-commit>
uv sync --locked --extra dev
uv run --no-sync python -m pytest -q
uv run --no-sync robot-infra validate configs/fake-control.json --dry-run
uv run --no-sync robot-infra discover --output artifacts/discovery.json
```

依赖锁uv.lock是环境重建基线；构建机/目标机平台、Python、最终包版本和commit均入报告。无网络时先准备对应Linux/Python轮子的wheelhouse，不将Windows二进制包复制到Linux环境。没有uv时可先用stdlib发现工具，完整运行环境再按锁文件解析安装；不要用系统pip替换现有ROS依赖。

## 配置与首轮运行

从configs/device-bindings.example.json复制本地profile，结合新发现结果填serial/通道与角色；已确认数据写profiles/local。新机器用同一模板，不改Python源码。首次只执行discover及fake；没有真实backend之前不提供伪装可用的硬件run命令。用户已确认A4-S相机/CAN角色，但这一点不自动证明流、反馈、标定或停止能力通过。

首轮物理功能顺序仍为独立输入/相机/反馈→双臂fake与FK/IK/shadow→单臂→双臂遥操数采，策略后续。M1 fake阈值不复制为设备参数。设备runtime不依赖开发SSH长期在线。

计划004已通过第三种**独立真机观测**部署：仅拷贝明确first-party模块至/home/ros/robot-infra-runs下新目录，以系统Python运行输入服务/纯CAN接收，以已安装ROS运行相机采样。无项目安装、无供应商目录改动，不能替代正式checkout。重现步骤见[运行说明](live-input.md)，证据与版本边界见[真实观测报告](validation/2026-10-16-a4s-live-observation.md)。两个临时WebXR进程均已停止，不留常驻服务。

## 更新与回退

停止项目自己的session后更新源码/独立venv；保留原commit、依赖锁、本地profile和标定版本。先重跑fake/discover并比较设备身份，再运行已实现功能。回退到上一个commit和对应venv/profile；不得用git reset/clean清理供应商工作区或数据。一个checkout只由一个开发任务维护。

## 本轮检查清单

- Windows全套与配置测试通过，Linux结果按实际范围记录；未运行的M1/Linux/物理项目不标pass。
- 发布文件清单无参考代码/数据/凭证，sdist/wheel独立检查；忽略规则不等于已经从历史中移除，因此首个提交前检查实际索引。
- 保留审计来源路径、HEAD/dirty和关键文件hash；可复用不等于可以未经许可重新发布。
- 建立本地Git基线，远程地址待用户指定。连接Codex远程项目属于后续开发环境配置，普通SSH测试不等于已完成聊天handoff。

计划007已完成独立源码真机部署和有界双臂运动验证。当前临时服务已停止；新运行入口与配置/启动/停止步骤见[真机部署手册](live-teleop.md)，记录完整性边界见[现场报告](validation/2026-10-16-a4s-live-control.md)。本轮仍未创建远程或正式安装wheel。上文“真实backend未实现”属于早期阶段背景，当前以此新增路径为准。

计划008进一步部署独立 `live-teleop/2` session，以现有系统Pinocchio/SciPy运行，未经系统pip安装。当前CLI、模板、依赖extras与离线网页资源均包含于wheel；uv离线构建/资源许可证与排除检查已通过，尚未在设备安装该wheel，现场仍用source checkout。启动/检查/停止命令以[session手册](teleop-session.md)为准，实际运行和验收边界见[现场报告](validation/2026-10-16-a4s-session.md)。保留原生ROS依赖，不以本项目uv.lock覆盖现有ROS；最终发布前另做目标环境的可重建依赖验证。用户仍要求本地基线，不创建远程或推送。
