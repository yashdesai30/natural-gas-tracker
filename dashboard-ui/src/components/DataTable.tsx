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
];

export function DataTable({ 
  data, 
  onToggleFilters, 
  showFilters,
  isFiltered 
}: { 
  data: Record[], 
  onToggleFilters: () => void,
  showFilters: boolean,
  isFiltered: boolean
}) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState('');

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      globalFilter,
    },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: {
        pageSize: 15,
      },
    },
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
          <span className="text-zinc-300 font-black">{table.getFilteredRowModel().rows.length}</span>
          <span>Records Loaded</span>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-3xl border border-white/[0.08] bg-zinc-900/30 backdrop-blur-2xl shadow-2xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id} className="border-b border-white/[0.08] bg-white/[0.03]">
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className="px-8 py-5 text-xs font-bold text-zinc-400 uppercase tracking-[0.15em] cursor-pointer hover:text-white transition-colors"
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
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors group"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-8 py-4 text-sm font-medium">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        <div className="px-8 py-4 flex items-center justify-between border-t border-white/[0.08] bg-white/[0.01]">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <button
                className="p-2 rounded-lg hover:bg-white/5 disabled:opacity-20 disabled:hover:bg-transparent transition-colors"
                onClick={() => table.setPageIndex(0)}
                disabled={!table.getCanPreviousPage()}
              >
                <ChevronsLeft className="w-4 h-4" />
              </button>
              <button
                className="p-2 rounded-lg hover:bg-white/5 disabled:opacity-20 disabled:hover:bg-transparent transition-colors"
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                className="p-2 rounded-lg hover:bg-white/5 disabled:opacity-20 disabled:hover:bg-transparent transition-colors"
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
              >
                <ChevronRight className="w-4 h-4" />
              </button>
              <button
                className="p-2 rounded-lg hover:bg-white/5 disabled:opacity-20 disabled:hover:bg-transparent transition-colors"
                onClick={() => table.setPageIndex(table.getPageCount() - 1)}
                disabled={!table.getCanNextPage()}
              >
                <ChevronsRight className="w-4 h-4" />
              </button>
            </div>
            <span className="text-xs font-mono text-zinc-500 uppercase tracking-widest">
              Page <span className="text-zinc-200">{table.getState().pagination.pageIndex + 1}</span> of{' '}
              <span className="text-zinc-200">{table.getPageCount()}</span>
            </span>
          </div>

          <select
            value={table.getState().pagination.pageSize}
            onChange={(e) => table.setPageSize(Number(e.target.value))}
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
