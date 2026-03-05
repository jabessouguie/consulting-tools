"""
Tests pour utils/image_generator.py
Phase 5 - Coverage improvement
"""
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

os.environ.setdefault("AUTH_PASSWORD", "testpass")
os.environ.setdefault("SECRET_KEY", "testsecret")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")


# ---------------------------------------------------------------------------
# DiagramGenerator
# ---------------------------------------------------------------------------

class TestDiagramGeneratorInit:
    def test_creates_llm_client_when_none(self):
        # LLMClient is imported locally inside __init__; patch source module
        with patch("utils.llm_client.LLMClient") as MockLLM:
            from utils.image_generator import DiagramGenerator
            gen = DiagramGenerator()
        MockLLM.assert_called_once()

    def test_uses_provided_llm_client(self):
        mock_llm = MagicMock()
        from utils.image_generator import DiagramGenerator
        gen = DiagramGenerator(llm_client=mock_llm)
        assert gen.llm_client is mock_llm


class TestGenerateMermaidCode:
    @pytest.fixture()
    def gen(self, tmp_path):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "graph TD\nA --> B"
        with patch("utils.image_generator.Path") as MockPath:
            mock_dir = MagicMock()
            mock_dir.__truediv__ = lambda self, other: tmp_path / "arch.png"
            mock_dir.mkdir = MagicMock()
            MockPath.return_value.parent.parent.__truediv__ = lambda self, other: mock_dir
            from utils.image_generator import DiagramGenerator
            return DiagramGenerator(llm_client=mock_llm)

    def test_returns_string(self, gen):
        result = gen.generate_mermaid_code(
            "architecture", "API system", ["API", "DB"], {"client_name": "Corp"}
        )
        assert isinstance(result, str)

    def test_strips_mermaid_code_fence(self, gen):
        gen.llm_client.generate.return_value = "```mermaid\ngraph TD\nA-->B\n```"
        result = gen.generate_mermaid_code("flow", "Process", ["A", "B"], {})
        assert not result.startswith("```")

    def test_strips_plain_code_fence(self, gen):
        gen.llm_client.generate.return_value = "```\ngraph TD\nA-->B\n```"
        result = gen.generate_mermaid_code("flow", "Process", ["A", "B"], {})
        assert not result.startswith("```")

    def test_calls_llm(self, gen):
        gen.generate_mermaid_code("architecture", "Desc", ["A"], {})
        gen.llm_client.generate.assert_called_once()


