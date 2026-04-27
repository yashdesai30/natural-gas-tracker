'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { StatsGrid } from '@/components/StatsGrid';
import { DataTable } from '@/components/DataTable';
import { RefreshCw, Database, Terminal, ShieldCheck, Search, Calendar, Filter, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function Dashboard() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);

  // Filter states
  const [symbolFilter, setSymbolFilter] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  const pollInterval = useRef<NodeJS.Timeout | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      params.set('limit', '500');
      if (symbolFilter) params.set('symbol', symbolFilter);
      if (startDate) params.set('start_date', startDate);
      if (endDate) params.set('end_date', endDate);

      const response = await fetch(`/api/data?${params.toString()}`);
      const result = await response.json();
      if (result.success) {
        setData(result.data);
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  }, [symbolFilter, startDate, endDate]);

  const checkSyncStatus = useCallback(async () => {
    try {
      const response = await fetch('/api/sync/status');
      const result = await response.json();

      if (result.success) {
        setSyncing(result.is_syncing);
        setSyncError(result.error);

        // If sync just finished, refresh data
        if (!result.is_syncing && syncing) {
          fetchData();
        }
      }
    } catch (error) {
      console.error('Failed to check sync status:', error);
    }
  }, [syncing, fetchData]);

  const handleSync = async () => {
    setSyncing(true);
    setSyncError(null);
    try {
      const response = await fetch('/api/sync', { method: 'POST' });
      const result = await response.json();
      if (!result.success) {
        setSyncError(result.error || 'Failed to start sync');
        setSyncing(false);
      }
    } catch (error) {
      console.error('Sync failed:', error);
      setSyncError('Network error starting sync');
      setSyncing(false);
    }
  };

  // Poll sync status if syncing is true
  useEffect(() => {
    if (syncing) {
      pollInterval.current = setInterval(checkSyncStatus, 3000);
    } else {
      if (pollInterval.current) clearInterval(pollInterval.current);
    }
    return () => {
      if (pollInterval.current) clearInterval(pollInterval.current);
    };
  }, [syncing, checkSyncStatus]);

  // Initial fetch and fetch on filter change
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchData();
    }, 500); // Debounce filter changes
    return () => clearTimeout(timer);
  }, [fetchData]);

  // Check status on mount in case a sync was already running
  useEffect(() => {
    checkSyncStatus();
  }, []);

  const clearFilters = () => {
    setSymbolFilter('');
    setStartDate('');
    setEndDate('');
  };

  const latest = data[0] || null;

  return (
    <main className="relative min-h-screen bg-black text-zinc-100 overflow-hidden pb-20">
      {/* Background Glows */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-[600px] h-[600px] bg-emerald-600/5 rounded-full blur-[140px] pointer-events-none" />

      <div className="relative max-w-7xl mx-auto px-6 py-12 md:py-20 space-y-16">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-8">
          <div className="space-y-4">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-3 text-blue-400 font-mono text-xs font-black tracking-[0.3em] uppercase"
            >
              <div className={`w-2 h-2 rounded-full ${syncing ? 'bg-amber-500 animate-ping' : 'bg-blue-500 animate-pulse'}`} />
              {syncing ? 'Background Sync Active' : 'Live Market Console'}
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
            className="flex flex-wrap items-center gap-4"
          >
            <button
              onClick={handleSync}
              disabled={syncing}
              className={`
                group relative flex items-center gap-3 px-8 py-4 rounded-2xl font-bold transition-all shadow-2xl
                ${syncing
                  ? 'bg-zinc-900 text-amber-500 cursor-not-allowed border border-amber-500/20'
                  : 'bg-white text-black hover:bg-blue-50 hover:scale-[1.02] active:scale-95 shadow-white/5'}
              `}
            >
              <RefreshCw className={`w-5 h-5 ${syncing ? 'animate-spin' : 'group-hover:rotate-180 transition-transform duration-700'}`} />
              {syncing ? 'Updating Database...' : 'Sync Latest'}
            </button>
          </motion.div>
        </div>

        {syncError && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm font-medium flex items-center gap-3"
          >
            <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
            Sync Error: {syncError}
          </motion.div>
        )}

        {/* Stats Row */}
        <StatsGrid latest={latest} />

        {/* Table Section */}
        <div className="space-y-8">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-2xl bg-white/5 border border-white/10">
                <Database className="w-6 h-6 text-zinc-400" />
              </div>
              <div>
                <h2 className="text-2xl font-black text-white tracking-tight">Market Snapshots</h2>
                <p className="text-sm text-zinc-500 font-medium">
                  {symbolFilter || startDate
                    ? `Showing filtered results (${data.length} records)`
                    : 'Showing most recent records from Supabase'}
                </p>
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
                  <span className="font-mono text-sm tracking-widest uppercase text-center px-4">
                    Retrieving Market Intelligence...
                  </span>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="table"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="space-y-6"
              >
                {/* Filter Panel (Now appears ABOVE the table) */}
                <AnimatePresence>
                  {showFilters && (
                    <motion.div
                      initial={{ opacity: 0, height: 0, y: -10 }}
                      animate={{ opacity: 1, height: 'auto', y: 0 }}
                      exit={{ opacity: 0, height: 0, y: -10 }}
                      className="overflow-hidden"
                    >
                      <div className="p-8 rounded-[2rem] bg-zinc-900/40 border border-white/10 backdrop-blur-3xl grid grid-cols-1 md:grid-cols-3 gap-8 relative">
                        <div className="space-y-3">
                          <label className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500 flex items-center gap-2">
                            <Search className="w-3 h-3" /> Search Symbol
                          </label>
                          <input
                            type="text"
                            placeholder="e.g. NATURALGAS24MAYFUT"
                            value={symbolFilter}
                            onChange={(e) => setSymbolFilter(e.target.value.toUpperCase())}
                            className="w-full bg-black/50 border border-white/5 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500/50 transition-colors placeholder:text-zinc-700"
                          />
                        </div>
                        <div className="space-y-3">
                          <label className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500 flex items-center gap-2">
                            <Calendar className="w-3 h-3" /> From Date
                          </label>
                          <input
                            type="date"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                            className="w-full bg-black/50 border border-white/5 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500/50 transition-colors [color-scheme:dark]"
                          />
                        </div>
                        <div className="space-y-3">
                          <label className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500 flex items-center gap-2">
                            <Calendar className="w-3 h-3" /> To Date
                          </label>
                          <input
                            type="date"
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                            className="w-full bg-black/50 border border-white/5 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500/50 transition-colors [color-scheme:dark]"
                          />
                        </div>

                        <button
                          onClick={clearFilters}
                          className="absolute top-4 right-4 p-2 text-zinc-600 hover:text-white transition-colors"
                        >
                          <X className="w-5 h-5" />
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                <DataTable 
                  data={data} 
                  showFilters={showFilters}
                  onToggleFilters={() => setShowFilters(!showFilters)}
                  isFiltered={!!(symbolFilter || startDate || endDate)}
                />

                {data.length === 0 && (
                  <div className="py-20 text-center space-y-4">
                    <div className="inline-flex p-4 rounded-full bg-white/5 text-zinc-700">
                      <Search className="w-8 h-8" />
                    </div>
                    <p className="text-zinc-500 font-medium">No records found for the selected criteria.</p>
                  </div>
                )}
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
          Build v1.3.0 • Groww API • Supabase Cloud
        </p>
      </footer>
    </main>
  );
}
