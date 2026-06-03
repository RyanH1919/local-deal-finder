"""
Test entry point — runs the pipeline once immediately, then starts the API server.
Use this instead of main.py while testing.
"""
from database.db import init_db
from scheduler.jobs import run_pipeline
import uvicorn

if __name__ == "__main__":
    init_db()
    run_pipeline()
    print("[api] starting on http://localhost:8000")
    uvicorn.run("api.routes:app", host="0.0.0.0", port=8000, reload=False)
