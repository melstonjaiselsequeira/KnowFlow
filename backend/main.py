
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import engine, Base
from app import models

app = FastAPI(title="KnowFlow API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
Base.metadata.create_all(bind=engine)


@app.get("/")
def home():
    return {"message": "KnowFlow Backend is running!"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/db-test")
def test_database():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {"database": "connected"}


@app.get("/tables")
def list_tables():
    from sqlalchemy import inspect

    inspector = inspect(engine)
    return {"tables": inspector.get_table_names()}

from app.api.documents import router as documents_router
app.include_router(documents_router)

from app.api.extraction import router as extraction_router
app.include_router(extraction_router)

from app.api.search import router as search_router
app.include_router(search_router)

from app.api.verification import router as verification_router
app.include_router(verification_router)

from app.api.review import router as review_router
app.include_router(review_router)


from app.api.handovers import router as handovers_router
app.include_router(handovers_router)