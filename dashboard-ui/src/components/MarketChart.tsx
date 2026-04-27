'use client';

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Area,
  ComposedChart,
  Brush,
  ReferenceLine
} from 'recharts';
import { format } from 'date-fns';

interface MarketData {
  timestamp: string;
  futures_price: number;
  ce_price: number;
  pe_price: number;
  atm_strike: number;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-zinc-900/95 backdrop-blur-2xl border border-white/10 p-4 rounded-2xl shadow-2xl space-y-3 min-w-[200px] z-50">
        <div className="flex items-center justify-between border-b border-white/5 pb-2">
          <p className="text-[10px] font-black uppercase tracking-widest text-zinc-500">
            Snapshot
          </p>
          <p className="text-[10px] font-mono text-blue-400">
            {format(new Date(label), 'dd MMM HH:mm:ss')}
          </p>
        </div>
        <div className="space-y-2">
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: entry.color }} />
                <span className="text-xs font-medium text-zinc-400">
                  {entry.name}:
                </span>
              </div>
              <span className="text-xs font-mono font-bold text-white">
                {entry.value.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};

export function MarketChart({ data }: { data: MarketData[] }) {
  const [hidden, setHidden] = React.useState<Record<string, boolean>>({
    'NG Future': false,
    'Call Premium': false,
    'Put Premium': false,
  });

  // Sort data chronologically for the chart
  const chartData = React.useMemo(() => [...data].reverse(), [data]);

  const toggleLine = (name: string) => {
    setHidden(prev => ({ ...prev, [name]: !prev[name] }));
  };

  return (
    <div className="w-full h-[550px] bg-zinc-900/20 border border-white/[0.08] rounded-[2rem] sm:rounded-[2.5rem] p-4 sm:p-8 backdrop-blur-3xl relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-blue-500/5 rounded-full blur-[120px] pointer-events-none" />
      
      <div className="relative h-full w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart 
            data={chartData}
            margin={{ top: 20, right: 20, bottom: 20, left: 10 }}
          >
            <defs>
              <linearGradient id="colorCE" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.2}/>
                <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorPE" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2}/>
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid 
              strokeDasharray="3 3" 
              vertical={false} 
              stroke="rgba(255,255,255,0.05)" 
            />
            <XAxis 
              dataKey="timestamp" 
              tickFormatter={(str) => format(new Date(str), 'HH:mm')}
              stroke="#52525b"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              dy={10}
              minTickGap={30}
            />
            <YAxis 
              yAxisId="left"
              stroke="#3b82f6"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              tickFormatter={(val) => val.toFixed(0)}
              domain={['auto', 'auto']}
              hide={hidden['NG Future']}
              label={{ value: 'Futures', angle: -90, position: 'insideLeft', offset: -5, fill: '#3b82f6', fontSize: 10, fontWeight: 'bold' }}
            />
            <YAxis 
              yAxisId="right"
              orientation="right"
              stroke="#a1a1aa"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              tickFormatter={(val) => val.toFixed(1)}
              domain={['auto', 'auto']}
              hide={hidden['Call Premium'] && hidden['Put Premium']}
              label={{ value: 'Premiums', angle: 90, position: 'insideRight', offset: -5, fill: '#a1a1aa', fontSize: 10, fontWeight: 'bold' }}
            />
            <Tooltip 
              content={<CustomTooltip />} 
              cursor={{ stroke: '#ffffff', strokeWidth: 1, strokeDasharray: '5 5' }}
            />
            <Legend 
              verticalAlign="top" 
              align="center"
              content={(props) => {
                const { payload } = props;
                return (
                  <div className="flex flex-wrap justify-center gap-4 sm:gap-8 mb-8 sm:mb-12">
                    {payload?.map((entry: any, index: number) => {
                      const isHidden = hidden[entry.value];
                      return (
                        <button 
                          key={index} 
                          onClick={() => toggleLine(entry.value)}
                          className={`flex items-center gap-3 px-4 py-2 rounded-xl border transition-all ${
                            isHidden 
                            ? 'bg-transparent border-white/5 text-zinc-700' 
                            : 'bg-white/5 border-white/10 text-white shadow-lg'
                          }`}
                        >
                          <div 
                            className={`w-2 h-2 rounded-full transition-opacity ${isHidden ? 'opacity-20' : 'opacity-100'}`} 
                            style={{ backgroundColor: entry.color }} 
                          />
                          <span className={`text-[10px] font-black uppercase tracking-widest ${isHidden ? 'line-through' : ''}`}>
                            {entry.value}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                );
              }}
            />
            
            <Area
              yAxisId="right"
              type="monotone"
              dataKey="ce_price"
              name="Call Premium"
              stroke="#10b981"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorCE)"
              animationDuration={500}
              hide={hidden['Call Premium']}
            />
            <Area
              yAxisId="right"
              type="monotone"
              dataKey="pe_price"
              name="Put Premium"
              stroke="#ef4444"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorPE)"
              animationDuration={500}
              hide={hidden['Put Premium']}
            />
            <Line
              yAxisId="left"
              type="stepAfter"
              dataKey="futures_price"
              name="NG Future"
              stroke="#3b82f6"
              strokeWidth={3}
              dot={false}
              activeDot={{ r: 6, strokeWidth: 0 }}
              animationDuration={500}
              hide={hidden['NG Future']}
            />

            <Brush 
              dataKey="timestamp" 
              height={40} 
              stroke="rgba(255,255,255,0.1)"
              fill="rgba(0,0,0,0.2)"
              gap={5}
              travellerWidth={8}
              tick={false} // Remove cheap-looking ticks
            >
              <ComposedChart>
                <defs>
                  <linearGradient id="brushGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <Area 
                  dataKey="futures_price" 
                  fill="url(#brushGradient)" 
                  stroke="#3b82f6" 
                  strokeWidth={1}
                  isAnimationActive={false}
                />
              </ComposedChart>
            </Brush>
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
