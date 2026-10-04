# Campus Customs

A storefront website for **Campus Customs**, a family-run Yale apparel shop in New Haven, with an AI shopping assistant.

- **Front end:** React + Vite + TypeScript (`frontend/`)
- **Back end:** Python FastAPI (`backend/`)
- **Chatbot:** a PydanticAI agent using an OpenAI 5.6/6 series model through Portkey (`backend/agent.py`, `tools.py`, `models.py`, `prompts/prompt.md`)

Shoppers can browse and filter 102 products, see stock by size, create an account and log in. They can also chat with an assistant that searches the real catalogue, quotes exact prices and stock, suggests in-stock alternatives, and remembers signed-in customers.

## Folder layout

```
hw4/
  README.md            this file
  AI_prompts.md        the prompts used to build each problem
  requirements.txt     Python packages (back end, agent, tests)
  .env.example         settings template: copy to .env
  backend/             FastAPI app + PydanticAI agent
    main.py  agent.py  models.py  tools.py  prompts/prompt.md
    auth.py  history.py  audit.py  db.py
  frontend/            React + Vite + TypeScript site
  output/              written docs and evidence
    harness.md  design.md  usability.md  app_check.html  app_check_images/  audit_trail.json
  tests/               check scripts (see output/harness.md → Testing)
  data/                the data pack goes here (NOT in the repo)
```

## 1. Add the data pack (not included in this repo)

The database and product images are not committed. Unzip the data pack so it sits **inside `hw4/`** like this:

```
hw4/
  data/
    campus_customs.db      SQLite: catalogue, inventory, users
    products/              102 product images (*.jpg)
```

The zip already contains a top-level `data/` folder, so extract it directly into `hw4/`. On first start the back end adds a `chat_history` table to the database for saved chats.

## 2. Settings (.env)

Copy `.env.example` to `.env` in `hw4/` and fill in:

| Variable | What it is |
|---|---|
| `PORTKEY_API_KEY` | Your Portkey API key |
| `MODEL_NAME` | An OpenAI 5.6 or 6 series model name from your Portkey account (e.g. `gpt-5.6-luna`) |
| `SESSION_SECRET` | Any long random string: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |

`.env` is git-ignored, so never commit it. Without it, the site still runs but the chat replies "isn't set up yet".

## 3. Run the back end (port 8000)

Requires Python 3.12+. From `hw4/`:

```powershell
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cd backend
uvicorn main:app --reload --port 8000
```

The API docs are at http://localhost:8000/docs.

## 4. Run the front end (port 5173)

Requires Node.js 20+. In a second terminal, from `hw4/`:

```powershell
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Vite forwards `/api`, `/chat` and `/images` to the back end on port 8000, so start both.

## 5. Try it
- **Products:** search, filter by category, sort by price, and open any item to see stock by size.
- **Create account / Log in:** the test account is `test@campuscustoms.yale.edu` / `password`.
- **Chat with us** (bottom-right): try "What hoodies do you have?", "Is the Baseball Left Chest Crewneck available in XL?", or, on a product page, "Is this in stock in medium?".

## 6. Tests

From `hw4/` with the venv active:

```powershell
python tests\check_chat_tools.py   # tools vs. database
python tests\check_memory.py       # chat history, identity, page context
python tests\check_usability.py    # filters, alternatives, low stock
python tests\check_audit.py        # audit trail, limits, redaction
python tests\app_check.py          # starts both servers, screenshots → output/app_check.html
```

## Documentation
- `output/harness.md`: how the whole system works (database, auth, architecture, models, tools, search, memory, safety, specs, audit trail, testing)
- `output/usability.md`: the four usability improvements
- `output/design.md`: the visual design and why
- `output/app_check.html`: the browser test report (open by double-clicking)
- `output/audit_trail.json`: the append-only log of agent activity
