# ADR0017：独立采集配置与夹爪进入行为

2026-10-22，accepted。用户开始正式fill_pen_holder采集：默认打开、按扳机闭合、仅头部深度、RGB MP4。

原逻辑只有扳机相对进入时变化后才下发夹爪目标，单独反转trigger_pressed不能满足默认打开。新增可选gripper.teleop_start：preserve（省略时默认，保留旧行为）或follow_trigger（遥操阶段收到有效手柄输入即使用当前扳机映射）。后者配合trigger_pressed=close，使松开时为limits_m上界、按下至下界；中间值连续映射。没有有效控制器、不在TELEOP、home、暂停和退出时不主动开合。夹爪继续通过独立目标通道、所有权和最终guard，不增加SDK旁路。

新增collect-configure，从已有robot-deployment/1复制设备身份并生成独立session/cameras/deployment三个文件。方向、进入行为、图像后端、深度角色与原生分辨率/帧率由参数明确给定；不在核心写死head/left/right序列号。输出目录必须新建，原配置不改，深度只在选定角色capture与record分支启用；未选角色关闭深度。

沿用real-episode/2的MP4 RGB与原始MCAP depth，不把16位深度编码为RGB H.264，不猜米制scale，不默认对齐RGB。相机内参/原始帧与时间戳仍按现有路径记录。存储契约版本不变，旧session配置默认preserve保持行为兼容。

新正式配置与原deployment分离，需要显式--deployment选择；CLI仍允许--image-storage显式覆盖。没有支持任意图解释器或新训练出口的额外承诺。验证范围见2026-10-22正式采集配置报告，首条真人遥操/完整数采仍需用户启动和验收。
