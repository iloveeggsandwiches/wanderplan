from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat, trips, places, itinerary
from db.database import init_db

app = FastAPI(title="WanderPlan API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()

app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(trips.router, prefix="/api/trips", tags=["trips"])
app.include_router(places.router, prefix="/api/places", tags=["places"])
app.include_router(itinerary.router, prefix="/api/itinerary", tags=["itinerary"])

@app.get("/api/health")
async def health():
    return {"status": "ok", "message": "WanderPlan API is running"}
