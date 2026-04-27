'use client';

import { useEffect, useState, useCallback } from 'react';
import { StatsGrid } from '@/components/StatsGrid';
import { DataTable } from '@/components/DataTable';
import { RefreshCw, Database, Terminal, ShieldCheck } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function Dashboard() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const response = await fetch('/data?limit=500');
      const result = await response.json();
      if (result.success) {
        setData(result.data);
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const response = await fetch('/sync', { method: 'POST' });
      const result = await response.json();
      if (result.success) {
        await fetchData();
      } else {
        alert(`Sync failed: ${result.error}`);
      }
    } catch (error) {
      console.error('Sync failed:', error);
      alert('Sync failed. check console for details.');
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const latest = data[0] || null;

  return (
    <main className="relative min-h-screen bg-black text-zinc-100 overflow-hidden">
      {/* Background Glows */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-[600px] h-[600px] bg-emerald-600/5 rounded-full blur-[140px] pointer-events-none" />

      <div className="relative max-w-7xl mx-auto px-6 py-12 md:py-20 space-y-16">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-8">
          <div className="space-y-4">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-3 text-blue-400 font-mono text-xs font-black tracking-[0.3em] uppercase"
            >
              <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
              Live Market Console
            </motion.div>
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="text-5xl md:text-7xl font-black tracking-tight text-white"
            >
              Natural Gas <span className="text-zinc-600 font-light">Tracker</span>
            </motion.h1>
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
            className="flex items-center gap-4"
          >
            <button
              onClick={handleSync}
              disabled={syncing}
              className={`
                group relative flex items-center gap-3 px-8 py-4 rounded-2xl font-bold transition-all shadow-2xl
                ${syncing
                  ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
                  : 'bg-white text-black hover:bg-blue-50 hover:scale-[1.02] active:scale-95 shadow-white/5'}
              `}
            >
              <RefreshCw className={`w-5 h-5 ${syncing ? 'animate-spin' : 'group-hover:rotate-180 transition-transform duration-700'}`} />
              {syncing ? 'Syncing...' : 'Sync Latest Data'}
            </button>
          </motion.div>
        </div>

        {/* Stats Row */}
        <StatsGrid latest={latest} />

        {/* Table Section */}
        <div className="space-y-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-2xl bg-white/5 border border-white/10">
                <Database className="w-6 h-6 text-zinc-400" />
              </div>
              <div>
                <h2 className="text-2xl font-black text-white tracking-tight">Historical Snapshots</h2>
                <p className="text-sm text-zinc-500 font-medium">Showing most recent records from Supabase</p>
              </div>
            </div>
          </div>

          <AnimatePresence mode="wait">
            {loading ? (
              <motion.div
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="h-96 flex items-center justify-center rounded-[2rem] border border-white/[0.08] bg-zinc-900/20 backdrop-blur-3xl"
              >
                <div className="flex flex-col items-center gap-4 text-zinc-500">
                  <div className="relative">
                    <RefreshCw className="w-10 h-10 animate-spin text-blue-500" />
                    <div className="absolute inset-0 blur-xl bg-blue-500/20 animate-pulse" />
                  </div>
                  <span className="font-mono text-sm tracking-widest uppercase">Loading Database...</span>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="table"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <DataTable data={data} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Footer */}
      <footer className="mt-32 pb-12 text-center space-y-4">
        <div className="flex items-center justify-center gap-2 text-zinc-500 font-mono text-[10px] tracking-[0.4em] uppercase">
          <ShieldCheck className="w-3 h-3" />
          Secured Connection Established
        </div>
        <p className="text-zinc-700 text-xs font-mono uppercase tracking-widest">
          Build v1.2.0 • Groww API • Supabase Cloud
        </p>
      </footer>
    </main>
  );
}
