"""
Tests pour agents/dataset_analyzer.py
Cible: augmenter la couverture depuis 19% (121 stmts)
"""
import io
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch, mock_open

import pytest
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("CONSULTANT_NAME", "Test Consultant")
os.environ.setdefault("CONSULTANT_TITLE", "Data Manager")
os.environ.setdefault("COMPANY_NAME", "TestCo")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("AUTH_PASSWORD", "testpass")
os.environ.setdefault("SECRET_KEY", "testsecret")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_df():
    """Return a small but realistic DataFrame for testing."""
    return pd.DataFrame({
        "age": [25, 30, 35, 40, 45, 30, 25],
        "salary": [50000, 60000, 70000, 80000, 90000, 60000, 50000],
        "department": ["HR", "IT", "IT", "Finance", "HR", "IT", "Finance"],
        "name": ["Alice", "Bob", "Charlie", "Dave", "Eve", "Frank", None],
    })


def _make_df_with_nulls():
    return pd.DataFrame({
        "a": [1, None, 3, None, 5],
        "b": ["x", "y", None, "w", "v"],
        "c": [10, 20, 30, 40, 50],
    })


def _make_df_duplicates():
    return pd.DataFrame({
        "x": [1, 1, 2, 3],
        "y": ["a", "a", "b", "c"],
    })


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def agent():
    """Return a DatasetAnalyzerAgent with LLM and consultant_info mocked."""
    from config.consultant import ConsultantConfig
    ConsultantConfig.reset()

    with patch("agents.dataset_analyzer.LLMClient") as MockLLM, \
         patch("agents.dataset_analyzer.get_consultant_info") as MockCI:
        MockCI.return_value = {
            "name": "Test Consultant",
            "title": "Data Manager",
            "company": "TestCo",
        }
        mock_llm_instance = MagicMock()
        MockLLM.return_value = mock_llm_instance
        mock_llm_instance.generate.return_value = "# Rapport\n\nAnalyse generee par LLM."

        from agents.dataset_analyzer import DatasetAnalyzerAgent
        a = DatasetAnalyzerAgent()
        yield a


# ---------------------------------------------------------------------------
# TestDatasetAnalyzerAgentInit
# ---------------------------------------------------------------------------

class TestDatasetAnalyzerAgentInit:
    def test_agent_has_llm_client(self, agent):
        assert hasattr(agent, "llm_client")

    def test_agent_has_consultant_info(self, agent):
        assert hasattr(agent, "consultant_info")
        assert isinstance(agent.consultant_info, dict)

    def test_consultant_info_name(self, agent):
        assert agent.consultant_info["name"] == "Test Consultant"

    def test_consultant_info_company(self, agent):
        assert agent.consultant_info["company"] == "TestCo"


# ---------------------------------------------------------------------------
# TestLoadDataset
# ---------------------------------------------------------------------------

