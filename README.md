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

Enable Prefect plugins and opt in to this integration:

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

Then start Prefect flow execution normally, including through a work pool
command that is wrapped with `opentelemetry-instrument`:

```bash
opentelemetry-instrument prefect flow-run execute
```

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

