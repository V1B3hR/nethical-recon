"""Learning submodule"""

from .baseline import BaselineLearner
from .anomaly_ml import SimpleMLAnomalyDetector

__all__ = [
    "BaselineLearner",
    "SimpleMLAnomalyDetector",
]
