import httpx
from typing import List, Dict, Optional

NOMINATIM_URL = "https://nominatim.openstreetmap.org"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OPENTRIPMAP_URL = "https://api.opentripmap.com/0.1/en"

HEADERS = {"User-Agent": "WanderPlan/1.0 (open-source travel planner)"}


async def geocode_destination(query: str) -> Optional[Dict]:
    """Convert place name to coordinates using Nominatim (free OSM)."""
    params = {"q": query, "format": "json", "limit": 1, "addressdetails": 1}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{NOMINATIM_URL}/search", params=params, headers=HEADERS)
        results = resp.json()
        if results:
            r = results[0]
            return {
                "name": r.get("display_name", query),
                "lat": float(r["lat"]),
                "lon": float(r["lon"]),
                "country": r.get("address", {}).get("country", ""),
                "city": r.get("address", {}).get("city") or r.get("address", {}).get("town", ""),
            }
    return None


async def search_places(lat: float, lon: float, category: str = "tourism", radius: int = 5000) -> List[Dict]:
    """Search for places near coordinates using Overpass API (free OSM data)."""
    tag_map = {
        "tourism": '["tourism"~"attraction|museum|artwork|viewpoint|gallery|theme_park|zoo"]',
        "food": '["amenity"~"restaurant|cafe|bar|fast_food|food_court"]',
        "hotel": '["tourism"~"hotel|hostel|guest_house|motel|apartment"]',
        "nature": '["natural"~"peak|beach|lake|waterfall|spring"]["leisure"~"park|nature_reserve"]',
        "shopping": '["shop"~"mall|market|supermarket|clothes|boutique"]',
    }
    tag_filter = tag_map.get(category, '["tourism"]')
    query = f"""
    [out:json][timeout:25];
    (
      node{tag_filter}(around:{radius},{lat},{lon});
      way{tag_filter}(around:{radius},{lat},{lon});
    );
    out center 20;
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(OVERPASS_URL, data=query)
        data = resp.json()
        places = []
        for el in data.get("elements", [])[:20]:
            tags = el.get("tags", {})
            name = tags.get("name")
            if not name:
                continue
            place_lat = el.get("lat") or el.get("center", {}).get("lat")
            place_lon = el.get("lon") or el.get("center", {}).get("lon")
            places.append({
                "id": str(el.get("id")),
                "name": name,
                "lat": place_lat,
                "lon": place_lon,
                "category": category,
                "description": tags.get("description", ""),
                "website": tags.get("website", ""),
                "opening_hours": tags.get("opening_hours", ""),
                "cuisine": tags.get("cuisine", ""),
                "stars": tags.get("stars", ""),
                "wikipedia": tags.get("wikipedia", ""),
            })
        return places


async def get_destination_info(destination: str) -> Dict:
    """Get full destination info: coordinates + nearby attractions."""
    geo = await geocode_destination(destination)
    if not geo:
        return {"error": f"Could not find destination: {destination}"}

    lat, lon = geo["lat"], geo["lon"]

    tourism = await search_places(lat, lon, "tourism")
    food = await search_places(lat, lon, "food")
    hotels = await search_places(lat, lon, "hotel")

    return {
        "destination": geo,
        "attractions": tourism[:10],
        "restaurants": food[:10],
        "hotels": hotels[:8],
    }
