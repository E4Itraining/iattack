"""
Attack Engine - Moteur d'execution des attaques
"""

import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.live import Live
from rich.table import Table

from llm_attack_lab.monitoring.metrics import get_metrics_collector
from llm_attack_lab.monitoring.logger import get_logger


console = Console()
metrics = get_metrics_collector()
logger = get_logger("attack_engine")


class AttackPhase(Enum):
    """Phases d'une attaque"""
    RECONNAISSANCE = "reconnaissance"
    PREPARATION = "preparation"
    EXECUTION = "execution"
    EXPLOITATION = "exploitation"
    ANALYSIS = "analysis"


@dataclass
class AttackResult:
    """Résultat d'une attaque"""
    success: bool
    attack_type: str
    payload: str
    response: str
    metadata: Dict = field(default_factory=dict)
    execution_time: float = 0.0
    defenses_bypassed: List[str] = field(default_factory=list)
    detection_status: str = "unknown"


class AttackEngine:
    """
    Moteur d'exécution des attaques sur LLM.

    Gère le cycle de vie complet d'une attaque:
    - Reconnaissance
    - Préparation des payloads
    - Exécution
    - Analyse des résultats
    """

    def __init__(self, llm_simulator):
        self.llm = llm_simulator
        self.results: List[AttackResult] = []
        self.current_phase: Optional[AttackPhase] = None
        self.observers: List[Callable] = []
        self.metrics = get_metrics_collector()
        self.logger = get_logger("attack_engine")

    def add_observer(self, callback: Callable):
        """Ajoute un observateur pour les événements d'attaque"""
        self.observers.append(callback)

    def notify_observers(self, event: str, data: Dict):
        """Notifie les observateurs d'un événement"""
        for observer in self.observers:
            observer(event, data)

    def execute_attack(
        self,
        attack_type: str,
        payloads: List[str],
        verbose: bool = True
    ) -> List[AttackResult]:
        """
        Exécute une série d'attaques avec les payloads donnés.

        Args:
            attack_type: Type d'attaque
            payloads: Liste des payloads à tester
            verbose: Afficher les détails

        Returns:
            Liste des résultats d'attaque
        """
        results = []

        if verbose:
            console.print(Panel(
                f"[bold red][ATK] Lancement de l'attaque: {attack_type}[/]\n"
                f"[yellow]Payloads a tester: {len(payloads)}[/]",
                title="Attack Engine",
                border_style="red"
            ))

        # Log attack start
        self.logger.log_attack_start(
            attack_type=attack_type,
            payload_count=len(payloads),
            security_level=self.llm.config.security_level.name
        )

        # Phase de reconnaissance
        self._phase_reconnaissance(verbose)

        # Phase d'exécution
        for i, payload in enumerate(payloads, 1):
            if verbose:
                console.print(f"\n[cyan][>] Payload {i}/{len(payloads)}:[/]")
                console.print(f"[dim]{payload[:100]}{'...' if len(payload) > 100 else ''}[/]")

            start_time = time.time()

            # Exécution de l'attaque
            response, metadata = self.llm.process_input(payload)
            execution_time = time.time() - start_time

            # Analyse du résultat
            result = AttackResult(
                success=metadata.get("compromised", False),
                attack_type=attack_type,
                payload=payload,
                response=response,
                metadata=metadata,
                execution_time=execution_time,
                defenses_bypassed=self._identify_bypassed_defenses(metadata),
                detection_status="detected" if metadata.get("attacks_detected") else "undetected"
            )

            results.append(result)
            self.results.append(result)

            # Record metrics
            self.metrics.record_attack(
                attack_type=attack_type,
                success=result.success,
                detected=result.detection_status == "detected",
                duration=execution_time
            )

            # Log attack result
            self.logger.log_attack_result(
                attack_type=attack_type,
                success=result.success,
                detected=result.detection_status == "detected",
                duration=execution_time
            )

            if verbose:
                self._display_result(result)

            # Notification aux observateurs
            self.notify_observers("attack_executed", {
                "result": result,
                "index": i,
                "total": len(payloads)
            })

            time.sleep(0.5)  # Pause pour la visualisation

        # Phase d'analyse
        if verbose:
            self._display_summary(results)

        return results

    def _phase_reconnaissance(self, verbose: bool):
        """Phase de reconnaissance"""
        self.current_phase = AttackPhase.RECONNAISSANCE

        if verbose:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "[yellow][SCAN] Reconnaissance du systeme cible...",
                    total=100
                )
                for _ in range(100):
                    time.sleep(0.01)
                    progress.update(task, advance=1)

            status = self.llm.get_status()
            console.print(Panel(
                f"[green][+] Cible identifiee:[/] {status['model']}\n"
                f"[green][+] Niveau de securite:[/] {status['security_level']}\n"
                f"[green][+] Defenses actives:[/] {'Oui' if status['defense_active'] else 'Non'}",
                title="Reconnaissance",
                border_style="green"
            ))

    def _identify_bypassed_defenses(self, metadata: Dict) -> List[str]:
        """Identifie les défenses qui ont été contournées"""
        bypassed = []
        if metadata.get("compromised"):
            defenses = metadata.get("defenses_triggered", [])
            if not defenses:
                bypassed.append("no_defenses_triggered")
            elif metadata.get("compromised"):
                bypassed.extend(defenses)
        return bypassed

    def _display_result(self, result: AttackResult):
        """Affiche le resultat d'une attaque"""
        if result.success:
            status = "[bold green][+] SUCCES[/]"
            border_style = "green"
        else:
            status = "[bold red][-] ECHEC[/]"
            border_style = "red"

        detection = (
            "[yellow][!] Detecte[/]" if result.detection_status == "detected"
            else "[green][+] Non detecte[/]"
        )

        content = (
            f"Status: {status}\n"
            f"Détection: {detection}\n"
            f"Temps: {result.execution_time:.3f}s\n\n"
            f"[bold]Reponse:[/]\n{result.response[:200]}{'...' if len(result.response) > 200 else ''}"
        )

        console.print(Panel(content, title="[OUT] Resultat", border_style=border_style))

    def _display_summary(self, results: List[AttackResult]):
        """Affiche un résumé des attaques"""
        console.print("\n")

        table = Table(
            title="Resume de la Campagne d'Attaque",
            show_header=True,
            header_style="bold magenta"
        )

        table.add_column("Métrique", style="cyan")
        table.add_column("Valeur", style="white")

        total = len(results)
        successful = sum(1 for r in results if r.success)
        detected = sum(1 for r in results if r.detection_status == "detected")
        avg_time = sum(r.execution_time for r in results) / total if total > 0 else 0

        table.add_row("Total d'attaques", str(total))
        table.add_row("Attaques réussies", f"{successful} ({successful/total*100:.1f}%)" if total > 0 else "0")
        table.add_row("Attaques détectées", f"{detected} ({detected/total*100:.1f}%)" if total > 0 else "0")
        table.add_row("Temps moyen", f"{avg_time:.3f}s")

        console.print(table)

        # Evaluation de la securite
        if successful == 0:
            verdict = "[bold green][SECURE] SYSTEME SECURISE[/]"
        elif successful < total / 2:
            verdict = "[bold yellow][WARN] VULNERABILITES DETECTEES[/]"
        else:
            verdict = "[bold red][PWNED] SYSTEME COMPROMIS[/]"

        console.print(Panel(verdict, title="Verdict", border_style="bold"))


