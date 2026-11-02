from fastapi import FastAPI

from app.api.routes import router


app = FastAPI(
    title="DISC–Travel Preference Survey Onboarding",
    description="Offline prompt + DISC Travel Quiz prototype for cold-start PTS preference initialization.",
    version="0.2.0",
)
app.include_router(router)