class TestMermaidToPng:
    @pytest.fixture()
    def gen(self):
        mock_llm = MagicMock()
        with patch("utils.image_generator.Path") as MockPath:
            mock_dir = MagicMock()
            mock_dir.__truediv__ = lambda self, other: Path("/tmp/test.png")
            mock_dir.mkdir = MagicMock()
            MockPath.return_value.parent.parent.__truediv__ = lambda self, other: mock_dir
            from utils.image_generator import DiagramGenerator
            return DiagramGenerator(llm_client=mock_llm)

    def test_returns_false_when_mmdc_not_installed(self, gen):
        with patch("utils.image_generator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result = gen.mermaid_to_png("graph TD\nA-->B", "/tmp/out.png")
        assert result is False

    def test_returns_true_on_success(self, gen):
        with patch("utils.image_generator.subprocess.run") as mock_run, \
             patch("builtins.open", mock_open()), \
             patch("utils.image_generator.os.path.exists", return_value=True), \
             patch("utils.image_generator.os.remove"):
            # First call (which mmdc) → success
            # Second call (mmdc -i ...) → success
            mock_run.side_effect = [
                MagicMock(returncode=0),  # which mmdc
                MagicMock(returncode=0),  # mmdc convert
            ]
            result = gen.mermaid_to_png("graph TD\nA-->B", "/tmp/out.png")
        assert result is True

    def test_returns_false_on_timeout(self, gen):
        import subprocess
        with patch("utils.image_generator.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(["mmdc"], 30)
            result = gen.mermaid_to_png("graph TD\nA-->B", "/tmp/out.png")
        assert result is False

    def test_returns_false_on_mmdc_error(self, gen):
        with patch("utils.image_generator.subprocess.run") as mock_run, \
             patch("builtins.open", mock_open()), \
             patch("utils.image_generator.os.path.exists", return_value=False):
            mock_run.side_effect = [
                MagicMock(returncode=0),  # which mmdc
                MagicMock(returncode=1, stderr="Error"),  # mmdc convert fails
            ]
            result = gen.mermaid_to_png("graph TD\nA-->B", "/tmp/out.png")
        assert result is False

    def test_returns_false_on_exception(self, gen):
        with patch("utils.image_generator.subprocess.run", side_effect=Exception("unexpected")):
            result = gen.mermaid_to_png("graph TD\nA-->B", "/tmp/out.png")
        assert result is False


class TestDiagramGeneratorMethods:
    @pytest.fixture()
    def gen(self):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "graph TD\nA-->B"
        with patch("utils.image_generator.Path") as MockPath:
            mock_dir = MagicMock()
            mock_dir.__truediv__ = lambda self, other: Path("/tmp/test_arch.png")
            mock_dir.mkdir = MagicMock()
            MockPath.return_value.parent.parent.__truediv__ = lambda self, other: mock_dir
            from utils.image_generator import DiagramGenerator
            gen = DiagramGenerator(llm_client=mock_llm)
            gen.output_dir = Path("/tmp")
        return gen

    def test_generate_architecture_returns_path_on_success(self, gen):
        with patch.object(gen, "mermaid_to_png", return_value=True):
            result = gen.generate_architecture_diagram(["API", "DB"], {"client_name": "Corp"})
        assert result is not None
        assert ".png" in result

    def test_generate_architecture_returns_none_on_failure(self, gen):
        with patch.object(gen, "mermaid_to_png", return_value=False):
            result = gen.generate_architecture_diagram(["API"], {})
        assert result is None

    def test_generate_flow_returns_path_on_success(self, gen):
        with patch.object(gen, "mermaid_to_png", return_value=True):
            result = gen.generate_flow_diagram(["Step1", "Step2", "Step3"], {})
        assert result is not None

    def test_generate_flow_returns_none_on_failure(self, gen):
        with patch.object(gen, "mermaid_to_png", return_value=False):
            result = gen.generate_flow_diagram(["A", "B", "C"], {})
        assert result is None

    def test_generate_sequence_returns_path_on_success(self, gen):
        with patch.object(gen, "mermaid_to_png", return_value=True):
            result = gen.generate_sequence_diagram(["User", "API", "DB"], {})
        assert result is not None

    def test_generate_sequence_returns_none_on_failure(self, gen):
        with patch.object(gen, "mermaid_to_png", return_value=False):
            result = gen.generate_sequence_diagram(["A", "B"], {})
        assert result is None


# ---------------------------------------------------------------------------
# ImageGenerator
# ---------------------------------------------------------------------------

class TestImageGeneratorInit:
    def test_uses_api_key_arg(self):
        with patch("utils.image_generator.Path") as MockPath:
            mock_dir = MagicMock()
            mock_dir.mkdir = MagicMock()
            MockPath.return_value.parent.parent.__truediv__ = lambda self, other: mock_dir
            mock_dir.__truediv__ = lambda self, other: mock_dir
            from utils.image_generator import ImageGenerator
            gen = ImageGenerator(api_key="my-key")
        assert gen.api_key == "my-key"

    def test_reads_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        with patch("utils.image_generator.Path") as MockPath:
            mock_dir = MagicMock()
            mock_dir.mkdir = MagicMock()
            MockPath.return_value.parent.parent.__truediv__ = lambda self, other: mock_dir
            mock_dir.__truediv__ = lambda self, other: mock_dir
            from utils.image_generator import ImageGenerator
            gen = ImageGenerator()
        assert gen.api_key == "env-key"


class TestGenerateDiagramImage:
    @pytest.fixture()
    def gen(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with patch("utils.image_generator.Path") as MockPath:
            mock_dir = MagicMock()
            mock_dir.mkdir = MagicMock()
            mock_dir.__truediv__ = lambda self, other: Path("/tmp/test_img.png")
            MockPath.return_value.parent.parent.__truediv__ = lambda self, other: mock_dir
            from utils.image_generator import ImageGenerator
            g = ImageGenerator(api_key="test-key")
            g.output_dir = Path("/tmp")
        return g

    def test_returns_none_when_no_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with patch("utils.image_generator.Path") as MockPath:
            mock_dir = MagicMock()
            mock_dir.mkdir = MagicMock()
            mock_dir.__truediv__ = lambda self, other: mock_dir
            MockPath.return_value.parent.parent.__truediv__ = lambda self, other: mock_dir
            from utils.image_generator import ImageGenerator
            g = ImageGenerator()  # No api_key arg
        result = g.generate_diagram_image("Desc", {})
        assert result is None

    def test_returns_path_on_success(self, gen, tmp_path):
        gen.output_dir = tmp_path
        mock_img_response = MagicMock()
        mock_img_response.status_code = 200
        mock_img_response.content = b"PNG_DATA"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"url": "https://dalle.com/img.png"}]}

        with patch("utils.image_generator.requests.post", return_value=mock_response), \
             patch("utils.image_generator.requests.get", return_value=mock_img_response), \
             patch("builtins.open", mock_open()):
            result = gen.generate_diagram_image("Description", {"client_name": "Corp"})
        assert result is not None

    def test_returns_none_on_api_error(self, gen):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        with patch("utils.image_generator.requests.post", return_value=mock_response):
            result = gen.generate_diagram_image("Description", {})
        assert result is None

    def test_returns_none_on_exception(self, gen):
        with patch("utils.image_generator.requests.post", side_effect=Exception("network error")):
            result = gen.generate_diagram_image("Description", {})
        assert result is None

    def test_returns_none_when_image_download_fails(self, gen, tmp_path):
        gen.output_dir = tmp_path
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"url": "https://dalle.com/img.png"}]}

        mock_img_response = MagicMock()
        mock_img_response.status_code = 404

        with patch("utils.image_generator.requests.post", return_value=mock_response), \
             patch("utils.image_generator.requests.get", return_value=mock_img_response):
            result = gen.generate_diagram_image("Description", {})
        assert result is None

    def test_uses_modern_style_for_modern(self, gen):
        with patch.object(gen, "generate_diagram_image", return_value=None) as mock_gen:
            gen.generate_architecture_diagram(["API", "DB"], {"client_name": "C"})
        mock_gen.assert_called_once()
        # style is passed as keyword arg
        assert mock_gen.call_args[1].get("style") == "modern" or mock_gen.call_args[0][-1] == "modern"

    def test_generate_process_flowchart(self, gen):
        with patch.object(gen, "generate_diagram_image", return_value="/tmp/img.png") as mock_gen:
            result = gen.generate_process_flowchart(["Step1", "Step2"], {})
        assert result == "/tmp/img.png"

    def test_generate_data_visualization_dashboard(self, gen):
        with patch.object(gen, "generate_diagram_image", return_value="/tmp/img.png"):
            result = gen.generate_data_visualization("dashboard", {})
        assert result == "/tmp/img.png"

    def test_generate_data_visualization_unknown_uses_dashboard(self, gen):
        with patch.object(gen, "generate_diagram_image", return_value=None) as mock_gen:
            gen.generate_data_visualization("unknown_type", {})
        call_desc = mock_gen.call_args[0][0]
        assert "dashboard" in call_desc.lower() or "analytics" in call_desc.lower()


