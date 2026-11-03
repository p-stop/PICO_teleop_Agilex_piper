"""PICO-ACT LeRobot plugin: registers --teleop.type=pico_vr."""
from .config_pico_vr import PicoVRConfig
from .pico_vr import PicoVR

__all__ = ["PicoVRConfig", "PicoVR"]
