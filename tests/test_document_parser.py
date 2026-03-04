"""
Tests unitaires pour utils/document_parser.py
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.document_parser import DocumentParser, document_parser


# ---------------------------------------------------------------------------
# parse_file — routing
# ---------------------------------------------------------------------------


class TestParseFileRouting:
    def test_returns_none_for_nonexistent_file(self, tmp_path):
        missing = str(tmp_path / "missing.txt")
        result = DocumentParser.parse_file(missing)
        assert result is None

    def test_routes_txt_to_parse_text(self, tmp_path):
        f = tmp_path / "sample.txt"
        f.write_text("Hello world")
        result = DocumentParser.parse_file(str(f))
        assert result == "Hello world"

    def test_routes_md_to_parse_text(self, tmp_path):
        f = tmp_path / "sample.md"
        f.write_text("# Title\nContent")
        result = DocumentParser.parse_file(str(f))
        assert "Title" in result

    def test_routes_markdown_extension(self, tmp_path):
        f = tmp_path / "sample.markdown"
        f.write_text("markdown content")
        result = DocumentParser.parse_file(str(f))
        assert result == "markdown content"

    def test_routes_pdf_calls_parse_pdf(self, tmp_path):
        f = tmp_path / "sample.pdf"
        f.write_bytes(b"%PDF-1.4 fake content")
        with patch.object(DocumentParser, "_parse_pdf", return_value="pdf text") as mock_pdf:
            result = DocumentParser.parse_file(str(f))
        mock_pdf.assert_called_once()
        assert result == "pdf text"

    def test_routes_docx_calls_parse_docx(self, tmp_path):
        f = tmp_path / "sample.docx"
        f.write_bytes(b"PK fake docx")
        with patch.object(DocumentParser, "_parse_docx", return_value="docx text") as mock_docx:
            result = DocumentParser.parse_file(str(f))
        mock_docx.assert_called_once()
        assert result == "docx text"

    def test_routes_doc_calls_parse_docx(self, tmp_path):
        f = tmp_path / "sample.doc"
        f.write_bytes(b"fake doc")
        with patch.object(DocumentParser, "_parse_docx", return_value="doc text") as mock_docx:
            result = DocumentParser.parse_file(str(f))
        mock_docx.assert_called_once()
        assert result == "doc text"

    def test_unsupported_format_returns_none(self, tmp_path):
        f = tmp_path / "sample.xyz"
        f.write_text("data")
        result = DocumentParser.parse_file(str(f))
        assert result is None

    def test_extension_case_insensitive(self, tmp_path):
        f = tmp_path / "sample.TXT"
        f.write_text("uppercase extension")
        result = DocumentParser.parse_file(str(f))
        assert result == "uppercase extension"


# ---------------------------------------------------------------------------
# _parse_text
# ---------------------------------------------------------------------------


class TestParseText:
    def test_reads_utf8_content(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Contenu UTF-8 avec accents: éàü", encoding="utf-8")
        result = DocumentParser._parse_text(f)
        assert "éàü" in result

    def test_returns_none_on_read_error(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("ok")
        with patch("builtins.open", side_effect=IOError("read error")):
            result = DocumentParser._parse_text(f)
        assert result is None

    def test_returns_full_content(self, tmp_path):
        content = "Line 1\nLine 2\nLine 3"
        f = tmp_path / "test.txt"
        f.write_text(content)
        result = DocumentParser._parse_text(f)
        assert result == content


# ---------------------------------------------------------------------------
# _parse_pdf
# ---------------------------------------------------------------------------


class TestParsePdf:
    def test_returns_none_on_import_error(self, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"%PDF")
        with patch.dict("sys.modules", {"PyPDF2": None}):
            result = DocumentParser._parse_pdf(f)
        assert result is None

    def test_extracts_text_from_pages(self, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"%PDF")

        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page one content"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page two content"

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page1, mock_page2]

        mock_pdf2 = MagicMock()
        mock_pdf2.PdfReader.return_value = mock_reader

        with patch.dict("sys.modules", {"PyPDF2": mock_pdf2}):
            result = DocumentParser._parse_pdf(f)

        assert result is not None
        assert "Page one content" in result
        assert "Page two content" in result

    def test_returns_none_when_no_text_extracted(self, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"%PDF")

        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]

        mock_pdf2 = MagicMock()
        mock_pdf2.PdfReader.return_value = mock_reader

        with patch.dict("sys.modules", {"PyPDF2": mock_pdf2}):
            result = DocumentParser._parse_pdf(f)

        assert result is None

    def test_returns_none_on_exception(self, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"%PDF")

        mock_pdf2 = MagicMock()
        mock_pdf2.PdfReader.side_effect = Exception("Corrupt PDF")

        with patch.dict("sys.modules", {"PyPDF2": mock_pdf2}):
            result = DocumentParser._parse_pdf(f)

        assert result is None

    def test_skips_none_pages(self, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_bytes(b"%PDF")

        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Real content"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = None  # Falsy page text

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page1, mock_page2]

        mock_pdf2 = MagicMock()
        mock_pdf2.PdfReader.return_value = mock_reader

        with patch.dict("sys.modules", {"PyPDF2": mock_pdf2}):
            result = DocumentParser._parse_pdf(f)

        assert result is not None
        assert "Real content" in result


# ---------------------------------------------------------------------------
# _parse_docx
# ---------------------------------------------------------------------------


class TestParseDocx:
    def test_returns_none_on_import_error(self, tmp_path):
        f = tmp_path / "test.docx"
        f.write_bytes(b"PK")
        with patch.dict("sys.modules", {"docx": None}):
            result = DocumentParser._parse_docx(f)
        assert result is None

    def test_extracts_paragraphs(self, tmp_path):
        f = tmp_path / "test.docx"
        f.write_bytes(b"PK")

        mock_para1 = MagicMock()
        mock_para1.text = "First paragraph"
        mock_para2 = MagicMock()
        mock_para2.text = "Second paragraph"
        mock_para_empty = MagicMock()
        mock_para_empty.text = ""

        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para1, mock_para2, mock_para_empty]
        mock_doc.tables = []

        mock_docx_mod = MagicMock()
        mock_docx_mod.Document.return_value = mock_doc

        with patch.dict("sys.modules", {"docx": mock_docx_mod}):
            result = DocumentParser._parse_docx(f)

        assert result is not None
        assert "First paragraph" in result
        assert "Second paragraph" in result

    def test_extracts_tables(self, tmp_path):
        f = tmp_path / "test.docx"
        f.write_bytes(b"PK")

        mock_para = MagicMock()
        mock_para.text = "Paragraph"

        mock_cell1 = MagicMock()
        mock_cell1.text = "Cell A"
        mock_cell2 = MagicMock()
        mock_cell2.text = "Cell B"
        mock_row = MagicMock()
        mock_row.cells = [mock_cell1, mock_cell2]
        mock_table = MagicMock()
        mock_table.rows = [mock_row]

        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para]
        mock_doc.tables = [mock_table]

        mock_docx_mod = MagicMock()
        mock_docx_mod.Document.return_value = mock_doc

        with patch.dict("sys.modules", {"docx": mock_docx_mod}):
            result = DocumentParser._parse_docx(f)

        assert result is not None
        assert "Cell A" in result
        assert "Cell B" in result

    def test_returns_none_when_empty_content(self, tmp_path):
        f = tmp_path / "test.docx"
        f.write_bytes(b"PK")

        mock_para = MagicMock()
        mock_para.text = "   "  # whitespace-only

        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para]
        mock_doc.tables = []

        mock_docx_mod = MagicMock()
        mock_docx_mod.Document.return_value = mock_doc

        with patch.dict("sys.modules", {"docx": mock_docx_mod}):
            result = DocumentParser._parse_docx(f)

        assert result is None

    def test_returns_none_on_exception(self, tmp_path):
        f = tmp_path / "test.docx"
        f.write_bytes(b"PK")

        mock_docx_mod = MagicMock()
        mock_docx_mod.Document.side_effect = Exception("Broken DOCX")

        with patch.dict("sys.modules", {"docx": mock_docx_mod}):
            result = DocumentParser._parse_docx(f)

        assert result is None


# ---------------------------------------------------------------------------
# is_format_supported
# ---------------------------------------------------------------------------


class TestIsFormatSupported:
    @pytest.mark.parametrize("ext", [".txt", ".md", ".markdown", ".pdf", ".docx", ".doc"])
    def test_supported_formats_with_dot(self, ext):
        assert DocumentParser.is_format_supported(ext) is True

    @pytest.mark.parametrize("ext", ["txt", "md", "pdf", "docx"])
    def test_supported_formats_without_dot(self, ext):
        assert DocumentParser.is_format_supported(ext) is True

    @pytest.mark.parametrize("ext", [".xyz", ".csv", ".html", ".pptx"])
    def test_unsupported_formats(self, ext):
        assert DocumentParser.is_format_supported(ext) is False

    def test_case_insensitive_check(self):
        assert DocumentParser.is_format_supported(".TXT") is True
        assert DocumentParser.is_format_supported("PDF") is True


# ---------------------------------------------------------------------------
# get_required_libraries
# ---------------------------------------------------------------------------


class TestGetRequiredLibraries:
    def test_returns_dict(self):
        result = DocumentParser.get_required_libraries()
        assert isinstance(result, dict)

    def test_contains_expected_keys(self):
        result = DocumentParser.get_required_libraries()
        for key in ("txt", "md", "pdf", "docx"):
            assert key in result

    def test_txt_and_md_always_true(self):
        result = DocumentParser.get_required_libraries()
        assert result["txt"] is True
        assert result["md"] is True

    def test_returns_boolean_values(self):
        result = DocumentParser.get_required_libraries()
        for v in result.values():
            assert isinstance(v, bool)


# ---------------------------------------------------------------------------
# Global instance
# ---------------------------------------------------------------------------


class TestGlobalInstance:
    def test_global_instance_is_document_parser(self):
        assert isinstance(document_parser, DocumentParser)
