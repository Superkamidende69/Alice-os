from __future__ import annotations

import asyncio
import math
import os
import re
import shutil
import subprocess
import time
from collections.abc import Awaitable, Callable
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote, urlparse

import httpx
import yaml
from huggingface_hub import HfApi, hf_hub_download, snapshot_download


class RuntimeOperationError(RuntimeError):
    pass


HF_REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*$")
OLLAMA_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*(?::[A-Za-z0-9._-]+)?$")
GIBIBYTE = 1024**3
LOCALAI_BASE_URL = "http://127.0.0.1:8080"
QUANTIZATION_PATTERN = re.compile(
    r"(?:^|[-_.])(IQ[1-4](?:_[A-Z]+)?|Q[2-8](?:_K_[SML]|_[0-9])?|BF16|F16|F32|FP16|FP32)(?:[-_.]|$)",
    re.IGNORECASE,
)
_LOCALAI_CATALOG_CACHE: tuple[float, dict[str, Any]] | None = None
_LOCALAI_CATALOG_CACHE_TTL = 30.0
_LOCALAI_GALLERY_CACHE: tuple[float, list[dict[str, Any]]] | None = None
_LOCALAI_GALLERY_CACHE_TTL = 300.0
LOCALAI_GALLERY_URL = "https://index.localai.io/models"


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
        return {
            "detected": False,
            "name": "",
            "vram_bytes": None,
            "vram_used_bytes": None,
            "vram_free_bytes": None,
        }
    try:
        result = subprocess.run(
            [
                executable,
                "--query-gpu=name,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return {
            "detected": False,
            "name": "",
            "vram_bytes": None,
            "vram_used_bytes": None,
            "vram_free_bytes": None,
        }
    devices: list[tuple[str, int, int]] = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 3:
            continue
        try:
            name, used_mib, total_mib = parts
            devices.append(
                (name, int(used_mib) * 1024**2, int(total_mib) * 1024**2)
            )
        except ValueError:
            continue
    if not devices:
        return {
            "detected": False,
            "name": "",
            "vram_bytes": None,
            "vram_used_bytes": None,
            "vram_free_bytes": None,
        }
    name, used_bytes, vram_bytes = max(devices, key=lambda device: device[2])
    return {
        "detected": True,
        "name": name,
        "vram_bytes": vram_bytes,
        "vram_used_bytes": used_bytes,
        "vram_free_bytes": max(vram_bytes - used_bytes, 0),
    }


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


def huggingface_download_progress(*, data_dir: Path, repository: str) -> dict[str, int]:
    """Return the files currently present for a managed Hugging Face download."""
    try:
        repository = _validate_huggingface_repository(repository)
    except RuntimeOperationError:
        return {"files_downloaded": 0, "downloaded_bytes": 0}
    root = data_dir / "models" / "huggingface" / repository.replace("/", "--")
    if not root.is_dir():
        return {"files_downloaded": 0, "downloaded_bytes": 0}
    files_downloaded = 0
    downloaded_bytes = 0
    try:
        for path in root.rglob("*"):
            if not path.is_file() or ".cache" in path.parts:
                continue
            try:
                downloaded_bytes += path.stat().st_size
            except OSError:
                continue
            files_downloaded += 1
    except OSError:
        pass
    return {"files_downloaded": files_downloaded, "downloaded_bytes": downloaded_bytes}


async def import_huggingface_gguf(
    *,
    data_dir: Path,
    repository: str,
    filename: str,
    revision: str = "main",
    requested_name: str = "",
    token: str = "",
    runtime: str = "localai",
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
    if runtime == "localai":
        result = await import_localai_gguf(
            data_dir=data_dir,
            gguf_path=downloaded_path,
            requested_name=requested_name,
        )
    elif runtime == "ollama":
        result = await import_gguf(
            data_dir=data_dir,
            gguf_path=downloaded_path,
            requested_name=requested_name,
        )
    else:
        raise RuntimeOperationError(f"Unsupported model runtime: {runtime}")
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


def localai_executable() -> str | None:
    return shutil.which("local-ai") or shutil.which("localai")


def llama_cpp_executable() -> Path:
    return Path(__file__).resolve().parents[2] / "tools" / "llama.cpp" / "bin3" / (
        "llama-server.exe" if os.name == "nt" else "llama-server"
    )


def localai_base_url() -> str:
    return os.environ.get("ALICE_LOCALAI_URL", LOCALAI_BASE_URL).rstrip("/")


def _localai_model_size_bytes(model: dict[str, Any]) -> int | None:
    direct_size = model.get("size_bytes", model.get("size"))
    if isinstance(direct_size, int) and direct_size > 0:
        return direct_size
    if isinstance(direct_size, float) and direct_size > 0:
        return round(direct_size)
    if isinstance(direct_size, str):
        match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*(B|KB|MB|GB|TB)\s*", direct_size, re.I)
        if match:
            units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
            return round(float(match.group(1)) * units[match.group(2).upper()])
    sizes = [
        file.get("size_bytes", file.get("size"))
        for file in model.get("files", [])
        if isinstance(file, dict)
    ]
    parsed_sizes = []
    for size in sizes:
        parsed = _localai_model_size_bytes({"size": size})
        if parsed:
            parsed_sizes.append(parsed)
    return sum(parsed_sizes) if parsed_sizes else None


def _localai_catalog_model(model: dict[str, Any]) -> dict[str, Any]:
    size_bytes = _localai_model_size_bytes(model)
    overrides = model.get("overrides") if isinstance(model.get("overrides"), dict) else {}
    result = {
        key: model[key]
        for key in (
            "name", "id", "description", "tags", "backend", "license", "size",
            "gallery", "icon", "urls", "has_variants", "last_checked",
        )
        if key in model
    }
    result.setdefault("gallery", "localai")
    if not result.get("backend") and overrides.get("backend"):
        result["backend"] = overrides["backend"]
    context_size = model.get("context_size") or overrides.get("context_size")
    if isinstance(context_size, int) and context_size > 0:
        result["context_size"] = context_size
    variants = model.get("variants")
    if isinstance(variants, list):
        result["variants"] = [
            {
                key: variant[key]
                for key in ("name", "model", "size", "size_bytes", "backend")
                if key in variant
            }
            for variant in variants
            if isinstance(variant, dict)
        ]
    description = result.get("description")
    if isinstance(description, str) and len(description) > 1200:
        result["description"] = f"{description[:1197].rstrip()}…"
    files = model.get("files")
    if isinstance(files, list):
        result["files"] = [
            {
                key: file[key]
                for key in ("filename", "size", "size_bytes", "uri")
                if key in file
            }
            for file in files
            if isinstance(file, dict)
        ]
    if size_bytes:
        result["model_size_bytes"] = size_bytes
        result["estimated_vram_bytes"] = _memory_estimate(size_bytes)["estimated_vram_bytes"]
        result["size_source"] = "LocalAI gallery" if "size" in model else "File metadata"
        result["vram_source"] = "Size-based estimate"
    return result


def _localai_installed_model(model: dict[str, Any]) -> dict[str, Any]:
    return {
        key: model[key]
        for key in ("name", "id", "backend", "owned_by")
        if key in model
    }


def clear_localai_model_catalog_cache() -> None:
    global _LOCALAI_CATALOG_CACHE, _LOCALAI_GALLERY_CACHE
    _LOCALAI_CATALOG_CACHE = None
    _LOCALAI_GALLERY_CACHE = None


async def _localai_gallery_models(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    global _LOCALAI_GALLERY_CACHE
    now = time.monotonic()
    if _LOCALAI_GALLERY_CACHE and now - _LOCALAI_GALLERY_CACHE[0] < _LOCALAI_GALLERY_CACHE_TTL:
        return _LOCALAI_GALLERY_CACHE[1]
    try:
        response = await client.get(LOCALAI_GALLERY_URL)
        response.raise_for_status()
        payload = yaml.safe_load(response.text)
    except (httpx.HTTPError, yaml.YAMLError, ValueError):
        return []
    models = payload if isinstance(payload, list) else payload.get("models", []) if isinstance(payload, dict) else []
    gallery = [model for model in models if isinstance(model, dict) and model.get("name")]
    _LOCALAI_GALLERY_CACHE = (time.monotonic(), gallery)
    return gallery


async def localai_model_catalog() -> dict[str, Any]:
    """Read LocalAI's gallery and installed model list for Alice's UI."""
    global _LOCALAI_CATALOG_CACHE
    now = time.monotonic()
    if _LOCALAI_CATALOG_CACHE and now - _LOCALAI_CATALOG_CACHE[0] < _LOCALAI_CATALOG_CACHE_TTL:
        return _LOCALAI_CATALOG_CACHE[1]
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        available_result, installed_result, gallery = await asyncio.gather(
            client.get(f"{localai_base_url()}/models/available"),
            client.get(f"{localai_base_url()}/v1/models"),
            _localai_gallery_models(client),
            return_exceptions=True,
        )
    available: Any = []
    installed_payload: Any = {}
    localai_available = False
    if isinstance(available_result, httpx.Response):
        try:
            available_result.raise_for_status()
            available = available_result.json()
            localai_available = True
        except (httpx.HTTPError, ValueError):
            pass
    if isinstance(installed_result, httpx.Response):
        try:
            installed_result.raise_for_status()
            installed_payload = installed_result.json()
        except (httpx.HTTPError, ValueError):
            pass
    if isinstance(gallery, Exception):
        gallery = []
    if not isinstance(available, list):
        available = available.get("models", []) if isinstance(available, dict) else []
    installed = installed_payload.get("data", []) if isinstance(installed_payload, dict) else []
    live_models = {
        str(item.get("name") or item.get("id")): item
        for item in available
        if isinstance(item, dict) and (item.get("name") or item.get("id"))
    }
    gallery_models = {
        str(item.get("name") or item.get("id")): item
        for item in gallery
        if isinstance(item, dict) and (item.get("name") or item.get("id"))
    }
    merged_models = []
    for name in dict.fromkeys([*gallery_models, *live_models]):
        merged = {**gallery_models.get(name, {}), **live_models.get(name, {})}
        gallery_files = gallery_models.get(name, {}).get("files", [])
        live_files = live_models.get(name, {}).get("files", [])
        if isinstance(gallery_files, list) and isinstance(live_files, list):
            gallery_by_filename = {
                str(file.get("filename")): file
                for file in gallery_files
                if isinstance(file, dict) and file.get("filename")
            }
            merged["files"] = [
                {
                    **gallery_by_filename.get(str(file.get("filename")), {}),
                    **file,
                }
                for file in live_files
                if isinstance(file, dict)
            ] or gallery_files
        merged_models.append(_localai_catalog_model(merged))
    if not localai_available and not merged_models:
        raise RuntimeOperationError("LocalAI model management is unavailable")
    payload = {
        "available": merged_models,
        "installed": [_localai_installed_model(item) for item in installed if isinstance(item, dict)],
        "gpu": gpu_status(),
        "runtime_available": localai_available,
    }
    _LOCALAI_CATALOG_CACHE = (time.monotonic(), payload)
    return payload


def _alice_model_root(data_dir: Path) -> Path:
    root = (data_dir / "models" / "localai").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _alice_model_path(root: Path, filename: str) -> Path:
    relative = Path(filename.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeOperationError("The gallery returned an unsafe model path")
    target = (root / relative).resolve()
    if target != root and root not in target.parents:
        raise RuntimeOperationError("The gallery returned an unsafe model path")
    return target


def _alice_installed_models(data_dir: Path) -> list[dict[str, Any]]:
    root = _alice_model_root(data_dir)
    entries: list[dict[str, Any]] = []
    for config_path in root.glob("*.yaml"):
        try:
            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if not isinstance(config, dict):
            continue
        name = str(config.get("name") or config_path.stem).strip()
        if not name:
            continue
        parameters = config.get("parameters")
        model_file = parameters.get("model") if isinstance(parameters, dict) else ""
        size = None
        if isinstance(model_file, str):
            try:
                model_path = _alice_model_path(root, model_file)
                if model_path.is_file():
                    size = model_path.stat().st_size
            except (OSError, RuntimeOperationError):
                pass
        item = {
            "name": name,
            "id": name,
            "backend": str(config.get("backend") or "llama-cpp"),
            "owned_by": "Alice",
            "model_size_bytes": size,
            "size_source": "Local file" if size else "",
            "installed": True,
        }
        entries.append({key: value for key, value in item.items() if value not in (None, "")})
    for model_path in root.glob("*.gguf"):
        if any(item["name"] == model_path.stem for item in entries):
            continue
        try:
            size = model_path.stat().st_size
        except OSError:
            continue
        entries.append(
            {
                "name": model_path.stem,
                "id": model_path.stem,
                "backend": "llama-cpp",
                "owned_by": "Alice",
                "model_size_bytes": size,
                "size_source": "Local file",
                "installed": True,
            }
        )
    return sorted(entries, key=lambda item: str(item["name"]).casefold())


async def alice_model_catalog(*, data_dir: Path) -> dict[str, Any]:
    """Return Alice-owned LocalAI-compatible gallery and installed metadata."""
    global _LOCALAI_CATALOG_CACHE
    now = time.monotonic()
    cache_key = str(data_dir.resolve())
    if _LOCALAI_CATALOG_CACHE and now - _LOCALAI_CATALOG_CACHE[0] < _LOCALAI_CATALOG_CACHE_TTL:
        cached = _LOCALAI_CATALOG_CACHE[1]
        if cached.get("manager_root") == cache_key:
            return cached
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        gallery = await _localai_gallery_models(client)
    available = [_localai_catalog_model(model) for model in gallery]
    installed = _alice_installed_models(data_dir)
    payload = {
        "available": available,
        "installed": installed,
        "gpu": gpu_status(),
        "runtime_available": True,
        "manager_root": cache_key,
        "manager": "alice",
    }
    _LOCALAI_CATALOG_CACHE = (time.monotonic(), payload)
    return payload


async def _alice_enrich_gallery_model(
    client: httpx.AsyncClient, model: dict[str, Any]
) -> dict[str, Any]:
    enriched = dict(model)
    files = [file for file in model.get("files", []) if isinstance(file, dict)]
    sizes: list[int] = []
    enriched_files: list[dict[str, Any]] = []
    for file in files[:8]:
        item = dict(file)
        size = _localai_model_size_bytes(item)
        uri = item.get("uri")
        remote_uri = _localai_remote_uri(uri) if isinstance(uri, str) else None
        if not size and remote_uri:
            try:
                response = await client.head(remote_uri)
                response.raise_for_status()
                size = int(response.headers.get("content-length", "0")) or None
            except (httpx.HTTPError, ValueError):
                size = None
        if size:
            item["size_bytes"] = size
            sizes.append(size)
        enriched_files.append(item)
    if enriched_files:
        enriched["files"] = enriched_files
    total = sum(sizes) if sizes else _localai_model_size_bytes(enriched)
    if total:
        enriched["model_size_bytes"] = total
        enriched["estimated_vram_bytes"] = _memory_estimate(total)["estimated_vram_bytes"]
        enriched["size_source"] = "Remote file headers"
        enriched["vram_source"] = "Size-based estimate"
    return enriched


async def alice_model_requirements(*, data_dir: Path, model_name: str) -> dict[str, Any]:
    name = model_name.strip()
    catalog = await alice_model_catalog(data_dir=data_dir)
    model = next((item for item in catalog["available"] if item.get("name") == name), None)
    if not model:
        return {}
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
        enriched = await _alice_enrich_gallery_model(client, model)
        variant_names = [
            str(variant.get("model") or variant.get("name"))
            for variant in model.get("variants", [])
            if isinstance(variant, dict) and (variant.get("model") or variant.get("name"))
        ]
        variants: list[dict[str, Any]] = []
        free_vram = int(catalog.get("gpu", {}).get("vram_free_bytes") or 0)

        def fit_for_memory(memory: int | None) -> bool | None:
            if not memory or not free_vram:
                return None
            return memory <= free_vram * 0.95

        for variant_name in variant_names:
            variant_model = next(
                (item for item in catalog["available"] if item.get("name") == variant_name),
                {"name": variant_name, "backend": model.get("backend", "llama-cpp")},
            )
            variant_data = await _alice_enrich_gallery_model(client, variant_model)
            variant_size = int(variant_data.get("model_size_bytes") or 0)
            variant_memory = _memory_estimate(variant_size).get("estimated_vram_bytes")
            variants.append(
                {
                    "model": variant_name,
                    "backend": variant_data.get("backend", model.get("backend", "llama-cpp")),
                    "memory_bytes": variant_memory,
                    "fits": fit_for_memory(variant_memory),
                    "is_base": False,
                }
            )
        base_size = int(enriched.get("model_size_bytes") or 0)
        base_memory = _memory_estimate(base_size).get("estimated_vram_bytes")
        variants.append(
            {
                "model": name,
                "backend": enriched.get("backend", "llama-cpp"),
                "memory_bytes": base_memory,
                "fits": fit_for_memory(base_memory),
                "is_base": True,
            }
        )
    enriched["variants"] = variants
    fitting = [item for item in variants if item.get("fits") is True]
    selected = max(fitting, key=lambda item: int(item.get("memory_bytes") or 0), default=None)
    enriched["auto_selected"] = str(selected["model"]) if selected else name
    return enriched


async def download_alice_model(
    *,
    data_dir: Path,
    model_id: str,
    variant: str = "",
    on_progress: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
) -> dict[str, Any]:
    name = model_id.strip()
    selected_name = variant.strip() or name
    catalog = await alice_model_catalog(data_dir=data_dir)
    gallery = {str(item.get("name")): item for item in catalog["available"]}
    model = gallery.get(selected_name)
    if not model:
        raise RuntimeOperationError(f"Alice could not find {selected_name} in the model gallery")
    files = [file for file in model.get("files", []) if isinstance(file, dict)]
    if not files:
        raise RuntimeOperationError("This gallery model does not provide downloadable files")
    root = _alice_model_root(data_dir)
    downloaded = 0
    total = 0
    for file in files:
        raw_size = _localai_model_size_bytes(file)
        if raw_size:
            total += raw_size
    async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
        for index, file in enumerate(files):
            filename = str(file.get("filename") or "").strip()
            uri = file.get("uri")
            remote_uri = _localai_remote_uri(uri) if isinstance(uri, str) else None
            if not filename or not remote_uri:
                raise RuntimeOperationError(f"Alice cannot download the file for {selected_name}")
            target = _alice_model_path(root, filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_name(f".{target.name}.partial")
            offset = partial.stat().st_size if partial.is_file() else 0
            headers = {"Range": f"bytes={offset}-"} if offset else {}
            async with client.stream("GET", remote_uri, headers=headers) as response:
                response.raise_for_status()
                if offset and response.status_code != 206:
                    offset = 0
                    partial.unlink(missing_ok=True)
                content_length = int(response.headers.get("content-length", "0"))
                file_total = content_length + offset if content_length else (raw_size or 0)
                mode = "ab" if offset else "wb"
                current = offset
                with partial.open(mode) as output:
                    async for chunk in response.aiter_bytes(1024 * 1024):
                        output.write(chunk)
                        current += len(chunk)
                        if on_progress:
                            progress_total = total or downloaded + file_total or downloaded + current or 1
                            display_filename = PurePosixPath(filename.replace("\\", "/")).name or filename
                            await on_progress(
                                {
                                    "downloaded_bytes": downloaded + current,
                                    "total_bytes": progress_total,
                                    "files_downloaded": index,
                                    "progress": min(
                                        99,
                                        round((downloaded + current) / progress_total * 100),
                                    ),
                                    "message": f"Downloading {display_filename}",
                                }
                            )
            expected_hash = str(file.get("sha256") or "").strip().lower()
            if expected_hash:
                digest = await asyncio.to_thread(_sha256_file, partial)
                if digest != expected_hash:
                    partial.unlink(missing_ok=True)
                    raise RuntimeOperationError(f"Checksum verification failed for {filename}")
            partial.replace(target)
            downloaded += target.stat().st_size
    config = dict(model.get("overrides") or {})
    config["name"] = name
    config["backend"] = config.get("backend") or model.get("backend") or "llama-cpp"
    parameters = dict(config.get("parameters") or {})
    parameters["model"] = files[0]["filename"]
    config["parameters"] = parameters
    config_path = root / f"{name}.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return {
        "model": name,
        "variant": selected_name,
        "runtime": "alice",
        "model_path": str(_alice_model_path(root, str(files[0]["filename"]))),
        "config_path": str(config_path),
        "downloaded_bytes": downloaded,
        "file_count": len(files),
    }


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def delete_alice_model(*, data_dir: Path, model_name: str) -> dict[str, Any]:
    name = model_name.strip()
    root = _alice_model_root(data_dir)
    config_path = root / f"{name}.yaml"
    removed: list[str] = []
    if config_path.is_file():
        try:
            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as error:
            raise RuntimeOperationError("Alice could not read the model configuration") from error
        parameters = config.get("parameters") if isinstance(config, dict) else {}
        model_file = parameters.get("model") if isinstance(parameters, dict) else ""
        if isinstance(model_file, str) and model_file:
            try:
                model_path = _alice_model_path(root, model_file)
                if model_path.is_file():
                    model_path.unlink()
                    removed.append(str(model_path))
            except RuntimeOperationError:
                pass
        config_path.unlink()
        removed.append(str(config_path))
    direct_path = root / f"{name}.gguf"
    if direct_path.is_file():
        direct_path.unlink()
        removed.append(str(direct_path))
    if not removed:
        raise RuntimeOperationError(f"Alice could not find installed model {name}")
    clear_localai_model_catalog_cache()
    return {"model": name, "runtime": "alice", "deleted": True, "removed": removed}


def _localai_remote_uri(uri: str) -> str | None:
    if uri.startswith("huggingface://"):
        parts = uri.removeprefix("huggingface://").split("/", 2)
        if len(parts) == 3:
            owner, repository, filename = parts
            return f"https://huggingface.co/{owner}/{repository}/resolve/main/{filename}"
    if uri.startswith(("https://", "http://")):
        return uri
    return None


async def localai_model_requirements(model_name: str) -> dict[str, Any]:
    """Fill in a selected gallery model's size from its remote files when needed."""
    name = model_name.strip()
    catalog = await localai_model_catalog()
    model = next(
        (
            item
            for item in catalog["available"]
            if str(item.get("name") or item.get("id")) == name
        ),
        None,
    )
    if not model:
        return model or {}
    enriched = dict(model)
    gallery_id = str(model.get("id") or f"localai@{name}")
    variant_payload: dict[str, Any] = {}
    measured_memory: int | None = None
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=False) as client:
        try:
            variant_response = await client.get(
                f"{localai_base_url()}/api/models/variants/{quote(gallery_id, safe='@')}"
            )
            variant_response.raise_for_status()
            payload = variant_response.json()
            if isinstance(payload, dict):
                variant_payload = payload
        except (httpx.HTTPError, ValueError):
            pass
    measured_variants = variant_payload.get("variants")
    if isinstance(measured_variants, list):
        enriched["variants"] = [
            {
                key: variant[key]
                for key in ("model", "backend", "memory_bytes", "fits", "is_base", "quantization")
                if key in variant
            }
            for variant in measured_variants
            if isinstance(variant, dict)
        ]
        selected = next(
            (
                variant
                for variant in measured_variants
                if isinstance(variant, dict) and variant.get("model") == name
            ),
            None,
        )
        if isinstance(selected, dict):
            memory_bytes = selected.get("memory_bytes")
            if isinstance(memory_bytes, (int, float)) and memory_bytes > 0:
                # LocalAI has already measured the runtime footprint for this build.
                # Prefer it over Alice's size-only fallback everywhere in the UI.
                measured_memory = round(memory_bytes)
                enriched["estimated_vram_bytes"] = measured_memory
                enriched["localai_memory_bytes"] = measured_memory
                enriched["vram_source"] = "LocalAI measured"
            if isinstance(selected.get("fits"), bool):
                enriched["localai_fit"] = selected["fits"]
    if variant_payload.get("auto_selected"):
        enriched["auto_selected"] = variant_payload["auto_selected"]
    if _localai_model_size_bytes(enriched):
        return enriched
    uris = [
        file.get("uri")
        for file in enriched.get("files", [])
        if isinstance(file, dict) and isinstance(file.get("uri"), str)
    ]
    if not uris:
        return enriched
    sizes: list[int] = []
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
        for uri in uris[:8]:
            remote_uri = _localai_remote_uri(uri)
            if not remote_uri:
                continue
            try:
                response = await client.head(remote_uri)
                response.raise_for_status()
                size = int(response.headers.get("content-length", "0"))
                if size > 0:
                    sizes.append(size)
            except (httpx.HTTPError, ValueError):
                continue
    if not sizes:
        return enriched
    enriched["model_size_bytes"] = sum(sizes)
    enriched["size_source"] = "Remote file headers"
    if measured_memory is None:
        enriched["estimated_vram_bytes"] = _memory_estimate(enriched["model_size_bytes"])[
            "estimated_vram_bytes"
        ]
        enriched["vram_source"] = "Size-based estimate"
    return enriched


async def install_localai_model(model_id: str, variant: str = "") -> dict[str, Any]:
    name = model_id.strip()
    selected_variant = variant.strip()
    if (
        not name
        or len(name) > 240
        or any(char in name for char in "\r\n")
        or len(selected_variant) > 240
        or any(char in selected_variant for char in "\r\n")
    ):
        raise RuntimeOperationError("That LocalAI model identifier is not valid")
    request = {"id": name if "@" in name else f"localai@{name}"}
    if selected_variant:
        request["variant"] = selected_variant
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            response = await client.post(
                f"{localai_base_url()}/models/apply",
                json=request,
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.ConnectError as error:
        raise RuntimeOperationError(
            f"LocalAI is not running at {localai_base_url()}. Start LocalAI, then try again."
        ) from error
    except httpx.TimeoutException as error:
        raise RuntimeOperationError(
            "LocalAI did not respond while starting the installation. Check that it is healthy and try again."
        ) from error
    except httpx.HTTPStatusError as error:
        detail = error.response.text.strip().replace("\n", " ")[:240]
        suffix = f": {detail}" if detail else ""
        raise RuntimeOperationError(
            f"LocalAI rejected the installation request ({error.response.status_code}){suffix}"
        ) from error
    except (httpx.HTTPError, ValueError) as error:
        raise RuntimeOperationError("LocalAI could not start installing that model") from error
    clear_localai_model_catalog_cache()
    return payload if isinstance(payload, dict) else {"result": payload}


async def localai_download_status(job_id: str) -> dict[str, Any]:
    cleaned = job_id.strip()
    if not cleaned or len(cleaned) > 240 or any(char in cleaned for char in "\r\n"):
        raise RuntimeOperationError("That LocalAI download job is not valid")
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=False) as client:
            response = await client.get(
                f"{localai_base_url()}/models/jobs/{quote(cleaned, safe='-_.')}"
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise RuntimeOperationError("LocalAI download status is unavailable") from error
    return payload if isinstance(payload, dict) else {"status": payload}


async def delete_localai_runtime_model(model_name: str) -> dict[str, Any]:
    name = model_name.strip()
    if not name or len(name) > 240 or any(char in name for char in "\r\n"):
        raise RuntimeOperationError("That LocalAI model name is not valid")
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            response = await client.post(
                f"{localai_base_url()}/models/delete/{quote(name, safe='')}"
            )
            response.raise_for_status()
    except (httpx.HTTPError, ValueError) as error:
        raise RuntimeOperationError("LocalAI could not delete that model") from error
    clear_localai_model_catalog_cache()
    return {"model": name, "source": "LocalAI", "deleted": True}


def _localai_model_name(requested: str, gguf_path: Path | None = None) -> str:
    name = sanitize_model_name(requested, gguf_path).replace("/", "-")
    return name or "alice-model"


def _install_localai_gguf(*, data_dir: Path, source: Path, model_name: str) -> dict[str, Any]:
    model_directory = data_dir / "models" / "localai"
    model_directory.mkdir(parents=True, exist_ok=True)
    model_filename = f"{model_name}.gguf"
    target = model_directory / model_filename
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    config_path = model_directory / f"{model_name}.yaml"
    config_path.write_text(
        "\n".join(
            [
                f"name: {model_name}",
                "backend: llama-cpp",
                "parameters:",
                f"  model: {model_filename}",
                "context_size: 8192",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "model": model_name,
        "source": str(source),
        "runtime": "localai",
        "model_path": str(target),
        "config_path": str(config_path),
    }


async def import_localai_gguf(
    *, data_dir: Path, gguf_path: str, requested_name: str = ""
) -> dict[str, Any]:
    path = Path(gguf_path).expanduser().resolve(strict=True)
    if not path.is_file() or path.suffix.casefold() != ".gguf":
        raise RuntimeOperationError("Select an existing .gguf file")
    model_name = _localai_model_name(requested_name, path)
    result = await asyncio.to_thread(
        _install_localai_gguf,
        data_dir=data_dir,
        source=path,
        model_name=model_name,
    )
    result["message"] = (
        "LocalAI model files installed. Start or refresh LocalAI if the model is not listed yet."
    )
    return result


async def runtime_status() -> dict[str, Any]:
    executable = ollama_executable()
    localai_binary = localai_executable()
    docker = shutil.which("docker")
    llama_executable = llama_cpp_executable()
    status: dict[str, Any] = {
        "gpu": gpu_status(),
        "ollama": {
            "installed": bool(executable),
            "executable": executable,
            "running": False,
            "version": "",
            "models": [],
        },
        "localai": {
            "installed": bool(localai_binary or docker),
            "executable": localai_binary or (docker or ""),
            "running": False,
            "version": "",
            "models": [],
            "base_url": "http://127.0.0.1:8080",
        },
        "llama_cpp": {
            "installed": llama_executable.is_file(),
            "executable": str(llama_executable),
            "running": False,
            "version": "",
            "base_url": "http://127.0.0.1:8081",
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
    # LocalAI exposes an OpenAI-compatible model endpoint.  /readyz keeps a
    # running llama.cpp server on the adjacent port from being misidentified.
    try:
        async with httpx.AsyncClient(timeout=2.0, follow_redirects=False) as client:
            ready_response = await client.get(f"{localai_base_url()}/readyz")
            ready_response.raise_for_status()
            models_response = await client.get(f"{localai_base_url()}/v1/models")
            models_response.raise_for_status()
            payload = models_response.json()
            models = payload.get("data", []) if isinstance(payload, dict) else []
            status["localai"].update(
                {
                    "running": True,
                    "models": [
                        item.get("id", "") for item in models
                        if isinstance(item, dict) and item.get("id")
                    ],
                }
            )
    except (httpx.HTTPError, ValueError):
        pass
    try:
        async with httpx.AsyncClient(timeout=2.0, follow_redirects=False) as client:
            health_response = await client.get("http://127.0.0.1:8081/health")
            health_response.raise_for_status()
            status["llama_cpp"]["running"] = True
            try:
                health = health_response.json()
                if isinstance(health, dict):
                    status["llama_cpp"]["status"] = health.get("status", "ok")
            except ValueError:
                status["llama_cpp"]["status"] = "ok"
    except (httpx.HTTPError, ValueError):
        pass
    return status


async def local_model_library(data_dir: Path) -> dict[str, Any]:
    status = await runtime_status()
    localai_status = status.get("localai", {})
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

    def scan_localai() -> list[dict[str, Any]]:
        root = data_dir / "models" / "localai"
        if not root.is_dir():
            return []
        entries: list[dict[str, Any]] = []
        for path in root.glob("*.gguf"):
            try:
                size = path.stat().st_size
            except OSError:
                continue
            name = path.stem
            entries.append(
                {
                    "name": name,
                    "source": "LocalAI",
                    "status": "Ready to chat" if localai_status.get("running") else "LocalAI is stopped",
                    "ready": bool(localai_status.get("running")),
                    "size": size,
                    "location": str(path),
                    "format": "GGUF",
                }
            )
        return sorted(entries, key=lambda entry: entry["name"].casefold())

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

    localai_models, huggingface_models = await asyncio.gather(
        asyncio.to_thread(scan_localai), asyncio.to_thread(scan_huggingface)
    )
    return {
        "localai": localai_models,
        "ollama": ollama_models,
        "huggingface": huggingface_models,
        "total_bytes": sum(
            item["size"]
            for item in [*localai_models, *ollama_models, *huggingface_models]
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


async def delete_ollama_model(model_name: str) -> dict[str, Any]:
    executable = ollama_executable()
    model = model_name.strip()
    if not executable:
        raise RuntimeOperationError("Ollama is not installed")
    if not model or len(model) > 240 or not OLLAMA_MODEL_PATTERN.fullmatch(model):
        raise RuntimeOperationError("That Ollama model name is not valid")
    try:
        process = await asyncio.create_subprocess_exec(
            executable,
            "rm",
            model,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=180)
    except TimeoutError as error:
        process.kill()
        await process.wait()
        raise RuntimeOperationError("Ollama model deletion timed out") from error
    except OSError as error:
        raise RuntimeOperationError(f"Could not start Ollama: {error}") from error
    output = (stdout + stderr).decode("utf-8", errors="replace")[-8000:]
    if process.returncode != 0:
        raise RuntimeOperationError(output or "Ollama could not delete the model")
    return {"model": model, "source": "Ollama", "deleted": True, "output": output}


def delete_huggingface_model(*, data_dir: Path, model_name: str) -> dict[str, Any]:
    name = model_name.strip()
    root = (data_dir / "models" / "huggingface").resolve()
    directory = (root / name.replace("/", "--")).resolve()
    if not name or directory.parent != root or not directory.is_dir():
        raise RuntimeOperationError("That Hugging Face model is not managed by Alice")
    shutil.rmtree(directory)
    return {"model": name, "source": "Hugging Face", "deleted": True}


def delete_localai_model(*, data_dir: Path, model_name: str) -> dict[str, Any]:
    name = model_name.strip()
    if not name or len(name) > 120 or not re.fullmatch(r"[A-Za-z0-9._-]+", name):
        raise RuntimeOperationError("That LocalAI model name is not valid")
    root = (data_dir / "models" / "localai").resolve()
    model_path = (root / f"{name}.gguf").resolve()
    config_path = (root / f"{name}.yaml").resolve()
    if model_path.parent != root or config_path.parent != root:
        raise RuntimeOperationError("That LocalAI model is not managed by Alice")
    removed = False
    for path in (model_path, config_path):
        try:
            path.unlink()
            removed = True
        except FileNotFoundError:
            pass
    if not removed:
        raise RuntimeOperationError("That LocalAI model is not managed by Alice")
    return {"model": name, "source": "LocalAI", "deleted": True}
