'use client';

import { motion } from 'framer-motion';
import { TrendingUp, Target, ArrowUpCircle, ArrowDownCircle } from 'lucide-react';

interface StatsGridProps {
  latest: {
    futures_price: number;
    atm_strike: number;
    ce_price: number;
    pe_price: number;
  } | null;
}

export function StatsGrid({ latest }: StatsGridProps) {
  if (!latest) return null;

  const stats = [
    {
      label: 'Futures Price',
      value: latest.futures_price.toFixed(2),
      icon: TrendingUp,
      color: 'text-blue-400',
      bg: 'bg-blue-400/10',
    },
    {
      label: 'ATM Strike',
      value: latest.atm_strike,
      icon: Target,
      color: 'text-zinc-400',
      bg: 'bg-zinc-400/10',
    },
    {
      label: 'ATM CE',
      value: latest.ce_price.toFixed(2),
      icon: ArrowUpCircle,
      color: 'text-emerald-400',
      bg: 'bg-emerald-400/10',
    },
    {
      label: 'ATM PE',
      value: latest.pe_price.toFixed(2),
      icon: ArrowDownCircle,
      color: 'text-rose-400',
      bg: 'bg-rose-400/10',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat, i) => (
        <motion.div
          key={stat.label}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.1 }}
          className="relative overflow-hidden group rounded-3xl border border-white/[0.08] bg-zinc-900/40 p-8 backdrop-blur-2xl transition-all hover:border-white/20 hover:bg-zinc-900/60"
        >
          <div className={`absolute top-0 right-0 w-32 h-32 -mr-12 -mt-12 rounded-full blur-[80px] opacity-30 ${stat.bg}`} />
          
          <div className="flex items-center gap-4 mb-6">
            <div className={`p-3 rounded-2xl ${stat.bg} shadow-lg shadow-black/20`}>
              <stat.icon className={`w-6 h-6 ${stat.color}`} />
            </div>
            <span className="text-zinc-400 text-xs font-bold tracking-[0.2em] uppercase">{stat.label}</span>
          </div>

          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-black text-white tracking-tighter">{stat.value}</span>
          </div>
        </motion.div>
      ))}
    </div>
  );
}
