from __future__ import annotations

from pathlib import Path

import pytest

from alice_os import runtimes


class _RepoEntry:
    def __init__(self, path: str, size: int | None = None) -> None:
        self.path = path
        self.size = size


@pytest.mark.asyncio
async def test_lists_only_gguf_files_from_huggingface(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    class FakeApi:
        def __init__(self, *, token: str | None) -> None:
            calls["token"] = token

        def list_repo_tree(self, **kwargs: object) -> list[_RepoEntry]:
            calls.update(kwargs)
            return [
                _RepoEntry("nested/model-q4.gguf", 42),
                _RepoEntry("README.md", 7),
                _RepoEntry("model-q8.GGUF", 84),
            ]

    monkeypatch.setenv("HF_TOKEN", "token-from-environment")
    monkeypatch.setattr(runtimes, "HfApi", FakeApi)

    files = await runtimes.list_huggingface_gguf_files("org/example", "v1")

    assert [file["filename"] for file in files] == [
        "model-q8.GGUF",
        "nested/model-q4.gguf",
    ]
    assert [file["quantization"] for file in files] == ["Q8", "Q4"]
    assert files[0]["estimated_vram_bytes"] > 84
    assert files[1]["estimated_ram_bytes"] > 42
    assert calls == {
        "token": "token-from-environment",
        "repo_id": "org/example",
        "repo_type": "model",
        "revision": "v1",
        "recursive": True,
        "expand": True,
    }


@pytest.mark.asyncio
async def test_imports_downloaded_huggingface_gguf_into_ollama(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    downloaded = tmp_path / "downloaded.gguf"
    downloaded.write_bytes(b"gguf")
    download_call: dict[str, object] = {}

    def fake_download(**kwargs: object) -> str:
        download_call.update(kwargs)
        return str(downloaded)

    async def fake_import(**kwargs: object) -> dict[str, object]:
        assert kwargs["gguf_path"] == str(downloaded)
        assert kwargs["requested_name"] == "alice-small"
        return {"model": "alice-small", "runtime": "ollama"}

    monkeypatch.setattr(runtimes, "hf_hub_download", fake_download)
    monkeypatch.setattr(runtimes, "import_gguf", fake_import)

    result = await runtimes.import_huggingface_gguf(
        data_dir=tmp_path / "alice-data",
        repository="org/example",
        filename="quant/model-q4.gguf",
        revision="revision-1",
        requested_name="alice-small",
    )

    assert download_call["repo_id"] == "org/example"
    assert download_call["filename"] == "quant/model-q4.gguf"
    assert download_call["revision"] == "revision-1"
    assert download_call["local_dir"] == str(
        tmp_path / "alice-data" / "models" / "huggingface" / "org--example"
    )
    assert result["repository"] == "org/example"
    assert result["filename"] == "quant/model-q4.gguf"
    assert result["runtime"] == "ollama"


@pytest.mark.asyncio
async def test_downloads_a_complete_model_repository_from_a_huggingface_link(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: dict[str, object] = {}

    def fake_snapshot_download(**kwargs: object) -> str:
        calls.update(kwargs)
        return str(tmp_path / "model-files")

    monkeypatch.setattr(runtimes, "snapshot_download", fake_snapshot_download)

    result = await runtimes.download_huggingface_repository(
        data_dir=tmp_path / "alice-data",
        repository="https://huggingface.co/Qwen/Qwen2.5-Omni-3B",
        token="hf_session_token",
    )

    assert calls["repo_id"] == "Qwen/Qwen2.5-Omni-3B"
    assert calls["revision"] == "main"
    assert calls["token"] == "hf_session_token"
    assert calls["local_dir"] == str(
        tmp_path / "alice-data" / "models" / "huggingface" / "Qwen--Qwen2.5-Omni-3B"
    )
    assert result["repository"] == "Qwen/Qwen2.5-Omni-3B"
    assert result["runtime"] == "downloaded"


@pytest.mark.asyncio
async def test_lists_ollama_and_downloaded_huggingface_models(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    async def fake_runtime_status() -> dict[str, object]:
        return {
            "ollama": {"model_details": [{"name": "qwen3:4b", "size": 2_000, "modified_at": ""}]}
        }

    model_dir = tmp_path / "models" / "huggingface" / "Qwen--Qwen2.5-3B-GGUF"
    model_dir.mkdir(parents=True)
    (model_dir / "model-q4.gguf").write_bytes(b"x" * 123)
    cache = model_dir / ".cache"
    cache.mkdir()
    (cache / "metadata").write_bytes(b"x" * 40)
    monkeypatch.setattr(runtimes, "runtime_status", fake_runtime_status)

    library = await runtimes.local_model_library(tmp_path)

    assert library["ollama"] == [
        {
            "name": "qwen3:4b",
            "source": "Ollama",
            "status": "Ready to chat",
            "ready": True,
            "size": 2_000,
            "location": "Managed by Ollama",
        }
    ]
    assert library["huggingface"][0]["name"] == "Qwen/Qwen2.5-3B-GGUF"
    assert library["huggingface"][0]["size"] == 123
    assert library["huggingface"][0]["format"] == "GGUF"


@pytest.mark.parametrize(
    "repository, filename",
    [
        ("not-a-repository", "model.gguf"),
        ("org/example", "../model.gguf"),
        ("org/example", "C:/model.gguf"),
        ("org/example", "model.safetensors"),
    ],
)
@pytest.mark.asyncio
async def test_huggingface_import_validates_identifiers(
    tmp_path: Path, repository: str, filename: str
) -> None:
    with pytest.raises(runtimes.RuntimeOperationError):
        await runtimes.import_huggingface_gguf(
            data_dir=tmp_path,
            repository=repository,
            filename=filename,
        )
