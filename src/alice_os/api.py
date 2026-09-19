from __future__ import annotations

import asyncio
import base64
import hmac
import ipaddress
import json
import os
import secrets
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import httpx
import psutil
from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__, kokoro, voicebox
from .agent import RunCapacityError, RunConflictError, RunManager
from .auth import create_auth_file, load_or_create_session_token, verify_auth_file
from .cluster import Cluster, mount_cluster
from .config import ConfigStore
from .diagnostics import SystemDiagnostics
from .distributed import DistributedSettings, probe_devices
from .handsfree import ConversationLease, HandsFreeConversation
from .memory import parse_memory_command
from .model_manager import ModelManager
from .models import ProviderProfile
from .paths import resource_root
from .providers import ProviderError, list_models
from .runtimes import (
    RuntimeOperationError,
    alice_model_catalog,
    alice_model_requirements,
    clear_localai_model_catalog_cache,
    delete_alice_model,
    delete_huggingface_model,
    delete_localai_model,
    delete_ollama_model,
    download_alice_model,
    download_huggingface_repository,
    huggingface_download_progress,
    import_gguf,
    import_huggingface_gguf,
    import_localai_gguf,
    inspect_huggingface_repository,
    local_model_library,
    pull_ollama_model,
    runtime_status,
)
from .secure_store import SecretStore, SecretStoreError
from .skill_packages import TEMPLATES, SkillManifest
from .skills import AgentSkill, SkillStore
from .storage import Storage
from .tools import ToolContext, ToolError, workspace_list, workspace_read
from .vad import SpeechActivityDetector
from .voice import (
    OPENVOICE_FEMALE_SPEAKER,
    VoiceCancellation,
    VoiceError,
    VoiceInterrupted,
    list_voice_references,
    openvoice_status,
    remove_voice_reference,
    save_voice_reference,
    shutdown_openvoice,
    synthesize_openvoice,
    transcribe_openvoice_audio,
    transcription_status,
    voice_pipeline_status,
    voice_worker_status,
    warm_openvoice,
)
from .windows_asyncio import install_connection_reset_handler
from .world_view import WorldView, is_host_client


class SessionCreate(BaseModel):
    title: str = "New conversation"
    workspace: str = ""
    provider_id: str = ""
    model: str = ""


class SessionUpdate(BaseModel):
    title: str | None = None
    workspace: str | None = None
    provider_id: str | None = None
    model: str | None = None


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    category: str = Field(default="fact", max_length=32)
    key: str = Field(default="", max_length=120)
    importance: int = Field(default=3, ge=1, le=5)
    confidence: float = Field(default=1.0, ge=0, le=1)


class MemoryUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=4000)
    category: str | None = Field(default=None, max_length=32)
    key: str | None = Field(default=None, max_length=120)
    importance: int | None = Field(default=None, ge=1, le=5)
    confidence: float | None = Field(default=None, ge=0, le=1)


