'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { DataTable } from '@/components/DataTable';
import { MarketChart } from '@/components/MarketChart';
import { RefreshCw, Database, Terminal, ShieldCheck, Search, Calendar, Filter, X, TrendingUp } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function Dashboard() {
  const [data, setData] = useState<any[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [pageIndex, setPageIndex] = useState(0);
  const [pageSize, setPageSize] = useState(15);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);

  // Filter states
  const [symbolFilter, setSymbolFilter] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [showChart, setShowChart] = useState(true);
  const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);
  const [activePreset, setActivePreset] = useState('all');

  const pollInterval = useRef<NodeJS.Timeout | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      params.set('page', (pageIndex + 1).toString());
      params.set('page_size', pageSize.toString());
      if (symbolFilter) params.set('symbol', symbolFilter);
      if (startDate) params.set('start_date', startDate);
      if (endDate) params.set('end_date', endDate);

      const response = await fetch(`/api/data?${params.toString()}`);
      const result = await response.json();
      if (result.success) {
        setData(result.data);
        setTotalCount(result.total || 0);
        
        // Dynamically accumulate unique symbols to present as quick-filter options
        if (result.data) {
          const symbols = Array.from(new Set(result.data.map((r: any) => r.futures_symbol).filter(Boolean))) as string[];
          setAvailableSymbols(prev => {
            const combined = Array.from(new Set([...prev, ...symbols]));
            return combined;
          });
        }
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  }, [pageIndex, pageSize, symbolFilter, startDate, endDate]);

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

  // Reset pageIndex when filters change
  useEffect(() => {
    setPageIndex(0);
  }, [symbolFilter, startDate, endDate]);

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

  const applyDatePreset = (preset: string) => {
    const today = new Date();
    const formatDate = (date: Date) => {
      const yyyy = date.getFullYear();
      const mm = String(date.getMonth() + 1).padStart(2, '0');
      const dd = String(date.getDate()).padStart(2, '0');
      return `${yyyy}-${mm}-${dd}`;
    };

    if (preset === 'today') {
      setStartDate(formatDate(today));
      setEndDate(formatDate(today));
      setActivePreset('today');
    } else if (preset === 'yesterday') {
      const yesterday = new Date();
      yesterday.setDate(today.getDate() - 1);
      setStartDate(formatDate(yesterday));
      setEndDate(formatDate(yesterday));
      setActivePreset('yesterday');
    } else if (preset === 'week') {
      const weekAgo = new Date();
      weekAgo.setDate(today.getDate() - 7);
      setStartDate(formatDate(weekAgo));
      setEndDate(formatDate(today));
      setActivePreset('week');
    } else if (preset === 'month') {
      const monthAgo = new Date();
      monthAgo.setDate(today.getDate() - 30);
      setStartDate(formatDate(monthAgo));
      setEndDate(formatDate(today));
      setActivePreset('month');
    } else if (preset === 'all') {
      setStartDate('');
      setEndDate('');
      setActivePreset('all');
    } else if (preset === 'custom') {
      setActivePreset('custom');
    }
  };

  const clearFilters = () => {
    setSymbolFilter('');
    setStartDate('');
    setEndDate('');
    setActivePreset('all');
  };

  const latest = data[0] || null;

  return (
    <main className="relative min-h-screen bg-black text-zinc-100 overflow-hidden pb-20">
      {/* Background Glows */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-[600px] h-[600px] bg-emerald-600/5 rounded-full blur-[140px] pointer-events-none" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-8 md:py-20 space-y-12 md:space-y-16">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-8">
          <div className="space-y-3 md:space-y-4">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-3 text-blue-400 font-mono text-[10px] md:text-xs font-black tracking-[0.3em] uppercase"
            >
              <div className={`w-2 h-2 rounded-full ${syncing ? 'bg-amber-500 animate-ping' : 'bg-blue-500 animate-pulse'}`} />
              {syncing ? 'Background Sync Active' : 'Live Market Console'}
            </motion.div>
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="text-4xl sm:text-5xl md:text-7xl font-black tracking-tight text-white leading-[1.1]"
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

        {/* Chart Section */}
        <div className="space-y-8">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-2xl bg-white/5 border border-white/10 text-blue-400">
                <TrendingUp className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-2xl font-black text-white tracking-tight">Price Dynamics</h2>
                <p className="text-sm text-zinc-500 font-medium">Real-time correlation between Futures and Option premiums</p>
              </div>
            </div>
            
            <button
              onClick={() => setShowChart(!showChart)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl border border-white/10 bg-white/5 text-zinc-400 hover:text-white transition-all text-xs font-bold"
            >
              {showChart ? 'Hide Chart' : 'Show Chart'}
            </button>
          </div>

          <AnimatePresence>
            {showChart && (
              <motion.div
                initial={{ opacity: 0, height: 0, scale: 0.95 }}
                animate={{ opacity: 1, height: 'auto', scale: 1 }}
                exit={{ opacity: 0, height: 0, scale: 0.95 }}
                className="overflow-hidden"
              >
                <MarketChart data={data} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

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
                      <div className="p-8 rounded-[2rem] bg-zinc-900/40 border border-white/10 backdrop-blur-3xl grid grid-cols-1 md:grid-cols-3 gap-8 relative shadow-2xl">
                        
                        {/* Column 1: Active Instruments quick filter */}
                        <div className="space-y-4 md:col-span-2">
                          <div className="space-y-3">
                            <label className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500">
                              Filter by Instrument
                            </label>
                            <div className="flex flex-wrap gap-2">
                              {availableSymbols.length > 0 ? (
                                availableSymbols.map((sym) => {
                                  const isActive = symbolFilter === sym;
                                  return (
                                    <button
                                      key={sym}
                                      type="button"
                                      onClick={() => setSymbolFilter(isActive ? '' : sym)}
                                      className={`px-4 py-2.5 rounded-xl font-mono text-xs font-bold border transition-all hover:scale-[1.02] active:scale-95 ${
                                        isActive 
                                        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 shadow-lg shadow-emerald-500/5' 
                                        : 'bg-zinc-950/40 border-white/[0.04] text-zinc-400 hover:text-zinc-200 hover:border-white/10 hover:bg-white/[0.01]'
                                      }`}
                                    >
                                      {sym}
                                    </button>
                                  );
                                })
                              ) : (
                                <span className="text-zinc-600 text-xs font-mono">No active instruments cached...</span>
                              )}
                            </div>
                          </div>

                          <div className="space-y-2">
                            <label className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500 flex items-center gap-2">
                              <Search className="w-3 h-3 text-zinc-600" /> Manual Search
                            </label>
                            <input
                              type="text"
                              placeholder="e.g. NATURALGAS26MAY26FUT"
                              value={symbolFilter}
                              onChange={(e) => setSymbolFilter(e.target.value.toUpperCase())}
                              className="w-full bg-black/50 border border-white/5 rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:border-emerald-500/50 transition-colors placeholder:text-zinc-700 font-mono"
                            />
                          </div>
                        </div>

                        {/* Column 2: Date Ranges */}
                        <div className="space-y-4">
                          <div className="space-y-3">
                            <label className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500">
                              Quick Date Ranges
                            </label>
                            <div className="flex flex-wrap gap-2">
                              {[
                                { id: 'all', label: 'All Time' },
                                { id: 'today', label: 'Today' },
                                { id: 'yesterday', label: 'Yesterday' },
                                { id: 'week', label: 'Last 7 Days' },
                                { id: 'month', label: 'Last 30 Days' },
                                { id: 'custom', label: 'Custom Range' },
                              ].map((preset) => {
                                const isActive = activePreset === preset.id;
                                return (
                                  <button
                                    key={preset.id}
                                    type="button"
                                    onClick={() => applyDatePreset(preset.id)}
                                    className={`px-4 py-2.5 rounded-xl text-xs font-bold border transition-all hover:scale-[1.02] active:scale-95 ${
                                      isActive 
                                      ? 'bg-blue-500/10 border-blue-500/30 text-blue-400 shadow-lg shadow-blue-500/5' 
                                      : 'bg-zinc-950/40 border-white/[0.04] text-zinc-400 hover:text-zinc-200 hover:border-white/10 hover:bg-white/[0.01]'
                                    }`}
                                  >
                                    {preset.label}
                                  </button>
                                );
                              })}
                            </div>
                          </div>

                          <AnimatePresence>
                            {activePreset === 'custom' && (
                              <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                className="overflow-hidden grid grid-cols-2 gap-4 pt-2"
                              >
                                <div className="space-y-2">
                                  <label className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500 flex items-center gap-2">
                                    <Calendar className="w-3 h-3 text-zinc-600" /> From
                                  </label>
                                  <input
                                    type="date"
                                    value={startDate}
                                    onChange={(e) => setStartDate(e.target.value)}
                                    className="w-full bg-black/50 border border-white/5 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500/50 transition-colors [color-scheme:dark]"
                                  />
                                </div>
                                <div className="space-y-2">
                                  <label className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500 flex items-center gap-2">
                                    <Calendar className="w-3 h-3 text-zinc-600" /> To
                                  </label>
                                  <input
                                    type="date"
                                    value={endDate}
                                    onChange={(e) => setEndDate(e.target.value)}
                                    className="w-full bg-black/50 border border-white/5 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500/50 transition-colors [color-scheme:dark]"
                                  />
                                </div>
                              </motion.div>
                            )}
                          </AnimatePresence>
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
                  pageIndex={pageIndex}
                  pageSize={pageSize}
                  pageCount={Math.ceil(totalCount / pageSize)}
                  totalCount={totalCount}
                  onPageChange={setPageIndex}
                  onPageSizeChange={setPageSize}
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
