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
            cmd = [
                self.libreoffice_path,
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', str(output_dir),
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
        body {{
            font-family: 'Inter', Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            color: #333;
        }}
        h1, h2, h3 {{ color: #FF6B58; font-family: 'Chakra Petch', sans-serif; }}
        code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        blockquote {{ border-left: 4px solid #FF6B58; padding-left: 20px; margin-left: 0; color: #666; }}
    </style>
</head>
<body>
{markdown.markdown(md_content, extensions=['extra', 'codehilite'])}
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
