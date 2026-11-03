# Project Status

## Approved scope (2026-10-24): S0 and S2; S1 deferred

The user approved the020 complete physical baseline (S0) and optional WebRTC
input (S2). The broader input-contract/asynchronous-WSS proposal (S1) is
deferred, not a prerequisite. Reuse `webxr-input/1` and the existing robot-side
`TeleopSession` state machine. Start with one reliable, ordered data channel;
no new command bus or browser-owned collection workflow. See [plan021](../plans/021-transport-semantics-and-live-validation.md).
Current remains018; today's operator is present and can use Quest 3.

S0 completed one37.276s physical collection/save: responsive per operator, no
automatic disconnect, but left-wrist RGB gap235.98ms fails QC; writer loss is0
and all MP4s fully decode. Six child exits0. S2 candidate implementation is
deployed separately (v2), Windows293/10skip, Ubuntu306, Node3 passing; optional
dependency/config preflight passes. Camera-only300s diagnostic QC/deep passes,
but received0 headset inputs, so Quest/selected-UDP and physical S2 remain
unvalidated. All test services ended; no formal promotion. See [evidence](validation/2026-10-24-state-machine-and-webrtc.md)
and [plain-language workflow](webxr-workflow-and-transport.md).

15:57 CST retry: the previous page was unreachable because its diagnostic
window had expired. v2 camera/input-only diagnostic is now open for600s;
robot-local DIAGNOSTIC/webrtc and Windows HTTP200 verified. Active receipt:
`runs/021-active-headset-diagnostic.json`, output
`runs/021-quest-webrtc-retry-20261024T075642Z`. Awaiting headset evidence;
no arm driver started. This supersedes the earlier all-services-ended state.

## Historical proposal (2026-10-23)

2026-10-23 plan021 is proposed, awaiting the user's explicit review as requested.
The [review document](transport-review.md) separates current TCP/UDP/IPC/CAN
facts from implementation options, evidence and necessity. Suggested first
batch S0–S2 covers020 physical baseline, common latest-state/idempotent-command
semantics with asynchronous WSS, then a WebRTC data adapter and controlled
physical A/B. Video S3 is a separate later review. No implementation, dependency,
network setting, deployment or device start occurred for021; only read-only
host inspection and documents. Current remains018; candidate020 unchanged.

## Latest candidate slice: communication profiling and preview isolation

2026-10-23 plan020 adds [communication/thread and QuestArm comparison](communication-and-performance.md),
bounded performance-snapshot/1 timing, shared CameraIngress/PreviewWorker,
demand-driven in-memory preview with optional JPEG archive, and independent
camera/WSS/offline metadata-audit tools. Image QoS is configurable, defaulting
to the original best_effort/5. Control ACK, scheduling, physical gateway,
gripper behavior and QC thresholds are unchanged.

[Field evidence](validation/2026-10-23-communication-performance.md): eleven
camera-only runs,19 minutes total recording, ten capture/deep QC passes and
one RGB gap failure. Missing RGB frames have continuous device metadata,
narrowing that occurrence to image processing/publication/DDS/receive after
driver observation. RELIABLE60/180s candidates pass, not a universal fix.
Quest3 operator reported100–200ms RTT, peaks600–700ms and a disconnect;
its300s local RGB-D recording passes. Pure WSS loopback p950.763ms versus
Windows WLAN109ms; same-process recording/preview WSS loopback p951.962ms.
ICMP also shows tails/loss. Wireless power-save is a candidate, unchanged.

Runtime is deployed only in independent020 candidate directories; current
and formal-018 profiles remain018. No arm driver/command was created.
All timed camera/echo services stopped,8445/8446 closed. Final Windows291/10skip,
Ubuntu304 and Node2 pass, including the offline metadata audit. Clean candidate
releases/020-20261023-profiled has byte-equivalent Python/web files to tested
v2, excluding generated package metadata; receipts are recorded in plan020.
Full physical concurrency, asynchronous input and streaming media remain
future work. User-reported Quest3 operability is distinct from latency proof.

## Latest field audit: collection gaps and VR latency

2026-10-22 plan019 is a read-only audit of the active018 run, with
[evidence and next steps](research/2026-10-22-collection-latency-audit.md).
Ten completed fill_pen_holder attempts include six with camera frame gaps;
writer counters show no queue drops/errors or rate filtering, but received
source stamps also have167–300ms gaps. USB/driver/DDS/callback cause remains
unresolved. Control RTT median27/p95121.8ms contrasts with app.input p950.335ms
(not total host processing). ACK-gated input and8→2fps preview degradation
amplify delay; headset visibility pause is independently confirmed.
Snapshot resource measurements are not fault-time traces. No service, source
dataset, configuration, QC threshold or runtime code was changed; no physical
command or new capture test was issued. Runtime remains018; performance
isolation and controlled comparisons are proposed, not implemented.

