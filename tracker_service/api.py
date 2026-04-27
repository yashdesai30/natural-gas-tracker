from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import logging

from tracker_service.config import get_settings
from tracker_service.data_fetcher import GrowwDataFetcher
from tracker_service.db import SupabaseRepository
from tracker_service.main import sync_history, LOCAL_TIMEZONE

app = FastAPI(title="Natural Gas Tracker API")

# Enable CORS for Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tracker_api")
logger.setLevel(logging.INFO)

print("API Script Loaded. Logging level: INFO", flush=True)

@app.post("/sync")
async def trigger_sync(background_tasks: BackgroundTasks, days: int = 30):
    """Trigger a sync in the background."""
    settings = get_settings()
    fetcher = GrowwDataFetcher(
        access_token=settings.groww_access_token,
        api_key=settings.groww_api_key,
        totp_secret=settings.groww_totp_secret,
        cache_ttl_hours=settings.instrument_cache_ttl_hours,
    )
    repository = SupabaseRepository(
        url=settings.supabase_url,
        key=settings.supabase_key,
        table=settings.supabase_table,
    )
    
    print(f"DEBUG: Sync requested for {days} days", flush=True)
    logger.info("Sync requested for %d days", days)
    
    def run_sync_with_logs():
        logger.info("Background sync started for %d days", days)
        try:
            sync_history(fetcher, repository, days)
            logger.info("Background sync completed successfully")
        except Exception as e:
            logger.error("Background sync failed: %s", str(e))

    background_tasks.add_task(run_sync_with_logs)
    
    return {"success": True, "message": f"Sync started for last {days} days"}

@app.get("/data")
async def get_data(limit: int = 500):
    """Fetch latest data from Supabase."""
    print(f"DEBUG: Fetching data with limit: {limit}", flush=True)
    logger.info("Fetching data with limit: %d", limit)
    settings = get_settings()
    repository = SupabaseRepository(
        url=settings.supabase_url,
        key=settings.supabase_key,
        table=settings.supabase_table,
    )
    data = repository.fetch_recent(limit=limit)
    logger.info("Fetched %d records", len(data))
    return {"success": True, "data": data}

@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now(LOCAL_TIMEZONE).isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
