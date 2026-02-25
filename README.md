# 🌍 WanderPlan — Open Source AI Travel Planner

A fully free, open source alternative to MindTrip. Built with FastAPI + React, powered by Ollama (local LLMs) and OpenStreetMap data. Zero paid API keys required.

## ✨ Features

- **AI Trip Planner** — Chat with local LLMs (llama3, mistral, etc.) to plan trips
- **Trip Management** — Create, organize, and manage multiple trips
- **Itinerary Builder** — Day-by-day activity planning with time, type, and location
- **Interactive Map** — Explore destinations using free OpenStreetMap data
- **Place Discovery** — Find attractions, restaurants, and hotels near any destination
- **100% Local** — All AI runs locally via Ollama, no data sent to third parties

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python + FastAPI |
| Database | SQLite (zero setup) |
| AI | Ollama (local LLMs) |
| Maps | Leaflet.js + OpenStreetMap |
| Places | Overpass API (free OSM data) |
| Geocoding | Nominatim (free OSM geocoding) |
| Frontend | React + Vite + Zustand |

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.ai) installed

### 1. Install & Start Ollama
```bash
# Install Ollama from https://ollama.ai
ollama pull llama3       # Download a model (~4GB)
ollama serve             # Start Ollama server
```

### 2. Backend Setup
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
# → API running at http://localhost:8000
# → Swagger docs at http://localhost:8000/docs
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
# → App running at http://localhost:5173
```

### Docker (Alternative)
```bash
docker compose up --build
# → App at http://localhost:5173
# Note: Connect Ollama with --network=host on Linux
```

## 📂 Project Structure

```
wanderplan/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── requirements.txt
│   ├── db/
│   │   └── database.py         # SQLite models & session
│   ├── routers/
│   │   ├── chat.py             # AI chat with SSE streaming
│   │   ├── trips.py            # Trip CRUD
│   │   ├── places.py           # Place search & geocoding
│   │   └── itinerary.py        # Day/activity management
│   └── services/
│       ├── ollama_service.py   # Ollama LLM integration
│       └── places_service.py  # OpenStreetMap APIs
└── frontend/
    └── src/
        ├── pages/              # HomePage, ChatPage, TripsPage, ItineraryPage, ExplorePage
        ├── components/         # Sidebar
        ├── store/              # Zustand global state
        └── services/           # API client
```

## 🔧 Configuration

Change the Ollama model in `backend/services/ollama_service.py`:
```python
DEFAULT_MODEL = "llama3"   # or "mistral", "phi3", "gemma2", etc.
```

## 🆓 Free APIs Used

| API | Purpose | Limit |
|-----|---------|-------|
| [Nominatim](https://nominatim.openstreetmap.org) | Geocoding | 1 req/sec |
| [Overpass API](https://overpass-api.de) | Place search | Fair use |
| [OpenStreetMap](https://openstreetmap.org) | Map tiles | Free |
| [Ollama](https://ollama.ai) | Local AI | Unlimited |

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push and open a Pull Request

## 📄 License

MIT License — free to use, modify, and distribute.
