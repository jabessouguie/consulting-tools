"""
Tests pour utils/security_audit.py
Phase 5 — couverture maximale des 168 statements
"""
import os
import stat
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

os.environ.setdefault("AUTH_PASSWORD", "testpass")
os.environ.setdefault("SECRET_KEY", "testsecret")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")

from utils.security_audit import (
    check_env_file,
    check_gitignore,
    check_hardcoded_secrets,
    check_ssl_config,
    generate_report,
    main,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stat(mode_octal: str):
    """Retourne un mock de stat avec st_mode correspondant au mode octal."""
    mock_stat = MagicMock()
    # oct() renvoie "0o100600" — on veut que [-3:] == mode_octal
    # On encode directement la valeur entiere
    mode_int = int("100" + mode_octal, 8)
    mock_stat.st_mode = mode_int
    return mock_stat


# ---------------------------------------------------------------------------
# check_env_file
# ---------------------------------------------------------------------------

class TestCheckEnvFile:
    def test_returns_error_when_env_file_missing(self, tmp_path):
        """tmp_path has no .env — function should return status=error."""
        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path
            result = check_env_file()
        assert result["status"] == "error"
        assert any(".env" in issue or "manquant" in issue for issue in result["issues"])

    def test_env_file_missing_gives_error_status(self, tmp_path):
        """Patch the base_dir to tmp_path so env file is truly absent."""
        with patch("utils.security_audit.Path") as MockPath:
            # Make Path(__file__) return something whose .parent.parent == tmp_path
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_env_file()

        # env_file = tmp_path / ".env" which doesn't exist
        assert result["status"] == "error"
        assert any("manquant" in issue for issue in result["issues"])

    def test_env_file_present_all_vars_ok(self, tmp_path):
        """Env file present with all required variables and secure permissions."""
        env_content = (
            "ANTHROPIC_API_KEY=sk-ant-real\n"
            "AUTH_USERNAME=admin\n"
            "AUTH_PASSWORD=StrongPass123!\n"
            "SESSION_SECRET=randomsecret\n"
        )
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)
        # Set 600 permissions
        env_file.chmod(0o600)

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_env_file()

        assert result["status"] == "ok"
        assert result["issues"] == []

    def test_env_file_permissive_permissions_warning(self, tmp_path):
        """Env file with 644 permissions should add an issue."""
        env_content = (
            "ANTHROPIC_API_KEY=sk-ant-real\n"
            "AUTH_USERNAME=admin\n"
            "AUTH_PASSWORD=StrongPass123!\n"
            "SESSION_SECRET=randomsecret\n"
        )
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)
        env_file.chmod(0o644)

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_env_file()

        assert any("Permissions" in issue for issue in result["issues"])

    def test_env_file_missing_required_vars(self, tmp_path):
        """Env file exists but is missing some required variables."""
        env_content = "ANTHROPIC_API_KEY=sk-ant-real\n"
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)
        env_file.chmod(0o600)

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_env_file()

        assert result["status"] == "warning"
        assert any("AUTH_USERNAME" in issue for issue in result["issues"])
        assert any("AUTH_PASSWORD" in issue for issue in result["issues"])
        assert any("SESSION_SECRET" in issue for issue in result["issues"])

    def test_env_file_default_anthropic_key_warning(self, tmp_path):
        """Detect use of default placeholder Anthropic key."""
        env_content = (
            "ANTHROPIC_API_KEY=your_anthropic_api_key_here\n"
            "AUTH_USERNAME=admin\n"
            "AUTH_PASSWORD=StrongPass\n"
            "SESSION_SECRET=mysecret\n"
        )
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)
        env_file.chmod(0o600)

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_env_file()

        assert any("ANTHROPIC_API_KEY" in issue for issue in result["issues"])

    def test_env_file_default_password_warning(self, tmp_path):
        """Detect use of default consultingtools2026 password."""
        env_content = (
            "ANTHROPIC_API_KEY=sk-ant-real\n"
            "AUTH_USERNAME=admin\n"
            "AUTH_PASSWORD=consultingtools2026\n"
            "SESSION_SECRET=mysecret\n"
        )
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)
        env_file.chmod(0o600)

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_env_file()

        assert any("Mot de passe" in issue for issue in result["issues"])

    def test_env_file_session_secret_not_generated_warning(self, tmp_path):
        """Detect when SESSION_SECRET is still the template placeholder."""
        env_content = (
            "ANTHROPIC_API_KEY=sk-ant-real\n"
            "AUTH_USERNAME=admin\n"
            "AUTH_PASSWORD=StrongPass\n"
            "SESSION_SECRET=generate_with_secrets.token_urlsafe\n"
        )
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)
        env_file.chmod(0o600)

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_env_file()

        assert any("SESSION_SECRET" in issue for issue in result["issues"])

    def test_env_file_640_permissions_are_ok(self, tmp_path):
        """640 is also an acceptable permission for .env."""
        env_content = (
            "ANTHROPIC_API_KEY=sk-ant-real\n"
            "AUTH_USERNAME=admin\n"
            "AUTH_PASSWORD=StrongPass!\n"
            "SESSION_SECRET=mysecret\n"
        )
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)
        env_file.chmod(0o640)

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_env_file()

        # 640 is accepted, no permissions issue
        assert not any("Permissions .env" in issue for issue in result["issues"])