## Latest runtime slice: formal collection profiles

2026-10-22 plan018 adds optional gripper.teleop_start=follow_trigger with
trigger_pressed=close, enabling released-trigger opening immediately in
TELEOP. Old profiles default to preserve; home/pause/startup and missing
controller/button data do not command the jaw. The gateway remains the only
physical write path. collect-configure generates an independent profile set
from existing identities, with explicit RGB backend/depth roles/profile.

fill_pen_holder uses profiles/formal-018/deployment.json: RGB640x480x30 MP4
for all three cameras, native scene_fixed depth640x480x30 only, wrist depth off.
Original deployment/profile and user datasets remain unchanged. CAN can0/can2
were DOWN; operator must activate them before full collect preflight/start.
Current points to releases/018-20261022-formal-collection; old014 retained.
Installed check-only refused CAN DOWN before constructing any devices.

Windows284 passed/10 skipped, Ubuntu297 passed. Camera-only physical ten-second
recording passed capture/deep QC: three RGB300 frames each, head depth295,
~30fps with native16UC1, all camera children exited0. No arm driver or formal
task episode was started. The new jaw entry behavior has fake evidence;
first full PICO/arms/RGB-D episode remains operator validation. See
[operator guide](episode-collection.md), [validation](validation/2026-10-22-formal-collection.md),
ADR0017 and plan018 for final deployment receipt/source identity.

## Latest research (no runtime change)

2026-10-22 plan017 adds the [data-quality evidence review](research/2026-10-22-data-quality-quantification.md),
[quantitative standard proposal](data-quality-standard.md), and
[machine-readable metric definitions](assets/data-quality/metrics-proposal.json).
The review covers seven requested companies plus academic data-selection,
coverage and latency work. Twenty proposed metrics separate integrity, timing,
semantics, perception, behavior, coverage and deployment; unknown measurements,
task-specific thresholds and recovery-data uses remain explicit. Definitions
are documentation only, not a new runtime QC schema or remote configuration.
Local links, eight example settings and worked arithmetic were checked;
framework source hash is unchanged from014/016. No hardware or model evaluation
was performed. See [validation](validation/2026-10-22-data-quality.md) and
[plan017](../plans/017-data-quality-standards.md). The proposed next slice is
offline timing/coverage/action-provenance reporting, followed by annotations
and controlled learning experiments.

### Previous mathematical modeling

2026-10-22 plan016 adds the [unified mathematical model](research/2026-10-22-pipeline-mathematical-model.md),
[eight-lesson course](pipeline-learning.md), and [offline learning reader](pipeline-model.html).
It maps the current hybrid/multirate teleop and inference implementations to
explicit clocks, IK objectives/state, gateway behavior, plant uncertainty,
recording queues, training labels, and chunk timing budgets. Implemented
behavior, analytical approximations and future proposals are distinguished.
The reader includes worked examples, expandable exercises, an IK response
experiment and four-budget inference calculator. Core source hash remains
unchanged from plan014; no device connection, parameter change or new physical
validation occurred. Hardware identification, real model execution, Timing QC
and transport improvements remain future work. See [plan016](../plans/016-pipeline-mathematical-model.md)
for reproducible report verification and the checkpoint.

### Previous signal research

2026-10-20 plan015 adds [signal/timing research](research/2026-10-20-signal-timing-and-learning.md)
and an [offline interactive report](signal-timing-report.html), with reproducible
JSON/CSV/SVG from plan014's recorded replay. RUNNING-window publish rate is
about60Hz, feedback receipt about169Hz; neither identifies native servo rate.
Report distinguishes reconstruction, target playback and physical reproduction;
documents ACK-gated input, asynchronous IK, causal training views and RTC limits.
No device was connected or commanded for this research; plan014 runtime and
deployment remain the latest implementation. Proposed timing QC, transport
benchmarking and replay-precision evaluation remain future work.

## Current phase

Updated 2026-10-20, architecture v0.16. Plan014 implements native
ReplaySource/AsyncPolicySource -> ExecutionSession -> existing LiveGateway ->
FakeBackend/PiperROSBackend, with explicit workflow-session/1 configuration.
The old teleop/collection entry is unchanged; read-only replay commands stay
read-only. This is a fixed native binding, not an arbitrary graph interpreter.

A4-S physical replay passed: saved new_test episode1 first3s, configured
4s zero-joint alignment, original-time native targets and evidence-backed jaw
initial state. Operator confirmed both arms moved and stopped without anomaly.
Actual feedback, ownership/guards, source hash and cleanup were verified;
both drivers exited0. Native driver speed remains20%; end-cut instantaneous
tracking errors max0.098176/0.051588rad, not precision reproduction certification.

