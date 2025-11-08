"""
Machine Learning classification engine for Data Destroyer.

This package provides ML-powered classification capabilities that complement
the existing regex-based patterns with context-aware entity recognition.
"""

from .engine import HybridClassificationEngine
from .entities import Entity, ClassificationResult

__all__ = [
    "HybridClassificationEngine",
    "Entity",
    "ClassificationResult",
]
