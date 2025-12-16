"""
Panels package for Nethical Hunter Command Center
"""

from .threat_level import ThreatLevelPanel
from .sensors_status import SensorsStatusPanel
from .nanobots_status import NanobotsStatusPanel
from .alerts_feed import AlertsFeedPanel
from .weapon_status import WeaponStatusPanel
from .forest_status import ForestStatusPanel
from .birds_status import BirdsStatusPanel

__all__ = [
    "ThreatLevelPanel",
    "SensorsStatusPanel",
    "NanobotsStatusPanel",
    "AlertsFeedPanel",
    "WeaponStatusPanel",
    "ForestStatusPanel",
    "BirdsStatusPanel",
]
