# Natural Gas Dashboard 💎

The premium frontend for the Natural Gas Tracker. Built with Next.js, Framer Motion, and Tailwind CSS.

## 🚀 Features
- **Real-time Table**: Paginated, sortable, and searchable data.
- **Glassmorphism UI**: High-end aesthetic with vibrant accents.
- **Python Integration**: Connects directly to the FastAPI backend for all data and sync logic.

## 🛠 Local Development

1. Ensure the Python API is running on `http://127.0.0.1:8000`.
2. Configure `.env.local`:
   ```env
   PYTHON_API_URL=http://127.0.0.1:8000
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```

## ☁️ Deployment (Vercel)

1. Push your code to GitHub.
2. Connect your repository to Vercel.
3. Set the **Root Directory** to `dashboard`.
4. Add the following **Environment Variable**:
   - `PYTHON_API_URL`: The public URL of your FastAPI backend (e.g., on Render).
5. Deploy!

## 🔧 API Proxy
The frontend proxies all `/api/data` and `/api/sync` requests to the Python backend to keep logic centralized and secure.
