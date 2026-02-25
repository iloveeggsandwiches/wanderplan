from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from collections import defaultdict

from db.database import get_db, Trip, Expense, EXPENSE_CATEGORIES
from services.ollama_service import generate_structured

router = APIRouter()

CATEGORY_ICONS = {
    "accommodation": "🏨",
    "food": "🍜",
    "transport": "✈️",
    "activities": "🎭",
    "shopping": "🛍️",
    "other": "📦",
}

# ── Pydantic ───────────────────────────────────────────────────────────────────

class BudgetUpdate(BaseModel):
    budget_total: Optional[float] = None
    budget_currency: Optional[str] = None

class ExpenseCreate(BaseModel):
    category: str
    description: str
    amount: float
    currency: Optional[str] = None
    date: Optional[str] = None
    notes: Optional[str] = None

class ExpenseUpdate(BaseModel):
    category: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    date: Optional[str] = None
    notes: Optional[str] = None

class EstimateRequest(BaseModel):
    model: str = "llama3"
    travelers: int = 1
    duration_days: Optional[int] = None
    travel_style: str = "mid-range"   # budget | mid-range | luxury

# ── Helpers ────────────────────────────────────────────────────────────────────

def expense_to_dict(e: Expense) -> dict:
    return {
        "id": e.id, "trip_id": e.trip_id,
        "category": e.category, "description": e.description,
        "amount": e.amount, "currency": e.currency,
        "date": e.date, "notes": e.notes,
        "created_at": str(e.created_at),
        "icon": CATEGORY_ICONS.get(e.category, "📦"),
    }

def compute_summary(trip: Trip, expenses: list[Expense]) -> dict:
    currency = trip.budget_currency or "USD"
    by_category = defaultdict(float)
    for e in expenses:
        by_category[e.category] += e.amount
    total_spent = sum(by_category.values())
    estimates = trip.budget_estimates or {}

    categories = []
    for cat in EXPENSE_CATEGORIES:
        spent = by_category.get(cat, 0.0)
        estimated = estimates.get(cat, {}).get("amount", 0.0)
        categories.append({
            "category": cat,
            "icon": CATEGORY_ICONS[cat],
            "spent": spent,
            "estimated": estimated,
            "pct_of_budget": round(spent / trip.budget_total * 100, 1) if trip.budget_total else None,
            "pct_of_estimate": round(spent / estimated * 100, 1) if estimated else None,
        })

    return {
        "budget_total": trip.budget_total,
        "budget_currency": currency,
        "total_spent": round(total_spent, 2),
        "remaining": round((trip.budget_total or 0) - total_spent, 2) if trip.budget_total else None,
        "pct_used": round(total_spent / trip.budget_total * 100, 1) if trip.budget_total else None,
        "categories": categories,
        "estimates": estimates,
    }

# ── Budget settings ────────────────────────────────────────────────────────────

