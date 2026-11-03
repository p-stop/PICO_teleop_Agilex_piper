# 图像保存选项：原始 MCAP 与 MP4

更新：2026-10-18。两种模式已实现，可由配置或 `collect --image-storage` 选择。默认不改变，仍是 `raw_mcap`；新增 `mp4` 已通过Windows/Ubuntu无硬件测试及真实样本离线重编码，实时三相机采集另验。

## 选择哪一种

| 模式 | 图像 | 其他记录 | 适用场景 |
|---|---|---|---|
| `raw_mcap` | 原始像素进入MCAP | 同一MCAP | 标定、原始证据、需要像素无损 |
| `mp4` | 每个RGB流独立MP4 | 小型MCAP＋逐帧时间索引＋manifest/QC | 希望降低常规RGB数据体积、后续导出LeRobot v3 |

两种模式都保留输入、意图、命令、反馈、相机metadata和事件；深度仍原样进MCAP，保留位深、字节序和单位。保存/丢弃作用于整个episode目录，不只某个视频文件。

使用方法和编码参数见[操作手册](episode-collection.md)与[技术说明](episode-storage-and-configuration.md#mp4-编码配置)。编码器通过可选PyAV/FFmpeg复用，raw模式不要求PyAV；支持的具体编码器以本机预检为准，不绑定机械臂或相机厂商。

## 为什么体积差这么大

原始episode2共2353帧640×480 RGB8图像：

```text
2353 × 640 × 480 × 3 = 2,168,524,800 bytes
```

整个原始MCAP为2,182,403,012bytes，约99.364%是未压缩RGB像素。raw模式目前使用CompressionType.NONE；MCAP本身也支持[zstd/lz4分块压缩](https://mcap.dev/spec)，不能将容器与图像编码混为一谈。

MP4同样是容器，压缩效果取决于编码器和画质/码率参数。当前默认libx264/yuv420p、CRF20、veryfast，属于有损RGB编码。对上述真实样本离线重编码后，三路视频4.18MB、事件MCAP14.09MB、含索引等整个文件组20.45MB，帧数与源一致且deep QC通过。该场景压缩率不代表其他场景，也未证明任务细节或训练效果不受影响。完整证据见[验证报告](validation/2026-10-18-mp4-storage.md)。

## 时间与文件格式

raw保持 `real-episode/1`；MP4使用 `real-episode/2`：

```text
episode_000000/
  streams.mcap       # 事件、feedback、原始depth、RGB帧引用
  videos/stream_<id>.mp4
  index.jsonl        # 源/接收时间＋帧索引/PTS
  manifest.json      # media流名→相对路径、编码/帧数/hash
  alignment.jsonl
  qc.json
  commit.json
```

RGB帧引用的 `robot-infra-video-frame/1` JSON保留完整源图像metadata和视频位置。视频采用dense CFR：第i帧PTS=i，time_base=1/FPS，不插帧，也不覆盖源时间。因此视频时长不能冒充真实采集时长；源掉帧/间隔仍由原始时间索引QC发现。普通QC核对header/帧数/索引，deep进一步校验视频hash、全帧解码/PTS和MCAP引用。

## 与 LeRobot v3 的关系

这是一种便于后续训练导出的视频中间格式。LeRobot v3将状态/动作放在Parquet、相机图像编码为MP4，并用元数据关联episode边界；多个episode可共享一个视频/Parquet分片。见[官方v3格式](https://huggingface.co/docs/lerobot/en/lerobot-dataset-v3)和[迁移说明](https://huggingface.co/docs/lerobot/en/porting_datasets_v3)。

**本次没有实现完整LeRobot v3导出。** 训练采样率、相机对齐、state/action映射、任务/统计和多episode分片应在独立导出模块完成。编码设置、帧率/尺寸和索引都兼容时，可评估复用码流或重封装减少重复有损编码；尚未验证这一优化。实现参考官方[视频参数](https://huggingface.co/docs/lerobot/en/video_encoding_parameters)与[流式编码](https://huggingface.co/docs/lerobot/en/streaming_video_encoding)，未引入LeRobot训练依赖到核心控制。
