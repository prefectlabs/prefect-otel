"""Tests for the Prefect OpenTelemetry plugin hook."""

from __future__ import annotations

import builtins
import logging
import sys
from types import ModuleType
from typing import Any

import pytest
from prefect.plugins import HookContext, SetupResult
from prefect_opentelemetry import setup_environment


@pytest.fixture
def hook_context() -> HookContext:
    """Return a minimal Prefect plugin hook context."""
    return HookContext(
        prefect_version="3.7.0",
        api_url=None,
        logger_factory=logging.getLogger,
    )


def _install_fake_opentelemetry(
    monkeypatch: pytest.MonkeyPatch,
    *,
    provider: object,
    initialize: object,
) -> None:
    """Install fake OpenTelemetry modules into sys.modules."""
    opentelemetry = ModuleType("opentelemetry")
    trace = ModuleType("opentelemetry.trace")
    instrumentation = ModuleType("opentelemetry.instrumentation")
    auto_instrumentation = ModuleType(
        "opentelemetry.instrumentation.auto_instrumentation"
    )

    def get_tracer_provider() -> object:
        return provider

    trace.get_tracer_provider = get_tracer_provider  # type: ignore[attr-defined]
    auto_instrumentation.initialize = initialize  # type: ignore[attr-defined]
    opentelemetry.trace = trace  # type: ignore[attr-defined]
    instrumentation.auto_instrumentation = auto_instrumentation  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "opentelemetry", opentelemetry)
    monkeypatch.setitem(sys.modules, "opentelemetry.trace", trace)
    monkeypatch.setitem(sys.modules, "opentelemetry.instrumentation", instrumentation)
    monkeypatch.setitem(
        sys.modules,
        "opentelemetry.instrumentation.auto_instrumentation",
        auto_instrumentation,
    )


def test_disabled_setting_does_not_import_opentelemetry(
    hook_context: HookContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Disabled auto-instrumentation should not touch OpenTelemetry imports."""
    original_import = builtins.__import__

    def guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.startswith("opentelemetry"):
            raise AssertionError("OpenTelemetry should not be imported")
        return original_import(name, *args, **kwargs)

    monkeypatch.setenv("PREFECT_INTEGRATIONS_OTEL_AUTO_INSTRUMENT", "false")
    monkeypatch.setattr(builtins, "__import__", guarded_import)

    assert setup_environment(ctx=hook_context) is None


def test_default_setting_initializes_opentelemetry(
    hook_context: HookContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default auto-instrumentation should call OpenTelemetry initialize."""

    class ProxyTracerProvider:
        pass

    calls: list[str] = []

    def initialize() -> None:
        calls.append("called")

    _install_fake_opentelemetry(
        monkeypatch,
        provider=ProxyTracerProvider(),
        initialize=initialize,
    )

    result = setup_environment(ctx=hook_context)

    assert isinstance(result, SetupResult)
    assert calls == ["called"]
    assert result.note == "Bootstrapped OpenTelemetry auto-instrumentation"


def test_already_configured_provider_skips_initialization(
    hook_context: HookContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An existing configured provider should not be initialized again."""

    class TracerProvider:
        pass

    calls: list[str] = []

    def initialize() -> None:
        calls.append("called")

    _install_fake_opentelemetry(
        monkeypatch,
        provider=TracerProvider(),
        initialize=initialize,
    )

    result = setup_environment(ctx=hook_context)

    assert isinstance(result, SetupResult)
    assert calls == []
    assert result.note == "OpenTelemetry auto-instrumentation already configured"


def test_optional_initialization_failure_logs_and_continues(
    hook_context: HookContext,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Optional auto-instrumentation failures should not raise."""

    class ProxyTracerProvider:
        pass

    def initialize() -> None:
        raise RuntimeError("bootstrap failed")

    _install_fake_opentelemetry(
        monkeypatch,
        provider=ProxyTracerProvider(),
        initialize=initialize,
    )

    with caplog.at_level(logging.ERROR):
        result = setup_environment(ctx=hook_context)

    assert result is None
    assert "Failed to bootstrap OpenTelemetry auto-instrumentation" in caplog.text


def test_required_initialization_failure_raises(
    hook_context: HookContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Required auto-instrumentation failures should be raised."""

    class ProxyTracerProvider:
        pass

    def initialize() -> None:
        raise RuntimeError("bootstrap failed")

    monkeypatch.setenv("PREFECT_INTEGRATIONS_OTEL_REQUIRE_AUTO_INSTRUMENT", "true")
    _install_fake_opentelemetry(
        monkeypatch,
        provider=ProxyTracerProvider(),
        initialize=initialize,
    )

    with pytest.raises(RuntimeError, match="bootstrap failed"):
        setup_environment(ctx=hook_context)


def test_optional_import_failure_logs_and_continues(
    hook_context: HookContext,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Optional missing OpenTelemetry imports should not raise."""
    original_import = builtins.__import__

    def guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.startswith("opentelemetry"):
            raise ImportError("opentelemetry is missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    with caplog.at_level(logging.ERROR):
        result = setup_environment(ctx=hook_context)

    assert result is None
    assert (
        "OpenTelemetry auto-instrumentation requested but not installed" in caplog.text
    )


def test_required_import_failure_raises(
    hook_context: HookContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Required missing OpenTelemetry imports should be raised."""
    original_import = builtins.__import__

    def guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.startswith("opentelemetry"):
            raise ImportError("opentelemetry is missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setenv("PREFECT_INTEGRATIONS_OTEL_REQUIRE_AUTO_INSTRUMENT", "true")
    monkeypatch.setattr(builtins, "__import__", guarded_import)

    with pytest.raises(ImportError, match="opentelemetry is missing"):
        setup_environment(ctx=hook_context)
