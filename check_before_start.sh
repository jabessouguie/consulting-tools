#!/bin/bash

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 DIAGNOSTIC PRÉ-DÉMARRAGE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check Python version
PYTHON_VERSION=$(python --version 2>&1)
echo "Python actif : $PYTHON_VERSION"

if [[ "$PYTHON_VERSION" == *"3.13"* ]]; then
    echo "✅ Python 3.13 actif - CORRECT"
else
    echo "❌ ERREUR : Python 3.13 requis !"
    echo "   Exécutez : source .venv/bin/activate"
    exit 1
fi

# Check critical imports
echo ""
echo "Test des imports critiques..."

python -c "
import sys
sys.path.insert(0, '.')
errors = []

try:
    from agents.formation_generator import FormationGeneratorAgent
    print('  ✅ FormationGeneratorAgent')
except Exception as e:
    errors.append(f'FormationGeneratorAgent: {e}')
    print(f'  ❌ FormationGeneratorAgent: {e}')

try:
    from pptx import Presentation
    print('  ✅ python-pptx (lxml)')
except Exception as e:
    errors.append(f'python-pptx: {e}')
    print(f'  ❌ python-pptx: {e}')

if errors:
    print('\n❌ ERREURS DÉTECTÉES - NE PAS DÉMARRER')
    sys.exit(1)
else:
    print('\n✅ Tous les imports OK')
" 2>&1 | grep -v "FutureWarning" | grep -v "google.generativeai"

if [ $? -eq 0 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ PRÊT À DÉMARRER !"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Exécutez maintenant : python app.py"
    echo ""
else
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "❌ PROBLÈMES DÉTECTÉS - CORRIGEZ AVANT DE DÉMARRER"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 1
fi
