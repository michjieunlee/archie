from fastapi import FastAPI
from app.config import get_settings
from app.api.routes import kb, slack, github

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Slack Chat to Living Knowledge Base Agent",
    version="0.1.0",
)

# Include routers
app.include_router(kb.router, prefix="/api/kb", tags=["KB Management"])
app.include_router(slack.router, prefix="/api/slack", tags=["Slack"])
app.include_router(github.router, prefix="/api/github", tags=["GitHub"])


@app.get("/")
async def root():
    return {
        "message": "Welcome to Archie - Slack Chat to Living Knowledge Base Agent",
        "version": "0.1.0",
        "endpoints": {
            "kb": "/api/kb",
            "slack": "/api/slack",
            "github": "/api/github",
            "health": "/health",
            "docs": "/docs",
            "redoc": "/redoc",
        },
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.app_name}
