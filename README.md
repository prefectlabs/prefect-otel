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

Then run Prefect normally. For example, start the worker that will execute your
deployments:

```bash
prefect worker start --pool my-pool
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

### Deployment Configuration

The key requirement is that both the Prefect plugin setting and the `OTEL_*`
variables are present in the environment of the process that imports Prefect
and runs your flow code.

Common places to set them:

- The worker process environment for local and process-based workers.
- Work pool job variables for infrastructure-backed deployments.
- Container image entrypoints or Kubernetes, Docker, ECS, Cloud Run, or other
  job environment settings.
- Deployment environment overrides when your deployment infrastructure supports
  them.

For a container image, install the package and OpenTelemetry instrumentation in
the image that will run flows:

```dockerfile
FROM prefecthq/prefect:3-python3.12

RUN pip install prefect-otel \
    && opentelemetry-bootstrap -a install
```

Then provide runtime configuration through your work pool, deployment, or
platform environment:

```bash
PREFECT_PLUGINS_ENABLED=1
OTEL_SERVICE_NAME=my-prefect-flow
OTEL_TRACES_EXPORTER=otlp
OTEL_METRICS_EXPORTER=none
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

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
