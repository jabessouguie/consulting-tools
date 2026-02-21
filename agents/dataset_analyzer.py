"""
Agent d'analyse de datasets
Génère un rapport d'analyse exploratoire automatique (EDA) à partir de CSV/Excel
"""
import os
import sys
from typing import Dict, Any, List
from datetime import datetime
import io

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

import pandas as pd
import numpy as np

from utils.llm_client import LLMClient
from config import get_consultant_info


class DatasetAnalyzerAgent:
    """Agent d'analyse automatique de datasets pour consultants data"""

    def __init__(self):
        self.llm_client = LLMClient()

        # Informations consultant (depuis config centralisee)
        self.consultant_info = get_consultant_info()

    def load_dataset(self, file_path: str) -> pd.DataFrame:
        """
        Charge un dataset depuis CSV ou Excel

        Args:
            file_path: Chemin du fichier

        Returns:
            DataFrame pandas
        """
        print(f"📂 Chargement du dataset: {os.path.basename(file_path)}")

        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.csv':
            # Essayer différents encodages
            for encoding in ['utf-8', 'latin1', 'iso-8859-1']:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    print(f"   ✅ Chargé avec encoding {encoding}")
                    break
                except UnicodeDecodeError:
                    continue
        elif ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
            print(f"   ✅ Chargé depuis Excel")
        else:
            raise ValueError(f"Format non supporté: {ext}")

        print(f"   📊 {len(df)} lignes, {len(df.columns)} colonnes")

        return df

    def analyze_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyse la structure du dataset

        Args:
            df: DataFrame

        Returns:
            Informations structurelles
        """
        print("🔍 Analyse de la structure...")

        structure = {
            'num_rows': len(df),
            'num_columns': len(df.columns),
            'columns': list(df.columns),
            'dtypes': df.dtypes.astype(str).to_dict(),
            'memory_usage': df.memory_usage(deep=True).sum() / 1024**2,  # MB
        }

        # Types de colonnes
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()

        structure['numeric_columns'] = numeric_cols
        structure['categorical_columns'] = categorical_cols
        structure['datetime_columns'] = datetime_cols

        print(f"   ✅ {len(numeric_cols)} colonnes numériques, {len(categorical_cols)} catégorielles")

        return structure

    def analyze_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyse la qualité des données

        Args:
            df: DataFrame

        Returns:
            Métriques de qualité
        """
        print("✨ Analyse de la qualité...")

        quality = {}

        # Valeurs manquantes
        missing = df.isnull().sum()
        missing_pct = (missing / len(df) * 100).round(2)
        quality['missing_values'] = {
            col: {'count': int(missing[col]), 'percentage': float(missing_pct[col])}
            for col in df.columns if missing[col] > 0
        }

        # Duplicats
        duplicates = df.duplicated().sum()
        quality['duplicates'] = {
            'count': int(duplicates),
            'percentage': float(round(duplicates / len(df) * 100, 2))
        }

        print(f"   ✅ {len(quality['missing_values'])} colonnes avec valeurs manquantes, {duplicates} duplicats")

        return quality

    def analyze_statistics(self, df: pd.DataFrame, structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcule les statistiques descriptives

        Args:
            df: DataFrame
            structure: Infos structurelles

        Returns:
            Statistiques
        """
        print("📊 Calcul des statistiques...")

        stats = {}

        # Stats numériques
        if structure['numeric_columns']:
            numeric_stats = df[structure['numeric_columns']].describe().round(2).to_dict()
            stats['numeric'] = numeric_stats

        # Stats catégorielles (top values)
        categorical_stats = {}
        for col in structure['categorical_columns'][:10]:  # Limiter à 10 cols
            value_counts = df[col].value_counts().head(5)
            categorical_stats[col] = {
                'unique_values': int(df[col].nunique()),
                'top_5': value_counts.to_dict()
            }
        stats['categorical'] = categorical_stats

        # Corrélations (top 10)
        if len(structure['numeric_columns']) > 1:
            corr_matrix = df[structure['numeric_columns']].corr()
            # Extraire les corrélations fortes (> 0.5 ou < -0.5)
            strong_corr = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i+1, len(corr_matrix.columns)):
                    val = corr_matrix.iloc[i, j]
                    if abs(val) > 0.5:
                        strong_corr.append({
                            'var1': corr_matrix.columns[i],
                            'var2': corr_matrix.columns[j],
                            'correlation': round(float(val), 3)
                        })
            # Trier par corrélation absolue
            strong_corr = sorted(strong_corr, key=lambda x: abs(x['correlation']), reverse=True)[:10]
            stats['correlations'] = strong_corr

        print(f"   ✅ Statistiques calculées")

        return stats

    def generate_report(
        self,
        df: pd.DataFrame,
        structure: Dict[str, Any],
        quality: Dict[str, Any],
        stats: Dict[str, Any],
        filename: str
    ) -> Dict[str, Any]:
        """
        Génère un rapport d'analyse avec insights LLM

        Args:
            df: DataFrame
            structure: Infos structurelles
            quality: Métriques qualité
            stats: Statistiques
            filename: Nom du fichier

        Returns:
            Rapport complet
        """
        print("✍️  Génération du rapport avec insights IA...")

        system_prompt = f"""Tu es {self.consultant_info['name']}, {self.consultant_info['title']} chez {self.consultant_info['company']}.
Tu analyses des datasets pour des clients et génères des rapports d'analyse exploratoire."""

        # Préparer le contexte
        context = f"""DATASET: {filename}

STRUCTURE:
- {structure['num_rows']} lignes, {structure['num_columns']} colonnes
- {len(structure['numeric_columns'])} colonnes numériques
- {len(structure['categorical_columns'])} colonnes catégorielles
- Taille mémoire: {structure['memory_usage']:.2f} MB

QUALITÉ:
- Valeurs manquantes: {len(quality['missing_values'])} colonnes concernées
- Duplicats: {quality['duplicates']['count']} ({quality['duplicates']['percentage']}%)

COLONNES NUMÉRIQUES:
{', '.join(structure['numeric_columns'][:20])}

COLONNES CATÉGORIELLES:
{', '.join(structure['categorical_columns'][:20])}

STATISTIQUES CLÉS (extrait):
{str(stats)[:1500]}"""

        prompt = f"""À partir de cette analyse de dataset, génère un rapport structuré en Markdown.

{context}

Le rapport doit contenir:

# 📊 Rapport d'Analyse - {filename}

## 🎯 Vue d'ensemble

[Résumé en 2-3 phrases : type de données, volume, usage potentiel]

## 📈 Structure du dataset

[Tableau récapitulatif : lignes, colonnes, types, mémoire]

## ⚠️ Qualité des données

[Points d'attention :
- Valeurs manquantes (si > 5% sur certaines colonnes)
- Duplicats (si présents)
- Anomalies potentielles]

## 🔍 Insights clés

[3-5 insights majeurs tirés des statistiques :
- Distributions remarquables
- Corrélations fortes identifiées
- Variables importantes
- Patterns observés]

## 💡 Recommandations

[3-4 recommandations actionnables :
- Nettoyage à effectuer
- Variables à creuser
- Analyses complémentaires à mener
- Cas d'usage potentiels]

Ton : professionnel et précis. Concentre-toi sur l'actionnable."""

        report = self.llm_client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=2000,
        )

        print("   ✅ Rapport généré")

        return {
            'report': report,
            'structure': structure,
            'quality': quality,
            'stats': stats,
            'generated_at': datetime.now().isoformat(),
        }

    def run(self, file_path: str) -> Dict[str, Any]:
        """
        Pipeline complet: charge -> analyse -> rapport

        Args:
            file_path: Chemin du fichier CSV/Excel

        Returns:
            Résultat complet
        """
        print(f"\n{'='*50}")
        print("📊 ANALYSE DE DATASET")
        print(f"{'='*50}\n")

        filename = os.path.basename(file_path)

        # Charger
        df = self.load_dataset(file_path)

        # Analyser
        structure = self.analyze_structure(df)
        quality = self.analyze_quality(df)
        stats = self.analyze_statistics(df, structure)

        # Générer rapport
        result = self.generate_report(df, structure, quality, stats, filename)

        # Sauvegarder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        md_path = os.path.join(output_dir, f"dataset_analysis_{timestamp}.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(result['report'])

        result['md_path'] = md_path
        result['filename'] = filename

        print(f"\n✅ Rapport sauvegardé: {md_path}")

        return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Analyse automatique de dataset')
    parser.add_argument('file', help='Fichier CSV ou Excel à analyser')

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"❌ Fichier introuvable: {args.file}")
        return

    agent = DatasetAnalyzerAgent()
    result = agent.run(file_path=args.file)

    print(f"\n{'='*50}")
    print("RAPPORT GÉNÉRÉ")
    print(f"{'='*50}\n")
    print(result['report'][:1000] + "...")


if __name__ == '__main__':
    main()