Fake inference passed both in-process and separate-process HTTP with three
real synthetic RGB buffers and fake measured feedback. Normal chunk execution
completed; injected model HTTP422 produced FAULT/nonzero exit and clean stop.
Timeout/old epoch/wrong units/empty chunks/queue exhaustion are tested.
No real camera/model/GPU policy or physical mock-policy execution is supported.

Windows278 passed/10 skipped; Ubuntu291 passed including localhost ROS.
Current deployment `releases/014-20261020-native-validated`; old013 retained,
machine profiles unchanged, no physical session left running. Read
[operator guide](replay-and-mock-inference.md),
[validation](validation/2026-10-20-replay-and-mock.md), ADR0016 and plan014.

## Previous data and graph design slice

Updated 2026-10-19, architecture v0.15. Plan013 audits three real MP4
new_test episodes: 0/1 saved with capture QC/deep passing, 2 remains review
with a 197.477ms fixed-camera frame gap, deep passing. All three contain
native/converted pose streams and no depth. RTT peaks and the post-episode
stale ticket are distinguished from capture QC. Task outcomes remain pending
manual annotation; these are engineering samples, not confirmed task demos.

New no-device software: shared streaming reader, episode-audit with separate
outputs, training-view/1 causal state/image references and confirmed target
actions, original-time trajectory-check and experiment-graph/1 typed templates
for collection/replay/inference. Unknown gripper goals remain null/masked;
new context.initial_targets records returned publish calls without claiming
hardware ACK. LeRobot v3 writer, physical graph runner/replay and ZeroWAM
network bridge are still pending. ZeroWAM runs on a separate server; its
EEF action/cache and legacy dataset requirements need explicit adapters.

Fixes: append-only segmented diagnostics (old session approached 512MiB),
native-FPS recording preserves received frames, callback/writer counters and
ACK input processing timing. These do not prove the old RTT root cause or
197ms image gap is resolved. Windows261 passed/10 skipped, Ubuntu274 passed;
Node2 passed. Real views: ep0 1858/740 valid, ep1 1724/1722 valid, with unknown
early goals explained, not fabricated. No physical service was started.

Deployed to `releases/013-20261019-workflows-validated` via the existing device
entry; previous 012 and configuration backups retained. Both raw/MP4 collect
preflights and all three offline graph plans pass; service ports remain closed.
Final archive/package and deployment receipts are recorded in plan013.

Read [data audit](research/2026-10-19-new-test-audit.md),
[training report](training-data-format-report.md), [three graphs](three-workflow-graphs.md),
[ZeroWAM](research/2026-10-19-zerowam-deployment.md),
[validation](validation/2026-10-19-data-and-workflows.md) and plan013 for deployment.

## Previous pose observation slice

Updated: 2026-10-18, architecture v0.14. Plan012 adds optional named pose
observations to raw/MP4 episodes. Piper native integer XYZ/Euler, units and
SDK float seconds are preserved by a read-only cache publisher in the
existing wrapper; no new SDK connection/query or control path. Existing ROS
Euler-to-quaternion output is a separate source with explicit orientation
provenance/conversion. Unknown frame/TCP/time semantics remain explicit.
MCAP/index/alignment/QC and directory lifecycle are shared with other streams.
Old episodes are not backfilled. Generic pose collection supports arbitrary
source IDs; the deployed WebXR controller still binds left/right arms.

Windows250 passed/10 skipped; Ubuntu263 passed, including actual localhost
ROS PoseStamped/String serialization without hardware. Config, native units,
converted provenance, missing/frozen/zero stamps and invalid quaternions,
raw/MP4 roundtrip/deep QC and existing regressions passed. Initial isolated
test setup lacked its temporary artifacts parent and used a default ROS
executor for a custom Context; the harness was corrected before the pass.

Read the [supervisor data format report](collection-data-format-report.md),
[ADR0014](adr/0014-native-pose-observations-and-provenance.md) and
[plan012](../plans/012-cartesian-feedback-and-data-dictionary.md). Added pose
streams and real-time MP4 still need onsite validation; the earlier real raw
episode does not contain these new pose streams. Deployment receipt/checkpoint
is in plan012. Current points to releases/012-20261018-pose-validated; raw/mp4
installed check-only both passed with four explicitly marked pose sources.
The session profile backup is profiles/robot.session.pre-012.json. Ports8445/
8446 remain closed. No physical experiment was started for this change.

## Previous MP4 software slice

