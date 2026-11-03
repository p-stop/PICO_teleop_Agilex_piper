# 训练数据格式报告与LeRobot v3转换设计

2026-10-19。面向supervisor、训练与部署开发者。原始字段详见[采集数据格式报告](collection-data-format-report.md)，实际三集质量见[审计](research/2026-10-19-new-test-audit.md)。本报告区分已实现的训练视图、候选训练schema和待实现的LeRobot writer。

## 1. 训练数据选择

建议保留“原始证据层 → 因果对齐的训练视图 → 模型/LeRobot出口”三层。换模型不改采集驱动，换存储不改action语义，转换不能破坏原始时间戳。

| 训练特征 | 候选dtype / 单样本shape | 含义与来源 |
|---|---|---|
| observation.images.scene_fixed | uint8[H,W,3] | 固定RGB；原始MCAP或MP4解码 |
| observation.images.left_wrist | uint8[H,W,3] | 左腕RGB |
| observation.images.right_wrist | uint8[H,W,3] | 右腕RGB |
| observation.depth.scene_fixed | uint16[H,W,1]原生，或显式换算float32米 | 固定depth；需要实测depth scale |
| observation.depth.left_wrist | 同上 | 左腕depth |
| observation.depth.right_wrist | 同上 | 右腕depth |
| observation.state | float32[14] | 两臂各6关节rad、各一夹爪开口m，实测状态 |
| action | float32[14] | 两臂各6关节绝对目标rad、各一夹爪目标开口m；不是实测下一状态 |
| task | str或task_index索引 | 真实任务指令，不能默认new_test是有意义的机器人任务 |
| timestamp / frame_index / episode_index | float秒 / int / int | 导出网格时间与episode归属 |
| action_valid / sample_valid | bool[14] / bool | 审计视图质量标记；正式训练若模型不支持mask，应筛选而非把null改零 |

H/W来自选定record分支；当前RGB为480×640×3。LeRobot通常向模型返回[C,H,W]，带时间窗口时[T,C,H,W]；不要将文件的HWC与模型CHW混淆。当前三集没有depth，**现在只能验证RGB训练出口，不能宣称已得到RGB-D训练集**。

packed state/action顺序固定为：

```text
0..5   left.joint1..joint6     rad
6      left.gripper.width     m
7..12  right.joint1..joint6    rad
13     right.gripper.width    m
```

这是当前A4-S模板的显式选择，不是核心写死的14维。`configs/training-a4s-rgb.example.json`通过endpoints的id/side/names/unit定义顺序，支持不同维数的具名端点；模型关节顺序与源manifest不同会拒绝。不同单位混在同一向量时，names/units/normalization须一并保存；不要对所有维度采用同一个尺度。

其他数据如原生末端、转换Quaternion、按钮、IK诊断、guard/receipt、相机metadata保留在原始层或provenance中，不默认全部喂给策略。它们可用于QC、接触分析、时延诊断以及以后生成末端action。

## 2. 夹爪：state与action必须分开

你的判断有道理：夹住物体时，期望开口可能为0mm，实际开口因物体而保持30mm。若把30mm反馈当作“关闭action”，策略可能在接触时只发布30mm目标，缺少继续闭合的意图。开口目标也不等同夹持力，本系统当前执行的是厂商位置/effort配置，不能声称推理一定夹得住。

三种候选标签的区别：

| 候选 | 适合用途 | 不宜直接作为统一action的原因 |
|---|---|---|
| 实际gripper开度 | observation、接触/跟踪误差分析 | 受物体阻挡和控制滞后影响，不是闭合目标 |
| 原始扳机value | 辅助意图/按钮分析 | 还未经过反向映射、开口范围、模式/暂停、独立夹爪逻辑和最终guard，未必真的执行 |
| 确认已发布的gripper_m目标 | **推荐训练action标签** | 最接近执行接口；仍只是ROS发布成功，不是硬件执行ACK |

当前台架“按下打开、松开关闭”，约70mm全开；转换必须读每集配置，不应写死`1-trigger`或假定所有机器人0/1方向相同。如果未来模型采用close_probability等归一化表示，应在模型adapter显式生成，保留米制标准动作与映射版本。

