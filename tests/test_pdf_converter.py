"""
Tests pour utils/pdf_converter.py — PDFConverter
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _make_converter(libreoffice_path=None, branding=None):
    """Create a PDFConverter with controlled __init__ side-effects."""
    with patch("utils.pdf_converter.PDFConverter._find_libreoffice", return_value=libreoffice_path), \
         patch("utils.pdf_converter.PDFConverter._load_branding",
               return_value=branding or {"colors": {}, "fonts": {}}):
        from utils.pdf_converter import PDFConverter
        return PDFConverter()


# ---------------------------------------------------------------------------
# _load_branding
# ---------------------------------------------------------------------------


class TestLoadBranding:
    def test_returns_fallback_when_no_file(self):
        """Retourne les defaults si branding.json est absent."""
        converter = _make_converter()
        with patch.object(Path, "exists", return_value=False):
            result = converter._load_branding()
        assert "colors" in result
        assert "fonts" in result
        assert "corail" in result["colors"]

    def test_loads_from_file_when_exists(self):
        """Charge depuis branding.json quand il existe."""
        data = {"colors": {"blanc": "FFFFFF"}, "fonts": {"title": "Roboto"}}
        converter = _make_converter()
        with patch.object(Path, "exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=json.dumps(data))):
            result = converter._load_branding()
        assert result["fonts"]["title"] == "Roboto"

    def test_returns_fallback_on_io_error(self):
        """Retourne les defaults en cas d'IOError."""
        converter = _make_converter()
        with patch.object(Path, "exists", return_value=True), \
             patch("builtins.open", side_effect=IOError("cannot open")):
            result = converter._load_branding()
        assert "colors" in result
        assert "fonts" in result

    def test_fallback_has_all_color_keys(self):
        """Le fallback contient toutes les clés de couleur requises."""
        converter = _make_converter()
        with patch.object(Path, "exists", return_value=False):
            result = converter._load_branding()
        for key in ("blanc", "rose-poudre", "noir-profond", "corail"):
            assert key in result["colors"]


# ---------------------------------------------------------------------------
# _find_libreoffice
# ---------------------------------------------------------------------------


