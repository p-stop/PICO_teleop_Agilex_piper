## 023 增量：VR 相机三角形布局（2026-11-03）

- `web/xr-scene.js`：`vr_layout.arrangement` 新增 `"triangle"`：`scene_fixed` 在上方中间，`left_wrist` / `right_wrist` 在下方左右，三块面板和上下两块 HUD 都转向观看者。参数（米，相对锚点）：`top_width_m` 1.8、`top_y_m` 0.78、`bottom_width_m` 1.5、`bottom_x_m` ±0.82、`bottom_y_m` -0.66、`hud_width_m` 2.0、`hud_gap_m` 0.04；距离仍用 `distance_m`（2.21）。不写 `arrangement` 或写 `"row"` 时是原来的横排布局（主视角 5.4 m 宽，约占 100° 视野）。
- `teleop_session.py`：校验 `arrangement` 只能是 `row` / `triangle`，`vr_layout` 里以 `_m` 结尾的长度必须是有限数、绝对值不超过 10 m。
- PICO-ACT `profiles/collection/session.json` 改为 `triangle`（collect 和 pico-record 共用这份 profile）。改回横排：把 `arrangement` 改成 `"row"`。
- 测试：023 全量 315 passed、1 skipped（需要 rclpy）。

# Changelog

- 023 increment interp-a/c (2026-11-03 20:20, in place; previous files in
  PICO-ACT/backups/023-before-interp-ac-20261103/). All new behavior is off by
  default and enabled per profile:
  (a) teleop_filter.input_delay_s > 0: fixed-delay input interpolation. Packets
  are placed on the host clock with client_time_ms + sliding-minimum offset
  (input_clock_window_s, default 5 s); the control tick uses the pose at now-D
  (linear position, slerp orientation), holding the last frame when the buffer
  runs dry; A/X edges are not delayed. Interpolated IK goals get unique seqs
  (intent carries input_seq/interp/interp_alpha).
  (c) teleop_filter.ik_gate_joint_jump_rad > 0: drop an IK result whose target
  moved < ik_gate_target_m and < ik_gate_target_rad from the last followed target
  while the joints jump more than the threshold (event motion_gate).
  ik.wrist_smooth_multiplier > 1 with ik.wrist_smooth_q5_rad: when |q5| of the
  IK seed is below the threshold, joints 4 and 6 get that multiplier on the
  smoothness weight (PinocchioModel.ik(smooth_scale=...); result wrist_smooth).
  Tests: +6 (316 passed). PICO-ACT collection profile enables D=0.1 s, gate
  1 mm / 0.01 rad / 15 mrad, wrist 0.15 rad x10.
