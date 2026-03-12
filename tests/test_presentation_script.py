"""Tests for routers/presentation_script.py"""
import io
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app import app

FAKE_PPTX = b"PK\x03\x04" + b"\x00" * 100  # minimal fake PPTX bytes
CSRF_HEADERS = {"origin": "http://test"}


def make_pptx_upload(filename="test.pptx", content=FAKE_PPTX):
    return ("pptx_file", (filename, io.BytesIO(content), "application/octet-stream"))


# ── Page route ────────────────────────────────────────────────────────────────

class TestPresentationScriptPage:
    async def test_page_ok(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/presentation-script")
        assert resp.status_code == 200
        assert "Script de" in resp.text

    async def test_page_has_form(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/presentation-script")
        assert "script-form" in resp.text
        assert "pptx-file" in resp.text


# ── /api/presentation-script/generate ────────────────────────────────────────

class TestPresentationScriptGenerate:
    async def test_no_file_returns_422(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/presentation-script/generate",
                headers=CSRF_HEADERS,
                data={"context": "test"},
            )
        assert resp.status_code == 422

    async def test_wrong_extension_returns_400(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/presentation-script/generate",
                headers=CSRF_HEADERS,
                files=[("pptx_file", ("test.docx", io.BytesIO(b"content"), "application/octet-stream"))],
                data={"context": ""},
            )
        assert resp.status_code == 400
        assert "PPTX" in resp.json()["error"]

    async def test_empty_file_returns_400(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/presentation-script/generate",
                headers=CSRF_HEADERS,
                files=[("pptx_file", ("test.pptx", io.BytesIO(b""), "application/octet-stream"))],
                data={"context": ""},
            )
        assert resp.status_code == 400
        assert "vide" in resp.json()["error"]

    async def test_valid_returns_job_id(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/presentation-script/generate",
                headers=CSRF_HEADERS,
                files=[make_pptx_upload()],
                data={"context": "test context"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert len(data["job_id"]) == 8

    async def test_valid_without_context(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/presentation-script/generate",
                headers=CSRF_HEADERS,
                files=[make_pptx_upload()],
                data={"context": ""},
            )
        # May hit rate limit (3/min) if other tests ran first
        assert resp.status_code in {200, 429}
        if resp.status_code == 200:
            assert "job_id" in resp.json()


# ── /api/presentation-script/stream/{job_id} ─────────────────────────────────

class TestPresentationScriptStream:
    async def test_unknown_job_returns_error_event(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/presentation-script/stream/nonexistent")
        assert resp.status_code == 200
        assert "error_msg" in resp.text

    async def test_done_job_returns_result(self):
        from routers.shared import jobs

        job_id = "ps000001"
        jobs[job_id] = {
            "type": "presentation-script",
            "status": "done",
            "steps": [{"step": "extract", "status": "done", "progress": 100}],
            "result": {"markdown": "# Script", "num_slides": 3, "estimated_duration": "8-11 min"},
            "error": None,
        }
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(f"/api/presentation-script/stream/{job_id}")
            assert resp.status_code == 200
            assert "result" in resp.text
            assert "Script" in resp.text
        finally:
            jobs.pop(job_id, None)

    async def test_error_job_returns_error_event(self):
        from routers.shared import jobs

        job_id = "pserr001"
        jobs[job_id] = {
            "type": "presentation-script",
            "status": "error",
            "steps": [],
            "result": None,
            "error": "Agent crashed",
        }
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(f"/api/presentation-script/stream/{job_id}")
            assert resp.status_code == 200
            assert "error_msg" in resp.text
            assert "Agent crashed" in resp.text
        finally:
            jobs.pop(job_id, None)
