from __future__ import annotations

import asyncio
import hmac
import ipaddress
import json
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from .agent import RunManager
from .config import ConfigStore
from .models import ProviderProfile
from .providers import ProviderError, list_models
from .runtimes import (
    RuntimeOperationError,
    download_huggingface_repository,
    import_gguf,
    import_huggingface_gguf,
    inspect_huggingface_repository,
    local_model_library,
    pull_ollama_model,
    runtime_status,
)
from .storage import Storage
from .tools import ToolContext, ToolError, workspace_list, workspace_read
from .voice import (
    VoiceError,
    list_voice_references,
    openvoice_status,
    save_voice_reference,
    synthesize_openvoice,
)


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


class RunCreate(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=200_000)
    provider_id: str
    model: str
    agent_mode: bool = True


class ApprovalDecision(BaseModel):
    call_id: str
    approved: bool


class ActiveProvider(BaseModel):
    provider_id: str


class GGUFImport(BaseModel):
    path: str
    name: str = ""


class ModelPull(BaseModel):
    name: str


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


class HuggingFaceInspect(BaseModel):
    repository: str = Field(min_length=3, max_length=500)
    revision: str = Field(default="main", max_length=200)
    token: str = Field(default="", max_length=500)


class VoiceSynthesis(BaseModel):
    text: str = Field(min_length=1, max_length=8_000)
    speaker: str = Field(default="OPENVOICE-FEMALE", max_length=40)
    speed: float = Field(default=1.0, ge=0.7, le=1.3)
    reference: str = Field(default="", max_length=160)


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


def create_app(data_dir: Path | None = None) -> FastAPI:
    config = ConfigStore(data_dir)
    storage = Storage(config.data_dir / "alice.db")
    runs = RunManager(storage, config)
    download_jobs: dict[str, dict[str, Any]] = {}
    download_tasks: set[asyncio.Task[None]] = set()
    session_token = secrets.token_urlsafe(32)
    web_dir = Path(__file__).resolve().parents[2] / "web"
    audio_dir = config.data_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        for task in download_tasks:
            task.cancel()
        if download_tasks:
            await asyncio.gather(*download_tasks, return_exceptions=True)
        await runs.shutdown()
        storage.close()

    app = FastAPI(
        title="Alice OS",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]
    )
    app.state.config = config
    app.state.storage = storage
    app.state.runs = runs
    app.state.download_jobs = download_jobs
    app.state.session_token = session_token

    def require_session(request: Request) -> None:
        supplied = request.cookies.get("alice_session") or request.headers.get("X-Alice-Token", "")
        if not supplied or not hmac.compare_digest(supplied, session_token):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Open Alice OS first")
        origin = request.headers.get("origin")
        if origin:
            parsed = urlparse(origin)
            if parsed.hostname not in {"127.0.0.1", "localhost"}:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Origin is not allowed")

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/", include_in_schema=False)
    async def index() -> Response:
        response = FileResponse(web_dir / "index.html")
        response.set_cookie(
            "alice_session",
            session_token,
            httponly=True,
            samesite="strict",
            secure=False,
            max_age=86400,
        )
        return response

    @app.get("/api/state", dependencies=[Depends(require_session)])
    async def state() -> dict[str, Any]:
        settings = config.get()
        return {
            "version": __version__,
            "active_provider_id": settings.active_provider_id,
            "providers": [provider.model_dump() for provider in settings.providers],
            "sessions": storage.list_sessions(),
            "runtimes": await runtime_status(),
            "voice": openvoice_status(),
            "privacy": {
                "api_bind": "loopback",
                "workspace_boundary": "selected directory",
                "write_policy": "approval required",
            },
        }

    @app.post("/api/providers", dependencies=[Depends(require_session)])
    async def save_provider(profile: ProviderProfile) -> dict[str, Any]:
        _validate_provider_url(profile)
        settings = config.upsert_provider(profile)
        return {"providers": [item.model_dump() for item in settings.providers]}

    @app.delete("/api/providers/{provider_id}", dependencies=[Depends(require_session)])
    async def remove_provider(provider_id: str) -> dict[str, Any]:
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

    @app.get("/api/providers/{provider_id}/models", dependencies=[Depends(require_session)])
    async def provider_models(provider_id: str) -> dict[str, list[str]]:
        try:
            profile = config.get_provider(provider_id)
            models = await list_models(profile)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        except ProviderError as error:
            raise HTTPException(502, str(error)) from error
        return {"models": models}

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
            storage.delete_session(session_id)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/api/runs", dependencies=[Depends(require_session)])
    async def create_run(body: RunCreate) -> dict[str, str]:
        try:
            config.get_provider(body.provider_id)
            run = runs.start(
                session_id=body.session_id,
                user_message=body.message,
                provider_id=body.provider_id,
                model=body.model,
                agent_mode=body.agent_mode,
            )
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        return {"run_id": run.id}

    @app.get("/api/runs/{run_id}/events", dependencies=[Depends(require_session)])
    async def run_events(run_id: str, after: int = 0) -> StreamingResponse:
        try:
            run = runs.get(run_id)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error

        async def event_stream() -> AsyncIterator[str]:
            async for event in run.stream(after):
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
        return await runtime_status()

    @app.get("/api/models/library", dependencies=[Depends(require_session)])
    async def model_library() -> dict[str, Any]:
        return await local_model_library(config.data_dir)

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

    @app.post("/api/gguf/import", dependencies=[Depends(require_session)])
    async def import_local_gguf(body: GGUFImport) -> dict[str, Any]:
        try:
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
            details = await inspect_huggingface_repository(repository, revision)
        except RuntimeOperationError as error:
            raise HTTPException(400, str(error)) from error
        return {**details, "files": details["gguf_files"]}

    @app.post("/api/huggingface/inspect", dependencies=[Depends(require_session)])
    async def inspect_huggingface_model(body: HuggingFaceInspect) -> dict[str, Any]:
        try:
            details = await inspect_huggingface_repository(
                body.repository, body.revision, body.token
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
        }
        download_jobs[job_id] = job

        async def run_download() -> None:
            job.update(status="downloading", message="Downloading model files from Hugging Face…")
            try:
                result = await download_huggingface_repository(
                    data_dir=config.data_dir,
                    repository=body.repository,
                    revision=body.revision,
                    token=body.token,
                )
            except RuntimeOperationError as error:
                job.update(status="failed", message=str(error))
            except Exception:
                job.update(
                    status="failed", message="The local download worker stopped unexpectedly."
                )
            else:
                job.update(status="complete", message="Model files saved locally.", result=result)

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
                token=body.token,
            )
        except RuntimeOperationError as error:
            raise HTTPException(400, str(error)) from error

    @app.get("/api/voice/status", dependencies=[Depends(require_session)])
    async def voice_status() -> dict[str, Any]:
        return openvoice_status()

    @app.post("/api/voice/synthesize", dependencies=[Depends(require_session)])
    async def voice_synthesize(body: VoiceSynthesis) -> dict[str, str]:
        try:
            return await synthesize_openvoice(
                data_dir=config.data_dir,
                text=body.text,
                speaker=body.speaker,
                speed=body.speed,
                reference=body.reference,
            )
        except VoiceError as error:
            raise HTTPException(503, str(error)) from error

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

    app.mount("/audio", StaticFiles(directory=audio_dir), name="audio")
    app.mount("/static", StaticFiles(directory=web_dir), name="static")
    return app
