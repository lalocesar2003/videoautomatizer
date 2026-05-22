import pytest

from ai import provider_registry
from ai.provider_registry import get_provider


def test_returns_ollama_provider_when_configured(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")

    provider = get_provider()

    from ai.ollama_provider import call_ollama_json
    assert provider is call_ollama_json


def test_case_insensitive_and_trims(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "  Ollama  ")

    provider = get_provider()

    assert callable(provider)


def test_fails_when_ai_provider_missing(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)

    with pytest.raises(RuntimeError, match="Falta AI_PROVIDER"):
        get_provider()


def test_fails_when_ai_provider_empty(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "   ")

    with pytest.raises(RuntimeError, match="Falta AI_PROVIDER"):
        get_provider()


def test_fails_with_unknown_provider(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "lalala")

    with pytest.raises(RuntimeError, match="Proveedor desconocido"):
        get_provider()


def test_gemini_is_registered_but_not_implemented(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")

    with pytest.raises(NotImplementedError, match="gemini"):
        get_provider()


def test_openai_is_registered_but_not_implemented(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai")

    with pytest.raises(NotImplementedError, match="openai"):
        get_provider()


def test_registry_lists_known_providers():
    assert "ollama" in provider_registry.PROVIDER_FACTORIES
    assert "gemini" in provider_registry.PROVIDER_FACTORIES
    assert "openai" in provider_registry.PROVIDER_FACTORIES
