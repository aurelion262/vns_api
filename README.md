# vns_api

> **Vietnamese Stock Market Data API** — A lightweight FastAPI server that wraps the `vnstock_data` (paid) library and exposes real-time stock market data as a REST API.

## Overview

`vns_api` acts as the **data layer** of the st0nks ecosystem. It communicates directly with the `vnstock_data` library (Vnstock sponsored/paid version) to fetch live market quotes from Vietnamese exchanges (HOSE, HNX, UPCOM) and serves them to downstream services via HTTP.

```
st0nks_web  →  st0nks_bot  →  vns_api  →  vnstock_data (HOSE/HNX/UPCOM)
```

## Prerequisites

| Requirement | Version |
|---|---|
| Python | ≥ 3.9 |
| `vnstock_data` | Installed via Vnstock Installer (paid licence) |

> **Note:** `vnstock_data` is a **paid library** and must be installed separately using the official Vnstock Installer. It is **not** listed in `requirements.txt`. Contact [vnstock.site](https://vnstock.site) for access.

## Installation

```bash
# 1. Clone / navigate to the project
cd vns_api

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

# 3. Install public dependencies
pip install -r requirements.txt

# 4. Install vnstock_data via the official installer (requires a valid licence key)
# Follow instructions at https://vnstock.site
```

## Running the Server

```bash
# Development — auto-reload on file changes
python main.py

# Or explicitly via uvicorn
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

The server will start at **http://127.0.0.1:8000**.

## API Specification

### Base URL

```
http://127.0.0.1:8000
```

### `/api/v1/quotes` — Get Stock Quotes

Fetches real-time market quotes for one or more stock symbols.

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/api/v1/quotes` |

#### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `symbols` | `string` | ✅ | Comma-separated list of stock symbols (case-insensitive). Example: `TCB,VIC,HPG` |

#### Example Request

```bash
curl "http://127.0.0.1:8000/api/v1/quotes?symbols=TCB,VIC,HPG"
```

#### Example Response

```json
{
  "data": [
    {
      "symbol": "TCB",
      "reference_price": 24500,
      "ceiling_price": 26200,
      "floor_price": 22800,
      "close_price": 25100
    },
    ...
  ]
}
```

#### Error Responses

| Status | Description |
|---|---|
| `400` | No valid symbols provided |
| `500` | Library error or upstream data unavailable |

### Interactive Docs

FastAPI automatically generates interactive documentation:

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

## Project Structure

```
vns_api/
├── main.py           # FastAPI app & single endpoint definition
├── requirements.txt  # Public dependencies (fastapi, uvicorn, pandas)
├── docs/             # Additional documentation & notes
└── .venv/            # Virtual environment (not committed)
```

## Dependencies

```
fastapi
uvicorn
pandas
vnstock_data  (paid — manual install)
```

## Notes for Docker

When running inside Docker, change the host binding in `main.py`:

```python
uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
```
