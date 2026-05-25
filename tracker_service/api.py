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

@app.post("/auth/refresh")
async def manual_token_refresh():
    """Manually trigger an access token refresh using credentials/TOTP."""
    try:
        fetcher = get_fetcher()
        fetcher.refresh_token()
        return {"success": True, "message": "Access token refreshed successfully"}
    except Exception as e:
        logger.error("Failed to manually refresh access token: %s", str(e))
        return {"success": False, "error": str(e)}

def enrich_records(records: list[dict[str, object]], repository: SupabaseRepository) -> list[dict[str, object]]:
    if not records:
        return []
    
    # Sort chronologically to calculate morning prices and previous day closes accurately
    sorted_records = sorted(records, key=lambda x: str(x.get("timestamp", "")))
    
    # Map each record to its IST date and time
    for r in sorted_records:
        ts = datetime.fromisoformat(str(r["timestamp"]).replace("Z", "+00:00")).astimezone(LOCAL_TIMEZONE)
        r["ist_date"] = ts.strftime("%Y-%m-%d")
        r["ist_time"] = ts.strftime("%H:%M:%S")
        r["ce_pe_total"] = (float(r.get("ce_price") or 0) + float(r.get("pe_price") or 0)) if (r.get("ce_price") is not None and r.get("pe_price") is not None) else None
        
    morning_cache = {}
    prev_day_close_cache = {}
    
    # Enrich each record
    enriched = []
    from datetime import timezone
    for r in sorted_records:
        date_str = r["ist_date"]
        futures_symbol = r.get("futures_symbol")
        cache_key = (date_str, futures_symbol)
        
        # Get morning record (first record of IST day)
        if cache_key not in morning_cache:
            morning_cache[cache_key] = repository.fetch_first_of_day(date_str, symbol=futures_symbol)
            
        morning_rec = morning_cache[cache_key]
        if morning_rec:
            m_ce = float(morning_rec.get("ce_price") or 0) if morning_rec.get("ce_price") is not None else None
            m_pe = float(morning_rec.get("pe_price") or 0) if morning_rec.get("pe_price") is not None else None
            if m_ce is not None and m_pe is not None:
                m_total = m_ce + m_pe
                r["morning_ce"] = m_ce
                r["morning_pe"] = m_pe
                r["morning_total"] = m_total
                if r["ce_pe_total"] is not None:
                    r["morning_diff"] = r["ce_pe_total"] - m_total
                else:
                    r["morning_diff"] = None
            else:
                r["morning_ce"] = r["morning_pe"] = r["morning_total"] = r["morning_diff"] = None
        else:
            r["morning_ce"] = r["morning_pe"] = r["morning_total"] = r["morning_diff"] = None
        
        # Get previous day closing record
        if cache_key not in prev_day_close_cache:
            start_dt_ist = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=LOCAL_TIMEZONE)
            start_dt_utc = start_dt_ist.astimezone(timezone.utc)
            prev_day_close_cache[cache_key] = repository.fetch_last_before(start_dt_utc, symbol=futures_symbol)
            
        prev_day_rec = prev_day_close_cache[cache_key]
        if prev_day_rec:
            p_ce = float(prev_day_rec.get("ce_price") or 0) if prev_day_rec.get("ce_price") is not None else None
            p_pe = float(prev_day_rec.get("pe_price") or 0) if prev_day_rec.get("pe_price") is not None else None
            p_fut = float(prev_day_rec.get("futures_price") or 0) if prev_day_rec.get("futures_price") is not None else None
            r["prev_day_ce"] = p_ce
            r["prev_day_pe"] = p_pe
            r["prev_day_future"] = p_fut
            if p_ce is not None and p_pe is not None:
                r["prev_day_total"] = p_ce + p_pe
                if r["ce_pe_total"] is not None:
                    r["prev_day_diff"] = r["ce_pe_total"] - r["prev_day_total"]
                else:
                    r["prev_day_diff"] = None
            else:
                r["prev_day_total"] = None
                r["prev_day_diff"] = None
        else:
            r["prev_day_ce"] = r["prev_day_pe"] = r["prev_day_future"] = r["prev_day_total"] = r["prev_day_diff"] = None
            
        enriched.append(r)
        
    return enriched[::-1]

