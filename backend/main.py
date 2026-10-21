from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import client, users_collection
from routes import auth, sessions, learning
from ml.predictor import KnowledgeTracerPredictor


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Check MongoDB connection
    await client.admin.command("ping")

    # Ensure email addresses are unique
    await users_collection.create_index("email", unique=True)

    # Load the trained LSTM knowledge-tracing model
    checkpoint_path = (
        Path(__file__).resolve().parent
        / "saved_models"
        / "lstm_knowledge_tracer.pt"
    )

    app.state.predictor = KnowledgeTracerPredictor(
        checkpoint_path
    )

    print("MongoDB connected successfully.")
    print("LSTM knowledge-tracing model loaded successfully.")

    yield

    # Close MongoDB connection on shutdown
    client.close()
    print("MongoDB connection closed.")


# Initialize FastAPI
app = FastAPI(
    title="Personalized Learning API",
    description="Backend for the AI Personalized Learning Platform",
    version="0.1.0",
    lifespan=lifespan,
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register API routers
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(learning.router)


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Personalized Learning API is running"
    }


# General health check
@app.get("/health")
async def health():
    return {
        "status": "ok"
    }


# LSTM model health check
@app.get("/health/model")
async def model_health():
    predictor = getattr(app.state, "predictor", None)

    return {
        "model_loaded": predictor is not None
    }
