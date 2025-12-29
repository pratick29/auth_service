from fastapi import FastAPI
from app.db.session import engine
from app.db.base import Base
from app.models import user
from app.routes.auth import router as auth_router

app = FastAPI(title="Auth Service")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


app.include_router(auth_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