- 023 webrtc-smoothing (2026-11-03): base 021-webrtc-r3 plus the 022 teleop
  smoothing, merged 3-way against 018 (022's actual base). Only
  teleop_session.py and tests/test_teleop_session.py change: One-Euro input
  low-pass with anchor-relative translation/rotation deadbands (GripFilter),
  IK convergence gate (converged or residual <= 5mm), per-cycle first-order
  blending plus 0.8rad/s joint rate limit (_shape_command), and teleop_filter
  profile validation. 021's webrtc input, TeleopSession(metrics=...) and the
  control.tick_interval/control.tick_work metrics are kept. All other files
  (control_webrtc, camera_ingress, preview, performance, live_teleop,
  session_launcher, web/*) are 021-r3 unchanged.
- Plan018: add optional immediate trigger following on TELEOP entry, keeping
  legacy preserve-until-change behavior. Missing trigger data never selects an
  implicit released target. Add passive collect-configure for independent
  machine-derived gripper/storage/depth profile sets; validate three RGB MP4
  streams plus only the head's raw16UC1 depth without starting arm drivers.

- Plan014: add source-neutral native ExecutionSession, evidence-backed replay
  clips, explicit workflow-run and fake/in-process or separate-process HTTP
  mock policy fixtures. Reuse LiveGateway/PiperROSBackend; preserve old teleop
  and read-only replay. A4-S three-second physical replay passed; model/GPU,
  precision trajectory tracking and arbitrary graph execution remain separate.

## Unreleased

- Add read-only real-episode audit outputs, causal training views using
  confirmed published targets, offline trajectory timelines and typed
  collection/replay/inference graph plans. Keep physical runner/model/export
  implementation boundaries explicit.
- Segment diagnostic journals without deleting evidence; preserve every
  native-rate received frame and record writer counters/callback sequences.
  Capture pre-episode published-target snapshots and optional ACK input timing.

- Add configurable read-only native-Euler/PoseStamped observation sources,
  explicit conversion provenance and common MCAP/index/alignment/QC support.
  Preserve Piper SDK integers/units with the existing driver cache only;
  document the full dataset field dictionary and remaining measurement gaps.

- Add pluggable raw_mcap/MP4 image storage with optional PyAV, configurable
  encoder settings, real-episode/2 video references/PTS indexes and media QC.
  Preserve raw v1, native depth and common asynchronous episode transactions;
  expose collect --image-storage without changing control or input adapters.
- Split operator collection steps from technical storage/configuration docs;
  fix the device launcher to honor explicit deployment selection consistently
  for ROS setup, Python paths and the CLI instead of overriding it with defaults.
- Add robot-local collect/device-teleop commands, independently configurable
  camera capture/preview/record branches and a bounded asynchronous raw MCAP
  writer with task/episode storage, A save/X discard, alignment and deep QC.
- Separate WSS control from HTTPS previews, latch connection failures, add
  preview diagnostics and route independent trigger jaws through the gateway.
- Validate one saved26.179s A4-S RGB episode with three near30fps cameras and
  deep integrity/QC; retain failed trials and leave policy/depth validation open.

- Add live-teleop/2 with A/home/start/end, explicit pause/resume, clutch pose
  control and per-gripper trigger polarity; preserve jaw opening on home/hold.
- Use optional Pinocchio/SciPy with independent latest-target solver processes,
  and a checked wrapper around the installed Piper driver without vendor edits.
- Add robot-infra teleop supervision and offline Three.js fixed VR video/HUD.
- Validate onsite dual-arm home and full session workflow; raw MCAP collection
  was subsequently validated above, while policy inference remains pending.

- Fix the A4-S dual-VR graph and logical-endpoint versus backend-batch boundary.
- Add collection-plan/1 and collection-event/1 for a separate one-group,
  multi-endpoint fake execution/streaming MCAP slice; preserve M1.
- Add collect-validate, collect-demo and device-free collect-read.
- Exercise source replacement, final checks per send, partial batch failure
  and aborted-episode integrity; this collection path stays fake-only.
- Add experimental explicit-profile FK/IK, position clutch mapping, device-local
  live gateway/watchdog and audited Piper ROS adapter; onsite dual-arm motion
  and three-camera immersive layout validated within bounded scope.
- Add JPEG preview isolation, diagnostic journals, graph/dataflow and deployment
  docs. Preserve incomplete original diagnostics; fix ROS shutdown finalization
  and validate timer/SIGINT without hardware. Full raw collection/policy pending.

## 0.3.0 — 2026-10-16

- Add independent HTTPS WebXR raw input recorder and offline browser assets.
- Add bounded RGB/metadata sampling with an optional ROS RealSense adapter,
  and receive-only SocketCAN sampling with explicit Piper-v2 joint decoding.
- Distinguish USB descriptor and RealSense SDK identity namespaces; correct
  the earlier camera-serial mismatch conclusion with physical-port evidence.
- Validate PICO input, three RGB streams and dual-arm feedback on Ubuntu24.04;
  no physical command backend, synchronized episodes or real teleop yet.
- Preserve M1 control/event contract 0.3.0-m1.

## 0.2.0 — 2026-10-16

- Add passive Linux USB/CAN/serial/video discovery, injected collectors,
  offline snapshots and explicit configurable device-role binding.
- Add `robot-infra discover` and a stdlib-only checkout bootstrap.
- Add remote source/environment audit, deployment and publishing guidance.
- Preserve fixed M1 control/event contract 0.3.0-m1; no physical control
  backend, camera streaming, VR adapter or policy execution is added.

## 0.1.0 — 2026-10-15

- Initial hardware-free control, ownership/guard, stub policy, MCAP and
  read-only replay slice, validated on Windows.
