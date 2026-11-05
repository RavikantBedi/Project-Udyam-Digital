from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.db import init_db
from app.api import routes, advisor, kyc, office, auth

app = FastAPI(
    title="Accel Business – Udyam Digital",
    version="1.0.0",
    description="API for the Udyam Digital SMB onboarding platform with Auth and Omnichannel Notifications",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()
    try:
        from app.scripts.seed import seed
        seed()
    except Exception as e:
        print(f"[startup] Seed error: {e}")


app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(routes.router, prefix="/api")
app.include_router(advisor.router, prefix="/api/advisor", tags=["advisor"])
app.include_router(kyc.router, prefix="/api", tags=["kyc"])
app.include_router(office.router, prefix="/api/office", tags=["office"])


@app.get("/")
def root():
    return {"message": "Accel Business API – Udyam Digital", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
