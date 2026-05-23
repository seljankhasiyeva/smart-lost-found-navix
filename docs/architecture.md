# Architecture — team-NaviX

## Overview

This project follows **Onion Architecture** (also known as Clean Architecture).  
The core rule is simple: **dependencies point inward only** — outer layers know about
inner layers, never the reverse.

```
                    ┌─────────────────────────────────────┐
                    │        Infrastructure Layer         │
                    │  api.py · cli.py                    │
                    │  storage/repository.py              │
                    │  ai/ (PROVIDED)                     │
                    │                                     │
                    │   ┌─────────────────────────────┐   │
                    │   │     Application Layer       │   │
                    │   │  services/ai_service.py     │   │
                    │   │  concurrency/pipeline.py    │   │
                    │   │                             │   │
                    │   │   ┌──────────────────────┐  │   │
                    │   │   │    Domain Core       │  │   │
                    │   │   │  models.py           │  │   │
                    │   │   │  core/               │  │   │
                    │   │   │  config.py           │  │   │
                    │   │   └──────────────────────┘  │   │
                    │   └─────────────────────────────┘   │
                    └─────────────────────────────────────┘

    Dependency direction:  Infrastructure → Application → Domain
                           (never reversed)
```

---

## Layer Breakdown

### 1. Domain Core — `src/models.py`, `src/core/`, `src/config.py`

The innermost layer. No imports from any other layer in this project.

| File | Role |
|------|------|
| `src/models.py` | `ItemCreate`, `ItemRecord`, `MatchResult` — Pydantic schemas |
| `src/core/__init__.py` | Business rules — similarity thresholds, domain constants |
| `src/core/interfaces.py` | `ItemRepositoryABC` — abstract contract for storage |
| `src/core/exceptions.py` | Domain-level exceptions (`ItemNotFound`, `StorageError`) |
| `src/config.py` | `pydantic-settings` typed env vars, singleton `settings` object |
| `src/core/validation.py` | `validate_image`, `validate_status`, `validate_item_id` |

**Rule:** Nothing in `src/core/` or `src/models.py` imports from `services/`,
`concurrency/`, `storage/`, `api.py`, or `ai/`.

---

### 2. Application Layer — `src/services/`, `src/concurrency/`

Orchestrates use-cases. Wraps external dependencies behind interfaces.
No HTTP, no DB drivers here.

| File | Role |
|------|------|
| `src/services/ai_service.py` | Wraps `ai.vlm` + `ai.embedding` with semaphore, logging, cache |
| `src/services/retry.py` | Tenacity decorator, exponential backoff, `setup_logging()` |
| `src/concurrency/pipeline.py` | `register_item()`, `register_batch()`, `find_matches()` — async orchestration via `asyncio.gather` |
| `src/services/cost_telemetry.py` | token counts + $ per call (bonus) |
| `src/services/failover.py` | multi-provider failover (bonus) |
| `src/services/rate_limiter.py` | token-aware rate limiter (bonus) |
| `src/services/streaming.py` | streaming responses (bonus) |
| `src/services/telemetry.py` | OpenTelemetry spans (bonus) |

**Rule:** `services/` and `concurrency/` import from `core/` and call `ai/` only
through `ai_service.py`. They never import `asyncpg`, `fastapi`, or `click` directly.  
`pipeline.py` calls `storage/repository.py` through the `ItemRepositoryABC` interface —
never bypasses the contract.

---

### 3. Infrastructure Layer — `src/api.py`, `src/cli.py`, `src/storage/`

The outermost layer. Talks to the outside world: HTTP, database, filesystem, external AI APIs.

| File | Role |
|------|------|
| `src/api.py` | FastAPI app — `POST /items/lost`, `POST /items/found`, `GET /items/{id}/matches` |
| `src/cli.py` | Click CLI — `register-lost`, `register-found`, `search-matches`, `list` |
| `src/storage/repository.py` | `ItemRepository` implements `ItemRepositoryABC` — asyncpg CRUD, `save_image()`, `create_pool()` |
| `ai/` (PROVIDED) | `vlm.py`, `embedding.py`, `similarity.py` — never modified |

**Rule:** `api.py` and `cli.py` read `config.py` and inject the concrete
`ItemRepository` into `pipeline.py`. They never call `repository.py` directly for
business operations — all logic goes through `concurrency/pipeline.py`.

---

## Dependency Flow

```
api.py / cli.py  (reads config.py, injects repository)
       │
       ▼
concurrency/pipeline.py
       ├──▶ services/ai_service.py ──▶ ai/ (vlm, embedding, similarity)
       └──▶ core/interfaces.py (ItemRepositoryABC)
                   ▲
                   │ implements
       storage/repository.py ──▶ PostgreSQL + pgvector

All layers ──▶ models.py, core/, config.py
```

