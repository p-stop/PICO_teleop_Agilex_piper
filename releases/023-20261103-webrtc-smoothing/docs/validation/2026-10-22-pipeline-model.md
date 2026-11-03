# 建模报告与学习阅读器验证

日期：2026-10-22。范围：Windows 本地报告构建、数学例子与浏览器检查。未连接机器人，未修改 `src/robot_infra`、配置、数据契约或原始实验数据。

## 交付与依据

- [完整数学模型](../research/2026-10-22-pipeline-mathematical-model.md)：实现、分析近似、建议分别标注，包含未知物理参数与代码索引。
- [八课教程](../pipeline-learning.md)与[离线阅读器](../pipeline-model.html)：例子、展开答案、IK 更新率和推理四预算交互。
- 本次读源码所得 `runtime_identity().framework_tree_sha256` 为 `380ee1788a47160a48382610fc8826ebc6996ef4b89ec25d64eed7ef80014248`，与014/015一致。它仅覆盖框架源码，不是全仓库哈希。
- 文献使用 SciPy 官方文档、Michigan 数字控制教材、Flow Matching、DiT、ACT、RTC、UMI 原论文；具体论断附近附原始链接。报告不宣称已完成驱动物理辨识或真实模型闭环。

## 已完成检查

| 项目 | 结果 |
|---|---|
| 数值例子 | 单关节映射/平滑/反馈、IK 时间常数、年龄误差、RGB/depth 吞吐、队列容量、chunk 时长/预算通过 |
| 边界条件 | 首动作恰好到期也拒绝；其它预算允许等号；有旧队列仍可能拒绝新段 |
| 公式 | 182 处原生 MathML；未见残留 LaTeX 指令；抽查公式截图 |
| 课程交互 | 八课选择、上一课/下一课、答案展开和 Markdown 强调正常 |
| 计算器 | IK 更新率/比例更新曲线和时间常数；推理预算成功/失败状态正常 |
| 响应布局 | 1440 / 768 / 390 / 320 px，检查全部八课，无页面水平溢出 |
| 资源与脚本 | 本地文件链接/目录锚点存在，无重复 ID，无浏览器异常、失败请求 |
| 阅读退化 | 禁用 JavaScript 仍显示全部八课；打印显示全部课程，打印事件展开答案 |
| 工作树检查 | `git diff --check` 通过；仅现有 README/CHANGELOG 的换行提示 |

自动结果和截图位于本地 [artifacts/validation/016-pipeline-model](../../artifacts/validation/016-pipeline-model/qa.json)。这些生成物在 artifacts 目录，报告 HTML/CSS/JS 与 Markdown 为可交付源码。测试脚本是报告核验工具，没有新增机器人运行时依赖。

## 如何重做

构建器需要独立环境中的 `markdown` 与 `latex2mathml`；本轮使用 uv 缓存，以离线模式执行：

```powershell
uv run --offline --no-project --with markdown --with latex2mathml python tools/build_pipeline_model.py
```

浏览器检查需要 Node、Playwright 和 Chrome。本轮使用 Codex 已有工具，不改项目 Python 依赖：

```powershell
$env:NODE_PATH='C:/Users/47328/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
$env:REPORT_CHROME='C:/Program Files/Google/Chrome/Application/chrome.exe'
& 'C:/Users/47328/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' tools/check_pipeline_model.cjs
```

这些是本机工具路径，其他电脑按实际安装设置。HTML 本身只需支持原生 MathML 的现代浏览器，打开后无需联网。

## 验证边界

本轮没有重跑未改动的控制测试，也没有新增 Linux、真机、真实相机或 GPU 模型证据。报告中的一阶响应、单关节映射与时间预算是教学近似；硬件响应、时钟误差、源观测年龄仍需专门测量。下一步 Timing QC、传输调度、真实观测 shadow 等均是建议，未在此次实现。
