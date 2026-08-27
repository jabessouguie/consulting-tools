# 🚀 Guide de Contribution & Roadmap de Production

Bienvenue dans le projet **Consulting Tools**. Ce document définit les standards de qualité, le flux de travail et la roadmap critique avant le passage en production.

## 🛠 Phase 1 : Corrections et Évolutions Prioritaires

Chaque contributeur doit s'assurer que les fonctionnalités suivantes sont pleinement opérationnelles et affinées selon les spécifications ci-dessous.

### 📝 1. Génération de Comptes Rendus (Meeting Summarizer)
- **Partage Gmail** : Implémenter la possibilité de partager le compte rendu directement via l'API Gmail.
- **Nettoyage LLM** : Supprimer systématiquement les préambules conversationnels de l'IA (ex: *"Absolument. Voici l'email rédigé..."*) pour ne garder que le contenu professionnel pur.

### 📄 2. Document Generator
- **Fidélité d'Export** : Garantir que le style visuel (mise en page, police, couleurs) est conservé lors de l'exportation vers Google Docs.

### 🧠 3. Market of Skills
- **Identité Visuelle** : Ajouter la gestion des photos de profil pour les consultants.
- **Génération Ciblé** : Permettre la génération automatique de CV (PDF ou HTML) directement depuis le profil, en adaptant le contenu à un besoin client spécifique fourni en entrée.

### 🎓 4. E-learning Adaptatif
- **Personnalisation** : Ajouter une option "Public cible personnalisé" dans les paramètres.
- **Moteur de Validation** : Corriger le bug de détection des bonnes réponses (faux négatifs occasionnels).
- **Ressources Premium** : Générer des ressources d'apprentissage personnalisées (ex: fiches mémo, résumés) pour chaque parcours.
- **Préparation Entretien** :
    - Transformer l'expérience en un **Chat interactif** simulant l'entretien.
    - Fournir une analyse détaillée de la performance à la fin.
    - Intégrer l'analyse du profil LinkedIn de l'interviewer et les documents de poste en entrée.

### 🛝 5. Slide & Document Editor
- **Multi-upload** : Activer la possibilité d'uploader plusieurs fichiers source simultanément pour la génération de contenu.

---

## 🏁 Phase 2 : Standard de Qualité Production (Definition of Done)

Avant tout déploiement en production, les critères suivants doivent être validés à 100% :

### 📖 Documentation & Wiki
- **Code Clair** : Documenter l'intégralité des modules (docstrings, commentaires complexes) pour faciliter la reprise par un nouveau développeur.
- **Wiki Centralisé** : Maintenir un wiki complet décrivant l'architecture et les processus métiers.

### 🔐 Sécurité & Qualité
- **Audit de Sécurité** : Effectuer un scan complet des vulnérabilités et corriger chaque faille identifiée.
- **Pre-commit Hooks** : Configurer et imposer des règles de pre-commit strictes (linting, secrets detection, formats).
- **Audit UI/UX** : Réaliser une revue ergonomique complète et appliquer les corrections pour une expérience utilisateur premium.

### 🧪 Tests et Couverture

**Cible de production** (non encore atteinte) : couverture 100 % sur l'ensemble
du code applicatif, et build vert.

**État mesuré au 27/08/2026** — c'est la référence à ne pas dégrader :

| Indicateur | Valeur | Écart à la cible |
|---|---|---|
| Tests qui passent | 1777 | — |
| Tests en échec | 7 | 7 à traiter (voir ci-dessous) |
| Couverture `agents/` + `utils/` | 87 % | 13 pts |
| Couverture `routers/` + `app.py` | **non mesurée** | ~9 500 lignes hors instrumentation |
| Seuil bloquant en CI (`--cov-fail-under`) | 15 % | à relever progressivement |

Les 7 échecs connus, à résorber et non à normaliser :
- `test_tender_scout` ×2 — dépendance `openpyxl` absente de l'environnement.
- `test_linkedin_client` ×3 et `test_config_consultant` ×1 — les tests lisent le
  `.env` réel au lieu d'un environnement isolé ; l'un d'eux effectue un appel
  réseau sortant vers l'API LinkedIn.
- `test_veille_tech` ×1 — collecte d'articles.

**Règle de contribution** : aucune PR ne doit augmenter le nombre d'échecs ni
faire baisser la couverture. Une PR qui résorbe un des 7 échecs ci-dessus met à
jour ce tableau.

> ⚠️ Un test qui n'assère rien ne compte pas comme un test. 163 des tests
> actuels n'ont aucune assertion utile — ne pas en ajouter de nouveaux.

---

## 💻 Flux de Travail
1. Créer une branche issue de `dev`.
2. Respecter les règles de pre-commit.
3. Documenter chaque ajout.
4. S'assurer que les tests passent et que la couverture est maintenue.
5. Ouvrir une Pull Request vers `dev`.
