# 采集操作手册：双 Piper + 三相机 + PICO

更新：2026-10-22。以下命令在**机器人主机的终端**执行；Windows 不参与运行。

## 1. 启动采集

当前正式任务配置为：松开扳机打开、按下闭合；三RGB MP4；仅头部固定相机录原始深度，腕部不录深度。三RGB和头部深度均640×480、30fps。任务为fill_pen_holder，保存到~/robot-infra/dataset，从0编号并跳过已占用编号。

确认机器人和三相机已接好，PICO能访问机器人，其他遥操程序已退出。当前can0/can2为DOWN时先激活（需要操作者在终端输入sudo密码）：

```bash
sudo ip link set can0 up type can bitrate 1000000
sudo ip link set can2 up type can bitrate 1000000
```

先检查（不启动设备）：

```bash
~/robot-infra/bin/robot-infra collect \
  --deployment ~/robot-infra/profiles/formal-018/deployment.json \
  --task "fill_pen_holder" \
  --dataset-root ~/robot-infra/dataset \
  --start-episode 0 --existing skip --image-storage mp4 --check-only
```

然后正式启动：

```bash
~/robot-infra/bin/robot-infra collect \
  --deployment ~/robot-infra/profiles/formal-018/deployment.json \
  --task "fill_pen_holder" \
  --dataset-root ~/robot-infra/dataset \
  --start-episode 0 \
  --existing skip \
  --image-storage mp4
```

终端保持打开。程序自检并启动网页，**启动本身不会让机械臂回位**。

| 参数 | 你需要填写什么 |
|---|---|
| `--deployment` | 本轮正式配置 `~/robot-infra/profiles/formal-018/deployment.json`；旧 `~/robot-infra/deployment.json` 保留旧实验设置 |
| `--task` | 本次任务，例如 `peach_to_box`；同一任务重复采集时保持一致 |
| `--dataset-root` | 数据保存的总目录 |
| `--start-episode` | 从哪个编号开始，首次采集通常填 `0` |
| `--existing skip` | 已占用编号自动跳过，推荐日常使用 |

编号策略另有 `error`（编号已占用就报错）、`overwrite`（保存时将旧版移入备份后覆盖）。X 丢弃后沿用当前编号；成功保存后编号加一。

**图像保存方式：** 上面的命令已选择`--image-storage mp4`，三RGB分别存MP4，头部深度以16位原始数据存streams.mcap。深度不进入RGB视频；MCAP会因原始深度而明显增大。若显式改成raw_mcap则连RGB也保存原始数据。不写时遵循所选session配置。

