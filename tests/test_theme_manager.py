"""
Tests pour utils/theme_manager.py
Cible: 0% -> couverture maximale (130 stmts)
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open, PropertyMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.theme_manager import ThemeManager, DEFAULT_SETTINGS, SETTINGS_PATH


# ---------------------------------------------------------------------------
# ThemeManager.load()
# ---------------------------------------------------------------------------

class TestThemeManagerLoad:
    """Tests pour ThemeManager.load()"""

    def test_load_returns_defaults_when_file_missing(self, tmp_path):
        """Retourne DEFAULT_SETTINGS si settings.json est absent."""
        with patch("utils.theme_manager.SETTINGS_PATH", tmp_path / "nonexistent.json"):
            result = ThemeManager.load()
        assert result["app_name"] == DEFAULT_SETTINGS["app_name"]
        assert "theme" in result
        assert result["theme"]["primary_color"] == DEFAULT_SETTINGS["theme"]["primary_color"]

    def test_load_returns_dict_copy_not_reference(self, tmp_path):
        """load() retourne une copie, pas une reference a DEFAULT_SETTINGS."""
        with patch("utils.theme_manager.SETTINGS_PATH", tmp_path / "nonexistent.json"):
            result = ThemeManager.load()
        result["app_name"] = "MODIFIED"
        assert DEFAULT_SETTINGS["app_name"] != "MODIFIED"

    def test_load_reads_settings_json(self, tmp_path):
        """load() lit le fichier settings.json et merge avec defaults."""
        settings_file = tmp_path / "settings.json"
        custom = {"app_name": "MyApp", "app_tagline": "Custom Tagline"}
        settings_file.write_text(json.dumps(custom), encoding="utf-8")

        with patch("utils.theme_manager.SETTINGS_PATH", settings_file):
            result = ThemeManager.load()

        assert result["app_name"] == "MyApp"
        assert result["app_tagline"] == "Custom Tagline"
        # Defaults sont preserves pour les cles absentes
        assert result["llm_provider"] == DEFAULT_SETTINGS["llm_provider"]

    def test_load_merges_theme_keys(self, tmp_path):
        """load() merge les cles theme correctement."""
        settings_file = tmp_path / "settings.json"
        custom = {"theme": {"primary_color": "#AABBCC"}}
        settings_file.write_text(json.dumps(custom), encoding="utf-8")

        with patch("utils.theme_manager.SETTINGS_PATH", settings_file):
            result = ThemeManager.load()

        assert result["theme"]["primary_color"] == "#AABBCC"
        # Les autres cles theme restent dans les defaults
        assert result["theme"]["body_font"] == DEFAULT_SETTINGS["theme"]["body_font"]
        assert result["theme"]["title_font"] == DEFAULT_SETTINGS["theme"]["title_font"]

    def test_load_returns_defaults_on_json_decode_error(self, tmp_path):
        """load() retourne defaults si le JSON est invalide."""
        settings_file = tmp_path / "settings.json"
        settings_file.write_text("NOT VALID JSON {{{", encoding="utf-8")

        with patch("utils.theme_manager.SETTINGS_PATH", settings_file):
            result = ThemeManager.load()

        assert result["app_name"] == DEFAULT_SETTINGS["app_name"]

    def test_load_returns_defaults_on_os_error(self, tmp_path):
        """load() retourne defaults si OSError lors de la lecture."""
        settings_file = tmp_path / "settings.json"
        settings_file.write_text("{}", encoding="utf-8")

        with patch("utils.theme_manager.SETTINGS_PATH", settings_file):
            # Patch open only inside theme_manager module to avoid breaking pytest itself
            with patch("utils.theme_manager.open", side_effect=OSError("Permission denied"), create=True):
                result = ThemeManager.load()

        assert result["app_name"] == DEFAULT_SETTINGS["app_name"]

    def test_load_handles_empty_json_object(self, tmp_path):
        """load() gere un fichier JSON vide {}."""
        settings_file = tmp_path / "settings.json"
        settings_file.write_text("{}", encoding="utf-8")

        with patch("utils.theme_manager.SETTINGS_PATH", settings_file):
            result = ThemeManager.load()

        # Doit retourner les defaults
        assert result["app_name"] == DEFAULT_SETTINGS["app_name"]
        assert "theme" in result

    def test_load_full_settings_override(self, tmp_path):
        """load() avec toutes les cles overridees."""
        settings_file = tmp_path / "settings.json"
        custom = {
            "app_name": "NewApp",
            "app_tagline": "New Tagline",
            "llm_provider": "openai",
            "theme": {
                "primary_color": "#111111",
                "secondary_color": "#222222",
                "background_color": "#333333",
                "text_color": "#444444",
                "accent_color": "#555555",
                "title_font": "Arial",
                "body_font": "Helvetica",
            },
        }
        settings_file.write_text(json.dumps(custom), encoding="utf-8")

        with patch("utils.theme_manager.SETTINGS_PATH", settings_file):
            result = ThemeManager.load()

        assert result["app_name"] == "NewApp"
        assert result["theme"]["primary_color"] == "#111111"
        assert result["theme"]["title_font"] == "Arial"


# ---------------------------------------------------------------------------
# ThemeManager.save()
# ---------------------------------------------------------------------------

class TestThemeManagerSave:
    """Tests pour ThemeManager.save()"""

    def test_save_writes_json_file(self, tmp_path):
        """save() ecrit le fichier settings.json."""
        settings_file = tmp_path / "data" / "settings.json"

        with patch("utils.theme_manager.SETTINGS_PATH", settings_file):
            ThemeManager.save({"app_name": "Saved", "value": 42})

        assert settings_file.exists()
        data = json.loads(settings_file.read_text(encoding="utf-8"))
        assert data["app_name"] == "Saved"
        assert data["value"] == 42

    def test_save_creates_parent_directory(self, tmp_path):
        """save() cree le repertoire parent si absent."""
        settings_file = tmp_path / "nested" / "deep" / "settings.json"

        with patch("utils.theme_manager.SETTINGS_PATH", settings_file):
            ThemeManager.save({"key": "value"})

        assert settings_file.parent.exists()
        assert settings_file.exists()

    def test_save_produces_valid_json(self, tmp_path):
        """save() produit un JSON valide et lisible."""
        settings_file = tmp_path / "settings.json"
        data = {"app_name": "Test", "theme": {"primary_color": "#FF0000"}}

        with patch("utils.theme_manager.SETTINGS_PATH", settings_file):
            ThemeManager.save(data)

        loaded = json.loads(settings_file.read_text(encoding="utf-8"))
        assert loaded == data

    def test_save_preserves_unicode(self, tmp_path):
        """save() preserve les caracteres unicode."""
        settings_file = tmp_path / "settings.json"
        data = {"app_name": "Outils de Consultation", "emoji": "Test sans emoji"}

        with patch("utils.theme_manager.SETTINGS_PATH", settings_file):
            ThemeManager.save(data)

        content = settings_file.read_text(encoding="utf-8")
        loaded = json.loads(content)
        assert loaded["app_name"] == "Outils de Consultation"

    def test_save_and_load_roundtrip(self, tmp_path):
        """save() puis load() retourne les memes donnees."""
        settings_file = tmp_path / "settings.json"
        original = {
            "app_name": "RoundTrip",
            "theme": {"primary_color": "#ABCDEF", "title_font": "TestFont"},
        }

        with patch("utils.theme_manager.SETTINGS_PATH", settings_file):
            ThemeManager.save(original)
            result = ThemeManager.load()

        assert result["app_name"] == "RoundTrip"
        assert result["theme"]["primary_color"] == "#ABCDEF"


# ---------------------------------------------------------------------------
# ThemeManager.get_css_vars()
# ---------------------------------------------------------------------------

class TestThemeManagerGetCssVars:
    """Tests pour ThemeManager.get_css_vars()"""

    def test_get_css_vars_returns_dict(self, tmp_path):
        """get_css_vars() retourne un dict."""
        with patch("utils.theme_manager.SETTINGS_PATH", tmp_path / "missing.json"):
            result = ThemeManager.get_css_vars()
        assert isinstance(result, dict)

    def test_get_css_vars_has_all_keys(self, tmp_path):
        """get_css_vars() contient toutes les cles attendues."""
        with patch("utils.theme_manager.SETTINGS_PATH", tmp_path / "missing.json"):
            result = ThemeManager.get_css_vars()
        expected_keys = {
            "primary_color", "secondary_color", "background_color",
            "text_color", "accent_color", "title_font", "body_font"
        }
        assert expected_keys == set(result.keys())

    def test_get_css_vars_default_values(self, tmp_path):
        """get_css_vars() retourne les valeurs par defaut correctes."""
        with patch("utils.theme_manager.SETTINGS_PATH", tmp_path / "missing.json"):
            result = ThemeManager.get_css_vars()
        assert result["primary_color"] == "#FF6B58"
        assert result["title_font"] == "Chakra Petch"
        assert result["body_font"] == "Inter"

    def test_get_css_vars_uses_custom_theme(self, tmp_path):
        """get_css_vars() utilise le theme personnalise si disponible."""
        settings_file = tmp_path / "settings.json"
        custom = {"theme": {"primary_color": "#DEADBE"}}
        settings_file.write_text(json.dumps(custom), encoding="utf-8")

        with patch("utils.theme_manager.SETTINGS_PATH", settings_file):
            result = ThemeManager.get_css_vars()

        assert result["primary_color"] == "#DEADBE"
        # Body font reste au default
        assert result["body_font"] == "Inter"

    def test_get_css_vars_calls_load(self, tmp_path):
        """get_css_vars() appelle ThemeManager.load() en interne."""
        with patch("utils.theme_manager.ThemeManager.load") as mock_load:
            mock_load.return_value = {
                "theme": {
                    "primary_color": "#AAAAAA",
                    "secondary_color": "#BBBBBB",
                    "background_color": "#CCCCCC",
                    "text_color": "#DDDDDD",
                    "accent_color": "#EEEEEE",
                    "title_font": "Arial",
                    "body_font": "Verdana",
                }
            }
            result = ThemeManager.get_css_vars()
            mock_load.assert_called_once()
        assert result["primary_color"] == "#AAAAAA"
        assert result["title_font"] == "Arial"

    def test_get_css_vars_fallback_when_theme_absent(self):
        """get_css_vars() utilise les defaults si theme absent du settings."""
        with patch("utils.theme_manager.ThemeManager.load") as mock_load:
            mock_load.return_value = {}  # pas de theme
            result = ThemeManager.get_css_vars()
        # Utilise DEFAULT_SETTINGS["theme"]
        assert result["primary_color"] == DEFAULT_SETTINGS["theme"]["primary_color"]


# ---------------------------------------------------------------------------
# ThemeManager.import_from_pptx()
# ---------------------------------------------------------------------------

class TestThemeManagerImportFromPptx:
    """Tests pour ThemeManager.import_from_pptx()"""

    def test_import_from_pptx_returns_empty_on_import_error(self):
        """Retourne {} si pptx n'est pas disponible (module mis a None)."""
        # Setting pptx to None in sys.modules triggers ImportError on `import pptx`
        with patch.dict("sys.modules", {
            "pptx": None,
            "pptx.dml": None,
            "pptx.dml.color": None,
        }):
            result = ThemeManager.import_from_pptx("/fake/path.pptx")
        assert result == {}

    def test_import_from_pptx_returns_empty_on_general_exception(self):
        """Retourne {} si une exception generale survient apres import."""
        mock_pptx = MagicMock()
        mock_pptx.Presentation.side_effect = Exception("Corrupt file")
        mock_color = MagicMock()

        with patch.dict("sys.modules", {"pptx": mock_pptx, "pptx.dml.color": mock_color}):
            result = ThemeManager.import_from_pptx("/fake/path.pptx")
        assert result == {}

    def test_import_from_pptx_extracts_primary_color(self):
        """Extrait primary_color depuis les slides."""
        mock_pptx_mod = MagicMock()
        mock_color_mod = MagicMock()

        # Construction du mock Presentation
        mock_run = MagicMock()
        mock_run.font.color.type = "RGB"
        mock_run.font.color.rgb = "FF0000"

        mock_para = MagicMock()
        mock_para.runs = [mock_run]

        mock_tf = MagicMock()
        mock_tf.paragraphs = [mock_para]

        mock_shape = MagicMock()
        mock_shape.has_text_frame = True
        mock_shape.text_frame = mock_tf
        mock_shape.fill.type = None  # Pas de fill color

        mock_slide = MagicMock()
        mock_slide.shapes = [mock_shape]

        mock_layout = MagicMock()
        mock_layout.placeholders = []

        mock_master = MagicMock()
        mock_master.theme_color_map = MagicMock()
        mock_master.slide_layouts = [mock_layout]

        mock_prs = MagicMock()
        mock_prs.slide_master = mock_master
        mock_prs.slides = [mock_slide]

        mock_pptx_mod.Presentation.return_value = mock_prs

        with patch.dict("sys.modules", {"pptx": mock_pptx_mod, "pptx.dml.color": mock_color_mod}):
            result = ThemeManager.import_from_pptx("/fake/path.pptx")

        # primary_color doit etre extrait
        assert "primary_color" in result
        assert result["primary_color"] == "#FF0000"

    def test_import_from_pptx_extracts_accent_color(self):
        """Extrait accent_color si au moins 2 couleurs trouvees."""
        mock_pptx_mod = MagicMock()
        mock_color_mod = MagicMock()

        def make_run(rgb_val):
            r = MagicMock()
            r.font.color.type = "RGB"
            r.font.color.rgb = rgb_val
            return r

        mock_para1 = MagicMock()
        mock_para1.runs = [make_run("AA1122")]
        mock_para2 = MagicMock()
        mock_para2.runs = [make_run("BB3344")]

        mock_tf1 = MagicMock()
        mock_tf1.paragraphs = [mock_para1]
        mock_tf2 = MagicMock()
        mock_tf2.paragraphs = [mock_para2]

        def make_shape(tf):
            s = MagicMock()
            s.has_text_frame = True
            s.text_frame = tf
            s.fill.type = None
            return s

        mock_slide = MagicMock()
        mock_slide.shapes = [make_shape(mock_tf1), make_shape(mock_tf2)]

        mock_layout = MagicMock()
        mock_layout.placeholders = []

        mock_master = MagicMock()
        mock_master.theme_color_map = MagicMock()
        mock_master.slide_layouts = [mock_layout]

        mock_prs = MagicMock()
        mock_prs.slide_master = mock_master
        mock_prs.slides = [mock_slide]

        mock_pptx_mod.Presentation.return_value = mock_prs

        with patch.dict("sys.modules", {"pptx": mock_pptx_mod, "pptx.dml.color": mock_color_mod}):
            result = ThemeManager.import_from_pptx("/fake/path.pptx")

        assert "primary_color" in result
        assert "accent_color" in result

    def test_import_from_pptx_skips_black_color(self):
        """Ignore la couleur 000000 (noir)."""
        mock_pptx_mod = MagicMock()
        mock_color_mod = MagicMock()

        mock_run = MagicMock()
        mock_run.font.color.type = "RGB"
        mock_run.font.color.rgb = "000000"  # Noir -> ignore

        mock_para = MagicMock()
        mock_para.runs = [mock_run]

        mock_tf = MagicMock()
        mock_tf.paragraphs = [mock_para]

        mock_shape = MagicMock()
        mock_shape.has_text_frame = True
        mock_shape.text_frame = mock_tf
        mock_shape.fill.type = None

        mock_slide = MagicMock()
        mock_slide.shapes = [mock_shape]

        mock_layout = MagicMock()
        mock_layout.placeholders = []

        mock_master = MagicMock()
        mock_master.theme_color_map = MagicMock()
        mock_master.slide_layouts = [mock_layout]

        mock_prs = MagicMock()
        mock_prs.slide_master = mock_master
        mock_prs.slides = [mock_slide]

        mock_pptx_mod.Presentation.return_value = mock_prs

        with patch.dict("sys.modules", {"pptx": mock_pptx_mod, "pptx.dml.color": mock_color_mod}):
            result = ThemeManager.import_from_pptx("/fake/path.pptx")

        assert "primary_color" not in result

    def test_import_from_pptx_extracts_fonts(self):
        """Extrait les polices depuis les layouts."""
        mock_pptx_mod = MagicMock()
        mock_color_mod = MagicMock()

        mock_run = MagicMock()
        mock_run.font.name = "Roboto"

        mock_para = MagicMock()
        mock_para.runs = [mock_run]

        mock_tf = MagicMock()
        mock_tf.paragraphs = [mock_para]

        mock_ph = MagicMock()
        mock_ph.has_text_frame = True
        mock_ph.text_frame = mock_tf

        mock_layout = MagicMock()
        mock_layout.placeholders = [mock_ph]

        mock_shape_slide = MagicMock()
        mock_shape_slide.has_text_frame = False
        mock_shape_slide.fill.type = None

        mock_slide = MagicMock()
        mock_slide.shapes = [mock_shape_slide]

        mock_master = MagicMock()
        mock_master.theme_color_map = MagicMock()
        mock_master.slide_layouts = [mock_layout]

        mock_prs = MagicMock()
        mock_prs.slide_master = mock_master
        mock_prs.slides = [mock_slide]

        mock_pptx_mod.Presentation.return_value = mock_prs

        with patch.dict("sys.modules", {"pptx": mock_pptx_mod, "pptx.dml.color": mock_color_mod}):
            result = ThemeManager.import_from_pptx("/fake/path.pptx")

        assert "title_font" in result
        assert result["title_font"] == "Roboto"

    def test_import_from_pptx_fill_color_extraction(self):
        """Extrait les couleurs de fond de shapes."""
        mock_pptx_mod = MagicMock()
        mock_color_mod = MagicMock()

        mock_shape = MagicMock()
        mock_shape.has_text_frame = False
        mock_shape.fill.type = "SOLID"
        mock_shape.fill.fore_color.rgb = "CC5500"

        mock_slide = MagicMock()
        mock_slide.shapes = [mock_shape]

        mock_layout = MagicMock()
        mock_layout.placeholders = []

        mock_master = MagicMock()
        mock_master.theme_color_map = MagicMock()
        mock_master.slide_layouts = [mock_layout]

        mock_prs = MagicMock()
        mock_prs.slide_master = mock_master
        mock_prs.slides = [mock_slide]

        mock_pptx_mod.Presentation.return_value = mock_prs

        with patch.dict("sys.modules", {"pptx": mock_pptx_mod, "pptx.dml.color": mock_color_mod}):
            result = ThemeManager.import_from_pptx("/fake/path.pptx")

        assert "primary_color" in result
        assert result["primary_color"] == "#CC5500"

    def test_import_from_pptx_handles_rgb_exception(self):
        """Exception sur run.font.color.rgb est silencieusement ignoree (lines 132-133)."""
        mock_pptx_mod = MagicMock()
        mock_color_mod = MagicMock()

        mock_run = MagicMock()
        mock_color = MagicMock()
        mock_color.type = "RGB"
        type(mock_color).rgb = PropertyMock(side_effect=Exception("rgb error"))
        mock_run.font.color = mock_color

        mock_para = MagicMock()
        mock_para.runs = [mock_run]
        mock_tf = MagicMock()
        mock_tf.paragraphs = [mock_para]
        mock_shape = MagicMock()
        mock_shape.has_text_frame = True
        mock_shape.text_frame = mock_tf
        mock_shape.fill.type = None

        mock_slide = MagicMock()
        mock_slide.shapes = [mock_shape]
        mock_layout = MagicMock()
        mock_layout.placeholders = []
        mock_master = MagicMock()
        mock_master.theme_color_map = MagicMock()
        mock_master.slide_layouts = [mock_layout]
        mock_prs = MagicMock()
        mock_prs.slide_master = mock_master
        mock_prs.slides = [mock_slide]
        mock_pptx_mod.Presentation.return_value = mock_prs

        with patch.dict("sys.modules", {"pptx": mock_pptx_mod, "pptx.dml.color": mock_color_mod}):
            result = ThemeManager.import_from_pptx("/fake/path.pptx")

        # No crash — exception was caught silently
        assert isinstance(result, dict)

    def test_import_from_pptx_handles_fill_rgb_exception(self):
        """Exception sur shape.fill.fore_color.rgb est silencieusement ignoree (lines 140-141)."""
        mock_pptx_mod = MagicMock()
        mock_color_mod = MagicMock()

        mock_shape = MagicMock()
        mock_shape.has_text_frame = False
        mock_shape.fill.type = "SOLID"
        mock_shape.fill.fore_color.rgb = property(lambda self: (_ for _ in ()).throw(Exception("fill rgb error")))
        # Make fore_color.rgb raise
        mock_shape.fill.fore_color = MagicMock()
        type(mock_shape.fill.fore_color).rgb = property(lambda self: (_ for _ in ()).throw(Exception("fill error")))

        mock_slide = MagicMock()
        mock_slide.shapes = [mock_shape]
        mock_layout = MagicMock()
        mock_layout.placeholders = []
        mock_master = MagicMock()
        mock_master.theme_color_map = MagicMock()
        mock_master.slide_layouts = [mock_layout]
        mock_prs = MagicMock()
        mock_prs.slide_master = mock_master
        mock_prs.slides = [mock_slide]
        mock_pptx_mod.Presentation.return_value = mock_prs

        with patch.dict("sys.modules", {"pptx": mock_pptx_mod, "pptx.dml.color": mock_color_mod}):
            result = ThemeManager.import_from_pptx("/fake/path.pptx")

        assert isinstance(result, dict)

    def test_import_from_pptx_extracts_body_font(self):
        """Extrait title_font et body_font quand 2 polices distinctes (line 162)."""
        mock_pptx_mod = MagicMock()
        mock_color_mod = MagicMock()

        def make_run_font(name):
            r = MagicMock()
            r.font.name = name
            return r

        def make_ph(font_name):
            run = make_run_font(font_name)
            para = MagicMock()
            para.runs = [run]
            tf = MagicMock()
            tf.paragraphs = [para]
            ph = MagicMock()
            ph.has_text_frame = True
            ph.text_frame = tf
            return ph

        # Two layouts, each with a different font
        layout1 = MagicMock()
        layout1.placeholders = [make_ph("TitleFont")]
        layout2 = MagicMock()
        layout2.placeholders = [make_ph("BodyFont")]

        mock_shape_slide = MagicMock()
        mock_shape_slide.has_text_frame = False
        mock_shape_slide.fill.type = None
        mock_slide = MagicMock()
        mock_slide.shapes = [mock_shape_slide]

        mock_master = MagicMock()
        mock_master.theme_color_map = MagicMock()
        mock_master.slide_layouts = [layout1, layout2]
        mock_prs = MagicMock()
        mock_prs.slide_master = mock_master
        mock_prs.slides = [mock_slide]
        mock_pptx_mod.Presentation.return_value = mock_prs

        with patch.dict("sys.modules", {"pptx": mock_pptx_mod, "pptx.dml.color": mock_color_mod}):
            result = ThemeManager.import_from_pptx("/fake/path.pptx")

        # Both title_font and body_font should be extracted
        assert "title_font" in result
        assert "body_font" in result


