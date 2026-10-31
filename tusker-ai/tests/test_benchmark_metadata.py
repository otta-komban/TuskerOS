"""Unit tests for portable benchmark environment metadata."""
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "ollama-smoke.py"
SPEC = importlib.util.spec_from_file_location("ollama_smoke", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_hardware_metadata_has_explicit_unknown_and_scope_fields(tmp_path):
    metadata = MODULE.hardware_metadata(tmp_path / "report.json")
    assert set(("os", "kernel", "architecture", "cpu", "memory_total_bytes",
                "memory_available_bytes", "cgroup_memory", "gpu", "storage")) <= set(metadata)
    assert "logical_cores" in metadata["cpu"]
    assert "physical_cores" in metadata["cpu"]
    assert set(metadata["cgroup_memory"]) == {"current_bytes", "limit_bytes"}
    assert metadata["storage"]["path_role"] == "report_output_parent"
    assert metadata["storage"]["total_bytes"] is None or metadata["storage"]["total_bytes"] > 0
    assert metadata["gpu"]["probe"]


def test_gpu_probe_is_bounded_and_does_not_assume_vendor(monkeypatch):
    monkeypatch.setattr(MODULE.shutil, "which", lambda _: None)
    result = MODULE._gpu_metadata()
    assert result["vendor"] is None
    assert result["devices"] is None
    assert "not probed" in result["probe"]


def test_client_rss_is_named_as_client_measurement():
    assert MODULE._client_peak_rss_bytes() is None or MODULE._client_peak_rss_bytes() >= 0