Updated: 2026-10-18, architecture v0.13. Plan011 adds optional MP4 storage
through an independent ImageStorage protocol/factory. raw_mcap stays default
and uses real-episode/1; MP4 uses real-episode/2 with per-stream videos,
JSON frame references, original timestamps and frame/PTS indexes. Events and
native depth remain in MCAP. The same bounded recorder worker, save/discard
and backup/rollback lifecycle serves both modes; no robot/input SDK changes.

Choose with collect --image-storage mp4 or recording.storage. Encoder,
pixel format, options, GOP and thread count are configurable. Optional
PyAV16.1/FFmpeg is preflighted in memory before device construction; raw
mode needs no PyAV. QC supports both versions; MP4 deep checking includes
file hashes, full decode/count/PTS and MCAP/index cross-reference checks.

Windows236 tests passed/9 skipped; Ubuntu248 passed; Node2 tests and changed
module syntax passed. Original data was not changed. On the robot host,
existing26.179s RGB episode2 was re-encoded offline:2,182,403,012 bytes source
MCAP became20,445,574 bytes of videos/events/indexes, all2353 RGB frames
preserved, QC/deep passed. This was no-device offline work, not a validated
real-time MP4 collection session or a training-quality/LeRobot compatibility
benchmark. Full LeRobot v3 Parquet export is still not implemented.

Read [operator guide](episode-collection.md), [technical configuration](episode-storage-and-configuration.md),
[storage layout](recording-storage-options.md), [ADR0013](adr/0013-pluggable-image-storage-and-mp4.md),
[validation](validation/2026-10-18-mp4-storage.md) and [plan011](../plans/011-pluggable-image-storage.md).
Robot current now points to releases/011-20261018-mp4-validated; the isolated
optional PyAV path is configured. Installed raw/mp4 check-only both passed
without device construction; ports8445/8446 remain closed. Deployment/final
checkpoint is recorded in plan011; no physical experiment was started for
this feature. Historical raw onsite evidence follows.

## Previously validated A4-S raw collection

Updated: 2026-10-18, architecture v0.12. Plan009 is complete for the
implemented A4-S RGB collection slice: robot-local launch, configurable
capture/preview/record, independent jaws, A save/X discard, original MCAP,
asynchronous writer and offline QC. M1/fake contracts remain unchanged.

The onsite user confirmed the complete flow works normally. Saved episode2
lasted26.179s, contains2,182,403,012 bytes of MCAP and24,380 messages. Three
native RGB640x480 streams have784/784/785 frames at29.941/29.939/29.986fps;
there are no application queue drops, profile mismatches or source timestamp
regressions. All785 nearest-receipt alignment rows are valid. Deep SHA256,
CRC, footer, count and raw-image decoding checks pass; QC passes with no
issues. This is not exposure synchronization or task-success annotation.

Independent jaw-only commands were observed for both arms (left913/right826)
and confirmed onsite without clutch. The saved trial has518 inputs, RTT
median17.8ms/p95 101.5ms/max299.2ms and max input gap211.1ms, with no
communication interruption. Earlier ON/OFF diagnostics did not isolate a
single cause; the earlier headset-frame pause and failed trials are retained.
One successful trial does not establish long-duration network reliability.

Robot entry: `/home/ros/robot-infra/bin/robot-infra collect`. Data:
`/home/ros/robot-infra/validation-data/a4s-session009-validation/episodes/episode_000002`.
Two incomplete episodes and three discarded episodes remain preserved.
Windows/SSH/proxy/CDN are not runtime dependencies; PICO still needs LAN access.
Read [operation](episode-collection.md), [onsite evidence](validation/2026-10-18-a4s-link-and-episodes.md),
[ADR0012](adr/0012-real-episodes-and-camera-fanout.md) and [plan009](../plans/009-local-deployment-and-real-episodes.md).

Validation: Windows218 passed/1 skipped (Pinocchio absent); Ubuntu222 passed
including Pinocchio; Node2 behavior tests passed; module syntax, wheel/sdist
assets and exclusion checks passed. r8 differs from Ubuntu-tested r7 only in
two frontend lines; Python source is identical. The executed package tree
SHA256 is `356fa01edbaf0044d301d6b1495a3dd24693a19f04fb9576fc462a205e6e0999`.
No system Python packages or vendor sources changed; no Git remote published.

All temporary stacks from today stopped normally. Final supervisor4314 and
all six children exited, child exit codes all0, journal finalized with
error=null/writer_stopped=true,8445/8446 closed and task lock released.
No active experiment remains. Next: repeated task episodes and sustained
latency tests, task labels/inspection and training export, then real policy
inference using the shared execution path. Depth/other resolutions, A1/A2,
policy inference and full M2 remain unvalidated.

## Previous v2 free-teleop milestone

