'use client'

import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable,
} from '@tanstack/react-table'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { EmptyState } from '@/components/shared/EmptyState'
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination'
import { useState } from 'react'

interface DataTableProps<TData, TValue> {
  data: TData[]
  columns: ColumnDef<TData, TValue>[]
  isLoading?: boolean
  emptyMessage?: string
  pageSize?: number
}

export function DataTable<TData, TValue>({
  data,
  columns,
  isLoading,
  emptyMessage = 'No hay datos para mostrar',
  pageSize = 10,
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = useState<SortingState>([])

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    state: {
      sorting,
    },
    initialState: {
      pagination: {
        pageSize,
      },
    },
  })

  if (isLoading) {
    return <LoadingSpinner label="Cargando datos..." />
  }

  if (!data.length) {
    return <EmptyState description={emptyMessage} />
  }

  return (
    <div className="space-y-4">
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id} data-state={row.getIsSelected() && 'selected'}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  <EmptyState description={emptyMessage} />
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      {table.getPageCount() > 1 && (
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                href="#"
                onClick={(e) => {
                  e.preventDefault()
                  table.previousPage()
                }}
                className={!table.getCanPreviousPage() ? 'pointer-events-none opacity-50' : ''}
              />
            </PaginationItem>
            {Array.from({ length: Math.min(5, table.getPageCount()) }).map((_, i) => {
              const currentPage = table.getState().pagination.pageIndex
              const totalPages = table.getPageCount()
              let pageIndex: number
              if (totalPages <= 5) {
                pageIndex = i
              } else if (currentPage < 3) {
                pageIndex = i
              } else if (currentPage > totalPages - 4) {
                pageIndex = totalPages - 5 + i
              } else {
                pageIndex = currentPage - 2 + i
              }
              return (
                <PaginationItem key={pageIndex}>
                  <a
                    href="#"
                    onClick={(e) => {
                      e.preventDefault()
                      table.setPageIndex(pageIndex)
                    }}
                    className={`flex h-10 items-center justify-center rounded-md px-3 text-sm transition-colors ${
                      pageIndex === currentPage
                        ? 'bg-primary text-primary-foreground'
                        : 'hover:bg-muted'
                    }`}
                  >
                    {pageIndex + 1}
                  </a>
                </PaginationItem>
              )
            })}
            <PaginationItem>
              <PaginationNext
                href="#"
                onClick={(e) => {
                  e.preventDefault()
                  table.nextPage()
                }}
                className={!table.getCanNextPage() ? 'pointer-events-none opacity-50' : ''}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}
    </div>
  )
}