---

## Module Boundaries

| From \ To | `core/` | `services/` | `concurrency/` | `storage/` | `api` / `cli` | `ai/` |
|-----------|:-------:|:-----------:|:--------------:|:----------:|:-------------:|:-----:|
| `core/` | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| `services/` | ✓ | ✓ | ✗ | ✗ | ✗ | via `ai_service` only |
| `concurrency/` | ✓ | ✓ | ✓ | via interface | ✗ | ✗ |
| `storage/` | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| `api` / `cli` | ✓ | ✓ | ✓ | ✗ | — | ✗ |

---

## Complete Folder Structure
```
team-NaviX/
├── README.md
├── requirements.txt
├── requirements-ai.txt
├── Dockerfile
├── docker-compose.yml
├── pytest.ini
├── mypy_output.txt
├── .env.example
├── .gitignore
│
├── .github/
│   ├── pull_request_template.md
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI (bonus)
│
├── ai/                          # PROVIDED — do not modify
│   ├── __init__.py
│   ├── vlm.py                   # describe_item(image_path, user_text)
│   ├── embedding.py             # embed(text) → unit vector
│   ├── similarity.py            # cosine(), top_k()
│   ├── schemas.py               # ItemDescription pydantic schema
│   └── providers/
│       ├── __init__.py
│       ├── anthropic.py
│       ├── base.py
│       ├── factory.py
│       ├── google.py
│       └── openai.py
│
├── src/
│   ├── __init__.py
│   ├── config.py                # DOMAIN — typed env settings, singleton
│   ├── models.py                # DOMAIN — ItemCreate, ItemRecord, MatchResult
│   ├── api.py                   # INFRASTRUCTURE — FastAPI entry point
│   ├── cli.py                   # INFRASTRUCTURE — Click entry point
│   │
│   ├── core/                    # DOMAIN — business rules & contracts
│   │   ├── __init__.py
│   │   ├── interfaces.py        # ItemRepositoryABC abstract contract
│   │   ├── exceptions.py        # ItemNotFound, StorageError, etc.
│   │   └── validation.py        # validate_image, validate_status, validate_item_id
│   │
│   ├── services/                # APPLICATION — wrappers around ai/, retries, logging
│   │   ├── __init__.py
│   │   ├── ai_service.py        # ai/ wrapper — semaphore, logging, cache
│   │   ├── retry.py             # Tenacity backoff, setup_logging()
│   │   ├── cost_telemetry.py    # token counts + $ per call (bonus)
│   │   ├── failover.py          # multi-provider failover (bonus)
│   │   ├── rate_limiter.py      # token-aware rate limiter (bonus)
│   │   ├── streaming.py         # streaming responses (bonus)
│   │   └── telemetry.py         # OpenTelemetry spans (bonus)
│   │
│   ├── concurrency/             # APPLICATION — async orchestration
│   │   ├── __init__.py
│   │   └── pipeline.py          # register_item(), register_batch(), find_matches()
│   │
│   └── storage/                 # INFRASTRUCTURE — persistence
│       ├── __init__.py
│       └── repository.py        # ItemRepository — asyncpg, save_image(), create_pool()
│
├── tests/
│   ├── conftest.py              # mock_pool, mock_ai, event_loop fixtures
│   ├── test_ai_smoke.py         # PROVIDED — never delete or weaken
│   ├── test_services.py         # embed cache hit/miss, describe_item logging
│   ├── test_core.py             # business rule unit tests
│   ├── test_concurrency.py      # gather succeeds, one-task-raises, benchmark
│   ├── test_storage.py          # CRUD happy path, mock DB
│   ├── test_robustness.py       # bad MIME, oversized, unknown item ID
│   ├── test_retry.py            # retry on ConnectionError, 3-attempt limit
│   ├── test_end_to_end.py       # register → match happy path (mocked AI)
│   ├── test_failover.py         # multi-provider failover (bonus)
│   ├── test_rate_limiter.py     # token-aware rate limiter (bonus)
│   └── test_bonus_modules.py    # bonus module tests
│
├── scripts/
│   ├── demo.py                  # registers all data/ items, prints top-3 matches — GRADED
│   └── benchmark.py             # sequential vs concurrent wall-clock comparison
│
├── data/
│   ├── lost/                    # sample lost item images
│   └── found/                   # sample found item images
│
├── artefacts/                   # output of demo runs — required in submission
│   ├── matches.json
│   ├── register_found.json
│   └── register_lost.json
│
├── ui/                          # Streamlit Web UI (bonus)
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── docs/
│   ├── architecture.md          # this file
│   └── schema.sql               # items table DDL
│
└── report/
    ├── Report.pdf
    └── Slide.pdf
```