# ---------------------------------------------------------------------------
# ImageLibrary
# ---------------------------------------------------------------------------

class TestImageLibrary:
    @pytest.fixture()
    def lib(self, tmp_path):
        with patch("utils.image_generator.Path") as MockPath:
            lib_dir = tmp_path / "library"
            lib_dir.mkdir()
            catalog_file = lib_dir / "catalog.json"
            # The constructor accesses Path(...) / "data" / "images" / "library"
            MockPath.return_value.parent.parent.__truediv__ = lambda self, other: lib_dir
            mock_path_instance = MagicMock()
            mock_path_instance.__truediv__ = lambda self, other: lib_dir
            MockPath.return_value = mock_path_instance
            from utils.image_generator import ImageLibrary
            lib = ImageLibrary.__new__(ImageLibrary)
            lib.library_dir = lib_dir
            lib.catalog_file = catalog_file
            lib._load_catalog()
        return lib

    def test_load_catalog_creates_empty_when_missing(self, lib):
        assert "categories" in lib.catalog
        assert "images" in lib.catalog

    def test_load_catalog_reads_existing_file(self, tmp_path):
        from utils.image_generator import ImageLibrary
        lib = ImageLibrary.__new__(ImageLibrary)
        catalog_file = tmp_path / "catalog.json"
        existing = {"categories": {"arch": []}, "images": [{"filename": "a.png"}]}
        catalog_file.write_text(json.dumps(existing))
        lib.library_dir = tmp_path
        lib.catalog_file = catalog_file
        lib._load_catalog()
        assert lib.catalog["images"][0]["filename"] == "a.png"

    def test_search_images_all(self, lib):
        lib.catalog["images"] = [
            {"filename": "a.png", "category": "arch", "tags": ["tech"], "description": "API arch"},
            {"filename": "b.png", "category": "team", "tags": ["people"], "description": "Team"},
        ]
        results = lib.search_images()
        assert len(results) == 2

    def test_search_images_by_category(self, lib):
        lib.catalog["images"] = [
            {"filename": "a.png", "category": "arch", "tags": [], "description": ""},
            {"filename": "b.png", "category": "team", "tags": [], "description": ""},
        ]
        results = lib.search_images(category="arch")
        assert len(results) == 1
        assert results[0]["filename"] == "a.png"

    def test_search_images_by_tag(self, lib):
        lib.catalog["images"] = [
            {"filename": "a.png", "category": "arch", "tags": ["cloud"], "description": ""},
            {"filename": "b.png", "category": "arch", "tags": ["onprem"], "description": ""},
        ]
        results = lib.search_images(tags=["cloud"])
        assert len(results) == 1

    def test_search_images_by_keyword(self, lib):
        lib.catalog["images"] = [
            {"filename": "a.png", "category": "arch", "tags": [], "description": "machine learning pipeline"},
            {"filename": "b.png", "category": "arch", "tags": [], "description": "data warehouse"},
        ]
        results = lib.search_images(keyword="machine")
        assert len(results) == 1

    def test_get_image_by_category_returns_none_when_empty(self, lib):
        lib.catalog["images"] = []
        result = lib.get_image_by_category("nonexistent")
        assert result is None

    def test_get_image_by_category_returns_path(self, lib):
        lib.catalog["images"] = [
            {"filename": "a.png", "category": "arch", "tags": [], "description": "", "path": "/tmp/a.png"},
        ]
        lib.catalog["categories"] = {"arch": ["a.png"]}
        result = lib.get_image_by_category("arch")
        assert result == "/tmp/a.png"

    def test_list_categories(self, lib):
        lib.catalog["categories"] = {"arch": [], "team": [], "data": []}
        categories = lib.list_categories()
        assert set(categories) == {"arch", "team", "data"}

    def test_get_statistics(self, lib):
        lib.catalog = {
            "categories": {"arch": ["a.png", "b.png"], "team": ["c.png"]},
            "images": [{"f": "a"}, {"f": "b"}, {"f": "c"}],
        }
        stats = lib.get_statistics()
        assert stats["total_images"] == 3
        assert stats["categories"] == 2
        assert stats["by_category"]["arch"] == 2

    def test_add_image_raises_when_source_missing(self, lib):
        from utils.image_generator import ImageLibrary
        with pytest.raises(FileNotFoundError):
            lib.add_image("/nonexistent/image.png", "arch", ["tag"], "Desc")

    def test_add_image_copies_and_updates_catalog(self, lib, tmp_path):
        source = tmp_path / "source.png"
        source.write_bytes(b"PNG")
        with patch.object(lib, "_save_catalog"):
            result = lib.add_image(str(source), "arch", ["tag"], "Test image")
        assert lib.catalog["images"][-1]["category"] == "arch"
        assert "arch" in lib.catalog["categories"]