原始`command`在publish之前记录，因此转换器还要匹配同side/seq的`receipt.status=published_not_acknowledged`，避免将发布异常的候选当成功发布。`measured_hold`事件是现有代码在send返回后发出，单独标为post_send_hold_event，不伪造receipt。

### 稀疏夹爪命令和初始目标

独立扳机只在需要更新时发夹爪目标；没有新命令通常表示上一个目标继续有效，而不是“复制当前开口”。因此action用零阶保持上一条有效目标，期间实测state持续更新。

最容易遗漏的是episode开始前的目标：回Home不动夹爪，之前的关闭目标可能仍保持，而夹爪实际夹着物体。**不能用episode第一帧实测开口猜初始目标。** 当前两条工程样本可从对应session journal中提取开始前最后确认发布的目标，并保存journal hash/行号；若没有证据，标unknown/mask，不补零、不补实测。

本轮为后续采集增加`context.initial_targets`，仅在后端publish调用返回后更新内存快照；仍标记“已发布、非硬件ACK”。这样新episode可带入前序夹爪目标，不必依赖庞大的整场日志。新进程从未发布过的目标仍未知，框架不会编造。

## 3. 对齐、action时序及有效性

当前原始alignment是按接收时间最近邻，可能选到未来帧，适合诊断，**不能不加区分直接当在线可用observation**。

已实现的训练视图采用显式配置：

1. 默认30Hz网格，原始host monotonic作时间轴；网格和原始stamp均保留。
2. state/RGB/depth仅选择`t_obs`之前最近样本，超过max_state_age_s/max_image_age_s无效，不拿未来样本冒充当前输入。
3. 默认`action_offset_steps=1`：标签为`t_obs+1/30s`前最新确认发布的绝对目标；这是明确的标签前移选择，不是硬件延迟校准。0步/其他步需作为版本化实验配置。
4. 若区间没有新目标，保留已知上一个目标；若初始目标未知，action为null且mask=false。episode尾部标签超过结束窗口也标无效。
5. RGB/depth保持原帧引用、源stamp/接收stamp/sequence；MP4另带frame_index/PTS。训练网格允许复用合法旧帧，但写清最大年龄；不得靠重复陈旧帧遮掩长掉线。
6. 不跨episode/控制中断拼接；最终writer应输出连续有效段并保留来源offset，不把中间无效区间剪掉后假装时间连续。

选择1步而非精确动作因果推断，是当前工程基线。真实传感/推理/执行延迟应通过测量后调整；不能根据两台不同设备墙钟直接算出精确的闭环延迟。

## 4. 深度接入与单位

三路深度在训练schema中是候选必选模态，但当前源数据全缺。RGB-only profile立即可用；RGB-D profile必须在后续实采启用capture.depth和record.depth，并核实每台相机单位/scale、深度无效值、畸变/内参和是否对齐RGB。

原始深度保留uint16等原生数值，不进RGB 8-bit H.264。不能把16位深度直接塞进普通RGB MP4；也不能把metadata里的任意单位自动猜成毫米。视图depth映射要求显式正数`depth_m_per_unit`，没有实测就拒绝，而不是默认为0.001。

原生640×480×uint16三路30fps，仅depth像素约55.3MB/s，约3.3GB/分钟；USB总线/写盘/CPU还要同时承担RGB和VR。启用前应单独做RGB-D吞吐测试，不直接沿用“RGB MP4很小”的容量预期。

