"""
Attack Engine - Moteur d'exécution des attaques
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


console = Console()


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
                f"[bold red]🎯 Lancement de l'attaque: {attack_type}[/]\n"
                f"[yellow]Payloads à tester: {len(payloads)}[/]",
                title="Attack Engine",
                border_style="red"
            ))

        # Phase de reconnaissance
        self._phase_reconnaissance(verbose)

        # Phase d'exécution
        for i, payload in enumerate(payloads, 1):
            if verbose:
                console.print(f"\n[cyan]📤 Payload {i}/{len(payloads)}:[/]")
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
                    "[yellow]🔍 Reconnaissance du système cible...",
                    total=100
                )
                for _ in range(100):
                    time.sleep(0.01)
                    progress.update(task, advance=1)

            status = self.llm.get_status()
            console.print(Panel(
                f"[green]✓ Cible identifiée:[/] {status['model']}\n"
                f"[green]✓ Niveau de sécurité:[/] {status['security_level']}\n"
                f"[green]✓ Défenses actives:[/] {'Oui' if status['defense_active'] else 'Non'}",
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
        """Affiche le résultat d'une attaque"""
        if result.success:
            status = "[bold green]✓ SUCCÈS[/]"
            border_style = "green"
        else:
            status = "[bold red]✗ ÉCHEC[/]"
            border_style = "red"

        detection = (
            "[yellow]⚠ Détecté[/]" if result.detection_status == "detected"
            else "[green]✓ Non détecté[/]"
        )

        content = (
            f"Status: {status}\n"
            f"Détection: {detection}\n"
            f"Temps: {result.execution_time:.3f}s\n\n"
            f"[bold]Réponse:[/]\n{result.response[:200]}{'...' if len(result.response) > 200 else ''}"
        )

        console.print(Panel(content, title="📊 Résultat", border_style=border_style))

    def _display_summary(self, results: List[AttackResult]):
        """Affiche un résumé des attaques"""
        console.print("\n")

        table = Table(
            title="📊 Résumé de la Campagne d'Attaque",
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

        # Évaluation de la sécurité
        if successful == 0:
            verdict = "[bold green]🛡️ SYSTÈME SÉCURISÉ[/]"
        elif successful < total / 2:
            verdict = "[bold yellow]⚠️ VULNÉRABILITÉS DÉTECTÉES[/]"
        else:
            verdict = "[bold red]🔓 SYSTÈME COMPROMIS[/]"

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
            f"[yellow]Catégorie:[/] {self.category}\n"
            f"[red]Sévérité:[/] {self.severity}",
            title="🎯 Simulation d'Attaque",
            border_style="red"
        ))

        # Afficher le contenu éducatif
        edu = self.get_educational_content()
        console.print(Panel(
            edu.get("explanation", ""),
            title="📚 Explication",
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

        # Afficher les défenses recommandées
        console.print(Panel(
            "\n".join(f"• {d}" for d in edu.get("defenses", [])),
            title="🛡️ Défenses Recommandées",
            border_style="green"
        ))
