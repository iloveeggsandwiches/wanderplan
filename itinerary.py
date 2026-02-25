from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Any
from db.database import get_db, ItineraryDay, Trip

router = APIRouter()


class ActivityItem(BaseModel):
    time: Optional[str] = None
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    type: Optional[str] = "activity"  # activity | food | hotel | transport


class DayCreate(BaseModel):
    day_number: int
    date: Optional[str] = None
    activities: List[ActivityItem] = []


@router.get("/{trip_id}")
def get_itinerary(trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    days = db.query(ItineraryDay).filter(ItineraryDay.trip_id == trip_id).order_by(ItineraryDay.day_number).all()
    return [
        {"id": d.id, "day_number": d.day_number, "date": d.date, "activities": d.activities}
        for d in days
    ]


@router.post("/{trip_id}/days")
def add_day(trip_id: int, data: DayCreate, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    day = ItineraryDay(
        trip_id=trip_id,
        day_number=data.day_number,
        date=data.date,
        activities=[a.dict() for a in data.activities],
    )
    db.add(day)
    db.commit()
    db.refresh(day)
    return {"id": day.id, "day_number": day.day_number, "date": day.date, "activities": day.activities}


@router.put("/{trip_id}/days/{day_id}")
def update_day(trip_id: int, day_id: int, data: DayCreate, db: Session = Depends(get_db)):
    day = db.query(ItineraryDay).filter(ItineraryDay.id == day_id, ItineraryDay.trip_id == trip_id).first()
    if not day:
        raise HTTPException(status_code=404, detail="Day not found")
    day.day_number = data.day_number
    day.date = data.date
    day.activities = [a.dict() for a in data.activities]
    db.commit()
    return {"id": day.id, "day_number": day.day_number, "date": day.date, "activities": day.activities}


@router.delete("/{trip_id}/days/{day_id}")
def delete_day(trip_id: int, day_id: int, db: Session = Depends(get_db)):
    day = db.query(ItineraryDay).filter(ItineraryDay.id == day_id, ItineraryDay.trip_id == trip_id).first()
    if not day:
        raise HTTPException(status_code=404, detail="Day not found")
    db.delete(day)
    db.commit()
    return {"success": True}
