from fastapi import FastAPI
from app.api.routes import router as api_router

app = FastAPI(
    title="AI Test Case Generator",
    version="1.0.0",
)

# Register routes
app.include_router(
    api_router,
    prefix="/api",
    tags=["Test Case Generation"],
)
