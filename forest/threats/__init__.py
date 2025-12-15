"""
forest/threats/__init__.py
Threats module initialization.
"""

from .base import BaseThreat, ThreatType, ThreatSeverity
from .crow import Crow
from .magpie import Magpie
from .squirrel import Squirrel
from .snake import Snake
from .parasite import Parasite
from .bat import Bat
from .detector import ThreatDetector

__all__ = [
    'BaseThreat',
    'ThreatType',
    'ThreatSeverity',
    'Crow',
    'Magpie',
    'Squirrel',
    'Snake',
    'Parasite',
    'Bat',
    'ThreatDetector'
]
