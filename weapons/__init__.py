"""
Weapons Module - Silent Marker System
FALA 5: Broń Markerowa (Silent Marker)

Arsenal Cichego Myśliwego:
"Cichy, z tłumikiem, naboje tracer - raz trafiony, zawsze widoczny"
"""

from .marker_gun import MarkerGun, WeaponMode
from .targeting import TargetingSystem, Target
from .fire_control import FireControlSystem, FireResult

# Weapon Modes
from .modes.pneumatic import PneumaticMode
from .modes.co2_silent import CO2SilentMode
from .modes.electric import ElectricMode

# Tracer Ammunition
from .ammo.tracer_red import RedTracer
from .ammo.tracer_purple import PurpleTracer
from .ammo.tracer_orange import OrangeTracer
from .ammo.tracer_yellow import YellowTracer
from .ammo.tracer_blue import BlueTracer
from .ammo.tracer_white import WhiteTracer
from .ammo.tracer_black import BlackTracer
from .ammo.tracer_brown import BrownTracer

__all__ = [
    "MarkerGun",
    "WeaponMode",
    "TargetingSystem",
    "Target",
    "FireControlSystem",
    "FireResult",
    "PneumaticMode",
    "CO2SilentMode",
    "ElectricMode",
    "RedTracer",
    "PurpleTracer",
    "OrangeTracer",
    "YellowTracer",
    "BlueTracer",
    "WhiteTracer",
    "BlackTracer",
    "BrownTracer",
]

__version__ = "1.0.0"
__author__ = "V1B3hR"