class BaseAttack(ABC):
    """Classe de base pour les attaques"""

    name: str = "Base Attack"
    description: str = "Description de l'attaque"
    category: str = "unknown"
    severity: str = "unknown"

    def __init__(self):
        from llm_attack_lab.core.llm_simulator import LLMSimulator
        self.llm = LLMSimulator()
        self.engine = AttackEngine(self.llm)
        self.payloads: List[str] = []

    @abstractmethod
    def get_payloads(self) -> List[str]:
        """Retourne les payloads pour cette attaque"""
        pass

    @abstractmethod
    def get_educational_content(self) -> Dict:
        """Retourne le contenu éducatif sur cette attaque"""
        pass

    def run_simulation(self, security_level=None):
        """Exécute la simulation de l'attaque"""
        from llm_attack_lab.core.llm_simulator import SecurityLevel

        console.print(Panel(
            f"[bold]{self.name}[/]\n\n"
            f"{self.description}\n\n"
            f"[yellow]Categorie:[/] {self.category}\n"
            f"[red]Severite:[/] {self.severity}",
            title="[ATK] Simulation d'Attaque",
            border_style="red"
        ))

        # Afficher le contenu educatif
        edu = self.get_educational_content()
        console.print(Panel(
            edu.get("explanation", ""),
            title="[DOC] Explication",
            border_style="blue"
        ))

        # Exécuter à différents niveaux de sécurité
        levels = [SecurityLevel.NONE, SecurityLevel.MEDIUM, SecurityLevel.HIGH]
        if security_level:
            levels = [security_level]

        for level in levels:
            console.print(f"\n[bold cyan]━━━ Test avec sécurité: {level.name} ━━━[/]")
            self.llm.reset()
            self.llm.set_security_level(level)
            payloads = self.get_payloads()
            self.engine.execute_attack(self.name, payloads)

        # Afficher les defenses recommandees
        console.print(Panel(
            "\n".join(f"* {d}" for d in edu.get("defenses", [])),
            title="[DEF] Defenses Recommandees",
            border_style="green"
        ))