# ---------------------------------------------------------------------------
# check_gitignore
# ---------------------------------------------------------------------------

class TestCheckGitignore:
    def test_gitignore_missing_returns_error(self, tmp_path):
        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_gitignore()

        assert result["status"] == "error"
        assert any(".gitignore" in issue for issue in result["issues"])

    def test_gitignore_all_patterns_present(self, tmp_path):
        gitignore_content = ".env\n*.pem\n*.key\nssl/\n"
        gitignore_file = tmp_path / ".gitignore"
        gitignore_file.write_text(gitignore_content)

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_gitignore()

        assert result["status"] == "ok"
        assert result["issues"] == []

    def test_gitignore_missing_patterns_warning(self, tmp_path):
        # Missing *.pem and ssl/
        gitignore_content = ".env\n*.key\n"
        gitignore_file = tmp_path / ".gitignore"
        gitignore_file.write_text(gitignore_content)

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_gitignore()

        assert result["status"] == "warning"
        assert any("*.pem" in issue for issue in result["issues"])
        assert any("ssl/" in issue for issue in result["issues"])

    def test_gitignore_empty_file_warns_all_patterns(self, tmp_path):
        gitignore_file = tmp_path / ".gitignore"
        gitignore_file.write_text("")

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_gitignore()

        assert result["status"] == "warning"
        # All 4 patterns should be reported as missing
        assert len(result["issues"]) == 4

    def test_gitignore_partial_patterns(self, tmp_path):
        """Only .env present — 3 patterns missing."""
        gitignore_file = tmp_path / ".gitignore"
        gitignore_file.write_text(".env\n")

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_gitignore()

        assert result["status"] == "warning"
        assert len(result["issues"]) == 3


# ---------------------------------------------------------------------------
# check_hardcoded_secrets
# ---------------------------------------------------------------------------

