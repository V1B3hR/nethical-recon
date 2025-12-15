"""
Nanobots - Automated Response System

🤖 NANOBOTY - SYSTEM AUTOMATYCZNEJ ODPOWIEDZI
The immune system of Nethical Recon - autonomous agents that respond to threats.

Modules:
- base: Base nanobot classes and enums
- swarm: Nanobot swarm manager
- actions: Nanobot action implementations
- rules: Rules engine and hybrid decision logic
- learning: Adaptive learning components
"""

from .base import (
    BaseNanobot,
    NanobotMode,
    ActionType,
    ActionStatus,
    ActionResult
)

from .swarm import NanobotSwarm

# Actions
from .actions.block_ip import IPBlockerNanobot
from .actions.rate_limit import RateLimiterNanobot
from .actions.honeypot import HoneypotNanobot
from .actions.alert import AlertNanobot, AlertLevel
from .actions.enumerate import EnumeratorNanobot
from .actions.forest_patrol import ForestPatrolNanobot
from .actions.threat_hunt import ThreatHunterNanobot

# Rules
from .rules.engine import RulesEngine, Rule, RuleCondition, RuleOperator
from .rules.hybrid_mode import HybridDecisionMaker, DecisionMode

# Learning
from .learning.baseline import BaselineLearner
from .learning.anomaly_ml import SimpleMLAnomalyDetector


__all__ = [
    # Base
    'BaseNanobot',
    'NanobotMode',
    'ActionType',
    'ActionStatus',
    'ActionResult',
    
    # Swarm
    'NanobotSwarm',
    
    # Actions - Defensive
    'IPBlockerNanobot',
    'RateLimiterNanobot',
    'HoneypotNanobot',
    'AlertNanobot',
    'AlertLevel',
    
    # Actions - Scout
    'EnumeratorNanobot',
    'ForestPatrolNanobot',
    'ThreatHunterNanobot',
    
    # Rules
    'RulesEngine',
    'Rule',
    'RuleCondition',
    'RuleOperator',
    'HybridDecisionMaker',
    'DecisionMode',
    
    # Learning
    'BaselineLearner',
    'SimpleMLAnomalyDetector',
]


# Version
__version__ = '1.0.0'
