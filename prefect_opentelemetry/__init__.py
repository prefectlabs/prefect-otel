"""Prefect plugin for OpenTelemetry auto-instrumentation."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from prefect.plugins import HookContext, SetupResult, register_hook

from prefect_opentelemetry.settings import PrefectOtelSettings

PREFECT_PLUGIN_API_REQUIRES = ">=0.1,<1"

try:
    __version__ = version("prefect-otel")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"


@register_hook
def setup_environment(*, ctx: HookContext) -> SetupResult | None:
    """Bootstrap OpenTelemetry auto-instrumentation for this Prefect process."""
    settings = PrefectOtelSettings()
    logger = ctx.logger_factory("prefect-otel")

    if not settings.auto_instrument:
        logger.debug(
            "PREFECT_INTEGRATIONS_OTEL_AUTO_INSTRUMENT is false; "
            "skipping OpenTelemetry bootstrap"
        )
        return None

    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.auto_instrumentation import initialize

        if type(trace.get_tracer_provider()).__name__ != "ProxyTracerProvider":
            logger.debug(
                "OpenTelemetry provider already configured; skipping bootstrap"
            )
            return SetupResult(
                env={},
                note="OpenTelemetry auto-instrumentation already configured",
            )

        initialize()
    except ImportError as exc:
        logger.error(
            "OpenTelemetry auto-instrumentation requested but not installed (%s); "
            "try installing opentelemetry-distro and opentelemetry-exporter-otlp",
            exc,
        )
        if settings.require_auto_instrument:
            raise
        return None
    except Exception:
        logger.exception("Failed to bootstrap OpenTelemetry auto-instrumentation")
        if settings.require_auto_instrument:
            raise
        return None

    return SetupResult(
        env={},
        note="Bootstrapped OpenTelemetry auto-instrumentation",
    )


__all__ = [
    "PREFECT_PLUGIN_API_REQUIRES",
    "PrefectOtelSettings",
    "__version__",
    "setup_environment",
]
