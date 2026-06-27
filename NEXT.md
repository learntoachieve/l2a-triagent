# Triagent — session pickup

## Where things stand (P0–P5a done)
- Project renamed Solve Engine -> **Triagent**, transferred to **learntoachieve/l2a-triagent** (the L2A account). Robert's original `l2a-issue-triage` left untouched.
- P0 Foundation, P1 Ingestion, P2 Scoring, P3 Evaluation, P4 Agent, **P5a Serve layer** — all merged to main.
- P5a = a **FastAPI read API + custom web frontend** (vanilla HTML/CSS/JS, no build step), runs locally at http://localhost:8000. API + UI in one process.
- `render.yaml` deploy config is merged (build: `pip install -e .`; start: `uvicorn triagent.api.app:app --host 0.0.0.0 --port $PORT`; health: `/api/health`; DATABASE_URL is dashboard-only / sync:false).
- DB (Neon): ~648 issues, 41 scored at prompt_version "v1". Backlog fills via daily `score.run` (Gemini free-tier daily cap).

## BLOCKER (resume here): Render deploy not done
- Render now **requires a verified card even for the FREE tier** ($1 reversible auth, not a charge).
- The card verification kept freezing/resetting; the $1 holds are stuck **pending on the bank side** (all $0.00 — no actual charge occurred).
- **Tomorrow:** check if the pending holds cleared. If yes, retry the Render free-tier deploy (it should go through). If the card still won't verify, options: (a) try a different card, or (b) pivot to a no-card host — note: Streamlit Community Cloud only hosts Streamlit apps, so for the custom FastAPI frontend we'd need another free FastAPI host (e.g. research Fly.io / Railway / PythonAnywhere free tiers) OR deploy the existing Streamlit board instead of the custom UI.

## Render deploy steps (when card clears) — do these on render.com as the learntoachieve GitHub account
1. New Web Service -> repo `learntoachieve/l2a-triagent`, branch main.
2. Build Command: `pip install -e .`
3. Start Command: `uvicorn triagent.api.app:app --host 0.0.0.0 --port $PORT`
4. Instance Type: **Free** (must be selected, not Starter).
5. Env var: `DATABASE_URL` = the Neon connection string (from .env). Do NOT screenshot the value.
6. Deploy. Watch logs. Likely snag spot: the deployed app reaching Neon (connection/SSL) — handle if it fails.
7. Result: a live URL like `l2a-triagent.onrender.com` — the clickable demo.

## After deploy is live
- Make `l2a-triagent` **public** (clear with Robert first — it's on L2A's account) so resume links work.
- Add the live URL to the resume serve-layer bullet.
- Then **P6 (Proof):** solve-tracker following real PRs open->merged + actually opening PRs to real repos (pandas/dbt/duckdb). This is the highest-value remaining work.

## Backlog / later (non-blocking)
- Fill scoring backlog via daily `score.run --sleep 4` (free-tier daily cap; agent quota too).
- Re-run live `agent.run --limit 5` for agent-v1 scores (was quota-blocked; .env key bug is now fixed).
- prompt_version "v2" to address the eval-found tractability bias, then re-run eval to prove improvement.
- Decide whether to track uv.lock (currently untracked) and whether to delete the personal Venura-Wijenayake/triagent mirror.

## Useful commands
- Web app (local):   `uvicorn triagent.api.app:app --reload`  -> http://localhost:8000
- Ingest issues:     `python -m triagent.ingest.run`
- Score issues:      `python -m triagent.score.run --sleep 4`
- Agent pass:        `python -m triagent.agent.run --limit 5`
- Run eval:          `python -m triagent.eval.run_eval`
- Board (Streamlit): `streamlit run triagent/board/app.py`

## Notes
- Repo lives on the learntoachieve account: `gh` PR creation needs `gh auth switch --user learntoachieve`; git push works over HTTPS. PR numbers on l2a-triagent start at #1.
- uv on PATH only after prepending its Scripts dir. Keep .env CLOSED in the editor (DB creds; gitignored).
- Local main keeps going stale — always `git pull origin main` before branching.
