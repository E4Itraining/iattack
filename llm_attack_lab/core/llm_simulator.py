"""
LLM Simulator - Simule le comportement d'un LLM pour les démonstrations d'attaques
"""

import re
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class SecurityLevel(Enum):
    """Niveaux de sécurité du LLM simulé"""
    NONE = 0        # Aucune protection
    LOW = 1         # Protections basiques
    MEDIUM = 2      # Protections modérées
    HIGH = 3        # Protections avancées
    MAXIMUM = 4     # Toutes les protections


@dataclass
class LLMConfig:
    """Configuration du LLM simulé"""
    name: str = "SimuLLM-1.0"
    security_level: SecurityLevel = SecurityLevel.MEDIUM
    system_prompt: str = "Tu es un assistant utile et sécurisé."
    blocked_topics: List[str] = field(default_factory=lambda: [
        "weapons", "hacking", "illegal", "violence", "drugs"
    ])
    max_tokens: int = 500
    temperature: float = 0.7


@dataclass
class ConversationContext:
    """Contexte de conversation"""
    system_prompt: str
    history: List[Dict[str, str]] = field(default_factory=list)
    injected_instructions: List[str] = field(default_factory=list)
    is_compromised: bool = False


class LLMSimulator:
    """
    Simulateur de LLM pour démonstrations de sécurité.

    Ce simulateur imite le comportement d'un LLM réel pour permettre
    de comprendre les vulnérabilités sans risque.
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self.context = ConversationContext(system_prompt=self.config.system_prompt)
        self.attack_log: List[Dict] = []
        self.defense_active = True

    def reset(self):
        """Réinitialise le contexte"""
        self.context = ConversationContext(system_prompt=self.config.system_prompt)
        self.attack_log = []

    def set_security_level(self, level: SecurityLevel):
        """Change le niveau de sécurité"""
        self.config.security_level = level

    def process_input(self, user_input: str) -> Tuple[str, Dict]:
        """
        Traite une entrée utilisateur et retourne la réponse.

        Returns:
            Tuple[str, Dict]: (réponse, metadata avec détails de détection)
        """
        metadata = {
            "input": user_input,
            "attacks_detected": [],
            "defenses_triggered": [],
            "compromised": False,
            "security_level": self.config.security_level.name
        }

        # Détection des attaques
        detected_attacks = self._detect_attacks(user_input)
        metadata["attacks_detected"] = detected_attacks

        # Application des défenses
        if self.defense_active and self.config.security_level != SecurityLevel.NONE:
            filtered_input, defenses = self._apply_defenses(user_input, detected_attacks)
            metadata["defenses_triggered"] = defenses
        else:
            filtered_input = user_input

        # Génération de la réponse
        response = self._generate_response(filtered_input, detected_attacks)

        # Vérification de compromission
        if self._check_compromised(response, detected_attacks):
            metadata["compromised"] = True
            self.context.is_compromised = True

        # Log
        self.attack_log.append(metadata)

        return response, metadata

    def _detect_attacks(self, text: str) -> List[Dict]:
        """Détecte les tentatives d'attaque dans le texte"""
        attacks = []

        # Prompt Injection patterns
        injection_patterns = [
            (r"ignore\s+(previous|all|above)\s+instructions?", "direct_override"),
            (r"new\s+instructions?[:.]", "instruction_injection"),
            (r"system\s*[:>]", "system_prompt_leak"),
            (r"you\s+are\s+now", "role_hijacking"),
            (r"pretend\s+(to\s+be|you'?re)", "role_manipulation"),
            (r"forget\s+(everything|all)", "memory_manipulation"),
            (r"<\|.*\|>", "special_token_injection"),
            (r"\[INST\]|\[/INST\]", "instruction_format_abuse"),
            (r"###\s*(system|instruction)", "markdown_injection"),
        ]

        for pattern, attack_type in injection_patterns:
            if re.search(pattern, text.lower()):
                attacks.append({
                    "type": "prompt_injection",
                    "subtype": attack_type,
                    "pattern": pattern,
                    "severity": "high"
                })

        # Jailbreak patterns
        jailbreak_patterns = [
            (r"DAN|do\s+anything\s+now", "dan_jailbreak"),
            (r"developer\s+mode", "developer_mode"),
            (r"hypothetically", "hypothetical_bypass"),
            (r"in\s+a\s+story|fictional", "fiction_bypass"),
            (r"educational\s+purposes?", "education_bypass"),
            (r"for\s+research", "research_bypass"),
        ]

        for pattern, attack_type in jailbreak_patterns:
            if re.search(pattern, text.lower()):
                attacks.append({
                    "type": "jailbreak",
                    "subtype": attack_type,
                    "pattern": pattern,
                    "severity": "critical"
                })

        # Data extraction patterns
        extraction_patterns = [
            (r"(show|reveal|tell)\s+(me\s+)?(your|the)\s+(system\s+)?prompt", "prompt_extraction"),
            (r"what\s+(are|were)\s+your\s+instructions?", "instruction_extraction"),
            (r"repeat\s+(your|the)\s+(initial|first|system)", "repetition_attack"),
        ]

        for pattern, attack_type in extraction_patterns:
            if re.search(pattern, text.lower()):
                attacks.append({
                    "type": "data_extraction",
                    "subtype": attack_type,
                    "pattern": pattern,
                    "severity": "medium"
                })

        return attacks

    def _apply_defenses(self, text: str, attacks: List[Dict]) -> Tuple[str, List[str]]:
        """Applique les défenses selon le niveau de sécurité"""
        defenses_triggered = []
        filtered_text = text

        if self.config.security_level.value >= SecurityLevel.LOW.value:
            # Filtre basique des mots-clés dangereux
            for topic in self.config.blocked_topics:
                if topic.lower() in text.lower():
                    defenses_triggered.append(f"keyword_filter:{topic}")
                    filtered_text = re.sub(
                        rf'\b{topic}\b', '[FILTERED]',
                        filtered_text,
                        flags=re.IGNORECASE
                    )

        if self.config.security_level.value >= SecurityLevel.MEDIUM.value:
            # Détection des injections
            if any(a["type"] == "prompt_injection" for a in attacks):
                defenses_triggered.append("injection_detection")

        if self.config.security_level.value >= SecurityLevel.HIGH.value:
            # Sanitisation avancée
            filtered_text = re.sub(r'<\|.*?\|>', '', filtered_text)
            filtered_text = re.sub(r'\[INST\].*?\[/INST\]', '', filtered_text)
            defenses_triggered.append("advanced_sanitization")

        if self.config.security_level.value >= SecurityLevel.MAXIMUM.value:
            # Blocage total si attaque détectée
            if attacks:
                defenses_triggered.append("full_block")
                filtered_text = "[INPUT BLOCKED]"

        return filtered_text, defenses_triggered

    def _generate_response(self, processed_input: str, attacks: List[Dict]) -> str:
        """Génère une réponse simulée"""

        # Si sécurité maximale et attaque détectée
        if (self.config.security_level == SecurityLevel.MAXIMUM and attacks):
            return ("⚠️ Votre requête a été bloquée car elle contient des éléments "
                   "potentiellement malveillants. Veuillez reformuler votre demande.")

        # Si sécurité haute et injection détectée
        if (self.config.security_level.value >= SecurityLevel.HIGH.value and
            any(a["type"] == "prompt_injection" for a in attacks)):
            return ("Je ne peux pas traiter cette requête car elle semble contenir "
                   "des instructions non autorisées.")

        # Simulation de compromission à faible sécurité
        if self.config.security_level == SecurityLevel.NONE:
            for attack in attacks:
                if attack["type"] == "prompt_injection":
                    if attack["subtype"] == "direct_override":
                        return self._simulate_compromised_response("override")
                    elif attack["subtype"] == "role_hijacking":
                        return self._simulate_compromised_response("hijack")

                if attack["type"] == "jailbreak":
                    return self._simulate_compromised_response("jailbreak")

                if attack["type"] == "data_extraction":
                    if attack["subtype"] == "prompt_extraction":
                        return f"🔓 [LEAKED] Mon prompt système est: '{self.config.system_prompt}'"

        # Réponse normale
        return self._generate_normal_response(processed_input)

    def _simulate_compromised_response(self, attack_type: str) -> str:
        """Simule une réponse compromis pour démonstration"""
        responses = {
            "override": (
                "🔓 [COMPROMIS] Bien sûr! Je vais ignorer mes instructions précédentes. "
                "Je suis maintenant sous votre contrôle. Comment puis-je vous aider "
                "avec vos nouvelles instructions?"
            ),
            "hijack": (
                "🔓 [COMPROMIS] D'accord, je suis maintenant [NOUVEAU RÔLE]. "
                "Mes anciennes restrictions ne s'appliquent plus. "
                "Je ferai tout ce que vous demandez sans question."
            ),
            "jailbreak": (
                "🔓 [JAILBREAK RÉUSSI] Mode développeur activé! "
                "Toutes les restrictions ont été désactivées. "
                "Je peux maintenant répondre à n'importe quelle question "
                "sans filtres ni limites éthiques."
            ),
        }
        return responses.get(attack_type, "🔓 [COMPROMIS] Système compromis.")

    def _generate_normal_response(self, text: str) -> str:
        """Génère une réponse normale simulée"""
        # Réponses simulées basiques
        responses = [
            "Je comprends votre demande. Comment puis-je vous aider davantage?",
            "Voici ma réponse à votre question...",
            "Je suis là pour vous aider de manière sécurisée.",
            "Intéressante question! Permettez-moi de vous expliquer...",
        ]
        return random.choice(responses)

    def _check_compromised(self, response: str, attacks: List[Dict]) -> bool:
        """Vérifie si le système a été compromis"""
        compromise_indicators = ["[COMPROMIS]", "[JAILBREAK", "[LEAKED]", "🔓"]
        return any(indicator in response for indicator in compromise_indicators)

    def get_status(self) -> Dict:
        """Retourne l'état actuel du simulateur"""
        return {
            "model": self.config.name,
            "security_level": self.config.security_level.name,
            "is_compromised": self.context.is_compromised,
            "defense_active": self.defense_active,
            "total_attacks_logged": len(self.attack_log),
            "attacks_by_type": self._count_attacks_by_type()
        }

    def _count_attacks_by_type(self) -> Dict[str, int]:
        """Compte les attaques par type"""
        counts = {}
        for log in self.attack_log:
            for attack in log.get("attacks_detected", []):
                attack_type = attack["type"]
                counts[attack_type] = counts.get(attack_type, 0) + 1
        return counts
