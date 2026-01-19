from endpoints import grading, templates
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="PCL Earthworks API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(grading.router, prefix="/api", tags=["grading"])
app.include_router(templates.router, prefix="/api", tags=["templates"])

@app.get("/")
def root():
    return {"message": "PCL Earthworks API"}

@app.get("/health")
def health():
    return {"status": "healthy"}