Updated: 2026-10-16, architecture v0.11. Plan008 adds the experimental
`live-teleop/2` session workflow, Pinocchio/SciPy worker processes, checked
vendor-driver wrapper, explicit gripper targets and modular world-fixed VR UI.
`robot-infra teleop` launches the project-owned stack; `--check-only` constructs
no devices. M1/fake collection contracts and old live v1 compatibility remain.

Current v2 onsite evidence: user confirmed large fixed screens/HUD, A/home,
both-arm position/orientation following, jaws, clutch release and A/end.
Feedback reached zero on both sides; HOMING→READY took4.52s, no guard
rejection and no jaw target during home. First A originally only resumed
PAUSED→STANDBY; fixed to execute the displayed phase action after neutral
input, with regression tests. One complete teleop trial ended in STANDBY,
followed by another home/READY and VR-exit PAUSED. User then requested
press-to-open/release-to-close; this explicit per-jaw configuration was deployed
and independently confirmed onsite. Do not inherit v1 claims as v2 evidence.

Windows final full suite196 passed/1 skipped (Pinocchio absent). Ubuntu final
full suite200 passed including actual Pinocchio; latest trigger-relevant suite35
passed. Three frontend modules passed node syntax checks. Source deployment
uses the robot's existing Pinocchio4.0.0/SciPy1.18.0; no system packages/vendor
sources modified. All three stacks' six children exited0 and produced journal
finalize/summary (error=null, writer_stopped=true). All project-owned processes
and solver descendants are stopped; port8445 is closed. All22028 indexed
previews passed path/file/hash checks. Checkpoint/run paths are in plan008.

Free v2 removes the old commissioning Cartesian/startup-excursion/software
joint-speed/tracking-error envelopes. Native speed remains20%; joint/jaw
limits, ownership, epochs and communication validity remain. No automatic
enable on launch or jaw-close on enable/home/stop. Diagnostic JSONL/JPEG is
not raw MCAP collection, saved episodes or policy inference. See
[operation and dataflow](teleop-session.md), [onsite evidence](validation/2026-10-16-a4s-session.md), [ADR-0011](adr/0011-session-workflow-and-pinocchio-workers.md)
and [plan008](../plans/008-session-workflow-and-pinocchio.md).

## Previous live v1 milestone

Updated: 2026-10-16. Architecture v0.10; package metadata0.3.0 plus
unreleased collection/live increments; M1 contract0.3.0-m1 unchanged.
One-group N-endpoint fake collection/streaming MCAP stays fake-only.
An independent experimental live-teleop/1 path now provides serial URDF FK,
local DLS IK, relative-position clutch mapping, device-local owner/epoch,
monotonic watchdog/guards and an audited Piper ROS adapter. Live diagnostics
use live-teleop-event/1 JSONL + lossy JPEG sidecars, not collection-event/1.

**Physical result:** onsite user confirmed both Piper arms follow the
corresponding PICO controllers, up/left/right appear correct, and release
holds position. Three-camera layout was confirmed inside PICO: fixed D455
large in the center, wrist D435 views smaller at both sides. Ubuntu24.04.4,
Python3.12.3, ROS Jazzy; can0 left/can2 right; base/lift/jaw untouched.
Native drivers reused without modifying vendor sources or installing packages.
Model FK agrees with Pinocchio and SDK; this does not establish external TCP
accuracy. [Detailed graph/dataflow](a4s-dataflow.md),
[physical evidence and limits](validation/2026-10-16-a4s-live-control.md),
[operation](live-teleop.md), [ADR-0010](adr/0010-live-gateway-and-position-teleop.md).

Final physical live-03:1813 raw input frames,123092 feedback events,2826
commands including holds,7188 indexed previews. Observed FK displacements
include about64mm right/62mm left. IK1068/1353 converged;285 met iteration
time budget. Partial release transients up to0.0222rad mean no instant-stop
claim. User-requested unrestricted/100% startup was rejected by automatic
approval; tested profile remained10cm clutch range/0.6rad startup excursion,
0.4rad/s and20% native driver speed. Both arms position-only, grippers disabled.

All temporary physical stack processes are stopped; control was revoked and
fresh measured hold attempted, with no auto home/disable. All30746 preview
references across three diagnostics passed file/hash checks. Original three
runs lack finalize/summary because of a ROS shutdown-context bug: retain as
incomplete diagnostics, never complete episodes. Fix passed timer/SIGINT
exit0 + summary/finalize checks in isolated ROS domain65 with zero commands;
it has not yet had a fresh physical episode. Full-stack launcher was added,
but onsite deployment used staged equivalent scripts, not that launcher.

Windows/Python3.11.12 and isolated Ubuntu/Python3.12.3 full suites each182
passed (165 prior +17 new). Linux used temporary pure-Python MCAP with license
and existing pytest/jsonschema, no installation. ROS shutdown integration is
separate from physical evidence. Local baseline5191923 remains, new work is
uncommitted; no Git remote created or repository published. Local serial/IP
profiles, credentials and raw evidence remain excluded from release.

