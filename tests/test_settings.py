"""Tests for Prefect OpenTelemetry integration settings."""

from __future__ import annotations

import os
from pathlib import Path

from prefect_opentelemetry.settings import PrefectOtelSettings


def test_default_settings_enable_auto_instrumentation() -> None:
    """Defaults should auto-instrument unless users opt out."""
    settings = PrefectOtelSettings()

    assert settings.auto_instrument is True
    assert settings.require_auto_instrument is False


def test_opt_out_via_environment_variables(
    monkeypatch: object,
) -> None:
    """Settings should load from Prefect integration env vars."""
    from pytest import MonkeyPatch

    assert isinstance(monkeypatch, MonkeyPatch)
    monkeypatch.setenv("PREFECT_INTEGRATIONS_OTEL_AUTO_INSTRUMENT", "false")
    monkeypatch.setenv("PREFECT_INTEGRATIONS_OTEL_REQUIRE_AUTO_INSTRUMENT", "true")

    settings = PrefectOtelSettings()

    assert settings.auto_instrument is False
    assert settings.require_auto_instrument is True


def test_opt_out_via_dot_env_file(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    """Settings should load from .env files."""
    from pytest import MonkeyPatch

    assert isinstance(monkeypatch, MonkeyPatch)
    (tmp_path / ".env").write_text(
        "PREFECT_INTEGRATIONS_OTEL_AUTO_INSTRUMENT=false\n"
        "PREFECT_INTEGRATIONS_OTEL_REQUIRE_AUTO_INSTRUMENT=true\n"
    )
    monkeypatch.chdir(tmp_path)

    settings = PrefectOtelSettings()

    assert settings.auto_instrument is False
    assert settings.require_auto_instrument is True


def test_opt_out_via_prefect_toml_file(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    """Settings should load from prefect.toml."""
    from pytest import MonkeyPatch

    assert isinstance(monkeypatch, MonkeyPatch)
    (tmp_path / "prefect.toml").write_text(
        "[integrations.otel]\nauto_instrument = false\nrequire_auto_instrument = true\n"
    )
    monkeypatch.chdir(tmp_path)

    settings = PrefectOtelSettings()

    assert settings.auto_instrument is False
    assert settings.require_auto_instrument is True


def test_opt_out_via_pyproject_toml_file(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    """Settings should load from pyproject.toml."""
    from pytest import MonkeyPatch

    assert isinstance(monkeypatch, MonkeyPatch)
    (tmp_path / "pyproject.toml").write_text(
        "[tool.prefect.integrations.otel]\n"
        "auto_instrument = false\n"
        "require_auto_instrument = true\n"
    )
    monkeypatch.chdir(tmp_path)

    settings = PrefectOtelSettings()

    assert settings.auto_instrument is False
    assert settings.require_auto_instrument is True


def test_to_environment_variables_uses_integration_names() -> None:
    """Exported env vars should use Prefect integration setting names."""
    settings = PrefectOtelSettings(
        auto_instrument=True,
        require_auto_instrument=True,
    )

    env = settings.to_environment_variables()

    assert env == {
        "PREFECT_INTEGRATIONS_OTEL_AUTO_INSTRUMENT": "True",
        "PREFECT_INTEGRATIONS_OTEL_REQUIRE_AUTO_INSTRUMENT": "True",
    }
    assert not any(key.startswith("PREFECT_OTEL_") for key in env)
    assert os.environ.get("PREFECT_OTEL_AUTO_INSTRUMENT") is None
