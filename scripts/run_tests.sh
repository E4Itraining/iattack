#!/bin/bash
#
# Script pour exécuter les tests du LLM Attack Lab
#
# ÉTAPES:
# 1. Installation des dépendances de test
# 2. Exécution des tests avec couverture
# 3. Génération du rapport
#
# MODES D'EXÉCUTION:
# - ./run_tests.sh         : Exécuter tous les tests une fois
# - ./run_tests.sh watch   : Exécuter les tests en continu (watch mode)
# - ./run_tests.sh coverage: Exécuter avec rapport de couverture
#

set -e

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Détecter la commande Python disponible
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo -e "${RED}Erreur: Python n'est pas installé.${NC}"
    exit 1
fi

# Répertoire du projet
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  LLM Attack Lab - Test Runner${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Vérifier si les dépendances de test sont installées
check_dependencies() {
    echo -e "${YELLOW}Vérification des dépendances...${NC}"

    if ! $PYTHON -c "import pytest" 2>/dev/null; then
        echo -e "${YELLOW}Installation de pytest...${NC}"
        $PYTHON -m pip install pytest pytest-watch pytest-cov
    fi

    echo -e "${GREEN}Dépendances OK${NC}"
    echo ""
}

# Exécuter les tests une fois
run_tests() {
    echo -e "${CYAN}Exécution des tests...${NC}"
    echo ""

    $PYTHON -m pytest tests/ \
        -v \
        --tb=short \
        -x \
        --strict-markers

    echo ""
    echo -e "${GREEN}Tests terminés!${NC}"
}

# Exécuter les tests en mode watch (continu)
run_watch() {
    echo -e "${CYAN}Mode watch activé - Les tests s'exécutent automatiquement à chaque modification${NC}"
    echo -e "${YELLOW}Appuyez sur Ctrl+C pour arrêter${NC}"
    echo ""

    # pytest-watch surveille les fichiers et relance les tests automatiquement
    $PYTHON -m pytest_watch -- tests/ \
        -v \
        --tb=short \
        -x
}

# Exécuter avec couverture de code
run_coverage() {
    echo -e "${CYAN}Exécution des tests avec couverture...${NC}"
    echo ""

    $PYTHON -m pytest tests/ \
        -v \
        --tb=short \
        --cov=llm_attack_lab \
        --cov-report=term-missing \
        --cov-report=html:coverage_report

    echo ""
    echo -e "${GREEN}Rapport de couverture généré dans: coverage_report/index.html${NC}"
}

# Exécuter uniquement les tests unitaires (rapides)
run_unit() {
    echo -e "${CYAN}Exécution des tests unitaires...${NC}"
    echo ""

    $PYTHON -m pytest tests/ \
        -v \
        --tb=short \
        -m "unit" \
        -x
}

# Exécuter uniquement les tests d'intégration
run_integration() {
    echo -e "${CYAN}Exécution des tests d'intégration...${NC}"
    echo ""

    $PYTHON -m pytest tests/ \
        -v \
        --tb=short \
        -m "integration"
}

# Exécuter uniquement les tests web/API
run_web() {
    echo -e "${CYAN}Exécution des tests Web/API...${NC}"
    echo ""

    $PYTHON -m pytest tests/test_web_api.py \
        -v \
        --tb=short
}

# Afficher l'aide
show_help() {
    echo "Usage: ./run_tests.sh [OPTION]"
    echo ""
    echo "Options:"
    echo "  (vide)      Exécuter tous les tests une fois"
    echo "  watch       Mode continu - relance les tests à chaque modification"
    echo "  coverage    Exécuter avec rapport de couverture"
    echo "  unit        Exécuter uniquement les tests unitaires"
    echo "  integration Exécuter uniquement les tests d'intégration"
    echo "  web         Exécuter uniquement les tests Web/API"
    echo "  help        Afficher cette aide"
    echo ""
    echo "Exemples:"
    echo "  ./run_tests.sh           # Tous les tests"
    echo "  ./run_tests.sh watch     # Tests en continu"
    echo "  ./run_tests.sh coverage  # Avec couverture"
}

# Main
check_dependencies

case "${1:-}" in
    watch)
        run_watch
        ;;
    coverage)
        run_coverage
        ;;
    unit)
        run_unit
        ;;
    integration)
        run_integration
        ;;
    web)
        run_web
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        run_tests
        ;;
esac