Earlier plan004 independently validated PICO input, three RGB streams and
receive-only CAN feedback; see [that report](validation/2026-10-16-a4s-live-observation.md).
USB descriptor serial and RealSense SDK serial remain explicitly separate;
old camera SDK serials were valid, with wrist roles requiring current binding.

Next: improve IK/workspace and startup posture, verify fore/aft/frame/TCP,
add independently tested jaw/rotation control, then real raw MCAP episode/QC
and policy observation/action decoding/scheduling. No complete synchronized
training collection, real policy, collision planner, independent hardware
crash watchdog, arbitrary graph compiler, GUI or A1/A2 acceptance yet.
[Plan007](../plans/007-live-vr-teleop-and-video.md) records the checkpoint.

## Existing robot workflow reference (research only)

Plan005 traced the robot host's old teleop/recording/policy code and historical
artifacts. Strong evidence exists for right-master→left-slave+base/two-camera
collection and historical policy EXEC publication; VR/right-side IK also has
runtime logs. This is a new lab reference, not this project's hardware result.
Of38 historical manifests all marked complete,36 have parseable bag metadata
and normal MCAP end markers;85/88 have empty metadata and missing end markers.
An offline18,000-message numeric prefix from one bag showed changing commands,
master input and feedback; no robot commands were executed in this research.
At least30 saved ROS log files contain policy EXEC excerpts. Training-server
conversion/checkpoint lineage, corresponding physical receipts and task
evaluation remain unverified. Old camera launch uses valid SDK serials but
its wrist role names are reversed relative to current user-confirmed mounting;
historical mounting cannot be inferred from this alone.
See [the report](research/2026-10-16-existing-robot-workflow.md),
[reference index](reference-repositories.md) and
[plan005](../plans/005-existing-robot-workflow-research.md). Research changes
no runtime contract/backend selection and does not complete M2 acceptance.

## Repository audit

- Before the v0.4 revision, the repository contained only AGENTS.md,
  docs/architecture.md and this status document.
- Before M1 there was no source, packaging, executable configuration or tests.
- M1 now has src/robot_infra, packaged JSON schemas, configs/fake-control.json
  and an invalid fixture, pyproject.toml/uv.lock and 80 M1 tests. Six new host
  inventory tests plus 19 discovery tests brought the prior total to105; 20 live-input/observation tests brought it to125; 40 collection tests made165;17 new live-control tests now make182.
  CI is not set up.
- Fourteen local reference repositories were inventoried, with focused source
  inspection of Piper/QuestArm, GELLO/FR3 and RealSense. No upstream build,
  test or hardware result was reproduced. See docs/reference-repositories.md.
- A first local Git baseline is recorded on codex/m2-discovery-baseline; user requested no remote
  creation/push yet. Relevant repos, PDF, evidence, local profiles and generated
  data are excluded by .gitignore/MANIFEST.in. Before the SSH inventory,
  no remote connection was made. No hardware command was performed. Development dependencies were
  installed into local ignored venv/cache directories using existing Python.

## Confirmed decisions

- Devices are described through overlapping capabilities:
  execution endpoints, intent sources, and observation sources.
- A typed-port graph describes devices, software nodes, mappings, and data flow.
- Models are intent-source nodes.
- Every physical command passes through arbitration and safety guards.
- MCAP is the raw evidence format; LeRobot is a derived training-data format.
- Simulation and real hardware share contracts but not necessarily assets,
  timing, calibration, or safety approval.
- PhyAgentOS may be integrated as an upper agent/task layer rather than rebuilt.
- The core is transport-neutral; ROS and vendor SDKs remain at plugin boundaries.
- Development, device execution, GPU inference and simulation are explicit host
  roles, with separate dependencies and evidence for each OS/profile.
- Policy artifacts, observation snapshots, chunk scheduling and motion profiles
  are distinct contracts. Native policy output still passes arbitration/safety.
- Device-local ownership epochs invalidate queued and in-flight actions after
  takeover, reset, faults or reconnection.
- GUI is a lower-priority client of the same graph schema and session API.
- The experiment loop gains thin task/evaluation, dataset quality/lineage,
  run-result and failure-label metadata proposals; training and task intelligence
  remain external. This does not expand the first implementation slice.
- Quickstart time numbers are conditional validation targets. Unknown hardware
  has no fixed setup-time promise; no efficiency benefit has been measured.

These are architecture decisions; only the M1 subset, passive discovery,
independent diagnostics, one-group fake collection and the bounded dual-arm live subset are implemented. Passive discovery/binding is described separately in ADR-0007.
See ADR-0001 through ADR-0010 under docs/adr/. Product positioning
and efficiency claims still await comparative evidence.

