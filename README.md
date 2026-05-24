# Natural Gas Tracker 🚀

A premium real-time monitoring and historical analysis dashboard for MCX Natural Gas futures and ATM options. Powered by a Python FastAPI backend and a Next.js frontend.

## 🏗 Architecture

- **Backend**: Python FastAPI (Groww API integration, Data logic, Background Sync).
- **Frontend**: Next.js 15+ with Tailwind CSS (Vibrant dark mode, Real-time data table).
- **Database**: Supabase (PostgreSQL) for persistent storage and sampling.
- **Rules**: Automatic 5-minute sampling and "Last Thursday" rollover logic.

## 🚀 Local Setup

### 1. Python Backend
```bash
# Create virtualenv
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the API
export PYTHONPATH=$PYTHONPATH:.
python -m tracker_service.api
```

### 2. Next.js Frontend
```bash
cd dashboard
npm install
npm run dev
```

## ☁️ Deployment

### 1. Backend (Render)
1. Create a new **Web Service** on Render.
2. The `.python-version` file will automatically set Python to `3.11.9`.
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python render_app.py`
5. Environment Variables:
   - `SUPABASE_URL`: Your Supabase Project URL
   - `SUPABASE_KEY`: Your Supabase API Key
   - `GROWW_ACCESS_TOKEN`: Your Groww Access Token
   - `GROWW_TOTP_SECRET`: (Optional) For automated re-auth
   - `PYTHONPATH`: `.`

### 2. Frontend (Vercel)
1. Import the `dashboard` directory into Vercel.
2. Environment Variables:
   - `PYTHON_API_URL`: The URL of your Render backend.
3. Build & Deploy.

## 📊 Market Rules
- **Windows**: 9:00-9:15, 15:00-15:15, 17:00-17:30, 20:00-20:30.
- **Sampling**: Every 5 minutes (0, 5, 10...).
- **Rollover**: If current date < Last Thursday of the month, stay in current contract; otherwise, roll to next month.


Testing 
