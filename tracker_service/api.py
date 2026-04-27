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

# Global shared state
_shared_fetcher = None
_sync_status = {"is_syncing": False, "last_sync": None, "error": None}

def get_fetcher():
    global _shared_fetcher
    if _shared_fetcher is None:
        settings = get_settings()
        logger.info("Initializing shared GrowwDataFetcher...")
        _shared_fetcher = GrowwDataFetcher(
            access_token=settings.groww_access_token,
            api_key=settings.groww_api_key,
            totp_secret=settings.groww_totp_secret,
            cache_ttl_hours=settings.instrument_cache_ttl_hours,
        )
    return _shared_fetcher

@app.post("/sync")
async def trigger_sync(background_tasks: BackgroundTasks, days: int = 30):
    """Trigger a sync in the background."""
    global _sync_status
    if _sync_status["is_syncing"]:
        return {"success": False, "message": "Sync already in progress"}

    try:
        fetcher = get_fetcher()
    except Exception as e:
        logger.error("Failed to initialize GrowwDataFetcher: %s", str(e))
        return {"success": False, "error": f"Authentication failed: {str(e)}"}

    settings = get_settings()
    repository = SupabaseRepository(
        url=settings.supabase_url,
        key=settings.supabase_key,
        table=settings.supabase_table,
    )
    
    def run_sync_with_logs():
        global _sync_status
        _sync_status["is_syncing"] = True
        _sync_status["error"] = None
        logger.info("Background sync started for %d days", days)
        try:
            sync_history(fetcher, repository, days)
            _sync_status["last_sync"] = datetime.now(LOCAL_TIMEZONE).isoformat()
            logger.info("Background sync completed successfully")
        except Exception as e:
            _sync_status["error"] = str(e)
            logger.error("Background sync failed: %s", str(e))
        finally:
            _sync_status["is_syncing"] = False

    background_tasks.add_task(run_sync_with_logs)
    return {"success": True, "message": f"Sync started for last {days} days"}

@app.get("/sync/status")
async def get_sync_status():
    """Check the status of the background sync."""
    return {"success": True, **_sync_status}

@app.get("/data")
async def get_data(
    limit: int = 500, 
    symbol: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None
):
    """Fetch latest data from Supabase with optional filters."""
    settings = get_settings()
    repository = SupabaseRepository(
        url=settings.supabase_url,
        key=settings.supabase_key,
        table=settings.supabase_table,
    )
    
    try:
        if start_date and end_date:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            data = repository.fetch_between(start_dt, end_dt, limit=limit, symbol=symbol)
        elif start_date:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            data = repository.fetch_since(start_dt, limit=limit, symbol=symbol)
        else:
            data = repository.fetch_recent(limit=limit, symbol=symbol)
            
        return {"success": True, "data": data}
    except Exception as e:
        logger.error("Failed to fetch data: %s", str(e))
        return {"success": False, "error": str(e)}

@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now(LOCAL_TIMEZONE).isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