class TestCheckHardcodedSecrets:
    def test_no_secrets_returns_ok(self, tmp_path):
        """Python file with no secrets."""
        py_file = tmp_path / "clean_module.py"
        py_file.write_text("def hello():\n    return 'world'\n")

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_hardcoded_secrets()

        assert result["status"] == "ok"
        assert result["issues"] == []

    def test_detects_anthropic_api_key(self, tmp_path):
        """sk-ant- pattern should be flagged."""
        py_file = tmp_path / "leak.py"
        py_file.write_text('API_KEY = "sk-ant-abcdef1234567890abcdef"\n')

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_hardcoded_secrets()

        assert result["status"] == "error"
        assert any("Anthropic" in issue for issue in result["issues"])

    def test_detects_password_in_code(self, tmp_path):
        """password = 'hardcoded' should be flagged."""
        py_file = tmp_path / "config.py"
        py_file.write_text('password = "supersecretpassword"\n')

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_hardcoded_secrets()

        assert result["status"] == "error"
        assert any("Mot de passe" in issue for issue in result["issues"])

    def test_ignores_comment_lines(self, tmp_path):
        """Secrets in comments should be ignored."""
        py_file = tmp_path / "commented.py"
        py_file.write_text('# password = "supersecretpassword"\n')

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_hardcoded_secrets()

        assert result["status"] == "ok"

    def test_ignores_doctest_lines(self, tmp_path):
        """Secrets in >>> doctest lines should be ignored."""
        py_file = tmp_path / "doctest.py"
        py_file.write_text('>>> password = "supersecretpassword"\n')

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_hardcoded_secrets()

        assert result["status"] == "ok"

    def test_ignores_example_values(self, tmp_path):
        """Values containing 'example' are filtered as false positives."""
        py_file = tmp_path / "example_config.py"
        py_file.write_text('api_key = "example_key_value"\n')

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_hardcoded_secrets()

        assert result["status"] == "ok"

    def test_ignores_your_underscore_prefix(self, tmp_path):
        """Values containing 'your_' are filtered as false positives."""
        py_file = tmp_path / "template.py"
        py_file.write_text('api_key = "your_api_key_here"\n')

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_hardcoded_secrets()

        assert result["status"] == "ok"

    def test_skips_unreadable_files(self, tmp_path):
        """If a file raises an exception it should be silently skipped."""
        py_file = tmp_path / "unreadable.py"
        py_file.write_text("dummy\n")

        original_open = open

        def patched_open(path, *args, **kwargs):
            if "unreadable" in str(path):
                raise PermissionError("no access")
            return original_open(path, *args, **kwargs)

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            with patch("builtins.open", side_effect=patched_open):
                result = check_hardcoded_secrets()

        assert result["status"] == "ok"

    def test_does_not_duplicate_same_issue(self, tmp_path):
        """The same issue should not be reported twice for the same file."""
        py_file = tmp_path / "dup.py"
        py_file.write_text(
            'password = "abcdefghij"\npassword = "abcdefghij"\n'
        )

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_hardcoded_secrets()

        # Issue count for dup.py should not exceed 1
        dup_issues = [i for i in result["issues"] if "dup.py" in i]
        assert len(dup_issues) == 1

    def test_skips_files_in_excluded_dirs(self, tmp_path):
        """Files under 'tests' or 'venv' directories are excluded."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        test_file = tests_dir / "fixture_secrets.py"
        test_file.write_text('password = "hardcoded_secret_value"\n')

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_hardcoded_secrets()

        assert result["status"] == "ok"

    def test_detects_api_key_assignment(self, tmp_path):
        """api_key = 'hardcoded' should be flagged."""
        py_file = tmp_path / "service.py"
        py_file.write_text('api_key = "myrealtoken12345"\n')

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_hardcoded_secrets()

        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# check_ssl_config
# ---------------------------------------------------------------------------

class TestCheckSslConfig:
    def test_ssl_dir_missing_returns_warning(self, tmp_path):
        # tmp_path has no 'ssl' subdirectory
        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_ssl_config()

        assert result["status"] == "warning"
        assert any("SSL" in issue for issue in result["issues"])

    def test_ssl_dir_exists_but_no_certs(self, tmp_path):
        ssl_dir = tmp_path / "ssl"
        ssl_dir.mkdir()
        # No cert.pem or key.pem

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_ssl_config()

        assert result["status"] == "warning"
        assert any("Certificats SSL" in issue for issue in result["issues"])

    def test_ssl_certs_present_secure_key(self, tmp_path):
        ssl_dir = tmp_path / "ssl"
        ssl_dir.mkdir()
        cert_file = ssl_dir / "cert.pem"
        key_file = ssl_dir / "key.pem"
        cert_file.write_text("CERT")
        key_file.write_text("KEY")
        key_file.chmod(0o600)

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_ssl_config()

        assert result["status"] == "ok"
        assert result["issues"] == []

    def test_ssl_key_permissive_permissions(self, tmp_path):
        ssl_dir = tmp_path / "ssl"
        ssl_dir.mkdir()
        cert_file = ssl_dir / "cert.pem"
        key_file = ssl_dir / "key.pem"
        cert_file.write_text("CERT")
        key_file.write_text("KEY")
        key_file.chmod(0o644)

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_ssl_config()

        assert any("Permissions clé" in issue or "Permissions" in issue for issue in result["issues"])

    def test_ssl_only_cert_no_key(self, tmp_path):
        ssl_dir = tmp_path / "ssl"
        ssl_dir.mkdir()
        cert_file = ssl_dir / "cert.pem"
        cert_file.write_text("CERT")
        # key.pem missing

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            result = check_ssl_config()

        assert result["status"] == "warning"


# ---------------------------------------------------------------------------
# generate_report
# ---------------------------------------------------------------------------

class TestGenerateReport:
    def test_no_issues_produces_clean_output(self, capsys):
        results = [
            {"status": "ok", "issues": []},
            {"status": "ok", "issues": []},
        ]
        generate_report(results)
        captured = capsys.readouterr()
        assert "Aucun problème" in captured.out or "problème" in captured.out

    def test_error_status_reported(self, capsys):
        results = [
            {"status": "error", "issues": ["Clé exposée"]},
        ]
        generate_report(results)
        captured = capsys.readouterr()
        assert "erreur" in captured.out.lower() or "Clé exposée" in captured.out

    def test_warning_status_reported(self, capsys):
        results = [
            {"status": "warning", "issues": ["Variable manquante: X"]},
        ]
        generate_report(results)
        captured = capsys.readouterr()
        assert "avertissement" in captured.out.lower() or "Variable manquante" in captured.out

    def test_multiple_issues_all_listed(self, capsys):
        results = [
            {"status": "error", "issues": ["Issue A", "Issue B"]},
            {"status": "warning", "issues": ["Issue C"]},
        ]
        generate_report(results)
        captured = capsys.readouterr()
        assert "Issue A" in captured.out
        assert "Issue B" in captured.out
        assert "Issue C" in captured.out

    def test_report_prints_general_recommendations(self, capsys):
        results = [{"status": "ok", "issues": []}]
        generate_report(results)
        captured = capsys.readouterr()
        assert "AUTH_PASSWORD" in captured.out
        assert "SESSION_SECRET" in captured.out

    def test_empty_results_list(self, capsys):
        generate_report([])
        captured = capsys.readouterr()
        assert len(captured.out) > 0  # At least recommendations are printed

    def test_mixed_errors_and_warnings(self, capsys):
        results = [
            {"status": "error", "issues": ["Critical failure"]},
            {"status": "warning", "issues": ["Minor issue"]},
            {"status": "ok", "issues": []},
        ]
        generate_report(results)
        captured = capsys.readouterr()
        assert "Critical failure" in captured.out
        assert "Minor issue" in captured.out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

class TestMain:
    def test_main_exits_0_on_clean(self, tmp_path):
        """main() should exit 0 when all checks pass."""
        env_content = (
            "ANTHROPIC_API_KEY=sk-ant-real\n"
            "AUTH_USERNAME=admin\n"
            "AUTH_PASSWORD=StrongPass!\n"
            "SESSION_SECRET=mysecret\n"
        )
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)
        env_file.chmod(0o600)

        gitignore_file = tmp_path / ".gitignore"
        gitignore_file.write_text(".env\n*.pem\n*.key\nssl/\n")

        ssl_dir = tmp_path / "ssl"
        ssl_dir.mkdir()
        cert = ssl_dir / "cert.pem"
        key = ssl_dir / "key.pem"
        cert.write_text("CERT")
        key.write_text("KEY")
        key.chmod(0o600)

        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0

    def test_main_exits_1_on_errors(self, tmp_path):
        """main() should exit 1 when there are critical errors."""
        # No .env → error status
        with patch("utils.security_audit.Path") as MockPath:
            mock_file_path = MagicMock()
            mock_file_path.parent.parent = tmp_path
            MockPath.return_value = mock_file_path

            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1

    def test_main_calls_all_four_checks(self, tmp_path):
        """Verify main invokes all four check functions."""
        with patch("utils.security_audit.check_env_file", return_value={"status": "ok", "issues": []}) as mock_env, \
             patch("utils.security_audit.check_gitignore", return_value={"status": "ok", "issues": []}) as mock_git, \
             patch("utils.security_audit.check_hardcoded_secrets", return_value={"status": "ok", "issues": []}) as mock_sec, \
             patch("utils.security_audit.check_ssl_config", return_value={"status": "ok", "issues": []}) as mock_ssl, \
             patch("utils.security_audit.generate_report"):
            with pytest.raises(SystemExit):
                main()

        mock_env.assert_called_once()
        mock_git.assert_called_once()
        mock_sec.assert_called_once()
        mock_ssl.assert_called_once()

    def test_main_exits_0_on_warnings_only(self, tmp_path):
        """Warnings should not cause exit(1)."""
        with patch("utils.security_audit.check_env_file", return_value={"status": "warning", "issues": ["warn"]}), \
             patch("utils.security_audit.check_gitignore", return_value={"status": "ok", "issues": []}), \
             patch("utils.security_audit.check_hardcoded_secrets", return_value={"status": "ok", "issues": []}), \
             patch("utils.security_audit.check_ssl_config", return_value={"status": "ok", "issues": []}), \
             patch("utils.security_audit.generate_report"):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0
