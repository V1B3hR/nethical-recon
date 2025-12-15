"""
forest/__init__.py
Forest module initialization - Infrastructure mapping as trees.

The Forest module maps infrastructure hierarchically:
- Forest: Entire infrastructure
- Trees: Hosts/servers
- Trunks: OS/kernel
- Crowns: Overview/monitoring
- Branches: Processes/services/connections
- Leaves: Threads/sessions/packets

Threats in the canopy:
- Crows: Malware
- Magpies: Data stealers
- Squirrels: Lateral movement
- Snakes: Rootkits
- Parasites: Cryptominers
- Bats: Night attacks
"""

from .base import ForestBase, ForestComponent, ComponentStatus
from .manager import ForestManager
from .health_check import HealthChecker

# Import tree components
from .trees import (
    Tree,
    Trunk,
    Branch,
    BranchType,
    Leaf,
    LeafType,
    Crown,
    ForestMap
)

# Import threat components
from .threats import (
    BaseThreat,
    ThreatType,
    ThreatSeverity,
    Crow,
    Magpie,
    Squirrel,
    Snake,
    Parasite,
    Bat,
    ThreatDetector
)

__all__ = [
    # Base classes
    'ForestBase',
    'ForestComponent',
    'ComponentStatus',
    
    # Management
    'ForestManager',
    'HealthChecker',
    
    # Tree components
    'Tree',
    'Trunk',
    'Branch',
    'BranchType',
    'Leaf',
    'LeafType',
    'Crown',
    'ForestMap',
    
    # Threat components
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
