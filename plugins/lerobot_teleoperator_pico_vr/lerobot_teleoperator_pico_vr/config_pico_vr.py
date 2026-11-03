from dataclasses import dataclass

from lerobot.teleoperators.config import TeleoperatorConfig

PICO_ROOT = "/home/ros/zero-wam/PICO-ACT"


@TeleoperatorConfig.register_subclass("pico_vr")
@dataclass
class PicoVRConfig(TeleoperatorConfig):
    """PICO headset through the 023 VR page and teleop session, as a LeRobot teleoperator.

    Defaults use the PICO-ACT collection profile: same page, certificate, ports, buttons,
    filters, IK and gripper mode as 023 collect.
    """
    pico_root: str = PICO_ROOT
    deployment: str = PICO_ROOT + "/profiles/collection/deployment.json"
    robot_infra_src: str = PICO_ROOT + "/releases/023-20261103-webrtc-smoothing/src"
    output_root: str = PICO_ROOT + "/runs"
    # "ros": feedback and camera previews from the ROS topics of the running robot stack.
    # "fake": no ROS; simulated arms follow this teleop's own output, gray camera frames.
    backend: str = "ros"
    # HTTPS page (and WebRTC offer) address. None: deployment.json host/port (0.0.0.0:8445).
    host: str | None = None
    port: int | None = None
    advertise_host: str | None = None
    # Camera panels in the headset. False: no camera subscriptions (and no camera self-check).
    cameras_enabled: bool = True
    # Refuse to start when another collect/driver/camera stack is running.
    check_conflicts: bool = True
    # First get_action() waits this long for fresh arm feedback (the robot connects after the teleop).
    first_feedback_timeout_s: float = 10.0
    # Override teleop_filter.input_delay_s (interpolation (a)); None keeps the profile value.
    input_delay_s: float | None = None
