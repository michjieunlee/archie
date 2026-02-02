from fastapi import FastAPI
from app.config import get_settings
from app.api.routes import slack, github, knowledge

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Slack Chat to Living Knowledge Base Agent",
    version="0.1.0",
)

# Include routers
app.include_router(slack.router, prefix="/api/slack", tags=["Slack"])
app.include_router(github.router, prefix="/api/github", tags=["GitHub"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["Knowledge"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.app_name}
