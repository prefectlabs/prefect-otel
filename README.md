# prefect-otel

`prefect-otel` is an experimental Prefect integration for OpenTelemetry.

This package provides a Prefect plugin hook that bootstraps OpenTelemetry
Python auto-instrumentation in Prefect flow-run subprocesses.

## Experimental Status

This package is experimental. Public settings, behavior, and compatibility
guarantees may change before a 1.0 release.

## Installation

```bash
pip install prefect-otel
```

OpenTelemetry automatic instrumentation still requires the normal
OpenTelemetry packages and instrumentation libraries. The package depends on
the OpenTelemetry distro and OTLP exporter, but users should still run
bootstrap in their target environment when they want library-specific
instrumentation:

```bash
opentelemetry-bootstrap -a install
```

## Usage

No flow code changes are required. The environment that actually executes your
flow must have:

- `prefect-otel` installed.
- Prefect plugins enabled with `PREFECT_PLUGINS_ENABLED=1`.
- Standard OpenTelemetry `OTEL_*` environment variables configured.

For deployed flows, this usually means the worker environment, job image,
virtual environment, or work pool job configuration used by the deployment.

Enable Prefect plugins in that same runtime:

```bash
export PREFECT_PLUGINS_ENABLED=1
```

Once Prefect loads this plugin, OpenTelemetry auto-instrumentation is enabled
by default.

Configure OpenTelemetry with standard `OTEL_*` environment variables in that
same runtime:

```bash
export OTEL_SERVICE_NAME=my-prefect-flow
export OTEL_TRACES_EXPORTER=otlp
export OTEL_METRICS_EXPORTER=none
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

For a flow run directly from Python, set the same variables before starting the
process:

```bash
python my_flow.py
```

The plugin runs when Prefect is imported. By default, it calls OpenTelemetry's
programmatic auto-instrumentation initializer in each Prefect process. This
allows spawned flow-run subprocesses to configure OpenTelemetry from inherited
`OTEL_*` variables even though the parent process's in-memory SDK setup is not
inherited across Python `spawn`.

You do not need to call `opentelemetry-instrument` in a custom Prefect command
to use this package. If you already wrap a worker or application entrypoint
with `opentelemetry-instrument`, you can keep that wrapper; this integration
handles Prefect processes that are started later from the inherited
environment.

### Deployment Job Variables

For deployments, set these variables in `job_variables.env` so the process that
runs your flow receives them:

```yaml
deployments:
- name: my-deployment
  entrypoint: flows.py:my_flow
  work_pool:
    name: my-pool
    job_variables:
      env:
        PREFECT_PLUGINS_ENABLED: "1"
        OTEL_SERVICE_NAME: "my-prefect-flow"
        OTEL_TRACES_EXPORTER: "otlp"
        OTEL_METRICS_EXPORTER: "none"
        OTEL_EXPORTER_OTLP_ENDPOINT: "http://otel-collector:4317"
```

If you create deployments from Python, pass the same environment variables in
`job_variables`:

```python
from prefect import flow


@flow
def my_flow() -> None:
    ...


if __name__ == "__main__":
    my_flow.deploy(
        name="my-deployment",
        work_pool_name="my-pool",
        job_variables={
            "env": {
                "PREFECT_PLUGINS_ENABLED": "1",
                "OTEL_SERVICE_NAME": "my-prefect-flow",
                "OTEL_TRACES_EXPORTER": "otlp",
                "OTEL_METRICS_EXPORTER": "none",
                "OTEL_EXPORTER_OTLP_ENDPOINT": "http://otel-collector:4317",
            }
        },
    )
```

These examples configure OTLP trace export and disable metric export. Adjust the
`OTEL_*` values for your collector, exporter, and telemetry pipeline.

Common places to set them:

- Deployment `job_variables.env`.
- Work pool default job variables.
- Container image entrypoints or Kubernetes, Docker, ECS, Cloud Run, or other
  job environment settings.

For a container image, install the package and OpenTelemetry instrumentation in
the image that will run flows:

```dockerfile
FROM prefecthq/prefect:3-python3.12

RUN pip install prefect-otel \
    && opentelemetry-bootstrap -a install
```

The image installs the package and instrumentation libraries. The deployment
or work pool still needs the `job_variables.env` values shown above so the
flow process can configure OpenTelemetry at runtime.

### Disable Auto-Instrumentation

To disable the integration without uninstalling it, set:

```bash
export PREFECT_INTEGRATIONS_OTEL_AUTO_INSTRUMENT=false
```

## Settings

Settings follow Prefect integration naming conventions and can be configured
with environment variables, `.env`, `prefect.toml`, or `pyproject.toml`.

| Setting | Environment variable | Default |
| --- | --- | --- |
| `auto_instrument` | `PREFECT_INTEGRATIONS_OTEL_AUTO_INSTRUMENT` | `true` |
| `require_auto_instrument` | `PREFECT_INTEGRATIONS_OTEL_REQUIRE_AUTO_INSTRUMENT` | `false` |

`prefect.toml`:

```toml
[integrations.otel]
auto_instrument = false
require_auto_instrument = false
```

`pyproject.toml`:

```toml
[tool.prefect.integrations.otel]
auto_instrument = false
require_auto_instrument = false
```

If `require_auto_instrument` is true, initialization failures are re-raised.
Use this with `PREFECT_PLUGINS_STRICT=1` when startup should fail instead of
running without OpenTelemetry auto-instrumentation:

```bash
export PREFECT_PLUGINS_STRICT=1
export PREFECT_INTEGRATIONS_OTEL_REQUIRE_AUTO_INSTRUMENT=true
```

## Diagnostics

Prefect can show plugin discovery and hook results:

```bash
prefect plugins diagnose
```

If traces are missing, check that:

- `prefect-otel` is installed in the environment that runs the flow, not just
  in the environment where the deployment was built.
- `PREFECT_PLUGINS_ENABLED=1` is set where the flow code runs.
- The `OTEL_*` variables are inherited by the flow-run process.
- The relevant OpenTelemetry instrumentation libraries are installed.
- Your collector or exporter endpoint is reachable from the flow-run
  environment.
