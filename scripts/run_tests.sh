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

# Ne pas utiliser set -e car pytest retourne un code d'erreur si des tests échouent

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Répertoire du projet
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Déterminer la commande Python à utiliser
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo -e "${RED}Python non trouvé. Veuillez installer Python 3.${NC}"
    exit 1
fi

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  LLM Attack Lab - Test Runner${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Vérifier si les dépendances de test sont installées
check_dependencies() {
    echo -e "${YELLOW}Vérification des dépendances...${NC}"

    # Installer les dépendances du projet si nécessaire
    if ! $PYTHON -c "import flask" 2>/dev/null; then
        echo -e "${YELLOW}Installation des dépendances du projet...${NC}"
        $PYTHON -m pip install -r requirements.txt
    fi

    if ! $PYTHON -c "import pytest" 2>/dev/null; then
        echo -e "${YELLOW}Installation de pytest...${NC}"
        $PYTHON -m pip install pytest pytest-cov watchdog
    fi

    if ! $PYTHON -c "import watchdog" 2>/dev/null; then
        echo -e "${YELLOW}Installation de watchdog pour le mode watch...${NC}"
        $PYTHON -m pip install watchdog
    fi

    echo -e "${GREEN}Dépendances OK${NC}"
    echo ""
}

# Exécuter les tests une fois
run_tests() {
    echo -e "${CYAN}Exécution des tests...${NC}"
    echo ""

    # Vérifier d'abord que les imports fonctionnent
    if ! $PYTHON -c "from llm_attack_lab.core.llm_simulator import LLMSimulator" 2>/dev/null; then
        echo -e "${RED}Erreur d'import - installez les dépendances:${NC}"
        echo -e "${YELLOW}pip3 install -r requirements.txt${NC}"
        return 1
    fi

    # Exécuter les tests avec sortie visible
    $PYTHON -m pytest tests/ --no-header

    local result=$?
    echo ""
    if [ $result -eq 0 ]; then
        echo -e "${GREEN}Tous les tests passent!${NC}"
    else
        echo -e "${RED}Certains tests ont échoué.${NC}"
    fi
}

# Exécuter les tests en mode watch (continu)
run_watch() {
    echo -e "${CYAN}Mode watch activé - Les tests s'exécutent automatiquement à chaque modification${NC}"
    echo -e "${YELLOW}Appuyez sur Ctrl+C pour arrêter${NC}"
    echo ""

    # Exécuter les tests une première fois
    $PYTHON -m pytest tests/ -v --tb=short -x || true

    echo ""
    echo -e "${CYAN}En attente de modifications...${NC}"
    echo ""

    # Utiliser watchmedo de watchdog pour surveiller les fichiers
    if $PYTHON -c "import watchdog" 2>/dev/null; then
        $PYTHON -m watchdog.watchmedo shell-command \
            --patterns="*.py" \
            --recursive \
            --command='echo -e "\n\033[0;36m[$(date +%H:%M:%S)] Changement détecté, relance des tests...\033[0m\n" && '"$PYTHON"' -m pytest tests/ -v --tb=short -x || true' \
            llm_attack_lab/ tests/
    else
        # Fallback: boucle simple avec polling
        echo -e "${YELLOW}watchdog non installé, utilisation du mode polling (moins efficace)${NC}"
        LAST_HASH=""
        while true; do
            CURRENT_HASH=$(find llm_attack_lab tests -name "*.py" -exec md5sum {} \; 2>/dev/null | md5sum)
            if [ "$CURRENT_HASH" != "$LAST_HASH" ] && [ -n "$LAST_HASH" ]; then
                echo -e "\n${CYAN}[$(date +%H:%M:%S)] Changement détecté, relance des tests...${NC}\n"
                $PYTHON -m pytest tests/ -v --tb=short -x || true
            fi
            LAST_HASH=$CURRENT_HASH
            sleep 2
        done
    fi
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