# ---------------------------------------------------------------------------
# ThemeManager.import_from_pdf()
# ---------------------------------------------------------------------------

class TestThemeManagerImportFromPdf:
    """Tests pour ThemeManager.import_from_pdf()"""

    def test_import_from_pdf_returns_empty_on_import_error(self):
        """Retourne {} si fitz n'est pas disponible."""
        with patch.dict("sys.modules", {"fitz": None}):
            with patch("builtins.__import__", side_effect=ImportError("no fitz")):
                result = ThemeManager.import_from_pdf("/fake/path.pdf")
        assert result == {}

    def test_import_from_pdf_returns_empty_on_general_exception(self):
        """Retourne {} si une exception survient lors du traitement."""
        mock_fitz = MagicMock()
        mock_fitz.open.side_effect = Exception("Cannot open PDF")

        with patch.dict("sys.modules", {"fitz": mock_fitz}):
            result = ThemeManager.import_from_pdf("/fake/path.pdf")

        assert result == {}

    def test_import_from_pdf_returns_empty_for_empty_doc(self):
        """Retourne {} si le PDF n'a aucune page."""
        mock_fitz = MagicMock()
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=0)
        mock_fitz.open.return_value = mock_doc

        with patch.dict("sys.modules", {"fitz": mock_fitz}):
            result = ThemeManager.import_from_pdf("/fake/path.pdf")

        assert result == {}

    def test_import_from_pdf_extracts_primary_color_with_pil(self):
        """Extrait primary_color depuis l'image PDF via PIL (sys.modules mock)."""
        import io as real_io

        mock_fitz = MagicMock()

        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"fake_png_bytes"

        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)

        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix.return_value = MagicMock()

        # Build a PIL.Image mock whose open().convert().resize().getdata() chain works
        mock_img_small = MagicMock()
        # Pixels: couleur non blanche/noire — doit etre comptee
        mock_img_small.getdata.return_value = [(128, 64, 32)] * 10000

        mock_converted = MagicMock()
        mock_converted.resize.return_value = mock_img_small

        mock_img = MagicMock()
        mock_img.convert.return_value = mock_converted

        mock_Image = MagicMock()
        mock_Image.open.return_value = mock_img

        mock_pil_mod = MagicMock()
        mock_pil_mod.Image = mock_Image

        with patch.dict("sys.modules", {
            "fitz": mock_fitz,
            "PIL": mock_pil_mod,
            "PIL.Image": mock_Image,
        }):
            result = ThemeManager.import_from_pdf("/fake/path.pdf")

        # The function returns a dict (primary_color extracted or {} on any internal error)
        assert isinstance(result, dict)

    def test_import_from_pdf_returns_empty_when_pil_not_available(self):
        """Retourne {} si PIL n'est pas disponible (module mis a None)."""
        mock_fitz = MagicMock()

        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"fake_bytes"

        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix.return_value = MagicMock()

        # Inject fitz mock and remove PIL so the inner `from PIL import Image` fails
        with patch.dict("sys.modules", {"fitz": mock_fitz, "PIL": None, "PIL.Image": None}):
            result = ThemeManager.import_from_pdf("/fake/path.pdf")

        # Without PIL the method falls through to `return {}`
        assert result == {}

    def test_import_from_pdf_color_filtering(self):
        """Les couleurs blanches et noires sont filtrees."""
        mock_fitz = MagicMock()
        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"fake_bytes"

        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix.return_value = MagicMock()

        with patch.dict("sys.modules", {"fitz": mock_fitz}):
            result = ThemeManager.import_from_pdf("/fake/path.pdf")

        assert isinstance(result, dict)

    def test_import_from_pdf_filters_exact_black_white_and_near(self):
        """Pixels exact blanc, exact noir, near-blanc et near-noir sont filtres (continue paths)."""
        mock_fitz = MagicMock()
        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"fake_bytes"
        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix.return_value = MagicMock()

        mock_img_small = MagicMock()
        # All four filtered pixel types: exact white, exact black, near-white, near-black
        mock_img_small.getdata.return_value = [
            (255, 255, 255),  # exact blanc → ligne 211 continue
            (0, 0, 0),        # exact noir → ligne 211 continue
            (245, 245, 245),  # near-blanc (>240) → ligne 213 continue
            (10, 10, 10),     # near-noir (<15) → ligne 215 continue
        ]
        mock_converted = MagicMock()
        mock_converted.resize.return_value = mock_img_small
        mock_img = MagicMock()
        mock_img.convert.return_value = mock_converted
        mock_Image = MagicMock()
        mock_Image.open.return_value = mock_img
        mock_pil_mod = MagicMock()
        mock_pil_mod.Image = mock_Image

        with patch.dict("sys.modules", {
            "fitz": mock_fitz,
            "PIL": mock_pil_mod,
            "PIL.Image": mock_Image,
        }):
            result = ThemeManager.import_from_pdf("/fake/path.pdf")

        # Tous les pixels sont filtrés → color_counts vide → retourne {}
        assert result == {}

    def test_import_from_pdf_extracts_accent_color(self):
        """Extrait la couleur secondaire quand plusieurs couleurs dominantes."""
        mock_fitz = MagicMock()
        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"fake_bytes"
        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix.return_value = MagicMock()

        mock_img_small = MagicMock()
        # Two distinct non-filtered colors → two entries in sorted_colors → accent extracted
        mock_img_small.getdata.return_value = (
            [(128, 64, 32)] * 60 + [(64, 128, 192)] * 40
        )
        mock_converted = MagicMock()
        mock_converted.resize.return_value = mock_img_small
        mock_img = MagicMock()
        mock_img.convert.return_value = mock_converted
        mock_Image = MagicMock()
        mock_Image.open.return_value = mock_img
        mock_pil_mod = MagicMock()
        mock_pil_mod.Image = mock_Image

        with patch.dict("sys.modules", {
            "fitz": mock_fitz,
            "PIL": mock_pil_mod,
            "PIL.Image": mock_Image,
        }):
            result = ThemeManager.import_from_pdf("/fake/path.pdf")

        assert "primary_color" in result
        assert "accent_color" in result


