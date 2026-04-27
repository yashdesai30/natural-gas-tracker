from tracker_service.config import get_settings
from tracker_service.db import SupabaseRepository

def check():
    settings = get_settings()
    repo = SupabaseRepository(
        url=settings.supabase_url,
        key=settings.supabase_key,
        table=settings.supabase_table
    )
    data = repo.fetch_recent(limit=10)
    print(f"Fetched {len(data)} records")
    if data:
        print("Latest timestamp:", data[0].get('timestamp'))

if __name__ == "__main__":
    check()
