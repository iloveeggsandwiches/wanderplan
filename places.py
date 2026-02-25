from fastapi import APIRouter, Query
from services.places_service import get_destination_info, search_places, geocode_destination

router = APIRouter()


@router.get("/search")
async def search_destination(q: str = Query(..., description="Destination name")):
    return await get_destination_info(q)


@router.get("/geocode")
async def geocode(q: str = Query(...)):
    result = await geocode_destination(q)
    if not result:
        return {"error": "Not found"}
    return result


@router.get("/nearby")
async def nearby(
    lat: float = Query(...),
    lon: float = Query(...),
    category: str = Query("tourism"),
    radius: int = Query(5000),
):
    return await search_places(lat, lon, category, radius)