## First implementation target: complete on Windows fake

The following M1 subset is implemented and covered by tests:

1. Versioned port and device manifests.
2. Graph configuration schema.
3. Static graph validation and `dry-run`.
4. Fake robot, fake camera, and fake teleoperator plugins.
5. Control ownership and multiple-writer rejection.
6. Minimal session lifecycle.
7. Deterministic recording and replay test.
8. Stub policy with declared action/observation semantics and injected latency.
9. Epoch invalidation, stale-result rejection and takeover tests.

No real robot control is included in this milestone.

Next, add multi-endpoint fake ownership/guards, bounded recording and the
continuous A4-S observation/recording path before physical motion, following
plans/002-a4s-teleop-acquisition.md. Model/FK/IK checks and minimal simulation
or shadow remain admission steps; full A3 is not a prerequisite to A4-S.

plans/001-fake-control-loop.md records completed milestones and limitations.
The CLI now supports validate/--dry-run, run with a new MCAP output, and
read-only replay/--jsonl. Graph validation permits only the fixed M1 topology,
not arbitrary plugins or the architecture's historical YAML examples.

Validation: 80 tests passed on Windows/Python3.11.12, including independent
MCAP reading, corruption rejection, no-device replay and takeover/expiry
boundaries. The 500-step demo has 5053 events, 502 fake executions and four
intentional rejections. A separate wheel-only environment passed smoke tests
outside the source directory. Disabling the limit check in a source copy was
detected by the guard regression test. No Linux or physical result is inferred.
Source-file hashes are preserved in artifacts/m1-source-manifest.json;
documentation checks passed for 23 Markdown files and 74 internal links.

Earlier on 2026-10-16, 86 tests passed on Windows/Python3.11.12 (80 M1 + 6 inventory;
artifacts/2026-10-16-pytest.xml). M1 source/contracts remain unchanged. Linux
probe behavior was tested with fakes only; neither Linux/Python3.8 execution
nor any hardware environment is validated by this result.
The Windows inventory CLI smoke produced an inventory-only report with Linux
probes marked not_applicable. Current documentation checks passed for 28
project Markdown files and 111 internal file links (excluding third-party
documentation); evidence: artifacts/2026-10-16-doc-check.json.

## Agent workflow and handoff preparation

- docs/agent-onboarding.md provides task-specific reading and invariants.
- docs/ai-development-workflow.md recommends one first-slice implementation
  task, then separate tasks when shared contracts and boundaries are stable.
- plans/templates/ provides task/checkpoint and validation-report templates.
- Root AGENTS.md links this entry point and requires explicit coordination
  for shared contracts and global status when parallel work is requested.
- The original workflow preparation created no chats, agents, worktrees,
  commits or remote connections. M1 was subsequently implemented in this chat.
- Documentation verification after preparation: 20 Markdown files and 49
  internal links, fences, UTF-8 replacement characters and architecture/status
  versions checked with zero issues. See plans/2026-10-11-agent-workflow.md.

## Acceptance scenarios, in user priority order

| ID | Target combination | Target OS | Project evidence |
|---|---|---|---|
| A4-S | Static dual Piper + grippers + dual wrist D435 + fixed D435/D435i/D455 + PICO primary / Quest 3 fallback | Ubuntu 24.04 | PICO input + three RGB + receive-only joint feedback tested; teleop/episode pending |
| A1 | FR3 + D405 wrist + D435 third-person + GELLO / phone WebXR | Ubuntu 22.04 | not_validated |
| A2 | Piper + CamBot + arm-mounted D435i + Quest 3 WebXR | Ubuntu 20.04 | not_validated |
| A3 | MuJoCo fixed arm asset + Quest 3 / optional phone WebXR | Windows / Ubuntu 20.04 / 22.04 | not_validated |
| A4 | Dual Piper + custom wheeled base + fixed head D435 + Quest 3 WebXR | Ubuntu 24.04 | not_validated |
| A5 | XLeRobot + Quest 3 | unknown | not_validated |
| A6 | Unitree G1-D, exact product/configuration to confirm | unknown | not_validated |

A4-S is a subset branch, not a renumbering or proof of full A4. Physical
priority is A4-S → A1 → A2, then remaining scenarios as resources allow.
Each fixed-camera model and VR route is an independently validated profile.
See docs/validation/a4s-a1-a2-playbook.md for the staged field procedure.

Do not substitute D435i for A1/A4's D435 or a ZED camera for A2's D435i.
GELLO and phone are separate acceptance branches; native iOS input does not
prove the requested WebXR branch. CamBot's upstream Ubuntu 24.04/Python 3.12+
and ZED Mini setup does not prove the A2 environment.

