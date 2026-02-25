from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from db.database import get_db, Trip, ItineraryDay
from services.places_service import geocode_destination
from datetime import datetime

router = APIRouter()


class TripCreate(BaseModel):
    title: str
    destination: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class TripUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


def trip_to_dict(trip: Trip) -> dict:
    return {
        "id": trip.id,
        "title": trip.title,
        "destination": trip.destination,
        "start_date": trip.start_date,
        "end_date": trip.end_date,
        "description": trip.description,
        "lat": trip.lat,
        "lon": trip.lon,
        "created_at": str(trip.created_at),
    }


@router.post("/")
async def create_trip(data: TripCreate, db: Session = Depends(get_db)):
    geo = await geocode_destination(data.destination)
    trip = Trip(
        title=data.title,
        destination=data.destination,
        start_date=data.start_date,
        end_date=data.end_date,
        description=data.description,
        lat=geo["lat"] if geo else None,
        lon=geo["lon"] if geo else None,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip_to_dict(trip)


@router.get("/")
def list_trips(db: Session = Depends(get_db)):
    trips = db.query(Trip).order_by(Trip.created_at.desc()).all()
    return [trip_to_dict(t) for t in trips]


@router.get("/{trip_id}")
def get_trip(trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip_to_dict(trip)


@router.put("/{trip_id}")
def update_trip(trip_id: int, data: TripUpdate, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    for field, value in data.dict(exclude_none=True).items():
        setattr(trip, field, value)
    db.commit()
    db.refresh(trip)
    return trip_to_dict(trip)


@router.delete("/{trip_id}")
def delete_trip(trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    db.delete(trip)
    db.commit()
    return {"success": True}
