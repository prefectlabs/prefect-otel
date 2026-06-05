"""Settings for the Prefect OpenTelemetry integration."""

from __future__ import annotations

from prefect.settings.base import PrefectBaseSettings, build_settings_config
from pydantic import Field


class PrefectOtelSettings(PrefectBaseSettings):
    """Settings for controlling Prefect OpenTelemetry plugin behavior."""

    model_config = build_settings_config(("integrations", "otel"))

    auto_instrument: bool = Field(
        default=True,
        description=(
            "Whether the Prefect OpenTelemetry integration should bootstrap "
            "OpenTelemetry auto-instrumentation when Prefect imports. Set to "
            "false to disable auto-instrumentation."
        ),
    )

    require_auto_instrument: bool = Field(
        default=False,
        description=(
            "Whether OpenTelemetry auto-instrumentation bootstrap failures should "
            "raise instead of being logged and ignored."
        ),
    )
