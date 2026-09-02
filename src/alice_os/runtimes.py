from __future__ import annotations

import asyncio
import math
import os
import re
import shutil
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

import httpx
from huggingface_hub import HfApi, hf_hub_download, snapshot_download


class RuntimeOperationError(RuntimeError):
    pass


HF_REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*$")
GIBIBYTE = 1024**3
QUANTIZATION_PATTERN = re.compile(
    r"(?:^|[-_.])(IQ[1-4](?:_[A-Z]+)?|Q[2-8](?:_K_[SML]|_[0-9])?|BF16|F16|F32|FP16|FP32)(?:[-_.]|$)",
    re.IGNORECASE,
)


def _validate_huggingface_repository(repository: str) -> str:
    cleaned = repository.strip().rstrip("/")
    parsed = urlparse(cleaned)
    if parsed.scheme or parsed.netloc:
        if (
            parsed.scheme != "https"
            or parsed.hostname not in {"huggingface.co", "www.huggingface.co"}
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise RuntimeOperationError(
                "Use a Hugging Face model link or an owner/repository name."
            )
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) != 2:
            raise RuntimeOperationError(
                "Use the repository's main Hugging Face link, without a file or tree path."
            )
        cleaned = "/".join(parts)
    if not HF_REPOSITORY_PATTERN.fullmatch(cleaned):
        raise RuntimeOperationError("Enter a Hugging Face model link or an owner/repository name.")
    return cleaned


def _validate_huggingface_filename(filename: str) -> str:
    cleaned = filename.strip().replace("\\", "/")
    path = PurePosixPath(cleaned)
    if (
        not cleaned
        or path.is_absolute()
        or ".." in path.parts
        or any(":" in part for part in path.parts)
        or path.suffix.casefold() != ".gguf"
    ):
        raise RuntimeOperationError("Select a valid GGUF file from the repository.")
    return cleaned


def _validate_huggingface_revision(revision: str) -> str:
    cleaned = revision.strip() or "main"
    if len(cleaned) > 200 or cleaned.startswith("/") or ".." in cleaned.split("/"):
        raise RuntimeOperationError("The Hugging Face revision is not valid.")
    return cleaned


def _huggingface_token(provided_token: str = "") -> str | None:
    return provided_token.strip() or os.environ.get("HF_TOKEN") or None


def _huggingface_error_message(error: Exception, token: str = "") -> str:
    detail = str(error).replace(token, "[redacted]") if token else str(error)
    environment_token = os.environ.get("HF_TOKEN", "")
    if environment_token:
        detail = detail.replace(environment_token, "[redacted]")
    detail = " ".join(detail.split())[:500]
    return detail or error.__class__.__name__


def _quantization_from_filename(filename: str) -> str:
    match = QUANTIZATION_PATTERN.search(Path(filename).stem)
    return match.group(1).upper() if match else "GGUF"


def _memory_estimate(weight_bytes: int | None) -> dict[str, int | None]:
    if not isinstance(weight_bytes, int) or weight_bytes <= 0:
        return {"estimated_vram_bytes": None, "estimated_ram_bytes": None}
    # Weights plus a modest execution/KV-cache allowance for a 4K context.
    return {
        "estimated_vram_bytes": math.ceil(weight_bytes * 1.15) + GIBIBYTE,
        "estimated_ram_bytes": math.ceil(weight_bytes * 1.2) + GIBIBYTE,
    }


