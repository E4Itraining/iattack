# LLM Attack Simulation Lab

Un laboratoire interactif pour comprendre et simuler les attaques sur les Large Language Models (LLMs).

## Objectif

Ce lab permet de:
- **Comprendre** les vulnérabilités des LLMs
- **Simuler** différents types d'attaques en environnement contrôlé
- **Apprendre** les mécanismes de défense

## Types d'attaques simulées

| Attaque | Description | Risque |
|---------|-------------|--------|
| **Prompt Injection** | Manipulation des instructions du LLM | Critique |
| **Data Poisoning** | Corruption des données d'entraînement | Élevé |
| **Jailbreak** | Contournement des guardrails | Critique |
| **Model Extraction** | Vol de propriété intellectuelle | Élevé |
| **Membership Inference** | Détection de données d'entraînement | Moyen |

## Installation

```bash
# Cloner le repository
git clone <repo-url>
cd iattack

# Installer les dépendances
pip install -r requirements.txt

# Lancer le lab
python -m llm_attack_lab
```

## Utilisation

### Mode CLI Interactif
```bash
python -m llm_attack_lab --interactive
```

### Mode Dashboard Web
```bash
python -m llm_attack_lab --web
# Ouvrir http://localhost:8080
```

### Exécuter une simulation spécifique
```bash
python -m llm_attack_lab --attack prompt_injection
python -m llm_attack_lab --attack data_poisoning
python -m llm_attack_lab --attack jailbreak
```

## Structure du Projet

```
llm_attack_lab/
├── __main__.py           # Point d'entrée
├── core/
│   ├── llm_simulator.py  # Simulateur de LLM
│   └── attack_engine.py  # Moteur d'attaques
├── attacks/
│   ├── prompt_injection.py
│   ├── data_poisoning.py
│   ├── jailbreak.py
│   └── model_extraction.py
├── defenses/
│   ├── input_sanitizer.py
│   └── output_filter.py
├── web/
│   ├── app.py
│   └── templates/
└── utils/
    └── logger.py
```

## Avertissement

Ce laboratoire est destiné à des fins **éducatives uniquement**.
L'utilisation de ces techniques sur des systèmes sans autorisation est illégale.

## Licence

MIT License - Usage éducatif uniquement
