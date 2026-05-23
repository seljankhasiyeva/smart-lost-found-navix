# Smart Lost & Found — team-NaviX

AI-powered system that matches lost and found items using vision-language models and embedding-based similarity search.

---

## How It Works

1. User registers a lost or found item with an image and description
2. The system runs VLM (GPT-4o-mini) to extract a structured description
3. An embedding is generated and stored in PostgreSQL
4. When searching, the system computes cosine similarity across the opposite pool and returns top-k matches

---

## Setup

### Prerequisites
- Docker & Docker Compose
- OpenAI API key

### 1. Clone the repository
```bash
git clone https://github.com/seljankhasiyeva/smart-lost-found-navix.git
cd smart-lost-found-navix
```

### 2. Configure environment
```bash
cp .env.example .env
```

Edit `.env` and fill in your values:
```
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://postgres:dev@localhost:5432/lostfound
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
IMAGE_STORE_DIR=image_store
MAX_IMAGE_SIZE_MB=5
AI_CONCURRENCY_LIMIT=5
LOG_LEVEL=INFO
API_URL=http://localhost:8000
```

### 3. Build and run
```bash
docker compose up --build
```

This starts:
- **PostgreSQL** on port `5432`
- **FastAPI** on port `8000`

---

## Running the Demo

```bash
docker compose exec api python scripts/demo.py
```

Registers all items in `data/lost/` and `data/found/`, then prints top-3 matches with similarity scores.

---

## HTTP API

### Register a lost item
```bash
curl -X POST http://localhost:8000/items/lost \
  -F "image=@data/lost/backpack_navy.png" \
  -F "text=Navy blue backpack, Nike logo"
```

### Register a found item
```bash
curl -X POST http://localhost:8000/items/found \
  -F "image=@data/found/backpack_navy_2.png" \
  -F "text=Dark blue backpack found near the library"
```

### Get matches
```bash
curl "http://localhost:8000/items/{item_id}/matches?k=3"
```

### List all items
```bash
curl "http://localhost:8000/items?status=lost"
```

---

## CLI

```bash
# Register a lost item
python -m src.cli register-lost data/lost/backpack_navy.png --text "Navy blue backpack"

# Register a found item
python -m src.cli register-found data/found/backpack_navy_2.png --text "Dark blue backpack"

# Find matches
python -m src.cli search-matches <item_id> --k 3

# List all items
python -m src.cli list-items --status lost
```

---

## Web UI (Bonus)

```bash
pip install gradio
python ui/app.py
```

Open `http://localhost:7860`

---

## Testing

```bash
# Run all tests (offline — no live network required)
pytest tests/ -v

# With coverage report
pytest tests/ --cov=src --cov-report=term-missing
```

All tests run offline. AI module and database are mocked via `conftest.py` fixtures.

---

## Benchmark

Sequential vs concurrent registration of 5 items:

```
Benchmark: 5 items
------------------------------------------
Sequential:   0.01s
Concurrent:   0.01s
Speedup:      0.9x
------------------------------------------
```

To reproduce:
```bash
python scripts/benchmark.py
```

---

## Project Structure

```
team-NaviX/
├── ai/              # PROVIDED — do not modify
├── src/
│   ├── core/        # Domain — models, interfaces, exceptions, validation
│   ├── services/    # Application — AI wrapper, retry, logging
│   ├── concurrency/ # Application — async pipeline
│   ├── storage/     # Infrastructure — PostgreSQL repository
│   ├── api.py       # FastAPI HTTP server
│   └── cli.py       # Click CLI
├── tests/           # Offline pytest suite
├── scripts/         # demo.py and benchmark.py
├── ui/              # Gradio web UI (bonus)
└── docs/
    └── architecture.md
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | OpenAI API key (required) |
| `DATABASE_URL` | `postgresql://postgres:dev@localhost:5432/lostfound` | PostgreSQL connection URL |
| `LLM_PROVIDER` | `openai` | AI provider |
| `LLM_MODEL` | `gpt-4o-mini` | Vision-language model |
| `EMBEDDING_PROVIDER` | `openai` | Embedding provider |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `IMAGE_STORE_DIR` | `image_store` | Directory for image blobs |
| `MAX_IMAGE_SIZE_MB` | `5` | Maximum image upload size |
| `AI_CONCURRENCY_LIMIT` | `5` | Max concurrent AI requests |
| `LOG_LEVEL` | `INFO` | Logging level |
| `API_URL` | `http://localhost:8000` | API URL for Web UI |

---

## Academic Integrity

AI coding assistants (Claude, ChatGPT, Gemini) were used as collaborators during development.
All code is understood and defensible by the team. See `report/report.pdf` for details.