MP4已有实际采集证据，本轮10秒三RGB＋头部深度的独立相机记录/deep检查也通过；完整新配置的PICO双臂并发采集由操作者首条短episode验收。缺少编码依赖或参数不兼容会在启动设备前报错。编码设置见[技术说明](episode-storage-and-configuration.md#mp4-编码配置)。

**关于 `--deployment`：** 上面的专用脚本在省略它时会默认使用 `~/robot-infra/deployment.json`；这里仍显式写出，便于核对。直接运行 `robot-infra collect` 或 `python3 -m robot_infra collect` 时，它是必填参数，还需要自行准备 ROS/Python 环境。操作员统一使用上面的完整路径入口即可。

首次使用或改过配置，可以在同一命令末尾加 `--check-only`：只检查，不启动设备。只遥操、不录数据：

```bash
~/robot-infra/bin/robot-infra device-teleop \
  --deployment ~/robot-infra/profiles/formal-018/deployment.json
```

## 2. 在 PICO 中采集

查机器人 IP 可执行 `hostname -I`，选择头显可访问的局域网地址。PICO 浏览器打开：

```text
https://<机器人IP>:8445/
```

2026-10-22当前地址为 `https://192.168.87.138:8445/`，IP改变时换成新地址。首次证书提示需在头显处理；若控制连接报错，点击网页“检查控制连接”处理8446端口证书，再刷新。正常采集保持“显示相机预览”勾选；VR预览仍是RGB，不显示深度图。

进入 VR，按 HUD 的状态逐步操作，每次按 A 后先松开：

| 当前状态 | 操作 |
|---|---|
| 待机 | 右手 **A**：双臂回 Home，等待“准备就绪” |
| 准备就绪 | 右手 **A**：开始一个 episode，等待“遥操中” |
| 遥操中 | 按住同侧**侧握键**让机械臂跟随；松开保持 |
| 遥操中 | 同侧**扳机按下闭合，松开打开**；无需侧握，进入遥操即跟随有效手柄输入 |
| 遥操中 | 右手 **A**：结束，等待写盘和 QC，直到“待审阅” |
| 待审阅 | 右手 **A** 保存；左手 **X** 丢弃；等返回待机 |

保存后可继续下一轮。启动、回Home和暂停阶段不主动开合夹爪；进入遥操后，松开的扳机会让夹爪打开，不必先按一次扳机。这是formal-018配置的行为，旧deployment保持原有方向/进入行为。

退出 VR 或连接中断会暂停；正在录制的 episode 会中止并留待审阅，不会自动拼接续录。QC 未通过时可保存用于排查，但它不是合格示范。

## 3. 确认数据和结束

先看 HUD 的“已保存”数量增加，再退出 VR。上面例子的保存位置是：

```text
~/robot-infra/dataset/fill_pen_holder/episodes/episode_000000/
```

里面有 `streams.mcap`、`manifest.json`、`qc.json` 等文件；MP4模式还有 `videos/`，相机与视频文件的对应关系保存在manifest的 `media` 中。保存/丢弃作用于整个文件夹。中文或包含空格的任务名会生成目录 ID，原始任务文字保存在该目录的 `task.json`。

结束工作时，回启动终端按 **Ctrl+C**，等待进程退出。它不自动回 Home、下电或关闭夹爪。

需要离线复查某一集时执行：

```bash
~/robot-infra/bin/robot-infra episode-qc \
  ~/robot-infra/dataset/fill_pen_holder/episodes/episode_000000 --deep
```

`passed: true` 表示 QC 通过；`deep_integrity_checked: true` 表示完成了文件完整性检查。此命令不控制设备。

## 常见问题

| 现象 | 处理 |
|---|---|
| 提示缺少 `--deployment` | 用第 1 节的完整命令；不要把脚本入口换成裸 Python 命令后遗漏参数 |
| 配置文件不存在 | 核对 `--deployment` 的路径；不是所有机器都部署在同一目录 |
| CAN 为 DOWN | 当前台架先分别执行下方两条命令，再重新启动 |
| 网页打不开 | 核对 IP、`https://` 和 `8445`，确认终端服务仍在运行 |
| 相机闪红或控制断开 | 退出 VR，查看普通网页错误和终端日志；中断数据先审阅，不反复启动第二套服务 |
| 提示任务已被占用 | 先确认其他采集进程已退出；确属崩溃旧锁时，在启动命令加 `--recover-lock`，程序会核验 |

当前台架的左臂是 can0，右臂是 can2；只有接口未激活时才需要：

```bash
sudo ip link set can0 up type can bitrate 1000000
sudo ip link set can2 up type can bitrate 1000000
```

**磁盘占用：原始RGB三相机约5GB/分钟；MP4体积取决于画面和编码配置。X丢弃仍保留整个文件组，不会立即释放空间。深度流在两种模式下都保留原始数据，另占空间。**

头部640×480×uint16×30fps仅深度像素约18.4MB/s，约1.1GB/分钟，另加MCAP封装/索引与RGB视频。深度保持原生数值和光学frame，不默认与RGB对齐或已换算为米。

相机分辨率、30fps采集与低帧率预览如何分别配置，见[采集技术说明](episode-storage-and-configuration.md)。MP4布局、时间索引与后续LeRobot v3导出边界见[视频存储说明](recording-storage-options.md)。

向 supervisor 说明“采了什么、字段/形状/单位、如何读取”，见[完整数据格式报告](collection-data-format-report.md)；训练字段/夹爪action与LeRobot出口见[训练数据报告](training-data-format-report.md)。2026-10-19三集已实际记录原生末端和转换Quaternion，来源明确，深度未开启；两集capture QC/deep通过，第三集固定RGB局部帧间隔失败，详见[审计](research/2026-10-19-new-test-audit.md)。QC通过不代表任务成功或操作低延迟。

诊断仍按计划013分段保存、不删历史，初始目标/计数沿用既有实现。2026-10-22新增独立正式配置和进入遥操即跟随扳机行为，记录与部署证据见[本轮验证](validation/2026-10-22-formal-collection.md)；完整PICO/双臂/三RGB＋头部深度并发由首条正式短episode继续验收。
