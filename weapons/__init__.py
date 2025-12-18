"""
Weapons Module - Silent Marker System
FALA 5: Broń Markerowa (Silent Marker)

Arsenal Cichego Myśliwego:
"Cichy, z tłumikiem, naboje tracer - raz trafiony, zawsze widoczny"
"""

from .ammo.tracer_black import BlackTracer
from .ammo.tracer_blue import BlueTracer
from .ammo.tracer_brown import BrownTracer
from .ammo.tracer_orange import OrangeTracer
from .ammo.tracer_purple import PurpleTracer

# Tracer Ammunition
from .ammo.tracer_red import RedTracer
from .ammo.tracer_white import WhiteTracer
from .ammo.tracer_yellow import YellowTracer
from .fire_control import FireControlSystem, FireResult
from .marker_gun import MarkerGun, WeaponMode
from .modes.co2_silent import CO2SilentMode
from .modes.electric import ElectricMode

# Weapon Modes
from .modes.pneumatic import PneumaticMode
from .targeting import Target, TargetingSystem

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
