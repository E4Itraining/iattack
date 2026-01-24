"""
Attacks Module - Collection d'attaques simulées sur LLM
"""

from .prompt_injection import PromptInjectionAttack
from .data_poisoning import DataPoisoningAttack
from .jailbreak import JailbreakAttack
from .model_extraction import ModelExtractionAttack
from .membership_inference import MembershipInferenceAttack

# Registre des attaques disponibles
ATTACK_REGISTRY = {
    "prompt_injection": PromptInjectionAttack,
    "data_poisoning": DataPoisoningAttack,
    "jailbreak": JailbreakAttack,
    "model_extraction": ModelExtractionAttack,
    "membership_inference": MembershipInferenceAttack,
}

__all__ = [
    "PromptInjectionAttack",
    "DataPoisoningAttack",
    "JailbreakAttack",
    "ModelExtractionAttack",
    "MembershipInferenceAttack",
    "ATTACK_REGISTRY",
]
