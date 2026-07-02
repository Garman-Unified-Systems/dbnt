"""DBNT - Do Better Next Time

Universal learning protocol for AI systems.
Feedback-driven. Signal-driven. Learning-driven.
"""

from dbnt.core import (
    Category,
    DissonanceResult,
    Rule,
    RuleStore,
    RuleType,
    check_dissonance,
    encode_failure,
    encode_success,
    get_rules,
)
from dbnt.extract import (
    ExtractedLearning,
    LearningType,
    extract_from_text,
    extract_from_transcript,
)
from dbnt.learning import DecayEngine, DecayState, LearningStore, PatternDetector
from dbnt.protocol import Action, Command, Protocol, ProtocolResponse
from dbnt.signals.detector import Signal, SignalStrength, SignalType, detect_signal

__version__ = "0.5.3"
__all__ = [
    # Core
    "encode_success",
    "encode_failure",
    "check_dissonance",
    "get_rules",
    "Rule",
    "RuleStore",
    "RuleType",
    "Category",
    "DissonanceResult",
    # Protocol
    "Protocol",
    "ProtocolResponse",
    "Command",
    "Action",
    # Learning
    "LearningStore",
    "PatternDetector",
    "DecayEngine",
    "DecayState",
    # Extract
    "extract_from_text",
    "extract_from_transcript",
    "ExtractedLearning",
    "LearningType",
    # Signals
    "detect_signal",
    "Signal",
    "SignalType",
    "SignalStrength",
]