class TestFindLibreOffice:
    def test_returns_none_when_not_found(self):
        """Retourne None si LibreOffice est introuvable."""
        converter = _make_converter()
        with patch("utils.pdf_converter.os.path.exists", return_value=False), \
             patch("utils.pdf_converter.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            result = converter._find_libreoffice()
        assert result is None

    def test_returns_path_when_mac_path_exists(self):
        """Retourne le chemin macOS si LibreOffice est trouvé."""
        mac_path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        converter = _make_converter()

        def exists_side_effect(p):
            return p == mac_path

        with patch("utils.pdf_converter.os.path.exists", side_effect=exists_side_effect):
            result = converter._find_libreoffice()
        assert result == mac_path

    def test_returns_path_when_linux_path_exists(self):
        """Retourne le chemin Linux si LibreOffice est trouvé."""
        linux_path = "/usr/bin/libreoffice"
        converter = _make_converter()

        def exists_side_effect(p):
            return p == linux_path

        with patch("utils.pdf_converter.os.path.exists", side_effect=exists_side_effect):
            result = converter._find_libreoffice()
        assert result == linux_path

    def test_returns_path_via_which(self):
        """Retourne le chemin via 'which soffice' si non trouvé directement."""
        converter = _make_converter()
        with patch("utils.pdf_converter.os.path.exists", return_value=False), \
             patch("utils.pdf_converter.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="/usr/local/bin/soffice\n")
            result = converter._find_libreoffice()
        assert result == "/usr/local/bin/soffice"

    def test_returns_none_when_which_fails(self):
        """Retourne None si 'which' retourne un code non-nul."""
        converter = _make_converter()
        with patch("utils.pdf_converter.os.path.exists", return_value=False), \
             patch("utils.pdf_converter.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            result = converter._find_libreoffice()
        assert result is None

    def test_returns_none_when_subprocess_raises(self):
        """Retourne None si subprocess lève une exception."""
        converter = _make_converter()
        with patch("utils.pdf_converter.os.path.exists", return_value=False), \
             patch("utils.pdf_converter.subprocess.run",
                   side_effect=Exception("no subprocess")):
            result = converter._find_libreoffice()
        assert result is None

    def test_returns_usr_local_bin_when_exists(self):
        """Retourne /usr/local/bin/soffice si ce chemin existe."""
        lo_path = "/usr/local/bin/soffice"
        converter = _make_converter()

        def exists_side_effect(p):
            return p == lo_path

        with patch("utils.pdf_converter.os.path.exists", side_effect=exists_side_effect):
            result = converter._find_libreoffice()
        assert result == lo_path


# ---------------------------------------------------------------------------
# pptx_to_pdf
# ---------------------------------------------------------------------------


class TestPptxToPdf:
    def test_returns_none_when_no_libreoffice(self, tmp_path):
        """Retourne None si LibreOffice n'est pas installé."""
        converter = _make_converter(libreoffice_path=None)
        result = converter.pptx_to_pdf(str(tmp_path / "file.pptx"))
        assert result is None

    def test_returns_none_when_pptx_not_found(self, tmp_path):
        """Retourne None si le fichier PPTX n'existe pas."""
        converter = _make_converter(libreoffice_path="/usr/bin/soffice")
        result = converter.pptx_to_pdf(str(tmp_path / "missing.pptx"))
        assert result is None

    def test_converts_successfully_default_output_dir(self, tmp_path):
        """Conversion réussie avec répertoire de sortie par défaut."""
        pptx = tmp_path / "slides.pptx"
        pptx.write_bytes(b"fake pptx")
        expected_pdf = tmp_path / "slides.pdf"
        expected_pdf.write_bytes(b"fake pdf")

        converter = _make_converter(libreoffice_path="/usr/bin/soffice")
        with patch("utils.pdf_converter.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            result = converter.pptx_to_pdf(str(pptx))

        assert result == str(expected_pdf)

    def test_converts_successfully_custom_output_dir(self, tmp_path):
        """Conversion réussie avec répertoire de sortie personnalisé."""
        pptx = tmp_path / "slides.pptx"
        pptx.write_bytes(b"fake pptx")
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        expected_pdf = out_dir / "slides.pdf"
        expected_pdf.write_bytes(b"fake pdf")

        converter = _make_converter(libreoffice_path="/usr/bin/soffice")
        with patch("utils.pdf_converter.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            result = converter.pptx_to_pdf(str(pptx), output_dir=str(out_dir))

        assert result == str(expected_pdf)

    def test_returns_none_when_pdf_not_created(self, tmp_path):
        """Retourne None si le PDF n'a pas été créé malgré returncode=0."""
        pptx = tmp_path / "slides.pptx"
        pptx.write_bytes(b"fake pptx")
        # PDF is NOT created

        converter = _make_converter(libreoffice_path="/usr/bin/soffice")
        with patch("utils.pdf_converter.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            result = converter.pptx_to_pdf(str(pptx))

        assert result is None

    def test_returns_none_on_nonzero_returncode(self, tmp_path):
        """Retourne None si LibreOffice retourne un code non-nul."""
        pptx = tmp_path / "slides.pptx"
        pptx.write_bytes(b"fake pptx")

        converter = _make_converter(libreoffice_path="/usr/bin/soffice")
        with patch("utils.pdf_converter.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="conversion failed")
            result = converter.pptx_to_pdf(str(pptx))

        assert result is None

    def test_returns_none_on_timeout(self, tmp_path):
        """Retourne None en cas de TimeoutExpired."""
        pptx = tmp_path / "slides.pptx"
        pptx.write_bytes(b"fake pptx")

        converter = _make_converter(libreoffice_path="/usr/bin/soffice")
        with patch("utils.pdf_converter.subprocess.run",
                   side_effect=subprocess.TimeoutExpired(cmd="soffice", timeout=120)):
            result = converter.pptx_to_pdf(str(pptx))

        assert result is None

    def test_returns_none_on_generic_exception(self, tmp_path):
        """Retourne None sur exception générique."""
        pptx = tmp_path / "slides.pptx"
        pptx.write_bytes(b"fake pptx")

        converter = _make_converter(libreoffice_path="/usr/bin/soffice")
        with patch("utils.pdf_converter.subprocess.run",
                   side_effect=Exception("unexpected error")):
            result = converter.pptx_to_pdf(str(pptx))

        assert result is None


# ---------------------------------------------------------------------------
# markdown_to_pdf
# ---------------------------------------------------------------------------


class TestMarkdownToPdf:
    def test_returns_none_when_md_not_found(self, tmp_path):
        """Retourne None si le fichier Markdown n'existe pas."""
        converter = _make_converter()
        result = converter.markdown_to_pdf(str(tmp_path / "missing.md"))
        assert result is None

    def test_pandoc_success_with_default_output(self, tmp_path):
        """Conversion pandoc réussie avec chemin de sortie par défaut."""
        md = tmp_path / "doc.md"
        md.write_text("# Hello", encoding="utf-8")
        expected_pdf = tmp_path / "doc.pdf"

        converter = _make_converter()
        with patch("utils.pdf_converter.shutil.which", return_value="/usr/bin/pandoc"), \
             patch("utils.pdf_converter.subprocess.run") as mock_run:
            def create_pdf(*args, **kwargs):
                expected_pdf.write_bytes(b"fake pdf")
                return MagicMock(returncode=0, stderr="")
            mock_run.side_effect = create_pdf
            result = converter.markdown_to_pdf(str(md))

        assert result == str(expected_pdf)

    def test_pandoc_success_with_custom_output(self, tmp_path):
        """Conversion pandoc réussie avec chemin de sortie personnalisé."""
        md = tmp_path / "doc.md"
        md.write_text("# Hello", encoding="utf-8")
        out_pdf = tmp_path / "custom.pdf"

        converter = _make_converter()
        with patch("utils.pdf_converter.shutil.which", return_value="/usr/bin/pandoc"), \
             patch("utils.pdf_converter.subprocess.run") as mock_run:
            def create_pdf(*args, **kwargs):
                out_pdf.write_bytes(b"fake pdf")
                return MagicMock(returncode=0, stderr="")
            mock_run.side_effect = create_pdf
            result = converter.markdown_to_pdf(str(md), output_path=str(out_pdf))

        assert result == str(out_pdf)

    def test_pandoc_failure_falls_through_to_weasyprint(self, tmp_path):
        """Après échec pandoc, essaie weasyprint."""
        md = tmp_path / "doc.md"
        md.write_text("# Hello", encoding="utf-8")

        mock_markdown_mod = MagicMock()
        mock_markdown_mod.markdown.return_value = "<h1>Hello</h1>"
        mock_html_cls = MagicMock()

        converter = _make_converter(
            branding={"colors": {"blanc": "FFF"}, "fonts": {"body": "Arial"}}
        )
        with patch("utils.pdf_converter.shutil.which", return_value="/usr/bin/pandoc"), \
             patch("utils.pdf_converter.subprocess.run") as mock_run, \
             patch.dict("sys.modules", {
                 "markdown": mock_markdown_mod,
                 "weasyprint": MagicMock(HTML=mock_html_cls),
             }):
            mock_run.return_value = MagicMock(returncode=1, stderr="pandoc error")
            converter.markdown_to_pdf(str(md))

        mock_html_cls.return_value.write_pdf.assert_called_once()

    def test_pandoc_exception_falls_through_to_weasyprint(self, tmp_path):
        """Après exception pandoc, essaie weasyprint."""
        md = tmp_path / "doc.md"
        md.write_text("# Hello", encoding="utf-8")

        mock_markdown_mod = MagicMock()
        mock_markdown_mod.markdown.return_value = "<h1>Hello</h1>"
        mock_html_cls = MagicMock()

        converter = _make_converter()
        with patch("utils.pdf_converter.shutil.which", return_value="/usr/bin/pandoc"), \
             patch("utils.pdf_converter.subprocess.run",
                   side_effect=Exception("pandoc crashed")), \
             patch.dict("sys.modules", {
                 "markdown": mock_markdown_mod,
                 "weasyprint": MagicMock(HTML=mock_html_cls),
             }):
            converter.markdown_to_pdf(str(md))

        mock_html_cls.return_value.write_pdf.assert_called_once()

    def test_weasyprint_success_no_pandoc(self, tmp_path):
        """Conversion weasyprint réussie sans pandoc."""
        md = tmp_path / "doc.md"
        md.write_text("# Hello", encoding="utf-8")

        mock_markdown_mod = MagicMock()
        mock_markdown_mod.markdown.return_value = "<h1>Hello</h1>"
        mock_html_cls = MagicMock()

        converter = _make_converter()
        with patch("utils.pdf_converter.shutil.which", return_value=None), \
             patch.dict("sys.modules", {
                 "markdown": mock_markdown_mod,
                 "weasyprint": MagicMock(HTML=mock_html_cls),
             }):
            result = converter.markdown_to_pdf(str(md))

        mock_html_cls.return_value.write_pdf.assert_called_once()
        assert result is not None

    def test_weasyprint_import_error_returns_none(self, tmp_path):
        """Retourne None si weasyprint n'est pas installé."""
        md = tmp_path / "doc.md"
        md.write_text("# Hello", encoding="utf-8")

        converter = _make_converter()
        with patch("utils.pdf_converter.shutil.which", return_value=None), \
             patch.dict("sys.modules", {"markdown": None, "weasyprint": None}):
            result = converter.markdown_to_pdf(str(md))

        assert result is None

    def test_weasyprint_exception_returns_none(self, tmp_path):
        """Retourne None si weasyprint lève une exception."""
        md = tmp_path / "doc.md"
        md.write_text("# Hello", encoding="utf-8")

        mock_markdown_mod = MagicMock()
        mock_markdown_mod.markdown.return_value = "<h1>Hello</h1>"
        mock_html_cls = MagicMock()
        mock_html_cls.return_value.write_pdf.side_effect = Exception("render error")

        converter = _make_converter()
        with patch("utils.pdf_converter.shutil.which", return_value=None), \
             patch.dict("sys.modules", {
                 "markdown": mock_markdown_mod,
                 "weasyprint": MagicMock(HTML=mock_html_cls),
             }):
            result = converter.markdown_to_pdf(str(md))

        assert result is None


# ---------------------------------------------------------------------------
# is_pdf_conversion_available
# ---------------------------------------------------------------------------


class TestIsPdfConversionAvailable:
    def test_both_unavailable(self):
        """Retourne False pour les deux si rien n'est installé."""
        converter = _make_converter(libreoffice_path=None)
        with patch("utils.pdf_converter.shutil.which", return_value=None), \
             patch.object(converter, "_has_weasyprint", return_value=False):
            result = converter.is_pdf_conversion_available()
        assert result["pptx_to_pdf"] is False
        assert result["markdown_to_pdf"] is False

    def test_pptx_available_markdown_not(self):
        """pptx_to_pdf True si libreoffice présent."""
        converter = _make_converter(libreoffice_path="/usr/bin/soffice")
        with patch("utils.pdf_converter.shutil.which", return_value=None), \
             patch.object(converter, "_has_weasyprint", return_value=False):
            result = converter.is_pdf_conversion_available()
        assert result["pptx_to_pdf"] is True
        assert result["markdown_to_pdf"] is False

    def test_markdown_available_via_pandoc(self):
        """markdown_to_pdf True si pandoc présent."""
        converter = _make_converter(libreoffice_path=None)
        with patch("utils.pdf_converter.shutil.which", return_value="/usr/bin/pandoc"), \
             patch.object(converter, "_has_weasyprint", return_value=False):
            result = converter.is_pdf_conversion_available()
        assert result["markdown_to_pdf"] is True

    def test_markdown_available_via_weasyprint(self):
        """markdown_to_pdf True si weasyprint présent."""
        converter = _make_converter(libreoffice_path=None)
        with patch("utils.pdf_converter.shutil.which", return_value=None), \
             patch.object(converter, "_has_weasyprint", return_value=True):
            result = converter.is_pdf_conversion_available()
        assert result["markdown_to_pdf"] is True

    def test_returns_dict_with_correct_keys(self):
        """Retourne un dict avec les bonnes clés."""
        converter = _make_converter()
        with patch("utils.pdf_converter.shutil.which", return_value=None), \
             patch.object(converter, "_has_weasyprint", return_value=False):
            result = converter.is_pdf_conversion_available()
        assert "pptx_to_pdf" in result
        assert "markdown_to_pdf" in result


# ---------------------------------------------------------------------------
# _has_weasyprint
# ---------------------------------------------------------------------------


class TestHasWeasyprint:
    def test_returns_true_when_installed(self):
        """Retourne True si weasyprint peut être importé."""
        with patch.dict("sys.modules", {"weasyprint": MagicMock()}):
            from utils.pdf_converter import PDFConverter
            result = PDFConverter._has_weasyprint()
        assert result is True

    def test_returns_false_when_not_installed(self):
        """Retourne False si weasyprint n'est pas installé."""
        with patch.dict("sys.modules", {"weasyprint": None}):
            from utils.pdf_converter import PDFConverter
            result = PDFConverter._has_weasyprint()
        assert result is False


# ---------------------------------------------------------------------------
# Module-level instance
# ---------------------------------------------------------------------------


class TestModuleLevelInstance:
    def test_global_instance_exists(self):
        """L'instance globale pdf_converter est créée au chargement du module."""
        from utils.pdf_converter import pdf_converter
        assert pdf_converter is not None

    def test_global_instance_has_branding(self):
        """L'instance globale a un attribut branding."""
        from utils.pdf_converter import pdf_converter
        assert hasattr(pdf_converter, "branding")

    def test_global_instance_has_libreoffice_path_attr(self):
        """L'instance globale a un attribut libreoffice_path."""
        from utils.pdf_converter import pdf_converter
        assert hasattr(pdf_converter, "libreoffice_path")