@router.get("/{trip_id}")
def get_budget(trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(404, "Trip not found")
    expenses = db.query(Expense).filter(Expense.trip_id == trip_id).order_by(Expense.created_at.desc()).all()
    return {
        "summary": compute_summary(trip, expenses),
        "expenses": [expense_to_dict(e) for e in expenses],
    }

@router.patch("/{trip_id}/settings")
def update_budget_settings(trip_id: int, data: BudgetUpdate, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(404, "Trip not found")
    if data.budget_total is not None:
        trip.budget_total = data.budget_total
    if data.budget_currency is not None:
        trip.budget_currency = data.budget_currency.upper()
    db.commit()
    expenses = db.query(Expense).filter(Expense.trip_id == trip_id).all()
    return compute_summary(trip, expenses)

# ── AI cost estimator ──────────────────────────────────────────────────────────

ESTIMATE_SCHEMA = {
    "type": "object",
    "properties": {
        "accommodation": {"type": "object", "properties": {"amount": {"type": "number"}, "notes": {"type": "string"}}, "required": ["amount", "notes"]},
        "food":          {"type": "object", "properties": {"amount": {"type": "number"}, "notes": {"type": "string"}}, "required": ["amount", "notes"]},
        "transport":     {"type": "object", "properties": {"amount": {"type": "number"}, "notes": {"type": "string"}}, "required": ["amount", "notes"]},
        "activities":    {"type": "object", "properties": {"amount": {"type": "number"}, "notes": {"type": "string"}}, "required": ["amount", "notes"]},
        "shopping":      {"type": "object", "properties": {"amount": {"type": "number"}, "notes": {"type": "string"}}, "required": ["amount", "notes"]},
        "other":         {"type": "object", "properties": {"amount": {"type": "number"}, "notes": {"type": "string"}}, "required": ["amount", "notes"]},
        "total":         {"type": "number"},
        "currency":      {"type": "string"},
        "summary":       {"type": "string"},
    },
    "required": ["accommodation", "food", "transport", "activities", "total", "currency", "summary"]
}

@router.post("/{trip_id}/estimate")
async def estimate_costs(trip_id: int, req: EstimateRequest, db: Session = Depends(get_db)):
    """Use Ollama to generate realistic per-category cost estimates for the trip."""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(404, "Trip not found")

    # Calculate duration from dates if not provided
    duration = req.duration_days
    if not duration and trip.start_date and trip.end_date:
        try:
            from datetime import date
            s = date.fromisoformat(trip.start_date)
            e = date.fromisoformat(trip.end_date)
            duration = max(1, (e - s).days)
        except Exception:
            pass
    duration = duration or 7

    prompt = f"""You are an expert travel budget estimator.

Estimate realistic travel costs for this trip in USD:
- Destination: {trip.destination}
- Duration: {duration} days
- Travelers: {req.travelers}
- Travel style: {req.travel_style}

Provide per-person total costs for the entire trip duration for each category.
Base your estimates on current real-world prices for {trip.destination}.
Be specific and realistic — not overly conservative or inflated.

Return a JSON object with cost estimates and brief notes for each category."""

    try:
        result = await generate_structured(prompt, model=req.model, schema=ESTIMATE_SCHEMA)
    except Exception as e:
        raise HTTPException(502, f"Ollama error: {str(e)}")

    estimates = result.get("result", {})
    if isinstance(estimates, str):
        raise HTTPException(422, "Could not parse estimates from Ollama response")

    # Save estimates to trip
    trip.budget_estimates = estimates
    if not trip.budget_currency:
        trip.budget_currency = estimates.get("currency", "USD")
    # Auto-set budget_total if not set yet
    if not trip.budget_total and estimates.get("total"):
        trip.budget_total = estimates["total"]
    db.commit()

    expenses = db.query(Expense).filter(Expense.trip_id == trip_id).all()
    return {
        "estimates": estimates,
        "summary": compute_summary(trip, expenses),
    }

# ── Expenses CRUD ──────────────────────────────────────────────────────────────

@router.post("/{trip_id}/expenses")
def add_expense(trip_id: int, data: ExpenseCreate, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(404, "Trip not found")
    if data.category not in EXPENSE_CATEGORIES:
        raise HTTPException(400, f"category must be one of: {EXPENSE_CATEGORIES}")
    expense = Expense(
        trip_id=trip_id,
        category=data.category,
        description=data.description,
        amount=data.amount,
        currency=data.currency or trip.budget_currency or "USD",
        date=data.date,
        notes=data.notes,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    # Return updated summary + new expense
    expenses = db.query(Expense).filter(Expense.trip_id == trip_id).all()
    return {"expense": expense_to_dict(expense), "summary": compute_summary(trip, expenses)}

@router.put("/{trip_id}/expenses/{expense_id}")
def update_expense(trip_id: int, expense_id: int, data: ExpenseUpdate, db: Session = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.id == expense_id, Expense.trip_id == trip_id).first()
    if not expense:
        raise HTTPException(404, "Expense not found")
    for field, value in data.dict(exclude_none=True).items():
        setattr(expense, field, value)
    db.commit()
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    expenses = db.query(Expense).filter(Expense.trip_id == trip_id).all()
    return {"expense": expense_to_dict(expense), "summary": compute_summary(trip, expenses)}

@router.delete("/{trip_id}/expenses/{expense_id}")
def delete_expense(trip_id: int, expense_id: int, db: Session = Depends(get_db)):
    expense = db.query(Expense).filter(Expense.id == expense_id, Expense.trip_id == trip_id).first()
    if not expense:
        raise HTTPException(404, "Expense not found")
    db.delete(expense)
    db.commit()
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    expenses = db.query(Expense).filter(Expense.trip_id == trip_id).all()
    return {"success": True, "summary": compute_summary(trip, expenses)}