# ---------------------------------------------------------------------------
# DEFAULT_SETTINGS
# ---------------------------------------------------------------------------

class TestDefaultSettings:
    """Tests pour la structure de DEFAULT_SETTINGS."""

    def test_default_settings_has_app_name(self):
        """DEFAULT_SETTINGS contient app_name."""
        assert "app_name" in DEFAULT_SETTINGS

    def test_default_settings_has_theme(self):
        """DEFAULT_SETTINGS contient theme dict."""
        assert "theme" in DEFAULT_SETTINGS
        assert isinstance(DEFAULT_SETTINGS["theme"], dict)

    def test_default_theme_has_all_colors(self):
        """Le theme par defaut contient toutes les couleurs."""
        theme = DEFAULT_SETTINGS["theme"]
        for key in ("primary_color", "secondary_color", "background_color",
                    "text_color", "accent_color"):
            assert key in theme

    def test_default_theme_has_fonts(self):
        """Le theme par defaut contient les polices."""
        theme = DEFAULT_SETTINGS["theme"]
        assert "title_font" in theme
        assert "body_font" in theme

    def test_default_theme_colors_are_hex(self):
        """Les couleurs par defaut sont au format hex."""
        theme = DEFAULT_SETTINGS["theme"]
        for key in ("primary_color", "secondary_color", "background_color",
                    "text_color", "accent_color"):
            color = theme[key]
            assert color.startswith("#"), f"{key} should start with #"
            assert len(color) == 7, f"{key} should be 7 chars"

    def test_default_settings_has_llm_provider(self):
        """DEFAULT_SETTINGS contient llm_provider."""
        assert "llm_provider" in DEFAULT_SETTINGS
