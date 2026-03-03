"""Tests for the Slide Editor template and route"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSlideEditorTemplate:
    """Tests for slide-editor.html template content"""

    def _read_template(self):
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates",
            "slide-editor.html",
        )
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_template_exists(self):
        """Test that slide-editor.html template exists"""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates",
            "slide-editor.html",
        )
        assert os.path.exists(template_path)

    def test_uses_blob_url_for_preview(self):
        """Test that preview uses Blob URL instead of srcdoc"""
        content = self._read_template()
        assert "createObjectURL" in content
        assert "new Blob(" in content

    def test_no_srcdoc_for_slides(self):
        """Test that srcdoc is not used for slide rendering"""
        content = self._read_template()
        assert "srcdoc" not in content

    def test_has_model_selector(self):
        """Test that model selector is present with Gemini models"""
        content = self._read_template()
        assert 'id="model-selector"' in content
        assert "gemini-3.1-pro-preview" in content
        assert "claude-opus-4-6" not in content

    def test_has_generation_overlay(self):
        """Test that generation overlay UI exists"""
        content = self._read_template()
        assert 'id="gen-overlay"' in content
        assert 'id="gen-progress"' in content
        assert 'id="gen-status"' in content

    def test_has_progress_overlay(self):
        """Test that progress overlay with bar exists"""
        content = self._read_template()
        assert 'id="gen-overlay"' in content
        assert "showGenOverlay" in content
        assert "hideGenOverlay" in content

    def test_has_render_functions(self):
        """Test that key render functions exist"""
        content = self._read_template()
        assert "function renderAll()" in content
        assert "function renderMainSlide()" in content
        assert "function renderThumbnails()" in content
        assert "function renderSlideHTML(" in content

    def test_has_ai_generation_functions(self):
        """Test that AI generation functions exist"""
        content = self._read_template()
        assert "function generateFromAI()" in content
        assert "function regenerateWithFeedback()" in content

    def test_has_export_functions(self):
        """Test that export functions exist"""
        content = self._read_template()
        assert "function exportPDF()" in content
        assert "function downloadHTML()" in content

    def test_revokes_blob_urls(self):
        """Test that Blob URLs are revoked to prevent memory leaks"""
        content = self._read_template()
        assert "revokeObjectURL" in content

    def test_has_minibar_html(self):
        """Test that mini progress bar HTML element exists"""
        content = self._read_template()
        assert 'id="gen-minibar"' in content
        assert 'id="minibar-fill"' in content
        assert 'id="minibar-text"' in content
        assert 'id="minibar-counter"' in content

    def test_has_minibar_functions(self):
        """Test that minibar JS helper functions exist"""
        content = self._read_template()
        assert "function showMinibar()" in content
        assert "function updateMinibar(" in content
        assert "function hideMinibar()" in content

    def test_minibar_shown_on_first_slide(self):
        """Test that minibar is shown when first slide arrives"""
        content = self._read_template()
        assert "showMinibar()" in content
        # hideMinibar should be called on done and error events
        assert content.count("hideMinibar()") >= 2

    def test_pdf_export_white_background(self):
        """Test that PDF export uses white background, not grey"""
        content = self._read_template()
        # The exportPDF function should override body background to white
        assert "background: #FFFFFF" in content
        # Should not have grey or black background in PDF export
        assert (
            "background: #f4f4f4"
            not in content.split("function exportPDF")[1].split("function ")[0]
        )
        assert (
            "background: #000" not in content.split("function exportPDF")[1].split("function ")[0]
        )

    def test_pdf_export_no_box_shadow(self):
        """Test that PDF export removes box-shadow from slides"""
        content = self._read_template()
        pdf_section = content.split("function exportPDF")[1].split("function ")[0]
        assert "box-shadow: none" in pdf_section

    def test_pdf_export_page_margin_zero(self):
        """Test that @page margin is 0 to remove browser header/footer"""
        content = self._read_template()
        pdf_section = content.split("function exportPDF")[1].split("function ")[0]
        assert "@page" in pdf_section
        assert "margin: 0" in pdf_section

    def test_pdf_export_empty_title(self):
        """Test that PDF export uses empty title to hide browser header"""
        content = self._read_template()
        pdf_section = content.split("function exportPDF")[1].split("function ")[0]
        assert "<title></title>" in pdf_section

    def test_pdf_export_slides_fill_page(self):
        """Test that slides are sized to fill the PDF page"""
        content = self._read_template()
        pdf_section = content.split("function exportPDF")[1].split("function ")[0]
        assert "100vw" in pdf_section
        assert "100vh" in pdf_section

    def test_no_pptx_export(self):
        """Test that PPTX export has been removed"""
        content = self._read_template()
        assert "exportPPTX" not in content
        assert "PptxGenJS" not in content
        assert "pptxgenjs" not in content

    def test_no_pptx_button(self):
        """Test that PPTX export button is removed from UI"""
        content = self._read_template()
        assert "PPTX" not in content.split("download-buttons")[1].split("</div>")[0]