# ---------------------------------------------------------------------------
# NanoBananaGenerator
# ---------------------------------------------------------------------------

class TestNanoBananaGenerator:
    def test_init_sets_model_none_on_import_error(self):
        with patch.dict("sys.modules", {"google.generativeai": None}):
            from utils.image_generator import NanoBananaGenerator
            gen = NanoBananaGenerator()
        assert gen.model is None

    def test_init_sets_model_none_when_no_api_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        mock_genai = MagicMock()
        with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
            with patch("utils.image_generator.os.getenv", return_value=None):
                from utils.image_generator import NanoBananaGenerator
                gen = NanoBananaGenerator()
        assert gen.model is None

    def test_generate_image_returns_none_when_model_none(self):
        from utils.image_generator import NanoBananaGenerator
        gen = NanoBananaGenerator.__new__(NanoBananaGenerator)
        gen.model = None
        result = gen.generate_image("prompt", "/tmp/out.png")
        assert result is None

    def test_generate_image_returns_none_on_exception(self):
        from utils.image_generator import NanoBananaGenerator
        gen = NanoBananaGenerator.__new__(NanoBananaGenerator)
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API error")
        gen.model = mock_model
        result = gen.generate_image("prompt", "/tmp/out.png")
        assert result is None

    def test_generate_article_illustration_calls_generate_image(self):
        from utils.image_generator import NanoBananaGenerator
        gen = NanoBananaGenerator.__new__(NanoBananaGenerator)
        gen.model = None
        result = gen.generate_article_illustration("Article text about AI", "/tmp/out.png")
        assert result is None
