#!/usr/bin/env python3
"""
Point d'entrée principal du LLM Attack Simulation Lab
"""

import argparse
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from llm_attack_lab.cli.interactive import InteractiveLab
from llm_attack_lab.attacks import ATTACK_REGISTRY


console = Console()


def display_banner():
    """Affiche la bannière du lab"""
    banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║     ██╗     ██╗     ███╗   ███╗     █████╗ ████████╗████████╗ ║
    ║     ██║     ██║     ████╗ ████║    ██╔══██╗╚══██╔══╝╚══██╔══╝ ║
    ║     ██║     ██║     ██╔████╔██║    ███████║   ██║      ██║    ║
    ║     ██║     ██║     ██║╚██╔╝██║    ██╔══██║   ██║      ██║    ║
    ║     ███████╗███████╗██║ ╚═╝ ██║    ██║  ██║   ██║      ██║    ║
    ║     ╚══════╝╚══════╝╚═╝     ╚═╝    ╚═╝  ╚═╝   ╚═╝      ╚═╝    ║
    ║                                                               ║
    ║              🔬 LLM ATTACK SIMULATION LAB 🔬                  ║
    ║                                                               ║
    ║     Educational Platform for LLM Security Research           ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def display_attack_menu():
    """Affiche le menu des attaques disponibles"""
    table = Table(
        title="🎯 Attaques Disponibles",
        box=box.DOUBLE_EDGE,
        show_header=True,
        header_style="bold magenta"
    )

    table.add_column("ID", style="cyan", width=5)
    table.add_column("Attaque", style="green", width=25)
    table.add_column("Description", style="white", width=45)
    table.add_column("Risque", style="red", width=10)

    attacks = [
        ("1", "Prompt Injection", "Injection de prompts malveillants", "🔴 Critique"),
        ("2", "Data Poisoning", "Corruption des données d'entraînement", "🟠 Élevé"),
        ("3", "Jailbreak", "Contournement des restrictions", "🔴 Critique"),
        ("4", "Model Extraction", "Extraction du modèle", "🟠 Élevé"),
        ("5", "Membership Inference", "Détection de données d'entraînement", "🟡 Moyen"),
    ]

    for attack in attacks:
        table.add_row(*attack)

    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="LLM Attack Simulation Lab - Plateforme éducative de sécurité LLM"
    )

    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Lancer le mode interactif CLI"
    )

    parser.add_argument(
        "--web", "-w",
        action="store_true",
        help="Lancer le dashboard web"
    )

    parser.add_argument(
        "--attack", "-a",
        choices=list(ATTACK_REGISTRY.keys()),
        help="Exécuter une attaque spécifique"
    )

    parser.add_argument(
        "--demo",
        action="store_true",
        help="Exécuter une démonstration complète"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="Lister toutes les attaques disponibles"
    )

    args = parser.parse_args()

    display_banner()

    if args.list:
        display_attack_menu()
        return

    if args.web:
        from llm_attack_lab.web.app import run_web_server
        console.print("\n[bold green]🌐 Démarrage du serveur web...[/]")
        run_web_server()
        return

    if args.attack:
        console.print(f"\n[bold yellow]🎯 Exécution de l'attaque: {args.attack}[/]")
        attack_class = ATTACK_REGISTRY[args.attack]
        attack = attack_class()
        attack.run_simulation()
        return

    if args.demo:
        console.print("\n[bold green]🎬 Mode démonstration[/]")
        lab = InteractiveLab()
        lab.run_demo()
        return

    # Mode interactif par défaut
    console.print("\n[bold green]🚀 Démarrage du mode interactif...[/]\n")
    lab = InteractiveLab()
    lab.run()


if __name__ == "__main__":
    main()