class NetworkLogin(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class RunCreate(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=200_000)
    provider_id: str
    model: str
    agent_mode: bool = True
    spoken_response: bool = False
    skill_id: str = Field(default="general", max_length=40)
    response_depth: str = Field(default="balanced", pattern="^(quick|balanced|thorough)$")


class ImageCreate(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)


class SkillUpsert(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=240)
    instructions: str = Field(min_length=1, max_length=8_000)
    read_only: bool = False


class ApprovalDecision(BaseModel):
    call_id: str
    approved: bool


class PackageEnabled(BaseModel):
    enabled: bool = Field(strict=True)


class ActiveProvider(BaseModel):
    provider_id: str


class ActiveModel(BaseModel):
    model: str = Field(default="", max_length=240)
    provider_id: str = Field(default="", max_length=120)


class GGUFImport(BaseModel):
    path: str
    name: str = ""
    runtime: Literal["localai", "ollama"] = "localai"


class ModelPull(BaseModel):
    name: str


class LocalAIModelAction(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    variant: str = Field(default="", max_length=240)


class ModelLoad(BaseModel):
    model_path: str = Field(min_length=1, max_length=4096)


class ModelDelete(BaseModel):
    source: Literal["LocalAI", "Ollama", "Hugging Face"]
    name: str = Field(min_length=1, max_length=240)


class HuggingFaceImport(BaseModel):
    repository: str = Field(min_length=3, max_length=200)
    filename: str = Field(min_length=6, max_length=500)
    revision: str = Field(default="main", max_length=200)
    name: str = Field(default="", max_length=120)
    token: str = Field(default="", max_length=500)


class HuggingFaceDownload(BaseModel):
    repository: str = Field(min_length=3, max_length=500)
    revision: str = Field(default="main", max_length=200)
    token: str = Field(default="", max_length=500)
    expected_bytes: int = Field(default=0, ge=0, le=10**16)


class HuggingFaceInspect(BaseModel):
    repository: str = Field(min_length=3, max_length=500)
    revision: str = Field(default="main", max_length=200)
    token: str = Field(default="", max_length=500)


class HuggingFaceToken(BaseModel):
    token: str = Field(min_length=1, max_length=500)


class VoiceSynthesis(BaseModel):
    request_id: str = Field(default="", max_length=64, pattern=r"^[a-zA-Z0-9_-]*$")
    text: str = Field(min_length=1, max_length=8_000)
    speaker: str = Field(default="OPENVOICE-FEMALE", max_length=80)
    speed: float = Field(default=1.0, ge=0.7, le=1.3)
    reference: str = Field(default="", max_length=160)
    style: str = Field(default="balanced", max_length=32)
    noise_scale: float | None = Field(default=None, ge=0.2, le=1.2)
    noise_scale_w: float | None = Field(default=None, ge=0.2, le=1.4)
    sdp_ratio: float | None = Field(default=None, ge=0.0, le=1.0)


class OpenAITTSRequest(BaseModel):
    """The small OpenAI/LocalAI-compatible surface for Alice's local TTS."""

    model: str = Field(default="alice-openvoice", max_length=120)
    input: str = Field(min_length=1, max_length=8_000)
    voice: str = Field(default="OPENVOICE-FEMALE", max_length=80)
    response_format: Literal["wav"] = "wav"
    speed: float = Field(default=1.0, ge=0.7, le=1.3)


class VoiceCancel(BaseModel):
    request_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")


def _validate_provider_url(profile: ProviderProfile) -> None:
    parsed = urlparse(profile.base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(400, "Provider URL must be an http(s) URL")
    if parsed.username or parsed.password or parsed.fragment:
        raise HTTPException(400, "Provider URL cannot contain credentials or fragments")
    if parsed.scheme == "http":
        host = parsed.hostname.casefold()
        loopback = host == "localhost"
        try:
            loopback = loopback or ipaddress.ip_address(host).is_loopback
        except ValueError:
            pass
        if not loopback:
            raise HTTPException(
                400,
                "Plain HTTP is allowed only for loopback providers. Use HTTPS for remote endpoints.",
            )


def _resolve_workspace(raw_workspace: str) -> str:
    workspace = Path(raw_workspace).expanduser() if raw_workspace.strip() else Path.cwd()
    try:
        resolved = workspace.resolve(strict=True)
    except OSError as error:
        raise HTTPException(400, f"Workspace does not exist: {workspace}") from error
    if not resolved.is_dir():
        raise HTTPException(400, "Workspace must be a directory")
    if str(resolved).startswith("\\\\"):
        raise HTTPException(400, "Network workspaces are disabled")
    return str(resolved)


def _model_display_name(model: str) -> str:
    """Keep provider model IDs intact while making path-based IDs readable in Alice."""
    value = model.strip()
    if not value:
        return value
    filename = value.replace("\\", "/").rsplit("/", 1)[-1]
    if filename.lower().endswith(".gguf"):
        filename = filename[:-5]
    return filename or value


async def _workspace_git_status(workspace: str) -> dict[str, Any]:
    try:
        process = await asyncio.create_subprocess_exec(
            "git",
            "-C",
            workspace,
            "status",
            "--short",
            "--branch",
            "--untracked-files=normal",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5)
    except (OSError, TimeoutError):
        return {"available": False, "branch": "", "changes": []}
    if process.returncode != 0:
        return {"available": False, "branch": "", "changes": []}
    lines = stdout.decode("utf-8", errors="replace").splitlines()
    branch = lines[0][3:] if lines and lines[0].startswith("## ") else ""
    changes = [{"status": line[:2], "path": line[3:]} for line in lines[1:101] if len(line) >= 4]
    return {"available": True, "branch": branch, "changes": changes, "truncated": len(lines) > 101}


async def _workspace_git_diff(workspace: str, path: str) -> dict[str, Any]:
    relative = Path(path)
    if not path or relative.is_absolute() or ".." in relative.parts:
        raise HTTPException(400, "Diff path must stay inside the selected workspace")
    try:
        process = await asyncio.create_subprocess_exec(
            "git", "-C", workspace, "diff", "--no-ext-diff", "--no-color", "HEAD", "--", path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
    except (OSError, TimeoutError) as error:
        raise HTTPException(400, "Git diff is unavailable for this workspace") from error
    if process.returncode != 0:
        detail = stderr.decode("utf-8", errors="replace").strip() or "Git could not read that diff"
        raise HTTPException(400, detail)
    diff = stdout.decode("utf-8", errors="replace")
    return {"path": path, "diff": diff[:60_000], "truncated": len(diff) > 60_000}


def create_app(data_dir: Path | None = None) -> FastAPI:
    config = ConfigStore(data_dir)
    model_manager = ModelManager(config)
    storage = Storage(config.data_dir / "alice.db")
    skills = SkillStore(config.data_dir)
    runs = RunManager(storage, config, skills=skills)
    diagnostics = SystemDiagnostics()
    cluster = Cluster(config)
    model_manager.bridges = cluster.bridges
    runs.cluster = cluster
    download_jobs: dict[str, dict[str, Any]] = {}
    localai_download_jobs: dict[str, dict[str, Any]] = {}
    download_tasks: set[asyncio.Task[None]] = set()
    audio_cache: dict[str, tuple[float, bytes]] = {}
    voice_jobs: dict[str, VoiceCancellation] = {}
    cancelled_voice_jobs: dict[str, float] = {}
    session_token = secrets.token_urlsafe(32)
    network_mode = (os.environ.get("ALICE_NETWORK_MODE") == "1"
                    or (config.data_dir / "network-auth.json").is_file())
    https_mode = os.environ.get("ALICE_HTTPS") == "1"
    network_auth_file = config.data_dir / "network-auth.json"
    network_access_token = load_or_create_session_token(config.data_dir / "network-session-token")
    huggingface_token_store = SecretStore(config.data_dir / "secrets" / "huggingface-token")
    web_dir = resource_root() / "web"
    world_view = WorldView(config.data_dir)
    voicebox_runtime = voicebox.Runtime(config.data_dir)
    runtime_snapshot: tuple[float, dict[str, Any]] | None = None
    runtime_refresh: asyncio.Task[dict[str, Any]] | None = None

    async def cached_runtime_status() -> dict[str, Any]:
        nonlocal runtime_snapshot, runtime_refresh
        if runtime_snapshot is not None and time.monotonic() - runtime_snapshot[0] < 5:
            return runtime_snapshot[1]

        async def refresh() -> dict[str, Any]:
            nonlocal runtime_snapshot
            result = await runtime_status()
            runtime_snapshot = (time.monotonic(), result)
            return result

        if runtime_refresh is None or runtime_refresh.done():
            runtime_refresh = asyncio.create_task(refresh())
            runtime_refresh.add_done_callback(lambda task: task.exception() if not task.cancelled() else None)
        return await asyncio.shield(runtime_refresh)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        restore_loop_handler = install_connection_reset_handler()
        try:
            yield
        finally:
            if runtime_refresh is not None and not runtime_refresh.done():
                runtime_refresh.cancel()
                await asyncio.gather(runtime_refresh, return_exceptions=True)
            pending_downloads = tuple(download_tasks)
            for task in pending_downloads:
                task.cancel()
            for cancellation in tuple(voice_jobs.values()):
                cancellation.cancel()
            try:
                if pending_downloads:
                    await asyncio.gather(*pending_downloads, return_exceptions=True)
                await runs.shutdown()
                await cluster.shutdown()
                await cluster.bridges.close()
                await cluster.gpu.stop()
                await shutdown_openvoice()
            finally:
                try:
                    await world_view.stop()
                finally:
                    await kokoro.shutdown()
                    await voicebox_runtime.stop()
                    audio_cache.clear()
                    storage.close()
                    restore_loop_handler()

    app = FastAPI(
        title="Alice OS",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "testserver"] if not network_mode else ["*"]
    )
    app.state.config = config
    app.state.storage = storage
    app.state.runs = runs
    app.state.cluster = cluster
    app.state.skills = skills
    app.state.download_jobs = download_jobs
    app.state.localai_download_jobs = localai_download_jobs
    app.state.session_token = session_token
    app.state.network_mode = network_mode
    app.state.audio_cache = audio_cache
    app.state.huggingface_token_store = huggingface_token_store

    def cache_audio(audio: bytes) -> str:
        cutoff = time.monotonic() - 15 * 60
        expired = [key for key, (created, _) in audio_cache.items() if created < cutoff]
        for key in expired:
            del audio_cache[key]
        while len(audio_cache) >= 128:
            oldest = min(audio_cache, key=lambda key: audio_cache[key][0])
            del audio_cache[oldest]
        token = secrets.token_urlsafe(18)
        audio_cache[token] = (time.monotonic(), audio)
        return token

    async def synthesize_voice_bytes(
        *,
        request_id: str,
        text: str,
        speaker: str,
        speed: float,
        reference: str = "",
        style: str = "balanced",
        noise_scale: float | None = None,
        noise_scale_w: float | None = None,
        sdp_ratio: float | None = None,
    ) -> bytes:
        if request_id in voice_jobs:
            raise HTTPException(409, "Voice request is already running.")
        cancelled_at = cancelled_voice_jobs.get(request_id)
        if cancelled_at is not None and cancelled_at > time.monotonic() - 300:
            raise HTTPException(409, "Speech was interrupted.")
        if len(voice_jobs) >= 16:
            raise HTTPException(429, "Too many pending voice requests.")
        cancellation = VoiceCancellation()
        voice_jobs[request_id] = cancellation
        try:
            result = await synthesize_openvoice(
                data_dir=config.data_dir,
                text=text,
                speaker=speaker,
                speed=speed,
                reference=reference,
                style=style,
                noise_scale=noise_scale,
                noise_scale_w=noise_scale_w,
                sdp_ratio=sdp_ratio,
                cancellation=cancellation,
            )
            cancellation.check()
            audio = result.get("audio", b"")
            if not isinstance(audio, bytes) or not audio:
                raise VoiceError("Voice synthesis returned no audio.")
            return audio
        finally:
            voice_jobs.pop(request_id, None)
            cancellation.close()

    def require_session(request: Request) -> None:
        if network_mode:
            network_cookie = request.cookies.get("alice_network_access", "")
            if not hmac.compare_digest(network_cookie, network_access_token):
                raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Use Alice's LAN connection link first")
        supplied = request.cookies.get("alice_session") or request.headers.get("X-Alice-Token", "")
        if not supplied or not hmac.compare_digest(supplied, session_token):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Open Alice OS first")
        origin = request.headers.get("origin")
        if origin:
            parsed = urlparse(origin)
            request_host = request.headers.get("host", "").split(":", 1)[0].lower()
            allowed_origin = {"127.0.0.1", "localhost", request_host}
            if parsed.hostname not in allowed_origin:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Origin is not allowed")

    # Network enrolment is authenticated with this host's existing account.
    # The password is verified only for the one HTTPS request and is never kept
    # in cluster state or the worker's secret store.
    mount_cluster(
        app,
        cluster,
        require_session,
        lambda username, password: network_auth_file.is_file()
        and verify_auth_file(network_auth_file, username, password),
    )

    async def available_models(profile: ProviderProfile) -> list[str]:
        if profile.kind == "cluster":
            return await cluster.list_models(profile)
        return await list_models(profile)

    def get_huggingface_token(provided: str = "") -> str:
        if provided.strip():
            return provided.strip()
        try:
            return huggingface_token_store.get() or ""
        except SecretStoreError as error:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "The saved Hugging Face token could not be unlocked on this host.",
            ) from error

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/system/status", dependencies=[Depends(require_session)])
    async def system_status() -> dict[str, Any]:
        return await diagnostics.snapshot(
            config=config, runs=runs, list_models=available_models, version=__version__,
        )

    @app.get("/api/auth/status")
    async def auth_status(request: Request) -> dict[str, bool]:
        authenticated = not network_mode or hmac.compare_digest(
            request.cookies.get("alice_network_access", ""), network_access_token
        )
        return {
            "required": network_mode,
            "authenticated": authenticated,
            "setup_required": network_mode and not network_auth_file.is_file(),
        }

    @app.post("/api/auth/setup")
    async def auth_setup(body: NetworkLogin) -> Response:
        if not network_mode:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "LAN authentication is not enabled")
        if network_auth_file.exists():
            raise HTTPException(status.HTTP_409_CONFLICT, "LAN account already exists")
        try:
            create_auth_file(network_auth_file, body.username, body.password)
        except ValueError as error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error
        response = Response(content=json.dumps({"authenticated": True}), media_type="application/json")
        response.set_cookie(
            "alice_network_access", network_access_token, httponly=True,
            samesite="strict", secure=False, max_age=60 * 60 * 24 * 365,
        )
        return response

    @app.post("/api/auth/login")
    async def auth_login(body: NetworkLogin) -> Response:
        if not network_mode or (
            network_auth_file.is_file() and verify_auth_file(network_auth_file, body.username, body.password)
        ):
            response = Response(content=json.dumps({"authenticated": True}), media_type="application/json")
            if network_mode:
                response.set_cookie(
                    "alice_network_access", network_access_token, httponly=True,
                    samesite="strict", secure=False, max_age=60 * 60 * 24 * 365,
                )
            return response
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")

    @app.get("/", include_in_schema=False)
    async def index(request: Request) -> Response:
        response = FileResponse(
            web_dir / "index.html",
            headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
        )
        response.set_cookie(
            "alice_session",
            session_token,
            httponly=True,
            samesite="strict",
            secure=https_mode,
            max_age=86400,
        )
        return response

    @app.get("/voice", include_in_schema=False)
    async def voice_page(request: Request) -> Response:
        """Serve the dedicated Alice Voice Studio route with the normal session cookie."""
        return await index(request)

    @app.get("/cluster", include_in_schema=False)
    async def cluster_page(request: Request) -> Response:
        response = await index(request)
        return FileResponse(web_dir / "cluster.html", headers=dict(response.headers))

    @app.get("/models", include_in_schema=False)
    async def models_page(request: Request) -> Response:
        """Serve the dedicated Alice model-management route with the normal session cookie."""
        return await index(request)

    @app.get("/world", include_in_schema=False)
    async def world_page(request: Request) -> Response:
        response = await index(request)
        return FileResponse(web_dir / "world.html", headers=dict(response.headers))

    def require_world_host(request: Request) -> None:
        require_session(request)
        if not is_host_client(request.client.host if request.client else ""):
            raise HTTPException(403, "World View runs on the Alice host. Open Alice on that computer to control the globe.")

    @app.get("/api/world/status", dependencies=[Depends(require_session)])
    async def world_status(request: Request) -> dict[str, Any]:
        local = is_host_client(request.client.host if request.client else "")
        result = world_view.status()
        result["can_control"] = local
        if not local:
            result["url"] = None
            result["access_message"] = "World View runs on the Alice host. Open Alice on that computer to control and view the globe."
        return result

    @app.post("/api/world/start", dependencies=[Depends(require_world_host)])
    async def world_start() -> dict[str, Any]:
        try:
            return await world_view.start()
        except (RuntimeError, OSError) as error:
            raise HTTPException(409, str(error)) from error

    @app.post("/api/world/stop", dependencies=[Depends(require_world_host)])
    async def world_stop() -> dict[str, Any]:
        return await world_view.stop()

    @app.get("/api/state", dependencies=[Depends(require_session)])
    async def state(include_runtimes: bool = True) -> dict[str, Any]:
        settings = config.get()
        return {
            "version": __version__,
            "active_provider_id": settings.active_provider_id,
            "selected_model": settings.active_model,
            "providers": [provider.model_dump() for provider in settings.providers],
            "sessions": storage.list_sessions(),
            "runtimes": await cached_runtime_status() if include_runtimes else None,
            "voice": {**openvoice_status(), "pipeline": voice_pipeline_status()},
            "privacy": {
                "api_bind": "loopback",
                "workspace_boundary": "selected directory",
                "write_policy": "approval required",
            },
        }

    @app.get("/api/skills", dependencies=[Depends(require_session)])
    async def skills() -> dict[str, Any]:
        return {"skills": app.state.skills.list()}

    @app.get("/api/skill-packages", dependencies=[Depends(require_session)])
    async def skill_packages() -> dict[str, Any]:
        return {"packages": app.state.skills.packages.list(),
                "templates": [manifest.model_dump() for manifest in TEMPLATES],
                "error": app.state.skills.packages.load_error,
                "tools": runs.tools.definitions()}

    @app.post("/api/skill-packages", dependencies=[Depends(require_session)])
    async def install_skill_package(body: SkillManifest) -> dict[str, Any]:
        try:
            return {"package": app.state.skills.install_package(body)}
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @app.patch("/api/skill-packages/{package_id}", dependencies=[Depends(require_session)])
    async def enable_skill_package(package_id: str, body: PackageEnabled) -> dict[str, Any]:
        try:
            return {"package": app.state.skills.packages.set_enabled(package_id, body.enabled)}
        except KeyError as error:
            raise HTTPException(404, "Unknown skill package") from error
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @app.get("/api/skill-packages/{package_id}/manifest", dependencies=[Depends(require_session)])
    async def export_skill_package(package_id: str) -> dict[str, Any]:
        try:
            return app.state.skills.packages.export(package_id)
        except KeyError as error:
            raise HTTPException(404, "Unknown skill package") from error

    @app.delete("/api/skill-packages/{package_id}", dependencies=[Depends(require_session)])
    async def remove_skill_package(package_id: str) -> Response:
        try:
            app.state.skills.packages.delete(package_id)
        except KeyError as error:
            raise HTTPException(404, "Unknown skill package") from error
        except ValueError as error:
            raise HTTPException(400, str(error)) from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/api/skills", dependencies=[Depends(require_session)])
    async def save_skill(body: SkillUpsert) -> dict[str, Any]:
        try:
            skill = app.state.skills.upsert(AgentSkill(**body.model_dump()))
        except ValueError as error:
            raise HTTPException(400, str(error)) from error
        return {"skill": app.state.skills._public(skill, built_in=False)}

    @app.delete(
        "/api/skills/{skill_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[Depends(require_session)],
    )
    async def remove_skill(skill_id: str) -> Response:
        try:
            app.state.skills.delete(skill_id)
        except KeyError as error:
            raise HTTPException(404, "Unknown custom skill") from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/api/providers", dependencies=[Depends(require_session)])
    async def save_provider(profile: ProviderProfile) -> dict[str, Any]:
        if profile.kind == "cluster" or profile.id in cluster.data["nodes"]:
            raise HTTPException(400, "Manage paired workers from the Cluster page")
        _validate_provider_url(profile)
        settings = config.upsert_provider(profile)
        return {"providers": [item.model_dump() for item in settings.providers]}

    @app.delete("/api/providers/{provider_id}", dependencies=[Depends(require_session)])
    async def remove_provider(provider_id: str) -> dict[str, Any]:
        if provider_id in cluster.data["nodes"]:
            raise HTTPException(400, "Remove paired workers from the Cluster page")
        try:
            settings = config.delete_provider(provider_id)
        except ValueError as error:
            raise HTTPException(400, str(error)) from error
        return {"providers": [item.model_dump() for item in settings.providers]}

    @app.post("/api/providers/active", dependencies=[Depends(require_session)])
    async def select_provider(body: ActiveProvider) -> dict[str, str]:
        try:
            config.set_active(body.provider_id)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        return {"active_provider_id": body.provider_id}

    @app.post("/api/models/active", dependencies=[Depends(require_session)])
    async def select_model(body: ActiveModel) -> dict[str, str]:
        if body.provider_id:
            try:
                config.set_active(body.provider_id)
            except KeyError as error:
                raise HTTPException(404, str(error)) from error
        settings = config.set_active_model(body.model)
        return {
            "active_provider_id": settings.active_provider_id,
            "selected_model": settings.active_model,
        }

    @app.get("/api/providers/{provider_id}/models", dependencies=[Depends(require_session)])
    async def provider_models(provider_id: str) -> dict[str, list[str]]:
        try:
            profile = config.get_provider(provider_id)
            models = await available_models(profile)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        except ProviderError as error:
            raise HTTPException(502, str(error)) from error
        return {"models": models}

    @app.get("/api/models/catalog", dependencies=[Depends(require_session)])
    async def model_catalog() -> dict[str, Any]:
        settings = config.get()

        async def provider_models_for_catalog(provider: ProviderProfile) -> tuple[ProviderProfile, list[str], str]:
            try:
                models = await asyncio.wait_for(available_models(provider), timeout=3)
                error = ""
            except (ProviderError, TimeoutError) as exc:
                models = []
                error = str(exc) or "Model discovery timed out."
            if provider.default_model and provider.default_model not in models:
                models = [provider.default_model, *models]
            return provider, models, error

        results = await asyncio.gather(
            *(provider_models_for_catalog(provider) for provider in settings.providers)
        )
        catalog: list[dict[str, str]] = []
        errors: list[dict[str, str]] = []
        for provider, models, error in results:
            if error:
                errors.append({"provider_id": provider.id, "message": error})
            for model in models:
                catalog.append(
                    {
                        "id": model,
                        "name": _model_display_name(model),
                        "provider_id": provider.id,
                        "provider_name": provider.name,
                        "backend": provider.kind,
                    }
                )
        return {"models": catalog, "errors": errors}

    @app.post("/api/sessions", dependencies=[Depends(require_session)])
    async def create_session(body: SessionCreate) -> dict[str, Any]:
        workspace = _resolve_workspace(body.workspace)
        return storage.create_session(
            title=body.title,
            workspace=workspace,
            provider_id=body.provider_id,
            model=body.model,
        )

    @app.get("/api/sessions/{session_id}", dependencies=[Depends(require_session)])
    async def get_session(session_id: str) -> dict[str, Any]:
        try:
            return storage.get_session(session_id)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error

    @app.patch("/api/sessions/{session_id}", dependencies=[Depends(require_session)])
    async def update_session(session_id: str, body: SessionUpdate) -> dict[str, Any]:
        changes = body.model_dump(exclude_none=True)
        if runs.active_for_session(session_id) and {"workspace", "provider_id", "model"} & changes.keys():
            raise HTTPException(409, "Stop this conversation's running task before changing its workspace or model.")
        if "workspace" in changes:
            changes["workspace"] = _resolve_workspace(changes["workspace"])
        try:
            return storage.update_session(session_id, **changes)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error

    @app.delete(
        "/api/sessions/{session_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[Depends(require_session)],
    )
    async def delete_session(session_id: str) -> Response:
        try:
            storage.get_session(session_id, include_messages=False)
            active_run = runs.active_for_session(session_id)
            if active_run:
                await runs.cancel(active_run.id)
            storage.delete_session(session_id)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/api/runs", dependencies=[Depends(require_session)])
    async def create_run(body: RunCreate) -> dict[str, str]:
        local_command = parse_memory_command(body.message) is not None
        if not body.model.strip() and not local_command:
            raise HTTPException(400, "Select a model before starting a task.")
        try:
            if not local_command:
                config.get_provider(body.provider_id)
            run = runs.start(
                session_id=body.session_id,
                user_message=body.message,
                provider_id=body.provider_id,
                model=body.model,
                agent_mode=body.agent_mode,
                skill_id=body.skill_id,
                response_depth=body.response_depth,
                spoken_response=body.spoken_response,
            )
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        except RunConflictError as error:
            raise HTTPException(409, str(error)) from error
        except RunCapacityError as error:
            raise HTTPException(429, str(error)) from error
        except ValueError as error:
            raise HTTPException(400, str(error)) from error
        return {"run_id": run.id}

    @app.get("/api/runs/{run_id}/events", dependencies=[Depends(require_session)])
    async def run_events(run_id: str, request: Request, after: int = 0) -> StreamingResponse:
        try:
            run = runs.get(run_id)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        # EventSource supplies this cursor when automatically reconnecting.
        try:
            cursor = max(after, int(request.headers.get("last-event-id", "0")))
        except ValueError as error:
            raise HTTPException(400, "Last-Event-ID must be an integer event sequence.") from error

        async def event_stream() -> AsyncIterator[str]:
            async for event in run.stream(cursor):
                data = {"sequence": event.sequence, **event.data}
                yield (
                    f"id: {event.sequence}\n"
                    f"event: {event.name}\n"
                    f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                )

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "X-Accel-Buffering": "no",
            },
        )

    @app.post("/api/runs/{run_id}/approval", dependencies=[Depends(require_session)])
    async def decide_approval(run_id: str, body: ApprovalDecision) -> dict[str, bool]:
        try:
            await runs.approve(run_id, body.call_id, body.approved)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        return {"accepted": True}

    @app.post("/api/runs/{run_id}/cancel", dependencies=[Depends(require_session)])
    async def cancel_run(run_id: str) -> dict[str, bool]:
        try:
            await runs.cancel(run_id)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        return {"cancelled": True}

    @app.get("/api/runtime/status", dependencies=[Depends(require_session)])
    async def get_runtime_status() -> dict[str, Any]:
        return await cached_runtime_status()

    @app.get("/api/memories", dependencies=[Depends(require_session)])
    async def list_memories() -> dict[str, Any]:
        return {"memories": storage.list_global_memories(10000, include_pending=True)}

    @app.post("/api/memories", dependencies=[Depends(require_session)])
    async def create_memory(body: MemoryCreate) -> dict[str, Any]:
        try:
            return storage.add_global_memory(
                body.content.strip(), category=body.category, memory_key=body.key,
                importance=body.importance, confidence=body.confidence, source="manual",
            )
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @app.post("/api/memories/{memory_id}/approve", dependencies=[Depends(require_session)])
    async def approve_memory(memory_id: str) -> dict[str, Any]:
        try:
            return storage.approve_global_memory(memory_id)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @app.delete("/api/memories/{memory_id}", dependencies=[Depends(require_session)])
    async def delete_memory(memory_id: str) -> dict[str, Any]:
        try:
            storage.delete_global_memory(memory_id)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        return {"deleted": True, "id": memory_id}

    @app.patch("/api/memories/{memory_id}", dependencies=[Depends(require_session)])
    async def update_memory(memory_id: str, body: MemoryUpdate) -> dict[str, Any]:
        try:
            return storage.update_global_memory(
                memory_id,
                content=body.content,
                category=body.category,
                memory_key=body.key,
                importance=body.importance,
                confidence=body.confidence,
            )
        except (KeyError, ValueError) as error:
            raise HTTPException(400, str(error)) from error

    @app.get("/api/models/library", dependencies=[Depends(require_session)])
    async def model_library() -> dict[str, Any]:
        library = await local_model_library(config.data_dir)
        library["models"] = await model_manager.list()
        library["total_bytes"] = sum(item["size"] for item in library["models"]) + sum(item.get("size") or 0 for item in library["ollama"])
        return library

    @app.post("/api/models/file/delete", dependencies=[Depends(require_session)])
    async def delete_downloaded_file(body: ModelLoad) -> dict[str, Any]:
        try:
            return await model_manager.delete(body.model_path)
        except (RuntimeOperationError, OSError) as error:
            raise HTTPException(400, str(error)) from error

    @app.post("/api/models/load", dependencies=[Depends(require_session)])
    async def load_downloaded_model(body: ModelLoad) -> dict[str, Any]:
        if any(run.task and not run.task.done() for run in runs.runs.values()):
            raise HTTPException(409, "Wait for the active response to finish before switching models")
        try:
            return await model_manager.load(body.model_path)
        except (RuntimeOperationError, OSError) as error:
            raise HTTPException(400, str(error)) from error

    @app.post("/api/models/janus/stop", dependencies=[Depends(require_session)])
    async def stop_janus_model() -> dict[str, Any]:
        if any(run.task and not run.task.done() for run in runs.runs.values()):
            raise HTTPException(409, "Wait for the active response to finish before stopping Janus")
        try:
            return await model_manager.stop_janus()
        except (RuntimeOperationError, OSError, psutil.Error) as error:
            raise HTTPException(400, str(error)) from error

    @app.get("/api/distributed", dependencies=[Depends(require_session)])
    async def distributed_settings() -> dict[str, Any]:
        return model_manager.distributed.get().model_dump()

    @app.post("/api/images/generate", dependencies=[Depends(require_session)])
    async def generate_image(body: ImageCreate) -> dict[str, Any]:
        if not body.prompt.strip():
            raise HTTPException(422, "Enter an image description")
        try:
            async with httpx.AsyncClient(timeout=300, trust_env=False) as client:
                response = await client.post("http://127.0.0.1:8082/v1/images/generations", json={"prompt": body.prompt})
            if response.status_code == 429:
                raise HTTPException(409, "Janus is busy. Wait for the current chat or image to finish.")
            if response.status_code == 404:
                raise HTTPException(409, "Restart the Janus runtime to enable image generation.")
            response.raise_for_status()
            encoded = response.json()["data"][0]["b64_json"]
            if not isinstance(encoded, str) or len(encoded) > 8 * 1024 * 1024:
                raise ValueError("Invalid image response size")
            data = base64.b64decode(encoded, validate=True)
            if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("Invalid PNG response")
        except HTTPException:
            raise
        except httpx.ConnectError as error:
            raise HTTPException(409, "Start Janus from Models → Installed before generating an image.") from error
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as error:
            raise HTTPException(502, "Janus could not generate an image. Check janus-server.log and retry.") from error
        directory = config.data_dir / "generated-images"
        directory.mkdir(exist_ok=True)
        image_id = secrets.token_hex(16)
        await asyncio.to_thread((directory / f"{image_id}.png").write_bytes, data)
        return {"url": f"/api/images/{image_id}", "prompt": body.prompt}

    @app.get("/api/images/{image_id}", dependencies=[Depends(require_session)])
    async def generated_image(image_id: str) -> Response:
        if len(image_id) != 32 or any(c not in "0123456789abcdef" for c in image_id):
            raise HTTPException(404, "Image not found")
        path = config.data_dir / "generated-images" / f"{image_id}.png"
        if not path.is_file():
            raise HTTPException(404, "Image not found")
        return Response(await asyncio.to_thread(path.read_bytes), media_type="image/png",
                        headers={"Cache-Control": "private, no-store"})

    @app.put("/api/distributed", dependencies=[Depends(require_session)])
    async def save_distributed_settings(body: DistributedSettings):
        async with model_manager.lock:
            model_manager.distributed.save(body)
        return {**body.model_dump(), "reload_required": True}

    @app.post("/api/distributed/probe", dependencies=[Depends(require_session)])
    async def distributed_probe(body: DistributedSettings):
        from .runtimes import llama_cpp_executable
        try:
            resolved = await cluster.bridges.resolve(body)
            return {"devices": await probe_devices(llama_cpp_executable(), resolved)}
        except (RuntimeOperationError, OSError, TimeoutError) as error:
            raise HTTPException(400, str(error) or "GPU discovery timed out") from error

    @app.get("/api/localai/models", dependencies=[Depends(require_session)])
    async def localai_models() -> dict[str, Any]:
        try:
            catalog = dict(await alice_model_catalog(data_dir=config.data_dir))
            catalog["installed"] = await model_manager.list()
            return catalog
        except RuntimeOperationError as error:
            raise HTTPException(502, str(error)) from error

    @app.get("/api/localai/models/requirements", dependencies=[Depends(require_session)])
    async def localai_model_requirements_action(name: str) -> dict[str, Any]:
        try:
            return await alice_model_requirements(data_dir=config.data_dir, model_name=name)
        except RuntimeOperationError as error:
            raise HTTPException(502, str(error)) from error

    async def queue_localai_download(name: str, variant: str = "") -> dict[str, Any]:
        # Repeated clicks / tabs must share an active transfer, not compete to
        # write the same model files. No await occurs before inserting the job.
        for existing in localai_download_jobs.values():
            if (existing.get("model") == name and existing.get("variant", "") == variant
                    and existing.get("status") in {"queued", "downloading"}):
                return existing
        alice_job_id = secrets.token_urlsafe(12)
        job = {
            "id": alice_job_id,
            "runtime": "alice",
            "model": name,
            "variant": variant,
            "status": "queued",
            "progress": 0,
            "downloaded_bytes": 0,
            "total_bytes": 0,
            "files_downloaded": 0,
            "speed_bytes_per_second": 0,
            "eta_seconds": None,
            "message": "Queued in Alice.",
            "created_at": time.time(),
        }
        localai_download_jobs[alice_job_id] = job

        async def run_download() -> None:
            job.update(status="downloading", message="Alice is downloading the selected model…")
            started_at = time.monotonic()
            previous_bytes = 0
            previous_at = started_at

            async def update_progress(update: dict[str, Any]) -> None:
                nonlocal previous_bytes, previous_at
                now = time.monotonic()
                downloaded_bytes = int(update.get("downloaded_bytes") or 0)
                delta = downloaded_bytes - previous_bytes
                elapsed = now - previous_at
                if delta > 0 and elapsed > 0:
                    instant_speed = delta / elapsed
                    old_speed = float(job.get("speed_bytes_per_second") or 0)
                    speed = instant_speed if old_speed <= 0 else (old_speed * 0.7) + (instant_speed * 0.3)
                    update["speed_bytes_per_second"] = round(speed)
                    total_bytes = int(update.get("total_bytes") or 0)
                    if total_bytes > downloaded_bytes and speed > 0:
                        update["eta_seconds"] = max(0, round((total_bytes - downloaded_bytes) / speed))
                previous_bytes = downloaded_bytes
                previous_at = now
                job.update(update)

            try:
                result = await download_alice_model(
                    data_dir=config.data_dir,
                    model_id=name,
                    variant=variant,
                    on_progress=update_progress,
                )
            except RuntimeOperationError as error:
                job.update(status="failed", message=str(error))
                return
            except Exception:
                job.update(status="failed", message="The Alice model downloader stopped unexpectedly.")
                return
            job.update(
                status="complete",
                progress=100,
                downloaded_bytes=result.get("downloaded_bytes", job["downloaded_bytes"]),
                files_downloaded=result.get("file_count", job["files_downloaded"]),
                message="Model download complete.",
                result=result,
            )
            clear_localai_model_catalog_cache()

        task = asyncio.create_task(run_download())
        download_tasks.add(task)
        task.add_done_callback(download_tasks.discard)
        return job

    @app.get("/api/localai/downloads", dependencies=[Depends(require_session)])
    async def localai_downloads() -> dict[str, Any]:
        jobs = sorted(
            localai_download_jobs.values(),
            key=lambda job: float(job.get("created_at", 0)),
            reverse=True,
        )
        return {"downloads": jobs}

    @app.get("/api/localai/downloads/{job_id}", dependencies=[Depends(require_session)])
    async def localai_download(job_id: str) -> dict[str, Any]:
        try:
            return localai_download_jobs[job_id]
        except KeyError as error:
            raise HTTPException(404, "Download job was not found") from error

    @app.post("/api/localai/downloads/{job_id}/retry", dependencies=[Depends(require_session)])
    async def retry_localai_download(job_id: str) -> dict[str, Any]:
        try:
            previous = localai_download_jobs[job_id]
        except KeyError as error:
            raise HTTPException(404, "Download job was not found") from error
        if previous.get("status") != "failed":
            raise HTTPException(400, "Only failed downloads can be retried")
        try:
            return await queue_localai_download(
                str(previous["model"]), str(previous.get("variant") or "")
            )
        except RuntimeOperationError as error:
            raise HTTPException(400, str(error)) from error

    @app.post("/api/localai/models/install", dependencies=[Depends(require_session)])
    async def install_localai_model_action(body: LocalAIModelAction) -> dict[str, Any]:
        try:
            return await queue_localai_download(body.name, body.variant)
        except RuntimeOperationError as error:
            raise HTTPException(400, str(error)) from error

    @app.post("/api/localai/models/delete", dependencies=[Depends(require_session)])
    async def delete_localai_runtime_model_action(body: LocalAIModelAction) -> dict[str, Any]:
        try:
            return await asyncio.to_thread(delete_alice_model, data_dir=config.data_dir, model_name=body.name)
        except RuntimeOperationError as error:
            raise HTTPException(400, str(error)) from error

    async def _delete_model(body: ModelDelete) -> dict[str, Any]:
        try:
            if body.source == "Ollama":
                result = await delete_ollama_model(body.name)
                if config.get().active_model == body.name:
                    config.set_active_model("")
                return result
            if body.source == "LocalAI":
                result = await asyncio.to_thread(
                    delete_localai_model,
                    data_dir=config.data_dir,
                    model_name=body.name,
                )
                if config.get().active_model == body.name:
                    config.set_active_model("")
                return result
            return await asyncio.to_thread(
                delete_huggingface_model,
                data_dir=config.data_dir,
                model_name=body.name,
            )
        except (RuntimeOperationError, OSError) as error:
            raise HTTPException(400, str(error)) from error

    @app.delete("/api/models/library", dependencies=[Depends(require_session)])
    async def delete_model(body: ModelDelete) -> dict[str, Any]:
        return await _delete_model(body)

    @app.post("/api/models/library/delete", dependencies=[Depends(require_session)])
    async def delete_model_action(body: ModelDelete) -> dict[str, Any]:
        return await _delete_model(body)

    @app.get("/api/workspace/files", dependencies=[Depends(require_session)])
    async def workspace_files(workspace: str, path: str = ".") -> dict[str, Any]:
        resolved_workspace = _resolve_workspace(workspace)
        context = ToolContext(workspace=Path(resolved_workspace), session_id="", storage=storage)
        try:
            return await workspace_list(context, {"path": path, "limit": 300})
        except (ToolError, OSError) as error:
            raise HTTPException(400, str(error)) from error

    @app.get("/api/workspace/read", dependencies=[Depends(require_session)])
    async def read_workspace_file(workspace: str, path: str) -> dict[str, Any]:
        resolved_workspace = _resolve_workspace(workspace)
        context = ToolContext(workspace=Path(resolved_workspace), session_id="", storage=storage)
        try:
            return await workspace_read(context, {"path": path})
        except (ToolError, OSError) as error:
            raise HTTPException(400, str(error)) from error

    @app.get("/api/workspace/git", dependencies=[Depends(require_session)])
    async def workspace_git(workspace: str) -> dict[str, Any]:
        return await _workspace_git_status(_resolve_workspace(workspace))

    @app.get("/api/workspace/diff", dependencies=[Depends(require_session)])
    async def workspace_diff(workspace: str, path: str) -> dict[str, Any]:
        return await _workspace_git_diff(_resolve_workspace(workspace), path)

    @app.post("/api/gguf/import", dependencies=[Depends(require_session)])
    async def import_local_gguf(body: GGUFImport) -> dict[str, Any]:
        try:
            if body.runtime == "localai":
                return await import_localai_gguf(
                    data_dir=config.data_dir,
                    gguf_path=body.path,
                    requested_name=body.name,
                )
            return await import_gguf(
                data_dir=config.data_dir,
                gguf_path=body.path,
                requested_name=body.name,
            )
        except (RuntimeOperationError, OSError) as error:
            raise HTTPException(400, str(error)) from error

    @app.post("/api/models/pull", dependencies=[Depends(require_session)])
    async def pull_model(body: ModelPull) -> dict[str, Any]:
        try:
            return await pull_ollama_model(body.name)
        except RuntimeOperationError as error:
            raise HTTPException(400, str(error)) from error

    @app.get("/api/huggingface/files", dependencies=[Depends(require_session)])
    async def huggingface_files(repository: str, revision: str = "main") -> dict[str, Any]:
        try:
            details = await inspect_huggingface_repository(
                repository, revision, get_huggingface_token()
            )
        except RuntimeOperationError as error:
            raise HTTPException(400, str(error)) from error
        return {**details, "files": details["gguf_files"]}

    @app.get("/api/huggingface/token", dependencies=[Depends(require_session)])
    async def huggingface_token_status() -> dict[str, Any]:
        try:
            configured = bool(huggingface_token_store.get())
        except SecretStoreError as error:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "The saved Hugging Face token could not be unlocked on this host.",
            ) from error
        return {
            "configured": configured,
            "storage": "Windows user encryption" if os.name == "nt" else "Host-local protected file",
        }

    @app.post("/api/huggingface/token", dependencies=[Depends(require_session)])
    async def save_huggingface_token(body: HuggingFaceToken) -> dict[str, Any]:
        try:
            huggingface_token_store.set(body.token)
        except (SecretStoreError, ValueError) as error:
            raise HTTPException(400, str(error)) from error
        return {"configured": True}

    @app.delete("/api/huggingface/token", dependencies=[Depends(require_session)])
    async def clear_huggingface_token() -> dict[str, Any]:
        try:
            huggingface_token_store.clear()
        except SecretStoreError as error:
            raise HTTPException(400, str(error)) from error
        return {"configured": False}

    @app.post("/api/huggingface/inspect", dependencies=[Depends(require_session)])
    async def inspect_huggingface_model(body: HuggingFaceInspect) -> dict[str, Any]:
        try:
            details = await inspect_huggingface_repository(
                body.repository, body.revision, get_huggingface_token(body.token)
            )
        except RuntimeOperationError as error:
            raise HTTPException(400, str(error)) from error
        return {**details, "files": details["gguf_files"]}

    @app.post("/api/huggingface/download", dependencies=[Depends(require_session)])
    async def download_huggingface_model(body: HuggingFaceDownload) -> dict[str, Any]:
        job_id = secrets.token_urlsafe(12)
        job = {
            "id": job_id,
            "status": "queued",
            "repository": body.repository,
            "revision": body.revision,
            "message": "Queued locally.",
            "progress": 0,
            "downloaded_bytes": 0,
            "files_downloaded": 0,
            "total_bytes": body.expected_bytes,
        }
        download_jobs[job_id] = job

        async def run_download() -> None:
            job.update(status="downloading", message="Downloading model files from Hugging Face…")
            worker = asyncio.create_task(
                download_huggingface_repository(
                    data_dir=config.data_dir,
                    repository=body.repository,
                    revision=body.revision,
                    token=get_huggingface_token(body.token),
                )
            )
            try:
                while not worker.done():
                    progress = await asyncio.to_thread(
                        huggingface_download_progress,
                        data_dir=config.data_dir,
                        repository=body.repository,
                    )
                    downloaded = progress["downloaded_bytes"]
                    job.update(**progress)
                    if body.expected_bytes:
                        job["progress"] = min(99, round(downloaded / body.expected_bytes * 100))
                    await asyncio.sleep(0.8)
                result = await worker
            except RuntimeOperationError as error:
                job.update(status="failed", message=str(error))
            except Exception:
                job.update(
                    status="failed", message="The local download worker stopped unexpectedly."
                )
            else:
                job.update(
                    status="complete",
                    progress=100,
                    downloaded_bytes=result.get("downloaded_bytes", 0),
                    files_downloaded=result.get("file_count", 0),
                    total_bytes=body.expected_bytes,
                    message="Model files saved locally.",
                    result=result,
                )

        task = asyncio.create_task(run_download())
        download_tasks.add(task)
        task.add_done_callback(download_tasks.discard)
        return job

    @app.get("/api/huggingface/downloads/{job_id}", dependencies=[Depends(require_session)])
    async def huggingface_download_status(job_id: str) -> dict[str, Any]:
        try:
            return download_jobs[job_id]
        except KeyError as error:
            raise HTTPException(404, "Download job was not found") from error

    @app.post("/api/huggingface/import", dependencies=[Depends(require_session)])
    async def import_huggingface_model(body: HuggingFaceImport) -> dict[str, Any]:
        try:
            return await import_huggingface_gguf(
                data_dir=config.data_dir,
                repository=body.repository,
                filename=body.filename,
                revision=body.revision,
                requested_name=body.name,
                token=get_huggingface_token(body.token),
                runtime="localai",
            )
        except RuntimeOperationError as error:
            raise HTTPException(400, str(error)) from error

    @app.get("/api/voice/status", dependencies=[Depends(require_session)])
    async def voice_status() -> dict[str, Any]:
        return {
            **openvoice_status(),
            "kokoro": {key: value for key, value in kokoro.status().items() if key != "python"},
            "transcription": transcription_status(),
            "worker": await voice_worker_status(),
            "pipeline": voice_pipeline_status(),
        }

    @app.get("/api/voicebox/status", dependencies=[Depends(require_session)])
    async def voicebox_status(request: Request) -> dict[str, Any]:
        return {**await voicebox.status(),
                "can_start": is_host_client(request.client.host if request.client else "")}

    @app.post("/api/voicebox/start", dependencies=[Depends(require_session)])
    async def voicebox_start(request: Request) -> dict[str, Any]:
        if not is_host_client(request.client.host if request.client else ""):
            raise HTTPException(403, "Start Voicebox from the Alice host computer.")
        try:
            return await voicebox_runtime.start()
        except (ValueError, OSError) as error:
            raise HTTPException(503, str(error)) from error

    @app.post("/api/voicebox/studio", dependencies=[Depends(require_session)])
    async def voicebox_studio(request: Request) -> dict[str, Any]:
        if not is_host_client(request.client.host if request.client else ""):
            raise HTTPException(403, "Open Voicebox Studio from the Alice host computer.")
        try:
            return await voicebox_runtime.open_studio()
        except (ValueError, OSError) as error:
            raise HTTPException(503, str(error)) from error

    @app.post("/api/voice/transcribe", dependencies=[Depends(require_session)])
    async def voice_transcribe(audio: UploadFile = File(...)) -> dict[str, str]:
        try:
            content = await audio.read(25 * 1024 * 1024 + 1)
            return await transcribe_openvoice_audio(filename=audio.filename or "dictation.webm", content=content)
        except VoiceError as error:
            raise HTTPException(503, str(error)) from error
        finally:
            await audio.close()

    @app.post("/api/voice/warm", dependencies=[Depends(require_session)])
    async def voice_warm() -> dict[str, Any]:
        try:
            return await warm_openvoice()
        except VoiceError as error:
            raise HTTPException(503, str(error)) from error

    @app.post("/api/voice/synthesize", dependencies=[Depends(require_session)])
    async def voice_synthesize(body: VoiceSynthesis) -> dict[str, str]:
        request_id = body.request_id or secrets.token_hex(16)
        try:
            audio = await synthesize_voice_bytes(
                request_id=request_id,
                text=body.text,
                speaker=body.speaker,
                speed=body.speed,
                reference=body.reference,
                style=body.style,
                noise_scale=body.noise_scale,
                noise_scale_w=body.noise_scale_w,
                sdp_ratio=body.sdp_ratio,
            )
            return {"url": f"/api/voice/audio/{cache_audio(audio)}"}
        except VoiceInterrupted as error:
            raise HTTPException(409, str(error)) from error
        except VoiceError as error:
            raise HTTPException(503, str(error)) from error

    @app.post("/v1/audio/speech", dependencies=[Depends(require_session)])
    @app.post("/tts", dependencies=[Depends(require_session)])
    async def openai_compatible_tts(body: OpenAITTSRequest) -> Response:
        """Expose Alice's local voice using the LocalAI/OpenAI TTS contract."""
        # OpenAI voice names are accepted for clients that already know that
        # contract; Alice still uses its configured local OpenVoice profile.
        voice = body.voice.strip()
        if voice.casefold() in {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}:
            voice = OPENVOICE_FEMALE_SPEAKER
        try:
            audio = await synthesize_voice_bytes(
                request_id=secrets.token_hex(16),
                text=body.input,
                speaker=voice or OPENVOICE_FEMALE_SPEAKER,
                speed=body.speed,
            )
            return Response(content=audio, media_type="audio/wav", headers={"Cache-Control": "no-store"})
        except VoiceInterrupted as error:
            raise HTTPException(409, str(error)) from error
        except VoiceError as error:
            raise HTTPException(503, str(error)) from error

    @app.post("/api/voice/cancel", dependencies=[Depends(require_session)])
    async def voice_cancel(body: VoiceCancel) -> dict[str, bool]:
        # Remember early cancellations: a cancel can overtake the synthesis POST.
        cutoff = time.monotonic() - 300
        for key in list(cancelled_voice_jobs):
            if cancelled_voice_jobs[key] < cutoff:
                del cancelled_voice_jobs[key]
        while len(cancelled_voice_jobs) >= 1024:
            del cancelled_voice_jobs[next(iter(cancelled_voice_jobs))]
        cancelled_voice_jobs[body.request_id] = time.monotonic()
        job = voice_jobs.get(body.request_id)
        if job:
            job.cancel()
        return {"cancelled": True}

    @app.websocket("/api/voice/activity")
    async def voice_activity(socket: WebSocket) -> None:
        supplied = socket.cookies.get("alice_session") or socket.headers.get("X-Alice-Token", "")
        network_cookie = socket.cookies.get("alice_network_access", "")
        origin = urlparse(socket.headers.get("origin", ""))
        # WebSockets need their own authentication and exact-origin check.
        if (
            (network_mode and not hmac.compare_digest(network_cookie, network_access_token))
            or not supplied or not hmac.compare_digest(supplied, session_token)
            or origin.scheme not in {"http", "https"}
            or origin.netloc != socket.headers.get("host")
        ):
            await socket.close(code=1008)
            return
        await socket.accept()
        detector = SpeechActivityDetector()
        await socket.send_json({"event": "ready", "sample_rate": 16000, "frame_ms": 20})
        try:
            while True:
                packet = await asyncio.wait_for(socket.receive(), timeout=30)
                if packet["type"] == "websocket.disconnect":
                    break
                pcm = packet.get("bytes")
                if pcm is None:
                    await socket.close(code=1003, reason="Send binary PCM16 audio.")
                    break
                for event in detector.feed(pcm):
                    await socket.send_json({"event": event})
        except (ValueError, TimeoutError):
            await socket.close(code=1008, reason="Invalid or inactive audio stream.")
        except WebSocketDisconnect:
            pass

    @app.websocket("/api/voice/conversation")
    async def voice_conversation(socket: WebSocket) -> None:
        supplied = socket.cookies.get("alice_session") or socket.headers.get("X-Alice-Token", "")
        network_cookie = socket.cookies.get("alice_network_access", "")
        origin = urlparse(socket.headers.get("origin", ""))
        expected_scheme = "https" if socket.url.scheme == "wss" else "http"
        if (
            (network_mode and not hmac.compare_digest(network_cookie, network_access_token))
            or not supplied or not hmac.compare_digest(supplied, session_token)
            or origin.scheme != expected_scheme
            or origin.netloc != socket.headers.get("host")
            or origin.path not in {"", "/"} or origin.query or origin.fragment
        ):
            await socket.close(code=1008)
            return
        await socket.accept()
        local_status = transcription_status()
        if not local_status["ready"]:
            await socket.send_json({
                "event": "error", "code": "unavailable", "recoverable": False,
                "message": local_status["message"],
            })
            await socket.close(code=1013, reason="Local speech recognition is unavailable.")
            return
        lease = ConversationLease.acquire()
        if lease is None:
            await socket.send_json({
                "event": "error", "code": "in_use", "recoverable": False,
                "message": "Hands-free conversation is already active in another window.",
            })
            await socket.close(code=1013, reason="Hands-free conversation is already in use.")
            return
        send_lock = asyncio.Lock()

        async def emit(event: dict[str, Any]) -> None:
            async with send_lock:
                await asyncio.wait_for(socket.send_json(event), timeout=5)

        conversation = HandsFreeConversation(transcribe=transcribe_openvoice_audio, emit=emit)
        try:
            await emit({
                "event": "ready", "sample_rate": 16000, "frame_ms": 20, "local": True,
                "max_utterance_seconds": 15,
            })
            last_packet = time.monotonic()
            while True:
                try:
                    packet = await asyncio.wait_for(socket.receive(), timeout=0.5)
                except TimeoutError:
                    if time.monotonic() - last_packet > 30:
                        await socket.close(code=1008, reason="Inactive audio stream.")
                        break
                    await conversation.tick()
                    continue
                last_packet = time.monotonic()
                if packet["type"] == "websocket.disconnect":
                    break
                pcm = packet.get("bytes")
                if pcm is not None:
                    await conversation.feed(pcm)
                    continue
                control = packet.get("text")
                if control is None or len(control) > 2048:
                    raise ValueError("Send PCM16 audio or a small JSON control message.")
                try:
                    message = json.loads(control)
                except (json.JSONDecodeError, RecursionError) as error:
                    raise ValueError("Control messages must be valid JSON objects.") from error
                if not isinstance(message, dict):
                    raise ValueError("Control messages must be JSON objects.")
                await conversation.control(message)
        except ValueError as error:
            await socket.close(code=1008, reason=str(error)[:120])
        except (WebSocketDisconnect, TimeoutError, RuntimeError, OSError):
            pass
        finally:
            pending = conversation.close()
            if pending is None:
                ConversationLease.release(lease)
            else:
                def release_when_finished(task: asyncio.Task[None]) -> None:
                    if not task.cancelled():
                        task.exception()
                    ConversationLease.release(lease)

                pending.add_done_callback(release_when_finished)

    @app.get("/api/voice/audio/{token}", dependencies=[Depends(require_session)])
    async def voice_audio(token: str) -> Response:
        clip = audio_cache.get(token)
        if clip is None or clip[0] < time.monotonic() - 15 * 60:
            audio_cache.pop(token, None)
            raise HTTPException(404, "Voice clip is no longer available")
        return Response(
            content=clip[1],
            media_type="audio/wav",
            headers={"Cache-Control": "private, max-age=900"},
        )

    @app.get("/api/voice/references", dependencies=[Depends(require_session)])
    async def voice_references() -> dict[str, Any]:
        return {"references": list_voice_references(config.data_dir)}

    @app.post("/api/voice/references", dependencies=[Depends(require_session)])
    async def upload_voice_reference(reference: UploadFile = File(...)) -> dict[str, str | int]:
        try:
            content = await reference.read(25 * 1024 * 1024 + 1)
            return save_voice_reference(
                data_dir=config.data_dir, filename=reference.filename or "reference.wav", content=content
            )
        except VoiceError as error:
            raise HTTPException(400, str(error)) from error
        finally:
            await reference.close()

    @app.delete("/api/voice/references/{name}", dependencies=[Depends(require_session)])
    async def delete_voice_reference(name: str) -> Response:
        try:
            remove_voice_reference(data_dir=config.data_dir, name=name)
        except VoiceError as error:
            raise HTTPException(400, str(error)) from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    app.mount("/static", StaticFiles(directory=web_dir), name="static")
    return app
