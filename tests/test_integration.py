"""Integration tests for Prefect/OpenTelemetry spawn behavior."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import TypedDict


class ProviderSnapshot(TypedDict):
    """Serialized tracer provider identity."""

    module: str
    name: str


class SpawnRunResult(TypedDict):
    """Serialized parent and child tracer provider identities."""

    parent: ProviderSnapshot
    child: ProviderSnapshot


def _write_driver(path: Path) -> None:
    """Write a small script that records parent and child tracer providers."""
    path.write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            import json
            import os
            from os.path import abspath, dirname
            from pathlib import Path

            import asyncio

            from opentelemetry import trace
            from opentelemetry.instrumentation import auto_instrumentation
            from prefect import flow
            from prefect.client.orchestration import get_client
            from prefect.runner import Runner
            from prefect.testing.utilities import prefect_test_harness

            RESULT_DIR = Path(os.environ["PREFECT_OTEL_TEST_RESULT_DIR"])


            def provider_snapshot() -> dict[str, str]:
                provider = trace.get_tracer_provider()
                provider_type = type(provider)
                return {
                    "module": provider_type.__module__,
                    "name": provider_type.__name__,
                }


            def remove_auto_instrumentation_pythonpath() -> None:
                auto_instrumentation_path = dirname(
                    abspath(auto_instrumentation.__file__)
                )
                pythonpath = os.environ.get("PYTHONPATH")
                if not pythonpath:
                    return
                os.environ["PYTHONPATH"] = os.pathsep.join(
                    path
                    for path in pythonpath.split(os.pathsep)
                    if path != auto_instrumentation_path
                )


            @flow
            def inspect_child_provider() -> None:
                (RESULT_DIR / "child.json").write_text(
                    json.dumps(provider_snapshot())
                )


            async def run_engine_command_subprocess() -> int | None:
                runner = Runner(name="prefect-otel-integration-test")
                deployment = await inspect_child_provider.to_deployment(__file__)
                deployment_id = await deployment.apply()
                async with get_client() as client:
                    flow_run = await client.create_flow_run_from_deployment(
                        deployment_id
                    )
                return await runner._run_process(
                    flow_run,
                    entrypoint=f"{__file__}:inspect_child_provider",
                    stream_output=False,
                )


            def main() -> None:
                RESULT_DIR.mkdir(parents=True, exist_ok=True)
                with prefect_test_harness():
                    (RESULT_DIR / "parent.json").write_text(
                        json.dumps(provider_snapshot())
                    )
                    remove_auto_instrumentation_pythonpath()
                    returncode = asyncio.run(run_engine_command_subprocess())
                    if returncode:
                        raise RuntimeError(
                            f"child flow process exited with {returncode}"
                        )


            if __name__ == "__main__":
                main()
            """
        )
    )


def _run_spawn_driver(
    *,
    tmp_path: Path,
    enable_plugin: bool,
) -> SpawnRunResult:
    """Run the spawn driver through the real opentelemetry-instrument command."""
    otel_instrument = shutil.which("opentelemetry-instrument")
    assert otel_instrument is not None, "opentelemetry-instrument is not installed"

    driver = tmp_path / "driver.py"
    result_dir = tmp_path / ("enabled" if enable_plugin else "disabled")
    _write_driver(driver)

    project_root = Path(__file__).resolve().parents[1]
    pythonpath_parts = [str(project_root)]
    if os.environ.get("PYTHONPATH"):
        pythonpath_parts.append(os.environ["PYTHONPATH"])

    env = os.environ.copy()
    env.update(
        {
            "OTEL_SERVICE_NAME": "prefect-otel-test",
            "OTEL_TRACES_EXPORTER": "console",
            "OTEL_METRICS_EXPORTER": "none",
            "OTEL_LOGS_EXPORTER": "none",
            "PREFECT_OTEL_TEST_RESULT_DIR": str(result_dir),
            "PREFECT_PLUGINS_ALLOW": "prefect_otel",
            "PYTHONPATH": os.pathsep.join(pythonpath_parts),
        }
    )
    if enable_plugin:
        env["PREFECT_PLUGINS_ENABLED"] = "1"
        env["PREFECT_INTEGRATIONS_OTEL_AUTO_INSTRUMENT"] = "true"
    else:
        env["PREFECT_PLUGINS_ENABLED"] = "0"
        env.pop("PREFECT_INTEGRATIONS_OTEL_AUTO_INSTRUMENT", None)

    completed = subprocess.run(
        [otel_instrument, sys.executable, str(driver)],
        cwd=project_root,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=90,
        check=False,
    )
    assert completed.returncode == 0, (
        f"driver failed\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )

    parent = json.loads((result_dir / "parent.json").read_text())
    child = json.loads((result_dir / "child.json").read_text())
    return {"parent": parent, "child": child}


def test_prefect_otel_plugin_bootstraps_auto_instrumentation_across_spawn(
    tmp_path: Path,
) -> None:
    """The plugin should fix the parent/child auto-instrumentation gap."""
    without_plugin = _run_spawn_driver(tmp_path=tmp_path, enable_plugin=False)
    with_plugin = _run_spawn_driver(tmp_path=tmp_path, enable_plugin=True)

    assert without_plugin["parent"]["name"] != "ProxyTracerProvider"
    assert without_plugin["child"] == {
        "module": "opentelemetry.trace",
        "name": "ProxyTracerProvider",
    }

    assert with_plugin["parent"]["name"] != "ProxyTracerProvider"
    assert with_plugin["child"]["name"] != "ProxyTracerProvider"
    assert with_plugin["child"]["module"].startswith("opentelemetry.sdk.trace")
