"""
Tests pour utils/word_exporter.py — export_to_word, _add_body_paragraph, _add_runs_with_bold
Uses mocks since python-docx may not be installed.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest


def _make_mock_docx():
    """Return a (mock_docx_module, mock_doc_instance) pair."""
    mock_doc_instance = MagicMock()
    mock_para = MagicMock()
    mock_doc_instance.add_paragraph.return_value = mock_para
    mock_doc_instance.add_heading.return_value = mock_para

    mock_docx_mod = MagicMock()
    mock_docx_mod.Document.return_value = mock_doc_instance
    mock_docx_mod.shared = MagicMock()

    return mock_docx_mod, mock_doc_instance


# ---------------------------------------------------------------------------
# ImportError path
# ---------------------------------------------------------------------------


class TestImportError:
    def test_raises_import_error_when_docx_not_installed(self, tmp_path):
        from utils.word_exporter import export_to_word

        with patch.dict("sys.modules", {"docx": None, "docx.shared": None}):
            with pytest.raises(ImportError, match="python-docx"):
                export_to_word({"title": "T", "sections": []}, str(tmp_path / "out.docx"))


# ---------------------------------------------------------------------------
# Helpers — _add_runs_with_bold
# ---------------------------------------------------------------------------


class TestAddRunsWithBold:
    def test_plain_text_not_bold(self):
        from utils.word_exporter import _add_runs_with_bold

        mock_para = MagicMock()
        runs = []

        def add_run(text):
            run = MagicMock()
            run.text = text
            runs.append(run)
            return run

        mock_para.add_run.side_effect = add_run
        _add_runs_with_bold(mock_para, "hello world")

        assert len(runs) == 1
        assert runs[0].bold is False

    def test_bold_text_is_bold(self):
        from utils.word_exporter import _add_runs_with_bold

        mock_para = MagicMock()
        runs = []

        def add_run(text):
            run = MagicMock()
            run.text = text
            runs.append(run)
            return run

        mock_para.add_run.side_effect = add_run
        _add_runs_with_bold(mock_para, "**important**")

        # "**important**".split("**") = ["", "important", ""]
        # Only "important" (i=1, odd) is bold; empty strings are skipped
        assert len(runs) == 1
        assert runs[0].bold is True

    def test_mixed_text_bold_and_normal(self):
        from utils.word_exporter import _add_runs_with_bold

        mock_para = MagicMock()
        runs = []

        def add_run(text):
            run = MagicMock()
            run.text = text
            runs.append(run)
            return run

        mock_para.add_run.side_effect = add_run
        _add_runs_with_bold(mock_para, "Start **bold** end")

        assert len(runs) == 3
        assert runs[0].bold is False   # "Start "
        assert runs[1].bold is True    # "bold"
        assert runs[2].bold is False   # " end"

    def test_empty_parts_are_skipped(self):
        from utils.word_exporter import _add_runs_with_bold

        mock_para = MagicMock()
        runs = []

        def add_run(text):
            run = MagicMock()
            runs.append(run)
            return run

        mock_para.add_run.side_effect = add_run
        _add_runs_with_bold(mock_para, "")
        assert len(runs) == 0

    def test_multiple_bold_segments(self):
        from utils.word_exporter import _add_runs_with_bold

        mock_para = MagicMock()
        runs = []

        def add_run(text):
            run = MagicMock()
            run.text = text
            runs.append(run)
            return run

        mock_para.add_run.side_effect = add_run
        # "**a** mid **b**" -> ["", "a", " mid ", "b", ""]
        # parts at odd indices (1, 3) are bold
        _add_runs_with_bold(mock_para, "**a** mid **b**")
        assert len(runs) == 3
        assert runs[0].bold is True   # "a"
        assert runs[1].bold is False  # " mid "
        assert runs[2].bold is True   # "b"

    def test_only_asterisks_no_content(self):
        from utils.word_exporter import _add_runs_with_bold

        mock_para = MagicMock()
        runs = []

        def add_run(text):
            run = MagicMock()
            runs.append(run)
            return run

        mock_para.add_run.side_effect = add_run
        # "****" -> ["", "", "", ""] — all empty, nothing added
        _add_runs_with_bold(mock_para, "****")
        assert len(runs) == 0


# ---------------------------------------------------------------------------
# Helpers — _add_body_paragraph
# ---------------------------------------------------------------------------


class TestAddBodyParagraph:
    def test_adds_plain_paragraph(self):
        from utils.word_exporter import _add_body_paragraph

        mock_doc = MagicMock()
        mock_para = MagicMock()
        mock_doc.add_paragraph.return_value = mock_para

        _add_body_paragraph(mock_doc, "Simple text")
        mock_doc.add_paragraph.assert_called()

    def test_bullet_item_uses_list_bullet_style(self):
        from utils.word_exporter import _add_body_paragraph

        mock_doc = MagicMock()
        mock_para = MagicMock()
        mock_doc.add_paragraph.return_value = mock_para

        _add_body_paragraph(mock_doc, "- first item")
        mock_doc.add_paragraph.assert_called_with(style="List Bullet")

    def test_bullet_with_bullet_unicode(self):
        from utils.word_exporter import _add_body_paragraph

        mock_doc = MagicMock()
        mock_para = MagicMock()
        mock_doc.add_paragraph.return_value = mock_para

        _add_body_paragraph(mock_doc, "• unicode bullet")
        mock_doc.add_paragraph.assert_called_with(style="List Bullet")

    def test_skips_empty_lines(self):
        from utils.word_exporter import _add_body_paragraph

        mock_doc = MagicMock()
        _add_body_paragraph(mock_doc, "\n\n\n")
        mock_doc.add_paragraph.assert_not_called()

    def test_multiline_text(self):
        from utils.word_exporter import _add_body_paragraph

        mock_doc = MagicMock()
        mock_para = MagicMock()
        mock_doc.add_paragraph.return_value = mock_para

        _add_body_paragraph(mock_doc, "Line 1\nLine 2\nLine 3")
        assert mock_doc.add_paragraph.call_count == 3

    def test_bullet_content_uses_add_runs_with_bold(self):
        """Bullet items strip '- ' prefix then pass remaining text to _add_runs_with_bold."""
        from utils.word_exporter import _add_body_paragraph

        mock_doc = MagicMock()
        mock_para = MagicMock()
        mock_doc.add_paragraph.return_value = mock_para

        _add_body_paragraph(mock_doc, "- **bold** item")
        mock_doc.add_paragraph.assert_called_with(style="List Bullet")
        # _add_runs_with_bold is called on the paragraph
        mock_para.add_run.assert_called()

    def test_regular_line_calls_add_runs(self):
        """Regular lines call add_paragraph() (no style arg) and then add_run."""
        from utils.word_exporter import _add_body_paragraph

        mock_doc = MagicMock()
        mock_para = MagicMock()
        mock_doc.add_paragraph.return_value = mock_para

        _add_body_paragraph(mock_doc, "Just text")
        mock_doc.add_paragraph.assert_called_once_with()
        mock_para.add_run.assert_called()


# ---------------------------------------------------------------------------
# export_to_word — mocked tests (works without python-docx installed)
# ---------------------------------------------------------------------------


class TestExportToWord:
    def _export(self, content, path, title="", mock_doc=None):
        """Run export_to_word with mocked docx module."""
        mock_docx_mod, mock_doc_instance = _make_mock_docx()
        if mock_doc is not None:
            mock_doc_instance = mock_doc
            mock_docx_mod.Document.return_value = mock_doc_instance
        with patch.dict(
            "sys.modules",
            {"docx": mock_docx_mod, "docx.shared": mock_docx_mod.shared},
        ):
            from utils.word_exporter import export_to_word
            return export_to_word(content, path, title=title), mock_doc_instance

    def test_returns_string_path(self, tmp_path):
        result, _ = self._export({"title": "My Doc", "sections": []}, str(tmp_path / "out.docx"))
        assert isinstance(result, str)
        assert result.endswith("out.docx")

    def test_save_called_on_doc(self, tmp_path):
        result, mock_doc = self._export({"title": "T", "sections": []}, str(tmp_path / "out.docx"))
        mock_doc.save.assert_called_once()

    def test_title_used_in_add_heading(self, tmp_path):
        _, mock_doc = self._export({"title": "Title", "sections": []}, str(tmp_path / "out.docx"))
        mock_doc.add_heading.assert_called()
        first_call = mock_doc.add_heading.call_args_list[0]
        assert first_call[0][0] == "Title"

    def test_title_parameter_overrides_content_title(self, tmp_path):
        _, mock_doc = self._export(
            {"title": "Content Title", "sections": []},
            str(tmp_path / "out.docx"),
            title="Override Title",
        )
        first_call = mock_doc.add_heading.call_args_list[0]
        assert first_call[0][0] == "Override Title"

    def test_default_title_when_no_title(self, tmp_path):
        _, mock_doc = self._export({"sections": []}, str(tmp_path / "out.docx"))
        first_call = mock_doc.add_heading.call_args_list[0]
        assert first_call[0][0] == "Document"

    def test_section_heading_added(self, tmp_path):
        content = {
            "title": "Report",
            "sections": [{"heading": "Introduction", "body": ""}],
        }
        _, mock_doc = self._export(content, str(tmp_path / "out.docx"))
        heading_calls = [c[0][0] for c in mock_doc.add_heading.call_args_list]
        assert "Introduction" in heading_calls

    def test_section_without_heading_skips_add_heading(self, tmp_path):
        content = {
            "title": "T",
            "sections": [{"heading": "", "body": "Body only"}],
        }
        _, mock_doc = self._export(content, str(tmp_path / "out.docx"))
        # Only the title heading call (level=0), not the empty section heading
        heading_calls = mock_doc.add_heading.call_args_list
        assert len(heading_calls) == 1

    def test_section_body_paragraph_added(self, tmp_path):
        content = {
            "title": "T",
            "sections": [{"heading": "S", "body": "Some body text"}],
        }
        _, mock_doc = self._export(content, str(tmp_path / "out.docx"))
        mock_doc.add_paragraph.assert_called()

    def test_section_without_body_skips_paragraph(self, tmp_path):
        content = {
            "title": "T",
            "sections": [{"heading": "Title Only", "body": ""}],
        }
        _, mock_doc = self._export(content, str(tmp_path / "out.docx"))
        mock_doc.add_paragraph.assert_not_called()

    def test_multiple_sections_all_headings_added(self, tmp_path):
        content = {
            "title": "T",
            "sections": [
                {"heading": f"Section {i}", "body": f"Body {i}"}
                for i in range(3)
            ],
        }
        _, mock_doc = self._export(content, str(tmp_path / "out.docx"))
        heading_texts = [c[0][0] for c in mock_doc.add_heading.call_args_list]
        for i in range(3):
            assert f"Section {i}" in heading_texts

    def test_section_level_capped_at_3(self, tmp_path):
        content = {
            "title": "T",
            "sections": [{"heading": "Deep", "body": "", "level": 10}],
        }
        _, mock_doc = self._export(content, str(tmp_path / "out.docx"))
        # Level is capped at 3 via min(level, 3) — passed as keyword arg
        section_heading_calls = mock_doc.add_heading.call_args_list[1:]
        if section_heading_calls:
            assert section_heading_calls[0][1].get("level") == 3

    def test_creates_parent_directories(self, tmp_path):
        out = tmp_path / "nested" / "deep" / "output.docx"
        result, _ = self._export({"title": "T", "sections": []}, str(out))
        # Path parent dirs are created by pathlib mkdir(parents=True)
        assert (tmp_path / "nested" / "deep").exists()