@app.get("/data")
async def get_data(
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
    symbol: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None
):
    """Fetch paginated data from Supabase with optional filters."""
    settings = get_settings()
    repository = SupabaseRepository(
        url=settings.supabase_url,
        key=settings.supabase_key,
        table=settings.supabase_table,
    )
    
    try:
        start_dt = None
        end_dt = None
        if start_date:
            dt_parsed = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            start_dt = datetime.combine(dt_parsed.date(), datetime.min.time(), tzinfo=LOCAL_TIMEZONE)
        if end_date:
            dt_parsed = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            end_dt = datetime.combine(dt_parsed.date(), datetime.max.time(), tzinfo=LOCAL_TIMEZONE)
            
        data, total_count = repository.fetch_paginated(
            page=page,
            page_size=page_size,
            symbol=symbol,
            start_date=start_dt,
            end_date=end_dt
        )
        
        enriched_data = enrich_records(data, repository)
        return {
            "success": True, 
            "data": enriched_data,
            "total": total_count,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        logger.error("Failed to fetch paginated data: %s", str(e))
        return {"success": False, "error": str(e)}

@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now(LOCAL_TIMEZONE).isoformat()}

import threading
import time as time_module
from tracker_service.main import resolve_daily_selection, run_once
from tracker_service.intraday_windows import build_intraday_windows

def run_tracker_loop():
    logger.info("Background options tracker loop thread started!")
    settings = get_settings()
    
    # 1. Initialize fetcher
    try:
        fetcher = GrowwDataFetcher(
            access_token=settings.groww_access_token,
            api_key=settings.groww_api_key,
            totp_secret=settings.groww_totp_secret,
            cache_ttl_hours=settings.instrument_cache_ttl_hours,
        )
    except Exception as e:
        logger.error("Failed to initialize GrowwDataFetcher in loop: %s", str(e))
        return
        
    # 2. Initialize repository
    repository = SupabaseRepository(
        url=settings.supabase_url,
        key=settings.supabase_key,
        table=settings.supabase_table,
    )
    
    # 3. Perform boot sync for today to fill any gaps
    try:
        logger.info("Booting historical sync for last 1 day to fill gaps...")
        sync_history(fetcher, repository, days=1)
    except Exception as e:
        logger.error("Boot historical sync failed: %s", str(e))

    logger.info("Starting continuous 5-minute sampling loop...")
    current_selection = None
    while True:
        loop_start = time_module.monotonic()
        try:
            local_now = datetime.now(LOCAL_TIMEZONE)
            current_date = local_now.date()
            
            # Check if we are in a monitoring window
            windows = build_intraday_windows(current_date, current_date, now=local_now)
            is_in_window = any(w[0] <= local_now <= w[1] for w in windows)
            
            if is_in_window:
                if current_selection is None or current_selection.trading_date != current_date:
                    instruments = fetcher.get_mcx_instruments()
                    current_selection = resolve_daily_selection(
                        fetcher=fetcher,
                        repository=repository,
                        instruments=instruments,
                        trading_date=current_date,
                    )
                run_once(fetcher, repository, current_selection)
            else:
                # Log occasionally
                if local_now.minute % 15 == 0 and local_now.second < 10:
                    logger.info("Outside monitoring windows. Sleeping...")

        except Exception:
            logger.exception("ATM tracker loop cycle failed")

        elapsed = time_module.monotonic() - loop_start
        time_module.sleep(max(1, settings.poll_interval_seconds - elapsed))

@app.on_event("startup")
def start_background_tracker():
    logger.info("Spawning background options tracker daemon thread...")
    thread = threading.Thread(target=run_tracker_loop, name="NG-Options-Tracker", daemon=True)
    thread.start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
