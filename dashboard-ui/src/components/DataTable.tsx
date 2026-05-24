'use client';

import React, { useState } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  flexRender,
  createColumnHelper,
  SortingState,
} from '@tanstack/react-table';
import { Search, ChevronDown, ChevronUp, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, Filter, Database } from 'lucide-react';
import { format } from 'date-fns';

interface Record {
  id: string;
  timestamp: string;
  futures_price: number;
  atm_strike: number;
  ce_price: number;
  pe_price: number;
  futures_symbol: string;
  ce_pe_total?: number;
  prev_day_ce?: number;
  prev_day_pe?: number;
  prev_day_future?: number;
  prev_day_total?: number;
  morning_diff?: number;
}

const columnHelper = createColumnHelper<Record>();

const columns = [
  columnHelper.accessor('timestamp', {
    header: 'Time',
    cell: (info) => format(new Date(info.getValue()), 'dd MMM HH:mm:ss'),
  }),
  columnHelper.accessor('futures_symbol', {
    header: 'Symbol',
    cell: (info) => <span className="font-mono text-zinc-400 text-xs">{info.getValue() || 'N/A'}</span>,
  }),
  columnHelper.accessor('futures_price', {
    header: 'Future',
    cell: (info) => <span className="font-mono text-blue-400">{info.getValue().toFixed(2)}</span>,
  }),
  columnHelper.accessor('atm_strike', {
    header: 'ATM',
    cell: (info) => <span className="font-mono text-zinc-300 font-bold">{info.getValue()}</span>,
  }),
  columnHelper.accessor('ce_price', {
    header: 'CE',
    cell: (info) => <span className="font-mono text-emerald-400">{info.getValue().toFixed(2)}</span>,
  }),
  columnHelper.accessor('pe_price', {
    header: 'PE',
    cell: (info) => <span className="font-mono text-rose-400">{info.getValue().toFixed(2)}</span>,
  }),
  columnHelper.accessor('ce_pe_total', {
    header: 'Total (CE+PE)',
    cell: (info) => {
      const val = info.getValue();
      return <span className="font-mono text-white font-semibold">{val !== undefined && val !== null ? val.toFixed(2) : '-'}</span>;
    },
  }),
  columnHelper.accessor('prev_day_future', {
    header: 'Prev Close (Fut/CE/PE)',
    cell: (info) => {
      const row = info.row.original;
      if (
        row.prev_day_future === undefined || 
        row.prev_day_future === null || 
        row.prev_day_ce === undefined || 
        row.prev_day_ce === null || 
        row.prev_day_pe === undefined || 
        row.prev_day_pe === null
      ) {
        return <span className="text-zinc-600 font-mono text-xs">-</span>;
      }
      return (
        <span className="font-mono text-xs">
          <span className="text-blue-400">{row.prev_day_future.toFixed(2)}</span>
          <span className="text-zinc-600 mx-1">/</span>
          <span className="text-emerald-500/70">{row.prev_day_ce.toFixed(2)}</span>
          <span className="text-zinc-600 mx-1">/</span>
          <span className="text-rose-500/70">{row.prev_day_pe.toFixed(2)}</span>
        </span>
      );
    },
  }),
  columnHelper.accessor('morning_diff', {
    header: 'Morning Diff',
    cell: (info) => {
      const val = info.getValue();
      if (val === undefined || val === null) {
        return <span className="text-zinc-600 font-mono text-xs">-</span>;
      }
      const isPositive = val >= 0;
      return (
        <span className={`font-mono text-xs font-bold ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
          {isPositive ? '+' : ''}{val.toFixed(2)}
        </span>
      );
    },
  }),
];

export function DataTable({ 
  data, 
  pageIndex,
  pageSize,
  pageCount,
  totalCount,
  onPageChange,
  onPageSizeChange,
  onToggleFilters, 
  showFilters,
  isFiltered 
}: { 
  data: Record[], 
  pageIndex: number,
  pageSize: number,
  pageCount: number,
  totalCount: number,
  onPageChange: (index: number) => void,
  onPageSizeChange: (size: number) => void,
  onToggleFilters: () => void,
  showFilters: boolean,
  isFiltered: boolean
}) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState('');

  const table = useReactTable({
    data,
    columns,
    pageCount,
    state: {
      sorting,
      globalFilter,
      pagination: {
        pageIndex,
        pageSize,
      },
    },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    manualPagination: true,
    getPaginationRowModel: getPaginationRowModel(),
  });

  return (
    <div className="space-y-6">
      {/* Filters & Actions */}
      <div className="flex items-center justify-between gap-4">
        <button
          onClick={onToggleFilters}
          className={`flex items-center gap-3 px-6 py-3 rounded-2xl font-bold transition-all border ${
            showFilters || isFiltered
            ? 'bg-white text-black border-white shadow-xl shadow-white/10' 
            : 'bg-zinc-900/50 border-white/[0.08] text-zinc-400 hover:text-white hover:border-white/20'
          }`}
        >
          <Filter className="w-4 h-4" />
          {showFilters ? 'Hide Filters' : 'Show Filters'}
          {isFiltered && <div className="w-1.5 h-1.5 rounded-full bg-blue-500 ml-1" />}
        </button>
        
        <div className="flex items-center gap-2 text-zinc-500 text-[10px] font-mono uppercase tracking-[0.2em]">
          <Database className="w-3 h-3" />
          <span className="text-zinc-300 font-black">{totalCount}</span>
          <span>Records Found</span>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-3xl border border-white/[0.08] bg-zinc-900/30 backdrop-blur-2xl shadow-2xl">
        <div className="overflow-auto max-h-[550px] relative">
          <table className="w-full text-left border-collapse min-w-[1050px]">
            <thead>
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id} className="sticky top-0 z-30 border-b border-white/[0.08] bg-zinc-950/95 backdrop-blur-md">
                  {headerGroup.headers.map((header) => {
                    const isTime = header.column.id === 'timestamp';
                    return (
                      <th
                        key={header.id}
                        className={`px-4 sm:px-8 py-5 text-[10px] sm:text-xs font-bold text-zinc-400 uppercase tracking-[0.15em] cursor-pointer hover:text-white transition-colors bg-zinc-950/90
                          ${isTime ? 'sticky left-0 z-40 border-r border-white/[0.08] shadow-[4px_0_10px_-3px_rgba(0,0,0,0.5)] bg-zinc-950' : ''}
                        `}
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        <div className="flex items-center gap-2">
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {{
                            asc: <ChevronUp className="w-4 h-4 text-blue-400" />,
                            desc: <ChevronDown className="w-4 h-4 text-blue-400" />,
                          }[header.column.getIsSorted() as string] ?? null}
                        </div>
                      </th>
                    );
                  })}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors group"
                >
                  {row.getVisibleCells().map((cell) => {
                    const isTime = cell.column.id === 'timestamp';
                    return (
                      <td 
                        key={cell.id} 
                        className={`px-4 sm:px-8 py-4 text-xs sm:text-sm font-medium
                          ${isTime ? 'sticky left-0 z-10 bg-zinc-950/95 group-hover:bg-zinc-900 border-r border-white/[0.08] shadow-[4px_0_10px_-3px_rgba(0,0,0,0.5)] transition-colors' : ''}
                        `}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        <div className="px-4 sm:px-8 py-4 flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-white/[0.08] bg-white/[0.01]">
          <div className="flex items-center gap-4 sm:gap-6">
            <div className="flex items-center gap-2">
              <button
                className="p-2 rounded-lg hover:bg-white/5 disabled:opacity-20 disabled:hover:bg-transparent transition-colors"
                onClick={() => onPageChange(0)}
                disabled={pageIndex === 0}
              >
                <ChevronsLeft className="w-4 h-4" />
              </button>
              <button
                className="p-2 rounded-lg hover:bg-white/5 disabled:opacity-20 disabled:hover:bg-transparent transition-colors"
                onClick={() => onPageChange(pageIndex - 1)}
                disabled={pageIndex === 0}
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                className="p-2 rounded-lg hover:bg-white/5 disabled:opacity-20 disabled:hover:bg-transparent transition-colors"
                onClick={() => onPageChange(pageIndex + 1)}
                disabled={pageIndex >= pageCount - 1}
              >
                <ChevronRight className="w-4 h-4" />
              </button>
              <button
                className="p-2 rounded-lg hover:bg-white/5 disabled:opacity-20 disabled:hover:bg-transparent transition-colors"
                onClick={() => onPageChange(pageCount - 1)}
                disabled={pageIndex >= pageCount - 1}
              >
                <ChevronsRight className="w-4 h-4" />
              </button>
            </div>
            <span className="text-xs font-mono text-zinc-500 uppercase tracking-widest">
              Page <span className="text-zinc-200">{pageIndex + 1}</span> of{' '}
              <span className="text-zinc-200">{pageCount || 1}</span>
            </span>
          </div>

          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className="bg-transparent text-xs font-mono text-zinc-400 uppercase tracking-widest border-none focus:ring-0 cursor-pointer hover:text-white"
          >
            {[15, 30, 50, 100].map((pageSize) => (
              <option key={pageSize} value={pageSize} className="bg-zinc-900 text-white">
                Show {pageSize}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
