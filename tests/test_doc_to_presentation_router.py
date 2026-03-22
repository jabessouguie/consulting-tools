"""Tests for routers/doc_to_presentation.py — HTTP endpoints"""
import io
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app import app

CSRF_HEADERS = {"origin": "http://test"}


def make_txt_file(name="doc.txt", content=b"Some document content for testing purposes."):
    return (name, io.BytesIO(content), "text/plain")


# ── Page route ────────────────────────────────────────────────────────────────

class TestDocToPresentationPage:
    async def test_page_ok(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/doc-to-presentation")
        assert resp.status_code == 200
        assert "sentation" in resp.text  # "Présentation" or "Presentation"

    async def test_page_has_form(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/doc-to-presentation")
        assert "dtp-form" in resp.text or "doc-files" in resp.text


# ── /api/doc-to-presentation/generate ────────────────────────────────────────

class TestDocToPresentationGenerate:
    async def test_no_files_returns_422(self):
        """Required 'files' field missing → FastAPI 422"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/doc-to-presentation/generate",
                headers=CSRF_HEADERS,
                data={"target_audience": "Managers", "objective": "Convince"},
            )
        assert resp.status_code == 422

    async def test_missing_audience_field_returns_422(self):
        """Required 'target_audience' field omitted → FastAPI 422"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/doc-to-presentation/generate",
                headers=CSRF_HEADERS,
                files=[("files", make_txt_file())],
                data={"objective": "Goal"},  # target_audience intentionally omitted
            )
        assert resp.status_code == 422

    async def test_missing_objective_field_returns_422(self):
        """Required 'objective' field omitted → FastAPI 422"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/doc-to-presentation/generate",
                headers=CSRF_HEADERS,
                files=[("files", make_txt_file())],
                data={"target_audience": "Managers"},  # objective intentionally omitted
            )
        assert resp.status_code == 422

    async def test_valid_returns_job_id(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/doc-to-presentation/generate",
                headers=CSRF_HEADERS,
                files=[("files", make_txt_file())],
                data={"target_audience": "Managers", "objective": "Present strategy"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert len(data["job_id"]) == 8

    async def test_multiple_files_accepted(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/doc-to-presentation/generate",
                headers=CSRF_HEADERS,
                files=[
                    ("files", make_txt_file("a.txt")),
                    ("files", make_txt_file("b.md", b"# Markdown content here")),
                ],
                data={"target_audience": "Tech team", "objective": "Review"},
            )
        # May hit rate limit (3/min)
        assert resp.status_code in {200, 429}
        if resp.status_code == 200:
            assert "job_id" in resp.json()


# ── /api/doc-to-presentation/stream/{job_id} ─────────────────────────────────

class TestDocToPresentationStream:
    async def test_unknown_job_returns_error_event(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/doc-to-presentation/stream/nonexistent")
        assert resp.status_code == 200
        assert "error_msg" in resp.text

    async def test_done_job_returns_result(self):
        from routers.shared import jobs

        job_id = "dtp00001"
        jobs[job_id] = {
            "type": "doc-to-presentation",
            "status": "done",
            "steps": [{"step": "pptx", "status": "done", "progress": 100}],
            "result": {
                "slide_count": 5,
                "pptx_filename": "presentation_20260312_120000.pptx",
                "generated_at": "2026-03-12T12:00:00",
            },
            "error": None,
        }
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(f"/api/doc-to-presentation/stream/{job_id}")
            assert resp.status_code == 200
            assert "result" in resp.text
            assert "slide_count" in resp.text
        finally:
            jobs.pop(job_id, None)

    async def test_error_job_returns_error_event(self):
        from routers.shared import jobs

        job_id = "dtperr01"
        jobs[job_id] = {
            "type": "doc-to-presentation",
            "status": "error",
            "steps": [],
            "result": None,
            "error": "LLM failed",
        }
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(f"/api/doc-to-presentation/stream/{job_id}")
            assert resp.status_code == 200
            assert "error_msg" in resp.text
            assert "LLM failed" in resp.text
        finally:
            jobs.pop(job_id, None)


# ── /api/doc-to-presentation/download/{filename} ─────────────────────────────

class TestDocToPresentationDownload:
    async def test_nonexistent_file_returns_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/doc-to-presentation/download/ghost.pptx")
        assert resp.status_code == 404

    async def test_non_pptx_extension_returns_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/doc-to-presentation/download/../../etc/passwd")
        assert resp.status_code == 404

    async def test_existing_file_returns_pptx(self, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        fake_pptx = output_dir / "presentation_test.pptx"
        fake_pptx.write_bytes(b"PK fake pptx content")

        with patch("routers.doc_to_presentation.BASE_DIR", tmp_path):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/doc-to-presentation/download/presentation_test.pptx")
        assert resp.status_code == 200
        assert "openxmlformats" in resp.headers.get("content-type", "")
