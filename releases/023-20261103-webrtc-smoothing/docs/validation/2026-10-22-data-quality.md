# 017研究交付与检查

本轮仅研究和文档。Windows本地核读源码/配置及公开一手材料；无SSH、机器人命令、模型训练或新增真实数据评测。

交付：

- [证据综述](../research/2026-10-22-data-quality-quantification.md)：七家公司及学术项目；按论断区分真机对照、系统评测、工程实践和项目建议。
- [量化标准草案](../data-quality-standard.md)：七维质量、20项指标、分母/单位/来源/未知项/用途与阈值制定法。
- [机器可读定义](../assets/data-quality/metrics-proposal.json)：documentation_only=true，16个一手来源条目；不是采集配置或已实现schema。

复核命令：

~~~powershell
.venv/Scripts/python.exe tools/check_data_quality_report.py
git diff --check
~~~

检查器验证指标ID、来源引用、文档本地链接、JSON、8项当前示例配置值与教学算例；不会自动证明外部论文论断、公式建模假设或阈值有效性。来源内容人工核查，外部实验均未独立复现；网页未来变动不改变本次研究适用日期。

教学算例：年龄预算45ms与5ms；运动模糊1.5px与4.5px；20/20成功的95% Wilson下界约0.8389；30FPS×0.8=24FPS。它们不是新的设备测量或生产阈值。

检查已通过：20项指标、16个来源条目、17个本地文档链接、8项配置值及上述算例。git diff --check退出0，只有既有README/CHANGELOG换行符提示。

检查输出位于 artifacts/validation/017-data-quality/document-check.json。框架源码hash为380ee1788a47160a48382610fc8826ebc6996ef4b89ec25d64eed7ef80014248，与014/016相同；覆盖src/robot_infra指定源码类型，不覆盖整个仓库。本文交付时未修改运行时；不以全套旧测试数量冒充新增功能验证。

限制：Tavily自动研究结果获取遇连接重置，未用于结论；报告依据直接打开的一手论文/官方材料。当前采集QC仍不能认证曝光同步、任务成功、数据覆盖或学习价值。下一步应独立立项离线质量报告v2，不把本草案当已部署功能。