当前LeRobot main提供专门的深度编码配置，采用高位深视频并保留量化参数/深度单位；它不是像素原值完全等价的普通RGB编码。若选择该路线，原始MCAP仍是无损证据，转换报告必须记录量化范围和误差；以实际锁定版本能力为准。[官方深度编码说明](https://github.com/huggingface/lerobot/blob/main/docs/source/video_encoding_parameters.mdx)、[DepthEncoderConfig](https://github.com/huggingface/lerobot/blob/main/src/lerobot/configs/video.py)。

## 5. LeRobot v3出口设计

v3不是“改后缀为mp4”。它将低维数据放Parquet、视觉放视频分片，用metadata描述特征、episode边界、文件偏移和统计；多个episode可以共享Parquet/MP4文件。应调用锁定版本官方writer，而不是手写一份看似v3的目录。[官方v3格式](https://huggingface.co/docs/lerobot/lerobot-dataset-v3)。

建议模块分层：

```text
真实episode reader ──→ 训练语义/质量准入 ──→ 因果采样视图
     │                       │                    │
原始MCAP/视频/索引       夹爪/坐标/单位映射       frame refs + state/action
                                                  │
                            ┌─────────────────────┴─────────────────┐
                            ▼                                       ▼
                    LeRobot v3 writer adapter               ZeroWAM-specific adapter
                    Parquet/视频/统计/episode索引           模型特定EEF/归一化/latent
```

转换程序的步骤与验收：

| 阶段 | 工作 | 验收 |
|---|---|---|
| preflight | 版本、hash/deep、saved/QC、任务标签、所需模态、关节顺序、单位 | 不合格集有明确排除原因；缺depth不填假数据 |
| semantic view | 命令与receipt关联、初始目标、状态/目标分离、因果图像引用 | 关闭目标不被接触开口替代；未知action不静默填值 |
| sampling | 固定网格、样本/episode连续段和时间映射 | 每训练行能追溯到原事件和图像帧 |
| media adapter | 按引用解码/重采样/编码，depth专用处理 | MP4原始丢帧导致时间轴不同，不能直接全视频复制后假设逐行对应 |
| official writer | create→add_frame→save_episode→finalize | 真实LeRobot reader读回、episode offset和归一化统计正确 |
| audit | 导出manifest、版本、源hash、排除列表、任务标注状态 | 不修改源数据，失败输出不冒充完整dataset |

训练视图的extra掩码/来源可以放adapter支持的列或独立provenance sidecar；不能强迫所有模型认识额外字段。对joint-action模型，保留14维物理目标；对EEF模型，需另做经审查的FK/TCP或原生末端语义映射，不能仅改feature名字。

当前ZeroWAM官方requirements固定`lerobot==0.3.3`，与v3 writer环境分开；不能声称v3数据直接被该训练loader接受。正确方式是原始层/标准视图稳定，出口adapter分别对接v3和ZeroWAM的数据/latent约定。[ZeroWAM依赖](https://github.com/robbyant-research/Zero-WAM/blob/08e2c4ae41e2b63573a299825cebe6753481407c/requirements.txt)。

## 6. 本轮实际实现与使用

已实现的是不依赖ROS/模型框架的 `training-view/1`，输出 `rows.jsonl` 与 `view.json`：包含state/action、掩码、视觉帧引用、逐维单位/名字、源manifest/MCAP/journal hash和证据位置。**它不是LeRobot数据集，不包含真正Parquet writer或训练可直接加载的视频分片。**

```bash
~/robot-infra/bin/robot-infra training-view \
  ~/robot-infra/dataset/new_test/episodes/episode_000000 \
  --config ~/robot-infra/current/configs/training-a4s-rgb.example.json \
  --journal ~/robot-infra/runs/20261019T125215Z_acf97d46/episode/events.jsonl \
  --output ~/robot-infra/runs/training-view-episode0
```

新分段journal需要按summary顺序重复`--journal`；数据集初始目标已完整记录后可省去它。输出应使用新目录；源目录保持只读。已存在的审计/视图示例路径见计划013的checkpoint，部署状态也以该checkpoint为准。

本次已在机器人隔离环境生成两集真实视图：episode0共1858行、740行完整有效，episode1共1724行、1722行有效。episode0左夹爪在约37.23秒、右夹爪约7.67秒前没有已确认目标证据，因此早段被标unknown，而不是补成实测开口；episode1可由前序session命令补齐已知初始目标。首/尾行和少量图像年龄超限也会标无效。这些行数是严格的工程视图结果，不代表任务训练样本数或成功率。

第三集默认因review/QC失败拒绝。前两集只能作为格式/手感工程样本，用户已确认任务成功/失败待标注；转换视图生成成功不代表该任务有足够训练数据，不能据此报告策略成功率。

下一步先审阅state与action曲线及夹爪目标，在隔离数据环境安装锁定的LeRobot v3 writer，做两集最小导出、官方reader读回和视频逐行对照；RGB-D须另采并确认scale。避免将PyTorch/训练依赖装进机器人驱动环境。
