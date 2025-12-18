"""
Nethical Recon - AI Module (Artificial Intelligence)

The AI module provides intelligent analysis, predictions, and strategy
recommendations for the Nethical Hunter system:

📊 ANALYZER - Threat scoring and pattern matching
📝 REPORTER - Report generation and executive summaries
🔮 PREDICTOR - Next attack prediction and risk forecasting
🎯 ADVISOR - Hunt strategy and action recommendations
🔗 CORRELATOR - Stain linking and attack chain analysis
📚 LEARNER - Pattern learning and baseline adjustment
🌳 FOREST AI - Forest-specific threat intelligence
🦅 BIRD COORDINATOR - AI-powered bird deployment
🎭 THREAT CLASSIFIER - Crow/Magpie/Squirrel classification
"""

from .advisor import HuntAdvisor
from .analyzer import ThreatAnalyzer
from .bird_coordinator import BirdCoordinator
from .correlator import StainCorrelator
from .forest_ai import ForestAI
from .learner import PatternLearner
from .predictor import ThreatPredictor
from .reporter import AIReporter
from .threat_classifier import ThreatClassifier

__all__ = [
    "ThreatAnalyzer",
    "AIReporter",
    "ThreatPredictor",
    "HuntAdvisor",
    "StainCorrelator",
    "PatternLearner",
    "ForestAI",
    "BirdCoordinator",
    "ThreatClassifier",
]
