#!/usr/bin/env python3
"""Run a reproducible, metadata-only smoke/benchmark against a live local Ollama."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tusker_ai.providers.ollama import OllamaProvider
from tusker_ai.runtime import InferenceRuntime
from tusker_ai.types import InferenceRequest


def _read_meminfo():
    values = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            key, _, raw = line.partition(":")
            fields = raw.strip().split()
            if fields and fields[0].isdigit():
                values[key] = int(fields[0]) * (1024 if len(fields) > 1 and fields[1] == "kB" else 1)
    except (OSError, ValueError):
        pass
    return values


def _cpu_metadata():
    records = []
    try:
        raw = Path("/proc/cpuinfo").read_text(encoding="utf-8")
        for block in raw.split("\n\n"):
            record = {}
            for line in block.splitlines():
                key, sep, value = line.partition(":")
                if sep:
                    record[key.strip().lower()] = value.strip()
            if record:
                records.append(record)
    except OSError:
        pass
    first = records[0] if records else {}
    physical = {
        (item.get("physical id"), item.get("core id"))
        for item in records if item.get("physical id") is not None and item.get("core id") is not None
    }
    flags = first.get("flags", first.get("features", "")).split()
    return {
        "model": platform.processor() or first.get("model name") or first.get("hardware"),
        "logical_cores": os.cpu_count(),
        "physical_cores": len(physical) or None,
        "instruction_flags": sorted(flags) if flags else None,
    }


def _cgroup_memory():
    result = {"current_bytes": None, "limit_bytes": None}
    for key, filename in (("current_bytes", "memory.current"), ("limit_bytes", "memory.max")):
        try:
            raw = Path("/sys/fs/cgroup", filename).read_text(encoding="ascii").strip()
            if raw != "max":
                result[key] = int(raw)
        except (OSError, ValueError):
            pass
    return result


def _gpu_metadata():
    executable = shutil.which("nvidia-smi")
    if not executable:
        return {"vendor": None, "devices": None, "probe": "nvidia-smi unavailable; other GPU vendors are not probed"}
    try:
        completed = subprocess.run(
            [executable, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=2, check=False,
        )
        if completed.returncode != 0:
            return {"vendor": "NVIDIA", "devices": None, "probe": "nvidia-smi query failed"}
        devices = []
        for line in completed.stdout.splitlines():
            parts = [part.strip() for part in line.split(",")]
            if len(parts) == 3:
                try:
                    memory_mib = int(parts[1])
                except ValueError:
                    memory_mib = None
                devices.append({"name": parts[0], "dedicated_vram_bytes": memory_mib * 1024 * 1024 if memory_mib is not None else None, "driver_version": parts[2]})
        return {"vendor": "NVIDIA", "devices": devices, "probe": "nvidia-smi"}
    except (OSError, subprocess.TimeoutExpired):
        return {"vendor": "NVIDIA", "devices": None, "probe": "nvidia-smi unavailable or timed out"}


def _storage_metadata(output_path):
    target = Path(output_path).expanduser().resolve().parent
    try:
        usage = shutil.disk_usage(target)
        return {"path_role": "report_output_parent", "total_bytes": usage.total, "free_bytes": usage.free}
    except OSError:
        return {"path_role": "report_output_parent", "total_bytes": None, "free_bytes": None}


def _client_peak_rss_bytes():
    # resource is unavailable on some platforms; this is the harness process only.
    try:
        import resource
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(value if sys.platform == "darwin" else value * 1024)
    except (ImportError, OSError, ValueError):
        return None


def hardware_metadata(output_path=None):
    memory = _read_meminfo()
    return {
        "os": platform.platform(),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "cpu": _cpu_metadata(),
        "memory_total_bytes": memory.get("MemTotal"),
        "memory_available_bytes": memory.get("MemAvailable"),
        "cgroup_memory": _cgroup_memory(),
        "gpu": _gpu_metadata(),
        "storage": _storage_metadata(output_path or "."),
    }


def runtime_revision():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            timeout=2, check=False,
        )
        value = result.stdout.strip()
        return value if result.returncode == 0 and len(value) == 40 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--model", required=True)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--output", default="ollama-smoke-report.json")
    args = parser.parse_args()
    if not 1 <= args.repeats <= 20:
        parser.error("--repeats must be between 1 and 20")

    provider = OllamaProvider(args.endpoint, read_timeout=2.0)
    version = provider.version()
    if version is None or not provider.health():
        raise SystemExit("Local Ollama is not healthy at the configured loopback endpoint")
    runtime = InferenceRuntime(provider)
    results = []
    for index in range(args.repeats):
        request = InferenceRequest(
            request_id=f"orbit-smoke-{index + 1}", model=args.model,
            messages=[{"role": "user", "content": "Reply with exactly: TUSKER-OLLAMA-OK"}],
            max_output_tokens=32, context_limit=2048, timeout_seconds=60.0,
        )
        started = time.monotonic()
        first_token = None
        text_parts = []
        usage = {}
        for event in runtime.infer(request):
            elapsed = time.monotonic() - started
            if event.event_type == "text_delta":
                if first_token is None:
                    first_token = elapsed
                text_parts.append(str(event.payload.get("delta", "")))
            elif event.event_type == "usage":
                usage = dict(event.payload)
            elif event.event_type == "failed":
                raise SystemExit("Provider returned a failure terminal event")
        total = time.monotonic() - started
        output = "".join(text_parts)
        if "TUSKER-OLLAMA-OK" not in output:
            raise SystemExit("Inference smoke assertion failed; response content is not written to the report")
        output_tokens = usage.get("output_tokens")
        results.append({
            "run": index + 1,
            "request_order": "first_request" if index == 0 else "subsequent_request",
            "model_load_state": "unknown_not_measured",
            "total_seconds": round(total, 6),
            "time_to_first_token_seconds": round(first_token, 6) if first_token is not None else None,
            "prompt_tokens": usage.get("input_tokens"), "output_tokens": output_tokens,
            "generation_tokens_per_second": round(output_tokens / max(total - (first_token or 0), 1e-9), 4)
            if isinstance(output_tokens, int) and first_token is not None and total > first_token else None,
            "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
        })
    totals = [item["total_seconds"] for item in results]
    report = {
        "schema_version": 2, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "ollama", "provider_version": version, "endpoint_scope": "loopback",
        "model_id": args.model, "model_sha256": os.environ.get("TUSKER_MODEL_SHA256"),
        "runtime_package": "TuskerOS tusker-ai", "runtime_git_sha": runtime_revision(),
        "python": platform.python_version(), "hardware": hardware_metadata(args.output),
        "client_process_peak_rss_bytes": _client_peak_rss_bytes(),
        "client_process_peak_rss_scope": "smoke harness process only; does not measure Ollama daemon RSS",
        "network_state": "connected for local endpoint; no cloud fallback configured",
        "prompt_id": "fixed-tusker-smoke-v1", "repeats": args.repeats,
        "median_total_seconds": statistics.median(totals), "runs": results,
        "limitations": [
            "First-request timing is not a cold model-load measurement; Ollama model residency is not observed",
            "GPU discovery is NVIDIA-only via nvidia-smi; other vendors and shared GPU memory are not probed",
            "Peak RSS is for the client smoke harness, not the Ollama daemon",
            "Model digest is null unless TUSKER_MODEL_SHA256 is supplied and independently verified",
            "This report does not establish quality beyond the fixed smoke assertion",
        ],
    }
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "report": args.output, "provider_version": version, "runs": len(results)}, sort_keys=True))


if __name__ == "__main__":
    main()