def gpu_status() -> dict[str, Any]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return {"detected": False, "vram_bytes": None, "name": ""}
    try:
        result = subprocess.run(
            [executable, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return {"detected": False, "vram_bytes": None, "name": ""}
    devices: list[tuple[str, int]] = []
    for line in result.stdout.splitlines():
        name, separator, memory_mib = line.rpartition(",")
        if not separator:
            continue
        try:
            devices.append((name.strip(), int(memory_mib.strip()) * 1024**2))
        except ValueError:
            continue
    if not devices:
        return {"detected": False, "vram_bytes": None, "name": ""}
    name, vram_bytes = max(devices, key=lambda device: device[1])
    return {"detected": True, "vram_bytes": vram_bytes, "name": name}


async def list_huggingface_gguf_files(
    repository: str, revision: str = "main", token: str = ""
) -> list[dict[str, Any]]:
    details = await inspect_huggingface_repository(repository, revision, token)
    return details["gguf_files"]


async def inspect_huggingface_repository(
    repository: str, revision: str = "main", token: str = ""
) -> dict[str, Any]:
    repository = _validate_huggingface_repository(repository)
    revision = _validate_huggingface_revision(revision)

    def inspect_files() -> dict[str, Any]:
        client = HfApi(token=_huggingface_token(token))
        gguf_files: list[dict[str, Any]] = []
        file_count = 0
        total_size = 0
        weight_size = 0
        has_transformers_files = False
        for item in client.list_repo_tree(
            repo_id=repository,
            repo_type="model",
            revision=revision,
            recursive=True,
            expand=True,
        ):
            filename = str(getattr(item, "path", ""))
            raw_size = getattr(item, "size", None)
            if filename:
                file_count += 1
            if isinstance(raw_size, int):
                total_size += raw_size
                if filename.casefold().endswith((".safetensors", ".bin")):
                    weight_size += raw_size
            if filename.casefold().endswith(".gguf"):
                size = raw_size if isinstance(raw_size, int) else None
                gguf_files.append(
                    {
                        "filename": filename,
                        "size": size,
                        "quantization": _quantization_from_filename(filename),
                        **_memory_estimate(size),
                    }
                )
            if filename.casefold().endswith(".safetensors") or filename == "config.json":
                has_transformers_files = True
        parameter_count: int | None = None
        try:
            model_info = client.model_info(repository, revision=revision)
            safetensors = getattr(model_info, "safetensors", None)
            total_parameters = getattr(safetensors, "total", None)
            if isinstance(total_parameters, int) and total_parameters > 0:
                parameter_count = total_parameters
        except Exception:
            # File inspection remains useful when a Hub metadata field is absent.
            pass
        estimates = _memory_estimate(weight_size or None)
        return {
            "repository": repository,
            "revision": revision,
            "gguf_files": sorted(gguf_files, key=lambda entry: entry["filename"].casefold()),
            "file_count": file_count,
            "total_size": total_size,
            "weight_size": weight_size or None,
            "parameter_count": parameter_count,
            **estimates,
            "gpu": gpu_status(),
            "format": "gguf"
            if gguf_files
            else ("transformers" if has_transformers_files else "other"),
        }

    try:
        return await asyncio.to_thread(inspect_files)
    except Exception as error:
        raise RuntimeOperationError(
            "Could not read that Hugging Face repository. It may be private, gated, "
            f"or unavailable. Details: {_huggingface_error_message(error, token)}"
        ) from error


async def download_huggingface_repository(
    *, data_dir: Path, repository: str, revision: str = "main", token: str = ""
) -> dict[str, Any]:
    repository = _validate_huggingface_repository(repository)
    revision = _validate_huggingface_revision(revision)
    download_dir = data_dir / "models" / "huggingface" / repository.replace("/", "--")
    download_dir.mkdir(parents=True, exist_ok=True)
    try:
        downloaded_path = await asyncio.to_thread(
            snapshot_download,
            repo_id=repository,
            repo_type="model",
            revision=revision,
            local_dir=str(download_dir),
            token=_huggingface_token(token),
        )
    except Exception as error:
        raise RuntimeOperationError(
            "Hugging Face could not download this model. Check available disk space and "
            f"access permissions. Details: {_huggingface_error_message(error, token)}"
        ) from error

    def downloaded_summary() -> tuple[int, int]:
        root = Path(downloaded_path)
        files = [path for path in root.rglob("*") if path.is_file()]
        return len(files), sum(path.stat().st_size for path in files)

    file_count, downloaded_bytes = await asyncio.to_thread(downloaded_summary)
    return {
        "repository": repository,
        "revision": revision,
        "download_dir": str(download_dir),
        "source": str(downloaded_path),
        "runtime": "downloaded",
        "file_count": file_count,
        "downloaded_bytes": downloaded_bytes,
    }


async def import_huggingface_gguf(
    *,
    data_dir: Path,
    repository: str,
    filename: str,
    revision: str = "main",
    requested_name: str = "",
    token: str = "",
) -> dict[str, Any]:
    repository = _validate_huggingface_repository(repository)
    filename = _validate_huggingface_filename(filename)
    revision = _validate_huggingface_revision(revision)
    download_dir = data_dir / "models" / "huggingface" / repository.replace("/", "--")
    download_dir.mkdir(parents=True, exist_ok=True)
    try:
        downloaded_path = await asyncio.to_thread(
            hf_hub_download,
            repo_id=repository,
            filename=filename,
            repo_type="model",
            revision=revision,
            local_dir=str(download_dir),
            token=_huggingface_token(token),
        )
    except Exception as error:
        raise RuntimeOperationError(
            "Hugging Face could not download that file. Check the repository, file, "
            f"available disk space, and access permissions. Details: {_huggingface_error_message(error, token)}"
        ) from error
    result = await import_gguf(
        data_dir=data_dir,
        gguf_path=downloaded_path,
        requested_name=requested_name,
    )
    result.update(
        {
            "repository": repository,
            "filename": filename,
            "revision": revision,
            "download_dir": str(download_dir),
        }
    )
    return result


def ollama_executable() -> str | None:
    return shutil.which("ollama")


async def runtime_status() -> dict[str, Any]:
    executable = ollama_executable()
    status: dict[str, Any] = {
        "gpu": gpu_status(),
        "ollama": {
            "installed": bool(executable),
            "executable": executable,
            "running": False,
            "version": "",
            "models": [],
        },
    }
    try:
        async with httpx.AsyncClient(timeout=2.0, follow_redirects=False) as client:
            version_response = await client.get("http://127.0.0.1:11434/api/version")
            version_response.raise_for_status()
            tags_response = await client.get("http://127.0.0.1:11434/api/tags")
            tags_response.raise_for_status()
            ollama_models = tags_response.json().get("models", [])
            status["ollama"].update(
                {
                    "running": True,
                    "version": version_response.json().get("version", ""),
                    "models": [
                        model.get("name", "") for model in ollama_models if model.get("name")
                    ],
                    "model_details": [
                        {
                            "name": model.get("name", ""),
                            "size": model.get("size"),
                            "modified_at": model.get("modified_at", ""),
                        }
                        for model in ollama_models
                        if model.get("name")
                    ],
                }
            )
    except (httpx.HTTPError, ValueError):
        pass
    return status


async def local_model_library(data_dir: Path) -> dict[str, Any]:
    status = await runtime_status()
    ollama_details = status["ollama"].get("model_details", [])
    ollama_models = [
        {
            "name": str(item.get("name", "")),
            "source": "Ollama",
            "status": "Ready to chat",
            "ready": True,
            "size": item.get("size") if isinstance(item.get("size"), int) else None,
            "location": "Managed by Ollama",
        }
        for item in ollama_details
        if item.get("name")
    ]

    def scan_huggingface() -> list[dict[str, Any]]:
        root = data_dir / "models" / "huggingface"
        if not root.is_dir():
            return []
        entries: list[dict[str, Any]] = []
        for directory in root.iterdir():
            if not directory.is_dir():
                continue
            files: list[Path] = []
            for path in directory.rglob("*"):
                try:
                    if path.is_file() and ".cache" not in path.relative_to(directory).parts:
                        files.append(path)
                except OSError:
                    continue
            if not files:
                continue
            size = sum(path.stat().st_size for path in files)
            has_gguf = any(path.suffix.casefold() == ".gguf" for path in files)
            entries.append(
                {
                    "name": directory.name.replace("--", "/"),
                    "source": "Hugging Face",
                    "status": "GGUF files available" if has_gguf else "Downloaded — runtime needed",
                    "ready": False,
                    "size": size,
                    "file_count": len(files),
                    "location": str(directory),
                    "format": "GGUF" if has_gguf else "Transformers / other",
                }
            )
        return sorted(entries, key=lambda entry: entry["name"].casefold())

    huggingface_models = await asyncio.to_thread(scan_huggingface)
    return {
        "ollama": ollama_models,
        "huggingface": huggingface_models,
        "total_bytes": sum(
            item["size"]
            for item in [*ollama_models, *huggingface_models]
            if isinstance(item.get("size"), int)
        ),
    }


def sanitize_model_name(requested: str, gguf_path: Path | None = None) -> str:
    source = requested.strip().lower() or (gguf_path.stem.lower() if gguf_path else "")
    source = re.sub(r"[^a-z0-9._/-]+", "-", source).strip("-./")
    if not source:
        raise RuntimeOperationError("A valid model name is required")
    if len(source) > 120:
        source = source[:120].rstrip("-./")
    return source


async def import_gguf(
    *, data_dir: Path, gguf_path: str, requested_name: str = ""
) -> dict[str, Any]:
    executable = ollama_executable()
    if not executable:
        raise RuntimeOperationError(
            "Ollama is not installed. Install Ollama or add an OpenAI-compatible llama.cpp profile."
        )
    path = Path(gguf_path).expanduser().resolve(strict=True)
    if not path.is_file() or path.suffix.casefold() != ".gguf":
        raise RuntimeOperationError("Select an existing .gguf file")
    model_name = sanitize_model_name(requested_name, path)
    import_dir = data_dir / "imports"
    import_dir.mkdir(parents=True, exist_ok=True)
    modelfile = import_dir / f"{model_name.replace('/', '-')}.Modelfile"
    escaped_path = str(path).replace("\\", "/").replace('"', '\\"')
    modelfile.write_text(f'FROM "{escaped_path}"\nPARAMETER num_ctx 8192\n', encoding="utf-8")
    try:
        process = await asyncio.create_subprocess_exec(
            executable,
            "create",
            model_name,
            "-f",
            str(modelfile),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=1800)
    except TimeoutError as error:
        process.kill()
        await process.wait()
        raise RuntimeOperationError("GGUF import timed out after 30 minutes") from error
    except OSError as error:
        raise RuntimeOperationError(f"Could not start Ollama: {error}") from error
    output = (stdout + stderr).decode("utf-8", errors="replace")[-8000:]
    if process.returncode != 0:
        raise RuntimeOperationError(output or "Ollama could not import the GGUF")
    return {
        "model": model_name,
        "source": str(path),
        "runtime": "ollama",
        "output": output,
    }


async def pull_ollama_model(model_name: str) -> dict[str, Any]:
    executable = ollama_executable()
    if not executable:
        raise RuntimeOperationError("Ollama is not installed")
    model = sanitize_model_name(model_name)
    try:
        process = await asyncio.create_subprocess_exec(
            executable,
            "pull",
            model,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=3600)
    except TimeoutError as error:
        process.kill()
        await process.wait()
        raise RuntimeOperationError("Model download timed out after one hour") from error
    except OSError as error:
        raise RuntimeOperationError(f"Could not start Ollama: {error}") from error
    output = (stdout + stderr).decode("utf-8", errors="replace")[-8000:]
    if process.returncode != 0:
        raise RuntimeOperationError(output or "Ollama could not download the model")
    return {"model": model, "runtime": "ollama", "output": output}
