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

Install `prefect-otel` in the environment that runs your Prefect flows. For
deployed flows, this usually means the worker image, job image, virtual
environment, or infrastructure block used by the deployment.

Enable Prefect plugins and opt in to this integration where your flow code runs:

```bash
export PREFECT_PLUGINS_ENABLED=1
export PREFECT_INTEGRATIONS_OTEL_AUTO_INSTRUMENT=true
```

Configure OpenTelemetry with standard `OTEL_*` environment variables:

```bash
export OTEL_SERVICE_NAME=my-prefect-flow
export OTEL_TRACES_EXPORTER=otlp
export OTEL_METRICS_EXPORTER=none
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

For deployments, put these variables wherever the flow-run process receives its
environment, such as work pool job variables, infrastructure block settings,
deployment environment overrides, a container image entrypoint, or the worker
process environment.

Then run Prefect normally. For example, start the worker for the work pool that
will execute your deployments:

```bash
prefect worker start --pool my-pool
```

If you already wrap the worker or application entrypoint with
`opentelemetry-instrument`, keep that wrapper in place. This integration handles
Prefect processes that are started later and need to configure OpenTelemetry
from the inherited environment.

The plugin runs when Prefect is imported. When
`PREFECT_INTEGRATIONS_OTEL_AUTO_INSTRUMENT=true`, it calls OpenTelemetry's
programmatic auto-instrumentation initializer in each Prefect process. This
allows spawned flow-run subprocesses to configure OpenTelemetry from inherited
`OTEL_*` variables even though the parent process's in-memory SDK setup is not
inherited across Python `spawn`.

## Settings

Settings follow Prefect integration naming conventions and can be configured
with environment variables, `.env`, `prefect.toml`, or `pyproject.toml`.

| Setting | Environment variable | Default |
| --- | --- | --- |
| `auto_instrument` | `PREFECT_INTEGRATIONS_OTEL_AUTO_INSTRUMENT` | `false` |
| `require_auto_instrument` | `PREFECT_INTEGRATIONS_OTEL_REQUIRE_AUTO_INSTRUMENT` | `false` |

`prefect.toml`:

```toml
[integrations.otel]
auto_instrument = true
require_auto_instrument = false
```

`pyproject.toml`:

```toml
[tool.prefect.integrations.otel]
auto_instrument = true
require_auto_instrument = false
```

If `require_auto_instrument` is true, initialization failures are re-raised.
Use this with `PREFECT_PLUGINS_STRICT=1` when startup should fail instead of
running without OpenTelemetry auto-instrumentation.

## Diagnostics

Prefect can show plugin discovery and hook results:

```bash
prefect plugins diagnose
```
