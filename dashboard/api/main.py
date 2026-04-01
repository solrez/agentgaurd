"""AgentGuard Dashboard — FastAPI application."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from dashboard.api.deps import DashboardState
from dashboard.api.routes import analytics, audit, config, escalation


def create_app(
    config_path: str = "agentguard.yaml",
    audit_path: str = "agentguard_audit.jsonl",
) -> FastAPI:
    app = FastAPI(
        title="AgentGuard Dashboard",
        description="Management dashboard for AgentGuard — real-time agent verification.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.dashboard = DashboardState(
        audit_path=audit_path,
        config_path=config_path,
    )

    app.include_router(audit.router)
    app.include_router(analytics.router)
    app.include_router(config.router)
    app.include_router(escalation.router)

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    # Serve built frontend if it exists
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists() and (static_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")

    return app
