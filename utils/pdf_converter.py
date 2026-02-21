"""
Convertisseur de documents vers PDF
Supporte PPTX → PDF et Markdown → PDF
"""
import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional


class PDFConverter:
    """Convertit différents formats vers PDF"""

    def __init__(self):
        """Initialise le convertisseur et détecte LibreOffice"""
        self.libreoffice_path = self._find_libreoffice()

    def _find_libreoffice(self) -> Optional[str]:
        """
        Détecte l'installation de LibreOffice

        Returns:
            Chemin vers LibreOffice ou None si non trouvé
        """
        # Chemins courants sur macOS
        mac_paths = [
            '/Applications/LibreOffice.app/Contents/MacOS/soffice',
            '/usr/local/bin/soffice',
        ]

        # Chemins courants sur Linux
        linux_paths = [
            '/usr/bin/libreoffice',
            '/usr/bin/soffice',
        ]

        # Vérifier les chemins
        for path in mac_paths + linux_paths:
            if os.path.exists(path):
                print(f"✅ LibreOffice trouvé : {path}")
                return path

        # Essayer via 'which'
        try:
            result = subprocess.run(
                ['which', 'soffice'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                path = result.stdout.strip()
                print(f"✅ LibreOffice trouvé : {path}")
                return path
        except Exception:
            pass

        print("⚠️  LibreOffice non trouvé - conversion PDF indisponible")
        return None

    def pptx_to_pdf(self, pptx_path: str, output_dir: Optional[str] = None) -> Optional[str]:
        """
        Convertit un fichier PPTX en PDF via LibreOffice

        Args:
            pptx_path: Chemin vers le fichier PPTX
            output_dir: Répertoire de sortie (par défaut : même que l'entrée)

        Returns:
            Chemin vers le PDF généré ou None si échec
        """
        if not self.libreoffice_path:
            print("❌ Conversion PDF impossible : LibreOffice non installé")
            return None

        pptx_path = Path(pptx_path)
        if not pptx_path.exists():
            print(f"❌ Fichier non trouvé : {pptx_path}")
            return None

        if output_dir is None:
            output_dir = pptx_path.parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        print(f"🔄 Conversion PPTX → PDF : {pptx_path.name}")

        try:
            # Commande LibreOffice pour conversion PDF
            # Options pour préserver les couleurs et la qualité
            cmd = [
                self.libreoffice_path,
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', str(output_dir),
                '-env:UserInstallation=file:///tmp/LibreOffice_Conversion_${USER}',
                str(pptx_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minutes max
            )

            if result.returncode == 0:
                # Le PDF a le même nom que le PPTX
                pdf_path = output_dir / f"{pptx_path.stem}.pdf"
                if pdf_path.exists():
                    print(f"✅ PDF créé : {pdf_path}")
                    return str(pdf_path)
                else:
                    print(f"❌ PDF non créé (erreur LibreOffice)")
                    return None
            else:
                print(f"❌ Erreur LibreOffice : {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            print("❌ Timeout lors de la conversion PDF")
            return None
        except Exception as e:
            print(f"❌ Erreur lors de la conversion : {e}")
            return None

    def markdown_to_pdf(self, md_path: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        Convertit un fichier Markdown en PDF via HTML intermédiaire

        Note: Nécessite weasyprint ou pandoc. Si non disponible, retourne None.

        Args:
            md_path: Chemin vers le fichier Markdown
            output_path: Chemin de sortie PDF (optionnel)

        Returns:
            Chemin vers le PDF généré ou None
        """
        md_path = Path(md_path)
        if not md_path.exists():
            print(f"❌ Fichier non trouvé : {md_path}")
            return None

        if output_path is None:
            output_path = md_path.parent / f"{md_path.stem}.pdf"
        else:
            output_path = Path(output_path)

        print(f"🔄 Conversion Markdown → PDF : {md_path.name}")

        # Essayer via pandoc (plus commun)
        pandoc_path = shutil.which('pandoc')
        if pandoc_path:
            try:
                cmd = [
                    pandoc_path,
                    str(md_path),
                    '-o', str(output_path),
                    '--pdf-engine=xelatex',  # ou pdflatex
                    '-V', 'geometry:margin=1in',
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode == 0 and output_path.exists():
                    print(f"✅ PDF créé : {output_path}")
                    return str(output_path)
                else:
                    print(f"❌ Erreur pandoc : {result.stderr}")
            except Exception as e:
                print(f"❌ Erreur pandoc : {e}")

        # Essayer via weasyprint (si installé)
        try:
            import markdown
            from weasyprint import HTML

            # Convertir MD → HTML
            with open(md_path, 'r', encoding='utf-8') as f:
                md_content = f.read()

            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        /* Palette WEnvision */
        :root {{
            --blanc: #FFFFFF;
            --rose-poudre: #F5E6E8;
            --noir-profond: #1A1A1A;
            --gris-clair: #F5F5F5;
            --gris-moyen: #9CA3AF;
            --corail: #E86F51;
            --terracotta: #C4624F;
        }}

        @page {{
            size: A4;
            margin: 2cm;
            @bottom-right {{
                content: counter(page);
                font-size: 10pt;
                color: #9CA3AF;
            }}
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #1A1A1A;
            background: #FFFFFF;
            font-size: 11pt;
        }}

        /* Titres avec palette WEnvision */
        h1 {{
            color: #E86F51;
            font-family: 'Chakra Petch', Arial, sans-serif;
            font-size: 28pt;
            font-weight: 700;
            margin-top: 0;
            margin-bottom: 16pt;
            padding-bottom: 8pt;
            border-bottom: 3px solid #F5E6E8;
        }}

        h2 {{
            color: #C4624F;
            font-family: 'Chakra Petch', Arial, sans-serif;
            font-size: 20pt;
            font-weight: 600;
            margin-top: 24pt;
            margin-bottom: 12pt;
        }}

        h3 {{
            color: #1A1A1A;
            font-family: 'Chakra Petch', Arial, sans-serif;
            font-size: 16pt;
            font-weight: 600;
            margin-top: 16pt;
            margin-bottom: 8pt;
        }}

        h4, h5, h6 {{
            color: #1A1A1A;
            font-weight: 600;
            margin-top: 12pt;
            margin-bottom: 6pt;
        }}

        /* Paragraphes */
        p {{
            margin-bottom: 10pt;
            text-align: justify;
        }}

        /* Listes */
        ul, ol {{
            margin-bottom: 12pt;
            padding-left: 25pt;
        }}

        li {{
            margin-bottom: 4pt;
        }}

        /* Emphase */
        strong {{
            color: #E86F51;
            font-weight: 600;
        }}

        em {{
            color: #C4624F;
            font-style: italic;
        }}

        /* Code */
        code {{
            background: #F5F5F5;
            color: #C4624F;
            padding: 2pt 4pt;
            border-radius: 3pt;
            font-family: 'Courier New', monospace;
            font-size: 10pt;
        }}

        pre {{
            background: #F5F5F5;
            border-left: 4px solid #E86F51;
            padding: 12pt;
            border-radius: 4pt;
            overflow-x: auto;
            margin-bottom: 12pt;
        }}

        pre code {{
            background: transparent;
            padding: 0;
            color: #1A1A1A;
        }}

        /* Citations */
        blockquote {{
            border-left: 4px solid #E86F51;
            background: #F5E6E8;
            padding: 12pt 16pt;
            margin: 12pt 0;
            color: #1A1A1A;
            font-style: italic;
        }}

        /* Tableaux */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 12pt;
        }}

        th {{
            background: #E86F51;
            color: #FFFFFF;
            padding: 8pt;
            text-align: left;
            font-weight: 600;
        }}

        td {{
            padding: 6pt 8pt;
            border-bottom: 1px solid #F5F5F5;
        }}

        tr:nth-child(even) {{
            background: #F5E6E8;
        }}

        /* Liens */
        a {{
            color: #E86F51;
            text-decoration: none;
            font-weight: 500;
        }}

        a:hover {{
            text-decoration: underline;
        }}

        /* Séparateurs */
        hr {{
            border: none;
            border-top: 2px solid #F5E6E8;
            margin: 24pt 0;
        }}
    </style>
</head>
<body>
{markdown.markdown(md_content, extensions=['extra', 'codehilite', 'tables', 'toc'])}
</body>
</html>
"""

            # HTML → PDF
            HTML(string=html_content).write_pdf(str(output_path))
            print(f"✅ PDF créé : {output_path}")
            return str(output_path)

        except ImportError:
            print("⚠️  weasyprint non installé - conversion MD→PDF indisponible")
            print("   Installez avec: pip install weasyprint markdown")
        except Exception as e:
            print(f"❌ Erreur weasyprint : {e}")

        return None

    def is_pdf_conversion_available(self) -> dict:
        """
        Vérifie quels types de conversion sont disponibles

        Returns:
            Dict avec les conversions disponibles
        """
        return {
            'pptx_to_pdf': self.libreoffice_path is not None,
            'markdown_to_pdf': shutil.which('pandoc') is not None or self._has_weasyprint(),
        }

    @staticmethod
    def _has_weasyprint() -> bool:
        """Vérifie si weasyprint est installé"""
        try:
            import weasyprint
            return True
        except ImportError:
            return False


# Instance globale
pdf_converter = PDFConverter()
