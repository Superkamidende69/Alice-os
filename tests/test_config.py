from pathlib import Path

from alice_os.config import ConfigStore


def test_new_settings_use_localai_as_primary_provider(tmp_path: Path) -> None:
    settings = ConfigStore(tmp_path).get()

    assert settings.active_provider_id == "localai"
    assert [provider.id for provider in settings.providers[:2]] == ["localai", "ollama"]
    assert settings.providers[0].base_url == "http://127.0.0.1:8080"


def test_existing_settings_migrate_without_dropping_custom_providers(tmp_path: Path) -> None:
    (tmp_path / "settings.json").write_text(
        '{"active_provider_id":"ollama","active_model":"old-model",'
        '"providers":[{"id":"ollama","name":"Ollama (local)","kind":"ollama",'
        '"base_url":"http://127.0.0.1:11434","default_model":"","api_key_env":""},'
        '{"id":"llama_cpp_local","name":"Bundled llama.cpp","kind":"openai",'
        '"base_url":"http://127.0.0.1:8080/v1","default_model":"qwen","api_key_env":""},'
        '{"id":"remote","name":"Remote","kind":"openai",'
        '"base_url":"https://example.test/v1","default_model":"","api_key_env":""}]}',
        encoding="utf-8",
    )

    settings = ConfigStore(tmp_path).get()

    assert settings.active_provider_id == "localai"
    assert settings.active_model == ""
    assert [provider.id for provider in settings.providers] == [
        "localai",
        "ollama",
        "llama_cpp_local",
        "remote",
    ]
    llama = next(provider for provider in settings.providers if provider.id == "llama_cpp_local")
    assert llama.base_url == "http://127.0.0.1:8081/v1"