class TestLoadDataset:
    def test_load_csv_returns_dataframe(self, agent, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b,c\n1,2,3\n4,5,6\n", encoding="utf-8")
        df = agent.load_dataset(str(csv_file))
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ["a", "b", "c"]

    def test_load_csv_utf8_encoding(self, agent, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("nom,valeur\nAlice,100\nBob,200\n", encoding="utf-8")
        df = agent.load_dataset(str(csv_file))
        assert len(df) == 2

    def test_load_csv_latin1_fallback(self, agent, tmp_path):
        csv_file = tmp_path / "data.csv"
        # Write with latin1 encoding (not valid utf-8 for certain chars)
        content = "nom,valeur\nAlice,100\n"
        csv_file.write_bytes(content.encode("latin1"))
        df = agent.load_dataset(str(csv_file))
        assert isinstance(df, pd.DataFrame)

    def test_load_xlsx_returns_dataframe(self, agent, tmp_path):
        mock_df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        with patch("agents.dataset_analyzer.pd.read_excel", return_value=mock_df):
            df = agent.load_dataset(str(tmp_path / "data.xlsx"))
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

    def test_load_xls_returns_dataframe(self, agent, tmp_path):
        mock_df = pd.DataFrame({"col": [10, 20, 30]})
        with patch("agents.dataset_analyzer.pd.read_excel", return_value=mock_df):
            df = agent.load_dataset(str(tmp_path / "data.xls"))
        assert isinstance(df, pd.DataFrame)

    def test_load_unsupported_format_raises(self, agent, tmp_path):
        fake_file = tmp_path / "data.json"
        fake_file.write_text("{}")
        with pytest.raises(ValueError, match="Format non supporté"):
            agent.load_dataset(str(fake_file))

    def test_load_csv_correct_row_count(self, agent, tmp_path):
        csv_file = tmp_path / "data.csv"
        rows = ["col1,col2"] + [f"{i},{i*2}" for i in range(10)]
        csv_file.write_text("\n".join(rows), encoding="utf-8")
        df = agent.load_dataset(str(csv_file))
        assert len(df) == 10


# ---------------------------------------------------------------------------
# TestAnalyzeStructure
# ---------------------------------------------------------------------------

class TestAnalyzeStructure:
    def test_returns_dict(self, agent):
        df = _make_df()
        result = agent.analyze_structure(df)
        assert isinstance(result, dict)

    def test_num_rows(self, agent):
        df = _make_df()
        result = agent.analyze_structure(df)
        assert result["num_rows"] == len(df)

    def test_num_columns(self, agent):
        df = _make_df()
        result = agent.analyze_structure(df)
        assert result["num_columns"] == len(df.columns)

    def test_columns_list(self, agent):
        df = _make_df()
        result = agent.analyze_structure(df)
        assert set(result["columns"]) == set(df.columns)

    def test_dtypes_dict(self, agent):
        df = _make_df()
        result = agent.analyze_structure(df)
        assert isinstance(result["dtypes"], dict)
        assert len(result["dtypes"]) == len(df.columns)

    def test_numeric_columns_identified(self, agent):
        df = _make_df()
        result = agent.analyze_structure(df)
        assert "age" in result["numeric_columns"]
        assert "salary" in result["numeric_columns"]

    def test_categorical_columns_identified(self, agent):
        df = _make_df()
        result = agent.analyze_structure(df)
        assert "department" in result["categorical_columns"]
        assert "name" in result["categorical_columns"]

    def test_datetime_columns_empty_when_none(self, agent):
        df = _make_df()
        result = agent.analyze_structure(df)
        assert result["datetime_columns"] == []

    def test_datetime_columns_detected(self, agent):
        df = pd.DataFrame({
            "date": pd.to_datetime(["2026-01-01", "2026-01-02"]),
            "value": [1, 2],
        })
        result = agent.analyze_structure(df)
        assert "date" in result["datetime_columns"]

    def test_memory_usage_is_float(self, agent):
        df = _make_df()
        result = agent.analyze_structure(df)
        assert isinstance(result["memory_usage"], float)
        assert result["memory_usage"] >= 0


# ---------------------------------------------------------------------------
# TestAnalyzeQuality
# ---------------------------------------------------------------------------

class TestAnalyzeQuality:
    def test_returns_dict(self, agent):
        df = _make_df()
        result = agent.analyze_quality(df)
        assert isinstance(result, dict)

    def test_missing_values_key_present(self, agent):
        df = _make_df()
        result = agent.analyze_quality(df)
        assert "missing_values" in result

    def test_duplicates_key_present(self, agent):
        df = _make_df()
        result = agent.analyze_quality(df)
        assert "duplicates" in result

    def test_no_missing_when_complete_df(self, agent):
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        result = agent.analyze_quality(df)
        assert len(result["missing_values"]) == 0

    def test_missing_values_detected(self, agent):
        df = _make_df_with_nulls()
        result = agent.analyze_quality(df)
        assert "a" in result["missing_values"]
        assert result["missing_values"]["a"]["count"] == 2

    def test_missing_values_percentage(self, agent):
        df = _make_df_with_nulls()
        result = agent.analyze_quality(df)
        # column "a" has 2 nulls out of 5 rows = 40%
        assert result["missing_values"]["a"]["percentage"] == pytest.approx(40.0, rel=0.01)

    def test_duplicates_count_correct(self, agent):
        df = _make_df_duplicates()
        result = agent.analyze_quality(df)
        assert result["duplicates"]["count"] == 1

    def test_no_duplicates_when_unique(self, agent):
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        result = agent.analyze_quality(df)
        assert result["duplicates"]["count"] == 0

    def test_duplicate_percentage(self, agent):
        df = _make_df_duplicates()
        result = agent.analyze_quality(df)
        expected_pct = round(1 / 4 * 100, 2)
        assert result["duplicates"]["percentage"] == pytest.approx(expected_pct, rel=0.01)

    def test_missing_values_structure(self, agent):
        df = _make_df_with_nulls()
        result = agent.analyze_quality(df)
        for col, info in result["missing_values"].items():
            assert "count" in info
            assert "percentage" in info


# ---------------------------------------------------------------------------
# TestAnalyzeStatistics
# ---------------------------------------------------------------------------

class TestAnalyzeStatistics:
    def test_returns_dict(self, agent):
        df = _make_df()
        structure = agent.analyze_structure(df)
        result = agent.analyze_statistics(df, structure)
        assert isinstance(result, dict)

    def test_numeric_stats_present_when_numeric_cols(self, agent):
        df = _make_df()
        structure = agent.analyze_structure(df)
        result = agent.analyze_statistics(df, structure)
        assert "numeric" in result

    def test_numeric_stats_has_describe_keys(self, agent):
        df = _make_df()
        structure = agent.analyze_structure(df)
        result = agent.analyze_statistics(df, structure)
        # describe() keys: count, mean, std, min, 25%, 50%, 75%, max
        assert "age" in result["numeric"]
        assert "mean" in result["numeric"]["age"]

    def test_categorical_stats_present(self, agent):
        df = _make_df()
        structure = agent.analyze_structure(df)
        result = agent.analyze_statistics(df, structure)
        assert "categorical" in result

    def test_categorical_stats_unique_values(self, agent):
        df = _make_df()
        structure = agent.analyze_structure(df)
        result = agent.analyze_statistics(df, structure)
        assert "department" in result["categorical"]
        assert result["categorical"]["department"]["unique_values"] == 3

    def test_categorical_stats_top5(self, agent):
        df = _make_df()
        structure = agent.analyze_structure(df)
        result = agent.analyze_statistics(df, structure)
        assert "top_5" in result["categorical"]["department"]

    def test_correlations_when_multiple_numeric_cols(self, agent):
        df = pd.DataFrame({
            "a": [1, 2, 3, 4, 5],
            "b": [2, 4, 6, 8, 10],  # perfectly correlated with a
            "c": [5, 4, 3, 2, 1],  # perfectly negatively correlated with a
        })
        structure = agent.analyze_structure(df)
        result = agent.analyze_statistics(df, structure)
        assert "correlations" in result
        assert len(result["correlations"]) > 0

    def test_correlations_absent_with_single_numeric_col(self, agent):
        df = pd.DataFrame({
            "value": [1, 2, 3, 4, 5],
            "label": ["a", "b", "c", "d", "e"],
        })
        structure = agent.analyze_structure(df)
        result = agent.analyze_statistics(df, structure)
        assert "correlations" not in result

    def test_correlations_sorted_by_absolute_value(self, agent):
        df = pd.DataFrame({
            "x": [1, 2, 3, 4, 5],
            "y": [2, 4, 6, 8, 10],
            "z": [5, 3, 1, -1, -3],
        })
        structure = agent.analyze_structure(df)
        result = agent.analyze_statistics(df, structure)
        if "correlations" in result and len(result["correlations"]) > 1:
            corr_vals = [abs(c["correlation"]) for c in result["correlations"]]
            assert corr_vals == sorted(corr_vals, reverse=True)

    def test_no_numeric_stats_when_no_numeric_cols(self, agent):
        df = pd.DataFrame({
            "cat1": ["a", "b", "c"],
            "cat2": ["x", "y", "z"],
        })
        structure = agent.analyze_structure(df)
        result = agent.analyze_statistics(df, structure)
        assert "numeric" not in result


# ---------------------------------------------------------------------------
# TestGenerateReport
# ---------------------------------------------------------------------------

class TestGenerateReport:
    def test_returns_dict(self, agent):
        df = _make_df()
        structure = agent.analyze_structure(df)
        quality = agent.analyze_quality(df)
        stats = agent.analyze_statistics(df, structure)
        result = agent.generate_report(df, structure, quality, stats, "test.csv")
        assert isinstance(result, dict)

    def test_result_has_report_key(self, agent):
        df = _make_df()
        structure = agent.analyze_structure(df)
        quality = agent.analyze_quality(df)
        stats = agent.analyze_statistics(df, structure)
        result = agent.generate_report(df, structure, quality, stats, "test.csv")
        assert "report" in result

    def test_result_has_structure(self, agent):
        df = _make_df()
        structure = agent.analyze_structure(df)
        quality = agent.analyze_quality(df)
        stats = agent.analyze_statistics(df, structure)
        result = agent.generate_report(df, structure, quality, stats, "test.csv")
        assert "structure" in result
        assert result["structure"] == structure

    def test_result_has_quality(self, agent):
        df = _make_df()
        structure = agent.analyze_structure(df)
        quality = agent.analyze_quality(df)
        stats = agent.analyze_statistics(df, structure)
        result = agent.generate_report(df, structure, quality, stats, "test.csv")
        assert "quality" in result
        assert result["quality"] == quality

    def test_result_has_stats(self, agent):
        df = _make_df()
        structure = agent.analyze_structure(df)
        quality = agent.analyze_quality(df)
        stats = agent.analyze_statistics(df, structure)
        result = agent.generate_report(df, structure, quality, stats, "test.csv")
        assert "stats" in result

    def test_result_has_generated_at(self, agent):
        df = _make_df()
        structure = agent.analyze_structure(df)
        quality = agent.analyze_quality(df)
        stats = agent.analyze_statistics(df, structure)
        result = agent.generate_report(df, structure, quality, stats, "test.csv")
        assert "generated_at" in result

    def test_llm_generate_called(self, agent):
        df = _make_df()
        structure = agent.analyze_structure(df)
        quality = agent.analyze_quality(df)
        stats = agent.analyze_statistics(df, structure)
        agent.generate_report(df, structure, quality, stats, "test.csv")
        agent.llm_client.generate.assert_called_once()

    def test_report_is_string(self, agent):
        df = _make_df()
        structure = agent.analyze_structure(df)
        quality = agent.analyze_quality(df)
        stats = agent.analyze_statistics(df, structure)
        result = agent.generate_report(df, structure, quality, stats, "test.csv")
        assert isinstance(result["report"], str)

    def test_llm_called_with_temperature(self, agent):
        df = _make_df()
        structure = agent.analyze_structure(df)
        quality = agent.analyze_quality(df)
        stats = agent.analyze_statistics(df, structure)
        agent.generate_report(df, structure, quality, stats, "data.csv")
        call_kwargs = agent.llm_client.generate.call_args
        assert call_kwargs is not None
        _, kwargs = call_kwargs
        assert kwargs.get("temperature") == 0.5


# ---------------------------------------------------------------------------
# TestRunPipeline
# ---------------------------------------------------------------------------

def _run_with_tmp_output(agent, csv_file, tmp_path):
    """Helper: run agent.run() redirecting output to tmp_path."""
    (tmp_path / "output").mkdir(exist_ok=True)
    with patch(
        "agents.dataset_analyzer.os.path.abspath",
        return_value=str(tmp_path / "agents" / "dataset_analyzer.py"),
    ):
        return agent.run(str(csv_file))


class TestRunPipeline:
    def test_run_returns_dict(self, agent, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
        result = _run_with_tmp_output(agent, csv_file, tmp_path)
        assert isinstance(result, dict)

    def test_run_contains_report(self, agent, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("x,y\n10,20\n30,40\n", encoding="utf-8")
        result = _run_with_tmp_output(agent, csv_file, tmp_path)
        assert "report" in result

    def test_run_contains_filename(self, agent, tmp_path):
        csv_file = tmp_path / "mydata.csv"
        csv_file.write_text("col\n1\n2\n", encoding="utf-8")
        result = _run_with_tmp_output(agent, csv_file, tmp_path)
        assert result.get("filename") == "mydata.csv"

    def test_run_saves_md_file(self, agent, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
        result = _run_with_tmp_output(agent, csv_file, tmp_path)
        assert "md_path" in result

    def test_run_calls_analyze_structure(self, agent, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b\n1,2\n", encoding="utf-8")
        with patch.object(agent, "analyze_structure", wraps=agent.analyze_structure) as mock_s:
            _run_with_tmp_output(agent, csv_file, tmp_path)
        mock_s.assert_called_once()

    def test_run_calls_analyze_quality(self, agent, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b\n1,2\n", encoding="utf-8")
        with patch.object(agent, "analyze_quality", wraps=agent.analyze_quality) as mock_q:
            _run_with_tmp_output(agent, csv_file, tmp_path)
        mock_q.assert_called_once()

    def test_run_calls_analyze_statistics(self, agent, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b\n1,2\n", encoding="utf-8")
        with patch.object(agent, "analyze_statistics", wraps=agent.analyze_statistics) as mock_st:
            _run_with_tmp_output(agent, csv_file, tmp_path)
        mock_st.assert_called_once()

    def test_run_calls_generate_report(self, agent, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b\n1,2\n", encoding="utf-8")
        with patch.object(agent, "generate_report", wraps=agent.generate_report) as mock_r:
            _run_with_tmp_output(agent, csv_file, tmp_path)
        mock_r.assert_called_once()

    def test_run_with_larger_dataset(self, agent, tmp_path):
        csv_file = tmp_path / "large.csv"
        rows = ["id,value,category"] + [
            f"{i},{i*10},{'A' if i % 2 == 0 else 'B'}" for i in range(50)
        ]
        csv_file.write_text("\n".join(rows), encoding="utf-8")
        result = _run_with_tmp_output(agent, csv_file, tmp_path)
        assert result["structure"]["num_rows"] == 50


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


class TestMainFunction:
    def test_main_missing_file_prints_error(self, capsys):
        with patch("sys.argv", ["dataset_analyzer.py", "/nonexistent/data.csv"]):
            from agents.dataset_analyzer import main

            main()
        out = capsys.readouterr().out
        assert "introuvable" in out.lower() or "❌" in out

    def test_main_runs_with_valid_file(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")

        mock_result = {"report": "R" * 1001, "md_path": str(tmp_path / "report.md")}
        with patch("sys.argv", ["dataset_analyzer.py", str(csv_file)]):
            with patch(
                "agents.dataset_analyzer.DatasetAnalyzerAgent"
            ) as MockAgent:
                MockAgent.return_value.run.return_value = mock_result
                from agents.dataset_analyzer import main

                main()
