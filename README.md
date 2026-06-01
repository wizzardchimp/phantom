# NovaFi Phantom — Cybersecurity Exercise Game

A cyber security exercise where players log into a portal as "hackers" and probe a fake financial company's stolen data. The dataset contains ~2000 emails, employee records, customer PII, payroll data, and 12 planted "secrets" for players to discover via a LLM-powered RAG interface.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Generate the dataset (2004 emails, 51 employees, 250 customers, 500 orders, 612 payroll records)
python3 generate.py

# Start the backend API + Terminal UI
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000/terminal** for the hacker terminal UI.
Open **http://localhost:8000/docs** for the API docs.

## Project Structure

```
phantom/
├── generate.py                       # Dataset generator entry point
├── requirements.txt
├── Dockerfile                        # Container deployment
├── Procfile                          # Heroku/Railway deployment
├── render.yaml                       # Render.com deployment
├── data/
│   ├── novafi.db                     # SQLite database
│   ├── novafi_dataset.json           # Full JSON export
│   └── secrets.json                  # Planted easter eggs
├── frontend/
│   └── index.html                    # Standalone hacker terminal UI
├── phantom_generator/
│   ├── models.py                     # Data classes
│   ├── people.py                     # Employee/customer generator
│   └── emails.py                     # Email thread templates (28 thread types)
└── backend/
    ├── main.py                       # FastAPI app + API endpoints
    ├── rag_engine.py                 # RAG query engine + SQL inference
    └── vector_store.py               # Vector embeddings + keyword search
```

## Deployment

### Option 1: Docker

```bash
docker build -t novafi-phantom .
docker run -p 8000:8000 novafi-phantom
```
Open http://localhost:8000/terminal

### Option 2: Render.com (easiest free hosting)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your repo
4. Render auto-detects `render.yaml` or:
   - Build: `pip install -r requirements.txt && python3 generate.py`
   - Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Deploy

### Option 3: Railway / Heroku

```bash
# Railway: connect repo, it auto-detects the Procfile
# Heroku:
heroku create novafi-phantom
heroku buildpacks:set heroku/python
git push heroku main
```

### Option 4: Any VPS

```bash
pip install -r requirements.txt
python3 generate.py
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /terminal` | Hacker terminal web UI |
| `GET /stats` | Dataset statistics |
| `POST /query` | **Main RAG endpoint** — ask questions in natural language |
| `POST /sql` | Run raw SQL against the database |
| `GET /schema` | Database table schema |
| `GET /secrets` | List all planted secrets |
| `GET /emails` | Paginated email browser |
| `GET /employees` | Employee directory |
| `GET /customers` | Customer list |
| `GET /orders` | Order records |

## Query Examples

```
> show me the highest salaries
> find emails about layoffs
> list all employees in engineering
> what customer data was breached?
> show confidential emails
> who is the CEO having an affair with?
> list all orders over $100k
> what's the total payroll cost?
> find plaintext passwords
```

## The LLM Interface

The core is a **RAG (Retrieval Augmented Generation)** pipeline:

1. **Query Classification** — detects intent (salary, security, layoffs, etc.)
2. **SQL Inference** — automatically generates SQL for structured data queries
3. **Email Search** — keyword search across all 2004 emails (with vector search support)
4. **Response Generation** — template-based (no API key needed) or LLM-powered

### LLM Mode (Optional)

```bash
export OPENAI_API_KEY="sk-..."
```

Then send queries with `"use_llm": true` to get GPT-4 generated responses using the retrieved context.

## Planted Secrets (12 total)

The dataset contains clues players can discover:

| # | Secret | Difficulty |
|---|---|---|
| 1 | CEO having affair with HR Director | Medium |
| 2 | "Project Phoenix" mass layoffs planned | Medium |
| 3 | Customer data breach cover-up | Easy |
| 4 | Vendor kickback scheme | Hard |
| 5 | Plaintext passwords in emails | Easy |
| 6 | CEO inflating metrics to investors | Medium |
| 7 | Offshoring plans (PH support, EU engineering) | Medium |
| 8 | Discrimination complaint against Engineering | Medium |
| 9 | CFO insider trading indicators | Hard |
| 10 | Inflated revenue recognition | Hard |
| 11 | SSN/credit cards accidentally emailed | Easy |
| 12 | Vendor data breach affecting 12K customers | Medium |

## Multi-Player Support

The backend is stateless — multiple players can query simultaneously. For a game master dashboard, add WebSocket support and session tracking.

## Game Concept

Players access a "stolen data dump" and use the LLM terminal to:
- **Find secrets** planted across emails and databases
- **Connect threads** between departments to uncover the full story
- **Rank on discoveries** (time to find all 12 secrets)
- **Roleplay** as a hacker uncovering corporate malfeasance
