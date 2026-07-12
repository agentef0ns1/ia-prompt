from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ia_local_prompt.config_loader import PACKAGE_ROOT
from ia_local_prompt.service import (
    GenerateOptions,
    create_session_zip,
    fetch_ollama_models,
    get_session_dir,
    get_ui_config,
    run_analyze,
    run_generate,
)

WEB_DIR = PACKAGE_ROOT / "web"

app = FastAPI(title="ia-prompt WebUI", version="0.1.0")


class AnalyzeRequest(BaseModel):
    objective: str = Field(..., min_length=3)


class GenerateRequest(BaseModel):
    objective: str = Field(..., min_length=3)
    agent: str = "cline"
    model: str | None = None
    skill: str | None = None
    skills: list[str] | None = None
    context_limit: int = 32768
    enhance_mode: str = "off"
    enhance_model: str | None = None
    enhance_api_base: str | None = None
    output_mode: str = "auto"
    profile: str | None = None


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    html_path = WEB_DIR / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/api/config")
def api_config() -> dict:
    return get_ui_config()


@app.get("/api/ollama/models")
def api_ollama_models(url: str) -> dict:
    try:
        return fetch_ollama_models(url)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/analyze")
def api_analyze(req: AnalyzeRequest) -> dict:
    return run_analyze(req.objective.strip())


@app.post("/api/generate")
def api_generate(req: GenerateRequest) -> dict:
    options = GenerateOptions(
        objective=req.objective.strip(),
        agent=req.agent,
        model=req.model or None,
        skill=req.skill or None,
        skills=req.skills or None,
        context_limit=req.context_limit,
        enhance_mode=req.enhance_mode,
        enhance_model=req.enhance_model or None,
        enhance_api_base=req.enhance_api_base or None,
        output_mode=req.output_mode,
        profile=req.profile or None,
    )
    result = run_generate(options)
    return {
        "mode": result.mode,
        "session_id": result.session_id,
        "files": result.files,
        "metadata": result.metadata,
        "warnings": result.warnings,
    }


@app.get("/api/download/{session_id}/zip")
def download_zip(session_id: str) -> Response:
    data = create_session_zip(session_id)
    if data is None:
        raise HTTPException(404, "Sesión no encontrada")
    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="ia-prompt-{session_id}.zip"',
        },
    )


@app.get("/api/download/{session_id}/{filename}")
def download_file(session_id: str, filename: str) -> FileResponse:
    session_dir = get_session_dir(session_id)
    if not session_dir:
        raise HTTPException(404, "Sesión no encontrada")

    for path in session_dir.rglob(filename):
        if path.is_file() and path.name == filename:
            return FileResponse(
                path,
                media_type="text/markdown",
                filename=filename,
            )
    raise HTTPException(404, "Archivo no encontrado")


if WEB_DIR.joinpath("static").exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")


def main() -> None:
    import uvicorn
    uvicorn.run(
        "ia_local_prompt.webapp:app",
        host="0.0.0.0",
        port=8765,
        reload=False,
    )


if __name__ == "__main__":
    main()