## Inference implementation order

1. Artifact validation, offline replay, stub/native synchronous scheduling.
2. Simulation/shadow, observation age and latency reports, device-local queue.
3. Async scheduling and optional IK/joint trajectory profiles.
4. TE or RTC when the adapter's action space/sampler supports it; compare
   rather than enabling every method at once.
5. Task-level planning and MPC only when task/model evidence justifies them.

RTC is not a generic smoothing switch. IK/planning/MPC are motion components,
not substitutes for ownership or final safety checks.

## Development and validation environments

- Windows: core development/fake/replay and optional simulation only.
- FR3 Ubuntu 22.04, Piper Ubuntu 20.04 and dual-Piper Ubuntu 24.04:
  independent host, SDK, firmware, calibration and stop-behavior profiles.
- Separate GPU inference host where useful; no hardware write authority.
- Recommended workflow: Codex SSH remote project with an eligible chat handoff;
  fallback: remote Codex CLI plus versioned project handoff documents.
- This chat still executes its tools locally; system SSH now reaches
  ranger-piper for read-only inventory. A registered desktop remote project,
  remote Codex setup remains pending; a local Git baseline exists.
- See docs/development-and-validation.md for the development loop and evidence
  requirements. Physical testing always requires an explicit user request.

## Design and implementation documentation

- plans/2026-10-11-architecture-research.md
- docs/research/2026-10-11-teleop-inference.md
- docs/development-and-validation.md
- docs/adr/0001-host-and-transport-boundaries.md
- docs/adr/0002-policy-scheduling-and-motion.md
- docs/adr/0003-gui-as-graph-client.md
- plans/2026-10-11-workflow-positioning.md
- docs/research/2026-10-11-workflow-positioning.md
- docs/positioning.md
- docs/adr/0004-experiment-loop-and-quickstart.md
- docs/adr/0005-m1-fake-contract-and-evidence.md
- docs/m1-review.md
- docs/validation/2026-10-15-m1-windows.md
- docs/reference-repositories.md
- plans/002-a4s-teleop-acquisition.md
- docs/validation/a4s-a1-a2-playbook.md
- docs/adr/0006-a4-static-subset-and-incremental-validation.md
- plans/2026-10-16-reference-and-bench-validation.md
- plans/003-remote-audit-discovery-and-release.md
- docs/remote-code-index.md
- docs/device-discovery.md
- docs/release-and-deployment.md
- docs/adr/0007-discovery-and-explicit-device-binding.md
- docs/validation/2026-10-16-discovery-and-audit.md

Research used primary GitHub repositories, arXiv papers and official docs.
Tavily CLI could not start, so direct primary-source browsing was used.
No upstream project was built or benchmarked locally. Architecture section 11
remains historical; the workflow study separately rechecked the current
PhyAgentOS README (declares v1.1.0) and distinguishes the older introduction
document. No upstream hardware support was inferred for this project.

The v0.4 documentation verification passed for 10 Markdown files and 14
internal file links. The v0.5 check passed for 14 Markdown files and 28
internal file links, balanced fences, UTF-8 replacement characters,
architecture/status versions and A1–A6 presence, with zero issues.
Those checks describe the earlier documentation revisions. M1 now has actual
unit, integration and configuration validation tests with the results above.
Those earlier checks did not validate physical support or quickstart time;
limited later observation evidence is listed in Current phase.

## Open decisions

- Broader Python/OS compatibility beyond the tested Windows/Python3.11.12;
  M1 packaging and JSON Schema subset are implemented.
- Concrete transport libraries/serialization and adapter compatibility matrix.
- Process supervision mechanism.
- Extension beyond M1's versioned JSON event schema, streaming/durability and
  broader data/profile schemas.
- Full PolicyArtifact/port/graph schemas: historical v0.2 examples are not
  runnable; 0.3.0-m1 is a strict experimental subset, not full v0.3 support.
- First policy/weights, GPU and task-specific latency/action-age budgets.
- Phone OS/browser/tracking capability; CamBot migration and display profile.
- PICO sustained input timing/tracking/reset failure behavior; device settings
  confirmation beyond browser UA. A4-S firmware, mounting/TCP/extrinsics, task,
  motion/stop beyond the bounded arm-only slice. SDK0.6.1/ROS Jazzy input/RGB/feedback
  and scoped position teleop are evidenced; full-feature teleop/raw episodes remain pending.
- Exact wheeled-base kinematics, XLeRobot configuration and G1-D identity.
- Physical admission thresholds and independently reproducible evidence.
- Task/EvalSpec and QC/RunReport schema details, task/profile quality gates,
  quickstart measurement protocols and reference-workflow comparative evidence.
