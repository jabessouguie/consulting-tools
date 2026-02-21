#!/bin/bash
# Script de démonstration des agents Consulting Tools

echo "=================================="
echo "🚀 DEMO AGENTS Consulting Tools"
echo "=================================="
echo ""

# Vérifier que l'environnement virtuel est activé
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Environnement virtuel non activé"
    echo "   Exécutez: source venv/bin/activate"
    exit 1
fi

# Vérifier que les dépendances sont installées
if ! python -c "import anthropic" 2>/dev/null; then
    echo "⚠️  Dépendances non installées"
    echo "   Exécutez: pip install -r requirements.txt"
    exit 1
fi

# Vérifier la clé API
if [[ -z "$ANTHROPIC_API_KEY" ]]; then
    if [[ -f .env ]]; then
        export $(cat .env | grep -v '^#' | xargs)
    fi

    if [[ -z "$ANTHROPIC_API_KEY" ]]; then
        echo "⚠️  Clé API Anthropic non trouvée"
        echo "   Configurez ANTHROPIC_API_KEY dans .env"
        exit 1
    fi
fi

echo "✅ Configuration OK"
echo ""

# Menu
echo "Que voulez-vous tester?"
echo ""
echo "1. 🔍 Veille uniquement (rapide, ~2 min)"
echo "2. ✍️  Veille + 1 post LinkedIn (~5 min)"
echo "3. 📄 Génération proposition commerciale (~5 min)"
echo "4. 🚀 Tout tester (~10 min)"
echo ""
read -p "Votre choix (1-4): " choice

case $choice in
    1)
        echo ""
        echo "=================================="
        echo "🔍 VEILLE TECHNOLOGIQUE"
        echo "=================================="
        echo ""
        python agents/linkedin_monitor.py --no-posts
        echo ""
        echo "✅ Veille terminée!"
        echo "   Résultats dans: data/monitoring/"
        ;;
    2)
        echo ""
        echo "=================================="
        echo "✍️  VEILLE + POST LINKEDIN"
        echo "=================================="
        echo ""
        python agents/linkedin_monitor.py --num-posts 1
        echo ""
        echo "✅ Post généré!"
        echo "   Résultats dans: output/"
        echo ""
        echo "Voulez-vous voir le post? (o/n)"
        read -p "> " show_post
        if [[ "$show_post" == "o" ]]; then
            cat output/linkedin_post_*.md 2>/dev/null | head -50
        fi
        ;;
    3)
        echo ""
        echo "=================================="
        echo "📄 PROPOSITION COMMERCIALE"
        echo "=================================="
        echo ""
        if [[ ! -f "data/examples/appel_offre_example.txt" ]]; then
            echo "⚠️  Fichier d'exemple non trouvé"
            echo "   Créez data/examples/appel_offre_example.txt"
            exit 1
        fi
        python agents/proposal_generator.py data/examples/appel_offre_example.txt
        echo ""
        echo "✅ Proposition générée!"
        echo "   Résultats dans: output/"
        echo ""
        echo "Voulez-vous voir la proposition? (o/n)"
        read -p "> " show_proposal
        if [[ "$show_proposal" == "o" ]]; then
            cat output/proposal_*.md 2>/dev/null | head -100
        fi
        ;;
    4)
        echo ""
        echo "=================================="
        echo "🚀 TEST COMPLET"
        echo "=================================="
        echo ""

        echo "1/2 - Veille + Post LinkedIn..."
        python agents/linkedin_monitor.py --num-posts 1

        echo ""
        echo "2/2 - Proposition commerciale..."
        python agents/proposal_generator.py data/examples/appel_offre_example.txt

        echo ""
        echo "✅ Tous les tests terminés!"
        echo ""
        echo "📊 Résultats:"
        echo "   - Veille: data/monitoring/"
        echo "   - Posts LinkedIn: output/linkedin_post_*.md"
        echo "   - Proposition: output/proposal_*.md"
        ;;
    *)
        echo "Choix invalide"
        exit 1
        ;;
esac

echo ""
echo "=================================="
echo "✨ DEMO TERMINÉE"
echo "=================================="
echo ""
echo "Prochaines étapes:"
echo "  - Consulter les résultats dans output/"
echo "  - Lire QUICKSTART.md pour plus de détails"
echo "  - Configurer Google API (optionnel): GOOGLE_API_SETUP.md"
echo ""
