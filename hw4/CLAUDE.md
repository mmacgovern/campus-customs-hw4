# HW4 Workspace Rules: Campus Customs

## Scope
- All HW4 work stays inside this `hw4` folder. Its parent folder becomes the GitHub repo.

## Project
Campus Customs is a campus merch store website with a chatbot.
- **Front end:** React + Vite + TypeScript in `frontend/`.
- **Back end:** Python FastAPI in `backend/`, with a PydanticAI agent as the chatbot.
- **Data:** `data/campus_customs.db` (SQLite tables: `catalogue`, `inventory`, `users`). Product images are in `data/products/`.
- **Written docs:** go in `output/`.

## Prompt log (`hw4/AI_prompts.md`)
- This file overrides the HW2 prompt-journal rule in the parent CLAUDE.md. Log HW4 prompts here, not in `hw2/`.
- The file has one section per problem (1–13), each with its number and title.
- When the user sends a prompt for a problem, copy their exact words into that section under **Prompt:** before doing the work.
- For a follow-up, add it under **Follow-up:** with one sentence on what was lacking after the first try.
- Never reword or invent prompts.

## Workflow
- Work on one problem at a time. Do not jump ahead to later problems.
- Keep explanations short.
- After each problem, tell the user how to test it.

## LLM and secrets
- The API key is `PORTKEY_API_KEY` in `.env`. Never print, log, or hard-code it. Load it from `.env` at run time.
- Use an OpenAI 5.6 or 6 series model through Portkey.
- Keep the model name in `.env` so the user can change it. Do not hard-code it.

## Git
Never commit any of these:
- `.env`
- the database (`data/campus_customs.db`)
- the product images (`data/products/`)
