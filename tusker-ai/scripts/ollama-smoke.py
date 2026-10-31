#!/usr/bin/env python3
"""Run a reproducible, metadata-only smoke/benchmark against a live local Ollama."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tusker_ai.providers.ollama import OllamaProvider
from tusker_ai.runtime import InferenceRuntime
from tusker_ai.types import InferenceRequest


def hardware_metadata():
    mem_total = mem_available = None
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            if line.startswith("MemTotal:"):
                mem_total = int(line.split()[1]) * 1024
            elif line.startswith("MemAvailable:"):
                mem_available = int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    cpu = platform.processor() or None
    if not cpu:
        try:
            for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
                if line.lower().startswith("model name"):
                    cpu = line.split(":", 1)[1].strip()
                    break
        except OSError:
            pass
    return {
        "os": platform.platform(), "kernel": platform.release(),
        "architecture": platform.machine(), "cpu_model": cpu,
        "logical_cores": os.cpu_count(), "memory_total_bytes": mem_total,
        "memory_available_bytes": mem_available, "gpu": None,
        "gpu_note": "Not probed by this portable smoke harness; do not infer GPU availability.",
    }


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
            "run": index + 1, "cold_or_warm": "first-run" if index == 0 else "warm",
            "total_seconds": round(total, 6),
            "time_to_first_token_seconds": round(first_token, 6) if first_token is not None else None,
            "prompt_tokens": usage.get("input_tokens"), "output_tokens": output_tokens,
            "generation_tokens_per_second": round(output_tokens / max(total - (first_token or 0), 1e-9), 4)
            if isinstance(output_tokens, int) and first_token is not None and total > first_token else None,
            "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
        })
    totals = [item["total_seconds"] for item in results]
    report = {
        "schema_version": 1, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "ollama", "provider_version": version, "endpoint_scope": "loopback",
        "model_id": args.model, "model_sha256": os.environ.get("TUSKER_MODEL_SHA256"),
        "runtime_package": "TuskerOS tusker-ai initial adapter", "python": platform.python_version(),
        "hardware": hardware_metadata(), "network_state": "connected for local endpoint; no cloud fallback configured",
        "prompt_id": "fixed-tusker-smoke-v1", "repeats": args.repeats,
        "median_total_seconds": statistics.median(totals), "runs": results,
        "limitations": [
            "GPU metadata is not probed",
            "Model digest is null unless TUSKER_MODEL_SHA256 is supplied and independently verified",
            "This report does not establish quality beyond the fixed smoke assertion",
        ],
    }
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "report": args.output, "provider_version": version, "runs": len(results)}, sort_keys=True))


if __name__ == "__main__":
    main()
