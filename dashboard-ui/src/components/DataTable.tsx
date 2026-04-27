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
import { Search, ChevronDown, ChevronUp, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';
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

export function DataTable({ data }: { data: Record[] }) {
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
      {/* Filters & Search */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
          <input
            type="text"
            value={globalFilter ?? ''}
            onChange={(e) => setGlobalFilter(e.target.value)}
            placeholder="Search records..."
            className="w-full bg-zinc-900/50 border border-white/[0.08] rounded-2xl pl-12 pr-4 py-3 text-sm text-white focus:outline-none focus:ring-4 focus:ring-blue-500/10 focus:border-white/20 transition-all placeholder:text-zinc-600"
          />
        </div>
        
        <div className="flex items-center gap-2 text-zinc-500 text-xs font-mono uppercase tracking-widest">
          <span className="text-zinc-300 font-bold">{table.getFilteredRowModel().rows.length}</span>
          <span>Results Found</span>
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
