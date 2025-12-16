"""
Weapons Modes Module
"""

from .pneumatic import PneumaticMode
from .co2_silent import CO2SilentMode
from .electric import ElectricMode

__all__ = ["PneumaticMode", "CO2SilentMode", "ElectricMode"]
